from __future__ import annotations

import json

from ..llm import chat
from ..prompts import FOLLOW_UP_QUESTIONS_PROMPT
from ..state import AgentState


_ANSWER_NODES = {"generate_answer", "generate_summary", "format_schedule_link"}


def _coerce_questions(raw: str) -> list[str]:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return []

    questions = data.get("follow_up_questions", [])
    if not isinstance(questions, list):
        return []

    cleaned: list[str] = []
    for question in questions:
        if isinstance(question, str) and question.strip():
            cleaned.append(question.strip())
    return cleaned[:3]


def generate_follow_up_questions_node(state: AgentState) -> dict:
    answer = state.get("generated_answer", "").strip()
    history = state.get("execution_history", [])
    if not answer or not history or history[-1] not in _ANSWER_NODES:
        return {"follow_up_questions": [], "execution_history": ["generate_follow_up_questions"]}

    messages = [
        {"role": "system", "content": FOLLOW_UP_QUESTIONS_PROMPT},
        {
            "role": "user",
            "content": (
                f"[사용자 질문]\n{state['question']}\n\n"
                f"[에이전트 답변]\n{answer}"
            ),
        },
    ]
    raw = chat(messages, temperature=0.2, json_mode=True)
    return {
        "follow_up_questions": _coerce_questions(raw),
        "execution_history": ["generate_follow_up_questions"],
    }
