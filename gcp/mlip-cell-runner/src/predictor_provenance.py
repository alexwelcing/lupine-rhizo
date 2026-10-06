"""Prospective CHGNet 0.4.2 CPU identity gate; never loads a model or predicts.

State serialization v1: prefix b'lupine.loaded-state.v1\\0', then tensors in
lexicographic state_dict-key order. Each tensor contributes three uint64 big-
endian length-prefixed fields: UTF-8 key, canonical JSON {dtype,shape}, and
contiguous C-order little-endian raw bytes. Dtype includes kind and width; shape
includes all dimensions. Dense finite bool/integer/float32/float64 tensors only.
Persistent buffers are included through state_dict; additional named buffers
are inserted with reserved key prefix '\\0buffer:' (original keys cannot contain
NUL). Storage layout/device addresses and pickle are not part of the digest.

This is a scoped adapter, not arbitrary PyTorch provenance. It requires observed
CHGNet constructor/graph/calculator settings, module repr/eval state, exact vendor
version, implementation hashes and CPU compute settings. Only the legacy graph
algorithm is covered; compiled fast-graph code is deliberately unsupported.
Concurrent writers to the same checkpoint are unsupported. A state digest is
not a checkpoint-file hash, signature or scientific proof.
"""
from __future__ import annotations

import hashlib
import importlib.metadata
import inspect
import json
import platform
from pathlib import Path
import re
import struct
from typing import Any

import numpy as np


class ProvenanceError(ValueError):
    """Strict evidence is missing, unsupported or disagrees with the pin."""


UNKNOWN = {"status": "unknown", "mode": "legacy", "reason": "loaded_predictor_not_verified"}
SCHEMA = "lupine.predictor.provenance.v1"
EXPECTATION_SCHEMA = "lupine.predictor.expectation.v1"
DIGEST = re.compile(r"sha256:[0-9a-f]{64}\Z")


def canonical(value: Any) -> bytes:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=True, allow_nan=False).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ProvenanceError("inference configuration is not finite JSON") from exc


def digest(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical(value)).hexdigest()


def source_identity(obj: Any) -> dict[str, str]:
    """Record source content and qualified symbol, never a private host path."""
    try:
        path = inspect.getsourcefile(obj)
        if not path:
            raise ValueError("source unavailable")
        content = Path(path).read_bytes()
        return {"symbol": f"{obj.__module__}.{obj.__qualname__}",
                "source_sha256": "sha256:" + hashlib.sha256(content).hexdigest()}
    except (OSError, TypeError, AttributeError, ValueError) as exc:
        raise ProvenanceError("implementation source identity unavailable") from exc


def package_version(name: str) -> str:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError as exc:
        raise ProvenanceError(f"required package version unavailable: {name}") from exc


def cpu_runtime() -> dict[str, Any]:
    import torch
    if torch.is_autocast_enabled() or torch.is_autocast_cpu_enabled():
        raise ProvenanceError("strict CPU adapter does not support autocast")
    return {
        "torch": package_version("torch"), "numpy": np.__version__,
        "ase": package_version("ase"), "pymatgen": package_version("pymatgen"),
        "default_dtype": str(torch.get_default_dtype()),
        "float32_matmul_precision": torch.get_float32_matmul_precision(),
        "deterministic_algorithms": torch.are_deterministic_algorithms_enabled(),
        "num_threads": torch.get_num_threads(),
        "num_interop_threads": torch.get_num_interop_threads(),
        "mkldnn_enabled": torch.backends.mkldnn.enabled,
        "cpu_capability": torch.backends.cpu.get_cpu_capability(),
        "machine": platform.machine(), "python": platform.python_version(),
        "torch_build": torch.__config__.show(),
    }


def loaded_state(model: Any) -> tuple[str, list[str]]:
    try:
        state = model.state_dict()
    except Exception as exc:
        raise ProvenanceError("actual loaded model state unavailable") from exc
    if not isinstance(state, dict) or not state or not all(isinstance(k, str) and k and "\0" not in k for k in state):
        raise ProvenanceError("loaded state must be a nonempty named tensor mapping")
    state = dict(state)
    if callable(getattr(model, "named_buffers", None)):
        try:
            for name, tensor in model.named_buffers():
                if not isinstance(name, str) or not name or "\0" in name:
                    raise ProvenanceError("unsupported registered buffer name")
                if name not in state:
                    state["\0buffer:" + name] = tensor
        except ProvenanceError:
            raise
        except Exception as exc:
            raise ProvenanceError("registered buffer enumeration unavailable") from exc
    hasher = hashlib.sha256(b"lupine.loaded-state.v1\0")
    dtypes: set[str] = set()
    for name in sorted(state):
        tensor = state[name]
        if str(getattr(tensor, "device", None)) != "cpu":
            raise ProvenanceError("strict adapter requires actual CPU tensors")
        if bool(getattr(tensor, "is_sparse", False)) or bool(getattr(tensor, "is_quantized", False)):
            raise ProvenanceError("sparse or quantized state is unsupported")
        try:
            array = tensor.detach().cpu().contiguous().numpy()
        except Exception as exc:
            raise ProvenanceError("loaded state contains an unsupported tensor") from exc
        if not isinstance(array, np.ndarray) or array.dtype.kind not in "biuf":
            raise ProvenanceError("loaded state must contain numeric dense tensors")
        if array.dtype.kind == "f" and array.dtype.itemsize not in (4, 8):
            raise ProvenanceError("strict adapter supports float32/float64 state only")
        if not np.isfinite(array).all():
            raise ProvenanceError("loaded state contains non-finite values")
        dtype = array.dtype.newbyteorder("<")
        shape = list(array.shape)
        array = np.ascontiguousarray(array.astype(dtype, copy=False))
        dtypes.add(dtype.name)
        metadata = canonical({"dtype": dtype.str, "shape": shape})
        for field in (name.encode("utf-8"), metadata, array.tobytes(order="C")):
            hasher.update(struct.pack(">Q", len(field)))
            hasher.update(field)
    return "sha256:" + hasher.hexdigest(), sorted(dtypes)


def _required(obj: Any, name: str, allowed: tuple[type, ...]) -> Any:
    value = getattr(obj, name, None)
    if not isinstance(value, allowed):
        raise ProvenanceError(f"required observed configuration missing: {name}")
    canonical(value)
    return value


def observe_chgnet(calc: Any, *, calculator_dtype: str, semantics: dict[str, Any]) -> dict[str, Any]:
    """Extract from calculator.model actually used for prediction, never a path."""
    if (type(calc).__module__, type(calc).__name__) != ("chgnet.model.dynamics", "CHGNetCalculator"):
        raise ProvenanceError("strict v1 supports only CHGNetCalculator from chgnet 0.4.2")
    if package_version("chgnet") != "0.4.2":
        raise ProvenanceError("strict v1 requires chgnet package version 0.4.2")
    model = getattr(calc, "model", None)
    if model is None or (type(model).__module__, type(model).__name__) != ("chgnet.model.model", "CHGNet"):
        raise ProvenanceError("calculator's actual CHGNet model is unavailable")
    version = _required(model, "version", (str,))
    if not version or len(version) > 128:
        raise ProvenanceError("loaded CHGNet version unavailable")
    if str(getattr(calc, "device", None)) != "cpu":
        raise ProvenanceError("strict v1 requires CPU calculator execution")
    # ASE can otherwise reuse results from a previous call on identical atoms,
    # including a preloaded calculator whose weights were subsequently changed.
    try:
        calc.reset()
        if getattr(calc, "atoms", None) is not None or getattr(calc, "results", None) != {}:
            raise ValueError("calculator retained prediction cache")
    except Exception as exc:
        raise ProvenanceError("cannot clear existing calculator prediction cache") from exc
    # CHGNet predict_graph calls eval before forward; observe that effective mode.
    try:
        model.eval()
    except Exception as exc:
        raise ProvenanceError("cannot establish effective CHGNet eval mode") from exc
    state_sha, dtypes = loaded_state(model)
    if calculator_dtype not in ("float32", "float64") or any(
        dtype.startswith("float") and dtype != calculator_dtype for dtype in dtypes
    ):
        raise ProvenanceError("actual loaded floating dtype disagrees with requested dtype")
    graph = getattr(model, "graph_converter", None)
    if graph is None:
        raise ProvenanceError("CHGNet graph converter configuration unavailable")
    graph_config = {name: _required(graph, name, kind) for name, kind in (
        ("atom_graph_cutoff", (int, float)), ("bond_graph_cutoff", (int, float)),
        ("algorithm", (str,)), ("on_isolated_atoms", (str,)),
    )}
    if graph_config["algorithm"] != "legacy":
        raise ProvenanceError("strict v1 requires legacy graph algorithm; fast binary identity is unsupported")
    if not callable(getattr(model, "named_buffers", None)):
        raise ProvenanceError("registered buffer enumeration unavailable")
    try:
        modules = list(model.named_modules())
        module_config = []
        for name, module in modules:
            if getattr(module, "training", None) is not False:
                raise ProvenanceError("strict predictor requires all loaded modules in eval mode")
            if any(getattr(module, hook, {}) for hook in ("_forward_hooks", "_forward_pre_hooks", "_backward_hooks")):
                raise ProvenanceError("strict predictor does not support installed module hooks")
            # CHGNet forward uses effective values such as is_intensive/mlp_first
            # and AtomRef.is_intensive, which can differ from constructor args.
            public = {}
            for key, value in vars(module).items():
                if not key.startswith("_") and isinstance(value, (type(None), bool, int, float, str)):
                    public[key] = value
            module_config.append({"name": name, "implementation": source_identity(type(module)),
                                  "extra_repr": module.extra_repr(), "public_scalars": public, "training": False})
        if not module_config:
            raise ProvenanceError("loaded module configuration unavailable")
    except ProvenanceError:
        raise
    except Exception as exc:
        raise ProvenanceError("loaded module configuration unavailable") from exc
    config = {
        "adapter": "chgnet-0.4.2-cpu-baseline-v1",
        "calculator": source_identity(type(calc)), "model": source_identity(type(model)),
        "graph_converter": source_identity(type(graph)), "graph_settings": graph_config,
        "model_args": _required(model, "model_args", (dict,)),
        "calculator_parameters": dict(_required(calc, "parameters", (dict,))),
        "stress_weight": _required(calc, "stress_weight", (int, float)),
        "return_site_energies": _required(calc, "return_site_energies", (bool,)),
        "device": "cpu", "loaded_dtypes": dtypes, "requested_dtype": calculator_dtype,
        "calculator_cache": "reset_before_identity_gate",
        "modules": module_config, "runtime": cpu_runtime(), "compute_semantics": semantics,
        "adapter_implementation": source_identity(observe_chgnet),
    }
    return {"schema": SCHEMA, "status": "observed", "mode": "strict",
            "model_identifier": f"chgnet:{version}", "loaded_state_sha256": state_sha,
            "inference_config_sha256": digest(config), "inference_config": config,
            "predictor_sha256": digest({"model_identifier": f"chgnet:{version}",
                "loaded_state_sha256": state_sha, "inference_config_sha256": digest(config)})}


def load_expected(path: str | None) -> dict[str, Any]:
    if not isinstance(path, str) or not path or "://" in path:
        raise ProvenanceError("strict mode requires a local --expected-predictor JSON file")
    try:
        if Path(path).stat().st_size > 16_384:
            raise ProvenanceError("predictor expectation exceeds size limit")
        value = json.loads(Path(path).read_text())
    except (OSError, ValueError) as exc:
        raise ProvenanceError("predictor expectation unavailable or malformed") from exc
    fields = {"schema", "model_identifier", "loaded_state_sha256", "inference_config_sha256"}
    if not isinstance(value, dict) or set(value) != fields or value["schema"] != EXPECTATION_SCHEMA:
        raise ProvenanceError("unsupported predictor expectation schema")
    if not isinstance(value["model_identifier"], str) or not value["model_identifier"]:
        raise ProvenanceError("expected model identity is required")
    if not all(isinstance(value[k], str) and DIGEST.fullmatch(value[k])
               for k in ("loaded_state_sha256", "inference_config_sha256")):
        raise ProvenanceError("expected state and configuration SHA256 digests are required")
    return value


def verify_expected(observed: dict[str, Any], expected: dict[str, Any]) -> dict[str, Any]:
    for key in ("model_identifier", "loaded_state_sha256", "inference_config_sha256"):
        if not expected.get(key) or observed.get(key) != expected[key]:
            raise ProvenanceError(f"loaded predictor mismatch: {key}")
    return {**observed, "status": "verified"}
