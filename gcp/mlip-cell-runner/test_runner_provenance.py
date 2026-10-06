"""Strict integration: local fake model only; gate occurs before row/cache/output."""
import json
from types import SimpleNamespace
from pathlib import Path

import pytest

import mlip_cell_runner as runner
from src import predictor_provenance as provenance
from test_predictor_provenance import fake_calc, expectation


def args_for(tmp_path):
    return runner.parse_args(["run-cell", "--run-id", "new-run", "--cell-id", "new-cell",
        "--row-id", "forces", "--mlip-id", "chgnet", "--artifact-prefix", str(tmp_path / "out"),
        "--manifest-url", str(tmp_path / "fixture.json"), "--predictor-provenance", "strict",
        "--expected-predictor", str(tmp_path / "pin.json")])


def fake_row(row_id, manifest, calc, **kwargs):
    checkpoint = kwargs.get("checkpoint")
    predictions = []
    for index, case in enumerate(manifest["cases"]):
        result = checkpoint.get_prediction(row_id, index, case) if checkpoint else None
        if result is None:
            calc.predictions += 1
            result = {"structure_id": case["structure_id"], "forces_ev_per_angstrom": [[0, 0, 0]]}
            if checkpoint: checkpoint.record_prediction(row_id, index, case, result)
        predictions.append(result)
    if getattr(calc, "fail_prediction", False): predictions[-1]["status"] = "failed"
    if getattr(calc, "nan_force", False): predictions[-1]["forces_ev_per_angstrom"][0][0] = float("nan")
    return {"predictions": predictions, "score": 1.0, "score_unit": "fake-only", "metrics": {},
            "n_structures": len(predictions), "fixture_contract": {}, "row_spec": {}}


def prepare(tmp_path, monkeypatch, calc):
    args = args_for(tmp_path)
    calc.predictions = 0
    manifest = {"cases": [{"structure_id": "fake-a", "symbols": ["H"]}, {"structure_id": "fake-b", "symbols": ["H"]}]}
    monkeypatch.setattr(runner, "load_manifest", lambda _url: manifest)
    monkeypatch.setattr(runner, "run_row", fake_row)
    monkeypatch.setattr(runner, "select_row", lambda _manifest, _row: SimpleNamespace(cases=manifest["cases"]))
    monkeypatch.setattr(runner, "runtime_versions", lambda: {"fake_only": True})
    observed = provenance.observe_chgnet(calc, calculator_dtype="float32", semantics={
        "row_id": "forces", "mlip_id": "chgnet", "distill_profile": "off",
        "fixture_contract": provenance.source_identity(runner.run_row),
        "runner": provenance.source_identity(runner.run_cell), "stress_unit_override": None,
    })
    Path(args.expected_predictor).write_text(json.dumps(expectation(observed)))
    return args, provenance.verify_expected(observed, expectation(observed)), manifest


@pytest.mark.parametrize("change", ["weight", "config", "missing_actual", "missing_pin", "model_id"])
def test_gate_before_cache_prediction_or_output(tmp_path, monkeypatch, fake_calc, change):
    args, _observed, _manifest = prepare(tmp_path, monkeypatch, fake_calc)
    if change == "weight": fake_calc.model.weight.array[0] += 1
    elif change == "config": fake_calc.stress_weight += 1
    elif change == "missing_actual": fake_calc.model = None
    elif change == "missing_pin": Path(args.expected_predictor).unlink()
    else:
        pin = json.loads(Path(args.expected_predictor).read_text())
        pin["model_identifier"] = "chgnet:different-checkpoint"
        Path(args.expected_predictor).write_text(json.dumps(pin))
    monkeypatch.setattr(runner, "CellCheckpoint", lambda *a, **kw: pytest.fail("cache accessed before identity gate"))
    with pytest.raises(provenance.ProvenanceError): runner.run_cell(args, preloaded_calc=fake_calc)
    assert fake_calc.predictions == 0
    assert not Path(args.artifact_prefix).exists()


def test_verified_partial_reuse_preserves_original_entry_producer(tmp_path, monkeypatch, fake_calc):
    args, observed, manifest = prepare(tmp_path, monkeypatch, fake_calc)
    checkpoint_path = Path(args.artifact_prefix) / "cell_checkpoint.json"
    checkpoint = runner.CellCheckpoint(str(checkpoint_path), "read-write", run_id="original-run",
        cell_id="original-cell", row_id="forces", mlip_id="chgnet", variant_id="baseline",
        distill_profile="off", manifest_hash="sha256:" + runner.sha256_hex(manifest),
        calculator_dtype="float32", predictor_provenance=observed)
    case = manifest["cases"][0]
    checkpoint.record_prediction("forces", 0, case, {"structure_id": "fake-a", "forces_ev_per_angstrom": [[1, 0, 0]]})
    original = json.loads(checkpoint_path.read_text())["predictions"][runner.case_cache_key("forces", 0, case)]
    result = runner.run_cell(args, preloaded_calc=fake_calc)
    assert fake_calc.predictions == 1
    assert result.metrics["checkpoint"]["loaded_predictions"] == 1
    assert result.metrics["execution"]["predictor_provenance"]["status"] == "verified"
    entries = json.loads(checkpoint_path.read_text())["predictions"]
    assert entries[runner.case_cache_key("forces", 0, case)] == original
    assert entries[runner.case_cache_key("forces", 1, manifest["cases"][1])]["producer_context"]["run_id"] == "new-run"


def test_legacy_output_explicitly_unknown(tmp_path, monkeypatch, fake_calc):
    args, _observed, _manifest = prepare(tmp_path, monkeypatch, fake_calc)
    args.predictor_provenance, args.expected_predictor = "legacy", None
    result = runner.run_cell(args, preloaded_calc=fake_calc)
    assert result.metrics["execution"]["predictor_provenance"]["status"] == "unknown"
    assert result.metrics["checkpoint"]["predictor_provenance"]["mode"] == "legacy"


def test_strict_batch_overrides_fail_before_calculator_load(tmp_path, monkeypatch, fake_calc):
    args, _observed, _manifest = prepare(tmp_path, monkeypatch, fake_calc)
    args.batch_spec_url = "fake-local"
    spec = {"defaults": {"predictor-provenance": "legacy"}, "cells": [{"mlip_id": "chgnet", "row_id": "forces"}]}
    monkeypatch.setattr(runner, "load_batch_spec", lambda _: spec)
    monkeypatch.setattr(runner, "load_calculator", lambda *a, **kw: pytest.fail("loaded before batch gate"))
    with pytest.raises(ValueError, match="downgrade"): runner.run_batch(args)
    spec["defaults"] = {}
    spec["cells"][0]["mlip_id"] = "mace-mp-0"
    with pytest.raises(provenance.ProvenanceError, match="supports CHGNet"): runner.run_batch(args)


@pytest.mark.parametrize("failure", ["fail_prediction", "nan_force"])
def test_strict_never_reports_failed_or_nonfinite_output_complete(tmp_path, monkeypatch, fake_calc, failure):
    args, _observed, _manifest = prepare(tmp_path, monkeypatch, fake_calc)
    args.checkpoint_mode = "off"
    setattr(fake_calc, failure, True)
    with pytest.raises(provenance.ProvenanceError): runner.run_cell(args, preloaded_calc=fake_calc)
    assert not Path(args.artifact_prefix).exists()
