from __future__ import annotations

import hashlib
import json
from pathlib import Path

import mlip_cell_runner as runner
import numpy as np
import pytest
from ase.calculators.calculator import Calculator, all_changes
from test_z2_soc_tc import ReferenceEnergyEngine, panel_fixture
from z1_barrier import canonical_content_hash
from z2_soc_tc import GPAWSpinEnergyEngine, load_campaign_panel

ROOT = Path(__file__).resolve().parents[2]


class ZeroForceCalculator(Calculator):
    implemented_properties = ["energy", "forces"]

    def calculate(self, atoms=None, properties=("energy",), system_changes=all_changes):
        super().calculate(atoms, properties, system_changes)
        self.results = {"energy": 0.0, "forces": np.zeros((len(atoms), 3))}


class ImmediateOptimizer:
    calls = 0

    def __init__(self, atoms, logfile=None):
        self.atoms = atoms

    def run(self, *, fmax: float, steps: int) -> bool:
        type(self).calls += 1
        return True


class ScalarCalculator:
    def __init__(self, ordering: str):
        self.ordering = ordering
        self.scalar_total = {"fm": -10.0, "afm": -9.9}[ordering]


def test_gpaw_engine_relaxes_once_and_emits_force_theorem_corrected_energies() -> None:
    material = panel_fixture()["materials"][0]
    protocol = {
        "geometry_force_convergence_ev_per_angstrom": 0.05,
        "geometry_maximum_steps": 20,
    }
    ImmediateOptimizer.calls = 0
    observed_magmoms: dict[str, list[float]] = {}

    def scalar_factory(atoms, ordering, frozen_protocol):
        assert frozen_protocol is protocol
        observed_magmoms[ordering] = atoms.get_initial_magnetic_moments().tolist()
        return ScalarCalculator(ordering)

    def scalar_energy(calc, atoms):
        return calc.scalar_total

    def band_energy(calc, *, theta, phi, scale):
        if scale == 0.0:
            return 5.0
        shifts = {
            "fm": {(90.0, 0.0): 0.002, (90.0, 90.0): 0.003, (0.0, 0.0): 0.001},
            "afm": {(90.0, 0.0): 0.004, (90.0, 90.0): 0.005, (0.0, 0.0): 0.006},
        }
        return 5.0 + shifts[calc.ordering][(theta, phi)]

    engine = GPAWSpinEnergyEngine(
        ZeroForceCalculator(),
        protocol,
        scalar_calculator_factory=scalar_factory,
        scalar_energy=scalar_energy,
        soc_band_energy=band_energy,
        optimizer_factory=ImmediateOptimizer,
    )

    fm = engine.evaluate_ordering(material, "fm")
    afm = engine.evaluate_ordering(material, "afm")

    assert ImmediateOptimizer.calls == 1
    assert observed_magmoms["fm"] == [3.0, 3.0]
    assert observed_magmoms["afm"] == [3.0, -3.0]
    assert fm["parallel_energy_ev"] == pytest.approx(-9.998)
    assert fm["y_energy_ev"] == pytest.approx(-9.997)
    assert fm["perpendicular_energy_ev"] == pytest.approx(-9.999)
    assert afm["parallel_energy_ev"] == pytest.approx(-9.896)
    assert afm["perpendicular_energy_ev"] == pytest.approx(-9.894)
    assert fm["soc_method"] == "non-selfconsistent_force_theorem"


@pytest.mark.parametrize(
    "mlip_id", ["chgnet", "mace-mp-small", "mace-mp-medium", "mace-mpa-0-medium"]
)
def test_repository_z2_campaign_lock_is_consumable(mlip_id: str) -> None:
    manifest_path = ROOT / "campaigns" / "v1" / "z2.campaign-manifest.v1.json"

    manifest, panel, manifest_hash, contract = load_campaign_panel(
        str(manifest_path), mlip_id, lambda path: Path(path).read_bytes()
    )

    assert manifest_hash == manifest["content_hash"]
    assert len(panel["materials"]) == 7
    assert contract["release_ready"] is True
    assert contract["material_count"] == 7


def test_z2_panel_lock_tampering_fails_closed(tmp_path: Path) -> None:
    panel_path = tmp_path / "data" / "candidates" / "z2_soc_tc_panel.lock.json"
    panel_path.parent.mkdir(parents=True)
    panel_path.write_bytes(
        (ROOT / "data" / "candidates" / "z2_soc_tc_panel.lock.json").read_bytes() + b" "
    )
    manifest_path = tmp_path / "campaigns" / "v1" / "z2.campaign-manifest.v1.json"
    manifest_path.parent.mkdir(parents=True)
    manifest_path.write_bytes(
        (ROOT / "campaigns" / "v1" / "z2.campaign-manifest.v1.json").read_bytes()
    )

    with pytest.raises(ValueError, match="candidate panel sha256 mismatch"):
        load_campaign_panel(str(manifest_path), "chgnet", lambda path: Path(path).read_bytes())


def test_z2_stale_manifest_is_rejected_before_panel_loading(tmp_path: Path) -> None:
    manifest = json.loads(
        (ROOT / "campaigns" / "v1" / "z2.campaign-manifest.v1.json").read_text(
            encoding="utf-8"
        )
    )
    manifest["campaign_id"] = "stale-z2"
    manifest["content_hash"] = canonical_content_hash(manifest)
    manifest_path = tmp_path / "campaigns" / "v1" / "z2.json"
    manifest_path.parent.mkdir(parents=True)
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ValueError, match="not the current reviewed manifest"):
        load_campaign_panel(str(manifest_path), "chgnet", lambda path: Path(path).read_bytes())


def test_mlip_cell_runner_dispatches_locked_soc_tc_row(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest_path = ROOT / "campaigns" / "v1" / "z2.campaign-manifest.v1.json"
    artifact_prefix = tmp_path / "artifacts"
    monkeypatch.setattr(runner, "runtime_versions", lambda: {})
    monkeypatch.setenv(
        "RUNNER_IMAGE_DIGEST",
        "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    )
    monkeypatch.setenv(
        "RUNNER_IMAGE_URI",
        "us-central1-docker.pkg.dev/lupine/z2/runner@sha256:" + "a" * 64,
    )
    monkeypatch.setattr(
        runner,
        "GPAWSpinEnergyEngine",
        lambda geometry_calculator, protocol: ReferenceEnergyEngine(),
        raising=False,
    )
    args = runner.parse_args(
        [
            "run-cell",
            "--run-id",
            "unit-z2",
            "--cell-id",
            "unit-z2:soc-tc:chgnet",
            "--row-id",
            "soc_tc",
            "--mlip-id",
            "chgnet",
            "--manifest-url",
            str(manifest_path),
            "--artifact-prefix",
            str(artifact_prefix),
            "--checkpoint-mode",
            "off",
        ]
    )

    result = runner.run_cell(args, preloaded_calc=ZeroForceCalculator())

    assert result.metrics["n_structures"] == 7
    assert result.metrics["row_metrics"]["measurement_complete"] is True
    assert result.metrics["execution"]["calculator_dtype"] == "float64"
    artifact = json.loads((artifact_prefix / "cell_result.json").read_text(encoding="utf-8"))
    assert len(artifact["predictions"]) == 7
    assert {item["status"] for item in artifact["predictions"]} == {"completed"}
    assert artifact["execution"]["runner_image_digest"] == "sha256:" + "a" * 64
    assert artifact["campaign_id"] == "discovery.round-4.z2-magnetic-anisotropy.v1"


def test_mlip_cell_runner_refuses_z2_without_immutable_image_digest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("RUNNER_IMAGE_DIGEST", raising=False)
    monkeypatch.delenv("RUNNER_IMAGE_URI", raising=False)
    args = runner.parse_args(
        [
            "run-cell",
            "--run-id",
            "unit-z2",
            "--cell-id",
            "unit-z2:soc-tc:chgnet",
            "--row-id",
            "soc_tc",
            "--mlip-id",
            "chgnet",
            "--manifest-url",
            str(ROOT / "campaigns" / "v1" / "z2.campaign-manifest.v1.json"),
            "--artifact-prefix",
            str(tmp_path / "artifacts"),
            "--checkpoint-mode",
            "off",
        ]
    )

    with pytest.raises(ValueError, match="RUNNER_IMAGE_DIGEST"):
        runner.run_cell(args, preloaded_calc=ZeroForceCalculator())

    assert not (tmp_path / "artifacts" / "cell_result.json").exists()


def test_z2_checkpoint_refuses_cross_image_prediction_reuse(tmp_path: Path) -> None:
    checkpoint_path = tmp_path / "cell_checkpoint.json"
    common = {
        "url": str(checkpoint_path),
        "run_id": "unit-z2",
        "cell_id": "unit-z2:soc-tc:chgnet",
        "row_id": "soc_tc",
        "mlip_id": "chgnet",
        "variant_id": "baseline",
        "distill_profile": "off",
        "manifest_hash": "sha256:" + "1" * 64,
        "calculator_dtype": "float64",
    }
    material = panel_fixture()["materials"][0]
    writer = runner.CellCheckpoint(
        mode="write-only", runner_image_digest="sha256:" + "a" * 64, **common
    )
    writer.record_prediction(
        "soc_tc", 0, material, {"material_id": material["material_id"], "status": "completed"}
    )
    writer.flush(force=True)

    reader = runner.CellCheckpoint(
        mode="read-only", runner_image_digest="sha256:" + "b" * 64, **common
    )

    assert reader.get_prediction("soc_tc", 0, material) is None
    assert reader.ignored_reason == "checkpoint_context_mismatch"
