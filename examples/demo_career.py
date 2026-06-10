"""职业选择 Multi-Agent 示例（命令行）。"""

import json

from dotenv import load_dotenv

load_dotenv()

from app.dto.career import CareerProfile
from app.graphs.career_graph import run_career_advisory

if __name__ == "__main__":
    profile = CareerProfile(
        education_level="本科",
        university="华南理工大学",
        major="软件工程",
        graduation_year=2026,
        gpa_level="良好",
        internship_experience=["某互联网公司 Java 后端实习 3 个月"],
        project_experience=["校园二手交易平台", "RAG 问答小项目"],
        skills=["Java", "Python", "MySQL", "Spring Boot"],
        personality_traits=["细致", "偏内向", "自驱力强"],
        mbti="ISTJ",
        values=["技术成长", "工作稳定", "合理薪资"],
        psychological_assessment="情绪较稳定，面对不确定性时会焦虑，偏好有明确目标的任务",
        career_aptitude_scores={
            "分析力": 88,
            "沟通力": 62,
            "执行力": 85,
            "创造力": 70,
            "领导力": 55,
        },
        preferred_cities=["广州", "深圳"],
        salary_expectation="应届 12-18K",
        work_life_balance="可接受适度加班，不希望 996",
        excluded_industries=["传统销售", "纯体力岗位"],
    )

    print("正在启动 5 位专家 Agent 协作分析，请稍候...\n")
    result = run_career_advisory(profile)
    print("=" * 60)
    print("【摘要】", result.summary)
    print("\n【推荐行业】", result.recommended_industries)
    print("【推荐岗位】", result.recommended_roles)
    print("\n【完整报告】\n", result.full_report)
    print("\n【结构化 JSON】")
    print(json.dumps(result.model_dump(exclude={"agent_insights", "full_report"}), ensure_ascii=False, indent=2))
