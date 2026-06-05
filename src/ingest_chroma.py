"""embed_pdf.py 가 생성한 data/raw/*.md + data/embeddings/*.npy 를
ChromaDB 컬렉션에 일괄 적재한다.

사용법:
    python src/ingest_chroma.py              # data/raw 전체 처리
    python src/ingest_chroma.py --reset      # 기존 컬렉션 초기화 후 재적재
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import numpy as np
import chromadb
from tqdm import tqdm

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
EMB_DIR = ROOT / "data" / "embeddings"


# ── 청크 텍스트 파싱 (embed_pdf.py 가 생성한 마크다운 형식) ─────────

def _parse_chunks(md_path: Path) -> list[str]:
    """'## chunk N (page P)' 구분자를 기준으로 청크 텍스트를 추출한다.
    구분자가 없으면 파일 전체를 단일 청크로 반환한다."""
    text = md_path.read_text(encoding="utf-8")
    parts = re.split(r"^## chunk \d+.*$", text, flags=re.MULTILINE)
    chunks = [p.strip() for p in parts[1:] if p.strip()]
    if not chunks:
        # 단일 문서 임베딩 포맷: 파일 전체를 하나의 청크로 처리
        chunks = [text.strip()]
    return chunks


# ── 메인 ─────────────────────────────────────────────────────────────

def ingest(reset: bool = False) -> None:
    from .config import get_settings
    s = get_settings()

    client = chromadb.PersistentClient(path=s.chroma_path)

    if reset:
        try:
            client.delete_collection(s.chroma_collection)
            print(f"기존 컬렉션 '{s.chroma_collection}' 삭제 완료")
        except Exception:
            pass

    collection = client.get_or_create_collection(
        s.chroma_collection,
        metadata={"hnsw:space": "cosine"},
    )

    md_files = sorted(RAW_DIR.glob("*.md"))
    if not md_files:
        sys.exit(f"data/raw/ 에 .md 파일이 없습니다. embed_pdf.py 를 먼저 실행하세요.")

    total = 0
    for md_path in tqdm(md_files, desc="파일", unit="file"):
        name = md_path.stem
        npy_path = EMB_DIR / f"{name}.npy"
        json_path = EMB_DIR / f"{name}.json"

        if not npy_path.exists():
            print(f"  ! {name}.npy 없음 — 건너뜀")
            continue

        chunks = _parse_chunks(md_path)
        embeddings: np.ndarray = np.load(npy_path)

        # 단일 벡터 (4096,) → (1, 4096) 로 reshape
        if embeddings.ndim == 1:
            embeddings = embeddings.reshape(1, -1)

        if len(chunks) != embeddings.shape[0]:
            print(f"  ! {name}: 청크 수({len(chunks)}) ≠ 임베딩 행({embeddings.shape[0]}) — 건너뜀")
            continue

        # 청크별 메타데이터 (페이지 번호 포함)
        meta_list: list[dict] = []
        if json_path.exists():
            meta = json.loads(json_path.read_text(encoding="utf-8"))
            for item in meta.get("chunks", []):
                meta_list.append({"source": name, "page": item.get("page", 0)})
        if len(meta_list) != len(chunks):
            meta_list = [{"source": name, "page": 0}] * len(chunks)

        ids = [f"{name}_{i}" for i in range(len(chunks))]

        # 이미 존재하는 ID 는 upsert 로 덮어씀
        collection.upsert(
            ids=ids,
            documents=chunks,
            embeddings=embeddings.tolist(),
            metadatas=meta_list,
        )
        tqdm.write(f"  ✓ {name}: {len(chunks)}청크 적재")
        total += len(chunks)

    print(f"\n완료: 총 {total}청크 → {s.chroma_path}/{s.chroma_collection}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest embeddings into ChromaDB")
    parser.add_argument("--reset", action="store_true", help="기존 컬렉션 초기화 후 재적재")
    args = parser.parse_args()
    ingest(reset=args.reset)


if __name__ == "__main__":
    main()
