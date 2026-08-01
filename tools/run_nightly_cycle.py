#!/usr/bin/env python3
"""Run the ingest → assumptions → runtime-gate stages of evidence-nightly."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

TOOLS = Path(__file__).resolve().parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from atlas_theorem_sync import compile_gate_manifest  # noqa: E402
from generate_assumptions import materialize, rendered  # noqa: E402
from ingest_campaign_results import ingest  # noqa: E402


def run_cycle(
    *, root: Path, campaigns: list[dict[str, Path]], output_dir: Path
) -> dict[str, Any]:
    """Execute all repository-local nightly stages and materialize review artifacts."""
    root = root.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    bundle_ids: list[str] = []
    for campaign in campaigns:
        bundle_ids.extend(
            ingest(
                root,
                Path(campaign["manifest"]).resolve(),
                Path(campaign["measurements"]).resolve(),
            )
        )
    if not materialize(root, root, check=False):
        raise ValueError("assumption registry materialization failed")
    theorem_registry_path = root / "config" / "atlas_theorem_registry.v1.json"
    theorem_registry = json.loads(theorem_registry_path.read_text(encoding="utf-8"))
    proof_revision = theorem_registry["authority"]["proof_revision"]
    theorem_evidence_path = root / "config" / f"atlas_theorem_sync.{proof_revision[:7]}.json"
    if not theorem_evidence_path.is_file():
        raise ValueError("missing theorem build evidence for the reviewed registry authority")
    gates = compile_gate_manifest(
        root / "registry" / "assumptions.v1.json",
        root / "registry" / "snapshots" / "current.lock.json",
        root / "registry" / "claims",
        root / "evidence" / "v1" / "examples",
        theorem_registry_path,
        theorem_evidence_path,
    )
    result = {"ingested_bundle_ids": sorted(set(bundle_ids))}
    (output_dir / "ingested-bundles.json").write_text(rendered(result), encoding="utf-8")
    (output_dir / "runtime-gates.json").write_text(rendered(gates), encoding="utf-8")
    return result


def _load_cycle(path: Path) -> list[dict[str, Path]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload.get("campaigns") if isinstance(payload, dict) else payload
    if not isinstance(rows, list) or not rows:
        raise ValueError("nightly cycle must contain at least one campaign")
    base = path.parent
    campaigns = []
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("manifest"), str) or not isinstance(row.get("measurements"), str):
            raise ValueError("each nightly campaign requires manifest and measurements paths")
        campaigns.append(
            {
                "manifest": (base / row["manifest"]).resolve(),
                "measurements": (base / row["measurements"]).resolve(),
            }
        )
    return campaigns


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--cycle", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    result = run_cycle(
        root=args.root,
        campaigns=_load_cycle(args.cycle.resolve()),
        output_dir=args.output_dir.resolve(),
    )
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
