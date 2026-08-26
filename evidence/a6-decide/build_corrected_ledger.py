#!/usr/bin/env python3
"""Build the corrected A6 execution ledger without rewriting historical executions."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    source_path = ROOT / "a6_execution_ledger.original.json"
    output_path = ROOT / "a6_execution_ledger.json"
    ledger = json.loads(source_path.read_text())
    assert ledger["actual_billed_cost"] is None
    assert len(ledger["records"]) == 12

    excluded = 0
    eligible = 0
    for record in ledger["records"]:
        if record["source"] == "mptrj":
            record["frozen_decision_eligible"] = False
            record["evidence_status"] = "excluded_nonpreregistered_source"
            record["exclusion_reason"] = (
                "Historical execution used nimashoghi/mptrj train/0000.parquet, "
                "not the frozen MPtrj test source"
            )
            excluded += 1
        else:
            record["frozen_decision_eligible"] = True
            record["evidence_status"] = "retained_exact_hash_evidence"
            eligible += 1

    ledger["schema"] = "lupine.a6_decide.execution_ledger.v2"
    ledger["historical_execution_count"] = ledger.pop("execution_count")
    ledger["frozen_decision_eligible_execution_records"] = eligible
    ledger["excluded_nonpreregistered_execution_records"] = excluded
    ledger["source_correction"] = {
        "frozen_source_identity": "MPtrj test",
        "dataset": "nimashoghi/mptrj",
        "dataset_revision": "f88fbe46e16524223210654bad9e1b05a15c2adb",
        "resolved_split": "test",
        "parquet_url": (
            "https://huggingface.co/datasets/nimashoghi/mptrj/resolve/"
            "f88fbe46e16524223210654bad9e1b05a15c2adb/data/test-00000-of-00001.parquet"
        ),
        "parquet_sha256": "cb77ce289ba73357be0cc375df40631d0df0541e7120913cb2e89a17aae19add",
        "status": "inconclusive",
        "failed_gate": (
            "MPtrj test has 0 trajectory blocks with >= 8 eligible configurations; "
            "frozen minimum is 30 independently bootstrappable blocks with >= 8 "
            "configurations per retained block and >= 240 total configurations; "
            "deterministic sampling target is 50 blocks"
        ),
        "model_execution_launched": False,
        "model_execution_refusal": (
            "No conforming MPtrj test manifest exists under the frozen pre-inference information gate"
        ),
        "input_lock_sha256": sha256_file(ROOT / "manifests" / "input-lock.json"),
        "corrected_analysis_sha256": sha256_file(ROOT / "a6_decide_analysis.json"),
    }
    ledger["actual_billed_cost_status"] = (
        "unavailable: dataset discovery succeeded but billing-export table listing timed out; "
        "no billing row obtained and no dollar estimate substituted"
    )
    output_path.write_text(json.dumps(ledger, indent=2, sort_keys=True) + "\n")
    print(output_path)
    print(f"sha256={sha256_file(output_path)}")
    print(f"eligible_records={eligible} excluded_records={excluded}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
