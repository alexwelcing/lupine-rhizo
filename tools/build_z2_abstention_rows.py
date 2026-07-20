#!/usr/bin/env python3
"""Build the four Z2 abstention measurement rows (RFC 8785, hash-chained).

The Z2 spin-aware campaign cannot execute honestly: no declared available
model exposes an SOC / magnetocrystalline-anisotropy / Tc measurement path
(runner ROW_IDS are scalar energy/forces/stress-derived), no >=5-material
SOC/Tc reference panel exists, the target ClaimContract is absent, and Tc
has no preregistered metric. The frozen Z2 hypothesis h.z2.scalar-abstention
requires scalar-only rows to abstain. These rows record that abstention:
one `unsupported` row per declared available model, with zero cloud spend
and no fabricated measurement.

Reconstruction note: the original t_52df7aae workspace artifacts were lost
with the kanban scratch workspace (2026-07-19). This builder recreates the
described deliverable faithfully from repository state; the original
blocker document's SHA-256 (c0c0e31773fa06d51d7310ffe19de42a59e1db95870ac32636d31e1d5bb450c3)
is cited for the record in docs/campaigns/z2-abstention-audit.md.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import rfc8785

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "campaigns/v1/z2.campaign-manifest.v1.json"
OUT_DIR = ROOT / "data/candidates/z2"

MODELS = ("chgnet", "mace-mp-small", "mace-mp-medium", "mace-mpa-0-medium")
ABSTENTION_RATIONALE = (
    "No spin-orbit / non-collinear magnetocrystalline-anisotropy or Tc "
    "measurement path exists among the declared available models (runner rows "
    "are scalar energy/forces/stress-derived). Per frozen hypothesis "
    "h.z2.scalar-abstention, scalar-only rows abstain and cannot count as "
    "ranking successes."
)


def canonical_bytes(document: dict) -> bytes:
    try:
        return rfc8785.dumps(document)
    except (rfc8785.CanonicalizationError, TypeError) as error:
        raise ValueError(f"row is not RFC 8785 canonicalizable: {error}") from error


def content_hash(document: dict) -> str:
    return "sha256:" + hashlib.sha256(canonical_bytes(document)).hexdigest()


def build_rows() -> list[dict]:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    manifest_hash = manifest["content_hash"]
    if manifest.get("campaign_id") != "discovery.round-4.z2-magnetic-anisotropy.v1":
        raise ValueError("unexpected Z2 manifest")
    rows = []
    previous_hash = None
    for model_id in MODELS:
        row = {
            "campaign_manifest": "campaigns/v1/z2.campaign-manifest.v1.json",
            "campaign_manifest_hash": manifest_hash,
            "model_id": model_id,
            "metric": "magnetocrystalline_anisotropy_ranking",
            "value": None,
            "unit": None,
            "sample_count": 0,
            "epistemic_status": "unsupported",
            "acceptance_test": {
                "comparator": "not_evaluated",
                "outcome": "abstained",
                "reason": ABSTENTION_RATIONALE,
            },
            "scope": {
                "panel": None,
                "panel_reason": "no locked >=5-material SOC/Tc reference panel exists",
                "claim_contract": None,
                "claim_contract_reason": "registry/claims/discovery.z2.magnetic-anisotropy.v1.json is absent",
            },
            "cloud_executions": 0,
            "previous_row_hash": previous_hash,
        }
        row["row_hash"] = content_hash({k: v for k, v in row.items() if k != "row_hash"})
        rows.append(row)
        previous_hash = row["row_hash"]
    return rows


def rendered_outputs(rows: list[dict]) -> tuple[bytes, bytes]:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    measurements = b"".join(rfc8785.dumps(row).decode("utf-8").encode("utf-8") + b"\n" for row in rows)
    artifact_manifest = {
        "schema": "lupine.z2.abstention_artifact_manifest.v1",
        "generator": "tools/build_z2_abstention_rows.py",
        "campaign_manifest_hash": manifest["content_hash"],
        "row_count": len(rows),
        "chain_head": rows[0]["row_hash"],
        "chain_tail": rows[-1]["row_hash"],
        "artifacts": [
            {
                "path": "data/candidates/z2/measurements.jsonl",
                "sha256": "sha256:" + hashlib.sha256(measurements).hexdigest(),
            }
        ],
    }
    rendered_manifest = (json.dumps(artifact_manifest, indent=1, sort_keys=True) + "\n").encode(
        "utf-8"
    )
    return measurements, rendered_manifest


def main() -> int:
    check = "--check" in sys.argv
    rows = build_rows()
    measurements, rendered_manifest = rendered_outputs(rows)
    out = OUT_DIR / "measurements.jsonl"
    manifest_path = OUT_DIR / "artifact-manifest.json"
    if check:
        stale = []
        for path, payload in ((out, measurements), (manifest_path, rendered_manifest)):
            try:
                actual = path.read_bytes()
            except OSError:
                actual = None
            if actual != payload:
                stale.append(path.name)
        if stale:
            print(f"stale: {', '.join(stale)}; rebuild Z2 abstention rows", file=sys.stderr)
            return 1
        print("Z2 abstention rows are up to date")
        return 0
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out.write_bytes(measurements)
    manifest_path.write_bytes(rendered_manifest)
    print(json.dumps({"rows": len(rows), "chain_tail": rows[-1]["row_hash"]}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
