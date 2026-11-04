from __future__ import annotations

import copy

import build_ni_publication_fixture as builder
import evaluate_ni_fixture_reference as evaluator
from local_artifacts import MISHIN_POTENTIAL, requires_local_artifact


def test_reference_evaluator_scores_fixture_rows() -> None:
    requires_local_artifact(MISHIN_POTENTIAL)
    manifest = builder.build_fixture(builder.load_source_packet())
    report = evaluator.evaluate_fixture(manifest)

    assert report["schema"] == "lupine.mlip.ni_fixture_reference_eval.v1"
    assert set(report["rows"]) == {
        "elastic_constants",
        "energy_volume",
        "forces",
        "stress",
        "relaxation_stability",
    }
    assert report["rows"]["energy_volume"]["score"] > 0.99
    assert report["rows"]["forces"]["score"] > 0.99
    assert report["rows"]["stress"]["score"] > 0.99
    assert report["rows"]["elastic_constants"]["metrics"]["primary_metric"] == "elastic_cij_mae_gpa"


def test_reference_calculator_loads_frozen_legacy_path_without_rewriting_metadata(
    tmp_path, monkeypatch
) -> None:
    fixture_path = (
        evaluator.ROOT / "gcp" / "mlip-cell-runner" / "fixtures"
        / "ni_fcc_eam_distill_support_v1.json"
    )
    manifest = evaluator.load_fixture(fixture_path)
    original = copy.deepcopy(manifest)
    recorded = manifest["reference_provenance"]["eam_reference"]["potential_file"]
    assert recorded == "atlas-distill/lammps_runs/Ni_Mishin-1999/Ni99.eam.alloy"

    captured = []
    sentinel = object()

    def fake_eam(*, potential):
        captured.append(potential)
        return sentinel

    monkeypatch.setattr(evaluator, "ROOT", tmp_path)
    monkeypatch.setattr(evaluator, "EAM", fake_eam)

    assert evaluator.reference_calculator(manifest) is sentinel
    assert captured == [
        str(tmp_path / "distill/lammps_runs/Ni_Mishin-1999/Ni99.eam.alloy")
    ]
    assert manifest == original
