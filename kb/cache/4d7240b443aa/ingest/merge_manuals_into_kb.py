#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
merge_manuals_into_kb.py

Takes crawled manual catalog and merges it into KB sources.json as SourceRef items.
This does NOT copy PDF content; it only stores references (safe default).

Usage:
  python merge_manuals_into_kb.py --catalog output/manual_catalog_raw.jsonl --kb_sources ../sources.json --out ../sources.json

"""
import argparse, json, re
from pathlib import Path

def slug(s: str) -> str:
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", "_", s).strip("_")
    return s[:80] if s else "doc"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--catalog", required=True)
    ap.add_argument("--kb_sources", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    kb = json.loads(Path(args.kb_sources).read_text(encoding="utf-8"))
    existing = {x["source_id"] for x in kb}

    new = []
    with open(args.catalog, "r", encoding="utf-8") as f:
        for line in f:
            d = json.loads(line)
            sid = f"auto_{d.get('source_id','src')}_{slug(d.get('title',''))}"
            if sid in existing:
                continue
            new.append({
                "source_id": sid,
                "title": d.get("title",""),
                "url": d.get("url",""),
                "publisher": d.get("source_id",""),
                "type": "pdf" if d.get("content_type")=="pdf" else "html",
                "published_or_updated": "",
                "notes": f"auto-added by crawler; brand={d.get('brand')}; doc_type={d.get('doc_type')}; discovered_from={d.get('discovered_from')}"
            })

    merged = kb + new
    Path(args.out).write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Added {len(new)} sources. Total now {len(merged)}")

if __name__ == "__main__":
    main()
