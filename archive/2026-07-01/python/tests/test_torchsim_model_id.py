"""TorchSim backend model-id -> MACE checkpoint mapping tests.

``runner.run_suite`` stamps the REQUESTED ``model_id`` into the emitted
``BenchmarkResult``, so the backend must load exactly the checkpoint that id
names. A silent default (the historical hardcoded ``"medium"``) attributes
benchmark numbers to models that never ran — a wrong claim entering the
evidence chain silently.

These tests MUST pass without torch_sim / torch / mace installed: every heavy
dependency is stubbed via ``sys.modules`` monkeypatching, mirroring the
import-safety conventions of ``test_backends.py``.
"""

from __future__ import annotations

import sys
from types import ModuleType
from typing import Any

import pytest

import lupine_distill.backends.torchsim as torchsim_mod
from lupine_distill.backends.torchsim import (
    MACE_CHECKPOINT_BY_MODEL_ID,
    TorchSimBenchmarkBackend,
    resolve_mace_checkpoint,
)

# --------------------------------------------------------------------------- #
# Pure resolver: the module-level mapping is the single source of truth.
# --------------------------------------------------------------------------- #


@pytest.mark.unit
def test_resolve_mace_mp_0_is_medium() -> None:
    # The canonical MACE-MP-0 foundation release is the medium checkpoint.
    assert resolve_mace_checkpoint("mace-mp-0") == "medium"


@pytest.mark.unit
@pytest.mark.parametrize(
    ("model_id", "expected"),
    [
        ("mace-mp-0-small", "small"),
        ("mace-small", "small"),
        ("mace-mp-0-medium", "medium"),
        ("mace-medium", "medium"),
        ("mace-mp-0-large", "large"),
        ("mace-large", "large"),
    ],
)
def test_resolve_size_aliases(model_id: str, expected: str) -> None:
    assert resolve_mace_checkpoint(model_id) == expected


@pytest.mark.unit
def test_resolve_is_case_insensitive() -> None:
    # schemas.py documents ids like 'MACE-MP-0-small'; casing must not
    # silently change which checkpoint runs.
    assert resolve_mace_checkpoint("MACE-MP-0-small") == "small"
    assert resolve_mace_checkpoint("MACE-MP-0") == "medium"


@pytest.mark.unit
def test_resolve_unknown_id_raises_with_accepted_ids() -> None:
    with pytest.raises(ValueError) as excinfo:
        resolve_mace_checkpoint("not-a-model")
    message = str(excinfo.value)
    assert "not-a-model" in message
    # The error must teach the caller the accepted vocabulary.
    for accepted in MACE_CHECKPOINT_BY_MODEL_ID:
        assert accepted in message


@pytest.mark.unit
def test_mapping_covers_repo_call_sites() -> None:
    # Ids actually passed to the backend in this repo must stay resolvable:
    # scripts/run_cross_material_transfer.py passes 'mace-mp-0'.
    assert "mace-mp-0" in MACE_CHECKPOINT_BY_MODEL_ID
    # Only real MACE-MP checkpoint sizes may appear as targets.
    assert set(MACE_CHECKPOINT_BY_MODEL_ID.values()) <= {"small", "medium", "large"}


# --------------------------------------------------------------------------- #
# Backend integration: _ensure_model must request the mapped checkpoint from
# mace_mp — asserted against fully stubbed torch / mace / torch_sim modules.
# --------------------------------------------------------------------------- #


class _FakeMaceModel:
    """Records the kwargs torchsim.MaceModel would receive."""

    def __init__(self, **kwargs: Any) -> None:
        self.kwargs = kwargs


def _install_stubs(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Stub every heavy import so _ensure_model runs without GPUs/deps.

    Returns the (mutable) list that records each ``model=`` size requested
    from the stubbed ``mace_mp``.
    """
    requested_sizes: list[str] = []

    # torch_sim: constructor import — a bare module object is enough.
    fake_torch_sim = ModuleType("torch_sim")
    fake_torch_sim.__version__ = "0.0-test"
    monkeypatch.setattr(torchsim_mod, "_import_torch_sim", lambda: fake_torch_sim)

    # torch: _ensure_model needs cuda.is_available, dtype attr, device().
    fake_torch = ModuleType("torch")
    fake_torch.cuda = ModuleType("torch.cuda")
    fake_torch.cuda.is_available = lambda: False
    fake_torch.float64 = object()
    fake_torch.device = lambda name: f"device({name})"
    monkeypatch.setitem(sys.modules, "torch", fake_torch)

    # mace.calculators.foundations_models.mace_mp: record the size requested.
    def fake_mace_mp(**kwargs: Any) -> str:
        requested_sizes.append(kwargs["model"])
        return "raw-mace-model"

    fake_foundations = ModuleType("mace.calculators.foundations_models")
    fake_foundations.mace_mp = fake_mace_mp
    monkeypatch.setitem(sys.modules, "mace", ModuleType("mace"))
    monkeypatch.setitem(sys.modules, "mace.calculators", ModuleType("mace.calculators"))
    monkeypatch.setitem(sys.modules, "mace.calculators.foundations_models", fake_foundations)

    # torch_sim.models.mace.MaceModel: capture construction.
    fake_ts_mace = ModuleType("torch_sim.models.mace")
    fake_ts_mace.MaceModel = _FakeMaceModel
    monkeypatch.setitem(sys.modules, "torch_sim.models.mace", fake_ts_mace)

    return requested_sizes


@pytest.mark.unit
def test_ensure_model_requests_medium_for_mace_mp_0(monkeypatch: pytest.MonkeyPatch) -> None:
    requested = _install_stubs(monkeypatch)
    backend = TorchSimBenchmarkBackend(model_id="mace-mp-0")
    model = backend._ensure_model()
    assert requested == ["medium"]
    assert isinstance(model, _FakeMaceModel)
    assert model.kwargs["model"] == "raw-mace-model"


@pytest.mark.unit
def test_ensure_model_requests_small_for_small_alias(monkeypatch: pytest.MonkeyPatch) -> None:
    requested = _install_stubs(monkeypatch)
    backend = TorchSimBenchmarkBackend(model_id="mace-mp-0-small")
    backend._ensure_model()
    assert requested == ["small"]


@pytest.mark.unit
def test_construct_with_unknown_id_fails_fast(monkeypatch: pytest.MonkeyPatch) -> None:
    # Fail at the call site, before any expensive model download/build.
    requested = _install_stubs(monkeypatch)
    with pytest.raises(ValueError, match="mace-mp-0"):
        TorchSimBenchmarkBackend(model_id="totally-unknown-model")
    assert requested == []  # mace_mp must never have been called


@pytest.mark.unit
def test_ensure_model_refuses_unmapped_id(monkeypatch: pytest.MonkeyPatch) -> None:
    # Belt-and-braces: even if an unmapped id sneaks past construction,
    # _ensure_model must refuse rather than default to a checkpoint.
    requested = _install_stubs(monkeypatch)
    backend = TorchSimBenchmarkBackend(model_id="mace-mp-0")
    backend._model_id = "smuggled-unknown-id"
    with pytest.raises(ValueError, match="smuggled-unknown-id"):
        backend._ensure_model()
    assert requested == []


@pytest.mark.unit
def test_stubs_do_not_leak_torch_sim_into_sys_modules(monkeypatch: pytest.MonkeyPatch) -> None:
    # test_backends.py asserts 'torch_sim' is never imported at module load;
    # this suite's stubbing must not violate that invariant either.
    _install_stubs(monkeypatch)
    backend = TorchSimBenchmarkBackend(model_id="mace-mp-0")
    backend._ensure_model()
    assert "torch_sim" not in sys.modules
