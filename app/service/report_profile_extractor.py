"""从测评报告分块中 LLM 抽取结构化画像。"""

from __future__ import annotations

import json

from langchain_core.messages import HumanMessage, SystemMessage

from app.dto.report_import import PsychReportExtraction
from app.llm import create_llm
from app.observability.progress import get_llm_callbacks
from app.service.report_chunker import ReportChunk, format_chunks_markdown

EXTRACT_PROMPT = """你是心理/职业测评报告解析专家。
请从用户上传的测评报告片段中抽取结构化信息：
- 保留各维度得分及参考标准/常模（不得编造）
- 提取 MBTI、性格、兴趣、价值观、能力得分
- 若报告含高考分数/省份/专业/院校也一并提取
- 未出现的字段留空，不要猜测"""


def extract_psych_profile(chunks: list[ReportChunk]) -> tuple[PsychReportExtraction, str]:
    """Map-Reduce：分块抽取 + 汇总合并。"""
    if not chunks:
        return PsychReportExtraction(psychological_summary=""), ""

    partials: list[PsychReportExtraction] = []
    config = {"callbacks": get_llm_callbacks()} if get_llm_callbacks() else None
    llm = create_llm(temperature=0.1).with_structured_output(PsychReportExtraction)

    for chunk in chunks[:12]:
        messages = [
            SystemMessage(content=EXTRACT_PROMPT),
            HumanMessage(
                content=(
                    f"报告片段 [{chunk.index}]（{chunk.section_hint}）：\n\n"
                    f"{chunk.content}\n\n"
                    "请抽取本片段中出现的结构化字段。"
                )
            ),
        ]
        try:
            partial = llm.invoke(messages, config=config)
            if isinstance(partial, PsychReportExtraction):
                partials.append(partial)
            else:
                partials.append(PsychReportExtraction.model_validate(partial))
        except Exception:
            continue

    if not partials:
        summary = chunks[0].content[:500]
        return PsychReportExtraction(psychological_summary=summary), summary

    merged = _merge_extractions(partials)
    summary = _build_summary(merged)
    return merged, summary


def _merge_extractions(items: list[PsychReportExtraction]) -> PsychReportExtraction:
    def first_str(attr: str) -> str | None:
        for it in items:
            val = getattr(it, attr)
            if val:
                return val
        return None

    def merge_list(attr: str) -> list[str]:
        seen: set[str] = set()
        out: list[str] = []
        for it in items:
            for v in getattr(it, attr, []) or []:
                if v and v not in seen:
                    seen.add(v)
                    out.append(v)
        return out

    scores: dict[str, int] = {}
    for it in items:
        scores.update(it.aptitude_scores or {})

    dimensions = []
    seen_dim: set[str] = set()
    for it in items:
        for d in it.dimension_scores or []:
            key = d.dimension
            if key and key not in seen_dim:
                seen_dim.add(key)
                dimensions.append(d)

    summaries = [it.psychological_summary for it in items if it.psychological_summary]
    psych = "\n".join(summaries[:3]) if summaries else None

    return PsychReportExtraction(
        report_title=first_str("report_title"),
        mbti=first_str("mbti"),
        personality_traits=merge_list("personality_traits"),
        interests=merge_list("interests"),
        values=merge_list("values"),
        psychological_summary=psych,
        aptitude_scores=scores,
        dimension_scores=dimensions,
        education_level=first_str("education_level"),
        university=first_str("university"),
        major=first_str("major"),
        province=first_str("province"),
        subject_track=first_str("subject_track"),
        total_score=next((it.total_score for it in items if it.total_score), None),
        rank=next((it.rank for it in items if it.rank), None),
        preferred_regions=merge_list("preferred_regions"),
        preferred_cities=merge_list("preferred_cities"),
        skills=merge_list("skills"),
        internship_experience=merge_list("internship_experience"),
        project_experience=merge_list("project_experience"),
    )


def _build_summary(extraction: PsychReportExtraction) -> str:
    lines = []
    if extraction.report_title:
        lines.append(f"**报告名称**：{extraction.report_title}")
    if extraction.mbti:
        lines.append(f"**MBTI**：{extraction.mbti}")
    if extraction.personality_traits:
        lines.append(f"**性格特点**：{', '.join(extraction.personality_traits)}")
    if extraction.aptitude_scores:
        lines.append(f"**能力得分**：{json.dumps(extraction.aptitude_scores, ensure_ascii=False)}")
    if extraction.dimension_scores:
        lines.append("**维度得分（含参考标准）**：")
        for d in extraction.dimension_scores[:15]:
            ref = f"（参考：{d.reference}）" if d.reference else ""
            score = d.score or "-"
            lines.append(f"- {d.dimension}: {score}{ref}")
    if extraction.psychological_summary:
        lines.append(f"**综合解读**：{extraction.psychological_summary}")
    return "\n".join(lines) if lines else "已从测评报告提取信息，详见各 Agent 分析。"
