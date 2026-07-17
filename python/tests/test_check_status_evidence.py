"""Acceptance tests for the anti-laundering status/evidence check."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tools.check_status_evidence import find_unbacked_status_changes


ROOT = Path(__file__).resolve().parents[2]
CHECKER = ROOT / "tools" / "check_status_evidence.py"
OLD_HASH = "sha256:" + "1" * 64
NEW_HASH = "sha256:" + "2" * 64


def registry(status: str, hashes: list[str]) -> dict:
    return {
        "version": 1,
        "assumptions": [
            {
                "claim_id": "claim.example.v1",
                "status": status,
                "assurance": status,
                "evidence": [{"bundle_id": bundle_hash} for bundle_hash in hashes],
            }
        ],
    }


def events(status: str, hashes: list[str]) -> dict:
    return {
        "status_events": [
            {
                "status_event_id": index + 1,
                "entity_id": "claim.example.v1",
                "to_status": status,
                "evidence_bundle_id": bundle_hash,
            }
            for index, bundle_hash in enumerate(hashes)
        ]
    }


class AntiLaunderingTests(unittest.TestCase):
    def test_registry_status_change_without_new_bundle_fails(self) -> None:
        violations = find_unbacked_status_changes(
            registry("provisional", [OLD_HASH]),
            registry("active", [OLD_HASH]),
            source="registry/assumptions.v1.json",
        )

        self.assertEqual(len(violations), 1)
        self.assertIn("claim.example.v1", violations[0])
        self.assertIn("no new EvidenceBundle hash", violations[0])

    def test_registry_status_change_with_new_bundle_passes(self) -> None:
        violations = find_unbacked_status_changes(
            registry("provisional", [OLD_HASH]),
            registry("active", [OLD_HASH, NEW_HASH]),
            source="registry/assumptions.v1.json",
        )

        self.assertEqual(violations, [])

    def test_d1_status_event_change_without_new_bundle_fails(self) -> None:
        before = events("exploratory", [OLD_HASH])
        after = {
            "status_events": before["status_events"]
            + [
                {
                    "status_event_id": 2,
                    "entity_id": "claim.example.v1",
                    "to_status": "confirmatory",
                    "evidence_bundle_id": OLD_HASH,
                }
            ]
        }

        violations = find_unbacked_status_changes(
            before, after, source="D1 status_event"
        )

        self.assertEqual(len(violations), 1)
        self.assertIn("status", violations[0])

    def test_d1_status_event_change_with_new_bundle_passes(self) -> None:
        before = events("exploratory", [OLD_HASH])
        after = {
            "status_events": before["status_events"]
            + [
                {
                    "status_event_id": 2,
                    "entity_id": "claim.example.v1",
                    "to_status": "confirmatory",
                    "evidence_bundle_id": NEW_HASH,
                }
            ]
        }

        self.assertEqual(
            find_unbacked_status_changes(before, after, source="D1 status_event"),
            [],
        )

    def test_assurance_change_is_guarded(self) -> None:
        before = registry("provisional", [OLD_HASH])
        after = registry("provisional", [OLD_HASH])
        before["assumptions"][0]["assurance"] = "provisional"
        after["assumptions"][0]["assurance"] = "active"

        violations = find_unbacked_status_changes(before, after, source="registry")

        self.assertEqual(len(violations), 1)
        self.assertIn("assurance", violations[0])

    def test_nested_registry_epistemic_status_change_is_guarded(self) -> None:
        before = registry("active", [OLD_HASH])
        after = registry("active", [OLD_HASH])
        before["assumptions"][0]["evidence"][0]["epistemic_status"] = "exploratory"
        after["assumptions"][0]["evidence"][0]["epistemic_status"] = "confirmatory"

        violations = find_unbacked_status_changes(before, after, source="registry")

        self.assertEqual(len(violations), 1)
        self.assertIn("epistemic_status", violations[0])

    def test_cli_fails_and_passes_for_file_pairs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            before = root / "before.json"
            after = root / "after.json"
            before.write_text(json.dumps(registry("provisional", [OLD_HASH])))
            after.write_text(json.dumps(registry("active", [OLD_HASH])))
            command = [
                sys.executable,
                str(CHECKER),
                "--before-registry",
                str(before),
                "--after-registry",
                str(after),
            ]

            rejected = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(rejected.returncode, 1)
            self.assertIn("anti-laundering check failed", rejected.stderr)

            after.write_text(json.dumps(registry("active", [OLD_HASH, NEW_HASH])))
            accepted = subprocess.run(command, capture_output=True, text=True)

        self.assertEqual(accepted.returncode, 0, accepted.stderr)
        self.assertIn("anti-laundering check passed", accepted.stdout)

    def test_cli_compares_git_revisions_for_ci(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            registry_path = root / "registry" / "assumptions.v1.json"
            registry_path.parent.mkdir(parents=True)
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            subprocess.run(
                ["git", "-C", str(root), "config", "user.email", "ci@example.test"],
                check=True,
            )
            subprocess.run(
                ["git", "-C", str(root), "config", "user.name", "CI"], check=True
            )
            registry_path.write_text(json.dumps(registry("provisional", [OLD_HASH])))
            subprocess.run(["git", "-C", str(root), "add", "."], check=True)
            subprocess.run(
                ["git", "-C", str(root), "commit", "-qm", "base"], check=True
            )
            base = subprocess.run(
                ["git", "-C", str(root), "rev-parse", "HEAD"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            registry_path.write_text(json.dumps(registry("active", [OLD_HASH])))
            subprocess.run(["git", "-C", str(root), "add", "."], check=True)
            subprocess.run(
                ["git", "-C", str(root), "commit", "-qm", "head"], check=True
            )
            head = subprocess.run(
                ["git", "-C", str(root), "rev-parse", "HEAD"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()

            result = subprocess.run(
                [
                    sys.executable,
                    str(CHECKER),
                    "--git-root",
                    str(root),
                    "--base-ref",
                    base,
                    "--head-ref",
                    head,
                ],
                capture_output=True,
                text=True,
            )

        self.assertEqual(result.returncode, 1)
        self.assertIn("no new EvidenceBundle hash", result.stderr)


if __name__ == "__main__":
    unittest.main()
