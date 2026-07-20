"""Tests for the preregistered MLIP-guided sparse-DFT row (z1_sparse_dft).

Heavy machinery (panel/manifest SHA locks, real GPAW convention) is exercised
the same way as test_runner_z1_barrier.py: locked toy fixtures, mock model
calculators, and one end-to-end pass with real GPAW on toy settings.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import mlip_cell_runner as runner
import numpy as np
import pytest
import z1_sparse_dft
from ase.calculators.calculator import Calculator, all_changes
from z1_sparse_dft import (
    build_anchor_set,
    run_sparse_dft_path,
    run_sparse_dft_row,
    select_extrema,
)

ROOT = Path(__file__).resolve().parents[2]
REGISTERED_Z1_MODELS = ("chgnet", "mace-mp-small", "mace-mp-medium", "mace-mpa-0-medium")


class ProfileCalculator(Calculator):
    """Mock model guide: energy = positions[0, 0] (the image's x tag)."""

    implemented_properties = ["energy"]

    def calculate(self, atoms=None, properties=("energy",), system_changes=all_changes):
        super().calculate(atoms, properties, system_changes)
        self.results = {"energy": float(atoms.positions[0, 0])}


class ScaledCalculator(Calculator):
    """Mock DFT: energy = scale * positions[0, 0] + shift."""

    implemented_properties = ["energy"]

    def __init__(self, scale=10.0, shift=0.0, fail_on_x=None):
        super().__init__()
        self.scale = scale
        self.shift = shift
        self.fail_on_x = fail_on_x

    def calculate(self, atoms=None, properties=("energy",), system_changes=all_changes):
        super().calculate(atoms, properties, system_changes)
        x = float(atoms.positions[0, 0])
        if self.fail_on_x is not None and x == self.fail_on_x:
            raise RuntimeError(f"injected GPAW failure at x={x}")
        self.results = {"energy": self.scale * x + self.shift}


class NanCalculator(Calculator):
    implemented_properties = ["energy"]

    def calculate(self, atoms=None, properties=("energy",), system_changes=all_changes):
        super().calculate(atoms, properties, system_changes)
        self.results = {"energy": float("nan")}


def _image(x: float, symbol: str = "H") -> dict:
    return {
        "symbols": [symbol],
        "positions_angstrom": [[x, 0.0, 0.0]],
        "cell_angstrom": [[5.0, 0.0, 0.0], [0.0, 5.0, 0.0], [0.0, 0.0, 5.0]],
        "pbc": [True, True, True],
    }


def _path(
    path_id: str,
    x_tags: list[float],
    reference_energies: list[float],
    chemical_system: str = "Ag-F-Li",
    reference_barrier_ev: float | None = None,
) -> dict:
    return {
        "path_id": path_id,
        "material_id": f"mat-{path_id}",
        "chemical_system": chemical_system,
        "reference_barrier_ev": (
            max(reference_energies) - min(reference_energies)
            if reference_barrier_ev is None
            else reference_barrier_ev
        ),
        "reference": {
            "energies_ev": reference_energies,
            "image_count": len(x_tags),
            "saddle_image_index": reference_energies.index(max(reference_energies)),
        },
        "input_images": [_image(x) for x in x_tags],
    }


def _write_locked_campaign(tmp_path: Path, paths: list[dict], minimum_path_count: int = 1) -> Path:
    panel_path = tmp_path / "data" / "candidates" / "z1-panel.json"
    panel_path.parent.mkdir(parents=True)
    panel = {
        "schema": "lupine.z1.neb_barrier_panel.v1",
        "panel_id": "unit-z1-sparse-panel",
        "measurement": {
            "metric": "barrier_mae",
            "unit": "meV",
            "minimum_path_count": minimum_path_count,
        },
        "execution_protocol": {
            "barrier_definition": "max(image_energy_ev) - min(image_energy_ev)",
            "climb": True,
            "endpoint_relaxation": True,
            "failure_policy": "record failure without imputation",
            "force_convergence_ev_per_angstrom": 0.1,
            "maximum_steps": 100,
            "method": "climbing-image NEB",
            "optimizer": "FIRE",
            "spring_constant_ev_per_angstrom2": 5.0,
            "tangent_method": "improvedtangent",
        },
        "paths": paths,
    }
    panel_bytes = (json.dumps(panel, indent=2, sort_keys=True) + "\n").encode()
    panel_path.write_bytes(panel_bytes)

    manifest = {
        "campaign_id": "discovery.round-5.z1-sparse-dft.v1",
        "available_models": [
            {"model_id": model_id, "version": "unit", "artifact_hash": "sha256:" + "1" * 64}
            for model_id in REGISTERED_Z1_MODELS
        ],
        "acceptance_test": {"metric": "barrier_mae", "operator": "lte", "threshold": 40, "unit": "meV"},
        "execution": {
            "candidate_panel": {
                "path": "data/candidates/z1-panel.json",
                "sha256": "sha256:" + hashlib.sha256(panel_bytes).hexdigest(),
            }
        },
    }
    manifest["content_hash"] = "sha256:" + runner.sha256_hex(manifest)
    manifest_path = tmp_path / "campaigns" / "v1" / "z1.json"
    manifest_path.parent.mkdir(parents=True)
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    return manifest_path


def _load(manifest_path: Path, mlip_id: str = "chgnet"):
    return runner.load_campaign_panel(str(manifest_path), mlip_id, runner.read_url)


# ---------------------------------------------------------------------------
# Anchor-set construction (frozen protocol step 2)
# ---------------------------------------------------------------------------


def test_anchor_set_long_path_uses_pm1_window() -> None:
    anchor = build_anchor_set(7, model_min_index=1, model_max_index=3)
    assert anchor == {
        "anchor_indices": [0, 1, 2, 3, 4, 6],
        "window": 1,
        "short_path_fallback": False,
    }


def test_anchor_set_dedupes_and_clamps() -> None:
    # model-min on an endpoint and model-max on the last image.
    anchor = build_anchor_set(7, model_min_index=0, model_max_index=6)
    assert anchor["anchor_indices"] == [0, 5, 6]
    assert anchor["window"] == 1
    # Flat profile: min == max.
    anchor = build_anchor_set(8, model_min_index=3, model_max_index=3)
    assert anchor["anchor_indices"] == [0, 2, 3, 4, 7]


def test_anchor_set_short_path_widens_to_pm2_declared() -> None:
    # 6 images: at the frozen threshold, the +/-2 fallback applies.
    anchor = build_anchor_set(6, model_min_index=1, model_max_index=3)
    assert anchor == {
        "anchor_indices": [0, 1, 2, 3, 4, 5],
        "window": 2,
        "short_path_fallback": True,
    }
    # 5 images, saddle in the middle: the whole path is anchored, still declared.
    anchor = build_anchor_set(5, model_min_index=0, model_max_index=2)
    assert anchor["anchor_indices"] == [0, 1, 2, 3, 4]
    assert anchor["window"] == 2
    # 7 images: one above the threshold, no fallback.
    assert build_anchor_set(7, 1, 3)["window"] == 1


def test_anchor_set_rejects_invalid_inputs() -> None:
    with pytest.raises(ValueError, match="at least 3 images"):
        build_anchor_set(2, 0, 1)
    with pytest.raises(ValueError, match="outside the path"):
        build_anchor_set(7, 0, 7)


def test_select_extrema_first_occurrence_tie_break() -> None:
    assert select_extrema([1.0, 0.5, 0.5, 2.0, 2.0]) == (1, 3)
    assert select_extrema([3.0]) == (0, 0)
    with pytest.raises(ValueError, match="empty"):
        select_extrema([])


# ---------------------------------------------------------------------------
# Per-path execution (frozen protocol steps 1-3)
# ---------------------------------------------------------------------------


def test_sparse_path_barrier_arithmetic_and_record() -> None:
    # Model profile (energy = x tag): min at 1, max at 3.
    x_tags = [0.0, -0.2, 0.4, 0.9, 0.3, -0.1, 0.1]
    # DFT mock (scale=10) reproduces the reference profile exactly.
    reference = [10.0 * x for x in x_tags]
    path = _path("p-arith", x_tags, reference)

    record = run_sparse_dft_path(path, ProfileCalculator(), lambda: ScaledCalculator(scale=10.0))

    assert record["status"] == "completed"
    assert record["anchor_indices"] == [0, 1, 2, 3, 4, 6]
    assert record["anchor_count"] == 6
    assert record["window"] == 1
    assert record["short_path_fallback"] is False
    assert record["model_min_index"] == 1
    assert record["model_max_index"] == 3
    assert record["dft_profile_max_index"] == 3
    assert record["saddle_index_agreement"] is True
    assert record["saddle_index_distance"] == 0
    assert record["model_energies_ev"] == pytest.approx(x_tags)
    # Anchors contain the true profile min (idx 1) and max (idx 3).
    assert record["sparse_barrier_ev"] == pytest.approx(10.0 * 0.9 - 10.0 * -0.2)
    assert record["reference_barrier_ev"] == pytest.approx(record["sparse_barrier_ev"])
    assert record["signed_error_mev"] == pytest.approx(0.0)
    assert record["absolute_error_mev"] == pytest.approx(0.0)
    anchors = {a["image_index"]: a for a in record["anchors"]}
    assert set(anchors) == {0, 1, 2, 3, 4, 6}
    for index, anchor in anchors.items():
        assert anchor["gpaw_energy_ev"] == pytest.approx(reference[index])
        assert anchor["reference_energy_ev"] == pytest.approx(reference[index])
        assert anchor["offset_mev"] == pytest.approx(0.0)


def test_sparse_path_records_saddle_disagreement_and_offsets() -> None:
    # Model says max at idx 2; the DFT reference profile peaks at idx 4.
    x_tags = [0.0, 0.1, 0.5, 0.2, 0.4, 0.3, 0.05]
    reference = [0.0, 0.2, 0.3, 0.4, 1.0, 0.6, 0.1]
    path = _path("p-saddle", x_tags, reference)
    # DFT mock returns reference + a constant 50 meV convention offset.
    shift = 0.050
    energies_by_x = dict(zip(x_tags, reference))

    class OffsetCalculator(ScaledCalculator):
        def calculate(self, atoms=None, properties=("energy",), system_changes=all_changes):
            Calculator.calculate(self, atoms, properties, system_changes)
            x = float(atoms.positions[0, 0])
            self.results = {"energy": energies_by_x[x] + shift}

    record = run_sparse_dft_path(path, ProfileCalculator(), OffsetCalculator)

    assert record["status"] == "completed"
    assert record["model_max_index"] == 2
    assert record["dft_profile_max_index"] == 4
    assert record["saddle_index_agreement"] is False
    assert record["saddle_index_distance"] == 2
    # Anchors: {0, 6, min=0, 2 +/- 1} = [0, 1, 2, 3, 6]; the shifted mock is
    # a constant offset, so the sparse barrier still matches reference shape.
    assert record["anchor_indices"] == [0, 1, 2, 3, 6]
    for anchor in record["anchors"]:
        assert anchor["offset_mev"] == pytest.approx(50.0)
    expected_sparse = (max(reference[i] for i in [0, 1, 2, 3, 6]) + shift) - (
        min(reference[i] for i in [0, 1, 2, 3, 6]) + shift
    )
    assert record["sparse_barrier_ev"] == pytest.approx(expected_sparse)


def test_sparse_path_fails_closed_without_reference_profile() -> None:
    path = _path("p-noref", [0.0, 0.5, 1.0], [0.0, 0.5, 1.0])
    path["reference"]["energies_ev"] = [0.0, 0.5]  # misaligned with 3 images
    with pytest.raises(RuntimeError, match="reference.energies_ev"):
        run_sparse_dft_path(path, ProfileCalculator(), lambda: ScaledCalculator())


def test_model_non_finite_energy_fails_the_path(tmp_path: Path) -> None:
    paths = [_path("p-nan", [0.0, 0.5, 1.0], [0.0, 0.5, 1.0])]
    manifest, panel, _, contract = _load(_write_locked_campaign(tmp_path, paths))

    result = run_sparse_dft_row(manifest, panel, NanCalculator(), contract)

    prediction = result["predictions"][0]
    assert prediction["status"] == "failed"
    assert prediction["error_class"] == "RuntimeError"
    assert "non-finite" in prediction["error"]
    assert "sparse_barrier_ev" not in prediction
    assert result["metrics"]["failed_path_count"] == 1
    assert result["metrics"]["measurement_complete"] is False
    assert result["metrics"]["verdict"] == "incomplete"
    assert result["score"] == 0.0


# ---------------------------------------------------------------------------
# Row aggregation: failures, thresholds, families, saddle stats
# ---------------------------------------------------------------------------


def _two_path_panel(tmp_path: Path, minimum: int = 2):
    paths = [
        _path("p-halide", [0.0, -0.2, 0.4, 0.9, 0.3, -0.1, 0.1],
              [10.0 * x for x in [0.0, -0.2, 0.4, 0.9, 0.3, -0.1, 0.1]],
              chemical_system="Ag-F-Li"),
        _path("p-sulfide", [0.0, 0.1, 0.2, 0.3, 0.4],
              [0.0, 0.2, 0.5, 0.3, 0.1],
              chemical_system="Bi-Li-S"),
    ]
    return _load(_write_locked_campaign(tmp_path, paths, minimum_path_count=minimum))


def test_gpaw_anchor_failure_is_recorded_never_imputed(tmp_path: Path) -> None:
    manifest, panel, _, contract = _two_path_panel(tmp_path)
    # GPAW fails on x=0.9 (the halide path's saddle anchor); sulfide path runs.
    factory = lambda: ScaledCalculator(scale=10.0, fail_on_x=0.9)  # noqa: E731

    result = run_sparse_dft_row(manifest, panel, ProfileCalculator(), contract, dft_calculator_factory=factory)

    halide, sulfide = result["predictions"]
    assert halide["status"] == "failed"
    assert halide["error_class"] == "RuntimeError"
    assert "injected GPAW failure" in halide["error"]
    assert "sparse_barrier_ev" not in halide
    assert "absolute_error_mev" not in halide
    assert sulfide["status"] == "completed"
    metrics = result["metrics"]
    assert metrics["completed_path_count"] == 1
    assert metrics["failed_path_count"] == 1
    # MAE aggregates completed paths only; the failure is reported, not hidden.
    assert metrics["sparse_barrier_mae_mev"] == pytest.approx(sulfide["absolute_error_mev"])
    assert metrics["measurement_complete"] is False
    assert metrics["verdict"] == "incomplete"
    assert metrics["win"] is False
    assert result["score"] == 0.0


def _crafted_row(monkeypatch: pytest.MonkeyPatch, abs_errors: list[float], anchor_count: int = 6):
    completed = [
        {
            "path_id": f"crafted-{i}",
            "material_id": None,
            "chemical_system": "Ag-F-Li",
            "family": "halide",
            "status": "completed",
            "anchor_count": anchor_count,
            "anchors": [],
            "saddle_index_agreement": True,
            "saddle_index_distance": 0,
            "absolute_error_mev": error,
            "signed_error_mev": error,
        }
        for i, error in enumerate(abs_errors)
    ]
    monkeypatch.setattr(
        z1_sparse_dft, "run_sparse_dft_path", lambda *args, **kwargs: completed.pop(0)
    )
    manifest = {"acceptance_test": {"threshold": 40}}
    panel = {
        "paths": [{"path_id": f"crafted-{i}"} for i in range(len(abs_errors))],
        "measurement": {"minimum_path_count": len(abs_errors)},
    }
    return run_sparse_dft_row(manifest, panel, object(), {})


def test_win_strong_win_thresholds_are_inclusive(monkeypatch: pytest.MonkeyPatch) -> None:
    result = _crafted_row(monkeypatch, [40.0])
    assert result["metrics"]["sparse_barrier_mae_mev"] == 40.0
    assert result["metrics"]["win"] is True
    assert result["metrics"]["strong_win"] is False
    assert result["metrics"]["verdict"] == "win"

    result = _crafted_row(monkeypatch, [15.0])
    assert result["metrics"]["win"] is True
    assert result["metrics"]["strong_win"] is True
    assert result["metrics"]["verdict"] == "strong_win"

    result = _crafted_row(monkeypatch, [40.000_001])
    assert result["metrics"]["win"] is False
    assert result["metrics"]["verdict"] == "loss"

    result = _crafted_row(monkeypatch, [15.000_001])
    assert result["metrics"]["win"] is True
    assert result["metrics"]["strong_win"] is False
    assert result["metrics"]["verdict"] == "win"


def test_thresholds_through_real_arithmetic(tmp_path: Path) -> None:
    # 39.9 meV error -> win; 40.1 meV error -> loss (real path, no crafting).
    def panel_with_error(tmp: Path, error_mev: float):
        x_tags = [0.0, -0.2, 0.4, 0.9, 0.3, -0.1, 0.1]
        reference = [10.0 * x for x in x_tags]
        sparse = max(reference) - min(reference)
        path = _path("p-th", x_tags, reference,
                     reference_barrier_ev=sparse - error_mev / 1000.0)
        return _load(_write_locked_campaign(tmp, [path]))

    manifest, panel, _, contract = panel_with_error(tmp_path / "win", 39.9)
    result = run_sparse_dft_row(manifest, panel, ProfileCalculator(), contract,
                                dft_calculator_factory=lambda: ScaledCalculator(scale=10.0))
    assert result["metrics"]["sparse_barrier_mae_mev"] == pytest.approx(39.9)
    assert result["metrics"]["win"] is True
    assert result["metrics"]["verdict"] == "win"

    manifest, panel, _, contract = panel_with_error(tmp_path / "loss", 40.1)
    result = run_sparse_dft_row(manifest, panel, ProfileCalculator(), contract,
                                dft_calculator_factory=lambda: ScaledCalculator(scale=10.0))
    assert result["metrics"]["sparse_barrier_mae_mev"] == pytest.approx(40.1)
    assert result["metrics"]["win"] is False
    assert result["metrics"]["verdict"] == "loss"


def test_family_breakdown_and_anchor_cost_metrics(tmp_path: Path) -> None:
    manifest, panel, _, contract = _two_path_panel(tmp_path)

    result = run_sparse_dft_row(manifest, panel, ProfileCalculator(), contract,
                                dft_calculator_factory=lambda: ScaledCalculator(scale=10.0))

    metrics = result["metrics"]
    halide, sulfide = result["predictions"]
    assert halide["family"] == "halide"
    assert sulfide["family"] == "sulfide"
    assert metrics["families"] == {
        "halide": {"path_count": 1, "mae_mev": pytest.approx(0.0)},
        "sulfide": {"path_count": 1, "mae_mev": pytest.approx(sulfide["absolute_error_mev"])},
    }
    # Halide path: 7 images -> 6 anchors; sulfide path: 5 images -> declared
    # fallback, anchors {0,4} u {2,3,4} = 4 anchors. Median of {4, 6} is 5.0;
    # both under the frozen budgets.
    assert halide["window"] == 1
    assert sulfide["window"] == 2 and sulfide["short_path_fallback"] is True
    assert halide["anchor_count"] == 6
    assert sulfide["anchor_count"] == 4
    assert metrics["median_anchors_per_path"] == pytest.approx(5.0)
    assert metrics["max_anchors_per_path"] == 6
    assert metrics["anchor_budget_met"] is True
    assert metrics["cost_claim_met"] is True
    assert metrics["total_dft_evaluations"] == halide["anchor_count"] + sulfide["anchor_count"]
    assert metrics["verdict"] in {"win", "strong_win", "loss"}
    assert result["row_spec"]["row_id"] == "sparse_dft_barrier"
    assert result["row_spec"]["dft"]["parameters"] == {
        "mode": "fd", "xc": "PBE", "h": 0.18, "kpts": [2, 2, 2], "txt": None,
    }
    assert result["row_spec"]["preregistration"].endswith("sparse-dft-pilot-preregistration.md")


def test_saddle_location_and_convention_offset_line_items(tmp_path: Path) -> None:
    # Path A: model saddle agrees with DFT profile. Path B: off by 2.
    # B's x-tags are shifted by +1.0 so a single dict-mocked DFT can serve
    # both paths without x collisions.
    x_a = [0.0, -0.2, 0.4, 0.9, 0.3, -0.1, 0.1]
    ref_a = [10.0 * x for x in x_a]
    x_b = [1.0, 1.1, 1.5, 1.2, 1.4, 1.3, 1.05]
    ref_b = [0.0, 0.2, 0.3, 0.4, 1.0, 0.6, 0.1]
    path_a = _path("p-agree", x_a, ref_a)
    path_b = _path("p-disagree", x_b, ref_b)
    manifest, panel, _, contract = _load(
        _write_locked_campaign(tmp_path, [path_a, path_b], minimum_path_count=2)
    )
    shift = 0.020  # constant +20 meV GPAW-vs-reference convention offset
    energies_by_x = {
        x: ref + shift for x, ref in zip(x_a + x_b, ref_a + ref_b)
    }

    class OffsetCalculator(Calculator):
        implemented_properties = ["energy"]

        def calculate(self, atoms=None, properties=("energy",), system_changes=all_changes):
            super().calculate(atoms, properties, system_changes)
            x = float(atoms.positions[0, 0])
            self.results = {"energy": energies_by_x[x]}

    result = run_sparse_dft_row(manifest, panel, ProfileCalculator(), contract,
                                dft_calculator_factory=OffsetCalculator)

    metrics = result["metrics"]
    assert metrics["saddle_location_exact_fraction"] == pytest.approx(0.5)
    assert metrics["saddle_location_within_1_fraction"] == pytest.approx(0.5)
    assert metrics["saddle_location_error_rate"] == pytest.approx(0.5)
    assert metrics["saddle_location_error_rate_gt_15pct"] is True
    # Constant +20 meV mock offset shows up as its own line item.
    assert metrics["gpaw_reference_offset_mean_mev"] == pytest.approx(20.0)
    assert metrics["gpaw_reference_offset_mae_mev"] == pytest.approx(20.0)


def test_family_classifier_matches_tools_original() -> None:
    from tools.score_z1r5_correction import family_of as tools_family_of

    panel = json.loads((ROOT / "data/candidates/z1_nebdft2k_barriers.lock.json").read_text())
    systems = [p["chemical_system"] for p in panel["paths"]] + [
        "H", "Li-F", "Na-S", "K-P", "Mg-B", "Ca-N", "Al-O", "As-Li-O", "Cl-Cr-Li",
    ]
    for system in systems:
        assert z1_sparse_dft.family_of(system) == tools_family_of(system)
    assert z1_sparse_dft.family_of("Ag-F-Li") == "halide"
    assert z1_sparse_dft.family_of("Al-Li-O") == "oxide"


# ---------------------------------------------------------------------------
# Runner integration (row dispatch, dtype, fail-closed loading)
# ---------------------------------------------------------------------------


def _run_cell_args(manifest_path: Path, artifact_prefix: Path, mlip_id: str = "chgnet"):
    return runner.parse_args(
        [
            "run-cell",
            "--run-id", "unit-run",
            "--cell-id", f"unit-run:sparse_dft_barrier:{mlip_id}",
            "--row-id", "sparse_dft_barrier",
            "--mlip-id", mlip_id,
            "--manifest-url", str(manifest_path),
            "--artifact-prefix", str(artifact_prefix),
            "--checkpoint-mode", "off",
        ]
    )


def test_runner_dispatches_sparse_row_with_float64(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    paths = [_path("p-dispatch", [0.0, -0.2, 0.4, 0.9, 0.3, -0.1, 0.1],
                   [10.0 * x for x in [0.0, -0.2, 0.4, 0.9, 0.3, -0.1, 0.1]])]
    manifest_path = _write_locked_campaign(tmp_path, paths)
    artifact_prefix = tmp_path / "artifacts"
    captured: list[str] = []

    def fake_load_calculator(mlip_id: str, default_dtype: str = "float32"):
        captured.append(default_dtype)
        return ProfileCalculator()

    monkeypatch.setattr(runner, "load_calculator", fake_load_calculator)
    monkeypatch.setattr(runner, "runtime_versions", lambda: {})
    monkeypatch.setattr(
        z1_sparse_dft, "default_dft_calculator_factory", lambda: ScaledCalculator(scale=10.0)
    )

    result = runner.run_cell(_run_cell_args(manifest_path, artifact_prefix))

    assert captured == ["float64"]
    assert result.metrics["row_id"] == "sparse_dft_barrier"
    assert result.metrics["row_metrics"]["primary_metric"] == "sparse_barrier_mae_mev"
    artifact = json.loads((artifact_prefix / "cell_result.json").read_text(encoding="utf-8"))
    assert artifact["row_id"] == "sparse_dft_barrier"
    assert artifact["row_spec"]["row_id"] == "sparse_dft_barrier"
    assert artifact["predictions"][0]["status"] == "completed"
    assert artifact["predictions"][0]["anchor_indices"] == [0, 1, 2, 3, 4, 6]


def test_sparse_row_fails_closed_on_tampered_manifest(tmp_path: Path) -> None:
    paths = [_path("p-tamper", [0.0, 0.5, 1.0], [0.0, 0.5, 1.0])]
    manifest_path = _write_locked_campaign(tmp_path, paths)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["campaign_id"] = "tampered"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    args = _run_cell_args(manifest_path, tmp_path / "artifacts")
    with pytest.raises(ValueError, match="CampaignManifest content_hash mismatch"):
        runner.run_cell(args, preloaded_calc=ProfileCalculator())


# ---------------------------------------------------------------------------
# End-to-end: toy panel, mock model guide, real GPAW on toy settings
# ---------------------------------------------------------------------------


def _al2_image(a: float, d: float) -> dict:
    """2-atom Al cell; the guide reads d from the second atom's z position."""
    return {
        "symbols": ["Al", "Al"],
        "positions_angstrom": [[0.0, 0.0, 0.0], [a / 2, a / 2, a / 2 + d]],
        "cell_angstrom": [[0.0, a / 2, a / 2], [a / 2, 0.0, a / 2], [a / 2, a / 2, 0.0]],
        "pbc": [True, True, True],
    }


class DisplacementGuide(Calculator):
    """Mock model guide for the real-GPAW panel: energy = displacement d."""

    implemented_properties = ["energy"]

    def calculate(self, atoms=None, properties=("energy",), system_changes=all_changes):
        super().calculate(atoms, properties, system_changes)
        self.results = {"energy": float(atoms.positions[1, 2])}


def test_end_to_end_real_gpaw_toy_panel(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    a = 4.05
    # Path A (7 images): guide min at endpoint 0 (d=0.0 -> z=a/2), max at
    # image 3 -> anchors {0, 6} ∪ {2, 3, 4} = [0, 2, 3, 4, 6].
    d_a = [0.00, 0.06, 0.10, 0.14, 0.10, 0.05, 0.03]
    # Path B (5 images, declared +/-2 fallback): guide min at endpoint 0,
    # max at image 2 -> anchors cover the whole short path.
    d_b = [0.00, 0.08, 0.12, 0.07, 0.04]

    def make_path(path_id: str, d_tags: list[float], chemical_system: str) -> dict:
        images = [_al2_image(a, d) for d in d_tags]
        n = len(images)
        # Fabricated reference profile: only its shape matters here (argmax at
        # the guide-proposed saddle on path A); energies are self-consistent.
        reference = [min(1.0, 8.0 * d) for d in d_tags]
        return {
            "path_id": path_id,
            "material_id": f"mat-{path_id}",
            "chemical_system": chemical_system,
            "reference_barrier_ev": max(reference) - min(reference),
            "reference": {
                "energies_ev": reference,
                "image_count": n,
                "saddle_image_index": reference.index(max(reference)),
            },
            "input_images": images,
        }

    paths = [
        make_path("p-gpaw-long", d_a, "Al-Li-O"),
        make_path("p-gpaw-short", d_b, "Al-F-Li"),
    ]
    manifest_path = _write_locked_campaign(tmp_path, paths, minimum_path_count=2)
    artifact_prefix = tmp_path / "artifacts"

    # Toy GPAW settings so the pass runs in seconds; row_spec must record the
    # executed parameters verbatim, so the artifact shows these, not the
    # frozen campaign values.
    toy_params = {"mode": "fd", "xc": "PBE", "h": 0.35, "kpts": (1, 1, 1), "txt": None}
    monkeypatch.setattr(z1_sparse_dft, "FROZEN_GPAW_PARAMS", toy_params)
    monkeypatch.setattr(runner, "runtime_versions", lambda: {})

    result = runner.run_cell(
        _run_cell_args(manifest_path, artifact_prefix),
        preloaded_calc=DisplacementGuide(),
    )

    artifact = json.loads((artifact_prefix / "cell_result.json").read_text(encoding="utf-8"))
    predictions = artifact["predictions"]
    assert [p["status"] for p in predictions] == ["completed", "completed"]

    long_path, short_path = predictions
    # Guide extrema: DisplacementGuide energy = z of atom 2 = a/2 + d.
    assert long_path["model_min_index"] == 0
    assert long_path["model_max_index"] == 3
    assert long_path["anchor_indices"] == [0, 2, 3, 4, 6]
    assert long_path["window"] == 1 and long_path["short_path_fallback"] is False
    assert short_path["model_min_index"] == 0
    assert short_path["model_max_index"] == 2
    assert short_path["anchor_indices"] == [0, 1, 2, 3, 4]
    assert short_path["window"] == 2 and short_path["short_path_fallback"] is True

    for prediction in predictions:
        energies = [anchor["gpaw_energy_ev"] for anchor in prediction["anchors"]]
        assert all(np.isfinite(energies))
        assert len(energies) == prediction["anchor_count"]
        # Real GPAW ran per anchor: energies differ across displaced images.
        assert len(set(energies)) > 1
        assert prediction["sparse_barrier_ev"] == pytest.approx(
            max(energies) - min(energies)
        )
        assert prediction["absolute_error_mev"] == pytest.approx(
            abs(prediction["sparse_barrier_ev"] - prediction["reference_barrier_ev"]) * 1000.0
        )
        for anchor in prediction["anchors"]:
            assert anchor["reference_energy_ev"] == pytest.approx(
                paths[0]["reference"]["energies_ev"][anchor["image_index"]]
                if prediction is long_path else
                paths[1]["reference"]["energies_ev"][anchor["image_index"]]
            )

    metrics = artifact["accuracy"]
    expected_mae = sum(p["absolute_error_mev"] for p in predictions) / 2
    assert metrics["sparse_barrier_mae_mev"] == pytest.approx(expected_mae)
    assert metrics["completed_path_count"] == 2
    assert metrics["failed_path_count"] == 0
    assert metrics["measurement_complete"] is True
    assert metrics["median_anchors_per_path"] == pytest.approx(5.0)
    assert metrics["anchor_budget_met"] is True
    assert metrics["families"]["oxide"]["path_count"] == 1
    assert metrics["families"]["halide"]["path_count"] == 1
    # The executed (toy) GPAW parameters are recorded, not the frozen ones.
    assert artifact["row_spec"]["dft"]["parameters"]["h"] == 0.35
    assert artifact["row_spec"]["dft"]["parameters"]["kpts"] == [1, 1, 1]
    assert result.metrics["row_id"] == "sparse_dft_barrier"
