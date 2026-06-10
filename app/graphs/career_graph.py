"""职业选择 Multi-Agent 工作流：并行专家 + 辩论 Supervisor + 总协调。"""

from typing import TypedDict

from langgraph.graph import END, StateGraph

from app.agents.prompts import (
    APTITUDE_ANALYST_PROMPT,
    CAREER_COORDINATOR_PROMPT,
    CAREER_PSYCHOLOGY_PROMPT,
    DEBATE_SUPERVISOR_PROMPT,
    INDUSTRY_ADVISOR_PROMPT,
    ROLE_ADVISOR_PROMPT,
)
from app.agents.runner import run_agent, run_agents_parallel
from app.dto.career import CareerProfile, CareerRecommendation
from app.dto.gaokao import AgentInsight
from app.graphs.utils import build_prior_context, extract_json_block


class CareerState(TypedDict):
    profile: dict
    rag_context: str
    aptitude_analysis: str
    psychology_analysis: str
    industry_analysis: str
    role_analysis: str
    debate_transcript: str
    final_report: str


def _parallel_phase1(state: CareerState) -> dict:
    profile = state["profile"]
    rag = state.get("rag_context", "")

    def aptitude_task():
        return run_agent(
            role="职业能力测评师",
            system_prompt=APTITUDE_ANALYST_PROMPT,
            user_payload=profile,
            prior_context=rag,
        )

    def psychology_task():
        return run_agent(
            role="职场心理顾问",
            system_prompt=CAREER_PSYCHOLOGY_PROMPT,
            user_payload=profile,
            prior_context=rag,
        )

    return run_agents_parallel([
        ("aptitude_analysis", aptitude_task),
        ("psychology_analysis", psychology_task),
    ])


def _parallel_phase2(state: CareerState) -> dict:
    profile = state["profile"]
    prior = build_prior_context([
        ("能力测评", state["aptitude_analysis"]),
        ("职场心理", state["psychology_analysis"]),
    ])
    prior = f"{state.get('rag_context', '')}\n\n{prior}".strip()

    def industry_task():
        return run_agent(
            role="行业趋势分析师",
            system_prompt=INDUSTRY_ADVISOR_PROMPT,
            user_payload=profile,
            prior_context=prior,
        )

    def role_task():
        return run_agent(
            role="岗位路径规划师",
            system_prompt=ROLE_ADVISOR_PROMPT,
            user_payload=profile,
            prior_context=prior,
        )

    return run_agents_parallel([
        ("industry_analysis", industry_task),
        ("role_analysis", role_task),
    ])


def _debate_supervisor(state: CareerState) -> dict:
    prior = build_prior_context([
        ("能力测评", state["aptitude_analysis"]),
        ("职场心理", state["psychology_analysis"]),
        ("行业分析", state["industry_analysis"]),
        ("岗位建议", state["role_analysis"]),
    ])
    content = run_agent(
        role="辩论主持人 Supervisor",
        system_prompt=DEBATE_SUPERVISOR_PROMPT,
        user_payload=state["profile"],
        prior_context=prior,
        temperature=0.4,
    )
    return {"debate_transcript": content}


def _coordinator(state: CareerState) -> dict:
    prior = build_prior_context([
        ("能力测评", state["aptitude_analysis"]),
        ("职场心理", state["psychology_analysis"]),
        ("行业分析", state["industry_analysis"]),
        ("岗位建议", state["role_analysis"]),
        ("辩论结论", state["debate_transcript"]),
    ])
    rag = state.get("rag_context", "")
    if rag:
        prior = f"{rag}\n\n{prior}"
    content = run_agent(
        role="生涯规划总协调员",
        system_prompt=CAREER_COORDINATOR_PROMPT,
        user_payload=state["profile"],
        prior_context=prior,
        temperature=0.2,
    )
    return {"final_report": content}


def build_career_graph():
    graph = StateGraph(CareerState)
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


_career_graph = None


def get_career_graph():
    global _career_graph
    if _career_graph is None:
        _career_graph = build_career_graph()
    return _career_graph


def run_career_advisory(profile: CareerProfile, *, rag_context: str = "") -> CareerRecommendation:
    graph = get_career_graph()
    result = graph.invoke({"profile": profile.model_dump(), "rag_context": rag_context})

    parsed = extract_json_block(result["final_report"])
    insights = [
        AgentInsight(agent="aptitude_analyst", role="职业能力测评师", content=result["aptitude_analysis"]),
        AgentInsight(agent="psychology_advisor", role="职场心理顾问", content=result["psychology_analysis"]),
        AgentInsight(agent="industry_advisor", role="行业趋势分析师", content=result["industry_analysis"]),
        AgentInsight(agent="role_advisor", role="岗位路径规划师", content=result["role_analysis"]),
        AgentInsight(agent="debate_supervisor", role="辩论主持人", content=result["debate_transcript"]),
        AgentInsight(agent="coordinator", role="生涯总协调员", content=result["final_report"]),
    ]

    return CareerRecommendation(
        summary=parsed.get("summary", "请查看完整报告。"),
        recommended_industries=parsed.get("recommended_industries", []),
        recommended_roles=parsed.get("recommended_roles", []),
        alternative_paths=parsed.get("alternative_paths", []),
        skill_gaps=parsed.get("skill_gaps", []),
        development_plan=parsed.get("development_plan", []),
        risk_warnings=parsed.get("risk_warnings", []),
        agent_insights=insights,
        full_report=result["final_report"],
    )
