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
from app.dto.gaokao import AgentInsight, GaokaoProfile, GaokaoRecommendation
from app.graphs.utils import build_prior_context, extract_json_block


class GaokaoState(TypedDict):
    profile: dict
    rag_context: str
    score_analysis: str
    personality_analysis: str
    major_recommendations: str
    school_recommendations: str
    debate_transcript: str
    final_report: str


def _parallel_phase1(state: GaokaoState) -> dict:
    profile = state["profile"]
    rag = state.get("rag_context", "")

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
    profile = state["profile"]
    prior = build_prior_context([
        ("分数定位分析", state["score_analysis"]),
        ("心理与兴趣分析", state["personality_analysis"]),
    ])
    prior = f"{state.get('rag_context', '')}\n\n{prior}".strip()

    def major_task():
        return run_agent(
            role="专业规划专家",
            system_prompt=MAJOR_ADVISOR_PROMPT,
            user_payload=profile,
            prior_context=prior,
        )

    def school_task():
        return run_agent(
            role="院校填报专家",
            system_prompt=SCHOOL_ADVISOR_PROMPT,
            user_payload=profile,
            prior_context=prior,
        )

    results = run_agents_parallel([
        ("major_recommendations", major_task),
        ("school_recommendations", school_task),
    ])
    return results


def _debate_supervisor(state: GaokaoState) -> dict:
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
    prior = build_prior_context([
        ("分数定位", state["score_analysis"]),
        ("心理兴趣", state["personality_analysis"]),
        ("专业建议", state["major_recommendations"]),
        ("院校建议", state["school_recommendations"]),
        ("辩论结论", state["debate_transcript"]),
    ])
    rag = state.get("rag_context", "")
    if rag:
        prior = f"{rag}\n\n{prior}"
    content = run_agent(
        role="志愿规划总协调员",
        system_prompt=GAOKAO_COORDINATOR_PROMPT,
        user_payload=state["profile"],
        prior_context=prior,
        temperature=0.2,
    )
    return {"final_report": content}


def build_gaokao_graph():
    graph = StateGraph(GaokaoState)
    graph.add_node("parallel_phase1", _parallel_phase1)
    graph.add_node("parallel_phase2", _parallel_phase2)
    graph.add_node("debate_supervisor", _debate_supervisor)
    graph.add_node("coordinator", _coordinator)

    graph.set_entry_point("parallel_phase1")
    graph.add_edge("parallel_phase1", "parallel_phase2")
    graph.add_edge("parallel_phase2", "debate_supervisor")
    graph.add_edge("debate_supervisor", "coordinator")
    graph.add_edge("coordinator", END)
    return graph.compile()


_gaokao_graph = None


def get_gaokao_graph():
    global _gaokao_graph
    if _gaokao_graph is None:
        _gaokao_graph = build_gaokao_graph()
    return _gaokao_graph


def run_gaokao_advisory(profile: GaokaoProfile, *, rag_context: str = "") -> GaokaoRecommendation:
    graph = get_gaokao_graph()
    result = graph.invoke({"profile": profile.model_dump(), "rag_context": rag_context})

    parsed = extract_json_block(result["final_report"])
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
