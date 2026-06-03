from __future__ import annotations

from functools import lru_cache

from langgraph.graph import END, START, StateGraph

from .nodes.format_schedule import format_schedule_node
from .nodes.generate_answer import generate_answer_node
from .nodes.generate_summary import generate_summary_node
from .nodes.handle_general import handle_general_node
from .nodes.handle_irrelevant import handle_irrelevant_node
from .nodes.handle_not_found import handle_not_found_node
from .nodes.retrieve import retrieve_node
from .nodes.router import router_node
from .state import AgentState


# ── 조건부 엣지 함수 ─────────────────────────────────────────────────

def _route_after_router(state: AgentState) -> str:
    intent = state["intent"]
    if intent == "general":
        return "handle_general"
    if intent == "soma_unrelated":
        return "handle_irrelevant"
    return "retrieve_documents"  # soma_query / soma_summarize / schedule_link


def _route_after_retrieve(state: AgentState) -> str:
    if not state["retrieved_chunks"]:
        return "handle_not_found"
    intent = state["intent"]
    mapping = {
        "soma_query":     "generate_answer",
        "soma_summarize": "generate_summary",
        "schedule_link":  "format_schedule_link",
    }
    return mapping.get(intent, "generate_answer")


# ── 그래프 조립 ──────────────────────────────────────────────────────

def _build_graph() -> StateGraph:
    g = StateGraph(AgentState)

    g.add_node("router",              router_node)
    g.add_node("handle_general",      handle_general_node)
    g.add_node("handle_irrelevant",   handle_irrelevant_node)
    g.add_node("retrieve_documents",  retrieve_node)
    g.add_node("generate_answer",     generate_answer_node)
    g.add_node("generate_summary",    generate_summary_node)
    g.add_node("format_schedule_link", format_schedule_node)
    g.add_node("handle_not_found",    handle_not_found_node)

    g.add_edge(START, "router")

    g.add_conditional_edges(
        "router",
        _route_after_router,
        {
            "handle_general":    "handle_general",
            "handle_irrelevant": "handle_irrelevant",
            "retrieve_documents": "retrieve_documents",
        },
    )

    g.add_conditional_edges(
        "retrieve_documents",
        _route_after_retrieve,
        {
            "handle_not_found":    "handle_not_found",
            "generate_answer":     "generate_answer",
            "generate_summary":    "generate_summary",
            "format_schedule_link": "format_schedule_link",
        },
    )

    for terminal in (
        "handle_general",
        "handle_irrelevant",
        "handle_not_found",
        "generate_answer",
        "generate_summary",
        "format_schedule_link",
    ):
        g.add_edge(terminal, END)

    return g


@lru_cache(maxsize=1)
def get_graph():
    """컴파일된 그래프를 싱글톤으로 반환한다."""
    return _build_graph().compile()
