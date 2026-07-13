"""LAMMPS ingest tests: parsers, evidence payload, Lean emission, CLI, backend.

The happy paths run on the committed synthetic sample logs under
``hpc/examples/sample_logs/`` so tests and demo exercise the same fixtures.
"""

from __future__ import annotations

import hashlib
import json
import pathlib

import pytest
from lupine_distill import lammps_ingest
from lupine_distill.backends.lammps import LammpsEvidenceBackend
from lupine_distill.lammps_ingest import (
    build_evidence,
    emit_lean_module,
    parse_elastic_log,
    parse_thermo_log,
)
from lupine_distill.runner import build_backend, run_suite
from lupine_distill.schemas import LAMMPS_EVIDENCE_SCHEMA, LammpsEvidence
from pydantic import ValidationError

_REPO = pathlib.Path(__file__).resolve().parents[2]
_SAMPLES = _REPO / "hpc" / "examples" / "sample_logs"

_NI_REFS = {"C11": 246.5, "C12": 147.3, "C44": 124.7}


def _elastic_text() -> str:
    return (_SAMPLES / "ni_eam_elastic.log").read_text(encoding="utf-8")


def _thermo_text() -> str:
    return (_SAMPLES / "ni_eam_thermo.log").read_text(encoding="utf-8")


def _evidence(**overrides: object) -> LammpsEvidence:
    kwargs: dict = {
        "material": "Ni",
        "potential_id": "Ni_u3.eam",
        "references": _NI_REFS,
        "reference_source": "Simmons & Wang 1971",
    }
    kwargs.update(overrides)
    return build_evidence(_elastic_text(), **kwargs)


# --------------------------------------------------------------------------- #
# parse_elastic_log
# --------------------------------------------------------------------------- #


@pytest.mark.unit
def test_parse_elastic_happy_path_on_sample_log() -> None:
    props = parse_elastic_log(_elastic_text())
    assert props["C11"].value == 246.79
    assert props["C12"].value == 147.32
    assert props["C44"].value == 124.85
    assert props["C11"].unit == "GPa"
    assert props["bulk_modulus"].value == 180.48
    assert props["shear_modulus_2"].value == 49.74
    assert props["poisson_ratio"].unit == "dimensionless"
    assert props["lattice_constant"].value == 3.5199
    assert props["lattice_constant"].unit == "Angstrom"
    assert props["cohesive_energy"].value == -4.4499
    # All 21 Cij lines are picked up, not just the cubic triple.
    assert "C56" in props


@pytest.mark.unit
def test_parse_elastic_rejects_noise_listing_all_missing() -> None:
    with pytest.raises(ValueError) as excinfo:
        parse_elastic_log("Step PotEng\n0 -1.0\nTotal wall time: 0:00:01\n")
    message = str(excinfo.value)
    assert "C11" in message and "C12" in message and "C44" in message


@pytest.mark.unit
def test_parse_elastic_lists_only_what_is_missing() -> None:
    partial = "Elastic Constant C11all = 246.79 GPa\nElastic Constant C12all = 147.32 GPa\n"
    with pytest.raises(ValueError) as excinfo:
        parse_elastic_log(partial)
    message = str(excinfo.value)
    assert "C44" in message
    assert "'C11'" not in message


# --------------------------------------------------------------------------- #
# parse_thermo_log
# --------------------------------------------------------------------------- #


@pytest.mark.unit
def test_parse_thermo_happy_path_on_sample_log() -> None:
    summary = parse_thermo_log(_thermo_text())
    assert summary.n_rows == 6
    assert summary.first_step == 0
    assert summary.last_step == 500
    assert summary.columns == ["Step", "Temp", "PotEng", "KinEng", "TotEng", "Press"]
    assert summary.energy_column == "PotEng"
    assert summary.initial_energy == -1423.9917
    assert summary.final_energy == -1423.9459
    assert summary.energy_drift_per_step == pytest.approx((-1423.9459 + 1423.9917) / 500)
    assert summary.final_values["Temp"] == 298.90
    assert "Step" not in summary.final_values


@pytest.mark.unit
def test_parse_thermo_stops_at_non_numeric_row() -> None:
    # The elastic sample's minimization block ends at "Loop time of ...".
    summary = parse_thermo_log(_elastic_text())
    assert summary.n_rows == 3
    assert summary.last_step == 25


@pytest.mark.unit
def test_parse_thermo_rejects_log_without_section() -> None:
    with pytest.raises(ValueError, match="no thermo section"):
        parse_thermo_log("LAMMPS (2 Aug 2023)\nunits metal\n")


@pytest.mark.unit
def test_parse_thermo_rejects_header_without_rows() -> None:
    with pytest.raises(ValueError, match="no thermo section"):
        parse_thermo_log("Step PotEng\nLoop time of 1.0 on 1 procs\n")


# --------------------------------------------------------------------------- #
# build_evidence
# --------------------------------------------------------------------------- #


@pytest.mark.unit
def test_build_evidence_payload_shape() -> None:
    evidence = _evidence()
    assert evidence.schema_version == LAMMPS_EVIDENCE_SCHEMA
    assert evidence.material == "Ni"
    assert evidence.source.lammps_version == "LAMMPS (2 Aug 2023 - Update 3)"
    assert evidence.provenance.log_sha256 == hashlib.sha256(
        _elastic_text().encode("utf-8")
    ).hexdigest()
    assert evidence.provenance.parsed_at is None  # never read from the clock
    by_name = {p.name: p for p in evidence.properties}
    assert by_name["C11"].reference_value == 246.5
    assert by_name["C11"].reference_source == "Simmons & Wang 1971"
    # Un-referenced properties carry neither a reference nor a citation.
    assert by_name["bulk_modulus"].reference_value is None
    assert by_name["bulk_modulus"].reference_source is None


@pytest.mark.unit
def test_build_evidence_rejects_unknown_reference_name() -> None:
    with pytest.raises(ValueError, match="C99"):
        _evidence(references={"C99": 1.0})


@pytest.mark.unit
def test_evidence_json_round_trip_carries_schema_key() -> None:
    evidence = _evidence()
    dumped = evidence.model_dump(mode="json", by_alias=True)
    assert dumped["schema"] == LAMMPS_EVIDENCE_SCHEMA
    rebuilt = LammpsEvidence.model_validate_json(json.dumps(dumped))
    assert rebuilt == evidence


@pytest.mark.unit
def test_evidence_rejects_wrong_schema_string() -> None:
    dumped = _evidence().model_dump(mode="json", by_alias=True)
    dumped["schema"] = "lupine.mlip.lammps_evidence.v0"
    with pytest.raises(ValidationError):
        LammpsEvidence.model_validate(dumped)


# --------------------------------------------------------------------------- #
# emit_lean_module
# --------------------------------------------------------------------------- #


@pytest.mark.unit
def test_emit_lean_module_within_tolerance(tmp_path: pathlib.Path) -> None:
    out = emit_lean_module([_evidence()], tmp_path / "Ni.lean")
    text = out.read_text(encoding="utf-8")
    assert "AUTHORED by lupine_distill.lammps_ingest" in text
    sha12 = hashlib.sha256(_elastic_text().encode("utf-8")).hexdigest()[:12]
    assert sha12 in text
    assert "namespace Lupine.LammpsEvidence.Ni" in text
    assert "end Lupine.LammpsEvidence.Ni" in text
    # C11: |246.79 - 246.5| = 0.29 -> 290; tol 5% of 246.5 -> 12325.
    assert "theorem lammps_within_tol_Ni_Ni_u3_eam_C11 : 290 ≤ 12325 := by decide" in text
    # Exactly one theorem per referenced property, verdict never hidden.
    assert text.count(":= by decide") == 3
    assert "sorry" not in text.replace("0 sorry", "")


@pytest.mark.unit
def test_emit_lean_module_encodes_exceeds_tolerance(tmp_path: pathlib.Path) -> None:
    evidence = _evidence(references={"C11": 200.0})  # |246.79-200| far beyond 5%
    text = emit_lean_module([evidence], tmp_path / "Ni.lean").read_text(encoding="utf-8")
    # err 46.79 -> 46790; tol 10.0 -> 10000.
    assert "theorem lammps_exceeds_tol_Ni_Ni_u3_eam_C11 : 10000 < 46790 := by decide" in text


@pytest.mark.unit
def test_emit_lean_module_requires_references(tmp_path: pathlib.Path) -> None:
    with pytest.raises(ValueError, match="nothing to prove"):
        emit_lean_module([_evidence(references=None)], tmp_path / "Ni.lean")


@pytest.mark.unit
def test_emit_lean_module_rejects_negative_tolerance(tmp_path: pathlib.Path) -> None:
    with pytest.raises(ValueError):
        emit_lean_module([_evidence()], tmp_path / "Ni.lean", tolerance_pct=-1.0)


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #


@pytest.mark.integration
def test_cli_parse_then_lean_round_trip(tmp_path: pathlib.Path) -> None:
    evidence_path = tmp_path / "evidence.json"
    rc = lammps_ingest.main(
        [
            "parse",
            str(_SAMPLES / "ni_eam_elastic.log"),
            "--material", "Ni",
            "--potential", "Ni_u3.eam",
            "--ref", "C11=246.5",
            "--ref", "C12=147.3",
            "--ref", "C44=124.7",
            "--ref-source", "Simmons & Wang 1971",
            "--thermo-log", str(_SAMPLES / "ni_eam_thermo.log"),
            "-o", str(evidence_path),
        ]
    )
    assert rc == 0
    evidence = LammpsEvidence.model_validate_json(evidence_path.read_text(encoding="utf-8"))
    assert evidence.trajectory is not None and evidence.trajectory.n_rows == 6

    lean_path = tmp_path / "Ni.lean"
    rc = lammps_ingest.main(["lean", str(evidence_path), "-o", str(lean_path)])
    assert rc == 0
    assert ":= by decide" in lean_path.read_text(encoding="utf-8")


@pytest.mark.integration
def test_cli_parse_thermo_kind(capsys: pytest.CaptureFixture[str]) -> None:
    rc = lammps_ingest.main(
        [
            "parse",
            str(_SAMPLES / "ni_eam_thermo.log"),
            "--material", "Ni",
            "--potential", "Ni_u3.eam",
            "--kind", "thermo",
        ]
    )
    assert rc == 0
    evidence = LammpsEvidence.model_validate_json(capsys.readouterr().out)
    assert evidence.properties == []
    assert evidence.trajectory is not None and evidence.trajectory.energy_column == "PotEng"


@pytest.mark.integration
def test_cli_parse_unrecognizable_log_returns_2(
    tmp_path: pathlib.Path, capsys: pytest.CaptureFixture[str]
) -> None:
    bad = tmp_path / "noise.log"
    bad.write_text("not a lammps log\n", encoding="utf-8")
    rc = lammps_ingest.main(
        ["parse", str(bad), "--material", "Ni", "--potential", "Ni_u3.eam"]
    )
    assert rc == 2
    assert "C11" in capsys.readouterr().err


@pytest.mark.integration
def test_cli_parse_bad_ref_returns_2(capsys: pytest.CaptureFixture[str]) -> None:
    rc = lammps_ingest.main(
        [
            "parse",
            str(_SAMPLES / "ni_eam_elastic.log"),
            "--material", "Ni",
            "--potential", "Ni_u3.eam",
            "--ref", "C11=not-a-number",
        ]
    )
    assert rc == 2
    assert "not a number" in capsys.readouterr().err


# --------------------------------------------------------------------------- #
# LAMMPS file-evidence backend
# --------------------------------------------------------------------------- #


def _evidence_dir(tmp_path: pathlib.Path) -> pathlib.Path:
    root = tmp_path / "evidence"
    root.mkdir()
    evidence = _evidence(
        references={**_NI_REFS, "cohesive_energy": -4.44},
        trajectory=parse_thermo_log(_thermo_text()),
    )
    payload = json.dumps(evidence.model_dump(mode="json", by_alias=True))
    (root / "ni_eam.json").write_text(payload, encoding="utf-8")
    return root


@pytest.mark.unit
def test_backend_maps_property_errors_to_metrics(tmp_path: pathlib.Path) -> None:
    backend = build_backend("lammps", model_id="Ni_u3.eam", evidence_dir=_evidence_dir(tmp_path))
    assert isinstance(backend, LammpsEvidenceBackend)
    assert backend.backend_id == "lammps"
    assert backend.engine_version == "LAMMPS (2 Aug 2023 - Update 3)"

    metrics = backend.run({}, "elastic_constants")
    # Mean abs error over the three referenced GPa constants: (0.29+0.02+0.15)/3.
    assert metrics.mae_stress == pytest.approx((0.29 + 0.02 + 0.15) / 3)
    # Cohesive energy is the only referenced eV property: |-4.4499 - -4.44|.
    assert metrics.mae_energy == pytest.approx(0.0099)
    assert metrics.dft_reference is not None and metrics.dft_reference["C11"] == 246.5
    assert metrics.wall_time_seconds == 0.0

    # Drift-weighted benchmark picks up the trajectory summary.
    md = backend.run({}, "nvt_md_300k")
    assert md.energy_drift == pytest.approx(abs(-1423.9459 + 1423.9917) / 500)
    # A benchmark with no matching evidence yields an empty metric, not a crash.
    assert backend.run({}, "phonon_dos").mae_forces is None


@pytest.mark.unit
def test_backend_run_suite_reports_lammps_backend(tmp_path: pathlib.Path) -> None:
    backend = LammpsEvidenceBackend(evidence_dir=_evidence_dir(tmp_path))
    result = run_suite(backend=backend, model_id="Ni_u3.eam", distill_version=0, suite="full")
    assert result.backend == "lammps"
    assert result.torchsim_version == "LAMMPS (2 Aug 2023 - Update 3)"
    assert set(result.results) == {
        "static_energy", "geometry_opt", "nvt_md_300k", "nvt_md_1000k",
        "elastic_constants", "phonon_dos", "eos_curve", "surface_energy",
    }


@pytest.mark.unit
def test_backend_unknown_benchmark_raises(tmp_path: pathlib.Path) -> None:
    backend = LammpsEvidenceBackend(evidence_dir=_evidence_dir(tmp_path))
    with pytest.raises(ValueError, match="unknown benchmark"):
        backend.run({}, "does_not_exist")


@pytest.mark.unit
def test_backend_empty_dir_raises(tmp_path: pathlib.Path) -> None:
    with pytest.raises(ValueError, match="no lammps_evidence"):
        LammpsEvidenceBackend(evidence_dir=tmp_path)


@pytest.mark.unit
def test_build_backend_lammps_without_dir_and_no_fallback_raises() -> None:
    with pytest.raises(ValueError, match="evidence_dir"):
        build_backend("lammps", model_id="m", allow_mock_fallback=False)
