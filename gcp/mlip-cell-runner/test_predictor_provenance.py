"""No vendor imports: observable calculator/state contract tested with fake tensors."""
import json
import sys
import types

import numpy as np
import pytest

from src import predictor_provenance as provenance


class FakeTensor:
    device = "cpu"
    is_sparse = False
    is_quantized = False

    def __init__(self, value, dtype="float32"):
        self.array = np.asarray(value, dtype=dtype)

    def detach(self): return self
    def cpu(self): return self
    def contiguous(self): return self
    def numpy(self): return self.array


class AtomRef:
    def __init__(self):
        self.training = True
        self.is_intensive = True

    def extra_repr(self): return ""


class CrystalGraphConverter:
    atom_graph_cutoff = 6.0
    bond_graph_cutoff = 3.0
    algorithm = "legacy"
    on_isolated_atoms = "warn"


class CHGNet:
    version = "0.3.0"

    def __init__(self, weight=1.0, dtype="float32"):
        self.weight = FakeTensor([weight], dtype)
        self.buffer = FakeTensor([2], "int64")
        self.training = True
        self.is_intensive = True
        self.n_conv = 4
        self.model_args = {"version": "0.3.0", "n_conv": 4, "atom_fea_dim": 64}
        self.graph_converter = CrystalGraphConverter()
        self.composition_model = AtomRef()

    def eval(self):
        self.training = self.composition_model.training = False
        return self

    def state_dict(self): return {"weight": self.weight, "buffer": self.buffer}
    def named_buffers(self): return [("buffer", self.buffer)]
    def named_modules(self): return [("", self), ("composition_model", self.composition_model)]
    def extra_repr(self): return ""


class CHGNetCalculator:
    def __init__(self, weight=1.0, dtype="float32"):
        self.model = CHGNet(weight, dtype)
        self.device = "cpu"
        self.parameters = {}
        self.stress_weight = 0.006241509125883258
        self.return_site_energies = False

    def reset(self):
        self.atoms = None
        self.results = {}


@pytest.fixture
def fake_calc(monkeypatch):
    for cls, name in [(CHGNetCalculator, "chgnet.model.dynamics"), (CHGNet, "chgnet.model.model")]:
        monkeypatch.setattr(cls, "__module__", name)
        module = types.ModuleType(name)
        module.__file__ = __file__
        setattr(module, cls.__name__, cls)
        monkeypatch.setitem(sys.modules, name, module)
    monkeypatch.setattr(provenance, "package_version", lambda name: "0.4.2" if name == "chgnet" else "test-only")
    monkeypatch.setattr(provenance, "cpu_runtime", lambda: {"torch": "fake-no-inference", "num_threads": 1})
    return CHGNetCalculator()


def observation(calc, dtype="float32"):
    return provenance.observe_chgnet(calc, calculator_dtype=dtype, semantics={"fixture": "fake-test-only"})


def expectation(observed):
    return {"schema": provenance.EXPECTATION_SCHEMA,
            **{key: observed[key] for key in ("model_identifier", "loaded_state_sha256", "inference_config_sha256")}}


def test_stable_same_loaded_state_and_config_allowed(fake_calc):
    first = observation(fake_calc)
    second = observation(CHGNetCalculator())
    assert first == second
    assert first["status"] == "observed"
    assert provenance.verify_expected(second, expectation(first))["status"] == "verified"
    assert fake_calc.model.training is False


def test_changed_loaded_weight_rejected_even_with_same_model_version(fake_calc):
    expected = expectation(observation(fake_calc))
    fake_calc.model.weight.array[0] = 9
    with pytest.raises(provenance.ProvenanceError, match="loaded_state_sha256"):
        provenance.verify_expected(observation(fake_calc), expected)


@pytest.mark.parametrize("change", [
    lambda c: setattr(c, "return_site_energies", True),
    lambda c: setattr(c, "stress_weight", 2.0),
    lambda c: setattr(c.model.graph_converter, "atom_graph_cutoff", 5.5),
    lambda c: setattr(c.model, "is_intensive", False),
    lambda c: setattr(c.model.composition_model, "is_intensive", False),
])
def test_effective_config_changes_rejected(fake_calc, change):
    before = observation(fake_calc)
    change(fake_calc)
    after = observation(fake_calc)
    assert after["loaded_state_sha256"] == before["loaded_state_sha256"]
    with pytest.raises(provenance.ProvenanceError, match="inference_config_sha256"):
        provenance.verify_expected(after, expectation(before))


def test_dtype_change_changes_state_and_config_and_wrong_requested_dtype_fails(fake_calc):
    before = observation(fake_calc)
    fake_calc.model.weight = FakeTensor([1.0], "float64")
    with pytest.raises(provenance.ProvenanceError, match="dtype"):
        observation(fake_calc)
    after = observation(fake_calc, "float64")
    assert before["loaded_state_sha256"] != after["loaded_state_sha256"]
    assert before["inference_config_sha256"] != after["inference_config_sha256"]


@pytest.mark.parametrize("mutation", [
    lambda c: setattr(c, "model", None),
    lambda c: setattr(c, "device", "cuda:0"),
    lambda c: setattr(c.model.weight, "device", "cuda:0"),
    lambda c: setattr(c.model, "model_args", None),
    lambda c: setattr(c.model.graph_converter, "algorithm", None),
    lambda c: setattr(c.model.graph_converter, "algorithm", "fast"),
    lambda c: setattr(c.model, "_forward_hooks", {0: object()}),
])
def test_unobserved_unsupported_configuration_fails(fake_calc, mutation):
    mutation(fake_calc)
    with pytest.raises(provenance.ProvenanceError): observation(fake_calc)


def test_missing_expected_pin_rejected(tmp_path):
    with pytest.raises(provenance.ProvenanceError): provenance.load_expected(None)
    path = tmp_path / "pin.json"
    path.write_text(json.dumps({"schema": provenance.EXPECTATION_SCHEMA}))
    with pytest.raises(provenance.ProvenanceError): provenance.load_expected(str(path))


def test_state_serialization_order_layout_byte_order_and_shape():
    model = CHGNet()
    original, _ = provenance.loaded_state(model)
    model.state_dict = lambda: {"buffer": model.buffer, "weight": model.weight}
    assert provenance.loaded_state(model)[0] == original
    model.weight.array = model.weight.array.astype(">f4")
    assert provenance.loaded_state(model)[0] == original
    model.weight.array = np.asarray(1.0, dtype="float32")
    assert provenance.loaded_state(model)[0] != original  # scalar differs from one-element vector


def test_nonpersistent_registered_buffer_changes_loaded_identity(fake_calc):
    before = observation(fake_calc)
    extra = FakeTensor([3.0])
    fake_calc.model.named_buffers = lambda: [("buffer", fake_calc.model.buffer), ("nonpersistent", extra)]
    after = observation(fake_calc)
    assert before["loaded_state_sha256"] != after["loaded_state_sha256"]
    extra.array[0] = 8
    assert observation(fake_calc)["loaded_state_sha256"] != after["loaded_state_sha256"]


def test_existing_calculator_result_is_cleared_before_identity(fake_calc):
    fake_calc.atoms = "previous structure"
    fake_calc.results = {"forces": "old weights"}
    observation(fake_calc)
    assert fake_calc.atoms is None
    assert fake_calc.results == {}
    fake_calc.reset = lambda: None
    fake_calc.results = {"forces": "stale"}
    with pytest.raises(provenance.ProvenanceError, match="prediction cache"):
        observation(fake_calc)
