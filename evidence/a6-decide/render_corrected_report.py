#!/usr/bin/env python3
"""Render the corrected, fail-closed A6-DECIDE report from exact artifacts."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SOURCE_LABELS = {
    "matpes-pbe-2025.2": "MatPES-PBE-2025.2",
    "omat24-validation-aimd-pbe-1000-nvt": "OMat24 validation AIMD PBE-1000 NVT",
}
PAIR_LABELS = {
    "chgnet|m3gnet": "CHGNet / M3GNet",
    "chgnet|mace-mp-small": "CHGNet / MACE-MP-small",
    "m3gnet|mace-mp-small": "M3GNet / MACE-MP-small",
}


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def span(values: list[float]) -> str:
    return f"{min(values):.6f}–{max(values):.6f}"


def main() -> int:
    analysis = json.loads((ROOT / "a6_decide_analysis.json").read_text())
    ledger = json.loads((ROOT / "a6_execution_ledger.json").read_text())
    lock = json.loads((ROOT / "manifests" / "input-lock.json").read_text())
    mptrj = analysis["sources"]["mptrj"]["integrity"]
    assert analysis["decision"]["verdict"] == "INCONCLUSIVE"
    assert ledger["actual_billed_cost"] is None
    assert mptrj["source_identity"]["resolved_split"] == "test"

    rows: list[str] = []
    for source in SOURCE_LABELS:
        runs = analysis["sources"][source]["seed_analyses"]
        first = runs[0]
        for pair in PAIR_LABELS:
            observed = first["pairs"][pair]["field_cos"]["observed"]
            null_means = [run["pairs"][pair]["field_cos"]["null"]["mean"] for run in runs]
            q025 = [run["pairs"][pair]["field_cos"]["bootstrap"]["q025"] for run in runs]
            holm = [run["pairs"][pair]["field_cos"]["holm_adjusted_p"] for run in runs]
            passed = all(run["pairs"][pair]["field_cos"]["passes_primary_pair_rule"] for run in runs)
            rows.append(
                f"| {SOURCE_LABELS[source]} | {PAIR_LABELS[pair]} | {observed:.6f} | "
                f"{span(null_means)} | {span(q025)} | {holm[0]:.8f} | {'yes' if passed else 'no'} |"
            )

    text = f"""# A6-DECIDE corrected source remediation

## Verdict

**INCONCLUSIVE under the frozen preregistered rule.**

The actual preregistered **MPtrj test** source exists, but it fails the mandatory pre-inference trajectory information gate. The pinned test parquet contains 10,273 rows. After the frozen schema, element, atom-count, finite-label, and nonzero-force filters, it has {mptrj['valid_configurations']:,} valid configurations across {mptrj['valid_blocks']:,} task/trajectory IDs; no block has the required eight configurations, and the observed maximum is {mptrj['maximum_valid_configurations_per_block']}. Therefore zero blocks are eligible: the source fails the frozen minimum of 30 independently bootstrappable blocks, at least 8 configurations per retained block, and at least 240 total configurations. It also cannot reach the deterministic 50-block × 8-configuration sampling target, so no MPtrj test model execution was launched.

OMat24 and MatPES retain their exact reviewed manifests and raw model outputs and still pass all three pairs at every seed. They do not rescue the global verdict because the frozen rule requires every source/integrity gate to pass before a support or scope-truncating verdict. The prior MPtrj train-shard result is excluded, not relabeled.

## Corrected source identity and exact failed gate

- Frozen identity: `MPtrj test`.
- Dataset: `nimashoghi/mptrj`.
- Pinned revision: `f88fbe46e16524223210654bad9e1b05a15c2adb`.
- Resolved split/file: `test` / `data/test-00000-of-00001.parquet`.
- Parquet SHA-256: `{lock['sources']['mptrj']['parquet_sha256']}`.
- Input-lock SHA-256: `{sha256_file(ROOT / 'manifests' / 'input-lock.json')}`.
- Failed gate: {mptrj['failed_gate']}.

This is a source/information refusal, not a negative model result. Running the three-model panel on a hand-made nonconforming subset would violate the frozen gate and was not done.

## Frozen decision rule

The preregistration remains unchanged: each source must provide at least 30 independently bootstrappable blocks, at least 8 configurations per retained block, and at least 240 total configurations; 50 blocks × 8 configurations is the deterministic sampling target. The primary endpoint is `field_cos`; independent Haar SO(3) rotations are applied per model × configuration; 5,000 null and 2,000 trajectory/material-block bootstrap replicates run at seeds 42, 1729, and 20260803; Holm correction is within source; pair pass requires adjusted p <= 0.05 and bootstrap q025 above the geometry-null mean; source pass requires at least two pairs. Final support requires OMat24 plus MPtrj or MatPES, with all information/integrity gates and seed-stability gates satisfied. Otherwise the verdict is `INCONCLUSIVE` with the failed gate.

## Retained exact-hash evidence

The three-model panel is retained on MatPES and OMat24. Their manifests are byte-identical to the independently reviewed set:

- MatPES manifest SHA-256: `{lock['sources']['matpes-pbe-2025.2']['manifest_sha256']}`.
- OMat24 manifest SHA-256: `{lock['sources']['omat24-validation-aimd-pbe-1000-nvt']['manifest_sha256']}`.

| source | model pair | observed | null mean range | bootstrap q025 range | Holm p (all seeds) | pair passes |
|---|---|---:|---:|---:|---:|---|
{chr(10).join(rows)}

Both retained sources remain seed-stable and pass 3/3 pairs. These retained results are subordinate to the global `INCONCLUSIVE` verdict because MPtrj test fails its information gate.

## Excluded MPtrj train-shard diagnostic

The historical `train/0000.parquet` executions and their hashes remain in the corrected ledger with `evidence_status: excluded_nonpreregistered_source` and `frozen_decision_eligible: false`. The previously observed CHGNet/M3GNet bootstrap heterogeneity is reproducible for that excluded train shard, but it is **not** evidence about MPtrj test and is not used in the corrected decision.

## Execution and cost ledger

- Historical Cloud Run records preserved: {ledger['historical_execution_count']}.
- Retained frozen-decision-eligible MatPES/OMat records: {ledger['frozen_decision_eligible_execution_records']}.
- Excluded MPtrj train-shard records: {ledger['excluded_nonpreregistered_execution_records']}.
- New MPtrj test model executions: 0, because the pre-inference source gate yielded no conforming manifest.
- Actual billed cost: unavailable (`null`); no dollar estimate, substitute, or derived dollar claim is provided.

## Reproducibility and verification

- Build source lock/manifests: `python3 build_a6_manifests.py`.
- Analyze retained evidence and failed source gate: `python3 analyze_a6_decide.py`.
- Mechanical verification: `python3 verify_a6_decide.py`.
- Repository-owned retained-manifest validation: `PYTHONPATH=/home/alex/Dev/lupine/lupine-rhizo/python python3 run_repository_validator.py`.
- Corrected analysis SHA-256: `{sha256_file(ROOT / 'a6_decide_analysis.json')}`.
- Corrected execution ledger SHA-256: `{sha256_file(ROOT / 'a6_execution_ledger.json')}`.

No preregistration rewrite, canonical/public claim, repository commit, merge, deployment, or publication was performed.
"""
    output = ROOT / "report_a6_decide_corrected.md"
    output.write_text(text)
    print(output)
    print(f"sha256={sha256_file(output)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
