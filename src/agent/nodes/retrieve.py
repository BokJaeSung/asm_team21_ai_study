from __future__ import annotations

import chromadb

from ..llm import chat, embed_query
from ..prompts import RELEVANCE_CHECK_PROMPT
from ..state import AgentState
from ...config import get_settings

_collection: chromadb.Collection | None = None

_SCORE_THRESHOLD = 0.4  # 이 점수 미만은 LLM 검증 없이 제외


def _get_collection() -> chromadb.Collection:
    global _collection
    if _collection is None:
        s = get_settings()
        client = chromadb.PersistentClient(path=s.chroma_path)
        _collection = client.get_or_create_collection(s.chroma_collection)
    return _collection


def _llm_validate(question: str, chunk: str) -> bool:
    """LLM에게 청크가 질문과 관련 있는지 yes/no로 확인한다."""
    prompt = RELEVANCE_CHECK_PROMPT.format(question=question, chunk=chunk[:800])
    messages = [{"role": "user", "content": prompt}]
    answer = chat(messages, temperature=0.0).strip().lower()
    return answer.startswith("yes")


def retrieve_node(state: AgentState) -> dict:
    s = get_settings()
    query_vec = embed_query(state["question"])
    collection = _get_collection()

    results = collection.query(
        query_embeddings=[query_vec],
        n_results=s.max_chunks,
        include=["documents", "metadatas", "distances"],
    )

    # 1단계: 벡터 유사도 기반 후보 수집
    candidates: list[dict] = []
    if results["documents"] and results["documents"][0]:
        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            score = round(1 - dist, 4)
            if score >= _SCORE_THRESHOLD:
                candidates.append({
                    "content": doc,
                    "source": meta.get("source", "unknown"),
                    "score": score,
                })

    # 2단계: LLM 재검증으로 false positive 제거
    validated: list[dict] = [
        chunk for chunk in candidates
        if _llm_validate(state["question"], chunk["content"])
    ]

    return {
        "retrieved_chunks": validated,
        "is_fallback_crawl": False,
        "execution_history": ["retrieve_documents"],
    }
