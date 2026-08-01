"""Tests for the versioned ontology atlas link checker."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tools.check_ontology_links import (
    OntologyError,
    parse_readiness,
    validate_atlas,
    validate_lock,
)

CLASS_CHAINS = {
    "MC1": "C8",
    "MC2": "C9",
    "MC3": "C4",
    "MC4": "C1",
    "MC5": "C3",
    "MC6": "C2",
    "MC7": "C7",
    "MC8": "C5",
    "MC9": ["C6", "C11"],
}
ROOT = Path(__file__).resolve().parents[2]
CHECKER = ROOT / "tools" / "check_ontology_links.py"
ATLAS_PATH = ROOT / "registry" / "ontology" / "atlas.v1.json"
LOCK_PATH = ROOT / "snapshots" / "ontology.lock.json"


def valid_atlas() -> dict:
    return {
        "metadata": {"compiled": "2026-07-30"},
        "materialClasses": [
            {"id": material_id, "chain": chain}
            for material_id, chain in CLASS_CHAINS.items()
        ],
        "acceptanceTests": [
            {"id": f"Z{index}", "chain": f"C{index}"}
            for index in range(1, 12)
        ],
        "discoveryChains": [
            {"id": f"C{index}", "readiness": "M"}
            for index in range(1, 12)
        ],
        "readinessGrades": [{"id": grade} for grade in ("H", "M", "L")],
        "relations": [
            {
                "name": "correctedBy",
                "domain": "Claim",
                "range": "ConflictRuling",
                "inverse": "corrects",
                "label": "claim.correctedBy",
                "inverseLabel": "claim.corrects",
            },
            {
                "name": "corrects",
                "domain": "CorrectionLever",
                "range": "ErrorType/MeasuredError",
                "inverse": "correctedBy",
                "label": "lever.corrects",
                "inverseLabel": "lever.correctedBy",
            },
        ],
        "freshnessLayer": {"atlasDate": "2026-07-30"},
    }


def repository_atlas() -> tuple[bytes, dict, dict]:
    atlas_bytes = ATLAS_PATH.read_bytes()
    return atlas_bytes, json.loads(atlas_bytes), json.loads(LOCK_PATH.read_bytes())


class ReadinessParsingTests(unittest.TestCase):
    def test_parses_plain_and_annotated_readiness_grades(self) -> None:
        self.assertEqual(parse_readiness("H"), ("H", None))
        self.assertEqual(
            parse_readiness("M (L→M boundary)"),
            ("M", "L→M boundary"),
        )

    def test_rejects_unknown_or_malformed_readiness_grades(self) -> None:
        for value in ("X", "M note", "M ()", "M (   )", "M (\t)"):
            with self.subTest(value=value), self.assertRaises(OntologyError):
                parse_readiness(value)


class OntologyLinkTests(unittest.TestCase):
    def test_material_class_chains_resolve_with_a1_identifier_parity(self) -> None:
        validate_atlas(valid_atlas())

        atlas = valid_atlas()
        atlas["materialClasses"][0]["chain"] = "C404"
        with self.assertRaisesRegex(OntologyError, "materialClasses.*MC1.*C404"):
            validate_atlas(atlas)

        atlas = valid_atlas()
        atlas["materialClasses"][0]["chain"] = "C1"
        with self.assertRaisesRegex(OntologyError, "A1 mapping"):
            validate_atlas(atlas)

    def test_acceptance_tests_are_one_to_one_with_discovery_chains(self) -> None:
        atlas = valid_atlas()
        atlas["acceptanceTests"][10]["chain"] = "C10"
        with self.assertRaisesRegex(OntologyError, "one-to-one"):
            validate_atlas(atlas)

        atlas = valid_atlas()
        atlas["acceptanceTests"][0]["id"] = "Z404"
        with self.assertRaisesRegex(OntologyError, "Z1–Z11"):
            validate_atlas(atlas)

    def test_all_readiness_values_parse_including_boundary_annotations(self) -> None:
        atlas = valid_atlas()
        atlas["discoveryChains"][0]["readiness"] = "M (L→M boundary)"
        atlas["scoreboard"] = [{"row": 1, "readiness": "M (upgraded from draft L)"}]
        validate_atlas(atlas)

        atlas["scoreboard"][0]["readiness"] = "medium"
        with self.assertRaisesRegex(OntologyError, "scoreboard.*readiness"):
            validate_atlas(atlas)

        atlas = valid_atlas()
        del atlas["discoveryChains"][0]["readiness"]
        with self.assertRaisesRegex(OntologyError, "C1.*readiness"):
            validate_atlas(atlas)

    def test_relation_labels_are_namespaced_by_relation_owner(self) -> None:
        validate_atlas(valid_atlas())

        atlas = valid_atlas()
        del atlas["relations"][0]["label"]
        with self.assertRaisesRegex(OntologyError, "claim.correctedBy"):
            validate_atlas(atlas)

        atlas = valid_atlas()
        atlas["relations"][1]["inverseLabel"] = "claim.correctedBy"
        with self.assertRaisesRegex(OntologyError, "lever.correctedBy"):
            validate_atlas(atlas)


class OntologyLockTests(unittest.TestCase):
    def test_lock_binds_artifact_source_date_and_freshness_layer(self) -> None:
        atlas_bytes, atlas, lock = repository_atlas()
        validate_lock(atlas_bytes, atlas, lock)

        for field, bad_value in (
            ("sha256", "sha256:" + "0" * 64),
            ("transformation", {"id": "unreviewed-rewrite"}),
            ("atlasDate", "2026-07-29"),
            ("freshnessLayer", {"atlasDate": "2026-07-29"}),
        ):
            with self.subTest(field=field):
                broken = dict(lock)
                broken[field] = bad_value
                with self.assertRaisesRegex(OntologyError, field):
                    validate_lock(atlas_bytes, atlas, broken)

        mutated_lock = dict(lock)
        mutated_lock["source"] = {
            **lock["source"],
            "sha256": "sha256:" + "0" * 64,
        }
        with self.assertRaisesRegex(OntologyError, "source.sha256"):
            validate_lock(atlas_bytes, atlas, mutated_lock)

        mutated_atlas = json.loads(atlas_bytes)
        mutated_atlas["metadata"]["title"] += " tampered"
        mutated_bytes = (
            json.dumps(mutated_atlas, indent=2, ensure_ascii=False) + "\n"
        ).encode()
        rehashed_lock = dict(lock)
        rehashed_lock["sha256"] = "sha256:" + hashlib.sha256(mutated_bytes).hexdigest()
        with self.assertRaisesRegex(OntologyError, "reversing the declared transformation"):
            validate_lock(mutated_bytes, mutated_atlas, rehashed_lock)

    def test_cli_validates_files_and_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            atlas_path = root / "atlas.json"
            lock_path = root / "lock.json"
            atlas_bytes, atlas, lock = repository_atlas()
            atlas_path.write_bytes(atlas_bytes)
            lock_path.write_text(json.dumps(lock))
            command = [
                sys.executable,
                str(CHECKER),
                "--atlas",
                str(atlas_path),
                "--lock",
                str(lock_path),
            ]

            accepted = subprocess.run(command, capture_output=True, text=True)
            del atlas["relations"][0]["label"]
            broken_bytes = (json.dumps(atlas, indent=2, ensure_ascii=False) + "\n").encode()
            atlas_path.write_bytes(broken_bytes)
            lock["sha256"] = "sha256:" + hashlib.sha256(broken_bytes).hexdigest()
            lock_path.write_text(json.dumps(lock))
            rejected = subprocess.run(command, capture_output=True, text=True)

        self.assertEqual(accepted.returncode, 0, accepted.stderr)
        self.assertIn("ontology link check passed", accepted.stdout)
        self.assertNotEqual(rejected.returncode, 0)
        self.assertIn("ontology link check failed", rejected.stderr)


if __name__ == "__main__":
    unittest.main()
