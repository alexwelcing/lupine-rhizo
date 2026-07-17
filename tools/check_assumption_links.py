#!/usr/bin/env python3
"""Check that formal assurance exports and registry premises have receipts."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

LEAN_REGISTRY = Path(
    "lean-spec/OpenDistillationFactory/UniversalCorrection/Empirical/Registry.lean"
)
ASSUMPTION_REGISTRY = Path("registry/assumptions.v1.json")
CLAIMS_DIRECTORY = Path("registry/claims")
EPISTEMIC_GRADES = {
    "pureMathematical",
    "empiricallyConditional",
    "assuranceExported",
    "unsupportedOverScoped",
}

_INVENTORY_RE = re.compile(
    r"def\s+theoremInventory\s*:[^=]*:=\s*\[(?P<body>.*?)\]\s*\n",
    re.DOTALL,
)
_FIELD_RE = {
    "module": re.compile(r'moduleName\s*:=\s*"(?P<value>[^"]+)"'),
    "declaration": re.compile(r'declarationName\s*:=\s*"(?P<value>[^"]+)"'),
    "grade": re.compile(
        r"epistemicGrade\s*:=\s*\(?\s*(?P<value>\.?[A-Za-z_][\w.]*)\s*\)?"
    ),
    "contract": re.compile(
        r'contractId\s*:=\s*\(?\s*(?:some\s+"(?P<value>[^"]+)"|(?P<none>none))\s*\)?'
    ),
}


def _load_json(path: Path) -> dict[str, Any]:
    document = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise ValueError("expected a JSON object")
    return document


def _entry_bodies(inventory: str) -> list[str]:
    """Split Lean structure literals while respecting nesting and quoted strings."""
    entries: list[str] = []
    start: int | None = None
    depth = 0
    in_string = False
    escaped = False
    for index, character in enumerate(inventory):
        if in_string:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == '"':
                in_string = False
            continue
        if character == '"':
            in_string = True
        elif character == "{":
            if depth == 0:
                start = index + 1
            depth += 1
        elif character == "}":
            if depth == 0:
                raise ValueError("unmatched closing brace in theoremInventory")
            depth -= 1
            if depth == 0 and start is not None:
                entries.append(inventory[start:index])
                start = None
    if in_string or depth:
        raise ValueError("unterminated theoremInventory entry")
    if not entries:
        raise ValueError("theoremInventory has no entries")
    return entries


def _inventory_entries(source: str) -> list[dict[str, str | None]]:
    inventory = _INVENTORY_RE.search(source)
    if inventory is None:
        raise ValueError("could not find theoremInventory")
    entries: list[dict[str, str | None]] = []
    for index, body in enumerate(_entry_bodies(inventory.group("body")), start=1):
        fields: dict[str, str | None] = {}
        for name, pattern in _FIELD_RE.items():
            field = pattern.search(body)
            if field is None:
                raise ValueError(
                    f"theoremInventory entry {index} has missing or malformed {name}"
                )
            value = field.group("value")
            if name == "grade" and value is not None:
                value = value.rsplit(".", maxsplit=1)[-1]
                if value not in EPISTEMIC_GRADES:
                    raise ValueError(
                        f"theoremInventory entry {index} could not parse "
                        f"epistemicGrade {value!r}"
                    )
            fields[name] = value
        entries.append(fields)
    return entries


def find_assumption_link_violations(root: Path) -> list[str]:
    """Return human-readable violations beneath a repository root."""
    violations: list[str] = []

    assumptions_path = root / ASSUMPTION_REGISTRY
    try:
        assumptions = _load_json(assumptions_path)
        assumption_ids = {
            assumption["claim_id"]
            for assumption in assumptions.get("assumptions", [])
            if isinstance(assumption, dict) and isinstance(assumption.get("claim_id"), str)
        }
    except (OSError, json.JSONDecodeError, ValueError) as error:
        violations.append(f"{ASSUMPTION_REGISTRY}: cannot load assumption registry: {error}")
        assumption_ids = set()

    lean_path = root / LEAN_REGISTRY
    try:
        entries = _inventory_entries(lean_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        violations.append(f"{LEAN_REGISTRY}: cannot load theorem inventory: {error}")
        entries = []

    for entry in entries:
        qualified_name = ".".join(
            part for part in (entry["module"], entry["declaration"]) if part
        ) or "<unknown declaration>"
        if entry["grade"] is None:
            violations.append(
                f"{qualified_name}: could not parse epistemicGrade; cannot verify assurance export"
            )
            continue
        if entry["grade"] != "assuranceExported":
            continue
        contract_id = entry["contract"]
        if contract_id is None:
            violations.append(
                f"{qualified_name}: assurance-exported declaration lacks "
                "@[requires(contract_id)] (contractId := some \"...\")"
            )
        elif contract_id not in assumption_ids:
            violations.append(
                f"{qualified_name}: required contract {contract_id!r} is not present in "
                f"{ASSUMPTION_REGISTRY}"
            )

    claims_directory = root / CLAIMS_DIRECTORY
    try:
        claim_paths = sorted(claims_directory.glob("*.json"))
    except OSError as error:
        violations.append(f"{CLAIMS_DIRECTORY}: cannot list claim contracts: {error}")
        claim_paths = []

    if not claims_directory.is_dir():
        violations.append(f"{CLAIMS_DIRECTORY}: claim contract directory is missing")

    for claim_path in claim_paths:
        relative_path = claim_path.relative_to(root)
        try:
            claim = _load_json(claim_path)
        except (OSError, json.JSONDecodeError, ValueError) as error:
            violations.append(f"{relative_path}: cannot load claim contract: {error}")
            continue
        for premise in claim.get("premises", []):
            if not isinstance(premise, dict):
                violations.append(f"{relative_path}: premise must be a JSON object")
                continue
            premise_id = premise.get("premise_id", "<unknown premise>")
            references = premise.get("bundle_references")
            support_policy = premise.get("support_policy")
            unsupported = (
                isinstance(support_policy, dict)
                and support_policy.get("mode") == "unsupported"
            )
            valid_references = (
                isinstance(references, list)
                and bool(references)
                and all(
                    isinstance(reference, dict)
                    and isinstance(reference.get("bundle_id"), str)
                    and bool(reference["bundle_id"].strip())
                    for reference in references
                )
            )
            if not valid_references and not unsupported:
                violations.append(
                    f"{relative_path}: premise {premise_id!r} has no valid bundle reference "
                    "and is not explicitly tagged unsupported"
                )

    return violations


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=repo_root())
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    violations = find_assumption_link_violations(args.root.resolve())
    if violations:
        print("assumption-link check failed:", file=sys.stderr)
        for violation in violations:
            print(f"- {violation}", file=sys.stderr)
        return 1
    print("assumption-link check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
