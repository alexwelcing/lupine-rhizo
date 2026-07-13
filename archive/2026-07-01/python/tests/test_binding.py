"""Tests for the Y-matrix reference binder (lupine_distill.binding + CLI).

The binder joins sweep evidence (``lupine.mlip.calc_evidence.v1``, no
references at run time) with compiled reference targets
(``lupine.y_matrix_targets.v1``) under the registered policy
(docs/plans/y-matrix-cross-property-preregistration-2026-07-01.md):
DFT-PBE preferred, else experiment; unresolved references leave the
property unbound. Binding must be pure surgery — the original payload is
never mutated and provenance (inputs_sha256) is byte-identical, because
the run inputs did not change.
"""

from __future__ import annotations

import importlib.util
import json
import pathlib
import shutil
import types

import pytest
from lupine_distill.binding import (
    DEFAULT_CONFIG,
    METHOD_PREFERENCE,
    PROPERTY_NAME_MAP,
    STATICS_EVIDENCE_PROPERTY_NAMES,
    TOLERANCE_FLOORS,
    BindingConfig,
    UnmappedPropertyError,
    bind_evidence,
    compute_tolerance,
    load_targets,
    resolve_structure,
)
from lupine_distill.calc_evidence import build_calc_evidence
from lupine_distill.schemas import CalcEvidence, PropertyValue

_REPO = pathlib.Path(__file__).resolve().parents[2]
_SCRIPT = _REPO / "python" / "scripts" / "bind_y_matrix_references.py"
_RUNS_DIR = _REPO / "data" / "y_matrix_runs"
_TARGETS_DIR = _REPO / "data" / "y_matrix_targets"


# --------------------------------------------------------------------------- #
# fixtures / helpers
# --------------------------------------------------------------------------- #


def _prop(name: str, value: float, unit: str) -> PropertyValue:
    return PropertyValue(name=name, value=value, unit=unit)


def _evidence(
    material: str = "Al",
    properties: list[PropertyValue] | None = None,
    model_id: str = "chgnet",
) -> CalcEvidence:
    return build_calc_evidence(
        material=material,
        model_id=model_id,
        device="cpu",
        inputs={"structure": f"{material}-fcc-test", "n_points": 11},
        properties=properties
        if properties is not None
        else [
            _prop("B0", 54.19, "GPa"),
            _prop("vacancy_formation_energy", 0.137, "eV"),
            _prop("stacking_fault_energy", 8.21, "mJ/m^2"),
            _prop("a0", 4.041, "Angstrom"),
        ],
    )


def _entry(
    material: str = "Al",
    structure: str = "fcc",
    prop: str = "vacancy_formation_energy",
    value: float = 0.61,
    unit: str = "eV",
    method: str = "DFT-PBE",
    citation: str = "Synthetic citation (test)",
) -> dict:
    return {
        "material": material,
        "structure": structure,
        "property": prop,
        "value": value,
        "unit": unit,
        "method": method,
        "source": {"citation": citation, "doi_or_url": None, "notes": None},
    }


def _write_targets(
    directory: pathlib.Path,
    entries: list[dict],
    family: str = "synthetic",
    name: str | None = None,
) -> pathlib.Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{name or family}.json"
    path.write_text(
        json.dumps(
            {"schema": "lupine.y_matrix_targets.v1", "family": family, "entries": entries}
        ),
        encoding="utf-8",
    )
    return path


def _targets(tmp_path: pathlib.Path, entries: list[dict], family: str = "synthetic"):
    return load_targets(_write_targets(tmp_path / "targets", entries, family=family).parent)


def _record(result, name: str):
    matches = [r for r in result.records if r.name == name]
    assert len(matches) == 1, f"expected one record for {name}, got {matches}"
    return matches[0]


@pytest.fixture(scope="module")
def cli() -> types.ModuleType:
    spec = importlib.util.spec_from_file_location("bind_y_matrix_references", _SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# --------------------------------------------------------------------------- #
# property-name mapping table
# --------------------------------------------------------------------------- #


@pytest.mark.unit
def test_property_map_covers_all_statics_evidence_names() -> None:
    # Every property name the statics runner emits must be mapped explicitly.
    for name in STATICS_EVIDENCE_PROPERTY_NAMES:
        assert name in PROPERTY_NAME_MAP, f"statics evidence name '{name}' unmapped"


@pytest.mark.unit
def test_property_map_targets_actual_compiled_names() -> None:
    # The compiled target files use long descriptive names, not the prereg
    # short names — the map must speak the compiled vocabulary.
    assert "intrinsic_stacking_fault_energy" in PROPERTY_NAME_MAP["stacking_fault_energy"]
    assert "surface_energy_100" in PROPERTY_NAME_MAP["gamma_100"]
    assert "lattice_constant_a" in PROPERTY_NAME_MAP["a0"]
    assert "bulk_modulus_pressure_derivative" in PROPERTY_NAME_MAP["B0_prime"]
    assert PROPERTY_NAME_MAP["B0"].index("bulk_modulus_0K_extrapolated") < PROPERTY_NAME_MAP[
        "B0"
    ].index("bulk_modulus_300K"), "statics B0 is a 0 K quantity: 0K-extrapolated preferred"


@pytest.mark.unit
def test_registered_method_preference_is_pbe_then_experiment() -> None:
    assert METHOD_PREFERENCE == ("DFT-PBE", "experiment")


@pytest.mark.unit
def test_sfe_tolerance_floor_default() -> None:
    assert TOLERANCE_FLOORS["stacking_fault_energy"] == 10.0


# --------------------------------------------------------------------------- #
# binding: method preference, structure awareness, matching
# --------------------------------------------------------------------------- #


@pytest.mark.unit
def test_pbe_preferred_over_experiment(tmp_path: pathlib.Path) -> None:
    targets = _targets(
        tmp_path,
        [
            _entry(value=0.67, method="experiment", citation="Exp cite"),
            _entry(value=0.61, method="DFT-PBE", citation="PBE cite"),
        ],
    )
    result = bind_evidence(_evidence(), structure="fcc", targets=targets)
    bound = {p.name: p for p in result.evidence.properties}["vacancy_formation_energy"]
    assert bound.reference_value == 0.61
    assert bound.reference_source == "PBE cite"
    record = _record(result, "vacancy_formation_energy")
    assert record.status == "bound"
    assert record.method == "DFT-PBE"
    assert record.target_property == "vacancy_formation_energy"


@pytest.mark.unit
def test_experiment_used_when_no_pbe(tmp_path: pathlib.Path) -> None:
    targets = _targets(tmp_path, [_entry(value=0.67, method="experiment")])
    result = bind_evidence(_evidence(), structure="fcc", targets=targets)
    record = _record(result, "vacancy_formation_energy")
    assert record.status == "bound"
    assert record.method == "experiment"
    assert record.reference_value == 0.67


@pytest.mark.unit
def test_unregistered_method_never_binds(tmp_path: pathlib.Path) -> None:
    targets = _targets(tmp_path, [_entry(value=0.6, method="DFT-SCAN")])
    result = bind_evidence(_evidence(), structure="fcc", targets=targets)
    record = _record(result, "vacancy_formation_energy")
    assert record.status == "unbound"


@pytest.mark.unit
def test_structure_mismatch_stays_unbound(tmp_path: pathlib.Path) -> None:
    # bcc / polycrystalline entries must not bind fcc evidence.
    targets = _targets(
        tmp_path,
        [
            _entry(structure="bcc", value=0.7),
            _entry(structure="polycrystalline", prop="surface_energy", value=1.14, unit="J/m^2"),
        ],
    )
    result = bind_evidence(_evidence(), structure="fcc", targets=targets)
    assert _record(result, "vacancy_formation_energy").status == "unbound"
    assert all(p.reference_value is None for p in result.evidence.properties)


@pytest.mark.unit
def test_material_mismatch_stays_unbound(tmp_path: pathlib.Path) -> None:
    targets = _targets(tmp_path, [_entry(material="Ni", value=1.72)])
    result = bind_evidence(_evidence(material="Al"), structure="fcc", targets=targets)
    assert _record(result, "vacancy_formation_energy").status == "unbound"


@pytest.mark.unit
def test_candidate_name_order_prefers_0k_bulk_modulus(tmp_path: pathlib.Path) -> None:
    targets = _targets(
        tmp_path,
        [
            _entry(prop="bulk_modulus_300K", value=79.4, unit="GPa", method="experiment"),
            _entry(prop="bulk_modulus_0K_extrapolated", value=81.3, unit="GPa", method="experiment"),
        ],
    )
    result = bind_evidence(_evidence(), structure="fcc", targets=targets)
    record = _record(result, "B0")
    assert record.status == "bound"
    assert record.target_property == "bulk_modulus_0K_extrapolated"
    assert record.reference_value == 81.3


@pytest.mark.unit
def test_method_preference_dominates_name_order(tmp_path: pathlib.Path) -> None:
    # A DFT-PBE entry under a later candidate name beats an experiment entry
    # under an earlier one: the registered policy is method-first.
    targets = _targets(
        tmp_path,
        [
            _entry(prop="bulk_modulus_0K_extrapolated", value=99.2, unit="GPa", method="experiment"),
            _entry(prop="bulk_modulus", value=89.2, unit="GPa", method="DFT-PBE"),
        ],
    )
    result = bind_evidence(_evidence(), structure="fcc", targets=targets)
    record = _record(result, "B0")
    assert record.method == "DFT-PBE"
    assert record.reference_value == 89.2


@pytest.mark.unit
def test_ambiguous_targets_skipped_never_silently_picked(tmp_path: pathlib.Path) -> None:
    targets = _targets(
        tmp_path,
        [_entry(value=0.61, citation="A"), _entry(value=0.63, citation="B")],
    )
    result = bind_evidence(_evidence(), structure="fcc", targets=targets)
    record = _record(result, "vacancy_formation_energy")
    assert record.status == "skipped_ambiguous"
    bound = {p.name: p for p in result.evidence.properties}["vacancy_formation_energy"]
    assert bound.reference_value is None


@pytest.mark.unit
def test_unit_mismatch_skipped_and_recorded(tmp_path: pathlib.Path) -> None:
    targets = _targets(tmp_path, [_entry(unit="eV/atom")])
    result = bind_evidence(_evidence(), structure="fcc", targets=targets)
    record = _record(result, "vacancy_formation_energy")
    assert record.status == "skipped_unit_mismatch"
    assert "eV/atom" in (record.detail or "")


@pytest.mark.unit
def test_unit_match_is_case_insensitive(tmp_path: pathlib.Path) -> None:
    # beyond_metals.json spells 'angstrom' lowercase; evidence says 'Angstrom'.
    targets = _targets(
        tmp_path,
        [_entry(prop="lattice_constant_a", value=4.05, unit="angstrom", method="experiment")],
    )
    result = bind_evidence(_evidence(), structure="fcc", targets=targets)
    record = _record(result, "a0")
    assert record.status == "bound"
    assert record.reference_value == 4.05


@pytest.mark.unit
def test_structure_match_is_case_insensitive(tmp_path: pathlib.Path) -> None:
    # Regression (2026-07-01): statics evidence carries lowercase 'b2'/'l12'
    # (structure_type from the statics CLI) while intermetallics.json compiled
    # 'B2'/'L12' — the 0-bound-intermetallics defect. Same treatment as units.
    targets = _targets(
        tmp_path,
        [
            _entry(
                material="NiAl",
                structure="B2",
                prop="formation_enthalpy",
                value=-0.6586,
                unit="eV/atom",
                method="DFT-PBE",
            )
        ],
        family="intermetallics",
    )
    evidence = _evidence(
        material="NiAl", properties=[_prop("formation_enthalpy", -0.55, "eV/atom")]
    )
    result = bind_evidence(evidence, structure="b2", targets=targets)
    record = _record(result, "formation_enthalpy")
    assert record.status == "bound"
    assert record.reference_value == -0.6586
    assert record.method == "DFT-PBE"


@pytest.mark.unit
def test_lowercase_structures_still_match_exactly(tmp_path: pathlib.Path) -> None:
    # fcc/bcc/diamond/rocksalt are lowercase on both sides; case-insensitive
    # matching must not change their behavior (match same, reject different).
    for structure in ("fcc", "bcc", "diamond", "rocksalt"):
        targets = _targets(tmp_path, [_entry(structure=structure)], family=structure)
        bound = bind_evidence(_evidence(), structure=structure, targets=targets)
        assert _record(bound, "vacancy_formation_energy").status == "bound"
        other = bind_evidence(_evidence(), structure="hcp", targets=targets)
        assert _record(other, "vacancy_formation_energy").status == "unbound"


@pytest.mark.integration
def test_real_nial_intermetallics_bind(tmp_path: pathlib.Path) -> None:
    # Real-data regression for the case-sensitivity defect: NiAl evidence
    # (structure 'b2') must bind against the compiled intermetallics targets
    # ('B2'), with the registered method preference applied per property.
    real_targets = _TARGETS_DIR / "intermetallics.json"
    real_evidence = sorted(_RUNS_DIR.glob("NiAl_b2_*.evidence.json"))
    if not real_targets.exists() or not real_evidence:
        pytest.skip("real NiAl sweep data / intermetallics targets not present")
    targets = load_targets(_TARGETS_DIR)
    evidence = CalcEvidence.model_validate_json(real_evidence[0].read_text(encoding="utf-8"))
    structure = resolve_structure(real_evidence[0], material="NiAl")
    assert structure == "b2"
    result = bind_evidence(evidence, structure=structure, targets=targets)
    records = {r.name: r for r in result.records}
    assert records["formation_enthalpy"].status == "bound"
    assert records["formation_enthalpy"].method == "DFT-PBE"  # PBE preferred
    assert records["a0"].status == "bound"
    assert records["a0"].target_property == "lattice_constant_a"
    assert records["B0"].status == "bound"
    assert records["B0"].target_property == "bulk_modulus"
    # NiAl bulk_modulus / lattice targets are experiment + DFT-GGA-PW91 only;
    # GGA-PW91 is not a registered method, so experiment must be chosen.
    assert records["B0"].method == "experiment"


@pytest.mark.unit
def test_no_structure_binds_nothing(tmp_path: pathlib.Path) -> None:
    targets = _targets(tmp_path, [_entry()])
    result = bind_evidence(_evidence(), structure=None, targets=targets)
    assert result.counts["bound"] == 0
    assert all(r.status == "unbound" for r in result.records)


# --------------------------------------------------------------------------- #
# binding: immutability + provenance discipline
# --------------------------------------------------------------------------- #


@pytest.mark.unit
def test_provenance_hash_unchanged_after_binding(tmp_path: pathlib.Path) -> None:
    original = _evidence()
    targets = _targets(tmp_path, [_entry()])
    result = bind_evidence(original, structure="fcc", targets=targets)
    assert result.counts["bound"] == 1
    # Inputs did not change, so provenance must be byte-identical.
    assert result.evidence.provenance == original.provenance
    assert result.evidence.provenance.inputs_sha256 == original.provenance.inputs_sha256
    assert result.evidence.material == original.material
    assert result.evidence.source == original.source
    assert result.evidence.schema_version == original.schema_version


@pytest.mark.unit
def test_original_evidence_never_mutated(tmp_path: pathlib.Path) -> None:
    original = _evidence()
    targets = _targets(tmp_path, [_entry()])
    result = bind_evidence(original, structure="fcc", targets=targets)
    assert result.evidence is not original
    assert all(p.reference_value is None for p in original.properties)


@pytest.mark.unit
def test_unbound_properties_preserved_verbatim(tmp_path: pathlib.Path) -> None:
    original = _evidence()
    targets = _targets(tmp_path, [_entry()])  # only vacancy binds
    result = bind_evidence(original, structure="fcc", targets=targets)
    by_name = {p.name: p for p in result.evidence.properties}
    for prop in original.properties:
        if prop.name == "vacancy_formation_energy":
            continue
        assert by_name[prop.name] == prop  # identical, including None reference
    # Order of the properties list is preserved.
    assert [p.name for p in result.evidence.properties] == [p.name for p in original.properties]


@pytest.mark.unit
def test_bound_payload_round_trips_through_schema(tmp_path: pathlib.Path) -> None:
    targets = _targets(tmp_path, [_entry()])
    result = bind_evidence(_evidence(), structure="fcc", targets=targets)
    dumped = result.evidence.model_dump(mode="json", by_alias=True)
    assert dumped["schema"] == "lupine.mlip.calc_evidence.v1"
    assert CalcEvidence.model_validate(dumped) == result.evidence


# --------------------------------------------------------------------------- #
# tolerance policy: None by default, explicit floor for near-zero references
# --------------------------------------------------------------------------- #


@pytest.mark.unit
def test_tolerance_stays_none_for_ordinary_references() -> None:
    assert compute_tolerance("B0", 79.4, DEFAULT_CONFIG) is None
    assert compute_tolerance("vacancy_formation_energy", 0.61, DEFAULT_CONFIG) is None


@pytest.mark.unit
def test_sfe_floor_applied_when_pct_degenerate() -> None:
    # 5% of 16.8 mJ/m^2 = 0.84 — degenerate; the 10 mJ/m^2 floor binds.
    assert compute_tolerance("stacking_fault_energy", 16.8, DEFAULT_CONFIG) == 10.0


@pytest.mark.unit
def test_sfe_floor_not_applied_when_pct_dominates() -> None:
    # 5% of 400 mJ/m^2 = 20 > 10 floor: default percentage rule stands (None).
    assert compute_tolerance("stacking_fault_energy", 400.0, DEFAULT_CONFIG) is None


@pytest.mark.unit
def test_sfe_floor_flows_into_bound_property(tmp_path: pathlib.Path) -> None:
    targets = _targets(
        tmp_path,
        [_entry(prop="intrinsic_stacking_fault_energy", value=16.8, unit="mJ/m^2")],
        family="stacking_faults",
    )
    result = bind_evidence(_evidence(), structure="fcc", targets=targets)
    bound = {p.name: p for p in result.evidence.properties}["stacking_fault_energy"]
    assert bound.reference_value == 16.8
    assert bound.tolerance == 10.0
    record = _record(result, "stacking_fault_energy")
    assert record.tolerance == 10.0


@pytest.mark.unit
def test_tolerance_floor_respects_config_pct() -> None:
    config = BindingConfig(tolerance_pct=100.0)
    # 100% of 16.8 = 16.8 > 10 floor: percentage rule dominates.
    assert compute_tolerance("stacking_fault_energy", 16.8, config) is None


# --------------------------------------------------------------------------- #
# strict vs default handling of unmapped evidence names
# --------------------------------------------------------------------------- #


@pytest.mark.unit
def test_unmapped_name_strict_raises(tmp_path: pathlib.Path) -> None:
    evidence = _evidence(properties=[_prop("mystery_property", 1.0, "eV")])
    targets = _targets(tmp_path, [_entry()])
    with pytest.raises(UnmappedPropertyError, match="mystery_property"):
        bind_evidence(
            evidence, structure="fcc", targets=targets, config=BindingConfig(strict=True)
        )


@pytest.mark.unit
def test_unmapped_name_default_recorded_never_silent(tmp_path: pathlib.Path) -> None:
    evidence = _evidence(properties=[_prop("mystery_property", 1.0, "eV")])
    targets = _targets(tmp_path, [_entry()])
    result = bind_evidence(evidence, structure="fcc", targets=targets)
    record = _record(result, "mystery_property")
    assert record.status == "skipped_unmapped"
    assert result.counts == {"bound": 0, "unbound": 0, "skipped": 1}


# --------------------------------------------------------------------------- #
# target loading / validation
# --------------------------------------------------------------------------- #


@pytest.mark.unit
def test_load_targets_rejects_wrong_schema(tmp_path: pathlib.Path) -> None:
    bad = tmp_path / "targets"
    bad.mkdir()
    (bad / "bad.json").write_text(
        json.dumps({"schema": "lupine.y_matrix_targets.v0", "family": "x", "entries": []}),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="bad.json"):
        load_targets(bad)


@pytest.mark.unit
def test_load_targets_attaches_family_and_merges_files(tmp_path: pathlib.Path) -> None:
    directory = tmp_path / "targets"
    _write_targets(directory, [_entry()], family="vacancy_formation")
    _write_targets(
        directory,
        [_entry(prop="melting_point", value=933.47, unit="K", method="experiment")],
        family="finite_t",
    )
    targets = load_targets(directory)
    assert len(targets) == 2
    assert {t.family for t in targets} == {"vacancy_formation", "finite_t"}


@pytest.mark.unit
def test_load_targets_missing_dir_raises(tmp_path: pathlib.Path) -> None:
    with pytest.raises(ValueError, match="no target files"):
        load_targets(tmp_path / "nope")


# --------------------------------------------------------------------------- #
# structure resolution (evidence payloads do not carry structure)
# --------------------------------------------------------------------------- #


@pytest.mark.unit
def test_resolve_structure_from_sibling_run_json(tmp_path: pathlib.Path) -> None:
    (tmp_path / "Al_weird_chgnet.json").write_text(
        json.dumps({"schema": "lupine.statics_run.v1", "material": "Al", "structure_type": "fcc"}),
        encoding="utf-8",
    )
    evidence_path = tmp_path / "Al_weird_chgnet.evidence.json"
    evidence_path.write_text("{}", encoding="utf-8")
    # Sibling wins over the (misleading) filename token.
    assert resolve_structure(evidence_path, material="Al") == "fcc"


@pytest.mark.unit
def test_resolve_structure_filename_fallback(tmp_path: pathlib.Path) -> None:
    path = tmp_path / "Ni3Al_l12_mace-mp-small.evidence.json"
    path.write_text("{}", encoding="utf-8")
    assert resolve_structure(path, material="Ni3Al") == "l12"


@pytest.mark.unit
def test_resolve_structure_material_mismatch_returns_none(tmp_path: pathlib.Path) -> None:
    path = tmp_path / "Cu_fcc_chgnet.evidence.json"
    path.write_text("{}", encoding="utf-8")
    assert resolve_structure(path, material="Al") is None


# --------------------------------------------------------------------------- #
# CLI: bind + report
# --------------------------------------------------------------------------- #


def _write_evidence(path: pathlib.Path, evidence: CalcEvidence) -> pathlib.Path:
    path.write_text(
        json.dumps(evidence.model_dump(mode="json", by_alias=True), indent=2) + "\n",
        encoding="utf-8",
    )
    return path


@pytest.mark.integration
def test_cli_binds_synthetic_and_writes_report(cli, tmp_path: pathlib.Path) -> None:
    runs = tmp_path / "runs"
    runs.mkdir()
    _write_evidence(runs / "Al_fcc_chgnet.evidence.json", _evidence())
    targets_dir = tmp_path / "targets"
    _write_targets(targets_dir, [_entry(value=0.61, method="DFT-PBE")], family="vacancy_formation")

    out_dir = tmp_path / "bound"
    rc = cli.main(
        [
            "--evidence-dir", str(runs),
            "--targets-dir", str(targets_dir),
            "--out-dir", str(out_dir),
        ]
    )
    assert rc == 0

    bound_path = out_dir / "Al_fcc_chgnet.evidence.json"
    bound = CalcEvidence.model_validate_json(bound_path.read_text(encoding="utf-8"))
    by_name = {p.name: p for p in bound.properties}
    assert by_name["vacancy_formation_energy"].reference_value == 0.61
    assert by_name["vacancy_formation_energy"].reference_source == "Synthetic citation (test)"
    assert by_name["B0"].reference_value is None

    report = json.loads((out_dir / "binding_report.json").read_text(encoding="utf-8"))
    assert report["schema"] == "lupine.y_matrix_binding_report.v1"
    (entry,) = report["files"]
    assert entry["material"] == "Al"
    assert entry["structure"] == "fcc"
    assert entry["counts"] == {"bound": 1, "unbound": 3, "skipped": 0}
    methods = {p["name"]: p["method"] for p in entry["properties"] if p["status"] == "bound"}
    assert methods == {"vacancy_formation_energy": "DFT-PBE"}
    assert report["totals"]["bound"] == 1


@pytest.mark.integration
def test_cli_strict_fails_on_unmapped(cli, tmp_path: pathlib.Path) -> None:
    runs = tmp_path / "runs"
    runs.mkdir()
    _write_evidence(
        runs / "Al_fcc_chgnet.evidence.json",
        _evidence(properties=[_prop("mystery_property", 1.0, "eV")]),
    )
    targets_dir = tmp_path / "targets"
    _write_targets(targets_dir, [_entry()], family="vacancy_formation")
    rc = cli.main(
        [
            "--evidence-dir", str(runs),
            "--targets-dir", str(targets_dir),
            "--out-dir", str(tmp_path / "bound"),
            "--strict",
        ]
    )
    assert rc == 2


@pytest.mark.integration
def test_cli_smoke_real_finite_t_zero_bound_is_not_an_error(cli, tmp_path: pathlib.Path) -> None:
    # melting_point / thermal expansion never match statics evidence: the CLI
    # must report 0 bound properties, not fail.
    real_targets = _TARGETS_DIR / "finite_t.json"
    real_evidence = sorted(_RUNS_DIR.glob("*.evidence.json"))
    if not real_targets.exists() or not real_evidence:
        pytest.skip("real sweep data not present in this checkout")
    targets_dir = tmp_path / "targets"
    targets_dir.mkdir()
    shutil.copy(real_targets, targets_dir / "finite_t.json")
    out_dir = tmp_path / "bound"
    rc = cli.main(
        [
            str(real_evidence[0]),
            "--targets-dir", str(targets_dir),
            "--out-dir", str(out_dir),
        ]
    )
    assert rc == 0
    report = json.loads((out_dir / "binding_report.json").read_text(encoding="utf-8"))
    (entry,) = report["files"]
    assert entry["counts"]["bound"] == 0
    assert entry["counts"]["skipped"] == 0
    assert report["totals"]["bound"] == 0
    # The unbound payload is still written, unchanged in its property values.
    original = CalcEvidence.model_validate_json(real_evidence[0].read_text(encoding="utf-8"))
    bound = CalcEvidence.model_validate_json(
        (out_dir / real_evidence[0].name).read_text(encoding="utf-8")
    )
    assert bound.provenance == original.provenance
    assert [p.value for p in bound.properties] == [p.value for p in original.properties]


# --------------------------------------------------------------------------- #
# CLI: Lean emission + lake vocabulary (verified / failed / unchecked)
# --------------------------------------------------------------------------- #


def _lean_setup(cli, tmp_path: pathlib.Path):
    runs = tmp_path / "runs"
    runs.mkdir()
    _write_evidence(runs / "Al_fcc_chgnet.evidence.json", _evidence())
    targets_dir = tmp_path / "targets"
    _write_targets(targets_dir, [_entry(value=0.61)], family="vacancy_formation")
    return [
        "--evidence-dir", str(runs),
        "--targets-dir", str(targets_dir),
        "--out-dir", str(tmp_path / "bound"),
        "--emit-lean",
        "--lean-dir", str(tmp_path / "lean"),
    ]


@pytest.mark.integration
def test_cli_emit_lean_writes_module_unchecked_without_lake(
    cli, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(cli.shutil, "which", lambda _: None)
    rc = cli.main(_lean_setup(cli, tmp_path))
    assert rc == 0
    module_path = tmp_path / "lean" / "Al_fcc_chgnet.lean"
    text = module_path.read_text(encoding="utf-8")
    assert "calc_" in text and ":= by decide" in text
    report = json.loads((tmp_path / "bound" / "binding_report.json").read_text(encoding="utf-8"))
    (entry,) = report["files"]
    # NEVER 'verified' without an actual lake check.
    assert entry["lean_status"] == "unchecked"
    assert report["totals"]["lean_verified"] == 0
    assert report["totals"]["lean_unchecked"] == 1


@pytest.mark.integration
def test_cli_emit_lean_records_verified_on_lake_success(
    cli, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(cli.shutil, "which", lambda _: "C:/fake/lake")
    calls: list[list[str]] = []

    def fake_run(cmd, **kwargs):
        calls.append(list(cmd))
        return types.SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(cli.subprocess, "run", fake_run)
    rc = cli.main(_lean_setup(cli, tmp_path))
    assert rc == 0
    report = json.loads((tmp_path / "bound" / "binding_report.json").read_text(encoding="utf-8"))
    assert report["files"][0]["lean_status"] == "verified"
    assert report["totals"]["lean_verified"] == 1
    (cmd,) = calls
    assert cmd[:3] == ["C:/fake/lake", "env", "lean"]


@pytest.mark.integration
def test_cli_emit_lean_records_failed_on_lake_error(
    cli, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(cli.shutil, "which", lambda _: "C:/fake/lake")
    monkeypatch.setattr(
        cli.subprocess,
        "run",
        lambda cmd, **kwargs: types.SimpleNamespace(
            returncode=1, stdout="", stderr="type error: boom"
        ),
    )
    rc = cli.main(_lean_setup(cli, tmp_path))
    assert rc == 0
    report = json.loads((tmp_path / "bound" / "binding_report.json").read_text(encoding="utf-8"))
    (entry,) = report["files"]
    assert entry["lean_status"] == "failed"
    assert "boom" in entry["lean_detail"]
    assert report["totals"]["lean_failed"] == 1


@pytest.mark.integration
def test_cli_skip_lake_flag_leaves_modules_unchecked(cli, tmp_path: pathlib.Path) -> None:
    rc = cli.main(_lean_setup(cli, tmp_path) + ["--skip-lake"])
    assert rc == 0
    report = json.loads((tmp_path / "bound" / "binding_report.json").read_text(encoding="utf-8"))
    assert report["files"][0]["lean_status"] == "unchecked"


@pytest.mark.integration
def test_cli_no_bound_properties_emits_no_lean_module(cli, tmp_path: pathlib.Path) -> None:
    runs = tmp_path / "runs"
    runs.mkdir()
    _write_evidence(runs / "Al_fcc_chgnet.evidence.json", _evidence())
    targets_dir = tmp_path / "targets"
    # Ni-only targets: nothing matches Al -> 0 bound -> no module (there is
    # nothing to prove), reported as not_emitted rather than erroring.
    _write_targets(targets_dir, [_entry(material="Ni", value=1.72)], family="vacancy_formation")
    rc = cli.main(
        [
            "--evidence-dir", str(runs),
            "--targets-dir", str(targets_dir),
            "--out-dir", str(tmp_path / "bound"),
            "--emit-lean",
            "--lean-dir", str(tmp_path / "lean"),
            "--skip-lake",
        ]
    )
    assert rc == 0
    assert not (tmp_path / "lean" / "Al_fcc_chgnet.lean").exists()
    report = json.loads((tmp_path / "bound" / "binding_report.json").read_text(encoding="utf-8"))
    assert report["files"][0]["lean_status"] == "not_emitted"
