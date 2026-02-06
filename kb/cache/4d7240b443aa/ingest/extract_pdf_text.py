#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
extract_pdf_text.py

Optional: download PDFs and extract text into chunked JSON for RAG indexing.

Usage:
  pip install requests pypdf
  python extract_pdf_text.py --in output/manual_catalog_raw.jsonl --pdf_dir output/pdfs --out output/pdf_chunks.jsonl

Notes:
  - Only run this for sources you have rights to ingest and display.
  - You can store text internally for search; avoid redistributing PDF content without permission.
"""
import argparse, json, os, re, time, hashlib
from pathlib import Path
import requests
from pypdf import PdfReader

UA = "HashInsightManualCrawler/0.1 (+contact: ops@yourdomain.example)"
TIMEOUT = 30
SLEEP_SEC = 1.0

def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1024*1024), b""):
            h.update(chunk)
    return h.hexdigest()

def download(url: str, out_path: Path) -> bool:
    try:
        r = requests.get(url, timeout=TIMEOUT, headers={"User-Agent": UA})
        r.raise_for_status()
        out_path.write_bytes(r.content)
        return True
    except Exception:
        return False

def chunk_text(text: str, chunk_size: int = 1200, overlap: int = 150):
    text = re.sub(r"\s+", " ", text).strip()
    chunks = []
    i = 0
    while i < len(text):
        chunks.append(text[i:i+chunk_size])
        i += max(1, chunk_size - overlap)
    return chunks

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True)
    ap.add_argument("--pdf_dir", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    pdf_dir = Path(args.pdf_dir)
    pdf_dir.mkdir(parents=True, exist_ok=True)

    docs = []
    with open(args.inp, "r", encoding="utf-8") as f:
        for line in f:
            docs.append(json.loads(line))

    out_f = open(args.out, "w", encoding="utf-8")
    for d in docs:
        url = d["url"]
        if not url.lower().endswith(".pdf"):
            continue

        fname = re.sub(r"[^a-zA-Z0-9._-]+", "_", url.split("/")[-1])
        if not fname.lower().endswith(".pdf"):
            fname += ".pdf"
        p = pdf_dir / fname

        if not p.exists():
            ok = download(url, p)
            time.sleep(SLEEP_SEC)
            if not ok:
                continue

        try:
            reader = PdfReader(str(p))
            full = []
            for page in reader.pages:
                full.append(page.extract_text() or "")
            full_text = "\n".join(full)
            chunks = chunk_text(full_text)
            digest = sha256_file(p)
            for idx, ch in enumerate(chunks):
                out_f.write(json.dumps({
                    "doc_url": url,
                    "doc_title": d.get("title",""),
                    "source_id": d.get("source_id",""),
                    "brand": d.get("brand","Unknown"),
                    "doc_type": d.get("doc_type","unknown"),
                    "pdf_sha256": digest,
                    "chunk_index": idx,
                    "text": ch
                }, ensure_ascii=False) + "\n")
        except Exception:
            continue

    out_f.close()
    print(f"Wrote chunks to {args.out}")

if __name__ == "__main__":
    main()
