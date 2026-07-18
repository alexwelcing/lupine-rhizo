#!/usr/bin/env python3
"""Lint public correction-scope claims against registered ClaimContracts."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Iterable
from pathlib import Path
from typing import Any

CLAIMS_DIRECTORY = Path("registry/claims")
DEFAULT_PUBLICATION_PATHS = (
    Path("paper/gates-licenses-paper/manuscript.tex"),
    Path("paper/gates-licenses-paper/manuscript.md"),
)

_CONTRACT_RE = re.compile(r"ClaimContract:\s*([a-z0-9][a-z0-9._-]*)", re.IGNORECASE)
_STATUS_RE = re.compile(r"ClaimStatus:\s*(exploratory|withdrawn)\b", re.IGNORECASE)
_CORRECTION_RE = re.compile(
    r"\b(?:correction|corrections|corrected|repair|de-bias)\b", re.IGNORECASE
)
_SCOPE_RE = re.compile(
    r"\b(?:scope|same[- ]class|cross[- ]class|universal|properties?|"
    r"lattice[- ]constant|bulk modulus|everywhere else)\b|(?:B|a)[_\\]?0",
    re.IGNORECASE,
)
_ASSERTION_RE = re.compile(
    r"\b(?:improv\w*|beat\w*|transfer\w*|validat\w*|safe\w*|licens\w*|"
    r"allow\w*|appl(?:y|ies|ied)|deny|denies|denied|abstain\w*|"
    r"unsupported|withdrawn|worsen\w*|harm\w*|shrinks?|strictly smaller)\b",
    re.IGNORECASE,
)
_B0_RE = re.compile(r"\bB[_\\]?0\b|bulk modulus", re.IGNORECASE)
_B0_IMPROVEMENT_RE = re.compile(
    r"\b(?:improv\w*|beat\w*|help\w*|transfer\w*|correctable|"
    r"reduces?|lower\w*|shrinks?|strictly smaller)\b",
    re.IGNORECASE,
)
_B0_NEGATED_RE = re.compile(
    r"\bno\s+correction\s+claim[^.]{0,200}\bB[_\\]?0\b|"
    r"\bno\s+B[_\\]?0\b[^.]{0,120}\b(?:claim|license)",
    re.IGNORECASE,
)


def _load_json(path: Path) -> dict[str, Any]:
    document = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise ValueError("expected a JSON object")
    return document


def _load_contracts(root: Path) -> tuple[dict[str, dict[str, Any]], list[str]]:
    contracts: dict[str, dict[str, Any]] = {}
    violations: list[str] = []
    claims_directory = root / CLAIMS_DIRECTORY
    if not claims_directory.is_dir():
        return {}, [f"{CLAIMS_DIRECTORY}: ClaimContract directory is missing"]

    for path in sorted(claims_directory.glob("*.json")):
        relative_path = path.relative_to(root)
        try:
            contract = _load_json(path)
        except (OSError, json.JSONDecodeError, ValueError) as error:
            violations.append(f"{relative_path}: cannot load ClaimContract: {error}")
            continue
        claim_id = contract.get("claim_id")
        if not isinstance(claim_id, str) or not claim_id:
            violations.append(f"{relative_path}: ClaimContract has no claim_id")
            continue
        contracts[claim_id] = contract
    return contracts, violations


def _blocks(text: str) -> Iterable[tuple[int, str]]:
    """Yield blank-line-delimited prose blocks with their first line number."""
    lines = text.splitlines()
    start: int | None = None
    block: list[str] = []
    for line_number, line in enumerate(lines, start=1):
        if line.strip():
            if start is None:
                start = line_number
            block.append(line)
        elif block:
            assert start is not None
            yield start, "\n".join(block)
            start = None
            block = []
    if block:
        assert start is not None
        yield start, "\n".join(block)


def _is_scope_claim(block: str) -> bool:
    return bool(
        _CORRECTION_RE.search(block) and _SCOPE_RE.search(block) and _ASSERTION_RE.search(block)
    )


def _is_b0_improvement_claim(block: str) -> bool:
    if not _CORRECTION_RE.search(block) or _B0_NEGATED_RE.search(block):
        return False
    b0_mentions = list(_B0_RE.finditer(block))
    improvements = list(_B0_IMPROVEMENT_RE.finditer(block))
    return any(
        abs(b0.start() - improvement.start()) <= 160
        for b0 in b0_mentions
        for improvement in improvements
    )


def _contract_is_active(contract: dict[str, Any]) -> bool:
    classification = contract.get("classification")
    bindings = contract.get("bindings")
    publication = bindings.get("publication") if isinstance(bindings, dict) else None
    return bool(
        isinstance(classification, dict)
        and classification.get("assurance") == "active"
        and isinstance(publication, dict)
        and publication.get("status") == "bound"
    )


def _display_path(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def find_publication_claim_violations(
    root: Path,
    *,
    publication_paths: Iterable[Path] | None = None,
) -> list[str]:
    """Return correction-scope claims lacking an active contract or status marker."""
    root = root.resolve()
    contracts, violations = _load_contracts(root)
    paths = publication_paths if publication_paths is not None else DEFAULT_PUBLICATION_PATHS

    for supplied_path in paths:
        path = supplied_path if supplied_path.is_absolute() else root / supplied_path
        display_path = _display_path(path, root)
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as error:
            violations.append(f"{display_path}: cannot read publication: {error}")
            continue

        for line_number, block in _blocks(text):
            is_b0_improvement = _is_b0_improvement_claim(block)
            if not is_b0_improvement and not _is_scope_claim(block):
                continue
            if _STATUS_RE.search(block):
                continue

            contract_match = _CONTRACT_RE.search(block)
            contract_id = contract_match.group(1) if contract_match else None
            if is_b0_improvement:
                violations.append(
                    f"{display_path}:{line_number}: unlicensed B0 improvement language; "
                    "B0 improvement has no active ClaimContract"
                )
                continue
            if contract_id is None:
                violations.append(
                    f"{display_path}:{line_number}: correction-scope claim must reference "
                    "an active ClaimContract or use ClaimStatus: exploratory/withdrawn"
                )
                continue
            contract = contracts.get(contract_id)
            if contract is None:
                violations.append(
                    f"{display_path}:{line_number}: referenced ClaimContract "
                    f"{contract_id!r} does not exist"
                )
            elif not _contract_is_active(contract):
                violations.append(
                    f"{display_path}:{line_number}: referenced ClaimContract "
                    f"{contract_id!r} is not active and publication-bound"
                )

    return violations


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=repo_root())
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        help="publication files to scan (defaults to the gates/licenses manuscript sources)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    paths = args.paths or None
    violations = find_publication_claim_violations(args.root.resolve(), publication_paths=paths)
    if violations:
        print("publication ClaimContract check failed:", file=sys.stderr)
        for violation in violations:
            print(f"- {violation}", file=sys.stderr)
        return 1
    print("publication ClaimContract check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
