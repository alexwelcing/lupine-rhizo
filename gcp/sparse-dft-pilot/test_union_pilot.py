"""Tests for the union-anchor sparse-DFT pilot driver (union_pilot.py).

No GPAW is touched: the energy function is injected, the panel and model
artifacts are synthetic, and every filesystem effect lands under pytest's
tmp_path. Covers anchor-universe construction (union + A3.2 dense
extension), resume/skip, the memory guard, receipt import, and the offline
assembly math (same-engine/VASP errors, T1 wander, verdicts).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import union_pilot as up  # noqa: E402
from z1_sparse_dft import build_anchor_set, select_extrema  # noqa: E402

MODEL_A = "chgnet"
MODEL_B = "mace-mp-small"


# --- Synthetic fixtures -----------------------------------------------------------

def make_path(index: int, image_count: int, reference: list[float]) -> dict:
    return {
        "path_id": f"mp-test-{index}",
        "chemical_system": "Li-Fe-O",
        "input_images": [{"image": j} for j in range(image_count)],
        "reference": {"energies_ev": reference},
        "reference_barrier_ev": max(reference) - min(reference),
    }


def make_artifact(profiles: dict[str, list[float] | None]) -> dict:
    """profiles: path_id -> energy profile, or None for a failed CI-NEB."""
    predictions = []
    for path_id, profile in profiles.items():
        if profile is None:
            predictions.append({
                "path_id": path_id,
                "status": "failed",
                "error_class": "RuntimeError",
                "error": "CI-NEB did not converge under the frozen protocol",
            })
        else:
            predictions.append({
                "path_id": path_id,
                "status": "completed",
                "predicted_image_energies_ev": profile,
            })
    return {"predictions": predictions}


@pytest.fixture()
def synthetic() -> dict:
    """Three 5-image paths; path 2 has no model guidance in any artifact."""
    references = {
        0: [0.00, 0.10, 0.40, 0.20, 0.05],
        1: [0.00, 0.30, 0.25, 0.10, 0.02],
        2: [0.00, 0.05, 0.15, 0.35, 0.10],
    }
    panel = {"paths": [make_path(i, 5, references[i]) for i in range(3)]}
    # Model A on path 0: min at 4, max at 0 -> frozen anchors {0,1,2,4}
    # (mirrors the real path-7 receipt shape). Model B: min at 0, max at 2
    # -> window +/-2 covers the whole path.
    artifacts = {
        MODEL_A: make_artifact({
            "mp-test-0": [0.50, 0.40, 0.30, 0.20, 0.10],
            "mp-test-1": [0.10, 0.50, 0.40, 0.30, 0.20],
            "mp-test-2": None,
        }),
        MODEL_B: make_artifact({
            "mp-test-0": [0.10, 0.30, 0.50, 0.40, 0.20],
            "mp-test-1": None,
            "mp-test-2": None,
        }),
    }
    return {"panel": panel, "artifacts": artifacts, "references": references}


def plans_of(synthetic: dict) -> list[dict]:
    return up.build_plans(synthetic["panel"], synthetic["artifacts"], deferred_indices=[])


# --- Anchor universe --------------------------------------------------------------

def test_anchor_universe_dense_extension_covers_every_image(synthetic):
    plans = plans_of(synthetic)
    for plan in plans:
        assert plan["dense_extension_applied"] is True
        assert plan["anchor_universe"] == list(range(plan["image_count"]))


def test_anchor_universe_no_extension_above_threshold():
    reference = [0.0, 0.1, 0.3, 0.5, 0.4, 0.2, 0.15, 0.05]
    panel = {"paths": [make_path(0, 8, reference)]}
    profile = [0.05, 0.2, 0.4, 0.5, 0.3, 0.1, 0.12, 0.0]  # min at 7, max at 3
    artifacts = {MODEL_A: make_artifact({"mp-test-0": profile})}
    plan = up.build_plans(panel, artifacts, deferred_indices=[])[0]
    expected = build_anchor_set(8, *select_extrema(profile))["anchor_indices"]
    assert plan["dense_extension_applied"] is False
    assert plan["anchor_universe"] == expected
    assert len(plan["anchor_universe"]) < 8


def test_per_model_selection_matches_frozen_logic(synthetic):
    plan = plans_of(synthetic)[0]
    for model, profile in (
        (MODEL_A, [0.50, 0.40, 0.30, 0.20, 0.10]),
        (MODEL_B, [0.10, 0.30, 0.50, 0.40, 0.20]),
    ):
        model_min, model_max = select_extrema(profile)
        frozen = build_anchor_set(5, model_min, model_max)
        assert plan["per_model"][model]["anchor_indices"] == frozen["anchor_indices"]
        assert plan["per_model"][model]["model_min_index"] == model_min
        assert plan["per_model"][model]["model_max_index"] == model_max
    assert plan["per_model"][MODEL_A]["anchor_indices"] == [0, 1, 2, 4]


def test_path_without_model_guidance_is_still_computable(synthetic):
    plan = plans_of(synthetic)[2]
    assert plan["per_model"] == {}
    assert set(plan["models_missing"]) == {MODEL_A, MODEL_B}
    # Dense extension still covers all images -> the path is computable.
    assert plan["anchor_universe"] == [0, 1, 2, 3, 4]


def test_deferred_paths_excluded(synthetic):
    plans = up.build_plans(synthetic["panel"], synthetic["artifacts"], deferred_indices=[1])
    assert [p["path_index"] for p in plans] == [0, 2]


# --- Compute loop: resume, memory guard, failure ------------------------------------

def completed_energy(reference: list[float]):
    offsets = [-0.010, -0.008, -0.002, -0.005, -0.012]

    def energy_fn(image_record: dict) -> float:
        j = image_record["image"]
        return reference[j] + offsets[j]

    return energy_fn, offsets


def test_compute_then_resume_skips_completed(synthetic, tmp_path):
    plans = plans_of(synthetic)
    reference = synthetic["references"][0]
    energy_fn, _ = completed_energy(reference)
    calls: list[int] = []

    def counting_fn(record: dict) -> float:
        calls.append(record["image"])
        return energy_fn(record)

    totals = up.compute_anchors(plans[:1], synthetic["panel"], tmp_path, 0, counting_fn)
    assert totals["computed"] == 5 and totals["resumed"] == 0
    assert sorted(calls) == [0, 1, 2, 3, 4]

    calls.clear()
    totals = up.compute_anchors(plans[:1], synthetic["panel"], tmp_path, 0, counting_fn)
    assert totals["resumed"] == 5 and totals["computed"] == 0
    assert calls == []

    checkpoint = json.loads(
        (tmp_path / "anchors" / "path-0" / "anchor-2.json").read_text()
    )
    for key in (
        "path_index", "anchor_index", "gpaw_energy_ev", "reference_energy_ev",
        "offset_ev", "wall_seconds", "gpaw_params", "status",
    ):
        assert key in checkpoint
    assert checkpoint["status"] == "completed"
    assert checkpoint["gpaw_params"]["mode"] == "fd"
    assert checkpoint["gpaw_params"]["h"] == 0.18
    assert checkpoint["gpaw_params"]["kpts"] == [2, 2, 2]
    assert checkpoint["offset_ev"] == pytest.approx(
        checkpoint["gpaw_energy_ev"] - checkpoint["reference_energy_ev"]
    )


def test_memory_guard_skips_and_later_retries(synthetic, tmp_path, monkeypatch):
    plans = plans_of(synthetic)
    energy_fn, _ = completed_energy(synthetic["references"][0])
    calls: list[int] = []

    def counting_fn(record: dict) -> float:
        calls.append(record["image"])
        return energy_fn(record)

    monkeypatch.setattr(up, "available_memory_bytes", lambda: 1 * 1024**3)
    totals = up.compute_anchors(
        plans[:1], synthetic["panel"], tmp_path, 3 * 1024**3, counting_fn
    )
    assert totals["skipped_memory"] == 5 and calls == []
    checkpoint = json.loads(
        (tmp_path / "anchors" / "path-0" / "anchor-0.json").read_text()
    )
    assert checkpoint["status"] == "skipped-memory"
    assert checkpoint["gpaw_energy_ev"] is None

    # Memory pressure gone: skipped anchors are retried, not treated as done.
    monkeypatch.setattr(up, "available_memory_bytes", lambda: 16 * 1024**3)
    totals = up.compute_anchors(
        plans[:1], synthetic["panel"], tmp_path, 3 * 1024**3, counting_fn
    )
    assert totals["computed"] == 5
    assert sorted(calls) == [0, 1, 2, 3, 4]


def test_failure_is_recorded_and_retried(synthetic, tmp_path):
    plans = plans_of(synthetic)
    energy_fn, _ = completed_energy(synthetic["references"][0])

    def flaky_fn(record: dict) -> float:
        if record["image"] == 3:
            raise RuntimeError("boom")
        return energy_fn(record)

    totals = up.compute_anchors(plans[:1], synthetic["panel"], tmp_path, 0, flaky_fn)
    assert totals["failed"] == 1 and totals["computed"] == 4
    checkpoint = json.loads(
        (tmp_path / "anchors" / "path-0" / "anchor-3.json").read_text()
    )
    assert checkpoint["status"] == "failed"
    assert "boom" in checkpoint["error"]

    totals = up.compute_anchors(plans[:1], synthetic["panel"], tmp_path, 0, energy_fn)
    assert totals["computed"] == 1 and totals["resumed"] == 4


# --- Receipt import -------------------------------------------------------------------

def receipt_for(plan: dict, indices: list[int], energy_fn) -> dict:
    return {
        "rows": [{
            "path_id": plan["path_id"],
            "status": "completed",
            "anchors": [
                {
                    "index": j,
                    "gpaw_energy_ev": energy_fn({"image": j}),
                    "reference_energy_ev": plan["reference_energies_ev"][j],
                    "offset_ev": energy_fn({"image": j}) - plan["reference_energies_ev"][j],
                }
                for j in indices
            ],
        }],
        "summary": {},
        "failures": [],
    }


def test_receipt_import_maps_to_checkpoints(synthetic, tmp_path):
    plans = plans_of(synthetic)
    plan = plans[0]
    energy_fn, _ = completed_energy(synthetic["references"][0])
    receipt = tmp_path / "path-0.json"
    receipt.write_text(json.dumps(receipt_for(plan, [0, 1, 2, 4], energy_fn)))

    stats = up.import_receipt(receipt, plan, tmp_path)
    assert stats["imported"] == [0, 1, 2, 4]
    assert stats["rejected"] == []
    for j in (0, 1, 2, 4):
        checkpoint = json.loads(
            (tmp_path / "anchors" / "path-0" / f"anchor-{j}.json").read_text()
        )
        assert checkpoint["status"] == "imported"
        assert checkpoint["gpaw_energy_ev"] == pytest.approx(energy_fn({"image": j}))
        assert checkpoint["offset_ev"] == pytest.approx(
            energy_fn({"image": j}) - plan["reference_energies_ev"][j]
        )
        assert checkpoint["source"].startswith("import:")

    # Re-import is a no-op for anchors already in the pool.
    stats = up.import_receipt(receipt, plan, tmp_path)
    assert stats["imported"] == [] and stats["skipped_existing"] == [0, 1, 2, 4]


def test_receipt_import_rejects_reference_mismatch(synthetic, tmp_path):
    plans = plans_of(synthetic)
    plan = plans[0]
    energy_fn, _ = completed_energy(synthetic["references"][0])
    bad = receipt_for(plan, [0, 1], energy_fn)
    bad["rows"][0]["anchors"][1]["reference_energy_ev"] += 0.1
    receipt = tmp_path / "path-0.json"
    receipt.write_text(json.dumps(bad))

    stats = up.import_receipt(receipt, plan, tmp_path)
    assert stats["imported"] == [0]
    assert len(stats["rejected"]) == 1 and "anchor 1" in stats["rejected"][0]


def test_receipt_import_rejects_wrong_path_id(synthetic, tmp_path):
    plans = plans_of(synthetic)
    energy_fn, _ = completed_energy(synthetic["references"][0])
    bad = receipt_for(plans[1], [0], energy_fn)  # receipt for path 1...
    receipt = tmp_path / "path-0.json"
    receipt.write_text(json.dumps(bad))
    stats = up.import_receipt(receipt, plans[0], tmp_path)  # ...imported as path 0
    assert stats["imported"] == []
    assert any("path_id mismatch" in r for r in stats["rejected"])


def test_imported_anchors_are_not_recomputed(synthetic, tmp_path):
    plans = plans_of(synthetic)
    energy_fn, _ = completed_energy(synthetic["references"][0])
    receipt = tmp_path / "receipts" / "path-0.json"
    receipt.parent.mkdir()
    receipt.write_text(json.dumps(receipt_for(plans[0], [0, 1, 2, 4], energy_fn)))

    results = up.import_receipts(tmp_path / "receipts", plans[:1], tmp_path)
    assert results[0]["imported"] == [0, 1, 2, 4]

    calls: list[int] = []

    def counting_fn(record: dict) -> float:
        calls.append(record["image"])
        return energy_fn(record)

    totals = up.compute_anchors(plans[:1], synthetic["panel"], tmp_path, 0, counting_fn)
    assert totals["resumed"] == 4 and totals["computed"] == 1
    assert calls == [3]  # only the image the receipt lacked


# --- Assembly ---------------------------------------------------------------------------

def fill_pool(synthetic: dict, workdir: Path, path_indices=(0, 1, 2)) -> None:
    plans = plans_of(synthetic)
    for i in path_indices:
        energy_fn, _ = completed_energy(synthetic["references"][i])
        up.compute_anchors(plans[i:i + 1], synthetic["panel"], workdir, 0, energy_fn)


def test_assembly_math(synthetic, tmp_path):
    fill_pool(synthetic, tmp_path)
    campaign = up.assemble_campaign(plans_of(synthetic), tmp_path, deferred_indices=[])
    path0 = campaign["per_path"][0]

    assert path0["dense_complete"] is True
    # GPAW = reference + offset; offsets span -2..-12 meV.
    assert path0["dense_barrier_ev"] == pytest.approx(0.408)
    assert path0["dense_vs_vasp_signed_error_mev"] == pytest.approx(8.0)
    assert path0["t1"]["evaluated_image_count"] == 5
    assert path0["t1"]["offset_mean_mev"] == pytest.approx(-7.4)
    assert path0["t1"]["offset_wander_mev"] == pytest.approx(10.0)
    # T1 gate: 10 meV wander is well under the 40 meV gate -> clean; the
    # residual wander is driven by images 4 (deepest, -12 meV) and 2.
    assert path0["t1_gate"] == {
        "wander_mev": pytest.approx(10.0),
        "verdict": "clean",
        "driver_pair": [4, 2],
    }
    assert campaign["t1_summary"]["paths_contaminated"] == 0
    assert campaign["t1_summary"]["contaminated_path_indices"] == []

    model_a = path0["per_model"][MODEL_A]
    assert model_a["complete"] is True
    assert model_a["sparse_barrier_ev"] == pytest.approx(0.408)
    assert model_a["same_engine_abs_error_mev"] == pytest.approx(0.0)
    assert model_a["vasp_abs_error_mev"] == pytest.approx(8.0)

    summary = campaign["per_model_summary"][MODEL_A]
    # Model A guides paths 0 and 1; both complete -> strong WIN on the
    # same-engine basis (sparse anchors catch the dense extrema here).
    assert summary["paths_guided"] == 2
    assert summary["same_engine_mae_mev"] == pytest.approx(0.0)
    assert summary["verdict"] == "strong_win"
    assert summary["strong_win"] is True and summary["win"] is True
    # Secondary VASP-referenced MAE is reported alongside, non-gating.
    # Path 0: sparse 0.408 vs reference 0.400 -> 8 meV; path 1: sparse 0.302
    # vs reference 0.300 -> 2 meV; MAE over both guided paths = 5 meV.
    assert summary["vasp_mae_mev"] == pytest.approx(5.0)

    # Path 2 has no model guidance: dense + T1 exist, per_model is empty.
    path2 = campaign["per_path"][2]
    assert path2["per_model"] == {}
    assert path2["dense_complete"] is True
    assert campaign["cost"]["anchors_evaluated"] == 15


def test_assembly_marks_incomplete_until_pool_is_full(synthetic, tmp_path):
    fill_pool(synthetic, tmp_path, path_indices=(0, 1))
    # Remove one anchor of path 0 that model A needs and the dense profile needs.
    (tmp_path / "anchors" / "path-0" / "anchor-4.json").unlink()
    campaign = up.assemble_campaign(plans_of(synthetic), tmp_path, deferred_indices=[])
    path0 = campaign["per_path"][0]
    assert path0["dense_complete"] is False
    assert path0["per_model"][MODEL_A]["complete"] is False
    assert "same_engine_abs_error_mev" not in path0["per_model"][MODEL_A]
    assert path0["anchors_missing"] == [4]
    # T1 uses whatever is evaluated.
    assert path0["t1"]["evaluated_image_count"] == 4
    assert path0["t1"]["offset_wander_mev"] == pytest.approx(8.0)
    assert path0["t1_gate"]["verdict"] == "clean"
    assert path0["t1_gate"]["driver_pair"] == [0, 2]
    summary = campaign["per_model_summary"][MODEL_A]
    assert summary["verdict"] == "incomplete"
    assert summary["win"] is False


def test_assembly_t1_gate_contaminated(synthetic, tmp_path):
    """A >40 meV offset wander flags the path convention-contaminated."""
    plans = plans_of(synthetic)
    reference = synthetic["references"][0]
    offsets = [-0.010, -0.008, -0.100, -0.005, -0.012]  # eV; 95 meV wander

    def energy_fn(image_record: dict) -> float:
        j = image_record["image"]
        return reference[j] + offsets[j]

    up.compute_anchors(plans[:1], synthetic["panel"], tmp_path, 0, energy_fn)
    campaign = up.assemble_campaign(plans, tmp_path, deferred_indices=[])
    path0 = campaign["per_path"][0]
    assert path0["t1_gate"]["wander_mev"] == pytest.approx(95.0)
    assert path0["t1_gate"]["verdict"] == "contaminated"
    # min offset -100 meV at image 2, max offset -5 meV at image 3.
    assert path0["t1_gate"]["driver_pair"] == [2, 3]
    summary = campaign["t1_summary"]
    assert summary["paths_contaminated"] == 1
    assert summary["contaminated_path_indices"] == [0]
    assert summary["max_offset_wander_mev"] == pytest.approx(95.0)


def test_assembly_t1_gate_insufficient_data_without_anchors(synthetic, tmp_path):
    campaign = up.assemble_campaign(plans_of(synthetic), tmp_path, deferred_indices=[])
    for path in campaign["per_path"]:
        assert path["t1_gate"] == {
            "wander_mev": None,
            "verdict": "insufficient_data",
            "driver_pair": None,
        }
    assert campaign["t1_summary"]["paths_contaminated"] == 0
    assert campaign["t1_summary"]["contaminated_path_indices"] == []


def test_dry_run_reports_done_and_todo(synthetic, tmp_path, capsys):
    fill_pool(synthetic, tmp_path, path_indices=(0,))
    report = up.dry_run(plans_of(synthetic), tmp_path, minutes_per_anchor=90.0)
    by_index = {r["path_index"]: r for r in report["per_path"]}
    assert by_index[0]["anchors_done"] == [0, 1, 2, 3, 4]
    assert by_index[0]["anchors_to_compute"] == []
    assert by_index[1]["anchors_to_compute"] == [0, 1, 2, 3, 4]
    assert by_index[2]["anchors_to_compute"] == [0, 1, 2, 3, 4]
    assert report["anchors_total"] == 15
    assert report["anchors_to_compute"] == 10
    assert report["estimated_hours"] == pytest.approx(15.0)
