"""Tests for the T1 convention-wander gate (t1_wander.py).

Covers synthetic clean/contaminated/boundary/degenerate cases plus the real
path-7 receipt (mp-770939_10_1_1_0_1, /tmp/z1-sparse-local/chgnet/path-7.json)
whose ~139 meV GPAW↔VASP offset wander motivated the gate (amendment 01).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from t1_wander import (  # noqa: E402
    GATE_MEV,
    analyze_offsets,
    offset_mev,
    spearman_rho,
)

# Real path-7 anchors, copied from /tmp/z1-sparse-local/chgnet/path-7.json
# (rows[0].anchors; recorded 2026-07-21, chgnet-guided, GPAW fd/h=0.18/
# kpts=(2,2,2)/PBE vs the panel's VASP reference). (index, gpaw, reference).
PATH7_ANCHORS = [
    (0, -339.6436421257205, -324.88751542),
    (1, -339.53605480499886, -324.8379344),
    (2, -339.19012055391545, -324.57336965),
    (4, -339.57424902897884, -324.9080875),
]
PATH7_RECEIPT = Path("/tmp/z1-sparse-local/chgnet/path-7.json")
PATH7_CHECKPOINTS = Path("/tmp/z1-union-local/anchors/path-7")


def images_from_offsets_mev(offsets_mev: list[float]) -> list[tuple[int, float, float]]:
    """Synthetic images: reference 0.0 eV everywhere, GPAW = offset."""
    return [(i, offset / 1000.0, 0.0) for i, offset in enumerate(offsets_mev)]


# --- Synthetic gate cases --------------------------------------------------------

def test_constant_offset_is_clean_with_zero_wander():
    report = analyze_offsets(images_from_offsets_mev([-15000.0, -15000.0, -15000.0]))
    assert report["verdict"] == "clean"
    assert report["offset_wander_mev"] == pytest.approx(0.0)
    assert report["offset_mean_mev"] == pytest.approx(-15000.0)
    assert report["offset_min_mev"] == pytest.approx(-15000.0)
    assert report["offset_max_mev"] == pytest.approx(-15000.0)
    # Degenerate driver: argmin == argmax == first image.
    assert report["driver_pair"] == [0, 0]
    # A constant offset has no trend and undefined monotonicity.
    assert report["trend_slope_mev_per_image"] == pytest.approx(0.0)
    assert report["spearman_rho"] is None
    for entry in report["per_image"]:
        assert entry["drift_mev"] == pytest.approx(0.0)


def test_wander_above_gate_is_contaminated_with_driver_pair():
    report = analyze_offsets(images_from_offsets_mev([-50.0, -10.0, -20.0, 30.0]))
    assert report["verdict"] == "contaminated"
    assert report["offset_wander_mev"] == pytest.approx(80.0)
    assert report["offset_mean_mev"] == pytest.approx(-12.5)
    # min offset -50 meV at image 0, max offset +30 meV at image 3.
    assert report["driver_pair"] == [0, 3]


def test_wander_exactly_at_gate_is_clean():
    report = analyze_offsets(images_from_offsets_mev([0.0, GATE_MEV]))
    assert report["offset_wander_mev"] == pytest.approx(GATE_MEV)
    assert report["verdict"] == "clean"


def test_gate_threshold_is_a_parameter():
    images = images_from_offsets_mev([-50.0, 30.0])  # 80 meV wander
    assert analyze_offsets(images, gate_mev=100.0)["verdict"] == "clean"
    assert analyze_offsets(images, gate_mev=80.0)["verdict"] == "clean"
    assert analyze_offsets(images, gate_mev=79.9)["verdict"] == "contaminated"


def test_empty_pool_is_insufficient_data():
    report = analyze_offsets([])
    assert report["verdict"] == "insufficient_data"
    assert report["image_count"] == 0
    assert report["offset_wander_mev"] is None
    assert report["offset_mean_mev"] is None
    assert report["driver_pair"] is None
    assert report["per_image"] == []


def test_single_image_is_insufficient_data():
    report = analyze_offsets(images_from_offsets_mev([-42.0]))
    assert report["verdict"] == "insufficient_data"
    assert report["image_count"] == 1
    assert report["offset_wander_mev"] == pytest.approx(0.0)
    assert report["offset_mean_mev"] == pytest.approx(-42.0)
    assert report["driver_pair"] is None
    assert report["trend_slope_mev_per_image"] is None


# --- Trend and monotonicity -------------------------------------------------------

def test_linear_offset_drift_is_recovered():
    # offsets = -14700 + 10 meV per image, exactly linear in the index.
    report = analyze_offsets(
        images_from_offsets_mev([-14700.0, -14690.0, -14680.0, -14670.0])
    )
    assert report["trend_intercept_mev"] == pytest.approx(-14700.0)
    assert report["trend_slope_mev_per_image"] == pytest.approx(10.0)
    assert report["spearman_rho"] == pytest.approx(1.0)
    assert report["verdict"] == "clean"  # wander 30 meV <= 40
    for entry in report["per_image"]:
        assert entry["drift_mev"] == pytest.approx(0.0)


def test_monotonic_decrease_gives_spearman_minus_one():
    report = analyze_offsets(images_from_offsets_mev([-10.0, -20.0, -30.0]))
    assert report["spearman_rho"] == pytest.approx(-1.0)
    assert report["trend_slope_mev_per_image"] == pytest.approx(-10.0)


def test_two_points_have_no_spearman():
    assert spearman_rho([0.0, 1.0], [5.0, 7.0]) is None


def test_non_contiguous_indices_are_honored():
    # Same linear law as above but on path-7's real index set {0, 1, 2, 4}.
    images = [(i, (-14700.0 + 10.0 * i) / 1000.0, 0.0) for i in (0, 1, 2, 4)]
    report = analyze_offsets(images)
    assert report["trend_slope_mev_per_image"] == pytest.approx(10.0)
    assert report["trend_intercept_mev"] == pytest.approx(-14700.0)
    assert report["spearman_rho"] == pytest.approx(1.0)
    assert report["offset_wander_mev"] == pytest.approx(40.0)
    assert report["verdict"] == "clean"


def test_unsorted_input_is_sorted_by_index():
    shuffled = [PATH7_ANCHORS[2], PATH7_ANCHORS[0], PATH7_ANCHORS[3], PATH7_ANCHORS[1]]
    report = analyze_offsets(shuffled)
    assert [e["index"] for e in report["per_image"]] == [0, 1, 2, 4]


# --- Real path-7 receipt ----------------------------------------------------------

def test_real_path7_anchors_are_contaminated():
    report = analyze_offsets(PATH7_ANCHORS)
    assert report["image_count"] == 4
    assert report["verdict"] == "contaminated"
    # Amendment 01 records "~139 meV" wander; recomputed value stands.
    assert report["offset_wander_mev"] == pytest.approx(139.375801805, abs=1e-6)
    assert report["offset_mean_mev"] == pytest.approx(-14684.2898859, abs=1e-6)
    # The wander is driven by images 0 (deepest offset) and 2 (shallowest).
    assert report["driver_pair"] == [0, 2]
    assert report["offset_min_mev"] == pytest.approx(-14756.1267057, abs=1e-6)
    assert report["offset_max_mev"] == pytest.approx(-14616.7509039, abs=1e-6)
    # Offsets drift shallow-to-deep along the path (rank correlation 0.8).
    assert report["spearman_rho"] == pytest.approx(0.8)
    assert report["trend_slope_mev_per_image"] == pytest.approx(22.144, abs=1e-3)


@pytest.mark.skipif(not PATH7_RECEIPT.is_file(), reason="path-7 receipt not present")
def test_embedded_path7_anchors_match_the_receipt():
    receipt = json.loads(PATH7_RECEIPT.read_text(encoding="utf-8"))
    anchors = receipt["rows"][0]["anchors"]
    images = [(a["index"], a["gpaw_energy_ev"], a["reference_energy_ev"]) for a in anchors]
    assert [list(t) for t in images] == [list(t) for t in PATH7_ANCHORS]
    # The receipt's recorded offset_ev equals our recomputation, and the
    # recorded 118.8 meV barrier error coexists with a contaminated gate —
    # the motivational pair for the writeup.
    for anchor in anchors:
        assert anchor["offset_ev"] == pytest.approx(
            offset_mev(anchor["gpaw_energy_ev"], anchor["reference_energy_ev"]) / 1000.0
        )
    assert receipt["rows"][0]["absolute_error_ev"] == pytest.approx(0.1188, abs=1e-4)
    assert analyze_offsets(images)["verdict"] == "contaminated"


@pytest.mark.skipif(
    not PATH7_CHECKPOINTS.is_dir(), reason="imported path-7 checkpoints not present"
)
def test_imported_path7_checkpoints_agree_with_the_receipt():
    images = []
    for checkpoint_path in sorted(PATH7_CHECKPOINTS.glob("anchor-*.json")):
        checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
        images.append(
            (
                checkpoint["anchor_index"],
                checkpoint["gpaw_energy_ev"],
                checkpoint["reference_energy_ev"],
            )
        )
    assert [list(t) for t in images] == [list(t) for t in PATH7_ANCHORS]
    assert analyze_offsets(images)["offset_wander_mev"] == pytest.approx(
        139.375801805, abs=1e-6
    )
