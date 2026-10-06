"""Independent negative-path checks; no vendor model or inference is loaded."""
from __future__ import annotations

import copy
import json

import numpy as np
import pytest

import mlip_cell_runner as runner
from src import predictor_provenance as provenance_module
from src.predictor_provenance import ProvenanceError, SCHEMA, digest, load_expected, loaded_state


def _expectation(**changes):
    value = {
        "schema": "lupine.predictor.expectation.v1",
        "model_identifier": "chgnet-0.4.2-cpu-baseline",
        "loaded_state_sha256": "sha256:" + "1" * 64,
        "inference_config_sha256": "sha256:" + "2" * 64,
    }
    value.update(changes)
    return value


@pytest.mark.parametrize(
    "value",
    [
        {},
        None,
        [],
        _expectation(schema="lupine.predictor.expectation.v999"),
        _expectation(loaded_state_sha256=None),
        _expectation(loaded_state_sha256="sha256:" + "0" * 63),
        _expectation(inference_config_sha256="sha256:" + "A" * 64),
        _expectation(allow_missing_weights=True),
    ],
)
def test_invalid_expectation_cannot_be_treated_as_legacy(tmp_path, value):
    """A malformed strict input must reject, never silently relax identity."""
    path = tmp_path / "expected.json"
    path.write_text(json.dumps(value), encoding="utf8")
    with pytest.raises(ProvenanceError):
        load_expected(str(path))


def test_unreadable_expectation_does_not_create_a_placeholder(tmp_path):
    path = tmp_path / "missing.json"
    with pytest.raises((ProvenanceError, FileNotFoundError)):
        load_expected(str(path))
    assert not path.exists()


def test_invalid_json_expectation_is_preserved(tmp_path):
    path = tmp_path / "expected.json"
    original = b'{"schema":"lupine.predictor.expectation.v1",'
    path.write_bytes(original)
    with pytest.raises(ProvenanceError):
        load_expected(str(path))
    assert path.read_bytes() == original


class _Tensor:
    """Minimal dense-tensor protocol; deliberately does not import Torch."""

    device = "cpu"
    is_sparse = False
    is_quantized = False

    def __init__(self, values, dtype="float32"):
        self.array = np.asarray(values, dtype=dtype)

    def detach(self):
        return self

    def cpu(self):
        return self

    def contiguous(self):
        return self

    def numpy(self):
        return self.array


class _State:
    def __init__(self, entries):
        self.entries = entries

    def state_dict(self):
        return self.entries


def test_loaded_identity_includes_buffers_names_shapes_and_dtypes():
    original = {"weights": _Tensor([1, 2]), "running_buffer": _Tensor([3])}
    baseline, _ = loaded_state(_State(original))
    mutations = [
        {**original, "weights": _Tensor([1, 9])},
        {**original, "running_buffer": _Tensor([4])},
        {**original, "weights": _Tensor([[1, 2]])},
        {**original, "weights": _Tensor([1, 2], "float64")},
        {"other_weights": original["weights"], "running_buffer": original["running_buffer"]},
    ]
    assert all(loaded_state(_State(value))[0] != baseline for value in mutations)
    assert loaded_state(_State(dict(reversed(list(original.items())))))[0] == baseline


def test_scalar_and_length_one_tensor_have_distinct_loaded_identities():
    """Contiguous conversion must not erase a real zero-dimensional shape."""
    scalar, _ = loaded_state(_State({"buffer": _Tensor(1.0)}))
    vector, _ = loaded_state(_State({"buffer": _Tensor([1.0])}))
    assert scalar != vector


@pytest.mark.parametrize("values", [[float("nan")], [float("inf")], [float("-inf")]])
def test_nonfinite_loaded_state_cannot_receive_an_identity(values):
    with pytest.raises(ProvenanceError):
        loaded_state(_State({"weights": _Tensor(values)}))


@pytest.mark.parametrize("attribute,value", [("device", "cuda:0"), ("is_sparse", True), ("is_quantized", True)])
def test_unsupported_actual_tensor_mode_rejects(attribute, value):
    tensor = _Tensor([1])
    setattr(tensor, attribute, value)
    with pytest.raises(ProvenanceError):
        loaded_state(_State({"weights": tensor}))


def _provenance(state="1"):
    config = {"adapter": "offline-test-double", "dtype": "float32"}
    identity = {
        "model_identifier": "chgnet:0.3.0",
        "loaded_state_sha256": "sha256:" + state * 64,
        "inference_config_sha256": digest(config),
    }
    return {
        "schema": SCHEMA, "status": "verified", "mode": "strict",
        **identity, "predictor_sha256": digest(identity), "inference_config": config,
    }


def _checkpoint(path, *, mode="read-write", producer="original", strict=True, provenance=None):
    return runner.CellCheckpoint(
        str(path), mode, run_id=producer, cell_id=producer + ":forces",
        row_id="forces", mlip_id="chgnet", variant_id="baseline", distill_profile="off",
        manifest_hash="sha256:" + "a" * 64, calculator_dtype="float32",
        predictor_provenance=(provenance or _provenance()) if strict else None,
    )


def _case(index=0):
    return {"structure_id": f"offline-{index}", "symbols": ["Al"], "positions": [[index, 0, 0]]}


def _prediction(index=0):
    return {"structure_id": f"offline-{index}", "forces_ev_per_angstrom": [[0.1, 0.0, 0.0]]}


def _seed(path):
    checkpoint = _checkpoint(path)
    checkpoint.record_prediction("forces", 0, _case(), _prediction())
    return json.loads(path.read_text())


def test_mixed_reuse_retains_each_original_producer(tmp_path):
    path = tmp_path / "checkpoint.json"
    saved = _seed(path)
    original_key = runner.case_cache_key("forces", 0, _case())
    original_entry = copy.deepcopy(saved["predictions"][original_key])
    resumed = _checkpoint(path, producer="remediation")
    assert resumed.get_prediction("forces", 0, _case()) == _prediction()
    resumed.record_prediction("forces", 1, _case(1), _prediction(1))
    mixed = json.loads(path.read_text())
    assert mixed["predictions"][original_key] == original_entry
    new_key = runner.case_cache_key("forces", 1, _case(1))
    assert mixed["predictions"][new_key]["producer_context"]["run_id"] == "remediation"
    assert mixed["predictions"][original_key]["producer_context"]["run_id"] == "original"


@pytest.mark.parametrize("damage", [
    "unknown_schema", "wrong_scope", "unknown_context_field", "not_predictions",
    "missing_producer", "missing_entry_identity", "changed_prediction", "malformed_case_hash",
])
def test_unrecognized_or_malformed_strict_cache_is_not_reused_or_overwritten(tmp_path, damage):
    path = tmp_path / "checkpoint.json"
    value = _seed(path)
    entry = next(iter(value["predictions"].values()))
    if damage == "unknown_schema": value["schema"] = "future.checkpoint.v99"
    elif damage == "wrong_scope": value["context"]["checkpoint_scope"] = "corrected_predictions"
    elif damage == "unknown_context_field": value["context"]["prediction_transform"] = "unknown"
    elif damage == "not_predictions": value["predictions"] = []
    elif damage == "missing_producer": entry.pop("producer_context")
    elif damage == "missing_entry_identity": entry.pop("predictor_provenance")
    elif damage == "changed_prediction": entry["prediction"]["forces_ev_per_angstrom"][0][0] = 999
    elif damage == "malformed_case_hash": entry["case_hash"] = "not-a-digest"
    path.write_text(json.dumps(value), encoding="utf8")
    before = path.read_bytes()
    with pytest.raises(ProvenanceError):
        _checkpoint(path, producer="resumer")
    assert path.read_bytes() == before


@pytest.mark.parametrize("strict", [True, False])
def test_write_only_cannot_destroy_existing_strict_evidence(tmp_path, strict):
    path = tmp_path / "checkpoint.json"
    _seed(path)
    before = path.read_bytes()
    with pytest.raises((ProvenanceError, ValueError)):
        _checkpoint(path, mode="write-only", producer="overwriter", strict=strict)
    assert path.read_bytes() == before


@pytest.mark.parametrize("mode", ["off", "unknown", "read_write", None])
@pytest.mark.parametrize("strict", [True, False])
def test_checkpoint_object_rejects_non_io_modes_without_touching_evidence(tmp_path, mode, strict):
    """run_cell handles off without a cache object; an object cannot become an unchecked writer."""
    path = tmp_path / "checkpoint.json"
    _seed(path)
    before = path.read_bytes()
    with pytest.raises(ValueError):
        _checkpoint(path, mode=mode, strict=strict)
    assert path.read_bytes() == before


@pytest.mark.parametrize("prior_bytes", [b"not-json", b"{}", b'{"schema":"unknown"}'])
def test_strict_write_only_does_not_replace_unknown_existing_data(tmp_path, prior_bytes):
    path = tmp_path / "checkpoint.json"
    path.write_bytes(prior_bytes)
    with pytest.raises(ProvenanceError):
        _checkpoint(path, mode="write-only")
    assert path.read_bytes() == prior_bytes


def test_reused_entry_cannot_be_replaced_by_current_producer(tmp_path):
    path = tmp_path / "checkpoint.json"
    _seed(path)
    before = path.read_bytes()
    resumed = _checkpoint(path, producer="replacement")
    with pytest.raises(ProvenanceError):
        resumed.record_prediction("forces", 0, _case(), _prediction())
    assert path.read_bytes() == before


def test_matching_alias_cannot_reuse_different_loaded_weights(tmp_path):
    path = tmp_path / "checkpoint.json"
    _seed(path)
    before = path.read_bytes()
    with pytest.raises(ProvenanceError):
        _checkpoint(path, provenance=_provenance(state="9"))
    assert path.read_bytes() == before


@pytest.mark.parametrize("defaults,cell", [
    ({"predictor-provenance": "legacy"}, {}),
    ({}, {"predictor_provenance": "legacy"}),
    ({}, {"predictor-provenance": None}),
    ({"expected-predictor": "replacement.json"}, {}),
    ({}, {"expected_predictor": None}),
    ({}, {"predictor-provenance": "strict", "predictor_provenance": "legacy"}),
])
def test_batch_layers_cannot_weaken_or_replace_inherited_pin(defaults, cell):
    args = runner.parse_args([
        "run-batch", "--predictor-provenance", "strict", "--expected-predictor", "reviewed.json",
    ])
    with pytest.raises(ValueError):
        runner.batch_cell_namespace(args, {"defaults": defaults}, cell)


def _strict_cell_args(tmp_path, expected_path=None):
    argv = [
        "run-cell", "--run-id", "offline-run", "--cell-id", "offline-cell",
        "--row-id", "forces", "--mlip-id", "chgnet", "--artifact-prefix", str(tmp_path / "artifacts"),
        "--fixture-url", str(tmp_path / "unused-fixture.json"), "--predictor-provenance", "strict",
        "--checkpoint-url", str(tmp_path / "checkpoint.json"),
    ]
    if expected_path is not None:
        argv += ["--expected-predictor", str(expected_path)]
    return runner.parse_args(argv)


def test_missing_pin_rejects_before_model_manifest_or_cache(monkeypatch, tmp_path):
    def forbidden(*args, **kwargs):
        pytest.fail("missing strict pin reached a model, manifest, or cache")

    for name in ("load_calculator", "load_manifest", "CellCheckpoint", "run_row"):
        monkeypatch.setattr(runner, name, forbidden)
    with pytest.raises(ProvenanceError):
        runner.run_cell(_strict_cell_args(tmp_path))


@pytest.mark.parametrize("field", ["model_identifier", "loaded_state_sha256", "inference_config_sha256"])
def test_observed_pin_mismatch_precedes_cache_and_prediction(monkeypatch, tmp_path, field):
    observed = _provenance()
    expected = {"schema": "lupine.predictor.expectation.v1", **{
        key: observed[key] for key in ("model_identifier", "loaded_state_sha256", "inference_config_sha256")
    }}
    expected[field] = "different-model" if field == "model_identifier" else "sha256:" + "f" * 64
    pin = tmp_path / "expected.json"
    pin.write_text(json.dumps(expected), encoding="utf8")
    cache = tmp_path / "checkpoint.json"
    cache.write_bytes(b"existing evidence must stay untouched")
    monkeypatch.setattr(runner, "load_manifest", lambda _path: {"offline": True})
    monkeypatch.setattr(provenance_module, "observe_chgnet", lambda *a, **kw: observed)

    def forbidden(*args, **kwargs):
        pytest.fail("mismatched loaded identity reached cache reuse or prediction")

    for name in ("CellCheckpoint", "run_row", "load_calculator"):
        monkeypatch.setattr(runner, name, forbidden)
    with pytest.raises(ProvenanceError, match="loaded predictor mismatch"):
        runner.run_cell(_strict_cell_args(tmp_path, pin), preloaded_calc=object())
    assert cache.read_bytes() == b"existing evidence must stay untouched"


@pytest.mark.parametrize("model,row,profile", [
    ("mace-mp-0", "forces", "off"),
    ("chgnet", runner.BARRIER_ROW_ID, "off"),
    ("chgnet", "forces", "accuracy"),
])
def test_unsupported_strict_batch_rejects_before_loading_a_calculator(monkeypatch, tmp_path, model, row, profile):
    pin = tmp_path / "expected.json"
    pin.write_text(json.dumps(_expectation()), encoding="utf8")
    spec = {
        "defaults": {"distill_profile": profile},
        "cells": [{"cell_id": "unsupported", "mlip_id": model, "row_id": row}],
    }
    monkeypatch.setattr(runner, "load_batch_spec", lambda _path: spec)

    def forbidden(*args, **kwargs):
        pytest.fail("unsupported strict batch attempted calculator loading or execution")

    monkeypatch.setattr(runner, "load_calculator", forbidden)
    monkeypatch.setattr(runner, "run_cell", forbidden)
    monkeypatch.setattr(runner, "emit_beat", lambda *a, **kw: None)
    monkeypatch.setattr(runner, "emit_telemetry", lambda *a, **kw: None)
    args = runner.parse_args([
        "run-batch", "--batch-spec-url", "unused.json", "--predictor-provenance", "strict",
        "--expected-predictor", str(pin),
    ])
    with pytest.raises(ProvenanceError):
        runner.run_batch(args)
