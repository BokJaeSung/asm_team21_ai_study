from __future__ import annotations

import re
import textwrap
from html.parser import HTMLParser
from urllib.request import Request, urlopen
from urllib.error import URLError

from ..state import AgentState

_BASE = "https://www.swmaestro.ai"
_LIST_URL = f"{_BASE}/busan/sw/mypage/myNotice/list.do?menuNo=200038"
_DETAIL_URL = f"{_BASE}/busan/sw/mypage/myNotice/view.do?nttId={{ntt_id}}&menuNo=200038"
_TIMEOUT = 5
_CHUNK_SIZE = 1000
_MAX_DOCS = 3  # 폴백 크롤링에서 가져올 최대 공지 수


class _TextExtractor(HTMLParser):
    """HTML에서 가시 텍스트만 추출한다."""

    _SKIP_TAGS = {"script", "style", "noscript", "head"}

    def __init__(self) -> None:
        super().__init__()
        self._skip = 0
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: object) -> None:
        if tag in self._SKIP_TAGS:
            self._skip += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in self._SKIP_TAGS:
            self._skip = max(0, self._skip - 1)

    def handle_data(self, data: str) -> None:
        if not self._skip:
            stripped = data.strip()
            if stripped:
                self.parts.append(stripped)


def _fetch_html(url: str) -> str | None:
    req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urlopen(req, timeout=_TIMEOUT) as resp:
            return resp.read().decode("utf-8", errors="ignore")
    except (URLError, OSError):
        return None


def _extract_text(html: str) -> str:
    parser = _TextExtractor()
    parser.feed(html)
    return " ".join(parser.parts)


def _extract_notice_ids(html: str) -> list[tuple[str, str]]:
    """목록 페이지에서 (nttId, 제목) 리스트를 추출한다."""
    pattern = re.compile(
        r"nttId[='](\d+)[^>]*>.*?<[^>]+class=['\"]?(?:board_)?title['\"]?[^>]*>([^<]+)",
        re.DOTALL,
    )
    results = pattern.findall(html)

    # 단순 패턴 실패 시 nttId만 추출
    if not results:
        ids = re.findall(r"nttId=(\d+)", html)
        return [(ntt_id, "") for ntt_id in dict.fromkeys(ids)]

    return [(ntt_id, title.strip()) for ntt_id, title in results]


def _keyword_score(title: str, question: str) -> int:
    """질문 단어 중 제목에 포함된 개수로 단순 관련도 점수를 계산한다."""
    words = re.findall(r"\w+", question)
    return sum(1 for w in words if w in title)


def _chunk_text(text: str, source: str) -> list[dict]:
    """텍스트를 _CHUNK_SIZE 길이로 분할해 retrieved_chunks 형식으로 반환한다."""
    chunks = textwrap.wrap(text, width=_CHUNK_SIZE, break_long_words=False)
    return [
        {"content": c, "source": source, "score": 0.0}
        for c in chunks
        if len(c.strip()) > 50  # 너무 짧은 조각 제외
    ]


def dynamic_crawl_node(state: AgentState) -> dict:
    """벡터 검색 결과가 없을 때 공식 공지 목록을 추가 크롤링한다."""
    question = state["question"]

    # 1. 공지 목록 페이지 fetch
    list_html = _fetch_html(_LIST_URL)
    if not list_html:
        return {
            "retrieved_chunks": [],
            "is_fallback_crawl": True,
            "execution_history": ["dynamic_crawl"],
        }

    # 2. 공지 ID 추출 → 질문 관련도 순 정렬
    notices = _extract_notice_ids(list_html)
    scored = sorted(
        notices,
        key=lambda item: _keyword_score(item[1], question),
        reverse=True,
    )
    top_notices = scored[:_MAX_DOCS] if scored else notices[:_MAX_DOCS]

    # 3. 상세 페이지 크롤링 → 청크 생성
    all_chunks: list[dict] = []
    for ntt_id, title in top_notices:
        detail_html = _fetch_html(_DETAIL_URL.format(ntt_id=ntt_id))
        if not detail_html:
            continue
        text = _extract_text(detail_html)
        source = title if title else f"공지 #{ntt_id}"
        all_chunks.extend(_chunk_text(text, source))

    return {
        "retrieved_chunks": all_chunks,
        "is_fallback_crawl": True,
        "execution_history": ["dynamic_crawl"],
    }
