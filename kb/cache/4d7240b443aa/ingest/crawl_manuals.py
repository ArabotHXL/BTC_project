#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
crawl_manuals.py

Goal:
  Crawl a small set of authoritative sources for miner manuals/repair docs and output a machine-readable catalog.

Usage:
  pip install requests pyyaml beautifulsoup4 lxml
  python crawl_manuals.py --config config/sources.yaml --out output/manual_catalog_raw.jsonl

Notes:
  - This crawler is conservative: it crawls limited pages and respects domain allow-lists.
  - It stores only metadata + links by default to avoid copyright issues.
  - You can later choose to download PDFs and extract text (optional scripts).

"""
import argparse, json, re, time, urllib.parse
from dataclasses import dataclass
from typing import List, Dict, Set, Optional

import requests
import yaml
from bs4 import BeautifulSoup

UA = "HashInsightManualCrawler/0.1 (+contact: ops@yourdomain.example)"
TIMEOUT = 20
SLEEP_SEC = 1.2

def norm_url(url: str) -> str:
    # strip fragments and normalize
    parsed = urllib.parse.urlsplit(url)
    parsed = parsed._replace(fragment="")
    return urllib.parse.urlunsplit(parsed)

def guess_doc_type(url: str, title: str) -> str:
    s = (title + " " + url).lower()
    if "repair" in s or "hash board" in s or "hashboard" in s:
        return "repair_guide"
    if "error code" in s or "error-code" in s:
        return "error_codes"
    if "spec" in s or "specification" in s:
        return "spec"
    if "firmware" in s or "upgrade" in s:
        return "firmware"
    if "operation" in s or "quick start" in s or "user manual" in s or "manual" in s:
        return "user_manual"
    if "troubleshooting" in s:
        return "troubleshooting"
    return "unknown"

def infer_brand(url: str, title: str) -> str:
    s = (title + " " + url).lower()
    if "antminer" in s or "bitmain" in s or "apw" in s:
        return "Bitmain"
    if "whatsminer" in s or "microbt" in s:
        return "MicroBT"
    if "avalon" in s or "canaan" in s:
        return "Canaan"
    if "iceriver" in s:
        return "IceRiver"
    if "goldshell" in s:
        return "Goldshell"
    if "jasminer" in s:
        return "Jasminer"
    if "ipollo" in s:
        return "iPollo"
    if "innosilicon" in s:
        return "Innosilicon"
    if "ebang" in s:
        return "Ebang"
    return "Unknown"

def extract_links(html: str, base_url: str) -> List[Dict]:
    soup = BeautifulSoup(html, "lxml")
    out = []
    for a in soup.find_all("a"):
        href = a.get("href")
        if not href:
            continue
        abs_url = urllib.parse.urljoin(base_url, href)
        abs_url = norm_url(abs_url)
        title = " ".join(a.get_text(" ", strip=True).split())
        out.append({"url": abs_url, "title": title})
    return out

def fetch(session: requests.Session, url: str) -> Optional[str]:
    try:
        r = session.get(url, timeout=TIMEOUT, headers={"User-Agent": UA})
        r.raise_for_status()
        ct = r.headers.get("Content-Type", "")
        # treat pdf as not-HTML; return empty html, but still include as doc
        if "application/pdf" in ct or url.lower().endswith(".pdf"):
            return None
        return r.text
    except Exception:
        return None

def allowed(url: str, allow_domains: List[str]) -> bool:
    host = urllib.parse.urlsplit(url).netloc.lower()
    return any(host == d or host.endswith("." + d) for d in allow_domains)

def match_any(patterns: List[str], s: str) -> bool:
    for p in patterns:
        if re.search(p, s):
            return True
    return False

def crawl_source(session: requests.Session, src: Dict) -> List[Dict]:
    allow_domains = [d.lower() for d in src["allow_domains"]]
    allow_re = src.get("link_allow_regex", [])
    deny_re = src.get("link_deny_regex", [])
    max_pages = int(src.get("max_pages", 3))

    seen_pages: Set[str] = set()
    queue: List[str] = list(src["root_urls"])
    docs: Dict[str, Dict] = {}

    while queue and len(seen_pages) < max_pages:
        page_url = norm_url(queue.pop(0))
        if page_url in seen_pages:
            continue
        if not allowed(page_url, allow_domains):
            continue
        seen_pages.add(page_url)

        html = fetch(session, page_url)
        time.sleep(SLEEP_SEC)

        # If PDF or non-html: record as doc and continue
        if html is None:
            title = page_url.split("/")[-1]
            docs[page_url] = {
                "url": page_url,
                "title": title,
                "source_id": src["source_id"],
                "doc_type": guess_doc_type(page_url, title),
                "brand": infer_brand(page_url, title),
                "content_type": "pdf" if page_url.lower().endswith(".pdf") else "unknown",
                "discovered_from": page_url,
            }
            continue

        links = extract_links(html, page_url)
        for lk in links:
            u = lk["url"]
            t = lk["title"] or u.split("/")[-1]
            if not allowed(u, allow_domains):
                continue
            combined = f"{t} {u}"
            if deny_re and match_any(deny_re, combined):
                continue

            is_doc = False
            if u.lower().endswith(".pdf"):
                is_doc = True
            if allow_re and match_any(allow_re, combined):
                is_doc = True

            if is_doc:
                if u not in docs:
                    docs[u] = {
                        "url": u,
                        "title": t,
                        "source_id": src["source_id"],
                        "doc_type": guess_doc_type(u, t),
                        "brand": infer_brand(u, t),
                        "content_type": "pdf" if u.lower().endswith(".pdf") else "html",
                        "discovered_from": page_url,
                    }

            # enqueue more pages (only for html pages, not pdf)
            if not u.lower().endswith(".pdf") and len(seen_pages) + len(queue) < max_pages * 3:
                queue.append(u)

    return list(docs.values())

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True, help="YAML config file")
    ap.add_argument("--out", required=True, help="output JSONL file")
    args = ap.parse_args()

    cfg = yaml.safe_load(open(args.config, "r", encoding="utf-8"))
    sources = cfg["sources"]

    session = requests.Session()
    all_docs = []
    for src in sources:
        docs = crawl_source(session, src)
        for d in docs:
            all_docs.append(d)

    # de-dup by url
    uniq = {}
    for d in all_docs:
        uniq[d["url"]] = d

    with open(args.out, "w", encoding="utf-8") as f:
        for d in uniq.values():
            f.write(json.dumps(d, ensure_ascii=False) + "\n")

    print(f"wrote {len(uniq)} docs to {args.out}")

if __name__ == "__main__":
    main()
