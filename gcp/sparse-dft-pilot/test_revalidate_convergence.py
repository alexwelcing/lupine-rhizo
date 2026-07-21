"""Tests for the convergence-revalidation runner (revalidate_convergence.py).

No GPAW is touched: the energy function is injected/monkeypatched, the panel
and the path-16 receipt are synthetic, and every filesystem effect lands
under pytest's tmp_path. Covers receipt schema validation (path_id, anchors,
reference profile, frozen-selection/window consistency, barrier consistency),
the variant compute loop (checkpoints, resume, memory guard, failure retry),
the barrier math on both variants, the PASS/FAIL 5 meV adoption criterion,
and the CLI (--dry-run, real run, --assemble-only).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import revalidate_convergence as rc  # noqa: E402
import union_pilot as up  # noqa: E402

PATH_ID = "mp-test-16"
REFERENCE = [0.00, 0.10, 0.40, 0.20, 0.05]
MODEL_MIN, MODEL_MAX = 4, 0  # mirrors the real path-7 receipt shape
ANCHORS = [0, 1, 2, 4]  # build_anchor_set(5, 4, 0), window=2 short-path fallback
FROZEN_OFFSETS = {0: -0.010, 1: -0.008, 2: -0.002, 4: -0.012}

# Variant energy shifts vs the frozen energies (eV), per anchor image.
# G: barrier moves +1 meV -> PASS. H: saddle image up 12 meV -> FAIL.
G_SHIFTS = {0: +0.001, 1: -0.002, 2: +0.002, 4: 0.000}
H_SHIFTS = {0: 0.000, 1: 0.000, 2: +0.012, 4: 0.000}


def frozen_energy(j: int) -> float:
    return REFERENCE[j] + FROZEN_OFFSETS[j]


FROZEN_BARRIER = max(frozen_energy(j) for j in ANCHORS) - min(
    frozen_energy(j) for j in ANCHORS
)  # 0.398 - (-0.010) = 0.408 eV


def fake_energy(image_record: dict, params: dict) -> float:
    """Param-keyed fake GPAW; also pins the 'all other settings frozen' contract."""
    assert params["mode"] == "fd" and params["xc"] == "PBE" and params["txt"] is None
    j = image_record["image"]
    if tuple(params["kpts"]) == (1, 1, 1):
        assert params["h"] == 0.18
        return frozen_energy(j) + G_SHIFTS[j]
    if params["h"] == 0.20:
        assert tuple(params["kpts"]) == (2, 2, 2)
        return frozen_energy(j) + H_SHIFTS[j]
    raise AssertionError(f"unexpected params {params}")


# --- Synthetic fixtures -----------------------------------------------------------

def make_panel() -> dict:
    return {
        "paths": [{
            "path_id": PATH_ID,
            "chemical_system": "C-Co-Li-Na-O-P",
            "input_images": [{"image": j} for j in range(5)],
            "reference": {"energies_ev": REFERENCE},
            "reference_barrier_ev": max(REFERENCE) - min(REFERENCE),
        }]
    }


def make_receipt(**row_overrides) -> dict:
    row = {
        "path_id": PATH_ID,
        "chemical_system": "C-Co-Li-Na-O-P",
        "status": "completed",
        "model_min_index": MODEL_MIN,
        "model_max_index": MODEL_MAX,
        "window": 2,
        "short_path_fallback": True,
        "anchor_count": len(ANCHORS),
        "anchors": [
            {
                "index": j,
                "gpaw_energy_ev": frozen_energy(j),
                "reference_energy_ev": REFERENCE[j],
                "offset_ev": frozen_energy(j) - REFERENCE[j],
            }
            for j in ANCHORS
        ],
        "sparse_barrier_ev": FROZEN_BARRIER,
        "reference_barrier_ev": max(REFERENCE) - min(REFERENCE),
    }
    row.update(row_overrides)
    return {"rows": [row], "summary": {}, "failures": []}


@pytest.fixture()
def panel() -> dict:
    return make_panel()


@pytest.fixture()
def receipt_path(tmp_path) -> Path:
    path = tmp_path / "path-16.json"
    path.write_text(json.dumps(make_receipt()))
    return path


def target_of(receipt_path: Path, panel: dict) -> dict:
    return rc.load_revalidation_target(receipt_path, panel, path_index=0)


def compute_all(target: dict, panel: dict, workdir: Path, energy_fn=fake_energy) -> dict:
    return rc.compute_variants(
        target, panel, workdir, 0, list(rc.VARIANTS), energy_fn, log=lambda *_: None
    )


# --- Receipt validation -------------------------------------------------------------

def test_target_validation_ok(receipt_path, panel):
    target = target_of(receipt_path, panel)
    assert target["path_id"] == PATH_ID
    assert target["chemical_system"] == "C-Co-Li-Na-O-P"
    assert target["anchor_indices"] == ANCHORS
    assert target["window"] == 2
    assert target["short_path_fallback"] is True
    assert target["frozen_barrier_ev"] == pytest.approx(0.408)
    assert target["anchors"][2]["gpaw_energy_ev"] == pytest.approx(0.398)
    assert target["anchors"][2]["reference_energy_ev"] == pytest.approx(0.40)


def test_reject_wrong_path_id(tmp_path, panel):
    bad = tmp_path / "path-16.json"
    bad.write_text(json.dumps(make_receipt(path_id="mp-other-99")))
    with pytest.raises(rc.ReceiptError, match="path_id"):
        target_of(bad, panel)


def test_reject_missing_anchors(tmp_path, panel):
    for override in ({"anchors": []}, {"anchors": None}):
        bad = tmp_path / "path-16.json"
        bad.write_text(json.dumps(make_receipt(**override)))
        with pytest.raises(rc.ReceiptError, match="no anchors"):
            target_of(bad, panel)
    receipt = make_receipt()
    del receipt["rows"][0]["anchors"]
    bad.write_text(json.dumps(receipt))
    with pytest.raises(rc.ReceiptError, match="no anchors"):
        target_of(bad, panel)


def test_reject_malformed_and_duplicate_anchors(tmp_path, panel):
    receipt = make_receipt()
    receipt["rows"][0]["anchors"][1] = {"index": "1", "gpaw_energy_ev": 0.1}
    bad = tmp_path / "path-16.json"
    bad.write_text(json.dumps(receipt))
    with pytest.raises(rc.ReceiptError, match="malformed anchor"):
        target_of(bad, panel)

    receipt = make_receipt()
    receipt["rows"][0]["anchors"].append(receipt["rows"][0]["anchors"][0])
    bad.write_text(json.dumps(receipt))
    with pytest.raises(rc.ReceiptError, match="duplicate anchor"):
        target_of(bad, panel)


def test_reject_reference_mismatch(tmp_path, panel):
    receipt = make_receipt()
    receipt["rows"][0]["anchors"][1]["reference_energy_ev"] += 0.1
    bad = tmp_path / "path-16.json"
    bad.write_text(json.dumps(receipt))
    with pytest.raises(rc.ReceiptError, match="anchor 1: reference"):
        target_of(bad, panel)


def test_reject_anchor_set_and_window_mismatch(tmp_path, panel):
    # Dropping anchor 4 breaks equality with the frozen selection.
    receipt = make_receipt()
    receipt["rows"][0]["anchors"] = receipt["rows"][0]["anchors"][:3]
    bad = tmp_path / "path-16.json"
    bad.write_text(json.dumps(receipt))
    with pytest.raises(rc.ReceiptError, match="anchor set"):
        target_of(bad, panel)

    bad.write_text(json.dumps(make_receipt(window=1)))
    with pytest.raises(rc.ReceiptError, match="window"):
        target_of(bad, panel)

    bad.write_text(json.dumps(make_receipt(short_path_fallback=False)))
    with pytest.raises(rc.ReceiptError, match="short_path_fallback"):
        target_of(bad, panel)


def test_reject_inconsistent_sparse_barrier(tmp_path, panel):
    bad = tmp_path / "path-16.json"
    bad.write_text(json.dumps(make_receipt(sparse_barrier_ev=FROZEN_BARRIER + 0.05)))
    with pytest.raises(rc.ReceiptError, match="sparse_barrier_ev"):
        target_of(bad, panel)


def test_reject_non_completed_row(tmp_path, panel):
    bad = tmp_path / "path-16.json"
    bad.write_text(json.dumps(make_receipt(status="failed")))
    with pytest.raises(rc.ReceiptError, match="status"):
        target_of(bad, panel)


# --- Compute loop: checkpoints, resume, memory guard, failure ---------------------------

def test_compute_checkpoints_then_resume(receipt_path, panel, tmp_path):
    target = target_of(receipt_path, panel)
    calls = []

    def counting(image_record, params):
        calls.append(image_record["image"])
        return fake_energy(image_record, params)

    totals = compute_all(target, panel, tmp_path, counting)
    assert totals["variant-g"]["computed"] == 4
    assert totals["variant-h"]["computed"] == 4
    assert len(calls) == 8

    checkpoint = json.loads((tmp_path / "variant-g" / "anchor-2.json").read_text())
    assert checkpoint["schema"] == rc.SCHEMA_ANCHOR
    assert checkpoint["status"] == "completed"
    assert checkpoint["variant"] == "variant-g"
    assert checkpoint["variant_label"] == "G"
    assert checkpoint["variant_energy_ev"] == pytest.approx(0.400)
    assert checkpoint["frozen_gpaw_energy_ev"] == pytest.approx(0.398)
    assert checkpoint["shift_vs_frozen_ev"] == pytest.approx(0.002)
    assert checkpoint["gpaw_params"]["kpts"] == [1, 1, 1]
    assert checkpoint["gpaw_params"]["h"] == 0.18
    assert checkpoint["gpaw_params"]["mode"] == "fd"

    checkpoint = json.loads((tmp_path / "variant-h" / "anchor-2.json").read_text())
    assert checkpoint["gpaw_params"]["kpts"] == [2, 2, 2]
    assert checkpoint["gpaw_params"]["h"] == 0.20
    assert checkpoint["variant_energy_ev"] == pytest.approx(0.410)

    calls.clear()
    totals = compute_all(target, panel, tmp_path, counting)
    assert all(t["resumed"] == 4 and t["computed"] == 0 for t in totals.values())
    assert calls == []


def test_memory_guard_skips_then_retries(receipt_path, panel, tmp_path, monkeypatch):
    target = target_of(receipt_path, panel)
    monkeypatch.setattr(up, "available_memory_bytes", lambda: 1 * 1024**3)
    totals = rc.compute_variants(
        target, panel, tmp_path, 3 * 1024**3, list(rc.VARIANTS), fake_energy,
        log=lambda *_: None,
    )
    assert all(t["skipped_memory"] == 4 for t in totals.values())
    checkpoint = json.loads((tmp_path / "variant-g" / "anchor-0.json").read_text())
    assert checkpoint["status"] == "skipped-memory"
    assert checkpoint["variant_energy_ev"] is None

    monkeypatch.setattr(up, "available_memory_bytes", lambda: 16 * 1024**3)
    totals = rc.compute_variants(
        target, panel, tmp_path, 3 * 1024**3, list(rc.VARIANTS), fake_energy,
        log=lambda *_: None,
    )
    assert all(t["computed"] == 4 for t in totals.values())


def test_failure_recorded_and_retried(receipt_path, panel, tmp_path):
    target = target_of(receipt_path, panel)
    attempts = set()

    def flaky(image_record, params):
        j = image_record["image"]
        if j == 2 and tuple(params["kpts"]) == (1, 1, 1) and j not in attempts:
            attempts.add(j)
            raise RuntimeError("scf did not converge")
        return fake_energy(image_record, params)

    totals = compute_all(target, panel, tmp_path, flaky)
    assert totals["variant-g"]["failed"] == 1
    assert totals["variant-h"]["computed"] == 4
    checkpoint = json.loads((tmp_path / "variant-g" / "anchor-2.json").read_text())
    assert checkpoint["status"] == "failed"
    assert "scf did not converge" in checkpoint["error"]

    info = rc.assemble_variant(target, tmp_path, "variant-g")
    assert info["complete"] is False
    assert info["anchors_missing"] == [2]
    assert info["verdict"] == "incomplete"
    assert info["sparse_barrier_ev"] is None

    totals = compute_all(target, panel, tmp_path, flaky)
    assert totals["variant-g"]["computed"] == 1
    assert totals["variant-g"]["resumed"] == 3
    assert rc.assemble_variant(target, tmp_path, "variant-g")["complete"] is True


# --- Barrier math and the 5 meV adoption criterion ----------------------------------------

def test_barrier_math_and_verdicts(receipt_path, panel, tmp_path):
    target = target_of(receipt_path, panel)
    compute_all(target, panel, tmp_path)
    report = rc.build_report(target, tmp_path, list(rc.VARIANTS), receipt_path, tmp_path)

    assert report["frozen"]["sparse_barrier_ev"] == pytest.approx(0.408)
    assert report["frozen"]["gpaw_params"] == {
        "mode": "fd", "xc": "PBE", "h": 0.18, "kpts": [2, 2, 2], "txt": None,
    }
    assert report["adoption_threshold_mev"] == 5.0

    variant_g = report["variants"]["variant-g"]
    assert variant_g["complete"] is True
    assert variant_g["sparse_barrier_ev"] == pytest.approx(0.409)
    assert variant_g["delta_vs_frozen_mev"] == pytest.approx(+1.0)
    assert variant_g["abs_delta_vs_frozen_mev"] == pytest.approx(1.0)
    assert variant_g["verdict"] == "PASS"
    assert variant_g["adoptable"] is True

    variant_h = report["variants"]["variant-h"]
    assert variant_h["complete"] is True
    assert variant_h["sparse_barrier_ev"] == pytest.approx(0.420)
    assert variant_h["delta_vs_frozen_mev"] == pytest.approx(+12.0)
    assert variant_h["verdict"] == "FAIL"
    assert variant_h["adoptable"] is False

    assert report["both_adoptable"] is False

    # Per-anchor tables: every anchor row carries both energies and the shift.
    for info in report["variants"].values():
        assert [a["anchor_index"] for a in info["anchors"]] == ANCHORS
        for anchor in info["anchors"]:
            assert anchor["status"] == "completed"
            assert anchor["variant_energy_ev"] is not None
            expected = (
                G_SHIFTS if info["label"] == "G" else H_SHIFTS
            )[anchor["anchor_index"]]
            assert anchor["shift_vs_frozen_mev"] == pytest.approx(expected * 1000.0)


def test_report_incomplete_without_checkpoints(receipt_path, panel, tmp_path):
    target = target_of(receipt_path, panel)
    report = rc.build_report(target, tmp_path, list(rc.VARIANTS), receipt_path, tmp_path)
    for info in report["variants"].values():
        assert info["verdict"] == "incomplete"
        assert info["complete"] is False
        assert info["anchors_missing"] == ANCHORS
        assert info["sparse_barrier_ev"] is None
        assert info["adoptable"] is None
        assert all(a["status"] == "missing" for a in info["anchors"])
    assert report["both_adoptable"] is None


# --- CLI: --dry-run, real run, --assemble-only ----------------------------------------------

def write_local(tmp_path) -> Path:
    local = tmp_path / "inputs"
    local.mkdir()
    (local / "panel.lock.json").write_text(json.dumps(make_panel()))
    return local


def test_main_dry_run(receipt_path, tmp_path, monkeypatch, capsys):
    local = write_local(tmp_path)
    workdir = tmp_path / "work"
    monkeypatch.setattr(sys, "argv", [
        "revalidate_convergence.py",
        "--receipt", str(receipt_path), "--local", str(local),
        "--workdir", str(workdir), "--path-index", "0", "--dry-run",
    ])
    assert rc.main() == 0
    out = capsys.readouterr().out
    assert "todo=[0, 1, 2, 4]" in out
    assert "8 GPAW evaluations to compute" in out

    target = target_of(receipt_path, make_panel())
    compute_all(target, make_panel(), workdir)
    monkeypatch.setattr(sys, "argv", [
        "revalidate_convergence.py",
        "--receipt", str(receipt_path), "--local", str(local),
        "--workdir", str(workdir), "--path-index", "0", "--dry-run",
    ])
    assert rc.main() == 0
    out = capsys.readouterr().out
    assert "todo=[]" in out
    assert "0 GPAW evaluations to compute" in out


def test_main_real_run_then_assemble_only(receipt_path, tmp_path, monkeypatch, capsys):
    local = write_local(tmp_path)
    workdir = tmp_path / "work"
    calls = []

    def counting(image_record, params):
        calls.append(image_record["image"])
        return fake_energy(image_record, params)

    monkeypatch.setattr(rc, "gpaw_energy", counting)
    argv = [
        "revalidate_convergence.py",
        "--receipt", str(receipt_path), "--local", str(local),
        "--workdir", str(workdir), "--path-index", "0",
        "--min-free-gb", "0",  # the guard has its own test; don't depend on free RAM
    ]
    monkeypatch.setattr(sys, "argv", argv)
    assert rc.main() == 0
    assert len(calls) == 8

    report = json.loads((workdir / "revalidation-report.json").read_text())
    assert report["schema"] == rc.SCHEMA_REPORT
    assert report["path_id"] == PATH_ID
    assert report["variants"]["variant-g"]["verdict"] == "PASS"
    assert report["variants"]["variant-h"]["verdict"] == "FAIL"
    assert report["both_adoptable"] is False
    assert report["report_sha256"].startswith("sha256:")
    out = capsys.readouterr().out
    assert "variant-g" in out and "PASS" in out
    assert "variant-h" in out and "FAIL" in out

    # --assemble-only recomputes the verdict from checkpoints; no energy calls.
    calls.clear()
    (workdir / "revalidation-report.json").unlink()
    monkeypatch.setattr(sys, "argv", argv + ["--assemble-only"])
    assert rc.main() == 0
    assert calls == []
    report = json.loads((workdir / "revalidation-report.json").read_text())
    assert report["variants"]["variant-g"]["sparse_barrier_ev"] == pytest.approx(0.409)
    assert report["variants"]["variant-h"]["verdict"] == "FAIL"


# --- Codex P2 regressions ------------------------------------------------------


def test_stale_checkpoint_identity_rejected(receipt_path, panel, tmp_path):
    target = target_of(receipt_path, panel)
    totals = compute_all(target, panel, tmp_path)
    assert totals["variant-g"]["computed"] == 4

    dest = tmp_path / "variant-g" / "anchor-2.json"
    checkpoint = json.loads(dest.read_text())
    checkpoint["path_id"] = "mp-someone-else"
    dest.write_text(json.dumps(checkpoint))

    totals = compute_all(target, panel, tmp_path)
    assert totals["variant-g"]["computed"] == 1  # stale checkpoint recomputed
    assert totals["variant-g"]["resumed"] == 3
    restored = json.loads(dest.read_text())
    assert restored["path_id"] == PATH_ID


def test_subset_variants_never_reports_both_adoptable(receipt_path, panel, tmp_path):
    target = target_of(receipt_path, panel)
    rc.compute_variants(
        target, panel, tmp_path, 0, ["variant-g"], fake_energy, log=lambda *_: None
    )
    report = rc.build_report(target, tmp_path, ["variant-g"], receipt_path, tmp_path)
    assert report["variants"]["variant-g"]["adoptable"] is True
    assert report["both_adoptable"] is None
