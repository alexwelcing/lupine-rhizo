from __future__ import annotations

import copy
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
import web_evidence_receipt as wer

pytestmark = pytest.mark.unit

STAMP = datetime(2026, 9, 21, 6, 0, tzinfo=timezone.utc)

# Shape mirrors fastbrowse 0.4.x `RunResult` as serialized by `--json`:
# status / answer / data / evidence[] / steps[] / cost.lines[] / final_url.
SAMPLE_RUN = {
    "status": "complete",
    "answer": "The default environment is Lean v4.33.1.",
    "data": {"lean_default": "v4.33.1"},
    "evidence": [
        {
            "source_id": "src-1",
            "url": "https://prove2.me/faq",
            "frame_id": None,
            "captured_at": "2026-09-21T05:41:59Z",
            "capture_sha256": "a" * 64,
            "start": 120,
            "end": 231,
            "quote": (
                "Three pinned environments are currently supported, Lean 4 v4.33.1 "
                "(the default for new theorems), v4.30.0, and v4.29.0-rc3."
            ),
        }
    ],
    "steps": [
        {
            "index": 0,
            "operation": "navigate",
            "decided_by": "code",
            "outcome": "ok",
            "url": "https://prove2.me/faq",
            "duration_ms": 900,
        }
    ],
    "cost": {
        "lines": [
            {
                "component": "llm",
                "basis": "tokens",
                "dollars": 0.0021,
                "purpose": "read",
                "input_tokens": 5000,
                "output_tokens": 200,
            },
            {"component": "jev", "basis": "calls", "dollars": 0.0004},
            {"component": "browser", "basis": "seconds", "dollars": None, "seconds": 12.0},
        ]
    },
    "artifacts": [],
    "error": None,
    "final_url": "https://prove2.me/faq",
}


def _build(run=SAMPLE_RUN, **overrides):
    kwargs = {
        "task_text": "Which Lean versions does Prove2Me support?",
        "tool_version": "0.4.2",
        "start_url": "https://prove2.me/faq",
        "llm_models": ["google/gemini-3.8-flash"],
        "generated_at": STAMP,
    }
    kwargs.update(overrides)
    return wer.build_receipt(run, **kwargs)


def test_complete_run_with_quotes_is_citable_and_hashes_quote() -> None:
    receipt = _build()

    assert receipt["schemaVersion"] == "web-evidence-receipt.v1"
    assert receipt["citable"] is True
    assert receipt["run_status"] == "complete"
    quote = receipt["quotes"][0]
    assert quote["quote_sha256"] == hashlib.sha256(quote["quote"].encode("utf-8")).hexdigest()
    assert quote["span"] == {"start": 120, "end": 231}
    assert quote["url"] == "https://prove2.me/faq"
    assert receipt["task"]["final_url"] == "https://prove2.me/faq"
    assert receipt["tool"] == {
        "name": "fastbrowse",
        "version": "0.4.2",
        "llm_models": ["google/gemini-3.8-flash"],
    }


def test_cost_sums_known_dollars_and_counts_unknown_lines() -> None:
    receipt = _build()

    assert receipt["cost_dollars"] == pytest.approx(0.0025)
    assert receipt["cost_lines_unknown"] == 1
    assert receipt["steps"] == 1


def test_receipt_hash_is_deterministic_and_checks_clean() -> None:
    first = _build()
    second = _build()

    assert first == second
    assert first["receipt_id"] == f"wer-{first['receipt_sha256'][:16]}"
    assert wer.check_receipt(first) == []


def test_unverified_run_is_never_citable() -> None:
    run = copy.deepcopy(SAMPLE_RUN)
    run["status"] = "unverified"

    receipt = _build(run)

    assert receipt["citable"] is False
    assert wer.check_receipt(receipt) == []


def test_complete_run_without_quotes_is_not_citable() -> None:
    run = copy.deepcopy(SAMPLE_RUN)
    run["evidence"] = []

    receipt = _build(run)

    assert receipt["citable"] is False


def test_edited_quote_fails_check() -> None:
    receipt = _build()
    tampered = copy.deepcopy(receipt)
    tampered["quotes"][0]["quote"] = tampered["quotes"][0]["quote"].replace("v4.33.1", "v4.29.0")

    issues = wer.check_receipt(tampered)

    assert any("quote_sha256" in issue for issue in issues)
    assert any("receipt_sha256" in issue for issue in issues)


def test_flipping_citable_by_hand_fails_check() -> None:
    receipt = _build()
    receipt["run_status"] = "blocked"  # body changed -> hash mismatch, and citable now inconsistent

    issues = wer.check_receipt(receipt)

    assert any("receipt_sha256" in issue for issue in issues)
    assert any("citable=True" in issue for issue in issues)


def test_unknown_status_and_missing_quote_fields_are_rejected() -> None:
    bad_status = copy.deepcopy(SAMPLE_RUN)
    bad_status["status"] = "done"
    with pytest.raises(wer.ReceiptError, match="unknown status"):
        _build(bad_status)

    missing_url = copy.deepcopy(SAMPLE_RUN)
    del missing_url["evidence"][0]["url"]
    with pytest.raises(wer.ReceiptError, match="url"):
        _build(missing_url)

    short_hash = copy.deepcopy(SAMPLE_RUN)
    short_hash["evidence"][0]["capture_sha256"] = "abc"
    with pytest.raises(wer.ReceiptError, match="capture_sha256"):
        _build(short_hash)


def test_source_run_is_hashed_and_must_be_repo_relative() -> None:
    raw = json.dumps(SAMPLE_RUN).encode("utf-8")
    receipt = _build(source_path="data/web_evidence/raw/run.json", source_bytes=raw)

    assert receipt["source_run"] == {
        "path": "data/web_evidence/raw/run.json",
        "sha256": hashlib.sha256(raw).hexdigest(),
    }
    with pytest.raises(wer.ReceiptError, match="repo-relative"):
        _build(source_path="/abs/run.json", source_bytes=raw)


def test_cli_build_then_check_roundtrip(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    run_path = tmp_path / "run.json"
    run_path.write_text(json.dumps(SAMPLE_RUN), encoding="utf-8")
    out_path = tmp_path / "receipt.json"

    rc = wer.main(
        [
            "build",
            str(run_path),
            "--task",
            "Which Lean versions does Prove2Me support?",
            "--tool-version",
            "0.4.2",
            "--out",
            str(out_path),
        ]
    )
    assert rc == 0
    receipt = json.loads(out_path.read_text(encoding="utf-8"))
    assert receipt["citable"] is True

    rc = wer.main(["check", str(out_path)])
    assert rc == 0
    assert "ok" in capsys.readouterr().out

    receipt["quotes"][0]["quote"] += " (edited)"
    out_path.write_text(json.dumps(receipt), encoding="utf-8")
    assert wer.main(["check", str(out_path)]) == 1
