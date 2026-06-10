"""高考志愿 Multi-Agent 示例（命令行）。"""

import json

from dotenv import load_dotenv

load_dotenv()

from app.dto.gaokao import GaokaoProfile
from app.graphs.gaokao_graph import run_gaokao_advisory

if __name__ == "__main__":
    profile = GaokaoProfile(
        province="广东",
        exam_year=2026,
        subject_track="物理类",
        total_score=612,
        rank=8500,
        preferred_regions=["广州", "深圳", "上海"],
        interests=["编程", "数学", "解决问题"],
        personality_traits=["逻辑清晰", "偏内向", "喜欢深度思考"],
        mbti="INTJ",
        psychological_notes="抗压能力中等，对新环境适应较快，不太喜欢频繁社交",
        family_constraints="希望留在华南，学费可接受公办本科",
        excluded_majors=["医学", "土木"],
    )

    print("正在启动 5 位专家 Agent 协作分析，请稍候...\n")
    result = run_gaokao_advisory(profile)
    print("=" * 60)
    print("【摘要】", result.summary)
    print("\n【冲】", result.rush_schools)
    print("【稳】", result.stable_schools)
    print("【保】", result.safe_schools)
    print("\n【完整报告】\n", result.full_report)
    print("\n【结构化 JSON】")
    print(json.dumps(result.model_dump(exclude={"agent_insights", "full_report"}), ensure_ascii=False, indent=2))
