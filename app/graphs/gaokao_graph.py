"""高考志愿 Multi-Agent 工作流：并行专家 + 辩论 Supervisor + 总协调。"""

from typing import TypedDict

from langgraph.graph import END, StateGraph

from app.agents.prompts import (
    DEBATE_SUPERVISOR_PROMPT,
    GAOKAO_COORDINATOR_PROMPT,
    MAJOR_ADVISOR_PROMPT,
    PERSONALITY_ADVISOR_PROMPT,
    SCORE_ANALYST_PROMPT,
    SCHOOL_ADVISOR_PROMPT,
)
from app.agents.runner import run_agent, run_agents_parallel
from app.agents.tool_runner import run_agent_with_tools, run_structured_coordinator
from app.agents.cancel import check_cancelled
from app.dto.gaokao import AgentInsight, GaokaoProfile, GaokaoRecommendation, GaokaoStructuredOutput
from app.graphs.utils import append_structured_summary, build_prior_context
from app.graphs.context_helpers import imported_prefix, merge_context
from app.graphs.progress_helpers import with_node_progress
from app.tools.registry import get_gaokao_tools


class GaokaoState(TypedDict):
    """LangGraph 工作流状态（运行时是普通 dict，在各节点间传递并累积）。

    节点函数只需 return 本次新增的字段，LangGraph 会自动 merge 进 state。
    """

    profile: dict                  # 用户问卷（GaokaoProfile.model_dump()）
    rag_context: str               # RAG 检索到的院校/专业知识
    imported_report_context: str   # 导入的测评报告（语义分块）
    score_analysis: str            # 阶段1：分数定位分析师
    personality_analysis: str      # 阶段1：心理与兴趣顾问
    major_recommendations: str     # 阶段2：专业规划专家
    school_recommendations: str    # 阶段2：院校填报专家
    debate_transcript: str         # 阶段3：辩论 Supervisor
    final_report: str              # 阶段4：总协调员完整报告
    structured_output: dict        # 阶段4：Pydantic Structured Output（供 API 直接使用）


def _parallel_phase1(state: GaokaoState) -> dict:
    """阶段1：分数分析师 + 心理顾问并行（互不依赖，可同时调 LLM）。"""
    check_cancelled()
    profile = state["profile"]
    rag = merge_context(imported_prefix(state), state.get("rag_context", ""))

    def score_task():
        return run_agent(
            role="分数定位分析师",
            system_prompt=SCORE_ANALYST_PROMPT,
            user_payload=profile,
            prior_context=rag,
        )

    def personality_task():
        return run_agent(
            role="心理与兴趣顾问",
            system_prompt=PERSONALITY_ADVISOR_PROMPT,
            user_payload=profile,
            prior_context=rag,
        )

    results = run_agents_parallel([
        ("score_analysis", score_task),
        ("personality_analysis", personality_task),
    ])
    return results


def _parallel_phase2(state: GaokaoState) -> dict:
    """阶段2：专业专家 + 院校专家并行（需读取阶段1结论 + RAG）。"""
    check_cancelled()
    profile = state["profile"]
    # 把前序专家输出拼成 prior_context，供 LLM 参考
    prior = build_prior_context([
        ("分数定位分析", state["score_analysis"]),
        ("心理与兴趣分析", state["personality_analysis"]),
    ])
    # RAG 知识库放在最前面，保证事实性信息优先
    prior = merge_context(imported_prefix(state), state.get("rag_context", ""), prior)

    gaokao_tools = get_gaokao_tools()

    def major_task():
        return run_agent_with_tools(
            role="专业规划专家",
            system_prompt=MAJOR_ADVISOR_PROMPT,
            user_payload=profile,
            prior_context=prior,
            tools=gaokao_tools,
        )

    def school_task():
        return run_agent_with_tools(
            role="院校填报专家",
            system_prompt=SCHOOL_ADVISOR_PROMPT,
            user_payload=profile,
            prior_context=prior,
            tools=gaokao_tools,
        )

    results = run_agents_parallel([
        ("major_recommendations", major_task),
        ("school_recommendations", school_task),
    ])
    return results


def _debate_supervisor(state: GaokaoState) -> dict:
    """阶段3：Supervisor 串行，识别 4 位专家的分歧并协调（temperature 略高）。"""
    check_cancelled()
    prior = build_prior_context([
        ("分数定位", state["score_analysis"]),
        ("心理兴趣", state["personality_analysis"]),
        ("专业建议", state["major_recommendations"]),
        ("院校建议", state["school_recommendations"]),
    ])
    content = run_agent(
        role="辩论主持人 Supervisor",
        system_prompt=DEBATE_SUPERVISOR_PROMPT,
        user_payload=state["profile"],
        prior_context=prior,
        temperature=0.4,
    )
    return {"debate_transcript": content}


def _coordinator(state: GaokaoState) -> dict:
    """阶段4：总协调员 Structured Output，消除 JSON 解析不稳定。"""
    check_cancelled()
    prior = build_prior_context([
        ("分数定位", state["score_analysis"]),
        ("心理兴趣", state["personality_analysis"]),
        ("专业建议", state["major_recommendations"]),
        ("院校建议", state["school_recommendations"]),
        ("辩论结论", state["debate_transcript"]),
    ])
    rag = merge_context(imported_prefix(state), state.get("rag_context", ""))
    if rag:
        prior = merge_context(rag, prior)
    structured = run_structured_coordinator(
        role="志愿规划总协调员",
        system_prompt=GAOKAO_COORDINATOR_PROMPT,
        user_payload=state["profile"],
        prior_context=prior,
        schema=GaokaoStructuredOutput,
        temperature=0.1,
    )
    content = append_structured_summary(structured.full_report, structured.model_dump())
    return {"final_report": content, "structured_output": structured.model_dump()}


def build_gaokao_graph():
    """构建并编译工作流：phase1 → phase2 → supervisor → coordinator → END。"""
    graph = StateGraph(GaokaoState)
    graph.add_node("parallel_phase1", with_node_progress("parallel_phase1", _parallel_phase1))
    graph.add_node("parallel_phase2", with_node_progress("parallel_phase2", _parallel_phase2))
    graph.add_node("debate_supervisor", with_node_progress("debate_supervisor", _debate_supervisor))
    graph.add_node("coordinator", with_node_progress("coordinator", _coordinator))

    graph.set_entry_point("parallel_phase1")
    graph.add_edge("parallel_phase1", "parallel_phase2")
    graph.add_edge("parallel_phase2", "debate_supervisor")
    graph.add_edge("debate_supervisor", "coordinator")
    graph.add_edge("coordinator", END)
    return graph.compile()


_gaokao_graph = None  # 懒加载单例，避免每次请求重复 compile


def get_gaokao_graph():
    global _gaokao_graph
    if _gaokao_graph is None:
        _gaokao_graph = build_gaokao_graph()
    return _gaokao_graph


def run_gaokao_advisory(
    profile: GaokaoProfile,
    *,
    rag_context: str = "",
    imported_report_context: str = "",
) -> GaokaoRecommendation:
    """对外入口：启动 LangGraph → Structured Output → 封装 GaokaoRecommendation。"""
    check_cancelled()
    graph = get_gaokao_graph()
    result = graph.invoke({
        "profile": profile.model_dump(),
        "rag_context": rag_context,
        "imported_report_context": imported_report_context,
    })

    parsed = result.get("structured_output") or {}
    insights = [
        AgentInsight(agent="score_analyst", role="分数定位分析师", content=result["score_analysis"]),
        AgentInsight(agent="personality_advisor", role="心理与兴趣顾问", content=result["personality_analysis"]),
        AgentInsight(agent="major_advisor", role="专业规划专家", content=result["major_recommendations"]),
        AgentInsight(agent="school_advisor", role="院校填报专家", content=result["school_recommendations"]),
        AgentInsight(agent="debate_supervisor", role="辩论主持人", content=result["debate_transcript"]),
        AgentInsight(agent="coordinator", role="志愿总协调员", content=result["final_report"]),
    ]

    return GaokaoRecommendation(
        summary=parsed.get("summary", "请查看完整报告。"),
        rush_schools=parsed.get("rush_schools", []),
        stable_schools=parsed.get("stable_schools", []),
        safe_schools=parsed.get("safe_schools", []),
        recommended_majors=parsed.get("recommended_majors", []),
        avoid_majors=parsed.get("avoid_majors", []),
        action_plan=parsed.get("action_plan", []),
        risk_warnings=parsed.get("risk_warnings", []),
        agent_insights=insights,
        full_report=result["final_report"],
    )
