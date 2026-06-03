"""Embed every .md in data/crawl/ with Upstage Solar and save one .npy per file.

- One 4096-dim vector per document (the strategy we agreed on).
- If a document is longer than ~5000 chars (~Solar's 4000-token window for
  Korean), truncate. We log a warning when that happens.
- Reads UPSTAGE_API_KEY from .env.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np
from dotenv import load_dotenv
from openai import OpenAI
from tqdm import tqdm

ROOT = Path(__file__).resolve().parent.parent
CRAWL_DIR = ROOT / "data" / "crawl"
EMB_DIR = ROOT / "data" / "embeddings"

MODEL = "solar-embedding-1-large-passage"
MAX_CHARS = 5000  # rough cap for Solar's 4000-token limit on Korean text


def get_client() -> OpenAI:
    load_dotenv(ROOT / ".env")
    api_key = os.environ.get("UPSTAGE_API_KEY")
    if not api_key:
        sys.exit("UPSTAGE_API_KEY not set. Put it in .env at the project root.")
    return OpenAI(api_key=api_key, base_url="https://api.upstage.ai/v1/solar")


def embed_text(client: OpenAI, text: str) -> np.ndarray:
    response = client.embeddings.create(model=MODEL, input=text)
    return np.asarray(response.data[0].embedding, dtype=np.float32)


def main() -> None:
    EMB_DIR.mkdir(parents=True, exist_ok=True)
    md_files = sorted(CRAWL_DIR.glob("*.md"))
    if not md_files:
        sys.exit(f"No .md files found in {CRAWL_DIR}")

    client = get_client()
    print(f"Embedding {len(md_files)} files with {MODEL} → {EMB_DIR}")

    for md_path in tqdm(md_files, unit="file"):
        text = md_path.read_text(encoding="utf-8")
        if len(text) > MAX_CHARS:
            tqdm.write(f"  ! truncating {md_path.name}: {len(text)} → {MAX_CHARS} chars")
            text = text[:MAX_CHARS]

        vec = embed_text(client, text)
        out_path = EMB_DIR / f"{md_path.stem}.npy"
        np.save(out_path, vec)
        tqdm.write(f"  ✓ {md_path.stem}.npy  shape={vec.shape}")


if __name__ == "__main__":
    main()
