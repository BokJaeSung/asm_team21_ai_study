from __future__ import annotations

import os
from typing import Any

import requests
import streamlit as st


API_URL = os.getenv("API_URL", "http://localhost:8000")

EXAMPLE_PROMPTS = [
    "이번 달 필수 제출 서류 뭐야?",
    "멘토링에서 포트폴리오 관련 내용 정리해줘",
    "기획 심의 언제야?",
    "오늘 점심 뭐 먹지?",
]


def init_state() -> None:
    if "session_id" not in st.session_state:
        st.session_state.session_id = None
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": "안녕하세요. SW마에스트로 부산 관련 질문을 도와드릴게요.",
                "intent": "일반 대화",
                "sources": [],
            }
        ]
    if "pending_prompt" not in st.session_state:
        st.session_state.pending_prompt = None


def create_session() -> str:
    response = requests.post(f"{API_URL}/sessions", timeout=10)
    response.raise_for_status()
    return response.json()["session_id"]


def ensure_session() -> str:
    if not st.session_state.session_id:
        st.session_state.session_id = create_session()
    return st.session_state.session_id


def send_chat(session_id: str, message: str) -> requests.Response:
    return requests.post(
        f"{API_URL}/chat/{session_id}",
        json={"message": message},
        timeout=30,
    )


def post_chat(message: str) -> dict[str, Any]:
    session_id = ensure_session()
    response = send_chat(session_id, message)
    try:
        response.raise_for_status()
    except requests.HTTPError:
        if response.status_code != 404:
            raise

        st.session_state.session_id = None
        response = send_chat(ensure_session(), message)
        response.raise_for_status()

    return response.json()


def render_message(message: dict[str, Any]) -> None:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message["role"] == "assistant":
            st.caption(f"의도: {message.get('intent', '-')}")

            sources = message.get("sources", [])
            if sources:
                for source in sources:
                    with st.container(border=True):
                        st.markdown(f"**{source['source']}**")
                        st.caption(source["preview"])


def submit_prompt(prompt: str) -> None:
    st.session_state.messages.append({"role": "user", "content": prompt})
    try:
        data = post_chat(prompt)
        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": data["answer"],
                "intent": data["intent"],
                "sources": data.get("sources", []),
                "followups": data.get("followups", []),
            }
        )
    except requests.RequestException:
        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": "API 서버에 연결할 수 없습니다. FastAPI 컨테이너가 실행 중인지 확인해 주세요.",
                "intent": "연결 오류",
                "sources": [],
            }
        )


st.set_page_config(
    page_title="SOMA 부산 정보 도우미",
    page_icon="S",
    layout="wide",
)

st.markdown(
    """
    <style>
    .stApp {
        background: #f7f8fa;
        color: #111827;
    }
    [data-testid="stSidebar"] {
        background: #ffffff;
        border-right: 1px solid #e5e7eb;
    }
    [data-testid="stSidebar"] * {
        color: #111827 !important;
    }
    .block-container {
        max-width: 980px;
        padding-top: 2rem;
        padding-bottom: 6rem;
    }
    h1, h2, h3, p, span, label, [data-testid="stMarkdownContainer"] {
        color: #111827 !important;
    }
    h1 {
        font-size: 2.15rem !important;
        line-height: 1.2 !important;
    }
    [data-testid="stChatMessage"] {
        background: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 8px;
        padding: 0.85rem 1rem;
    }
    [data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] * {
        color: #475569 !important;
    }
    div.stButton > button {
        border-radius: 8px;
        border-color: #cbd5e1;
        background: #ffffff;
        color: #111827;
        text-align: left;
        min-height: 2.75rem;
    }
    div.stButton > button:hover {
        border-color: #0f766e;
        color: #0f766e;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

init_state()

with st.sidebar:
    st.subheader("SOMA 부산")
    st.caption("FastAPI + Streamlit MVP")
    st.divider()
    st.metric("대화 턴", max(len(st.session_state.messages) - 1, 0))
    st.caption(f"API: {API_URL}")
    if st.button("대화 초기화", use_container_width=True):
        st.session_state.clear()
        st.rerun()

st.title("SOMA 부산 정보 도우미")
st.caption("SW마에스트로 부산 관련 질문을 의도별로 분류해 응답하는 채팅 UI")

with st.expander("예시 질문", expanded=False):
    for prompt in EXAMPLE_PROMPTS:
        if st.button(prompt, use_container_width=True):
            st.session_state.pending_prompt = prompt
            st.rerun()

for chat_message in st.session_state.messages:
    render_message(chat_message)

prompt = st.chat_input("소마 부산 관련 질문을 입력하세요")
pending_prompt = st.session_state.pending_prompt

if pending_prompt:
    st.session_state.pending_prompt = None
    submit_prompt(pending_prompt)
    st.rerun()

if prompt:
    submit_prompt(prompt)
    st.rerun()
