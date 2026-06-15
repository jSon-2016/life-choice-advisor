"""测评报告导入编排：解析 → 语义分块 → 结构化抽取 → 画像预填。"""

from __future__ import annotations

from app.config import REPORT_MAX_UPLOAD_MB
from app.dto.career import CareerProfile
from app.dto.gaokao import GaokaoProfile
from app.dto.report_import import PsychReportExtraction, ReportImportResponse
from app.service.report_chunker import format_chunks_markdown, semantic_chunk_with_overlap
from app.service.report_document_parser import extract_text_from_upload
from app.service.report_profile_extractor import extract_psych_profile


class ReportImportService:
    def parse_upload(
        self,
        *,
        filename: str,
        data: bytes,
        content_type: str | None,
        advisory_type: str,
    ) -> ReportImportResponse:
        if len(data) > REPORT_MAX_UPLOAD_MB * 1024 * 1024:
            raise ValueError(f"文件过大，最大 {REPORT_MAX_UPLOAD_MB}MB")

        raw_text, warnings = extract_text_from_upload(filename, data, content_type)
        chunks = semantic_chunk_with_overlap(raw_text)
        report_context = format_chunks_markdown(chunks)

        extraction, summary = extract_psych_profile(chunks)
        full_context = f"{report_context}\n\n## 结构化抽取摘要\n{summary}".strip()

        gaokao_profile: GaokaoProfile | None = None
        career_profile: CareerProfile | None = None
        missing: list[str] = []

        if advisory_type == "gaokao":
            gaokao_profile, missing = _build_gaokao_profile(extraction)
        elif advisory_type == "career":
            career_profile, missing = _build_career_profile(extraction)
        else:
            raise ValueError("advisory_type 须为 gaokao 或 career")

        return ReportImportResponse(
            filename=filename,
            report_context=full_context,
            structured_summary=summary,
            chunk_count=len(chunks),
            warnings=warnings,
            missing_fields=missing,
            gaokao_profile=gaokao_profile,
            career_profile=career_profile,
            extraction=extraction,
        )


def _build_gaokao_profile(ext: PsychReportExtraction) -> tuple[GaokaoProfile | None, list[str]]:
    missing: list[str] = []
    province = ext.province or "待补充"
    subject_track = ext.subject_track or "待补充"
    total_score = ext.total_score if ext.total_score is not None else 0

    if not ext.province:
        missing.append("province")
    if ext.total_score is None:
        missing.append("total_score")
    if not ext.subject_track:
        missing.append("subject_track")

    psych_notes = ext.psychological_summary or ""
    if ext.dimension_scores:
        dim_lines = [
            f"{d.dimension}: {d.score or '-'} 参考:{d.reference or '-'}"
            for d in ext.dimension_scores[:20]
        ]
        psych_notes = (psych_notes + "\n" + "\n".join(dim_lines)).strip()

    profile = GaokaoProfile(
        province=province,
        exam_year=2026,
        subject_track=subject_track,
        total_score=total_score,
        rank=ext.rank,
        preferred_regions=ext.preferred_regions,
        interests=ext.interests,
        personality_traits=ext.personality_traits,
        mbti=ext.mbti,
        psychological_notes=psych_notes or None,
        family_constraints=None,
        excluded_majors=[],
        extra_notes=f"已从测评报告导入：{ext.report_title or '心理测评'}",
    )
    return profile, missing


def _build_career_profile(ext: PsychReportExtraction) -> tuple[CareerProfile | None, list[str]]:
    missing: list[str] = []
    education = ext.education_level or "待补充"
    university = ext.university or "待补充"
    major = ext.major or "待补充"

    if not ext.education_level:
        missing.append("education_level")
    if not ext.university:
        missing.append("university")
    if not ext.major:
        missing.append("major")

    psych = ext.psychological_summary or ""
    if ext.dimension_scores:
        psych += "\n" + "\n".join(
            f"{d.dimension}: {d.score} ({d.reference})" for d in ext.dimension_scores[:20]
        )

    profile = CareerProfile(
        education_level=education,
        university=university,
        major=major,
        graduation_year=2026,
        skills=ext.skills,
        personality_traits=ext.personality_traits,
        mbti=ext.mbti,
        values=ext.values,
        psychological_assessment=psych.strip() or None,
        career_aptitude_scores=ext.aptitude_scores or None,
        preferred_cities=ext.preferred_cities,
        internship_experience=ext.internship_experience,
        project_experience=ext.project_experience,
        extra_notes=f"已从测评报告导入：{ext.report_title or '职业/心理测评'}",
    )
    return profile, missing
