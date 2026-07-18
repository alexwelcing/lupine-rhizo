from __future__ import annotations

import sys
import types

import mlip_cell_runner as runner


def test_load_uma_uses_fairchem_calculator_contract(monkeypatch) -> None:
    calls = {}

    class PretrainedMlip:
        @staticmethod
        def get_predict_unit(model_name, device):
            calls["model_name"] = model_name
            calls["device"] = device
            return {"predictor": model_name}

    def fake_calculator(predictor, task_name):
        calls["predictor"] = predictor
        calls["task_name"] = task_name
        return {"calculator": predictor, "task_name": task_name}

    fairchem = types.ModuleType("fairchem")
    core = types.ModuleType("fairchem.core")
    core.pretrained_mlip = PretrainedMlip
    core.FAIRChemCalculator = fake_calculator
    fairchem.core = core
    monkeypatch.setitem(sys.modules, "fairchem", fairchem)
    monkeypatch.setitem(sys.modules, "fairchem.core", core)
    monkeypatch.setattr(runner, "device", lambda: "cuda")
    monkeypatch.setenv("UMA_TASK_NAME", "omat")

    calc = runner.load_calculator("uma-s-1p2")

    assert calc == {"calculator": {"predictor": "uma-s-1p2"}, "task_name": "omat"}
    assert calls == {
        "model_name": "uma-s-1p2",
        "device": "cuda",
        "predictor": {"predictor": "uma-s-1p2"},
        "task_name": "omat",
    }


def test_load_mace_checkpoint_by_registered_id(monkeypatch) -> None:
    calls = []

    def fake_mace_mp(**kwargs):
        calls.append(kwargs)
        return {"calculator": kwargs["model"]}

    mace = types.ModuleType("mace")
    calculators = types.ModuleType("mace.calculators")
    calculators.__dict__["mace_mp"] = fake_mace_mp
    mace.__dict__["calculators"] = calculators
    monkeypatch.setitem(sys.modules, "mace", mace)
    monkeypatch.setitem(sys.modules, "mace.calculators", calculators)
    monkeypatch.setattr(runner, "device", lambda: "cuda")
    monkeypatch.setattr(runner, "patch_torch_load_for_trusted_checkpoints", lambda: None)

    expected = {
        "mace-mp-0": "medium",
        "mace-mp-small": "small",
        "mace-mp-medium": "medium",
        "mace-mpa-0-medium": "medium-mpa-0",
    }
    for mlip_id, checkpoint in expected.items():
        assert runner.load_calculator(mlip_id) == {"calculator": checkpoint}
    assert calls == [
        {"model": checkpoint, "device": "cuda", "default_dtype": "float32"}
        for checkpoint in expected.values()
    ]
