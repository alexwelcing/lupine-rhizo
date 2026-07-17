#!/usr/bin/env python3
"""Materialize the derived assumption registry and its content lock."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


STATUS_LEVELS = {
    "unsupported": 0,
    "exploratory": 1,
    "descriptive": 2,
    "confirmatory": 3,
}
LIFECYCLE = ("unsupported", "provisional", "eligible", "active")
NEGATIVE_STATUS = "negative"


def canonical_bytes(document: Any) -> bytes:
    return json.dumps(
        document, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")


def content_hash(document: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_bytes(document)).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"cannot read JSON from {path}: {error}") from error
    if not isinstance(document, dict):
        raise ValueError(f"expected a JSON object in {path}")
    return document


def derive_premise_level(
    premise: dict[str, Any], evidence_by_id: dict[str, dict[str, Any]]
) -> tuple[int, list[dict[str, Any]]]:
    references = premise.get("bundle_references", [])
    if not references:
        return 0, []

    bundles = []
    for reference in references:
        bundle_id = reference["bundle_id"]
        try:
            bundles.append(evidence_by_id[bundle_id])
        except KeyError as error:
            raise ValueError(
                f"premise {premise.get('premise_id', '<unknown>')} references "
                f"missing EvidenceBundle {bundle_id}"
            ) from error

    if any(bundle["epistemic_status"] == NEGATIVE_STATUS for bundle in bundles):
        return -1, bundles

    levels = [STATUS_LEVELS[bundle["epistemic_status"]] for bundle in bundles]
    mode = premise["support_policy"]["mode"]
    if mode == "unsupported":
        return 0, bundles
    if mode == "all":
        return min(levels), bundles
    if mode == "any":
        return max(levels), bundles
    if mode == "at_least":
        minimum = premise["support_policy"]["minimum"]
        if minimum > len(levels):
            return 0, bundles
        return sorted(levels, reverse=True)[minimum - 1], bundles
    raise ValueError(f"unknown support policy mode {mode!r}")


def derive_assumption(
    claim: dict[str, Any], evidence_by_id: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    premise_levels = []
    referenced_bundles: dict[str, dict[str, Any]] = {}
    for premise in claim["premises"]:
        level, bundles = derive_premise_level(premise, evidence_by_id)
        premise_levels.append(level)
        for bundle in bundles:
            referenced_bundles[bundle["bundle_id"]] = bundle

    if any(level < 0 for level in premise_levels):
        status = "withdrawn"
        disposition = "refuted"
    else:
        level = min(premise_levels, default=0)
        status = LIFECYCLE[level]
        disposition = "unsupported" if status == "unsupported" else "supported"

    evidence = [
        {
            "bundle_id": bundle_id,
            "epistemic_status": bundle["epistemic_status"],
            "scope": bundle["scope"],
        }
        for bundle_id, bundle in sorted(referenced_bundles.items())
    ]
    return {
        "claim_id": claim["claim_id"],
        "claim_version": claim["version"],
        "claim_content_hash": claim["content_hash"],
        "statement": claim["statement"],
        "status": status,
        "disposition": disposition,
        "evidence": evidence,
    }


def build_documents(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    claim_paths = sorted((root / "registry" / "claims").glob("*.json"))
    evidence_paths = sorted((root / "evidence" / "v1" / "examples").glob("*.json"))

    evidence_by_id: dict[str, dict[str, Any]] = {}
    for path in evidence_paths:
        bundle = load_json(path)
        bundle_id = bundle["bundle_id"]
        if bundle_id in evidence_by_id:
            raise ValueError(f"duplicate EvidenceBundle ID {bundle_id}")
        expected_id = content_hash(
            {key: value for key, value in bundle.items() if key != "bundle_id"}
        )
        if bundle_id != expected_id:
            raise ValueError(f"non-canonical EvidenceBundle ID in {path}")
        evidence_by_id[bundle_id] = bundle

    claims = []
    seen_claim_ids = set()
    for path in claim_paths:
        claim = load_json(path)
        claim_id = claim["claim_id"]
        if claim_id in seen_claim_ids:
            raise ValueError(f"duplicate ClaimContract ID {claim_id}")
        seen_claim_ids.add(claim_id)
        expected_hash = content_hash(
            {key: value for key, value in claim.items() if key != "content_hash"}
        )
        if claim["content_hash"] != expected_hash:
            raise ValueError(f"non-canonical ClaimContract content_hash in {path}")
        claims.append(claim)

    registry = {
        "version": 1,
        "assumptions": [
            derive_assumption(claim, evidence_by_id)
            for claim in sorted(claims, key=lambda item: item["claim_id"])
        ],
    }
    lock = {
        "version": 1,
        "artifacts": {
            "registry/assumptions.v1.json": {"content_hash": content_hash(registry)}
        },
        "inputs": {
            "claim_contracts": [
                {
                    "claim_id": claim["claim_id"],
                    "content_hash": claim["content_hash"],
                }
                for claim in sorted(claims, key=lambda item: item["claim_id"])
            ],
            "evidence_bundles": sorted(evidence_by_id),
        },
    }
    return registry, lock


def rendered(document: dict[str, Any]) -> str:
    return json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def materialize(root: Path, output_root: Path, check: bool) -> bool:
    registry, lock = build_documents(root)
    outputs = {
        output_root / "registry" / "assumptions.v1.json": rendered(registry),
        output_root / "registry" / "snapshots" / "current.lock.json": rendered(lock),
    }
    stale = []
    for path, expected in outputs.items():
        if check:
            try:
                actual = path.read_text(encoding="utf-8")
            except OSError:
                actual = None
            if actual != expected:
                stale.append(path)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(expected, encoding="utf-8")
    if stale:
        for path in stale:
            print(f"stale generated file: {path}", file=sys.stderr)
        print("run tools/generate_assumptions.py to refresh", file=sys.stderr)
        return False
    return True


def repo_root() -> Path:
    """Return the repository root where this script lives under tools/."""
    return Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=repo_root())
    parser.add_argument("--output-root", type=Path)
    parser.add_argument(
        "--check", action="store_true", help="fail if generated files differ"
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = args.root.resolve()
    output_root = (args.output_root or root).resolve()
    try:
        return 0 if materialize(root, output_root, args.check) else 1
    except (KeyError, TypeError, ValueError) as error:
        print(f"generation failed: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
