"""Acceptance tests for the publication ClaimContract linter."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = Path(__file__).parent / "fixtures" / "publication_claims"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.check_publication_claims import (  # noqa: E402, I001
    find_publication_claim_violations,
)


class PublicationClaimTests(unittest.TestCase):
    def test_synthetic_b0_improvement_overclaim_fails(self) -> None:
        violations = find_publication_claim_violations(
            ROOT,
            publication_paths=[FIXTURES / "b0_overclaim.md"],
        )

        self.assertEqual(len(violations), 1)
        self.assertIn("B0", violations[0])
        self.assertIn("unlicensed B0 improvement", violations[0])

    def test_b0_improvement_synonyms_cannot_bypass_scope_claim_detection(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            publication = Path(directory) / "b0-synonyms.md"
            for verb in ("reduces", "lowers", "helps"):
                with self.subTest(verb=verb):
                    publication.write_text(
                        f"The B0 correction {verb} prediction error.\n",
                        encoding="utf-8",
                    )

                    violations = find_publication_claim_violations(
                        ROOT, publication_paths=[publication]
                    )

                    self.assertEqual(len(violations), 1)
                    self.assertIn("unlicensed B0 improvement", violations[0])

    def test_active_claim_contract_licenses_scope_claim(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            publication = Path(directory) / "licensed.md"
            publication.write_text(
                "<!-- ClaimContract: correction.same_class.a0.v1 -->\n"
                "Within the registered same-class scope, the correction improves a0 error.\n",
                encoding="utf-8",
            )

            violations = find_publication_claim_violations(ROOT, publication_paths=[publication])

        self.assertEqual(violations, [])

    def test_exploratory_scope_claim_is_explicitly_allowed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            publication = Path(directory) / "exploratory.md"
            publication.write_text(
                "<!-- ClaimStatus: exploratory -->\n"
                "A universal correction may improve B0 in future trials.\n",
                encoding="utf-8",
            )

            violations = find_publication_claim_violations(ROOT, publication_paths=[publication])

        self.assertEqual(violations, [])

    def test_withdrawn_contract_does_not_license_positive_claim(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            publication = Path(directory) / "withdrawn-contract.md"
            publication.write_text(
                "<!-- ClaimContract: correction.b0.v1 -->\n"
                "The B0 correction improves predictions in the registered scope.\n",
                encoding="utf-8",
            )

            violations = find_publication_claim_violations(ROOT, publication_paths=[publication])

        self.assertEqual(len(violations), 1)
        self.assertIn("no active ClaimContract", violations[0])

    def test_checked_in_publication_passes(self) -> None:
        self.assertEqual(find_publication_claim_violations(ROOT), [])

    def test_verify_workflow_runs_checker_and_tests(self) -> None:
        workflow = (ROOT / ".github" / "workflows" / "verify.yml").read_text(encoding="utf-8")

        self.assertIn("python/tests/test_check_publication_claims.py", workflow)
        self.assertIn("python tools/check_publication_claims.py", workflow)


if __name__ == "__main__":
    unittest.main()
