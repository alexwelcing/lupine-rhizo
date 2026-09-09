#!/usr/bin/env python3
"""Regression tests for the TMS proceedings result/figure bundle."""

from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("tms_build_results", HERE / "build_results.py")
assert SPEC and SPEC.loader
BUILD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUILD)


class ResultsBundleTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.result = json.loads((HERE / "results.json").read_text(encoding="utf-8"))

    def test_canonical_result_passes_fail_closed_validator(self) -> None:
        BUILD.validate(self.result)

    def test_every_claim_family_has_source_bindings(self) -> None:
        sources = self.result["source_files"]
        self.assertEqual(set(sources), {
            "alignment",
            "anchor_blocker",
            "anchor_spec",
            "benchmark_rows",
            "classical_tensors",
            "environment_field",
            "geometry",
            "global_operator",
            "negative_results",
            "oracle_loo_table",
            "query_universe",
        })
        for record in sources.values():
            self.assertEqual(len(record["sha256"]), 64)
            self.assertTrue(record["locator"])
            self.assertTrue(record["repository_revision"])

    def test_group_rows_bind_all_42_source_rows(self) -> None:
        rows = self.result["geometry"]["groups"]
        self.assertEqual([row["source_row"] for row in rows], list(range(42)))
        self.assertEqual(sum(row["n_materials"] == 3 for row in rows), 21)

    def test_oracle_and_deployable_results_cannot_be_conflated(self) -> None:
        elastic = self.result["elastic_benchmark"]
        oracle = elastic["oracle_directional_ceiling"]
        deployable = elastic["global_operator_failure"]
        self.assertFalse(oracle["deployable"])
        self.assertTrue(deployable["deployable_test"])
        self.assertEqual((oracle["raw_mae_gpa"], oracle["corrected_mae_gpa"]), (17.84, 10.36))
        self.assertEqual((deployable["raw_mae_gpa"], deployable["corrected_mae_gpa"]), (14.55, 63.40))

    def test_all_electron_anchor_remains_pending(self) -> None:
        layers = self.result["qualification_stack"]["layers"]
        anchor = next(row for row in layers if row["key"] == "all_electron_anchor")
        self.assertEqual(anchor["status"], "PENDING")

    def test_four_pdf_and_png_pairs_are_real_files(self) -> None:
        for stem in BUILD.FIGURES:
            png = (HERE / f"{stem}.png").read_bytes()
            pdf = (HERE / f"{stem}.pdf").read_bytes()
            self.assertTrue(png.startswith(b"\x89PNG\r\n\x1a\n"))
            self.assertTrue(pdf.startswith(b"%PDF-"))
            self.assertGreater(len(png), 10_000)
            self.assertGreater(len(pdf), 5_000)


if __name__ == "__main__":
    unittest.main()
