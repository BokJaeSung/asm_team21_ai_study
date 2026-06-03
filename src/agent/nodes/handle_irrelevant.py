from __future__ import annotations

from ..state import AgentState

_MSG = "소마(SW마에스트로) 관련 질문만 답변할 수 있어요. 다른 질문이 있으신가요? 😊"


def handle_irrelevant_node(state: AgentState) -> dict:
    return {"generated_answer": _MSG, "execution_history": ["handle_irrelevant"]}
