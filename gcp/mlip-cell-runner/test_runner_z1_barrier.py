from __future__ import annotations

import hashlib
import json
from pathlib import Path

import mlip_cell_runner as runner
import numpy as np
import pytest
from ase.calculators.calculator import Calculator, all_changes
from z1_barrier import load_campaign_panel, run_barrier_row

REGISTERED_Z1_MODELS = (
    "chgnet",
    "mace-mp-small",
    "mace-mp-medium",
    "mace-mpa-0-medium",
)
ROOT = Path(__file__).resolve().parents[2]


class FrozenProfileCalculator(Calculator):
    implemented_properties = ["energy", "forces"]

    def calculate(self, atoms=None, properties=("energy",), system_changes=all_changes):
        super().calculate(atoms, properties, system_changes)
        x = float(atoms.positions[0, 0])
        self.results = {
            "energy": max(0.0, 1.0 - abs(x - 1.0)),
            "forces": np.zeros((len(atoms), 3)),
        }


def _image(x: float) -> dict:
    return {
        "symbols": ["H"],
        "positions_angstrom": [[x, 0.0, 0.0]],
        "cell_angstrom": [[5.0, 0.0, 0.0], [0.0, 5.0, 0.0], [0.0, 0.0, 5.0]],
        "pbc": [True, True, True],
    }


def _write_locked_campaign(tmp_path: Path) -> Path:
    panel_path = tmp_path / "data" / "candidates" / "z1-panel.json"
    panel_path.parent.mkdir(parents=True)
    panel = {
        "schema": "lupine.z1.neb_barrier_panel.v1",
        "panel_id": "unit-z1-panel",
        "measurement": {"metric": "barrier_mae", "unit": "meV", "minimum_path_count": 1},
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
        "paths": [
            {
                "path_id": "unit-path",
                "material_id": "unit-material",
                "chemical_system": "H",
                "reference_barrier_ev": 0.98,
                "input_images": [_image(0.0), _image(1.0), _image(2.0)],
            }
        ],
    }
    panel_bytes = (json.dumps(panel, indent=2, sort_keys=True) + "\n").encode()
    panel_path.write_bytes(panel_bytes)

    manifest = {
        "campaign_id": "unit-z1-campaign",
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


@pytest.mark.parametrize("mlip_id", REGISTERED_Z1_MODELS)
def test_registered_z1_models_run_locked_barrier_panel(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mlip_id: str
) -> None:
    manifest_path = _write_locked_campaign(tmp_path)
    artifact_prefix = tmp_path / "artifacts" / mlip_id
    monkeypatch.setattr(runner, "runtime_versions", lambda: {})
    args = runner.parse_args(
        [
            "run-cell",
            "--run-id", "unit-run",
            "--cell-id", f"unit-run:barrier:{mlip_id}",
            "--row-id", "barrier",
            "--mlip-id", mlip_id,
            "--manifest-url", str(manifest_path),
            "--artifact-prefix", str(artifact_prefix),
            "--checkpoint-mode", "off",
        ]
    )

    result = runner.run_cell(args, preloaded_calc=FrozenProfileCalculator())

    assert result.accuracy_unit == "row_native_physical_score"
    assert result.metrics["n_structures"] == 1
    assert result.metrics["row_metrics"] == {
        "primary_metric": "barrier_mae_mev",
        "barrier_mae_mev": pytest.approx(20.0),
        "completed_path_count": 1,
        "failed_path_count": 0,
        "minimum_path_count": 1,
        "measurement_complete": True,
        "acceptance_threshold_mev": 40.0,
    }
    artifact = json.loads((artifact_prefix / "cell_result.json").read_text(encoding="utf-8"))
    prediction = artifact["predictions"][0]
    assert prediction["status"] == "completed"
    assert prediction["predicted_barrier_ev"] == pytest.approx(1.0)
    assert prediction["signed_error_mev"] == pytest.approx(20.0)
    assert prediction["absolute_error_mev"] == pytest.approx(20.0)
    assert prediction["endpoint_initial_converged"] is True
    assert prediction["endpoint_final_converged"] is True
    assert prediction["neb_converged"] is True


def test_campaign_manifest_content_hash_mismatch_fails_closed(tmp_path: Path) -> None:
    manifest_path = _write_locked_campaign(tmp_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["campaign_id"] = "tampered"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ValueError, match="CampaignManifest content_hash mismatch"):
        load_campaign_panel(str(manifest_path), "chgnet", runner.read_url)


def test_candidate_panel_sha_mismatch_fails_closed(tmp_path: Path) -> None:
    manifest_path = _write_locked_campaign(tmp_path)
    panel_path = tmp_path / "data" / "candidates" / "z1-panel.json"
    panel_path.write_bytes(panel_path.read_bytes() + b" ")

    with pytest.raises(ValueError, match="candidate panel sha256 mismatch"):
        load_campaign_panel(str(manifest_path), "chgnet", runner.read_url)


@pytest.mark.parametrize("mlip_id", REGISTERED_Z1_MODELS)
def test_repository_z1_campaign_lock_is_consumable_by_registered_job(mlip_id: str) -> None:
    manifest_path = ROOT / "campaigns" / "v1" / "z1.campaign-manifest.v1.json"

    _, panel, _, contract = load_campaign_panel(
        str(manifest_path), mlip_id, runner.read_url
    )

    assert len(panel["paths"]) == 30
    assert contract["path_count"] == 30
    catalog = json.loads(
        (ROOT / "gcp" / "mlip-cell-runner" / "backend_catalog.json").read_text(
            encoding="utf-8"
        )
    )
    jobs = {
        backend["mlip_id"]: backend["target_job"] for backend in catalog["backends"]
    }
    assert jobs[mlip_id] in {
        "mlip-cell-chgnet",
        "mlip-cell-mace-mp-small",
        "mlip-cell-mace-mp-medium",
        "mlip-cell-mace-mpa-0-medium",
    }


def test_failed_path_is_reported_without_imputation(tmp_path: Path) -> None:
    manifest_path = _write_locked_campaign(tmp_path)
    manifest, panel, _, contract = load_campaign_panel(
        str(manifest_path), "chgnet", runner.read_url
    )
    failed_path = json.loads(json.dumps(panel["paths"][0]))
    failed_path["path_id"] = "invalid-path"
    del failed_path["input_images"][1]["positions_angstrom"]
    panel["paths"].append(failed_path)
    panel["measurement"]["minimum_path_count"] = 2

    result = run_barrier_row(manifest, panel, FrozenProfileCalculator(), contract)

    assert result["score"] == 0.0
    assert result["metrics"]["barrier_mae_mev"] == pytest.approx(20.0)
    assert result["metrics"]["completed_path_count"] == 1
    assert result["metrics"]["failed_path_count"] == 1
    assert result["metrics"]["measurement_complete"] is False
    failure = result["predictions"][1]
    assert failure["status"] == "failed"
    assert failure["path_id"] == "invalid-path"
    assert "predicted_barrier_ev" not in failure
    assert "signed_error_mev" not in failure
