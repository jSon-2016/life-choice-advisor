"""高考志愿填报请求 / 响应模型。"""

from pydantic import BaseModel, Field


class GaokaoProfile(BaseModel):
    """考生画像。"""

    province: str = Field(..., description="高考省份，如：广东")
    exam_year: int = Field(..., ge=2020, le=2030, description="高考年份")
    subject_track: str = Field(..., description="科类/选科，如：物理类、历史类、理科、文科")
    total_score: int = Field(..., ge=0, le=900, description="高考总分")
    rank: int | None = Field(None, ge=1, description="全省位次（有则填）")
    preferred_regions: list[str] = Field(default_factory=list, description="意向地区，如：北京、长三角")
    interests: list[str] = Field(default_factory=list, description="兴趣方向，如：编程、生物、设计")
    personality_traits: list[str] = Field(
        default_factory=list,
        description="性格特点，如：内向、细致、喜欢独立工作",
    )
    mbti: str | None = Field(None, description="MBTI 类型，如 INTP")
    psychological_notes: str | None = Field(
        None,
        description="心理素质说明：抗压、社交、适应新环境、对失败的承受力等",
    )
    family_constraints: str | None = Field(
        None,
        description="家庭约束：经济、地域、父母期望等",
    )
    excluded_majors: list[str] = Field(default_factory=list, description="明确不想学的专业")
    extra_notes: str | None = Field(None, description="其他补充信息")


class AgentInsight(BaseModel):
    """单个专家 Agent 的输出摘要。"""

    agent: str
    role: str
    content: str


class GaokaoRecommendation(BaseModel):
    """高考志愿综合建议。"""

    summary: str = Field(..., description="200 字以内 Executive Summary")
    rush_schools: list[str] = Field(default_factory=list, description="冲：略高风险院校+专业")
    stable_schools: list[str] = Field(default_factory=list, description="稳：匹配度高的院校+专业")
    safe_schools: list[str] = Field(default_factory=list, description="保：录取把握大的院校+专业")
    recommended_majors: list[str] = Field(default_factory=list, description="推荐专业方向（含理由关键词）")
    avoid_majors: list[str] = Field(default_factory=list, description="需谨慎或不建议的方向")
    action_plan: list[str] = Field(default_factory=list, description="接下来 3-5 步行动建议")
    risk_warnings: list[str] = Field(default_factory=list, description="风险提醒")
    agent_insights: list[AgentInsight] = Field(default_factory=list, description="各专家详细分析")
    full_report: str = Field(..., description="协调员整合后的完整 Markdown 报告")
    report_id: str | None = Field(None, description="保存到 MySQL 后的报告 ID")
