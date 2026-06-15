"""职业选择请求 / 响应模型。"""

from pydantic import BaseModel, Field

from app.dto.gaokao import AgentInsight


class CareerProfile(BaseModel):
    """毕业生 / 职场新人画像。"""

    name: str | None = Field(None, description="姓名（可选）")
    age: int | None = Field(None, ge=16, le=60)
    education_level: str = Field(..., description="学历：本科、硕士、博士等")
    university: str = Field(..., description="毕业院校")
    major: str = Field(..., description="所学专业")
    graduation_year: int | None = Field(None, description="毕业年份")
    gpa_level: str | None = Field(None, description="成绩水平：优秀/良好/一般")
    internship_experience: list[str] = Field(default_factory=list, description="实习经历摘要")
    project_experience: list[str] = Field(default_factory=list, description="项目经历")
    skills: list[str] = Field(default_factory=list, description="已掌握技能")
    personality_traits: list[str] = Field(default_factory=list, description="性格特点")
    mbti: str | None = Field(None, description="MBTI")
    values: list[str] = Field(
        default_factory=list,
        description="价值观：如稳定、高收入、创造性、社会影响力",
    )
    psychological_assessment: str | None = Field(
        None,
        description="心理素质测评摘要：情绪稳定、抗压、社交、决策风格等",
    )
    career_aptitude_scores: dict[str, int] | None = Field(
        None,
        description="职业能力测评得分，如 {'分析力': 85, '沟通力': 70, '执行力': 90}",
    )
    preferred_cities: list[str] = Field(default_factory=list, description="意向工作城市")
    salary_expectation: str | None = Field(None, description="薪资期望")
    work_life_balance: str | None = Field(None, description="对工作生活平衡的期望")
    excluded_industries: list[str] = Field(default_factory=list, description="不想进入的行业")
    extra_notes: str | None = Field(None, description="其他补充")


class CareerRecommendation(BaseModel):
    """职业选择综合建议。"""

    summary: str
    recommended_industries: list[str] = Field(default_factory=list, description="推荐行业及简要理由")
    recommended_roles: list[str] = Field(default_factory=list, description="推荐岗位类型")
    alternative_paths: list[str] = Field(default_factory=list, description="备选路径（如考研、考公、转行）")
    skill_gaps: list[str] = Field(default_factory=list, description="需补齐的能力短板")
    development_plan: list[str] = Field(default_factory=list, description="3-6 个月行动计划")
    risk_warnings: list[str] = Field(default_factory=list, description="风险与注意事项")
    agent_insights: list[AgentInsight] = Field(default_factory=list)
    full_report: str
    report_id: str | None = None


class CareerStructuredOutput(BaseModel):
    """协调员 Structured Output schema。"""

    summary: str = Field(..., description="200 字以内综合摘要")
    recommended_industries: list[str] = Field(default_factory=list, description="推荐行业及理由")
    recommended_roles: list[str] = Field(default_factory=list, description="推荐岗位类型")
    alternative_paths: list[str] = Field(default_factory=list, description="备选路径")
    skill_gaps: list[str] = Field(default_factory=list, description="能力短板")
    development_plan: list[str] = Field(default_factory=list, description="3-6 个月行动计划")
    risk_warnings: list[str] = Field(default_factory=list, description="风险提醒")
    full_report: str = Field(..., description="完整 Markdown 报告正文")
