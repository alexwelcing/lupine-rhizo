"""Acceptance tests for the assumption-link CI check."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CHECKER = ROOT / "tools" / "check_assumption_links.py"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.check_assumption_links import (  # noqa: E402, I001
    find_assumption_link_violations,
)


LEAN_REGISTRY = """\
def theoremInventory : List TheoremInventoryEntry := [
{ moduleName := "Example", declarationName := "linked", declarationKind := .theorem, epistemicGrade := .assuranceExported, contractId := some "claim.linked.v1" }
]
"""


def write_fixture(
    root: Path,
    *,
    lean_registry: str = LEAN_REGISTRY,
    bundle_references: list[dict[str, str]] | None = None,
    support_mode: str = "all",
) -> None:
    lean_path = (
        root
        / "lean-spec"
        / "OpenDistillationFactory"
        / "UniversalCorrection"
        / "Empirical"
        / "Registry.lean"
    )
    lean_path.parent.mkdir(parents=True, exist_ok=True)
    lean_path.write_text(lean_registry, encoding="utf-8")

    assumptions_path = root / "registry" / "assumptions.v1.json"
    assumptions_path.parent.mkdir(parents=True, exist_ok=True)
    assumptions_path.write_text(
        json.dumps(
            {
                "version": 1,
                "assumptions": [{"claim_id": "claim.linked.v1"}],
            }
        ),
        encoding="utf-8",
    )

    claims_path = root / "registry" / "claims"
    claims_path.mkdir(exist_ok=True)
    (claims_path / "claim.linked.v1.json").write_text(
        json.dumps(
            {
                "claim_id": "claim.linked.v1",
                "premises": [
                    {
                        "premise_id": "premise.linked",
                        "support_policy": {"mode": support_mode},
                        "bundle_references": (
                            bundle_references
                            if bundle_references is not None
                            else [{"bundle_id": "sha256:" + "1" * 64}]
                        ),
                    }
                ],
            }
        ),
        encoding="utf-8",
    )


class AssumptionLinkTests(unittest.TestCase):
    def test_assurance_export_without_requires_contract_fails(self) -> None:
        unlinked_registry = LEAN_REGISTRY.replace(
            'contractId := some "claim.linked.v1"', "contractId := none"
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_fixture(root, lean_registry=unlinked_registry)

            violations = find_assumption_link_violations(root)

        self.assertEqual(len(violations), 1)
        self.assertIn("Example.linked", violations[0])
        self.assertIn("@[requires(contract_id)]", violations[0])

    def test_parenthesized_assurance_grade_cannot_bypass_requires_check(self) -> None:
        unlinked_registry = LEAN_REGISTRY.replace(
            ".assuranceExported", "(.assuranceExported)"
        ).replace('contractId := some "claim.linked.v1"', "contractId := none")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_fixture(root, lean_registry=unlinked_registry)

            violations = find_assumption_link_violations(root)

        self.assertEqual(len(violations), 1)
        self.assertIn("Example.linked", violations[0])

    def test_unparseable_inventory_entry_fails_closed(self) -> None:
        malformed_registry = LEAN_REGISTRY.replace(
            "epistemicGrade := .assuranceExported, ", ""
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_fixture(root, lean_registry=malformed_registry)

            violations = find_assumption_link_violations(root)

        self.assertEqual(len(violations), 1)
        self.assertIn("cannot load theorem inventory", violations[0])

    def test_linked_assurance_export_and_supported_premise_pass(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_fixture(root)

            violations = find_assumption_link_violations(root)

        self.assertEqual(violations, [])

    def test_requires_contract_must_exist_in_assumption_registry(self) -> None:
        unknown_registry = LEAN_REGISTRY.replace("claim.linked.v1", "claim.unknown.v1")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_fixture(root, lean_registry=unknown_registry)

            violations = find_assumption_link_violations(root)

        self.assertEqual(len(violations), 1)
        self.assertIn("claim.unknown.v1", violations[0])
        self.assertIn("not present", violations[0])

    def test_premise_without_bundle_or_unsupported_tag_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_fixture(root, bundle_references=[])

            violations = find_assumption_link_violations(root)

        self.assertEqual(len(violations), 1)
        self.assertIn("premise.linked", violations[0])
        self.assertIn("bundle reference", violations[0])

    def test_malformed_truthy_bundle_reference_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_fixture(root, bundle_references=[{}])

            violations = find_assumption_link_violations(root)

        self.assertEqual(len(violations), 1)
        self.assertIn("premise.linked", violations[0])
        self.assertIn("valid bundle reference", violations[0])

    def test_explicitly_unsupported_premise_without_bundle_passes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_fixture(root, bundle_references=[], support_mode="unsupported")

            violations = find_assumption_link_violations(root)

        self.assertEqual(violations, [])

    def test_qualified_enum_syntax_for_grade_is_parsed(self) -> None:
        qualified_registry = LEAN_REGISTRY.replace(
            "epistemicGrade := .assuranceExported",
            "epistemicGrade := (.assuranceExported)",
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_fixture(root, lean_registry=qualified_registry)

            violations = find_assumption_link_violations(root)

        self.assertEqual(violations, [])

    def test_unparseable_grade_is_a_violation(self) -> None:
        bad_registry = LEAN_REGISTRY.replace(
            "epistemicGrade := .assuranceExported",
            "epistemicGrade := unknown",
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_fixture(root, lean_registry=bad_registry)

            violations = find_assumption_link_violations(root)

        self.assertEqual(len(violations), 1)
        self.assertIn("could not parse epistemicGrade", violations[0])

    def test_nested_braces_do_not_break_entry_parsing(self) -> None:
        nested_registry = """\
def theoremInventory : List TheoremInventoryEntry := [
{ moduleName := "Example", declarationName := "linked", declarationKind := .theorem, epistemicGrade := .assuranceExported, contractId := some "claim.linked.v1", extra := { nested := 1 } }
]
"""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_fixture(root, lean_registry=nested_registry)

            violations = find_assumption_link_violations(root)

        self.assertEqual(violations, [])

    def test_cli_fails_for_missing_requires_and_passes_when_linked(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_fixture(
                root,
                lean_registry=LEAN_REGISTRY.replace(
                    'contractId := some "claim.linked.v1"', "contractId := none"
                ),
            )
            rejected = subprocess.run(
                [sys.executable, str(CHECKER), "--root", str(root)],
                check=False,
                capture_output=True,
                text=True,
            )
            write_fixture(root)
            accepted = subprocess.run(
                [sys.executable, str(CHECKER), "--root", str(root)],
                check=False,
                capture_output=True,
                text=True,
            )

        self.assertEqual(rejected.returncode, 1)
        self.assertIn("assumption-link check failed", rejected.stderr)
        self.assertEqual(accepted.returncode, 0, accepted.stderr)
        self.assertIn("assumption-link check passed", accepted.stdout)

    def test_checked_in_registry_passes(self) -> None:
        self.assertEqual(find_assumption_link_violations(ROOT), [])

    def test_verify_workflow_runs_checker_for_relevant_pr_paths(self) -> None:
        workflow = (ROOT / ".github" / "workflows" / "verify.yml").read_text(
            encoding="utf-8"
        )

        self.assertIn("assumption-links:", workflow)
        self.assertIn("git diff --quiet", workflow)
        self.assertIn("-- lean-spec/ registry/", workflow)
        self.assertIn("python tools/check_assumption_links.py", workflow)
        self.assertIn("python/tests/test_check_assumption_links.py", workflow)


if __name__ == "__main__":
    unittest.main()
