"""咨询编排：Multi-Agent + RAG + 报告持久化。"""

from app.dto.career import CareerProfile, CareerRecommendation
from app.dto.gaokao import GaokaoProfile, GaokaoRecommendation
from app.graphs.career_graph import run_career_advisory
from app.graphs.gaokao_graph import run_gaokao_advisory
from app.service.rag_service import RAGService
from app.service.report_service import ReportService


class AdvisoryService:
    def __init__(self, rag_service: RAGService, report_service: ReportService) -> None:
        self._rag = rag_service
        self._reports = report_service

    def advise_gaokao(self, user_id: str, profile: GaokaoProfile) -> GaokaoRecommendation:
        rag_context = self._rag.build_context_for_gaokao(profile.model_dump())
        result = run_gaokao_advisory(profile, rag_context=rag_context)
        report_id = self._reports.save_gaokao(user_id, profile, result)
        result.report_id = report_id
        return result

    def advise_career(self, user_id: str, profile: CareerProfile) -> CareerRecommendation:
        rag_context = self._rag.build_context_for_career(profile.model_dump())
        result = run_career_advisory(profile, rag_context=rag_context)
        report_id = self._reports.save_career(user_id, profile, result)
        result.report_id = report_id
        return result
