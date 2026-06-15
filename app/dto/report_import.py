"""测评报告导入相关 DTO。"""

from pydantic import BaseModel, Field

from app.dto.career import CareerProfile
from app.dto.gaokao import GaokaoProfile


class DimensionScore(BaseModel):
    """测评维度条目（含参考标准）。"""

    dimension: str = Field(..., description="维度名称")
    score: str | None = Field(None, description="得分或等级")
    reference: str | None = Field(None, description="参考标准/常模")
    interpretation: str | None = Field(None, description="报告中的解读")


class PsychReportExtraction(BaseModel):
    """从测评报告中 LLM 抽取的结构化信息。"""

    report_title: str | None = None
    mbti: str | None = None
    personality_traits: list[str] = Field(default_factory=list)
    interests: list[str] = Field(default_factory=list)
    values: list[str] = Field(default_factory=list)
    psychological_summary: str | None = None
    aptitude_scores: dict[str, int] = Field(default_factory=dict)
    dimension_scores: list[DimensionScore] = Field(default_factory=list)
    education_level: str | None = None
    university: str | None = None
    major: str | None = None
    province: str | None = None
    subject_track: str | None = None
    total_score: int | None = None
    rank: int | None = None
    preferred_regions: list[str] = Field(default_factory=list)
    preferred_cities: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    internship_experience: list[str] = Field(default_factory=list)
    project_experience: list[str] = Field(default_factory=list)


class ReportImportResponse(BaseModel):
    """报告解析结果。"""

    filename: str
    report_context: str = Field(..., description="重叠分块后的 Markdown，供 Agent 注入")
    structured_summary: str = Field(..., description="测评摘要")
    chunk_count: int
    warnings: list[str] = Field(default_factory=list)
    missing_fields: list[str] = Field(default_factory=list, description="仍需用户补充的字段")
    gaokao_profile: GaokaoProfile | None = None
    career_profile: CareerProfile | None = None
    extraction: PsychReportExtraction | None = None


class GaokaoAdviseRequest(BaseModel):
    """高考咨询请求（支持导入报告上下文）。"""

    profile: GaokaoProfile
    imported_report_context: str | None = Field(
        None,
        description="导入的心理/测评报告解析上下文（重叠分块 Markdown）",
    )


class CareerAdviseRequest(BaseModel):
    """职业咨询请求（支持导入报告上下文）。"""

    profile: CareerProfile
    imported_report_context: str | None = None
