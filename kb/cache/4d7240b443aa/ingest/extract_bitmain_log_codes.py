#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
extract_bitmain_log_codes.py

Extract Bitmain Antminer log-string "codes" from official support articles.

Bitmain typically does NOT publish a single numeric error-code table.
Instead, they publish troubleshooting by interpreting kernel/diagnostic logs.

This script:
  - reads a JSONL catalog (from crawl_manuals.py)
  - fetches HTML for Bitmain support articles
  - extracts patterns like:
      ERROR_[A-Z_]+
      Sweep error string = X:N
      Read Temp Sensor Failed
      fail to read pic temp
      stratum connection timeout
      soc init failed
  - outputs:
      output/bitmain_log_codes_extracted.json (dictionary entries)
      output/bitmain_log_codes_hitlist.jsonl (per-article hits)

Usage:
  pip install requests beautifulsoup4 lxml
  python extract_bitmain_log_codes.py --catalog output/manual_catalog_raw.jsonl --out_dir output

"""
import argparse, json, re, urllib.parse
from collections import defaultdict
import requests
from bs4 import BeautifulSoup

UA = "HashInsightManualCrawler/0.1 (+contact: ops@yourdomain.example)"
TIMEOUT = 25

PATTERNS = [
  re.compile(r"\bERROR_[A-Z0-9_]+\b"),
  re.compile(r"Sweep\s*error\s*string\s*=\s*[A-Z]:\d+", re.IGNORECASE),
  re.compile(r"Read\s*Temp\s*Sensor\s*Failed", re.IGNORECASE),
  re.compile(r"fail\s*to\s*read\s*pic\s*temp", re.IGNORECASE),
  re.compile(r"soc\s*init\s*failed", re.IGNORECASE),
  re.compile(r"stratum\s*connection\s*timeout", re.IGNORECASE),
  re.compile(r"retry\s*after\s*30\s*seconds\s*failures\s*\d+", re.IGNORECASE),
  re.compile(r"only\s*find\s*\d+\s*asic", re.IGNORECASE),
  re.compile(r"detect\s*0\s*chips", re.IGNORECASE),
  re.compile(r"get_sw_version\s*error", re.IGNORECASE),
  re.compile(r"eeprom_[a-z0-9_]+\s*.*error", re.IGNORECASE),
  re.compile(r"net\s*lost", re.IGNORECASE),
]

def fetch_html(url: str) -> str:
    r = requests.get(url, headers={"User-Agent": UA}, timeout=TIMEOUT)
    r.raise_for_status()
    return r.text

def extract_text(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    # remove scripts/styles
    for tag in soup(["script","style","noscript"]):
        tag.decompose()
    return soup.get_text("\n", strip=True)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--catalog", required=True)
    ap.add_argument("--out_dir", required=True)
    args = ap.parse_args()

    out_dir = args.out_dir
    docs = []
    with open(args.catalog, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                docs.append(json.loads(line))

    # filter bitmain
    bitmain = [d for d in docs if "support.bitmain.com" in (d.get("url",""))]
    hits = []
    all_codes = defaultdict(int)

    for d in bitmain:
        url = d["url"]
        if url.lower().endswith(".pdf"):
            continue
        try:
            html = fetch_html(url)
            text = extract_text(html)
        except Exception:
            continue

        found = set()
        for pat in PATTERNS:
            for m in pat.finditer(text):
                code = m.group(0)
                code = re.sub(r"\s+", " ", code).strip()
                found.add(code)

        if found:
            hits.append({"url": url, "title": d.get("title",""), "codes": sorted(found)})
            for c in found:
                all_codes[c] += 1

    # output per-article hitlist
    import os
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "bitmain_log_codes_hitlist.jsonl"), "w", encoding="utf-8") as f:
        for h in hits:
            f.write(json.dumps(h, ensure_ascii=False) + "\n")

    # output aggregated codes (frequency)
    agg = [{"code": k, "hits": v} for k,v in sorted(all_codes.items(), key=lambda x: (-x[1], x[0]))]
    with open(os.path.join(out_dir, "bitmain_log_codes_extracted.json"), "w", encoding="utf-8") as f:
        json.dump({"brand":"Bitmain","generated_from":"catalog+support articles","entries": agg}, f, ensure_ascii=False, indent=2)

    print(f"Extracted {len(agg)} unique codes from {len(hits)} pages")

if __name__ == "__main__":
    main()
