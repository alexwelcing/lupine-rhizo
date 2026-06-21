#!/usr/bin/env python3
"""Activate the live Rhizo evidence loop.

This script is intentionally dependency-free. It reads public, non-mutating
glim-think routes, writes CocoIndex-compatible JSONL records, and can optionally
upsert those same records into the GCP evidence-index service when
EVIDENCE_INGEST_TOKEN is present in the environment.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from typing import Any, Iterable


DEFAULT_WORKER_URL = "https://glim-think-v1.aw-ab5.workers.dev"
DEFAULT_EVIDENCE_INDEX_URL = "https://evidence-index-edbhtpvina-uc.a.run.app"
DEFAULT_OUT = pathlib.Path(__file__).resolve().parents[1] / "cocoindex" / "data"
MAX_TEXT = 6000
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/126.0.0.0 Safari/537.36 RhizoEvidenceActivation/1.0"
)
KIND_FILENAMES = {
    "claim": "claims.jsonl",
    "coordination_trace": "coordination_traces.jsonl",
    "hypothesis": "hypotheses.jsonl",
    "research_question": "research_questions.jsonl",
    "workflow_descriptor": "workflow_descriptors.jsonl",
    "workflow_snapshot": "workflow_snapshots.jsonl",
}


def _url(base: str, path: str, params: dict[str, Any] | None = None) -> str:
    base = base.rstrip("/")
    query = urllib.parse.urlencode({k: v for k, v in (params or {}).items() if v is not None})
    return f"{base}{path}{'?' + query if query else ''}"


def _fetch_json(url: str, token: str | None = None, timeout: int = 30) -> Any:
    headers = {"Accept": "application/json", "User-Agent": USER_AGENT}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _post_json(url: str, payload: dict[str, Any], token: str, timeout: int = 30) -> Any:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": USER_AGENT,
            "Authorization": f"Bearer {token}",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _clean_text(value: Any, limit: int = MAX_TEXT) -> str:
    text = str(value or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    while "\n\n\n" in text:
        text = text.replace("\n\n\n", "\n\n")
    return text[:limit]


def _stable_json(value: Any, limit: int = 2500) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            return _clean_text(value, limit)
    return _clean_text(json.dumps(value, ensure_ascii=False, sort_keys=True), limit)


def _record(
    *,
    rec_id: str,
    kind: str,
    ref_id: str,
    text: str,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    rec_id = _clean_text(rec_id, 300)
    text = _clean_text(text)
    if not rec_id or not text:
        return None
    return {
        "id": rec_id,
        "kind": kind,
        "ref_id": _clean_text(ref_id or rec_id, 300),
        "text": text,
        "metadata": metadata or {},
    }


def _coordination_records(worker_url: str, limit: int) -> Iterable[dict[str, Any]]:
    data = _fetch_json(_url(worker_url, "/coordination/traces", {"limit": limit}))
    for row in data.get("traces", []):
        trace_id = str(row.get("trace_id") or row.get("id") or "")
        text = (
            f"Strategy: {row.get('strategy')}. Outcome: {row.get('coordination_outcome')}. "
            f"Intent: {row.get('intent')}. Priority: {row.get('priority')}. "
            f"Baseline provider: {row.get('baseline_provider')}; winner: {row.get('winner_provider')}. "
            f"Coordination hit: {row.get('coordination_hit')}. Tokens: {row.get('cost_tokens')}; "
            f"latency ms: {row.get('latency_ms')}. Agent: {row.get('agent_class')}.\n\n"
            f"{row.get('winner_text') or ''}"
        )
        rec = _record(
            rec_id=trace_id,
            kind="coordination_trace",
            ref_id=trace_id,
            text=text,
            metadata={
                "strategy": row.get("strategy"),
                "coordination_outcome": row.get("coordination_outcome"),
                "coordination_hit": row.get("coordination_hit"),
                "agent_class": row.get("agent_class"),
                "created_at": row.get("created_at"),
            },
        )
        if rec:
            yield rec


def _evidence_recent_records(worker_url: str, limit: int) -> Iterable[dict[str, Any]]:
    data = _fetch_json(_url(worker_url, "/evidence/recent", {"limit": limit}))
    for row in data.get("hypotheses", []):
        hyp_id = str(row.get("id") or "")
        text = (
            f"{row.get('title') or ''}\n\n"
            f"Status: {row.get('status')}. Confidence: {row.get('confidence')}. "
            f"Agent: {row.get('agent_id')}. Updated: {row.get('updated_at')}."
        )
        rec = _record(
            rec_id=hyp_id,
            kind="hypothesis",
            ref_id=hyp_id,
            text=text,
            metadata={
                "status": row.get("status"),
                "confidence": row.get("confidence"),
                "agent_id": row.get("agent_id"),
                "updated_at": row.get("updated_at"),
            },
        )
        if rec:
            yield rec


def _claim_records(worker_url: str, limit: int) -> Iterable[dict[str, Any]]:
    data = _fetch_json(_url(worker_url, "/claims", {"limit": limit}))
    for row in data.get("claims", []):
        claim_id = str(row.get("claim_id") or "")
        description = row.get("description") or ""
        claim_data = _stable_json(row.get("claim_data"))
        text = (
            f"Claim type: {row.get('claim_type')}. Status: {row.get('status')}. "
            f"Confidence: {row.get('confidence')}. Agent: {row.get('agent_id')}.\n\n"
            f"{description}\n\nClaim data summary:\n{claim_data}"
        )
        rec = _record(
            rec_id=claim_id,
            kind="claim",
            ref_id=claim_id,
            text=text,
            metadata={
                "claim_type": row.get("claim_type"),
                "status": row.get("status"),
                "confidence": row.get("confidence"),
                "agent_id": row.get("agent_id"),
                "created_at": row.get("created_at"),
            },
        )
        if rec:
            yield rec


def _question_records(worker_url: str, limit: int) -> Iterable[dict[str, Any]]:
    data = _fetch_json(_url(worker_url, "/research/questions", {"limit": limit}))
    for row in data.get("questions", []):
        question_id = str(row.get("id") or "")
        text = (
            f"Research question: {row.get('question') or ''}\n\n"
            f"Status: {row.get('status')}. Asked by: {row.get('asked_by')}. "
            f"Target hypothesis: {row.get('target_hypothesis_id')}.\n\n"
            f"Answer:\n{row.get('answer_md') or ''}"
        )
        rec = _record(
            rec_id=question_id,
            kind="research_question",
            ref_id=question_id,
            text=text,
            metadata={
                "status": row.get("status"),
                "asked_by": row.get("asked_by"),
                "target_hypothesis_id": row.get("target_hypothesis_id"),
            },
        )
        if rec:
            yield rec


def _workflow_records(worker_url: str) -> Iterable[dict[str, Any]]:
    data = _fetch_json(_url(worker_url, "/research/workflows"))
    for workflow in data.get("workflows", []):
        workflow_id = str(workflow.get("workflow_id") or "")
        text = (
            f"Workflow: {workflow.get('label') or workflow_id}\n\n"
            f"Purpose: {workflow.get('purpose') or ''}\n\n"
            f"Descriptor:\n{_stable_json(workflow, limit=MAX_TEXT)}"
        )
        rec = _record(
            rec_id=f"workflow:{workflow_id}",
            kind="workflow_descriptor",
            ref_id=workflow_id,
            text=text,
            metadata={"workflow_id": workflow_id, "unit_kind": workflow.get("unit_kind")},
        )
        if rec:
            yield rec


def _workflow_snapshot_records(worker_url: str) -> Iterable[dict[str, Any]]:
    progress = _fetch_json(_url(worker_url, "/research/mlip-discovery/progress"))
    campaign_id = str(progress.get("campaign_id") or "latest")
    rec = _record(
        rec_id=f"workflow_snapshot:mlip-discovery-loop:{campaign_id}",
        kind="workflow_snapshot",
        ref_id=campaign_id,
        text=(
            f"MLIP discovery progress: {progress.get('headline')}\n\n"
            f"State: {progress.get('state')}. Phase: {progress.get('phase')}. "
            f"Records: {progress.get('progress', {}).get('records')}; "
            f"sentinels: {progress.get('progress', {}).get('sentinels')}; "
            f"agenda actions: {progress.get('progress', {}).get('agenda_actions')}.\n\n"
            f"Snapshot:\n{_stable_json(progress, limit=MAX_TEXT)}"
        ),
        metadata={
            "workflow_id": progress.get("workflow_id"),
            "campaign_id": progress.get("campaign_id"),
            "state": progress.get("state"),
            "phase": progress.get("phase"),
        },
    )
    if rec:
        yield rec


def collect_records(worker_url: str, limit: int) -> list[dict[str, Any]]:
    streams = [
        _coordination_records(worker_url, limit),
        _evidence_recent_records(worker_url, limit),
        _claim_records(worker_url, limit),
        _question_records(worker_url, limit),
        _workflow_records(worker_url),
        _workflow_snapshot_records(worker_url),
    ]
    records: dict[str, dict[str, Any]] = {}
    for stream in streams:
        for rec in stream:
            records[rec["id"]] = rec
    return sorted(records.values(), key=lambda r: (r["kind"], r["id"]))


def write_jsonl(records: list[dict[str, Any]], out_dir: pathlib.Path) -> Counter:
    out_dir.mkdir(parents=True, exist_ok=True)
    by_kind: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for rec in records:
        by_kind[rec["kind"]].append(rec)
    counts: Counter = Counter()
    for kind, rows in sorted(by_kind.items()):
        path = out_dir / KIND_FILENAMES.get(kind, f"{kind}s.jsonl")
        with path.open("w", encoding="utf-8") as handle:
            for rec in rows:
                handle.write(json.dumps(rec, ensure_ascii=False, sort_keys=True) + "\n")
        counts[kind] = len(rows)
    return counts


def ingest_records(records: list[dict[str, Any]], ingest_url: str, token: str) -> tuple[int, list[str]]:
    failures: list[str] = []
    ok = 0
    for rec in records:
        try:
            _post_json(_url(ingest_url, "/ingest"), rec, token)
            ok += 1
        except Exception as exc:  # noqa: BLE001 - keep batch moving and report ids.
            failures.append(f"{rec['id']}: {exc}")
    return ok, failures


def command_collect(args: argparse.Namespace) -> int:
    records = collect_records(args.worker_url, args.limit)
    counts = write_jsonl(records, pathlib.Path(args.out))
    print(json.dumps({
        "ok": True,
        "records": len(records),
        "out": str(pathlib.Path(args.out).resolve()),
        "counts": dict(counts),
    }, indent=2, sort_keys=True))
    return 0 if records else 2


def command_ingest(args: argparse.Namespace) -> int:
    token = (args.token or os.environ.get("EVIDENCE_INGEST_TOKEN") or "").strip()
    if not token:
        print("EVIDENCE_INGEST_TOKEN is required for ingest", file=sys.stderr)
        return 2
    records = collect_records(args.worker_url, args.limit)
    counts = write_jsonl(records, pathlib.Path(args.out))
    before = None
    try:
        before = _fetch_json(_url(args.ingest_url, "/count"), token=token).get("count")
    except Exception:
        before = None
    started = time.monotonic()
    ingested, failures = ingest_records(records, args.ingest_url, token)
    after = None
    try:
        after = _fetch_json(_url(args.ingest_url, "/count"), token=token).get("count")
    except Exception:
        after = None
    print(json.dumps({
        "ok": not failures,
        "collected": len(records),
        "ingested": ingested,
        "failed": len(failures),
        "count_before": before,
        "count_after": after,
        "seconds": round(time.monotonic() - started, 2),
        "out": str(pathlib.Path(args.out).resolve()),
        "counts": dict(counts),
        "failures": failures[:5],
    }, indent=2, sort_keys=True))
    return 0 if not failures and records else 1


def command_health(args: argparse.Namespace) -> int:
    token = (args.token or os.environ.get("EVIDENCE_INGEST_TOKEN") or "").strip() or None
    health = _fetch_json(_url(args.ingest_url, "/health"))
    count = None
    if token:
        try:
            count = _fetch_json(_url(args.ingest_url, "/count"), token=token).get("count")
        except urllib.error.HTTPError:
            count = None
    print(json.dumps({
        "health": health,
        "authenticated_count": count,
    }, indent=2, sort_keys=True))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    def add_common(p: argparse.ArgumentParser) -> None:
        p.add_argument("--worker-url", default=DEFAULT_WORKER_URL)
        p.add_argument("--limit", type=int, default=200)
        p.add_argument("--out", default=str(DEFAULT_OUT))

    p_collect = sub.add_parser("collect", help="Fetch live Worker evidence and write CocoIndex JSONL.")
    add_common(p_collect)
    p_collect.set_defaults(func=command_collect)

    p_ingest = sub.add_parser("ingest", help="Collect evidence and upsert it into evidence-index.")
    add_common(p_ingest)
    p_ingest.add_argument("--ingest-url", default=DEFAULT_EVIDENCE_INDEX_URL)
    p_ingest.add_argument("--token", default=None, help="Bearer token; defaults to EVIDENCE_INGEST_TOKEN.")
    p_ingest.set_defaults(func=command_ingest)

    p_health = sub.add_parser("health", help="Check evidence-index health and authenticated count.")
    p_health.add_argument("--ingest-url", default=DEFAULT_EVIDENCE_INDEX_URL)
    p_health.add_argument("--token", default=None, help="Bearer token; defaults to EVIDENCE_INGEST_TOKEN.")
    p_health.set_defaults(func=command_health)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")[:500]
        print(f"HTTP {exc.code}: {body}", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001 - top-level CLI error.
        print(f"evidence activation failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
