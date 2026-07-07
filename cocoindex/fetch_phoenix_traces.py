#!/usr/bin/env python3
"""
Export agent-trace telemetry from Phoenix (Arize) into the evidence index.

The stack already SENDS OpenInference spans to Phoenix from two places —
the glim-think worker (src/telemetry/phoenix.ts, OTLP protobuf) and the GCP
runners (mlip-cell-runner). This script closes the read side: it pulls
recent spans back out of Phoenix's REST API, summarizes each trace's ROOT
span into a prose evidence record (kind="agent_trace"), and writes
./data/agent_traces.jsonl for the pipeline to embed. That makes questions
like "which agent runs failed last night and why?" or "what did the
Theorist actually conclude?" semantic queries over the same index as the
research corpus.

Configuration (same secret names the deploy workflows already use):
    PHOENIX_COLLECTOR_ENDPOINT   e.g. https://app.phoenix.arize.com
    PHOENIX_API_KEY              read-scoped API key
    PHOENIX_PROJECT_NAME         project to export (default: all projects)

Offline-tolerant: without credentials it prints a skip notice and exits 0
(--strict to fail instead), so local/CI runs never require Phoenix access.
Records are deterministic per span (no fetch-time clock), and the JSONL is
rewritten only on change — an unchanged export keeps the re-index a no-op.

Usage:
    python fetch_phoenix_traces.py [--limit 200] [--project NAME] [--strict]
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys
import urllib.error
import urllib.parse
import urllib.request

from fetch_site_content import write_if_changed

OUT = pathlib.Path(__file__).resolve().parent / "data" / "agent_traces.jsonl"
TIMEOUT_S = 30
SNIPPET_CHARS = 600  # keep prompts/outputs bounded in the embedded text


def _get(base: str, path: str, key: str, params: dict | None = None):
    url = base.rstrip("/") + path
    if params:
        url += "?" + urllib.parse.urlencode({k: v for k, v in params.items() if v})
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {key}",
        "api_key": key,  # legacy Phoenix header; harmless alongside Bearer
        "accept": "application/json",
        "user-agent": "lupine-evidence-index/1.0 (+https://github.com/alexwelcing/lupine-rhizo)",
    })
    with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
        return json.loads(resp.read().decode("utf-8", errors="replace"))


def _attr(span: dict, key: str, default=None):
    """Attributes arrive either flat ({"llm.model_name": ...}) or nested
    ({"llm": {"model_name": ...}}) depending on Phoenix version — accept both."""
    attrs = span.get("attributes") or {}
    if key in attrs:
        return attrs[key]
    node = attrs
    for part in key.split("."):
        if not isinstance(node, dict) or part not in node:
            return default
        node = node[part]
    return node


def _latency_ms(span: dict) -> int | None:
    try:
        from datetime import datetime
        start = datetime.fromisoformat(str(span["start_time"]).replace("Z", "+00:00"))
        end = datetime.fromisoformat(str(span["end_time"]).replace("Z", "+00:00"))
        return int((end - start).total_seconds() * 1000)
    except (KeyError, ValueError, TypeError):
        return None


def is_root(span: dict) -> bool:
    return not span.get("parent_id")


def span_record(span: dict, project: str) -> dict | None:
    """One trace-summary evidence record from a ROOT span. Returns None for
    spans that carry nothing worth embedding."""
    ctx = span.get("context") or {}
    trace_id = ctx.get("trace_id") or span.get("trace_id")
    if not trace_id:
        return None
    name = span.get("name") or "unnamed"
    okind = _attr(span, "openinference.span.kind") or span.get("span_kind") or "UNKNOWN"
    status = span.get("status_code") or span.get("status", {}).get("code") or "UNSET"
    model = _attr(span, "llm.model_name")
    tokens = _attr(span, "llm.token_count.total")
    latency = _latency_ms(span)
    inp = str(_attr(span, "input.value") or "")[:SNIPPET_CHARS].strip()
    out = str(_attr(span, "output.value") or "")[:SNIPPET_CHARS].strip()
    status_msg = span.get("status_message") or ""

    parts = [f"Agent trace '{name}' ({okind}) in project {project}. Status: {status}."]
    if status_msg:
        parts.append(f"Status message: {status_msg}.")
    if model:
        parts.append(f"Model: {model}.")
    if tokens is not None:
        parts.append(f"Tokens: {tokens}.")
    if latency is not None:
        parts.append(f"Latency: {latency} ms.")
    if inp:
        parts.append(f"Input: {inp}")
    if out:
        parts.append(f"Output: {out}")
    if len(parts) <= 1:
        return None
    return {
        "id": trace_id,
        "kind": "agent_trace",
        "ref_id": trace_id,
        "text": " ".join(parts),
        "metadata": {"project": project, "name": name, "span_kind": okind,
                     "status": str(status), "start_time": span.get("start_time")},
    }


def fetch_records(base: str, key: str, project: str | None, limit: int) -> list[dict]:
    if project:
        projects = [project]
    else:
        payload = _get(base, "/v1/projects", key)
        projects = [p.get("name") for p in payload.get("data", []) if p.get("name")]
    records: list[dict] = []
    for proj in projects:
        cursor = None
        remaining = limit
        while remaining > 0:
            page = _get(base, f"/v1/projects/{urllib.parse.quote(proj, safe='')}/spans",
                        key, {"limit": min(remaining, 100), "cursor": cursor})
            spans = page.get("data", [])
            for s in spans:
                if is_root(s):
                    rec = span_record(s, proj)
                    if rec:
                        records.append(rec)
            cursor = page.get("next_cursor")
            remaining -= len(spans)
            if not cursor or not spans:
                break
    # Deterministic order: newest first by start_time, then trace id.
    records.sort(key=lambda r: (str(r["metadata"].get("start_time") or ""), r["id"]),
                 reverse=True)
    return records


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--limit", type=int, default=200, help="max spans per project")
    ap.add_argument("--project", default=os.environ.get("PHOENIX_PROJECT_NAME"))
    ap.add_argument("--out", default=str(OUT))
    ap.add_argument("--strict", action="store_true",
                    help="exit non-zero when Phoenix is unreachable/unconfigured")
    args = ap.parse_args(argv)

    base = (os.environ.get("PHOENIX_COLLECTOR_ENDPOINT") or "").strip()
    key = (os.environ.get("PHOENIX_API_KEY") or "").strip()
    if not base or not key:
        print("[phoenix] PHOENIX_COLLECTOR_ENDPOINT / PHOENIX_API_KEY not set; skipping.",
              file=sys.stderr)
        return 1 if args.strict else 0

    try:
        records = fetch_records(base, key, args.project, args.limit)
    except (urllib.error.URLError, OSError, TimeoutError, json.JSONDecodeError) as e:
        print(f"[phoenix] fetch failed ({e})", file=sys.stderr)
        return 1 if args.strict else 0

    if not records:
        print("[phoenix] no root spans found; leaving existing file untouched")
        return 0
    out = pathlib.Path(args.out)
    if write_if_changed(records, out):
        print(f"wrote {len(records)} agent-trace records -> {out}. "
              "Run `cocoindex update main.py` to index.")
    else:
        print(f"unchanged ({len(records)} records) — no rewrite, re-index will be a no-op")
    return 0


if __name__ == "__main__":
    sys.exit(main())
