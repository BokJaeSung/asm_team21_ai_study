from __future__ import annotations

import json

from ..llm import chat
from ..prompts import ROUTER_PROMPT
from ..state import AgentState, INTENT_VALUES


def router_node(state: AgentState) -> dict:
    messages = [
        {"role": "system", "content": ROUTER_PROMPT},
        {"role": "user", "content": state["question"]},
    ]
    raw = chat(messages, temperature=0, json_mode=True)
    try:
        intent = json.loads(raw).get("intent", "general")
        if intent not in INTENT_VALUES:
            intent = "general"
    except Exception:
        intent = "general"

    return {"intent": intent, "execution_history": ["router"]}
