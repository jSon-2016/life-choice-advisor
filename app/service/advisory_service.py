"""咨询编排：Multi-Agent + RAG + 报告持久化。"""

import time

from app.agents.cancel import check_cancelled
from app.dto.career import CareerProfile, CareerRecommendation
from app.dto.gaokao import GaokaoProfile, GaokaoRecommendation
from app.graphs.career_graph import run_career_advisory
from app.graphs.gaokao_graph import run_gaokao_advisory
from app.observability.progress import emit_progress
from app.observability.tracing import log_advisory_done, log_rag_done
from app.service.rag_service import RAGService
from app.service.report_service import ReportService

_RAG_REFUSAL_HINT = (
    "\n\n## 系统约束（RAG 低置信）\n"
    "知识库未命中可靠依据，各 Agent 不得编造具体院校/专业/分数线/薪资；"
    "仅输出通用分析框架，并在报告中提醒用户查阅官方渠道。"
)


class AdvisoryService:
    """咨询编排：RAG 检索 → LangGraph 多 Agent → MySQL 存报告。"""

    def __init__(self, rag_service: RAGService, report_service: ReportService) -> None:
        self._rag = rag_service
        self._reports = report_service

    def advise_gaokao(
        self,
        user_id: str,
        profile: GaokaoProfile,
        *,
        imported_report_context: str | None = None,
    ) -> GaokaoRecommendation:
        start = time.perf_counter()
        rag_context = self._run_rag(lambda: self._rag.build_context_for_gaokao(profile.model_dump()))
        result = run_gaokao_advisory(
            profile,
            rag_context=rag_context,
            imported_report_context=imported_report_context or "",
        )
        check_cancelled()
        report_id = self._reports.save_gaokao(user_id, profile, result)
        result.report_id = report_id
        log_advisory_done(advisory_type="gaokao", elapsed_ms=int((time.perf_counter() - start) * 1000))
        return result

    def advise_career(
        self,
        user_id: str,
        profile: CareerProfile,
        *,
        imported_report_context: str | None = None,
    ) -> CareerRecommendation:
        start = time.perf_counter()
        rag_context = self._run_rag(lambda: self._rag.build_context_for_career(profile.model_dump()))
        result = run_career_advisory(
            profile,
            rag_context=rag_context,
            imported_report_context=imported_report_context or "",
        )
        check_cancelled()
        report_id = self._reports.save_career(user_id, profile, result)
        result.report_id = report_id
        log_advisory_done(advisory_type="career", elapsed_ms=int((time.perf_counter() - start) * 1000))
        return result

    def _run_rag(self, builder):
        emit_progress(step="rag", status="started", message="混合检索 + Rerank")
        rag_start = time.perf_counter()
        rag_result = builder()
        context = self._finalize_rag_context(rag_result.context, rag_result.low_confidence)
        elapsed = int((time.perf_counter() - rag_start) * 1000)
        emit_progress(
            step="rag",
            status="done",
            elapsed_ms=elapsed,
            message=f"hits={len(rag_result.hits)} score={rag_result.top_score:.2f}",
        )
        log_rag_done(
            hits=len(rag_result.hits),
            low_confidence=rag_result.low_confidence,
            elapsed_ms=elapsed,
        )
        return context

    @staticmethod
    def _finalize_rag_context(context: str, low_confidence: bool) -> str:
        if not context:
            return _RAG_REFUSAL_HINT.strip()
        if low_confidence:
            return context + _RAG_REFUSAL_HINT
        return context
