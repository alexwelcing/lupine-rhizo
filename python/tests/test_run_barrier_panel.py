"""Tests for run_barrier_panel.py pure helpers (no GPU, no MLIPs, no NEB).

The runner itself is GPU-lane only; these tests import the script and unit
test a0/targets resolution, dispersion summaries, and report rendering with
synthetic data, mirroring the other script test modules.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import run_barrier_panel as rbp  # noqa: E402

from lupine_distill.statics import relative_dispersion  # noqa: E402

pytestmark = pytest.mark.unit


# --------------------------------------------------------------------------
# synthetic fixtures
# --------------------------------------------------------------------------


def _synthetic_a0_report() -> dict:
    return {
        "schema": "lupine.discovery_gates.v1",
        "generated_at": "2026-07-13T00:00:00+00:00",
        "subjects": {
            "LiF_rocksalt": {
                "per_model": {
                    "chgnet": {"properties": {"a0": 4.0908}},
                    "mace-mp-medium": {"properties": {"a0": 4.0701}},
                }
            }
        },
    }


def _synthetic_cells() -> dict[str, dict[str, object]]:
    return {
        "chgnet": {
            "forward_barrier_ev": 0.60,
            "backward_barrier_ev": 0.61,
            "barrier_asymmetry_ev": 0.01,
        },
        "mace-mp-medium": {
            "forward_barrier_ev": 0.80,
            "backward_barrier_ev": 0.79,
            "barrier_asymmetry_ev": 0.01,
        },
        "mace-mp-small": {"error": "ConvergenceError: NEB did not converge"},
    }


# --------------------------------------------------------------------------
# panel selection / CLI defaults
# --------------------------------------------------------------------------


class TestPanelSelection:
    def test_panel_is_the_five_halide_rocksalts(self) -> None:
        assert [formula for _, formula in rbp.PANEL] == [
            "LiF",
            "LiCl",
            "LiBr",
            "LiI",
            "NaCl",
        ]

    def test_default_selects_all(self) -> None:
        assert rbp.select_panel("") == list(rbp.PANEL)

    def test_subset_keeps_requested_order(self) -> None:
        assert rbp.select_panel("NaCl,LiF") == [
            ("NaCl_rocksalt", "NaCl"),
            ("LiF_rocksalt", "LiF"),
        ]

    def test_unknown_compound_fails_fast(self) -> None:
        with pytest.raises(SystemExit):
            rbp.select_panel("MgO")

    def test_cli_defaults(self) -> None:
        args = rbp.parse_args([])
        assert args.device == "cuda"
        assert args.n_images == 5
        assert args.supercell == 2
        assert args.fmax == 0.05
        assert args.max_steps == 300
        assert args.out_dir.replace("\\", "/").endswith("data/kinetics/barrier_panel")
        assert args.targets.replace("\\", "/").endswith(
            "data/candidates/kinetics_targets.json"
        )


# --------------------------------------------------------------------------
# a0 resolution
# --------------------------------------------------------------------------


class TestResolveA0:
    def test_prefers_report_a0_with_provenance(self) -> None:
        a0, provenance = rbp.resolve_a0(
            _synthetic_a0_report(), "LiF_rocksalt", "chgnet", "LiF"
        )
        assert a0 == pytest.approx(4.0908)
        assert "per_model[chgnet]" in provenance

    def test_missing_model_falls_back_to_estimate(self) -> None:
        a0, provenance = rbp.resolve_a0(
            _synthetic_a0_report(), "LiF_rocksalt", "mace-mpa-0-medium", "LiF"
        )
        assert a0 > 0
        assert "estimate" in provenance

    def test_missing_report_falls_back_to_estimate(self) -> None:
        a0, provenance = rbp.resolve_a0(None, "LiF_rocksalt", "chgnet", "LiF")
        assert a0 > 0
        assert "estimate" in provenance

    def test_load_a0_report_missing_file_is_none(self, tmp_path: Path) -> None:
        assert rbp.load_a0_report(tmp_path / "nope.json") is None

    def test_load_a0_report_malformed_fails_fast(self, tmp_path: Path) -> None:
        path = tmp_path / "report.json"
        path.write_text("{not json", encoding="utf-8")
        with pytest.raises(SystemExit):
            rbp.load_a0_report(path)


# --------------------------------------------------------------------------
# targets file
# --------------------------------------------------------------------------


class TestLoadTargets:
    def test_missing_file_is_tolerated(self, tmp_path: Path) -> None:
        assert rbp.load_targets(tmp_path / "kinetics_targets.json") is None

    def test_flat_mapping(self, tmp_path: Path) -> None:
        path = tmp_path / "targets.json"
        path.write_text(json.dumps({"LiF": 0.7}), encoding="utf-8")
        targets = rbp.load_targets(path)
        assert targets == {"LiF": {"barrier_ev": 0.7, "source": None}}

    def test_nested_mapping_with_source(self, tmp_path: Path) -> None:
        path = tmp_path / "targets.json"
        payload = {
            "schema": "lupine.kinetics_targets.v1",
            "targets": {"NaCl": {"barrier_ev": 0.65, "source": "expt (NMR)"}},
        }
        path.write_text(json.dumps(payload), encoding="utf-8")
        targets = rbp.load_targets(path)
        assert targets == {"NaCl": {"barrier_ev": 0.65, "source": "expt (NMR)"}}

    def test_malformed_entry_fails_fast(self, tmp_path: Path) -> None:
        path = tmp_path / "targets.json"
        path.write_text(json.dumps({"LiF": "high"}), encoding="utf-8")
        with pytest.raises(SystemExit):
            rbp.load_targets(path)


# --------------------------------------------------------------------------
# dispersion summary
# --------------------------------------------------------------------------


class TestSummarizeCompound:
    def test_dispersion_matches_gates_metric(self) -> None:
        summary = rbp.summarize_compound("LiF", _synthetic_cells())
        assert summary["n_models"] == 2  # failed cell excluded
        assert summary["barrier_relative_dispersion"] == pytest.approx(
            relative_dispersion([0.60, 0.80])
        )
        assert summary["barrier_absolute_spread_ev"] == pytest.approx(0.20)
        assert summary["max_barrier_asymmetry_ev"] == pytest.approx(0.01)
        assert summary["reference_comparison"] is None

    def test_single_model_has_no_dispersion(self) -> None:
        cells = {"chgnet": {"forward_barrier_ev": 0.6, "barrier_asymmetry_ev": 0.0}}
        summary = rbp.summarize_compound("LiF", cells)
        assert summary["barrier_relative_dispersion"] is None
        assert summary["barrier_absolute_spread_ev"] is None

    def test_reference_comparison_deltas(self) -> None:
        target = {"barrier_ev": 0.70, "source": "synthetic"}
        summary = rbp.summarize_compound("LiF", _synthetic_cells(), target)
        comparison = summary["reference_comparison"]
        assert comparison["reference_barrier_ev"] == pytest.approx(0.70)
        assert comparison["delta_ev_by_model"]["chgnet"] == pytest.approx(-0.10)
        assert comparison["delta_ev_by_model"]["mace-mp-medium"] == pytest.approx(0.10)
        assert comparison["median_delta_ev"] == pytest.approx(0.0)

    def test_all_failed_cells(self) -> None:
        cells = {"chgnet": {"error": "CalculationError: boom"}}
        summary = rbp.summarize_compound("LiF", cells)
        assert summary["forward_barrier_ev_by_model"] == {}
        assert summary["n_models"] == 0


# --------------------------------------------------------------------------
# report rendering
# --------------------------------------------------------------------------


def _synthetic_report(with_targets: bool) -> dict:
    cells = {"LiF_rocksalt": _synthetic_cells()}
    target = {"barrier_ev": 0.70, "source": "synthetic"} if with_targets else None
    return {
        "schema": rbp.REPORT_SCHEMA,
        "generated_at": "2026-07-13T00:00:00+00:00",
        "device": "cuda",
        "models": ["chgnet", "mace-mp-medium", "mace-mp-small"],
        "parameters": {
            "supercell": 2,
            "n_images": 5,
            "climb": True,
            "neb_method": "improvedtangent",
            "fmax_ev_per_angstrom": 0.05,
        },
        "provenance": ["synthetic provenance line"],
        "cells": cells,
        "compounds": {
            "LiF_rocksalt": rbp.summarize_compound("LiF", cells["LiF_rocksalt"], target)
        },
        "notes": ["synthetic honesty note"],
    }


class TestRenderMarkdown:
    def test_barrier_table_and_failure_marker(self) -> None:
        text = rbp.render_markdown(_synthetic_report(with_targets=False))
        assert "# Halide cation-vacancy migration-barrier panel" in text
        assert "| LiF | 0.600 | 0.800 | FAILED |" in text
        assert "No kinetics references file was found" in text
        assert "synthetic honesty note" in text

    def test_reference_table_when_targets_present(self) -> None:
        text = rbp.render_markdown(_synthetic_report(with_targets=True))
        assert "## Reference comparison" in text
        assert "0.700" in text
        assert "No kinetics references file was found" not in text
