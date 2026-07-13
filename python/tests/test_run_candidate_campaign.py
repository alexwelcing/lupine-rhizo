"""Tests for run_candidate_campaign.py (Round-1 candidate campaign runner).

CPU-only (EMT); the GPU MLIPs never load. The runner is a script, so it is
imported from python/scripts like the discovery-gates tests do.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from ase.calculators.emt import EMT

_SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import run_candidate_campaign as rcc  # noqa: E402
import run_discovery_gates as rdg  # noqa: E402

from lupine_distill.statics import (  # noqa: E402
    InputValidationError,
    build_rss_supercell,
    build_structure,
    compute_cubic_elastic_constants,
    load_license_registry,
)

pytestmark = pytest.mark.unit


# --------------------------------------------------------------------------
# fixtures
# --------------------------------------------------------------------------


def _thresholds_payload(flag: float = 0.05, refuse: float = 0.10) -> dict:
    return {
        "schema": "lupine.discovery_gates.thresholds.v2",
        "per_property": {
            prop: {
                "flag": flag,
                "refuse": refuse,
                "flag_percentile": 75.0,
                "refuse_percentile": 95.0,
                "n_samples": 6,
                "source": "synthetic test baseline",
                "sample_dispersions": [["M0", 0.01], ["M1", 0.02]],
            }
            for prop in rcc.CAMPAIGN_PROPERTIES
        },
    }


@pytest.fixture()
def thresholds_file(tmp_path: Path) -> Path:
    path = tmp_path / "thresholds.v2.json"
    path.write_text(json.dumps(_thresholds_payload()), encoding="utf-8")
    return path


def _targets_payload() -> dict:
    return {
        "candidates": [
            {
                "id": "nicu-rss",
                "group": "hea-fcc",
                "formula": "NiCu",
                "structure_type": "fcc-rss",
                "composition": {"Ni": 1, "Cu": 1},
                "lattice_guess_angstrom": None,
                "references": {
                    "a0": {"value": 3.56},
                    "b0": {"value": 160.0},
                    "c11": None,
                    "c12": None,
                    "c44": None,
                },
            }
        ]
    }


@pytest.fixture()
def targets_file(tmp_path: Path) -> Path:
    path = tmp_path / "round1_targets.json"
    path.write_text(json.dumps(_targets_payload()), encoding="utf-8")
    return path


@pytest.fixture()
def bias_file(tmp_path: Path) -> Path:
    payload = {
        "schema": "lupine.model_biases.v1",
        "biases": {
            "emt-a": {"a0": {"fcc-metals": 1.05}, "b0": {"fcc-metals": 0.90}},
        },
        "cij": {"available": False, "reason": "test"},
    }
    path = tmp_path / "model_biases.v1.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _emt_factory(device: str) -> tuple[object, str]:
    assert device == "cpu"
    return EMT(), "emt (ase built-in)"


@pytest.fixture()
def emt_models(monkeypatch: pytest.MonkeyPatch) -> None:
    registry = {"emt-a": _emt_factory, "emt-b": _emt_factory}
    monkeypatch.setattr(rdg, "MODEL_REGISTRY", registry)
    monkeypatch.setattr(rcc, "MODEL_REGISTRY", registry)


# --------------------------------------------------------------------------
# targets / thresholds / bias loading
# --------------------------------------------------------------------------


class TestLoadTargets:
    def test_valid_targets(self, targets_file: Path) -> None:
        candidates = rcc.load_targets(targets_file)
        assert len(candidates) == 1
        c = candidates[0]
        assert c.id == "nicu-rss"
        assert c.composition_dict() == {"Ni": 1, "Cu": 1}
        assert c.reference("a0") == pytest.approx(3.56)
        assert c.reference("c11") is None

    def test_missing_file(self, tmp_path: Path) -> None:
        with pytest.raises(InputValidationError, match="does not exist"):
            rcc.load_targets(tmp_path / "nope.json")

    def test_bad_structure_type(self, tmp_path: Path) -> None:
        payload = _targets_payload()
        payload["candidates"][0]["structure_type"] = "hcp-rss"
        path = tmp_path / "targets.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        with pytest.raises(InputValidationError, match="structure_type"):
            rcc.load_targets(path)

    def test_duplicate_ids(self, tmp_path: Path) -> None:
        payload = _targets_payload()
        payload["candidates"].append(payload["candidates"][0])
        path = tmp_path / "targets.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        with pytest.raises(InputValidationError, match="duplicate"):
            rcc.load_targets(path)

    def test_unknown_reference_property(self, tmp_path: Path) -> None:
        payload = _targets_payload()
        payload["candidates"][0]["references"]["gamma_111"] = {"value": 1.0}
        path = tmp_path / "targets.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        with pytest.raises(InputValidationError, match="unknown reference"):
            rcc.load_targets(path)


class TestLoadThresholds:
    def test_reconstructs_concordance_thresholds(self, thresholds_file: Path) -> None:
        thresholds = rcc.load_thresholds_file(thresholds_file)
        assert set(thresholds) == set(rcc.CAMPAIGN_PROPERTIES)
        t = thresholds["c44"]
        assert t.flag == pytest.approx(0.05)
        assert t.refuse == pytest.approx(0.10)
        assert t.n_samples == 6
        assert t.source == "synthetic test baseline"

    def test_missing_property_errors(self, tmp_path: Path) -> None:
        payload = _thresholds_payload()
        del payload["per_property"]["c44"]
        path = tmp_path / "thresholds.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        with pytest.raises(InputValidationError, match="c44"):
            rcc.load_thresholds_file(path)


class TestApplyBias:
    def test_correction_arithmetic(self) -> None:
        biases = {"m": {"b0": {"fcc-metals": 1.25}}}
        value, corrected = rcc.apply_bias(100.0, "m", "b0", "fcc-metals", biases)
        assert corrected is True
        assert value == pytest.approx(80.0)

    def test_missing_bias_leaves_raw(self) -> None:
        value, corrected = rcc.apply_bias(100.0, "m", "c44", "fcc-metals", {})
        assert corrected is False
        assert value == pytest.approx(100.0)

    def test_nonpositive_bias_ignored(self) -> None:
        biases = {"m": {"b0": {"fcc-metals": 0.0}}}
        value, corrected = rcc.apply_bias(100.0, "m", "b0", "fcc-metals", biases)
        assert corrected is False
        assert value == pytest.approx(100.0)

    def test_missing_class_leaves_raw(self) -> None:
        biases = {"m": {"b0": {"all-21": 1.1}}}
        value, corrected = rcc.apply_bias(100.0, "m", "b0", "fcc-metals", biases)
        assert corrected is False
        assert value == pytest.approx(100.0)


# --------------------------------------------------------------------------
# candidate structure building (no calculator; rocksalt has no EMT support,
# so the rocksalt route is tested on structure geometry/bookkeeping only)
# --------------------------------------------------------------------------


def _rocksalt_candidate(lattice_guess: float | None = 6.29) -> "rcc.Candidate":
    return rcc.Candidate(
        id="rs-kcl",
        group="ionic-rocksalt",
        formula="KCl",
        structure_type="rocksalt",
        composition=(),
        lattice_guess_angstrom=lattice_guess,
        references=tuple((p, None) for p in rcc.CAMPAIGN_PROPERTIES),
    )


class TestBuildCandidateAtoms:
    def test_rocksalt_counts_and_cell(self) -> None:
        atoms, n_conv_cells, a_guess = rcc.build_candidate_atoms(
            _rocksalt_candidate(), repeat=2, seed=42
        )
        # One conventional cubic rocksalt cell: 4 K + 4 Cl, cell = a * I.
        assert len(atoms) == 8
        symbols = atoms.get_chemical_symbols()
        assert symbols.count("K") == 4 and symbols.count("Cl") == 4
        assert n_conv_cells == 1  # a0 = (V0 / n_conv_cells)^(1/3) stays exact
        assert a_guess == pytest.approx(6.29)
        cell = atoms.get_cell()[:]
        for i in range(3):
            for j in range(3):
                expected = 6.29 if i == j else 0.0
                assert cell[i][j] == pytest.approx(expected)
        assert all(atoms.get_pbc())

    def test_rocksalt_estimates_lattice_when_no_guess(self) -> None:
        atoms, n_conv_cells, a_guess = rcc.build_candidate_atoms(
            _rocksalt_candidate(lattice_guess=None), repeat=2, seed=42
        )
        assert a_guess > 0.0
        assert len(atoms) == 8 and n_conv_cells == 1

    def test_rocksalt_ignores_rss_repeat_and_seed(self) -> None:
        a, _, _ = rcc.build_candidate_atoms(_rocksalt_candidate(), repeat=3, seed=1)
        b, _, _ = rcc.build_candidate_atoms(_rocksalt_candidate(), repeat=2, seed=99)
        assert len(a) == len(b) == 8
        assert (a.get_positions() == b.get_positions()).all()

    def test_rocksalt_bias_class_routed_to_ionics(self) -> None:
        assert rcc.BIAS_CLASS_BY_STRUCTURE["rocksalt"] == "ionics-rocksalt"
        per_model = {"m1": _record(6.3, 18.0, 40.0, 8.0, 8.0)}
        arm = rcc.corrected_arm(per_model, "rocksalt", {})
        assert arm["m1"]["bias_class"] == "ionics-rocksalt"
        # No ionic bias in the Round-1 artifact -> uncorrected, labeled so.
        assert all(not v["corrected"] for v in arm["m1"]["values"].values())

    def test_load_targets_accepts_rocksalt_and_requires_formula(
        self, tmp_path: Path
    ) -> None:
        payload = _targets_payload()
        payload["candidates"].append(
            {
                "id": "rs-kcl",
                "group": "ionic-rocksalt",
                "formula": "KCl",
                "structure_type": "rocksalt",
                "composition": {},
                "lattice_guess_angstrom": 6.29,
                "references": {"a0": {"value": 6.29}},
            }
        )
        path = tmp_path / "targets.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        candidates = rcc.load_targets(path)
        assert any(c.structure_type == "rocksalt" for c in candidates)
        payload["candidates"][-1]["formula"] = ""
        path.write_text(json.dumps(payload), encoding="utf-8")
        with pytest.raises(InputValidationError, match="rocksalt candidates need"):
            rcc.load_targets(path)


# --------------------------------------------------------------------------
# cell-based measurement on EMT
# --------------------------------------------------------------------------


class TestRelaxCellEv:
    def test_emt_nicu_rss_sane_a0_b0(self) -> None:
        atoms = build_rss_supercell({"Ni": 1, "Cu": 1}, "fcc", 3.56, 2, 42)
        fit, relaxed = rcc.relax_cell_ev(EMT(), atoms)
        a0 = (fit.v0_a3 / 8) ** (1.0 / 3.0)  # 2x2x2 -> 8 conventional cells
        assert 3.4 < a0 < 3.8
        assert 100.0 < fit.b0_gpa < 230.0
        # Relaxed cell carries the fitted volume.
        assert relaxed.get_volume() == pytest.approx(fit.v0_a3, rel=1e-6)
        assert len(relaxed) == 32

    def test_deterministic(self) -> None:
        atoms = build_rss_supercell({"Ni": 1, "Cu": 1}, "fcc", 3.56, 2, 42)
        fit_a, _ = rcc.relax_cell_ev(EMT(), atoms)
        fit_b, _ = rcc.relax_cell_ev(EMT(), atoms)
        assert fit_a.v0_a3 == pytest.approx(fit_b.v0_a3)
        assert fit_a.b0_gpa == pytest.approx(fit_b.b0_gpa)


class TestCubicElasticFromAtoms:
    def test_matches_library_probe_on_prototype(self) -> None:
        """Replicated FD probe == compute_cubic_elastic_constants on the same cell."""
        reference = build_structure("Cu", "fcc", 3.6)
        mine = rcc.cubic_elastic_from_atoms(
            EMT(), reference, delta=0.005, relax_internal=False
        )
        theirs = compute_cubic_elastic_constants(
            EMT(), "Cu", "fcc", 3.6, delta=0.005, relax_internal=False
        )
        assert mine["c11_gpa"] == pytest.approx(theirs.c11_gpa, rel=1e-8)
        assert mine["c12_gpa"] == pytest.approx(theirs.c12_gpa, rel=1e-8)
        assert mine["c44_gpa"] == pytest.approx(theirs.c44_gpa, rel=1e-8)


# --------------------------------------------------------------------------
# report assembly (pure, synthetic records)
# --------------------------------------------------------------------------


def _record(a0: float, b0: float, c11: float, c12: float, c44: float, born: bool = True) -> dict:
    return {
        "properties": {"a0": a0, "b0": b0, "c11": c11, "c12": c12, "c44": c44},
        "born_passed": born,
        "gates": {},
        "wall_time_seconds": {},
    }


class TestAssembleReport:
    def _report(self, targets_file: Path, thresholds_file: Path, per_model: dict, biases: dict | None = None) -> dict:
        candidates = rcc.load_targets(targets_file)
        thresholds = rcc.load_thresholds_file(thresholds_file)
        return rcc.assemble_report(
            candidates=candidates,
            per_candidate_models={"nicu-rss": per_model},
            dynamic_gates={},
            thresholds=thresholds,
            biases=biases or {},
            bias_note="test",
            models=list(per_model),
            parameters={},
        )

    def test_concordance_wiring_pass_and_refuse(
        self, targets_file: Path, thresholds_file: Path
    ) -> None:
        # a0 disperses 0.28% (< 5% flag) -> pass; c44 disperses 40% -> refuse.
        per_model = {
            "m1": _record(3.55, 150.0, 200.0, 100.0, 40.0),
            "m2": _record(3.56, 151.0, 201.0, 101.0, 60.0),
        }
        report = self._report(targets_file, thresholds_file, per_model)
        gates = report["candidates"]["nicu-rss"]["gates"]["concordance"]
        assert gates["a0"]["values"]["level"] == "pass"
        assert gates["c44"]["values"]["level"] == "refuse"
        assert report["candidates"]["nicu-rss"]["verdict"] == "REFUSED"

    def test_born_failure_refuses(self, targets_file: Path, thresholds_file: Path) -> None:
        per_model = {
            "m1": _record(3.55, 150.0, 200.0, 100.0, 50.0, born=False),
            "m2": _record(3.55, 150.0, 200.0, 100.0, 50.0),
        }
        report = self._report(targets_file, thresholds_file, per_model)
        sub = report["candidates"]["nicu-rss"]
        assert sub["gates"]["born_aggregate"]["passed"] is False
        assert sub["verdict"] == "REFUSED"

    def test_clean_candidate_certified(
        self, targets_file: Path, thresholds_file: Path
    ) -> None:
        per_model = {
            "m1": _record(3.55, 150.0, 200.0, 100.0, 50.0),
            "m2": _record(3.55, 150.0, 200.0, 100.0, 50.0),
        }
        report = self._report(targets_file, thresholds_file, per_model)
        assert report["candidates"]["nicu-rss"]["verdict"] == "CERTIFIED"

    def test_corrected_arm_and_null_references(
        self, targets_file: Path, thresholds_file: Path
    ) -> None:
        per_model = {
            "m1": _record(3.55, 150.0, 200.0, 100.0, 50.0),
            "m2": _record(3.55, 150.0, 200.0, 100.0, 50.0),
        }
        biases = {"m1": {"a0": {"fcc-metals": 1.10}}}
        report = self._report(targets_file, thresholds_file, per_model, biases)
        arm = report["candidates"]["nicu-rss"]["corrected_arm"]
        assert arm["m1"]["bias_class"] == "fcc-metals"
        assert arm["m1"]["values"]["a0"]["corrected"] is True
        assert arm["m1"]["values"]["a0"]["value"] == pytest.approx(3.55 / 1.10)
        assert arm["m1"]["values"]["b0"]["corrected"] is False
        assert arm["m2"]["values"]["a0"]["corrected"] is False
        # Metrics only pool properties with non-null references (a0, b0 here).
        metrics = report["arm_metrics"]["abs_rel_error_by_group_property"]
        assert set(metrics["hea-fcc"]) == {"a0", "b0"}
        assert metrics["hea-fcc"]["a0"]["n_cells"] == 2
        # m1 raw a0 error = |3.55-3.56|/3.56; corrected error is larger (bad bias).
        raw_err = abs(3.55 - 3.56) / 3.56
        assert metrics["hea-fcc"]["a0"]["median_abs_rel_err_raw"] == pytest.approx(
            raw_err, rel=1e-9
        )
        coverage = report["arm_metrics"]["risk_coverage"]
        assert coverage["n_candidates"] == 1
        assert coverage["n_certified"] == 1
        assert coverage["coverage_issued_fraction"] == pytest.approx(1.0)

    def test_b0_concordance_descriptive_note_in_report(
        self, targets_file: Path, thresholds_file: Path
    ) -> None:
        """Round-3 registered fix 6: B0 concordance demoted to descriptive."""
        per_model = {
            "m1": _record(3.55, 150.0, 200.0, 100.0, 50.0),
            "m2": _record(3.55, 150.0, 200.0, 100.0, 50.0),
        }
        report = self._report(targets_file, thresholds_file, per_model)
        note = report["notes"]["b0_concordance_descriptive"]
        assert note == rcc.B0_CONCORDANCE_DESCRIPTIVE_NOTE
        assert "DESCRIPTIVE" in note and "rho = -0.63" in note
        # The note travels into the rendered markdown too.
        assert "b0_concordance_descriptive" not in rcc.render_markdown(report)
        assert "DESCRIPTIVE only" in rcc.render_markdown(report)

    def test_measurement_error_refuses_and_render_survives(
        self, targets_file: Path, thresholds_file: Path
    ) -> None:
        per_model = {
            "m1": {"error": "CalculationError: boom"},
            "m2": _record(3.55, 150.0, 200.0, 100.0, 50.0),
        }
        report = self._report(targets_file, thresholds_file, per_model)
        sub = report["candidates"]["nicu-rss"]
        assert sub["verdict"] == "REFUSED"
        assert sub["gates"]["concordance"] == {}  # <2 ok models
        markdown = rcc.render_markdown(report)
        assert "REFUSED" in markdown
        assert "boom" in markdown


# --------------------------------------------------------------------------
# gate-license annotation wiring (synthetic registry; annotates, never
# re-gates)
# --------------------------------------------------------------------------


def _license_registry_payload() -> dict:
    return {
        "schema": "lupine.discovery_gates.licenses.v1",
        "generated_at": "2026-07-13T00:00:00+00:00",
        "derived_from": {"path": "synthetic", "schema": "s", "generated_at": "t"},
        "derivation_rule": {"n_min": 5},
        "program_overrides": [
            {"property": "b0", "license_ceiling": "descriptive", "provenance": "test"}
        ],
        "by_class": {
            "metals-fcc": {
                "a0": {
                    "status": "licensed",
                    "rho": 0.9,
                    "n": 6,
                    "corpus": "synthetic-bound",
                    "corpus_kind": "reference-bound",
                    "caveats": [],
                },
                "b0": {
                    "status": "anti-correlated",
                    "rho": -0.63,
                    "n": 9,
                    "corpus": "synthetic-bound",
                    "corpus_kind": "reference-bound",
                    "caveats": [],
                },
            }
        },
    }


@pytest.fixture()
def license_registry(tmp_path: Path):
    path = tmp_path / "licenses.v1.json"
    path.write_text(json.dumps(_license_registry_payload()), encoding="utf-8")
    return load_license_registry(path)


class TestLicenseAnnotation:
    def _report(
        self,
        targets_file: Path,
        thresholds_file: Path,
        per_model: dict,
        registry=None,
    ) -> dict:
        candidates = rcc.load_targets(targets_file)
        thresholds = rcc.load_thresholds_file(thresholds_file)
        return rcc.assemble_report(
            candidates=candidates,
            per_candidate_models={"nicu-rss": per_model},
            dynamic_gates={},
            thresholds=thresholds,
            biases={},
            bias_note="test",
            models=list(per_model),
            parameters={},
            license_registry=registry,
            license_registry_path=registry.path if registry else "missing.json",
        )

    def test_registry_annotates_and_note_derives(
        self, targets_file: Path, thresholds_file: Path, license_registry
    ) -> None:
        per_model = {
            "m1": _record(3.55, 150.0, 200.0, 100.0, 50.0),
            "m2": _record(3.55, 150.0, 200.0, 100.0, 50.0),
        }
        report = self._report(
            targets_file, thresholds_file, per_model, license_registry
        )
        sub = report["candidates"]["nicu-rss"]
        gates = sub["gates"]["concordance"]
        # fcc-rss resolves to metals-fcc: a0 licensed, b0 anti-correlated;
        # unlisted c11/c12/c44 fail closed to descriptive.
        assert gates["a0"]["license"]["status"] == "licensed"
        assert gates["b0"]["license"]["status"] == "anti-correlated"
        assert gates["c44"]["license"]["status"] == "descriptive"
        assert gates["b0"]["license"]["source"] == license_registry.path
        # A license annotates; it never re-gates.
        assert sub["verdict"] == "CERTIFIED"
        assert report["license_registry"]["loaded"] is True
        # The note is now GENERATED from the registry, not the constant.
        note = report["notes"]["b0_concordance_descriptive"]
        assert note != rcc.B0_CONCORDANCE_DESCRIPTIVE_NOTE
        assert "License registry" in note
        markdown = rcc.render_markdown(report)
        assert "| concordance | license |" in markdown
        assert "**WARNING (b0):**" in markdown
        assert "must NOT be read as low error" in markdown

    def test_headline_appends_driving_license_summary(
        self, targets_file: Path, thresholds_file: Path, license_registry
    ) -> None:
        # c44 disperses 40% -> refuse drives the verdict; its license is the
        # fail-closed descriptive.
        per_model = {
            "m1": _record(3.55, 150.0, 200.0, 100.0, 40.0),
            "m2": _record(3.55, 150.0, 200.0, 100.0, 60.0),
        }
        report = self._report(
            targets_file, thresholds_file, per_model, license_registry
        )
        assert report["candidates"]["nicu-rss"]["verdict"] == "REFUSED"
        markdown = rcc.render_markdown(report)
        assert (
            "**REFUSED** (c44 - descriptive: agreement arithmetic only, "
            "no uncertainty claim)" in markdown
        )

    def test_absent_registry_fails_closed_with_constant_note(
        self, targets_file: Path, thresholds_file: Path
    ) -> None:
        per_model = {
            "m1": _record(3.55, 150.0, 200.0, 100.0, 50.0),
            "m2": _record(3.55, 150.0, 200.0, 100.0, 50.0),
        }
        report = self._report(targets_file, thresholds_file, per_model, None)
        sub = report["candidates"]["nicu-rss"]
        for prop in rcc.CAMPAIGN_PROPERTIES:
            license_entry = sub["gates"]["concordance"][prop]["license"]
            assert license_entry["status"] == "descriptive"
            assert license_entry["source"] is None
        assert report["license_registry"]["loaded"] is False
        assert (
            report["notes"]["b0_concordance_descriptive"]
            == rcc.B0_CONCORDANCE_DESCRIPTIVE_NOTE
        )


# --------------------------------------------------------------------------
# end-to-end on EMT
# --------------------------------------------------------------------------


class TestEndToEnd:
    def test_full_campaign_emt(
        self,
        emt_models: None,
        targets_file: Path,
        thresholds_file: Path,
        bias_file: Path,
        tmp_path: Path,
    ) -> None:
        out_dir = tmp_path / "round1"
        rc = rcc.main(
            [
                "--targets", str(targets_file),
                "--device", "cpu",
                "--models", "emt-a,emt-b",
                "--out-dir", str(out_dir),
                "--seed", "42",
                "--repeat", "2",
                "--thresholds-file", str(thresholds_file),
                "--bias-file", str(bias_file),
                "--dynamic-model", "emt-a",
            ]
        )
        assert rc == 0
        report = json.loads((out_dir / "report.json").read_text(encoding="utf-8"))
        sub = report["candidates"]["nicu-rss"]
        # Identical EMT models -> zero dispersion -> concordance passes.
        for prop in rcc.CAMPAIGN_PROPERTIES:
            assert sub["gates"]["concordance"][prop]["values"]["level"] == "pass"
        assert sub["gates"]["born_aggregate"]["passed"] is True
        assert "dynamic_return" in sub["gates"]
        assert sub["verdict"] in ("CERTIFIED", "REFUSED", "FLAGGED")
        # Bias arm: emt-a corrected by the file, emt-b left raw.
        raw_a0 = sub["per_model"]["emt-a"]["properties"]["a0"]
        corr = sub["corrected_arm"]["emt-a"]["values"]["a0"]
        assert corr["corrected"] is True
        assert corr["value"] == pytest.approx(raw_a0 / 1.05)
        assert sub["corrected_arm"]["emt-b"]["values"]["a0"]["corrected"] is False
        assert sub["corrected_arm"]["emt-a"]["values"]["c11"]["corrected"] is False
        # a0 sanity for EMT NiCu.
        assert 3.4 < raw_a0 < 3.8
        assert (out_dir / "REPORT.md").is_file()

    def test_skip_dynamic(
        self,
        emt_models: None,
        targets_file: Path,
        thresholds_file: Path,
        tmp_path: Path,
    ) -> None:
        out_dir = tmp_path / "round1-skip"
        rc = rcc.main(
            [
                "--targets", str(targets_file),
                "--device", "cpu",
                "--models", "emt-a,emt-b",
                "--out-dir", str(out_dir),
                "--thresholds-file", str(thresholds_file),
                "--bias-file", str(tmp_path / "absent-biases.json"),
                "--skip-dynamic",
            ]
        )
        assert rc == 0
        report = json.loads((out_dir / "report.json").read_text(encoding="utf-8"))
        sub = report["candidates"]["nicu-rss"]
        assert "dynamic_return" not in sub["gates"]
        # No bias file -> everything uncorrected.
        for model in ("emt-a", "emt-b"):
            for prop in rcc.CAMPAIGN_PROPERTIES:
                assert sub["corrected_arm"][model]["values"][prop]["corrected"] is False
        assert "uncorrected" in report["bias_provenance"]
