#!/usr/bin/env python3
"""
Fetch the LIVE public-site guide files into the evidence index's source dir.

The published Library at https://library.lupine.science is an SPA — article
bodies are not individually fetchable, and the authoritative article content
is already indexed from the in-repo `library-content.v1` bundle
(exports/library-content/latest, see process_article_file in main.py). What
the live site DOES serve as plain text are its agent/crawler guide files
(llms.txt, llms-full.txt): the canonical public description of the program,
its surfaces, and its URLs. This script pulls those into ./data as
kind="site_guide" JSONL records so the index also carries what the live
site says about itself.

Incrementality-friendly: the output file is rewritten only when the fetched
content actually changed, so an unchanged fetch leaves the CocoIndex content
fingerprint untouched and the re-index is a no-op.

Usage:
    python fetch_site_content.py             # fetch defaults, tolerate failures
    python fetch_site_content.py --strict    # non-zero exit on any failure
    python fetch_site_content.py --url https://lupine.science/llms.txt  # add more
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
import urllib.error
import urllib.request

OUT = pathlib.Path(__file__).resolve().parent / "data" / "site_guides.jsonl"
DEFAULT_URLS = [
    "https://library.lupine.science/llms.txt",
    "https://library.lupine.science/llms-full.txt",
]
MAX_BYTES = 1024 * 1024  # a guide file should be small; refuse to embed a mistake
TIMEOUT_S = 30
# The site's edge 403s the default Python-urllib UA; identify ourselves honestly.
USER_AGENT = "lupine-evidence-index/1.0 (+https://github.com/alexwelcing/lupine-rhizo)"


def _record(url: str, text: str) -> dict:
    """One site-guide JSONL record in the pipeline's evidence format.
    Deliberately timestamp-free: identical content must produce identical
    bytes so the indexer's fingerprint sees no change on a no-op fetch."""
    return {
        "id": url,
        "kind": "site_guide",
        "ref_id": url,
        "text": text.strip(),
        "metadata": {"url": url, "bytes": len(text.encode("utf-8"))},
    }


def _fetch(url: str) -> str | None:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
            body = resp.read(MAX_BYTES + 1)
        if len(body) > MAX_BYTES:
            print(f"[site] {url}: larger than {MAX_BYTES} bytes, skipping", file=sys.stderr)
            return None
        text = body.decode("utf-8", errors="replace")
        if text.lstrip()[:9].lower() == "<!doctype":
            print(f"[site] {url}: got the SPA HTML shell, not a guide file — skipping",
                  file=sys.stderr)
            return None
        return text
    except (urllib.error.URLError, OSError, TimeoutError) as e:
        print(f"[site] {url}: fetch failed ({e})", file=sys.stderr)
        return None


def write_if_changed(records: list[dict], out: pathlib.Path) -> bool:
    """Write JSONL only when content differs. Returns True if written."""
    payload = "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records)
    if out.exists() and out.read_text(encoding="utf-8") == payload:
        return False
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(payload, encoding="utf-8")
    return True


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--url", action="append", default=[],
                    help="additional guide URL(s) to fetch (repeatable)")
    ap.add_argument("--out", default=str(OUT))
    ap.add_argument("--strict", action="store_true",
                    help="exit non-zero if any fetch fails (default: tolerate, keep old file)")
    args = ap.parse_args(argv)

    urls = DEFAULT_URLS + args.url
    records, failed = [], []
    for url in urls:
        text = _fetch(url)
        if text:
            records.append(_record(url, text))
            print(f"[site] fetched {url} ({len(text)} chars)")
        else:
            failed.append(url)

    out = pathlib.Path(args.out)
    if not records:
        print("[site] nothing fetched; leaving existing file untouched", file=sys.stderr)
        return 1 if args.strict else 0
    if write_if_changed(records, out):
        print(f"wrote {len(records)} records -> {out}. Run `cocoindex update main.py` to index.")
    else:
        print(f"unchanged ({len(records)} records) — no rewrite, re-index will be a no-op")
    return 1 if (failed and args.strict) else 0


if __name__ == "__main__":
    sys.exit(main())
