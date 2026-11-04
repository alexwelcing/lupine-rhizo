from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import lupine_distill_runtime.policy_engine as policy_engine_module
import pytest
from lupine_distill_runtime.policy_engine import AutoPolicyEngine, RustPolicyEngine, build_policy_engine


class _PlainBiasSupport:
    correction = {"energy_bias_ev_per_atom": 0.01}
    diagnostics: dict = {}

    def correction_evidence(self):
        return dict(self.correction)

    def correct_prediction(self, prediction):
        return dict(prediction), [{"action": "accept", "reason": "bias_applied"}]


class _GatedSupport(_PlainBiasSupport):
    correction = {
        "direction_gated_correction_v1": {
            "schema": "lupine.distill.direction_gate.v1",
            "cells": {"energy:default": {"applied": True, "b": 1.1, "s": 0.02, "n_calibration": 3}},
        }
    }

    def correction_evidence(self):
        return dict(self.correction)


def _engine_with_fake_rust(tmp_path: Path, monkeypatch, calls: list) -> AutoPolicyEngine:
    distill_bin = tmp_path / "distill"
    distill_bin.write_text("test double", encoding="utf-8")

    def fake_run(argv, **_kwargs):
        calls.append(argv)
        if "--request-jsonl" in argv:
            requests = [
                json.loads(line)
                for line in Path(argv[argv.index("--request-jsonl") + 1]).read_text().splitlines()
            ]
            output_path = Path(argv[argv.index("--output") + 1])
            output_path.write_text(
                "".join(
                    json.dumps(
                        {
                            "corrected_prediction": request["prediction"],
                            "actions": [{"action": "accept", "reason": "runtime_guards_passed"}],
                            "decision": "accept",
                            "refused": False,
                        }
                    )
                    + "\n"
                    for request in requests
                ),
                encoding="utf-8",
            )
            return SimpleNamespace(returncode=0, stderr="", stdout="")
        request_path = Path(argv[argv.index("--request") + 1])
        request = json.loads(request_path.read_text(encoding="utf-8"))
        return SimpleNamespace(
            returncode=0,
            stderr="",
            stdout=json.dumps(
                {
                    "corrected_prediction": request["prediction"],
                    "actions": [{"action": "accept", "reason": "runtime_guards_passed"}],
                    "decision": "accept",
                    "refused": False,
                }
            ),
        )

    monkeypatch.setattr(policy_engine_module.subprocess, "run", fake_run)
    return AutoPolicyEngine(profile="accuracy", distill_bin=distill_bin)


def test_direction_gated_support_routes_around_rust(tmp_path, monkeypatch) -> None:
    """Codex PR#53 P1: the Rust engine has no handler for the gated block;
    its presence must force the Python path with an audit trail."""
    calls: list = []
    engine = _engine_with_fake_rust(tmp_path, monkeypatch, calls)
    decisions = engine.decide_many(
        row_id="energy_volume",
        mlip_id="chgnet",
        predictions=[{"material_id": "Ni-fcc", "energy_ev_per_atom": -5.0}],
        support_model=_GatedSupport(),
    )
    assert calls == [], "rust binary must not be invoked for direction-gated support"
    assert len(decisions) == 1
    assert decisions[0].policy_engine == "python_fallback"
    assert decisions[0].raw["route_reason"] == "direction_gate_python_engine"


def test_plain_bias_support_still_prefers_rust(tmp_path, monkeypatch) -> None:
    calls: list = []
    engine = _engine_with_fake_rust(tmp_path, monkeypatch, calls)
    decisions = engine.decide_many(
        row_id="energy_volume",
        mlip_id="chgnet",
        predictions=[{"material_id": "Ni-fcc", "energy_ev_per_atom": -5.0}],
        support_model=_PlainBiasSupport(),
    )
    assert len(calls) == 1, "rust remains the default for un-gated support"
    assert decisions[0].policy_engine != "python_fallback" or "route_reason" not in decisions[0].raw


@pytest.mark.parametrize(
    "factory",
    [
        pytest.param(lambda **kwargs: RustPolicyEngine(**kwargs), id="rust"),
        pytest.param(lambda **kwargs: AutoPolicyEngine(profile="accuracy", **kwargs), id="auto"),
        pytest.param(
            lambda **kwargs: build_policy_engine(
                "rust", profile="accuracy", env_field_report_path=None, **kwargs
            ),
            id="builder",
        ),
    ],
)
def test_binary_configuration_accepts_legacy_input_and_stores_canonical(tmp_path, factory):
    binary = tmp_path / "distill"
    for kwargs in (
        {"distill_bin": binary},
        {"atlas_distill_bin": binary},
        {"distill_bin": binary, "atlas_distill_bin": str(binary)},
    ):
        engine = factory(**kwargs)
        rust = getattr(engine, "rust", engine)
        assert rust.distill_bin == binary
        assert not hasattr(rust, "atlas_distill_bin")
    with pytest.raises(ValueError, match="conflicting distill_bin"):
        factory(distill_bin=binary, atlas_distill_bin=tmp_path / "other")


def test_binary_environment_accepts_legacy_and_rejects_conflicts(tmp_path, monkeypatch):
    canonical = tmp_path / "distill"
    monkeypatch.delenv("DISTILL_BIN", raising=False)
    monkeypatch.setenv("ATLAS_DISTILL_BIN", str(canonical))
    assert RustPolicyEngine().distill_bin == canonical
    monkeypatch.setenv("DISTILL_BIN", str(canonical))
    assert RustPolicyEngine().distill_bin == canonical
    monkeypatch.setenv("DISTILL_BIN", str(tmp_path / "other"))
    with pytest.raises(ValueError, match="conflicting DISTILL_BIN"):
        RustPolicyEngine()


def test_explicit_binary_overrides_environment(tmp_path, monkeypatch):
    monkeypatch.setenv("ATLAS_DISTILL_BIN", str(tmp_path / "legacy"))
    monkeypatch.delenv("DISTILL_BIN", raising=False)
    assert RustPolicyEngine(distill_bin=tmp_path / "distill").distill_bin == tmp_path / "distill"


def test_default_binary_discovery_uses_distill(tmp_path, monkeypatch):
    monkeypatch.delenv("DISTILL_BIN", raising=False)
    monkeypatch.delenv("ATLAS_DISTILL_BIN", raising=False)
    commands = []
    monkeypatch.setattr(
        policy_engine_module.shutil, "which", lambda command: commands.append(command)
    )
    engine = RustPolicyEngine()
    assert commands == ["distill"]
    executable = "distill.exe" if policy_engine_module.os.name == "nt" else "distill"
    assert engine.distill_bin == policy_engine_module._repo_root() / "distill" / "target" / "debug" / executable
