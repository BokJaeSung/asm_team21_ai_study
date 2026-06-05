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

CSS = """
<style>
/* ── 전체 배경 ── */
.stApp {
    background: linear-gradient(160deg, #e8f4fd 0%, #dbeafe 100%);
}

/* ── 사이드바 ── */
[data-testid="stSidebar"] {
    background: #ffffff;
    border-right: 1px solid #bfdbfe;
}
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] div {
    color: #1e3a5f !important;
}
[data-testid="stSidebar"] hr { border-color: #bfdbfe !important; }
[data-testid="stSidebar"] [data-testid="stMetricValue"] {
    color: #2563eb !important;
    font-size: 1.8rem !important;
    font-weight: 700 !important;
}
[data-testid="stSidebarUserContent"] .stButton button {
    background: #eff6ff;
    border: 1px solid #bfdbfe;
    color: #1e40af !important;
    border-radius: 10px;
    font-size: 0.82rem;
    text-align: left;
    transition: all 0.15s;
}
[data-testid="stSidebarUserContent"] .stButton button:hover {
    background: #2563eb;
    border-color: #2563eb;
    color: #ffffff !important;
}

/* ── 메인 영역 ── */
.block-container {
    max-width: 800px;
    padding-top: 0 !important;
    padding-bottom: 5rem;
    padding-left: 1.5rem;
    padding-right: 1.5rem;
}

/* ── 상단 헤더 바 ── */
.chat-topbar {
    position: sticky;
    top: 0;
    z-index: 100;
    background: #ffffff;
    border-bottom: 1px solid #bfdbfe;
    padding: 0.9rem 1.2rem;
    margin: -1.5rem -1.5rem 1.5rem -1.5rem;
    display: flex;
    align-items: center;
    gap: 0.75rem;
    box-shadow: 0 2px 8px rgba(37,99,235,0.08);
}
.chat-topbar-avatar {
    width: 40px;
    height: 40px;
    border-radius: 50%;
    background: linear-gradient(135deg, #2563eb, #38bdf8);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.2rem;
    flex-shrink: 0;
}
.chat-topbar-title {
    font-size: 1rem;
    font-weight: 700;
    color: #1e3a5f;
    line-height: 1.2;
}
.chat-topbar-sub {
    font-size: 0.72rem;
    color: #60a5fa;
}
.online-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #22c55e;
    display: inline-block;
    margin-right: 4px;
}

/* ── 말풍선 래퍼 ── */
.msg-row {
    display: flex;
    align-items: flex-end;
    gap: 0.5rem;
    margin-bottom: 0.75rem;
}
.msg-row.user { flex-direction: row-reverse; }

/* ── 아바타 ── */
.msg-avatar {
    width: 34px;
    height: 34px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1rem;
    flex-shrink: 0;
    box-shadow: 0 1px 4px rgba(0,0,0,0.1);
}
.msg-avatar.bot  { background: linear-gradient(135deg, #2563eb, #38bdf8); }
.msg-avatar.user { background: #e0f2fe; }

/* ── 말풍선 감싸기 ── */
.msg-body {
    display: flex;
    flex-direction: column;
    max-width: 68%;
    gap: 0.2rem;
}
.msg-row.user .msg-body { align-items: flex-end; }

.msg-name {
    font-size: 0.7rem;
    font-weight: 600;
    color: #3b82f6;
    margin-left: 0.15rem;
}

/* ── 말풍선 ── */
.bubble {
    padding: 0.65rem 1rem;
    border-radius: 18px;
    font-size: 0.875rem;
    line-height: 1.6;
    word-break: break-word;
    white-space: pre-wrap;
}
.bubble.bot {
    background: #ffffff;
    color: #1e293b;
    border-top-left-radius: 4px;
    box-shadow: 0 2px 8px rgba(37,99,235,0.08);
}
.bubble.user {
    background: linear-gradient(135deg, #2563eb, #3b82f6);
    color: #ffffff;
    border-top-right-radius: 4px;
    box-shadow: 0 2px 8px rgba(37,99,235,0.25);
}

/* ── 출처 카드 ── */
.source-wrap { margin-top: 0.4rem; display: flex; flex-direction: column; gap: 0.3rem; }
.source-card {
    background: #f0f9ff;
    border: 1px solid #bae6fd;
    border-left: 3px solid #38bdf8;
    border-radius: 0 10px 10px 0;
    padding: 0.45rem 0.75rem;
    font-size: 0.78rem;
    color: #0c4a6e;
}
.source-card b { display: block; color: #0369a1; margin-bottom: 0.1rem; }

/* ── 의도 뱃지 ── */
.intent-badge {
    display: inline-block;
    background: #dbeafe;
    color: #1d4ed8;
    font-size: 0.67rem;
    font-weight: 600;
    border-radius: 20px;
    padding: 0.1rem 0.55rem;
    margin-top: 0.3rem;
}

/* ── 입력창 ── */
[data-testid="stChatInputContainer"] > div {
    background: #ffffff !important;
    border: 1.5px solid #93c5fd !important;
    border-radius: 26px !important;
    box-shadow: 0 2px 12px rgba(37,99,235,0.1) !important;
    padding: 0.2rem 0.5rem !important;
}
[data-testid="stChatInputContainer"] > div:focus-within {
    border-color: #2563eb !important;
    box-shadow: 0 0 0 3px rgba(37,99,235,0.15) !important;
}
[data-testid="stChatInput"] textarea {
    color: #1e293b !important;
    font-size: 0.9rem !important;
}
</style>
"""


def init_state() -> None:
    if "session_id" not in st.session_state:
        st.session_state.session_id = None
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": "안녕하세요! 👋\nSW마에스트로 부산 관련 질문을 도와드릴게요.\n궁금한 것을 편하게 물어보세요 😊",
                "intent": "일반 대화",
                "sources": [],
            }
        ]
    if "pending_prompt" not in st.session_state:
        st.session_state.pending_prompt = None
    if "waiting" not in st.session_state:
        st.session_state.waiting = False


def create_session() -> str:
    r = requests.post(f"{API_URL}/sessions", timeout=10)
    r.raise_for_status()
    return r.json()["session_id"]


def ensure_session() -> str:
    if not st.session_state.session_id:
        st.session_state.session_id = create_session()
    return st.session_state.session_id


def send_chat(session_id: str, message: str) -> requests.Response:
    return requests.post(f"{API_URL}/chat/{session_id}", json={"message": message}, timeout=30)


def post_chat(message: str) -> dict[str, Any]:
    sid = ensure_session()
    r = send_chat(sid, message)
    try:
        r.raise_for_status()
    except requests.HTTPError:
        if r.status_code != 404:
            raise
        st.session_state.session_id = None
        r = send_chat(ensure_session(), message)
        r.raise_for_status()
    return r.json()


def _escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def render_message(message: dict[str, Any]) -> None:
    role = message["role"]
    content = _escape(message["content"])
    sources = message.get("sources", [])
    intent = message.get("intent", "")

    if role == "user":
        st.markdown(
            f"""
            <div class="msg-row user">
                <div class="msg-body">
                    <div class="bubble user">{content}</div>
                </div>
                <div class="msg-avatar user">🙋</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        source_html = ""
        if sources:
            cards = "".join(
                f'<div class="source-card"><b>📎 {_escape(s["source"])}</b>{_escape(s.get("preview", ""))}</div>'
                for s in sources
            )
            source_html = f'<div class="source-wrap">{cards}</div>'

        badge = f'<span class="intent-badge">#{_escape(intent)}</span>' if intent else ""

        st.markdown(
            f"""
            <div class="msg-row">
                <div class="msg-avatar bot">🤖</div>
                <div class="msg-body">
                    <span class="msg-name">SOMA 도우미</span>
                    <div class="bubble bot">{content}</div>
                    {source_html}
                    {badge}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def submit_prompt(prompt: str) -> None:
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.session_state.waiting = True


def fetch_response(prompt: str) -> None:
    try:
        data = post_chat(prompt)
        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": data["answer"],
                "intent": data["intent"],
                "sources": data.get("sources", []),
            }
        )
    except requests.RequestException:
        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": "API 서버에 연결할 수 없어요. 🔌\nFastAPI 컨테이너가 실행 중인지 확인해 주세요.",
                "intent": "연결 오류",
                "sources": [],
            }
        )
    st.session_state.waiting = False


# ── 앱 시작 ────────────────────────────────────────────────────
st.set_page_config(page_title="SOMA 부산 채팅", page_icon="💬", layout="centered")
st.markdown(CSS, unsafe_allow_html=True)
init_state()

# ── 사이드바 ───────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 💬 SOMA 부산")
    st.caption("SW마에스트로 부산 AI 도우미")
    st.divider()
    st.metric("대화 턴", max(len(st.session_state.messages) - 1, 0))
    st.caption(f"API: {API_URL}")
    st.divider()
    st.markdown("**예시 질문**")
    for p in EXAMPLE_PROMPTS:
        if st.button(p, use_container_width=True, key=f"ex_{p}"):
            st.session_state.pending_prompt = p
            st.rerun()
    st.divider()
    if st.button("🗑️ 대화 초기화", use_container_width=True):
        st.session_state.clear()
        st.rerun()

# ── 헤더 ───────────────────────────────────────────────────────
st.markdown(
    """
    <div class="chat-topbar">
        <div class="chat-topbar-avatar">🤖</div>
        <div>
            <div class="chat-topbar-title">SOMA 부산 도우미</div>
            <div class="chat-topbar-sub">
                <span class="online-dot"></span>SW마에스트로 부산 AI 어시스턴트
            </div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── 메시지 목록 ────────────────────────────────────────────────
for msg in st.session_state.messages:
    render_message(msg)

# 답변 대기 중: 유저 메시지는 이미 표시된 상태에서 API 호출
if st.session_state.waiting:
    last_user = next(
        (m["content"] for m in reversed(st.session_state.messages) if m["role"] == "user"),
        None,
    )
    with st.spinner("답변을 생성하고 있어요..."):
        if last_user:
            fetch_response(last_user)
    st.rerun()

# ── 입력 ──────────────────────────────────────────────────────
prompt = st.chat_input("메시지를 입력하세요...")
pending = st.session_state.pending_prompt

if pending:
    st.session_state.pending_prompt = None
    submit_prompt(pending)
    st.rerun()

if prompt:
    submit_prompt(prompt)
    st.rerun()
