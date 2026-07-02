"""CalcEvidence tests: schema round-trip, canonical-input hashing, Lean emission.

Covers the ASE-calculator/GPU evidence lane: ``lupine.mlip.calc_evidence.v1``
payloads must validate exactly like the LAMMPS ones (frozen, extra="forbid",
``"schema"`` alias key) and must flow through ``emit_lean_module`` into the
same decidable Nat-inequality theorem style, including explicit per-property
tolerance overrides for near-zero references (e.g. stacking-fault energies).
"""

from __future__ import annotations

import hashlib
import json
import pathlib

import pytest
from lupine_distill import lammps_ingest
from lupine_distill.calc_evidence import build_calc_evidence, canonical_inputs_sha256
from lupine_distill.lammps_ingest import build_evidence, emit_lean_module
from lupine_distill.schemas import (
    CALC_EVIDENCE_SCHEMA,
    CalcEvidence,
    CalcProvenance,
    CalcSource,
    LammpsEvidence,
    LammpsPropertyValue,
    LammpsProvenance,
    LammpsSource,
    PropertyValue,
)
from pydantic import ValidationError

_REPO = pathlib.Path(__file__).resolve().parents[2]
_SAMPLES = _REPO / "hpc" / "examples" / "sample_logs"

_INPUTS = {"structure": "fcc-Ni-108at", "kpts": [4, 4, 4], "fmax": 0.01}


def _prop(
    name: str,
    value: float,
    unit: str,
    ref: float,
    tolerance: float | None = None,
) -> PropertyValue:
    return PropertyValue(
        name=name,
        value=value,
        unit=unit,
        reference_value=ref,
        reference_source="DFT (PBE) reference set",
        tolerance=tolerance,
    )


def _calc_evidence(properties: list[PropertyValue] | None = None) -> CalcEvidence:
    return build_calc_evidence(
        material="Ni",
        model_id="MACE-MP-0-small",
        device="cuda",
        inputs=_INPUTS,
        properties=properties
        if properties is not None
        else [
            _prop("E_vac", 1.65, "eV", 1.60),
            _prop("gamma_111", 2.08, "J/m^2", 2.00),
            _prop("B0", 186.0, "GPa", 181.0),
        ],
        calculator_version="mace 0.3.6",
        run_label="gpu-discovery-01",
    )


# --------------------------------------------------------------------------- #
# Schema: round-trip, alias, frozen, extra="forbid", pattern validation
# --------------------------------------------------------------------------- #


@pytest.mark.unit
def test_property_value_alias_is_the_lammps_model() -> None:
    # Reuse, not a copy: one property model shared by both evidence lanes.
    assert PropertyValue is LammpsPropertyValue


@pytest.mark.unit
def test_calc_evidence_json_round_trip_carries_schema_key() -> None:
    evidence = _calc_evidence()
    assert evidence.schema_version == CALC_EVIDENCE_SCHEMA
    dumped = evidence.model_dump(mode="json", by_alias=True)
    assert dumped["schema"] == "lupine.mlip.calc_evidence.v1"
    rebuilt = CalcEvidence.model_validate_json(json.dumps(dumped))
    assert rebuilt == evidence


@pytest.mark.unit
def test_calc_evidence_rejects_wrong_schema_string() -> None:
    dumped = _calc_evidence().model_dump(mode="json", by_alias=True)
    dumped["schema"] = "lupine.mlip.calc_evidence.v0"
    with pytest.raises(ValidationError):
        CalcEvidence.model_validate(dumped)


@pytest.mark.unit
def test_calc_models_are_frozen() -> None:
    evidence = _calc_evidence()
    with pytest.raises(ValidationError):
        evidence.material = "Cu"  # type: ignore[misc]
    with pytest.raises(ValidationError):
        evidence.source.model_id = "other"  # type: ignore[misc]
    with pytest.raises(ValidationError):
        evidence.provenance.run_label = "x"  # type: ignore[misc]


@pytest.mark.unit
def test_calc_source_rejects_extra_fields() -> None:
    with pytest.raises(ValidationError):
        CalcSource(model_id="m", device="cpu", bogus=1)  # type: ignore[call-arg]


@pytest.mark.unit
def test_calc_provenance_rejects_extra_fields() -> None:
    with pytest.raises(ValidationError):
        CalcProvenance(inputs_sha256="a" * 64, bogus=1)  # type: ignore[call-arg]


@pytest.mark.unit
def test_calc_evidence_rejects_extra_fields() -> None:
    dumped = _calc_evidence().model_dump(mode="json", by_alias=True)
    dumped["bogus"] = 1
    with pytest.raises(ValidationError):
        CalcEvidence.model_validate(dumped)


@pytest.mark.unit
@pytest.mark.parametrize(
    "bad_sha",
    ["abc", "A" * 64, "g" * 64, "a" * 63, "a" * 65],
    ids=["short", "uppercase", "non-hex", "63-chars", "65-chars"],
)
def test_calc_provenance_rejects_bad_inputs_sha256(bad_sha: str) -> None:
    with pytest.raises(ValidationError):
        CalcProvenance(inputs_sha256=bad_sha)


@pytest.mark.unit
def test_calc_source_rejects_unknown_device() -> None:
    with pytest.raises(ValidationError):
        CalcSource(model_id="m", device="tpu")  # type: ignore[arg-type]


@pytest.mark.unit
def test_property_value_rejects_negative_tolerance() -> None:
    with pytest.raises(ValidationError):
        _prop("gamma_SFE", 12.0, "mJ/m^2", 10.0, tolerance=-1.0)


@pytest.mark.unit
def test_property_value_tolerance_defaults_none_for_v1_payloads() -> None:
    # A v1 payload without the key still validates; old behavior preserved.
    prop = PropertyValue.model_validate(
        {"name": "C11", "value": 246.79, "unit": "GPa", "reference_value": 246.5}
    )
    assert prop.tolerance is None


# --------------------------------------------------------------------------- #
# build_calc_evidence: canonical-input hashing, clock discipline
# --------------------------------------------------------------------------- #


@pytest.mark.unit
def test_builder_hashes_canonical_json_of_inputs() -> None:
    evidence = _calc_evidence()
    canonical = json.dumps(
        _INPUTS, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    )
    expected = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    assert evidence.provenance.inputs_sha256 == expected
    assert canonical_inputs_sha256(_INPUTS) == expected


@pytest.mark.unit
def test_input_hash_is_key_order_independent() -> None:
    reordered = {"fmax": 0.01, "structure": "fcc-Ni-108at", "kpts": [4, 4, 4]}
    assert canonical_inputs_sha256(reordered) == canonical_inputs_sha256(_INPUTS)


@pytest.mark.unit
def test_builder_rejects_unserializable_inputs() -> None:
    with pytest.raises(ValueError, match="JSON"):
        build_calc_evidence(
            material="Ni",
            model_id="m",
            device="cpu",
            inputs={"obj": object()},
            properties=[],
        )


@pytest.mark.unit
def test_builder_rejects_nan_inputs() -> None:
    with pytest.raises(ValueError, match="JSON"):
        build_calc_evidence(
            material="Ni",
            model_id="m",
            device="cpu",
            inputs={"x": float("nan")},
            properties=[],
        )


@pytest.mark.unit
def test_builder_never_reads_the_clock() -> None:
    assert _calc_evidence().provenance.computed_at is None


# --------------------------------------------------------------------------- #
# emit_lean_module from CalcEvidence
# --------------------------------------------------------------------------- #


@pytest.mark.unit
def test_emit_lean_from_calc_evidence(tmp_path: pathlib.Path) -> None:
    evidence = _calc_evidence()
    text = emit_lean_module([evidence], tmp_path / "Ni_calc.lean").read_text(encoding="utf-8")
    assert "AUTHORED by lupine_distill.lammps_ingest" in text
    assert "from calculator evidence" in text
    sha12 = evidence.provenance.inputs_sha256[:12]
    assert f"Ni/MACE-MP-0-small inputs sha256 {sha12}" in text
    assert "namespace Lupine.CalcEvidence.Ni" in text
    assert "end Lupine.CalcEvidence.Ni" in text
    # E_vac: |1.65-1.60| -> 50; 5% of 1.60 -> 80.
    assert "theorem calc_within_tol_Ni_MACE_MP_0_small_E_vac : 50 ≤ 80 := by decide" in text
    # gamma_111: |2.08-2.00| -> 80; 5% of 2.00 -> 100.
    assert "theorem calc_within_tol_Ni_MACE_MP_0_small_gamma_111 : 80 ≤ 100 := by decide" in text
    # B0: |186-181| -> 5000; 5% of 181 -> 9050.
    assert "theorem calc_within_tol_Ni_MACE_MP_0_small_B0 : 5000 ≤ 9050 := by decide" in text
    assert text.count(":= by decide") == 3
    assert "Machine-checked from calculator evidence" in text
    assert "sorry" not in text.replace("0 sorry", "")


@pytest.mark.unit
def test_new_property_names_sanitize_to_valid_theorem_names(tmp_path: pathlib.Path) -> None:
    props = [
        _prop("E_vac", 1.0, "eV", 1.0),
        _prop("gamma_100", 2.0, "J/m^2", 2.0),
        _prop("gamma_SFE", 10.0, "mJ/m^2", 10.0),
        _prop("B0", 100.0, "GPa", 100.0),
        _prop("dH_f", -0.5, "eV/atom", -0.5),
    ]
    text = emit_lean_module([_calc_evidence(props)], tmp_path / "Names.lean").read_text(
        encoding="utf-8"
    )
    for name in ("E_vac", "gamma_100", "gamma_SFE", "B0", "dH_f"):
        assert f"calc_within_tol_Ni_MACE_MP_0_small_{name} : 0 ≤" in text


@pytest.mark.unit
def test_explicit_tolerance_override_respected(tmp_path: pathlib.Path) -> None:
    # 5% of a 10 mJ/m^2 SFE reference is 0.5 -- degenerate. Explicit absolute
    # tolerance of 5.0 mJ/m^2 turns the same 2.0 error into a within verdict.
    without = _calc_evidence([_prop("gamma_SFE", 12.0, "mJ/m^2", 10.0)])
    text = emit_lean_module([without], tmp_path / "A.lean").read_text(encoding="utf-8")
    assert "theorem calc_exceeds_tol_Ni_MACE_MP_0_small_gamma_SFE : 500 < 2000 := by decide" in text

    with_tol = _calc_evidence([_prop("gamma_SFE", 12.0, "mJ/m^2", 10.0, tolerance=5.0)])
    text = emit_lean_module([with_tol], tmp_path / "B.lean").read_text(encoding="utf-8")
    assert "theorem calc_within_tol_Ni_MACE_MP_0_small_gamma_SFE : 2000 ≤ 5000 := by decide" in text
    assert "(explicit)" in text


@pytest.mark.unit
def test_zero_reference_requires_explicit_tolerance(tmp_path: pathlib.Path) -> None:
    # 5% of a 0.0 reference is 0: everything nonzero "exceeds". The explicit
    # override is the only sound way to bound formation-energy-style values.
    bare = _calc_evidence([_prop("dH_f", 0.02, "eV/atom", 0.0)])
    text = emit_lean_module([bare], tmp_path / "A.lean").read_text(encoding="utf-8")
    assert "theorem calc_exceeds_tol_Ni_MACE_MP_0_small_dH_f : 0 < 20 := by decide" in text

    bounded = _calc_evidence([_prop("dH_f", 0.02, "eV/atom", 0.0, tolerance=0.05)])
    text = emit_lean_module([bounded], tmp_path / "B.lean").read_text(encoding="utf-8")
    assert "theorem calc_within_tol_Ni_MACE_MP_0_small_dH_f : 20 ≤ 50 := by decide" in text


@pytest.mark.unit
def test_lammps_payload_honors_tolerance_override_too(tmp_path: pathlib.Path) -> None:
    evidence = LammpsEvidence(
        material="Ni",
        source=LammpsSource(potential_id="Ni_u3.eam"),
        properties=[
            LammpsPropertyValue(
                name="gamma_SFE",
                value=12.0,
                unit="mJ/m^2",
                reference_value=10.0,
                tolerance=5.0,
            )
        ],
        provenance=LammpsProvenance(log_sha256="a" * 64),
    )
    text = emit_lean_module([evidence], tmp_path / "L.lean").read_text(encoding="utf-8")
    assert "theorem lammps_within_tol_Ni_Ni_u3_eam_gamma_SFE : 2000 ≤ 5000 := by decide" in text


@pytest.mark.unit
def test_calc_evidence_without_references_nothing_to_prove(tmp_path: pathlib.Path) -> None:
    unreferenced = PropertyValue(name="E_vac", value=1.65, unit="eV")
    with pytest.raises(ValueError, match="nothing to prove"):
        emit_lean_module([_calc_evidence([unreferenced])], tmp_path / "X.lean")


@pytest.mark.unit
def test_mixed_lammps_and_calc_payloads_share_a_module(tmp_path: pathlib.Path) -> None:
    lammps_evidence = build_evidence(
        (_SAMPLES / "ni_eam_elastic.log").read_text(encoding="utf-8"),
        material="Ni",
        potential_id="Ni_u3.eam",
        references={"C11": 246.5},
    )
    text = emit_lean_module(
        [lammps_evidence, _calc_evidence()], tmp_path / "Mixed.lean"
    ).read_text(encoding="utf-8")
    assert "namespace Lupine.Evidence.Ni" in text
    assert "lammps_within_tol_Ni_Ni_u3_eam_C11" in text
    assert "calc_within_tol_Ni_MACE_MP_0_small_E_vac" in text
    assert "log sha256" in text and "inputs sha256" in text
    assert "from LAMMPS log and calculator evidence" in text


# --------------------------------------------------------------------------- #
# Regression: LAMMPS emission is byte-identical to the pre-CalcEvidence output
# --------------------------------------------------------------------------- #


@pytest.mark.unit
def test_lammps_emission_byte_identical_to_pre_calc_baseline(tmp_path: pathlib.Path) -> None:
    log_text = (_SAMPLES / "ni_eam_elastic.log").read_text(encoding="utf-8")
    evidence = build_evidence(
        log_text,
        material="Ni",
        potential_id="Ni_u3.eam",
        references={"C11": 246.5, "C12": 147.3, "C44": 124.7},
        reference_source="Simmons & Wang 1971",
    )
    sha12 = hashlib.sha256(log_text.encode("utf-8")).hexdigest()[:12]
    expected = (
        "/- AUTHORED by lupine_distill.lammps_ingest from LAMMPS log evidence.\n"
        f"   Inputs: Ni/Ni_u3.eam log sha256 {sha12}.\n"
        "   Decidable Nat facts (abs error vs reference, x1000) — 0 sorry. -/\n"
        "\n"
        "namespace Lupine.LammpsEvidence.Ni\n"
        "\n"
        "/-- Ni/Ni_u3.eam C11 = 246.7900 GPa vs reference 246.5000 (Simmons & Wang 1971): "
        "|err| 0.2900 ≤ tol 12.3250 GPa (5%). Machine-checked from LAMMPS log evidence "
        "(abs error x1000). -/\n"
        "theorem lammps_within_tol_Ni_Ni_u3_eam_C11 : 290 ≤ 12325 := by decide\n"
        "\n"
        "/-- Ni/Ni_u3.eam C12 = 147.3200 GPa vs reference 147.3000 (Simmons & Wang 1971): "
        "|err| 0.0200 ≤ tol 7.3650 GPa (5%). Machine-checked from LAMMPS log evidence "
        "(abs error x1000). -/\n"
        "theorem lammps_within_tol_Ni_Ni_u3_eam_C12 : 20 ≤ 7365 := by decide\n"
        "\n"
        "/-- Ni/Ni_u3.eam C44 = 124.8500 GPa vs reference 124.7000 (Simmons & Wang 1971): "
        "|err| 0.1500 ≤ tol 6.2350 GPa (5%). Machine-checked from LAMMPS log evidence "
        "(abs error x1000). -/\n"
        "theorem lammps_within_tol_Ni_Ni_u3_eam_C44 : 150 ≤ 6235 := by decide\n"
        "\n"
        "end Lupine.LammpsEvidence.Ni\n"
    )
    emitted = emit_lean_module([evidence], tmp_path / "Ni.lean").read_text(encoding="utf-8")
    assert emitted == expected


# --------------------------------------------------------------------------- #
# CLI: the `lean` subcommand accepts calc_evidence payloads too
# --------------------------------------------------------------------------- #


@pytest.mark.integration
def test_cli_lean_accepts_calc_evidence_json(tmp_path: pathlib.Path) -> None:
    payload = json.dumps(_calc_evidence().model_dump(mode="json", by_alias=True))
    evidence_path = tmp_path / "calc.json"
    evidence_path.write_text(payload, encoding="utf-8")
    lean_path = tmp_path / "Calc.lean"
    rc = lammps_ingest.main(["lean", str(evidence_path), "-o", str(lean_path)])
    assert rc == 0
    text = lean_path.read_text(encoding="utf-8")
    assert "calc_within_tol_Ni_MACE_MP_0_small_E_vac" in text
    assert ":= by decide" in text
