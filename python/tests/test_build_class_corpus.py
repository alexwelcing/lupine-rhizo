"""Tests for build_class_corpus.py (class-native calibration corpus builder).

CPU-only synthetic data in tmp dirs; no calculator ever loads. The builder is
a script, so it is imported from python/scripts like the discovery-gates
tests do.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

_SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import build_class_corpus as bcc  # noqa: E402

from lupine_distill.calc_evidence import build_calc_evidence  # noqa: E402
from lupine_distill.schemas import CalcEvidence, PropertyValue  # noqa: E402
from lupine_distill.statics import InputValidationError  # noqa: E402

pytestmark = pytest.mark.unit

FCC_METALS = ("Ag", "Al", "Au", "Ca", "Cu")
BCC_METALS = ("Cr", "Fe", "Mo", "Nb", "Ta")
COVALENT = ("Si", "NiAl")
MODELS = ("model-a", "model-b")

_PROPS = (("a0", "Angstrom"), ("B0", "GPa"), ("C11", "GPa"), ("C12", "GPa"), ("C44", "GPa"))


# --------------------------------------------------------------------------
# synthetic fixtures
# --------------------------------------------------------------------------


def _write_baseline_evidence(directory: Path, material: str, model: str, seed: float) -> None:
    """One valid calc_evidence.v1 file with model-dependent property values."""
    offset = 0.02 if model.endswith("b") else 0.0
    properties = [
        PropertyValue(name=name, value=seed * (1.0 + offset) + i, unit=unit)
        for i, (name, unit) in enumerate(_PROPS)
    ]
    evidence = build_calc_evidence(
        material=material,
        model_id=model,
        device="cpu",
        inputs={"material": material, "model_id": model, "synthetic": True},
        properties=properties,
        computed_at=datetime(2026, 7, 13, tzinfo=timezone.utc),
    )
    path = directory / f"{material}_x_{model}.evidence.json"
    path.write_text(
        json.dumps(evidence.model_dump(mode="json", by_alias=True), indent=2),
        encoding="utf-8",
    )


@pytest.fixture()
def baseline_dir(tmp_path: Path) -> Path:
    directory = tmp_path / "elastic_baseline"
    directory.mkdir()
    for i, material in enumerate(FCC_METALS + BCC_METALS + COVALENT + ("MgO",)):
        for model in MODELS:
            _write_baseline_evidence(directory, material, model, seed=10.0 + i)
    # a non-evidence JSON that the schema check must ignore
    (directory / "baseline_summary.json").write_text("{}", encoding="utf-8")
    return directory


def _per_model_record(base: float, spread: float) -> dict:
    return {
        "properties": {
            "a0": base,
            "b0": base * 10.0 + spread,
            "c11": base * 20.0 + spread,
            "c12": base * 5.0 + spread,
            "c44": base * 3.0 + spread,
        }
    }


def _halide_report(n_subjects: int = 5) -> dict:
    formulas = ("LiF", "LiCl", "LiBr", "LiI", "NaCl", "MgO")[:n_subjects]
    subjects = {
        f"{formula}_rocksalt": {
            "role": "synthetic",
            "formula": formula,
            "structure_type": "rocksalt",
            "per_model": {
                "model-a": _per_model_record(4.0 + i, 0.0),
                "model-b": _per_model_record(4.0 + i, 0.5 + i),
            },
        }
        for i, formula in enumerate(formulas)
    }
    # one error cell (skipped, recorded) and one non-rocksalt subject (ignored)
    subjects[f"{formulas[0]}_rocksalt"]["per_model"]["model-c"] = {
        "error": "StaticsError: synthetic failure"
    }
    subjects["Li2S_antifluorite"] = {
        "role": "ignored",
        "formula": "Li2S",
        "structure_type": "antifluorite",
        "per_model": {"model-a": _per_model_record(5.7, 0.0)},
    }
    return {
        "schema": "lupine.discovery_gates.v1",
        "generated_at": "2026-07-13T13:17:10+00:00",
        "device": "cpu",
        "calculator_versions": {"model-a": "model-a 1.0", "model-b": "model-b 2.0"},
        "subjects": subjects,
    }


def _round1_report(n_perovskites: int = 5) -> dict:
    formulas = ("CsSnCl3", "CsSnBr3", "CsSnI3", "CsGeI3", "CsPbI3")[:n_perovskites]
    candidates = {
        f"hp-{formula.lower()}": {
            "group": "halide-perovskite",
            "formula": formula,
            "structure_type": "perovskite",
            "references": {
                "a0": None if formula == "CsGeI3" else 5.5 + i,
                "b0": 20.0 + i,
                "c11": None,
                "c12": None,
                "c44": None,
            },
            "per_model": {
                "model-a": _per_model_record(5.5 + i, 0.0),
                "model-b": _per_model_record(5.5 + i, 0.1 + 0.1 * i),
            },
        }
        for i, formula in enumerate(formulas)
    }
    candidates["hea-coni"] = {
        "group": "hea-fcc",
        "formula": "CoNi",
        "structure_type": "fcc-rss",
        "references": {"a0": 3.535},
        "per_model": {"model-a": _per_model_record(3.5, 0.0)},
    }
    return {
        "schema": "lupine.candidate_campaign.v1",
        "generated_at": "2026-07-13T14:14:06+00:00",
        "parameters": {"device": "cpu"},
        "candidates": candidates,
    }


@pytest.fixture()
def halide_report_path(tmp_path: Path) -> Path:
    path = tmp_path / "halide_report.json"
    path.write_text(json.dumps(_halide_report()), encoding="utf-8")
    return path


@pytest.fixture()
def round1_report_path(tmp_path: Path) -> Path:
    path = tmp_path / "round1_report.json"
    path.write_text(json.dumps(_round1_report()), encoding="utf-8")
    return path


# --------------------------------------------------------------------------
# class map
# --------------------------------------------------------------------------


def test_metal_class_map_splits_prototypes() -> None:
    assert bcc.METAL_CLASS_BY_MATERIAL["Ag"] == bcc.CLASS_METALS_FCC
    assert bcc.METAL_CLASS_BY_MATERIAL["W"] == bcc.CLASS_METALS_BCC
    assert bcc.METAL_CLASS_BY_MATERIAL["Si"] == bcc.CLASS_COVALENT
    assert bcc.METAL_CLASS_BY_MATERIAL["Ni3Al"] == bcc.CLASS_COVALENT
    assert bcc.METAL_CLASS_BY_MATERIAL["NiAl"] == bcc.CLASS_COVALENT
    # rocksalts are sourced from the halide panel, not the elastic baseline
    assert bcc.METAL_CLASS_BY_MATERIAL["MgO"] is None
    assert bcc.METAL_CLASS_BY_MATERIAL["NaCl"] is None


def test_baseline_class_sizes_match_expectation() -> None:
    counts: dict[str, int] = {}
    for cls in bcc.METAL_CLASS_BY_MATERIAL.values():
        if cls is not None:
            counts[cls] = counts.get(cls, 0) + 1
    assert counts == {
        bcc.CLASS_METALS_FCC: 9,
        bcc.CLASS_METALS_BCC: 7,
        bcc.CLASS_COVALENT: 3,
    }


# --------------------------------------------------------------------------
# (a) metals gathering
# --------------------------------------------------------------------------


def test_gather_metals_copies_and_splits(baseline_dir: Path, tmp_path: Path) -> None:
    corpus = tmp_path / "corpus"
    copied = bcc.gather_metals(baseline_dir, corpus)
    assert sorted(copied) == sorted(
        [bcc.CLASS_METALS_FCC, bcc.CLASS_METALS_BCC, bcc.CLASS_COVALENT]
    )
    assert len(copied[bcc.CLASS_METALS_FCC]) == len(FCC_METALS) * len(MODELS)
    assert len(copied[bcc.CLASS_METALS_BCC]) == len(BCC_METALS) * len(MODELS)
    assert len(copied[bcc.CLASS_COVALENT]) == len(COVALENT) * len(MODELS)
    # rocksalt MgO cells were NOT copied anywhere
    for class_dir in corpus.iterdir():
        assert not list(class_dir.glob("MgO_*"))
    # copied file content is byte-identical to the source (copy as-is)
    name = copied[bcc.CLASS_METALS_FCC][0]
    assert (corpus / bcc.CLASS_METALS_FCC / name).read_bytes() == (
        baseline_dir / name
    ).read_bytes()


def test_gather_metals_unknown_material_fails(tmp_path: Path) -> None:
    directory = tmp_path / "baseline"
    directory.mkdir()
    _write_baseline_evidence(directory, "Unobtainium", "model-a", seed=1.0)
    with pytest.raises(InputValidationError, match="Unobtainium"):
        bcc.gather_metals(directory, tmp_path / "corpus")


def test_gather_metals_missing_dir_fails(tmp_path: Path) -> None:
    with pytest.raises(InputValidationError, match="does not exist"):
        bcc.gather_metals(tmp_path / "nope", tmp_path / "corpus")


def test_gather_metals_empty_dir_fails(tmp_path: Path) -> None:
    directory = tmp_path / "baseline"
    directory.mkdir()
    (directory / "not_evidence.json").write_text("{}", encoding="utf-8")
    with pytest.raises(InputValidationError, match="no lupine.mlip.calc_evidence"):
        bcc.gather_metals(directory, tmp_path / "corpus")


# --------------------------------------------------------------------------
# (b) ionics from the halide-panel report
# --------------------------------------------------------------------------


def test_gather_ionics_emits_valid_evidence(
    halide_report_path: Path, tmp_path: Path
) -> None:
    corpus = tmp_path / "corpus"
    result = bcc.gather_ionics(halide_report_path, corpus)
    class_dir = corpus / bcc.CLASS_IONICS
    files = sorted(class_dir.glob("*.evidence.json"))
    assert len(files) == 5 * len(MODELS)  # 5 rocksalts x 2 ok models
    assert result["skipped_error_cells"] == ["LiF_rocksalt/model-c"]
    payload = json.loads((class_dir / "LiF_rocksalt_model-a.evidence.json").read_text())
    evidence = CalcEvidence.model_validate(payload)  # schema-valid at the boundary
    assert evidence.material == "LiF"
    assert evidence.source.device == "cpu"
    assert evidence.source.calculator_version == "model-a 1.0"
    by_name = {p.name: p for p in evidence.properties}
    assert set(by_name) == {"a0", "B0", "C11", "C12", "C44"}
    assert by_name["a0"].value == pytest.approx(4.0)
    assert by_name["B0"].value == pytest.approx(40.0)  # report key b0 -> B0
    assert by_name["B0"].unit == "GPa"
    # provenance: computed_at is the source report's generated_at, not the clock
    assert evidence.provenance.computed_at == datetime.fromisoformat(
        "2026-07-13T13:17:10+00:00"
    )
    # the antifluorite subject was ignored
    assert not list(class_dir.glob("Li2S*"))


def test_gather_ionics_rejects_wrong_schema(tmp_path: Path) -> None:
    path = tmp_path / "report.json"
    path.write_text(json.dumps({"schema": "wrong", "generated_at": "x"}))
    with pytest.raises(InputValidationError, match="expected schema"):
        bcc.gather_ionics(path, tmp_path / "corpus")


def test_gather_ionics_rejects_missing_report(tmp_path: Path) -> None:
    with pytest.raises(InputValidationError, match="does not exist"):
        bcc.gather_ionics(tmp_path / "nope.json", tmp_path / "corpus")


def test_gather_ionics_rejects_bad_device(tmp_path: Path) -> None:
    report = _halide_report()
    report["device"] = "tpu"
    path = tmp_path / "report.json"
    path.write_text(json.dumps(report), encoding="utf-8")
    with pytest.raises(InputValidationError, match="device"):
        bcc.gather_ionics(path, tmp_path / "corpus")


# --------------------------------------------------------------------------
# (c) perovskites from the Round-1 report
# --------------------------------------------------------------------------


def test_gather_perovskites_emits_only_perovskites(
    round1_report_path: Path, tmp_path: Path
) -> None:
    corpus = tmp_path / "corpus"
    bcc.gather_perovskites(round1_report_path, corpus)
    class_dir = corpus / bcc.CLASS_PEROVSKITES
    files = sorted(p.name for p in class_dir.glob("*.evidence.json"))
    assert len(files) == 5 * len(MODELS)
    assert not [f for f in files if "CoNi" in f]  # HEA candidate excluded


def test_gather_perovskites_embeds_references(
    round1_report_path: Path, tmp_path: Path
) -> None:
    corpus = tmp_path / "corpus"
    bcc.gather_perovskites(round1_report_path, corpus)
    class_dir = corpus / bcc.CLASS_PEROVSKITES
    with_a0_ref = CalcEvidence.model_validate(
        json.loads((class_dir / "CsSnCl3_perovskite_model-a.evidence.json").read_text())
    )
    by_name = {p.name: p for p in with_a0_ref.properties}
    assert by_name["a0"].reference_value == pytest.approx(5.5)
    assert "candidate hp-cssncl3" in by_name["a0"].reference_source
    assert by_name["C11"].reference_value is None  # null reference stays null
    no_a0_ref = CalcEvidence.model_validate(
        json.loads((class_dir / "CsGeI3_perovskite_model-a.evidence.json").read_text())
    )
    assert {p.name: p for p in no_a0_ref.properties}["a0"].reference_value is None


# --------------------------------------------------------------------------
# thresholds.v3
# --------------------------------------------------------------------------


@pytest.fixture()
def full_corpus(
    baseline_dir: Path, halide_report_path: Path, round1_report_path: Path, tmp_path: Path
) -> Path:
    corpus = tmp_path / "corpus"
    bcc.gather_metals(baseline_dir, corpus)
    bcc.gather_ionics(halide_report_path, corpus)
    bcc.gather_perovskites(round1_report_path, corpus)
    return corpus


def test_derive_class_thresholds_per_class(full_corpus: Path) -> None:
    per_class, skipped = bcc.derive_class_thresholds(full_corpus)
    assert sorted(per_class) == sorted(
        [
            bcc.CLASS_METALS_FCC,
            bcc.CLASS_METALS_BCC,
            bcc.CLASS_IONICS,
            bcc.CLASS_PEROVSKITES,
        ]
    )
    # every class carries all five per-property thresholds
    for thresholds in per_class.values():
        assert sorted(thresholds) == ["a0", "b0", "c11", "c12", "c44"]
        for t in thresholds.values():
            assert 0.0 <= t.flag <= t.refuse
    assert per_class[bcc.CLASS_IONICS]["a0"].n_samples == 5
    assert per_class[bcc.CLASS_PEROVSKITES]["b0"].n_samples == 5
    # covalent-intermetallic has n=2 < 5: documented skip, no thresholds
    assert bcc.CLASS_COVALENT in skipped
    assert "2 material(s)" in skipped[bcc.CLASS_COVALENT]


def test_derive_class_thresholds_rejects_low_minimum(full_corpus: Path) -> None:
    with pytest.raises(InputValidationError, match="min_materials"):
        bcc.derive_class_thresholds(full_corpus, min_materials=3)


def test_render_threshold_table_lists_every_class_property(full_corpus: Path) -> None:
    per_class, _ = bcc.derive_class_thresholds(full_corpus)
    table = bcc.render_threshold_table(per_class)
    assert len(table.splitlines()) == 2 + 4 * 5  # header + separator + 4x5 rows
    assert "metals-fcc" in table and "perovskites" in table


def test_main_end_to_end(
    baseline_dir: Path,
    halide_report_path: Path,
    round1_report_path: Path,
    tmp_path: Path,
) -> None:
    corpus = tmp_path / "corpus"
    thresholds_out = tmp_path / "thresholds.v3.json"
    rc = bcc.main(
        [
            "--elastic-baseline-dir",
            str(baseline_dir),
            "--halide-report",
            str(halide_report_path),
            "--round1-report",
            str(round1_report_path),
            "--corpus-root",
            str(corpus),
            "--thresholds-out",
            str(thresholds_out),
        ]
    )
    assert rc == 0
    artifact = json.loads(thresholds_out.read_text(encoding="utf-8"))
    assert artifact["schema"] == "lupine.discovery_gates.thresholds.v3"
    assert sorted(artifact["per_class"]) == sorted(
        [
            bcc.CLASS_METALS_FCC,
            bcc.CLASS_METALS_BCC,
            bcc.CLASS_IONICS,
            bcc.CLASS_PEROVSKITES,
        ]
    )
    for class_block in artifact["per_class"].values():
        assert set(class_block["per_property"]) == {"a0", "b0", "c11", "c12", "c44"}
        assert class_block["n_materials"] >= 5
    assert bcc.CLASS_COVALENT in artifact["classes_without_thresholds"]
    assert set(artifact["provenance"]) == set(bcc.ALL_CLASSES)
    assert artifact["notes"]  # honesty notes travel with the artifact


def test_main_reports_failure_on_missing_inputs(tmp_path: Path) -> None:
    rc = bcc.main(
        [
            "--elastic-baseline-dir",
            str(tmp_path / "nope"),
            "--halide-report",
            str(tmp_path / "nope.json"),
            "--round1-report",
            str(tmp_path / "nope2.json"),
            "--corpus-root",
            str(tmp_path / "corpus"),
            "--thresholds-out",
            str(tmp_path / "t.json"),
        ]
    )
    assert rc == 1
    assert not (tmp_path / "t.json").exists()
