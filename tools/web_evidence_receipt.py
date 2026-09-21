#!/usr/bin/env python3
"""Turn a `fastbrowse --json` run result into a Lupine web-evidence receipt.

fastbrowse (https://github.com/agent-labs-dev/fastbrowse) returns, for every
browser task, a list of verbatim page quotes with the URL and a hash of the
page capture each quote was cut from. That is the same shape as the provenance
discipline this repo already applies to LAMMPS traces and citation audits: a
number is only as good as the receipt behind it.

This tool is the intake boundary. It reads the raw `RunResult` JSON, keeps only
what the ledger needs (quotes, URLs, capture hashes, run status, cost), hashes
every quote and the receipt itself, and refuses to mark a receipt `citable`
unless the run finished `complete` with at least one quote. It has no network
access and no dependency outside the standard library, so it runs in CI with no
API keys.

Usage:

    python tools/web_evidence_receipt.py build run.json --out receipt.json \
        --source-path data/web_evidence/raw/run.json
    python tools/web_evidence_receipt.py check receipt.json

`check` re-derives the receipt hash and every quote hash and exits non-zero on
any mismatch, so a hand-edited quote cannot pass as captured text.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys
from datetime import datetime, timezone
from typing import Any

SCHEMA_VERSION = "web-evidence-receipt.v1"
TOOL_NAME = "fastbrowse"
CITABLE_STATUS = "complete"
KNOWN_STATUSES = {
    "complete",
    "unverified",
    "needs_confirmation",
    "needs_login",
    "blocked",
    "needs_input",
    "stuck",
    "budget_exceeded",
    "error",
}
HASHED_FIELDS_EXCLUDED = ("receipt_id", "receipt_sha256")


class ReceiptError(ValueError):
    """Raised when a run result or receipt is malformed."""


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def canonical_json(payload: Any) -> str:
    """Deterministic JSON: sorted keys, no whitespace, NFC-free ASCII escapes."""

    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _require_str(mapping: dict[str, Any], key: str, where: str) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ReceiptError(f"{where}: missing or empty string field {key!r}")
    return value


def _require_int(mapping: dict[str, Any], key: str, where: str) -> int:
    value = mapping.get(key)
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ReceiptError(f"{where}: field {key!r} must be a non-negative integer")
    return value


def _quote_from_evidence(item: Any, index: int) -> dict[str, Any]:
    where = f"evidence[{index}]"
    if not isinstance(item, dict):
        raise ReceiptError(f"{where}: expected an object")
    quote = _require_str(item, "quote", where)
    record: dict[str, Any] = {
        "quote": quote,
        "quote_sha256": _sha256_text(quote),
        "url": _require_str(item, "url", where),
        "captured_at": _require_str(item, "captured_at", where),
        "capture_sha256": _require_str(item, "capture_sha256", where).lower(),
    }
    if len(record["capture_sha256"]) != 64:
        raise ReceiptError(f"{where}: capture_sha256 must be 64 hex characters")
    source_id = item.get("source_id")
    if isinstance(source_id, str) and source_id:
        record["source_id"] = source_id
    if "frame_id" in item:
        frame_id = item.get("frame_id")
        if frame_id is not None and not isinstance(frame_id, str):
            raise ReceiptError(f"{where}: frame_id must be a string or null")
        record["frame_id"] = frame_id
    if "start" in item or "end" in item:
        record["span"] = {
            "start": _require_int(item, "start", where),
            "end": _require_int(item, "end", where),
        }
    return record


def _cost_summary(cost: Any) -> tuple[float, int]:
    """Return (known dollars, count of lines with no dollar figure)."""

    lines = cost.get("lines") if isinstance(cost, dict) else None
    if not isinstance(lines, list):
        return 0.0, 0
    known = 0.0
    unknown = 0
    for line in lines:
        dollars = line.get("dollars") if isinstance(line, dict) else None
        if isinstance(dollars, int | float) and not isinstance(dollars, bool):
            known += float(dollars)
        else:
            unknown += 1
    return round(known, 6), unknown


def _finalize(receipt: dict[str, Any]) -> dict[str, Any]:
    body = {k: v for k, v in receipt.items() if k not in HASHED_FIELDS_EXCLUDED}
    digest = _sha256_text(canonical_json(body))
    body["receipt_sha256"] = digest
    body["receipt_id"] = f"wer-{digest[:16]}"
    return body


def build_receipt(
    run: dict[str, Any],
    *,
    task_text: str,
    tool_version: str,
    start_url: str | None = None,
    llm_models: list[str] | None = None,
    source_path: str | None = None,
    source_bytes: bytes | None = None,
    generated_at: datetime | None = None,
) -> dict[str, Any]:
    """Build a receipt from a parsed fastbrowse RunResult."""

    if not isinstance(run, dict):
        raise ReceiptError("run result must be a JSON object")
    status = _require_str(run, "status", "run")
    if status not in KNOWN_STATUSES:
        raise ReceiptError(f"run: unknown status {status!r}")
    evidence = run.get("evidence")
    if evidence is None:
        evidence = []
    if not isinstance(evidence, list):
        raise ReceiptError("run: evidence must be a list")
    quotes = [_quote_from_evidence(item, i) for i, item in enumerate(evidence)]
    known_dollars, unknown_lines = _cost_summary(run.get("cost"))
    steps = run.get("steps")
    if not task_text.strip():
        raise ReceiptError("task text must be non-empty")

    tool: dict[str, Any] = {"name": TOOL_NAME, "version": tool_version}
    if llm_models:
        tool["llm_models"] = list(llm_models)

    task: dict[str, Any] = {"text": task_text}
    if start_url:
        task["start_url"] = start_url
    final_url = run.get("final_url")
    if isinstance(final_url, str) and final_url:
        task["final_url"] = final_url

    stamp = generated_at or datetime.now(tz=timezone.utc)
    receipt: dict[str, Any] = {
        "schemaVersion": SCHEMA_VERSION,
        "tool": tool,
        "task": task,
        "run_status": status,
        "citable": status == CITABLE_STATUS and len(quotes) > 0,
        "answer": run.get("answer") if isinstance(run.get("answer"), str) else None,
        "quotes": quotes,
        "cost_dollars": known_dollars,
        "cost_lines_unknown": unknown_lines,
        "steps": len(steps) if isinstance(steps, list) else 0,
        "generated_at": stamp.isoformat().replace("+00:00", "Z"),
    }
    if "data" in run and run["data"] is not None:
        receipt["data"] = run["data"]
    if source_path is not None:
        if source_bytes is None:
            raise ReceiptError("source_bytes is required when source_path is given")
        if source_path.startswith(("/", "\\")) or "\\" in source_path:
            raise ReceiptError("source_path must be a repo-relative POSIX path")
        receipt["source_run"] = {"path": source_path, "sha256": _sha256_bytes(source_bytes)}
    return _finalize(receipt)


def check_receipt(receipt: dict[str, Any]) -> list[str]:
    """Return human-readable issues. An empty list is a pass."""

    issues: list[str] = []
    if not isinstance(receipt, dict):
        return ["receipt must be a JSON object"]
    if receipt.get("schemaVersion") != SCHEMA_VERSION:
        issues.append(f"schemaVersion must be {SCHEMA_VERSION!r}")
    body = {k: v for k, v in receipt.items() if k not in HASHED_FIELDS_EXCLUDED}
    expected = _sha256_text(canonical_json(body))
    if receipt.get("receipt_sha256") != expected:
        issues.append("receipt_sha256 does not match canonical body")
    if receipt.get("receipt_id") != f"wer-{expected[:16]}":
        issues.append("receipt_id does not match receipt hash")
    status = receipt.get("run_status")
    if status not in KNOWN_STATUSES:
        issues.append(f"unknown run_status {status!r}")
    quotes = receipt.get("quotes")
    if not isinstance(quotes, list):
        issues.append("quotes must be a list")
        quotes = []
    for i, quote in enumerate(quotes):
        if not isinstance(quote, dict):
            issues.append(f"quotes[{i}] must be an object")
            continue
        text = quote.get("quote")
        if not isinstance(text, str) or not text:
            issues.append(f"quotes[{i}].quote must be a non-empty string")
            continue
        if quote.get("quote_sha256") != _sha256_text(text):
            issues.append(f"quotes[{i}].quote_sha256 does not match quote text")
        for key in ("url", "captured_at", "capture_sha256"):
            if not isinstance(quote.get(key), str) or not quote[key]:
                issues.append(f"quotes[{i}].{key} missing")
    citable = receipt.get("citable")
    should_be_citable = status == CITABLE_STATUS and len(quotes) > 0
    if citable is not should_be_citable:
        issues.append(
            f"citable={citable!r} but run_status={status!r} with {len(quotes)} quotes "
            f"implies citable={should_be_citable!r}"
        )
    return issues


def _read_json(path: pathlib.Path) -> tuple[Any, bytes]:
    raw = path.read_bytes()
    try:
        return json.loads(raw.decode("utf-8")), raw
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ReceiptError(f"{path}: not valid UTF-8 JSON ({exc})") from exc


def _cmd_build(args: argparse.Namespace) -> int:
    run, raw = _read_json(pathlib.Path(args.run_json))
    receipt = build_receipt(
        run,
        task_text=args.task,
        tool_version=args.tool_version,
        start_url=args.start_url,
        llm_models=args.llm_model or None,
        source_path=args.source_path,
        source_bytes=raw if args.source_path else None,
    )
    text = json.dumps(receipt, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    if args.out:
        pathlib.Path(args.out).write_text(text, encoding="utf-8")
        print(f"wrote {args.out} ({receipt['receipt_id']}, citable={receipt['citable']})")
    else:
        sys.stdout.write(text)
    return 0


def _cmd_check(args: argparse.Namespace) -> int:
    failures = 0
    for path_text in args.receipts:
        receipt, _ = _read_json(pathlib.Path(path_text))
        issues = check_receipt(receipt)
        if issues:
            failures += 1
            print(f"FAIL {path_text}")
            for issue in issues:
                print(f"  - {issue}")
        else:
            print(
                f"ok   {path_text} ({receipt.get('receipt_id')}, citable={receipt.get('citable')})"
            )
    return 1 if failures else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = parser.add_subparsers(dest="command", required=True)

    build = sub.add_parser("build", help="convert a fastbrowse --json result into a receipt")
    build.add_argument("run_json", help="path to the raw fastbrowse --json output")
    build.add_argument("--task", required=True, help="the task text given to fastbrowse")
    build.add_argument(
        "--tool-version", required=True, help="fastbrowse version that produced the run"
    )
    build.add_argument("--start-url", default=None)
    build.add_argument("--llm-model", action="append", help="model id used by the run (repeatable)")
    build.add_argument(
        "--source-path",
        default=None,
        help="repo-relative path where the raw run JSON is committed; hashed into the receipt",
    )
    build.add_argument("--out", default=None, help="write the receipt here instead of stdout")
    build.set_defaults(func=_cmd_build)

    check = sub.add_parser("check", help="re-derive hashes and validate one or more receipts")
    check.add_argument("receipts", nargs="+")
    check.set_defaults(func=_cmd_check)

    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except ReceiptError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
