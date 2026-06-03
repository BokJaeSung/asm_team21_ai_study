"""Extract a PDF, chunk it, embed each chunk, and save outputs under data/.

Example:
    python src/embed_pdf.py "/path/to/file.pdf" --name "document name"
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

import numpy as np
from dotenv import load_dotenv
from openai import OpenAI
from pypdf import PdfReader
from tqdm import tqdm

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
EMB_DIR = ROOT / "data" / "embeddings"

MODEL = "solar-embedding-1-large-passage"
CHUNK_CHARS = 1800
OVERLAP_CHARS = 200


def get_client() -> OpenAI:
    load_dotenv(ROOT / ".env")
    api_key = os.environ.get("UPSTAGE_API_KEY")
    if not api_key:
        sys.exit("UPSTAGE_API_KEY not set. Put it in .env at the project root.")
    return OpenAI(api_key=api_key, base_url="https://api.upstage.ai/v1/solar")


def clean_text(text: str) -> str:
    text = text.replace("\x00", "")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_pages(pdf_path: Path) -> list[tuple[int, str]]:
    reader = PdfReader(pdf_path)
    pages = []
    for index, page in enumerate(reader.pages, start=1):
        text = clean_text(page.extract_text() or "")
        if text:
            pages.append((index, text))
    return pages


def chunk_page_text(page_no: int, text: str, max_chars: int, overlap_chars: int) -> list[str]:
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks: list[str] = []
    current = f"[page {page_no}]\n"

    for paragraph in paragraphs:
        next_text = f"{current}\n{paragraph}".strip()
        if len(next_text) <= max_chars:
            current = next_text
            continue

        if current.strip() != f"[page {page_no}]":
            chunks.append(current.strip())

        if len(paragraph) <= max_chars:
            current = f"[page {page_no}]\n{paragraph}"
            continue

        for start in range(0, len(paragraph), max_chars - overlap_chars):
            part = paragraph[start : start + max_chars]
            chunks.append(f"[page {page_no}]\n{part}".strip())
        current = f"[page {page_no}]\n"

    if current.strip() != f"[page {page_no}]":
        chunks.append(current.strip())
    return chunks


def chunk_pages(
    pages: list[tuple[int, str]], max_chars: int = CHUNK_CHARS, overlap_chars: int = OVERLAP_CHARS
) -> list[dict[str, object]]:
    chunks = []
    for page_no, text in pages:
        for page_chunk in chunk_page_text(page_no, text, max_chars, overlap_chars):
            chunks.append({"page": page_no, "text": page_chunk})
    return chunks


def embed_text(client: OpenAI, text: str) -> np.ndarray:
    response = client.embeddings.create(model=MODEL, input=text)
    return np.asarray(response.data[0].embedding, dtype=np.float32)


def write_raw_files(name: str, pages: list[tuple[int, str]], chunks: list[dict[str, object]]) -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    full_text = "\n\n".join(f"[page {page_no}]\n{text}" for page_no, text in pages)
    (RAW_DIR / f"{name}.txt").write_text(full_text + "\n", encoding="utf-8")

    md_parts = [f"# {name}", "", f"- pages: {len(pages)}", f"- chunks: {len(chunks)}", ""]
    for index, chunk in enumerate(chunks, start=1):
        md_parts.extend([f"## chunk {index} (page {chunk['page']})", "", str(chunk["text"]), ""])
    (RAW_DIR / f"{name}.md").write_text("\n".join(md_parts), encoding="utf-8")


def write_embeddings(name: str, chunks: list[dict[str, object]]) -> Path:
    EMB_DIR.mkdir(parents=True, exist_ok=True)
    client = get_client()
    vectors = []
    for chunk in tqdm(chunks, desc="Embedding chunks", unit="chunk"):
        vectors.append(embed_text(client, str(chunk["text"])))

    matrix = np.vstack(vectors).astype(np.float32)
    out_path = EMB_DIR / f"{name}.npy"
    np.save(out_path, matrix)

    metadata = {
        "source": f"{name}.pdf",
        "model": MODEL,
        "shape": list(matrix.shape),
        "chunks": [{"index": i, "page": chunk["page"]} for i, chunk in enumerate(chunks)],
    }
    (EMB_DIR / f"{name}.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return out_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Chunk and embed a PDF into sadari/data.")
    parser.add_argument("pdf", type=Path)
    parser.add_argument("--name", help="Output basename. Defaults to the PDF stem.")
    parser.add_argument("--chunk-chars", type=int, default=CHUNK_CHARS)
    parser.add_argument("--overlap-chars", type=int, default=OVERLAP_CHARS)
    parser.add_argument("--skip-embeddings", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    name = args.name or args.pdf.stem
    pages = extract_pages(args.pdf)
    if not pages:
        sys.exit(f"No text extracted from {args.pdf}")

    chunks = chunk_pages(pages, args.chunk_chars, args.overlap_chars)
    write_raw_files(name, pages, chunks)
    print(f"Wrote raw files for {len(pages)} pages and {len(chunks)} chunks.")

    if not args.skip_embeddings:
        out_path = write_embeddings(name, chunks)
        print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
