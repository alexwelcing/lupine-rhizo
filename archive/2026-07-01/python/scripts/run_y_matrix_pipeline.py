"""Y-matrix micro-demonstration pipeline: ONE command from config to packet.

Composes the two existing, tested CLIs into the demo a visiting lab runs:

1. **sweep**  — every (material, model) cell via
   ``python/scripts/run_y_matrix_statics.py`` as a subprocess. Resumable:
   cells whose result AND evidence JSONs already exist are skipped unless
   ``--force``; a failing cell is recorded loudly and never aborts the run.
2. **bind**   — ``python/scripts/bind_y_matrix_references.py --emit-lean``
   joins the compiled reference targets, emits one Lean module per cell and
   lake-checks it. Honest vocabulary throughout: ``verified`` / ``failed`` /
   ``unchecked`` — an emitted-but-unchecked module is never called verified.
3. **packet** — assembles the CONTRIBUTION PACKET directory (and ``.tar.gz``):
   ``evidence/``, ``bound/``, ``lean/``, ``binding_report.json``,
   ``manifest.json`` (config used, package versions, torch/CUDA versions,
   GPU name, timestamps, per-cell wall times) and a human-readable
   ``REPORT.md``. The packet is what a lab mails back — nothing in this
   pipeline assumes wrangler, tokens, or cloud access.

Run (from any directory; relative config paths resolve against the repo root):

    python python/scripts/run_y_matrix_pipeline.py \
        --config config/y_matrix_demo.yaml --profile demo-small \
        [--device cuda|cpu] [--skip-lake] [--force] [--python PATH]

``--python`` selects the interpreter used for the sweep/bind subprocesses
(default: the interpreter running this script). Use it when the pipeline is
driven from a different environment than the pinned MLIP one.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import logging
import platform
import shutil
import subprocess
import sys
import tarfile
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

_HERE = Path(__file__).resolve()
_REPO_ROOT = _HERE.parents[2]
for _p in (str(_HERE.parents[1]), str(_REPO_ROOT)):  # python/ ; repo root
    if _p not in sys.path:
        sys.path.insert(0, _p)

import yaml  # noqa: E402

from lupine_distill.statics import SUPPORTED_STRUCTURE_TYPES  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
log = logging.getLogger("y_matrix_pipeline")

CONFIG_SCHEMA = "lupine.y_matrix_demo_config.v1"
MANIFEST_SCHEMA = "lupine.y_matrix_packet_manifest.v1"
STATICS_RUN_SCHEMA = "lupine.statics_run.v1"

_STATICS_SCRIPT = _HERE.with_name("run_y_matrix_statics.py")
_BINDER_SCRIPT = _HERE.with_name("bind_y_matrix_references.py")

# A runner executes one subprocess command, teeing combined stdout+stderr to
# the given log file, and returns the exit code. Injectable for tests.
Runner = Callable[[list[str], Path], int]


def _load_statics_module():
    """Import the statics CLI as a module: its MODEL_REGISTRY, KNOWN_PROPERTIES
    and validate_request are the single source of truth for what a cell may
    request (no torch import happens at module scope)."""
    spec = importlib.util.spec_from_file_location("run_y_matrix_statics", _STATICS_SCRIPT)
    if spec is None or spec.loader is None:  # pragma: no cover - packaging error
        raise ImportError(f"cannot load statics CLI from {_STATICS_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_STATICS = _load_statics_module()
KNOWN_PROPERTIES: tuple[str, ...] = tuple(_STATICS.KNOWN_PROPERTIES)
KNOWN_MODEL_IDS: tuple[str, ...] = tuple(sorted(_STATICS.MODEL_REGISTRY))


class ConfigError(ValueError):
    """A demo config that failed schema or compatibility validation."""


# --------------------------------------------------------------------------
# config schema (style-matched to lupine_distill.schemas: frozen, forbid)
# --------------------------------------------------------------------------


class MaterialSpec(BaseModel):
    """One material row of the matrix: formula + structure + property list."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    formula: str = Field(..., min_length=1, description="Formula, e.g. 'Ni' or 'NiAl'")
    structure: str = Field(..., description=f"One of {SUPPORTED_STRUCTURE_TYPES}")
    properties: tuple[str, ...] = Field(..., min_length=1)

    @field_validator("structure")
    @classmethod
    def _structure_known(cls, value: str) -> str:
        if value not in SUPPORTED_STRUCTURE_TYPES:
            raise ValueError(
                f"unknown structure {value!r}; supported: "
                f"{', '.join(sorted(SUPPORTED_STRUCTURE_TYPES))}"
            )
        return value

    @field_validator("properties")
    @classmethod
    def _properties_known(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        unknown = [p for p in value if p not in KNOWN_PROPERTIES]
        if unknown:
            raise ValueError(
                f"unknown properties {unknown}; known: {', '.join(KNOWN_PROPERTIES)}"
            )
        return value

    @model_validator(mode="after")
    def _compatible(self) -> "MaterialSpec":
        # Reuse the statics CLI's compatibility rules verbatim (it raises
        # SystemExit — a CLI habit — so translate to a validation error).
        try:
            _STATICS.validate_request(self.formula, self.structure, list(self.properties))
        except SystemExit as exc:
            raise ValueError(str(exc)) from exc
        return self


class PacketOptions(BaseModel):
    """Contribution-packet knobs: name and binding tolerance."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str = Field(..., pattern=r"^[A-Za-z0-9._-]+$", description="Packet directory / tarball stem")
    tolerance_pct: float = Field(default=5.0, gt=0.0, description="Binding tolerance, % of |reference|")


class ProfileConfig(BaseModel):
    """One runnable matrix: materials x models plus output/targets/lean paths."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    description: str = Field(..., min_length=1)
    device: str = Field(..., description="'cuda' or 'cpu' (CLI --device overrides)")
    allow_cpu_fallback: bool = Field(
        default=False,
        description="When device=cuda but CUDA is unavailable: fall back to cpu (loudly) "
        "instead of aborting",
    )
    models: tuple[str, ...] = Field(..., min_length=1)
    materials: tuple[MaterialSpec, ...] = Field(..., min_length=1)
    output_dir: str = Field(..., min_length=1)
    targets_dir: str = Field(default="data/y_matrix_targets")
    lean_spec_dir: str = Field(default="lean-spec")
    packet: PacketOptions

    @field_validator("device")
    @classmethod
    def _device_known(cls, value: str) -> str:
        if value not in ("cuda", "cpu"):
            raise ValueError(f"device must be 'cuda' or 'cpu', got {value!r}")
        return value

    @field_validator("models")
    @classmethod
    def _models_known(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        unknown = [m for m in value if m not in KNOWN_MODEL_IDS]
        if unknown:
            raise ValueError(
                f"unknown model id(s) {unknown}; known ids: {', '.join(KNOWN_MODEL_IDS)}. "
                f"Refusing to substitute a different model."
            )
        return value


class DemoConfig(BaseModel):
    """Top-level demo config: schema string + named profiles."""

    model_config = ConfigDict(frozen=True, extra="forbid", populate_by_name=True)

    schema_version: str = Field(..., alias="schema")
    profiles: dict[str, ProfileConfig] = Field(..., min_length=1)

    @field_validator("schema_version")
    @classmethod
    def _schema_known(cls, value: str) -> str:
        if value != CONFIG_SCHEMA:
            raise ValueError(f"expected schema '{CONFIG_SCHEMA}', got {value!r}")
        return value


def load_demo_config(path: Path | str) -> DemoConfig:
    """Read + schema-validate a demo config; every failure is a ConfigError."""
    config_path = Path(path)
    try:
        raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise ConfigError(f"cannot read config {config_path}: {exc}") from exc
    if not isinstance(raw, dict):
        raise ConfigError(f"{config_path}: config must be a YAML mapping")
    try:
        return DemoConfig.model_validate(raw)
    except ValidationError as exc:
        raise ConfigError(f"invalid demo config {config_path}:\n{exc}") from exc


def select_profile(config: DemoConfig, name: str) -> ProfileConfig:
    if name not in config.profiles:
        raise ConfigError(
            f"unknown profile {name!r}; available: {', '.join(sorted(config.profiles))}"
        )
    return config.profiles[name]


def resolve_path(path_str: str) -> Path:
    """Relative config paths resolve against the repo root (works from anywhere)."""
    path = Path(path_str)
    return path if path.is_absolute() else _REPO_ROOT / path


# --------------------------------------------------------------------------
# cell planning + resumability
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Cell:
    """One (material, model) sweep cell and its canonical output names."""

    material: str
    structure: str
    model: str
    properties: tuple[str, ...]

    @property
    def label(self) -> str:
        return f"{self.material}_{self.structure}_{self.model}"

    @property
    def out_name(self) -> str:
        return f"{self.label}.json"

    @property
    def evidence_name(self) -> str:
        return f"{self.label}.evidence.json"


@dataclass(frozen=True)
class CellOutcome:
    """Result of one sweep cell: ok / cached / failed, with wall times."""

    cell: Cell
    status: str  # "ok" | "cached" | "failed"
    wall_time_seconds: float | None = None
    compute_wall_time_seconds: float | None = None
    returncode: int | None = None
    log_name: str | None = None
    detail: str | None = None


def plan_cells(profile: ProfileConfig) -> tuple[Cell, ...]:
    """Materials x models, material-major (matches the worked-example layout)."""
    return tuple(
        Cell(
            material=material.formula,
            structure=material.structure,
            model=model,
            properties=material.properties,
        )
        for material in profile.materials
        for model in profile.models
    )


def is_cached(cell: Cell, runs_dir: Path) -> bool:
    """A cell is resumable-cached iff BOTH outputs exist and the result JSON
    parses with the statics-run schema (a torn write re-runs the cell)."""
    out_path = runs_dir / cell.out_name
    evidence_path = runs_dir / cell.evidence_name
    if not (out_path.is_file() and evidence_path.is_file()):
        return False
    try:
        payload = json.loads(out_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return isinstance(payload, dict) and payload.get("schema") == STATICS_RUN_SCHEMA


def _subprocess_runner(cmd: list[str], log_path: Path) -> int:
    with log_path.open("w", encoding="utf-8") as handle:
        proc = subprocess.run(
            cmd, stdout=handle, stderr=subprocess.STDOUT, cwd=str(_REPO_ROOT)
        )
    return proc.returncode


def _log_tail(log_path: Path, n_lines: int = 8) -> str:
    try:
        lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return "(no log)"
    return "\n".join(lines[-n_lines:])


def _compute_wall_from_result(out_path: Path) -> float | None:
    try:
        payload = json.loads(out_path.read_text(encoding="utf-8"))
        wall = payload.get("total_wall_time_seconds")
        return float(wall) if wall is not None else None
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return None


def sweep_cell_command(
    cell: Cell, *, runs_dir: Path, device: str, python_exe: str, run_label: str
) -> list[str]:
    return [
        python_exe,
        str(_STATICS_SCRIPT),
        "--material", cell.material,
        "--structure", cell.structure,
        "--model", cell.model,
        "--device", device,
        "--properties", ",".join(cell.properties),
        "--out", str(runs_dir / cell.out_name),
        "--evidence-out", str(runs_dir / cell.evidence_name),
        "--run-label", run_label,
    ]


def run_sweep(
    cells: tuple[Cell, ...],
    *,
    runs_dir: Path,
    logs_dir: Path,
    device: str,
    python_exe: str,
    run_label: str,
    force: bool = False,
    runner: Runner | None = None,
) -> tuple[CellOutcome, ...]:
    """Run every cell; skip cached ones unless force; never abort on one failure."""
    run = runner if runner is not None else _subprocess_runner
    runs_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)
    outcomes: list[CellOutcome] = []
    for index, cell in enumerate(cells, start=1):
        prefix = f"[{index}/{len(cells)}]"
        if not force and is_cached(cell, runs_dir):
            log.info("%s [cached] %s", prefix, cell.label)
            outcomes.append(CellOutcome(cell=cell, status="cached"))
            continue
        log.info("%s [cell] %s (%s) on %s ...", prefix, cell.label, ",".join(cell.properties), device)
        cmd = sweep_cell_command(
            cell, runs_dir=runs_dir, device=device, python_exe=python_exe, run_label=run_label
        )
        log_path = logs_dir / f"{cell.label}.log"
        t0 = time.perf_counter()
        try:
            returncode = run(cmd, log_path)
        except OSError as exc:
            wall = time.perf_counter() - t0
            log.error("%s [FAIL] %s: could not launch runner: %s", prefix, cell.label, exc)
            outcomes.append(
                CellOutcome(
                    cell=cell, status="failed", wall_time_seconds=wall,
                    log_name=log_path.name, detail=f"could not launch runner: {exc}",
                )
            )
            continue
        wall = time.perf_counter() - t0
        outputs_present = (runs_dir / cell.out_name).is_file() and (
            runs_dir / cell.evidence_name
        ).is_file()
        if returncode == 0 and outputs_present:
            log.info("%s [ok]   %s (%.1fs)", prefix, cell.label, wall)
            outcomes.append(
                CellOutcome(
                    cell=cell, status="ok", wall_time_seconds=wall,
                    compute_wall_time_seconds=_compute_wall_from_result(runs_dir / cell.out_name),
                    returncode=returncode, log_name=log_path.name,
                )
            )
        else:
            detail = (
                f"exit {returncode}" if returncode != 0
                else "runner exited 0 but outputs are missing"
            )
            log.error(
                "%s [FAIL] %s (%s, %.1fs) — log tail:\n%s",
                prefix, cell.label, detail, wall, _log_tail(log_path),
            )
            outcomes.append(
                CellOutcome(
                    cell=cell, status="failed", wall_time_seconds=wall,
                    returncode=returncode, log_name=log_path.name, detail=detail,
                )
            )
    return tuple(outcomes)


# --------------------------------------------------------------------------
# runner-environment probe + device resolution
# --------------------------------------------------------------------------

_PROBE_PACKAGES = (
    "lupine-distill", "ase", "numpy", "scipy", "pydantic", "PyYAML",
    "torch", "mace-torch", "chgnet", "e3nn", "pymatgen", "matscipy",
)

_PROBE_CODE = f"""
import json, platform
info = {{"python": platform.python_version(), "platform": platform.platform(),
        "torch": None, "cuda_available": False, "cuda_version": None,
        "gpu_name": None, "packages": {{}}}}
try:
    import torch
    info["torch"] = torch.__version__
    info["cuda_available"] = bool(torch.cuda.is_available())
    info["cuda_version"] = getattr(torch.version, "cuda", None)
    if info["cuda_available"]:
        info["gpu_name"] = torch.cuda.get_device_name(0)
except Exception:
    pass
from importlib import metadata
for pkg in {list(_PROBE_PACKAGES)!r}:
    try:
        info["packages"][pkg] = metadata.version(pkg)
    except Exception:
        info["packages"][pkg] = None
print(json.dumps(info))
"""


def probe_runner_env(python_exe: str) -> dict:
    """One subprocess probe of the runner interpreter: torch/CUDA/GPU + pins."""
    try:
        proc = subprocess.run(
            [python_exe, "-c", _PROBE_CODE], capture_output=True, text=True, timeout=300
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"error": f"probe failed: {exc}"}
    if proc.returncode != 0:
        return {"error": f"probe exited {proc.returncode}: {(proc.stderr or '').strip()[:500]}"}
    try:
        return json.loads(proc.stdout.strip().splitlines()[-1])
    except (json.JSONDecodeError, IndexError):
        return {"error": f"probe output unparseable: {proc.stdout[:500]!r}"}


def resolve_device(requested: str, probe: dict, allow_cpu_fallback: bool) -> tuple[str, bool]:
    """Return (device_used, fell_back). CUDA absence either falls back loudly
    or aborts with an actionable message — never silently."""
    if requested == "cpu":
        return "cpu", False
    if probe.get("cuda_available"):
        return "cuda", False
    if allow_cpu_fallback:
        log.warning(
            "WARNING: device 'cuda' requested but CUDA is not available in the runner "
            "environment — falling back to cpu (allowed by this profile)."
        )
        return "cpu", True
    raise SystemExit(
        "device 'cuda' requested but CUDA is not available, and this profile does not "
        "allow CPU fallback. Re-run with --device cpu to opt in explicitly."
    )


# --------------------------------------------------------------------------
# bind stage
# --------------------------------------------------------------------------


def bind_command(
    *,
    python_exe: str,
    runs_dir: Path,
    bound_dir: Path,
    lean_dir: Path,
    report_path: Path,
    targets_dir: Path,
    lean_spec_dir: Path,
    tolerance_pct: float,
    skip_lake: bool,
) -> list[str]:
    cmd = [
        python_exe,
        str(_BINDER_SCRIPT),
        "--evidence-dir", str(runs_dir),
        "--targets-dir", str(targets_dir),
        "--out-dir", str(bound_dir),
        "--lean-dir", str(lean_dir),
        "--lean-spec", str(lean_spec_dir),
        "--report", str(report_path),
        "--tolerance-pct", str(tolerance_pct),
        "--emit-lean",
    ]
    if skip_lake:
        cmd.append("--skip-lake")
    return cmd


def run_bind(*, cmd: list[str], log_path: Path, runner: Runner | None = None) -> int:
    """Run the binder CLI; echo its log so verdicts are visible in the console."""
    run = runner if runner is not None else _subprocess_runner
    log.info("[bind] %s", " ".join(cmd[1:3] + ["..."]))
    try:
        returncode = run(cmd, log_path)
    except OSError as exc:
        log.error("[bind] could not launch binder: %s", exc)
        return -1
    for line in _log_tail(log_path, n_lines=200).splitlines():
        log.info("  %s", line)
    if returncode != 0:
        log.error("[bind] FAILED (exit %d) — see %s", returncode, log_path)
    return returncode


# --------------------------------------------------------------------------
# deviations (mirrors the Lean within/exceeds encoding)
# --------------------------------------------------------------------------


def compute_deviations(bound_dir: Path, tolerance_pct: float) -> dict:
    """Re-derive within/exceeds from the bound payloads: |value - ref| vs the
    explicit tolerance when the binder set one (floor rule), else
    tolerance_pct% of |ref|. Properties without a reference stay uncounted."""
    within = 0
    exceeds: list[dict] = []
    for path in sorted(bound_dir.glob("*.evidence.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        material = payload.get("material", "?")
        model_id = (payload.get("source") or {}).get("model_id", "?")
        for prop in payload.get("properties", []):
            reference = prop.get("reference_value")
            if reference is None:
                continue
            tolerance = prop.get("tolerance")
            if tolerance is None:
                tolerance = abs(reference) * tolerance_pct / 100.0
            error = abs(prop["value"] - reference)
            if error <= tolerance:
                within += 1
            else:
                exceeds.append(
                    {
                        "material": material,
                        "model_id": model_id,
                        "property": prop["name"],
                        "value": prop["value"],
                        "reference_value": reference,
                        "unit": prop.get("unit", ""),
                        "abs_error": error,
                        "tolerance": tolerance,
                        "ratio": (error / tolerance) if tolerance > 0 else float("inf"),
                    }
                )
    exceeds.sort(key=lambda item: item["ratio"], reverse=True)
    return {"within": within, "exceeds": exceeds}


# --------------------------------------------------------------------------
# packet assembly: manifest, REPORT.md, directory, tarball
# --------------------------------------------------------------------------


def build_manifest(
    *,
    profile_name: str,
    profile: ProfileConfig,
    config_path: str,
    invocation: list[str],
    device_requested: str,
    device_used: str,
    device_fallback: bool,
    probe: dict,
    outcomes: tuple[CellOutcome, ...],
    bind_returncode: int | None,
    binding_report: dict | None,
    started_at: str,
    finished_at: str,
    total_wall_time_seconds: float,
) -> dict:
    counts = {status: sum(1 for o in outcomes if o.status == status) for status in ("ok", "cached", "failed")}
    totals = (binding_report or {}).get("totals", {})
    return {
        "schema": MANIFEST_SCHEMA,
        "packet_name": profile.packet.name,
        "profile": profile_name,
        "profile_config": profile.model_dump(mode="json"),
        "config_path": config_path,
        "invocation": invocation,
        "started_at": started_at,
        "finished_at": finished_at,
        "total_wall_time_seconds": total_wall_time_seconds,
        "device": {
            "requested": device_requested,
            "used": device_used,
            "cpu_fallback": device_fallback,
        },
        "pipeline_python": platform.python_version(),
        "pipeline_platform": platform.platform(),
        "runner_env": probe,
        "cells": [
            {
                "label": outcome.cell.label,
                "material": outcome.cell.material,
                "structure": outcome.cell.structure,
                "model_id": outcome.cell.model,
                "properties": list(outcome.cell.properties),
                "status": outcome.status,
                "returncode": outcome.returncode,
                "wall_time_seconds": outcome.wall_time_seconds,
                "compute_wall_time_seconds": outcome.compute_wall_time_seconds,
                "log": outcome.log_name,
                "detail": outcome.detail,
            }
            for outcome in outcomes
        ],
        "sweep_counts": counts,
        "bind_returncode": bind_returncode,
        "binding_totals": totals,
        "lean_verdicts": {
            "verified": totals.get("lean_verified", 0),
            "failed": totals.get("lean_failed", 0),
            "unchecked": totals.get("lean_unchecked", 0),
        },
    }


def render_report_md(manifest: dict, deviations: dict) -> str:
    """Human-readable packet summary: coverage + notable deviations."""
    device = manifest["device"]
    runner_env = manifest.get("runner_env", {})
    counts = manifest["sweep_counts"]
    totals = manifest.get("binding_totals", {})
    lean = manifest["lean_verdicts"]

    lines = [
        f"# Y-matrix contribution packet — {manifest['packet_name']}",
        "",
        f"Generated {manifest['finished_at']} by `run_y_matrix_pipeline.py` "
        f"(profile `{manifest['profile']}`, total wall "
        f"{manifest['total_wall_time_seconds']:.1f}s).",
        "",
        "## Environment",
        "",
        f"- Device: requested `{device['requested']}`, used `{device['used']}`"
        + (" (CPU fallback)" if device["cpu_fallback"] else ""),
        f"- GPU: {runner_env.get('gpu_name') or 'n/a'}"
        f" | torch {runner_env.get('torch') or 'n/a'}"
        f" | CUDA {runner_env.get('cuda_version') or 'n/a'}",
        f"- Runner Python: {runner_env.get('python') or 'n/a'}"
        f" on {runner_env.get('platform') or 'n/a'}",
        "- Pinned packages: "
        + ", ".join(
            f"{name} {version}"
            for name, version in sorted((runner_env.get("packages") or {}).items())
            if version
        ),
        "",
        f"## Sweep — {len(manifest['cells'])} cells "
        f"(ok {counts['ok']}, cached {counts['cached']}, failed {counts['failed']})",
        "",
        "| cell | status | wall (s) | compute (s) |",
        "| --- | --- | --- | --- |",
    ]
    for cell in manifest["cells"]:
        wall = f"{cell['wall_time_seconds']:.1f}" if cell["wall_time_seconds"] is not None else "-"
        compute = (
            f"{cell['compute_wall_time_seconds']:.1f}"
            if cell["compute_wall_time_seconds"] is not None
            else "-"
        )
        status = cell["status"].upper() if cell["status"] == "failed" else cell["status"]
        lines.append(f"| {cell['label']} | {status} | {wall} | {compute} |")

    lines += [
        "",
        "## Reference binding",
        "",
        f"- Files bound: {totals.get('files', 0)} | properties bound: {totals.get('bound', 0)}, "
        f"unbound: {totals.get('unbound', 0)}, skipped: {totals.get('skipped', 0)}",
        "- Policy: DFT-PBE preferred, else experiment; unresolved references leave a "
        "property unbound (never guessed). Full detail: `binding_report.json`.",
        "",
        "## Lean verdicts",
        "",
        f"- verified: {lean['verified']} | failed: {lean['failed']} | "
        f"unchecked: {lean['unchecked']}",
        "- Vocabulary is deliberate: `verified` means `lake env lean` exited 0; "
        "`unchecked` modules were emitted but not type-checked and are never "
        "reported as verified.",
        "",
        f"## Notable deviations — {len(deviations['exceeds'])} exceed tolerance "
        f"({deviations['within']} within)",
        "",
    ]
    if deviations["exceeds"]:
        lines += [
            "| material | model | property | value | reference | unit | \\|err\\| | tol |",
            "| --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
        for item in deviations["exceeds"]:
            lines.append(
                f"| {item['material']} | {item['model_id']} | {item['property']} | "
                f"{item['value']:.4g} | {item['reference_value']:.4g} | {item['unit']} | "
                f"{item['abs_error']:.4g} | {item['tolerance']:.4g} |"
            )
        lines += [
            "",
            "Deviations are encoded in the Lean modules as `calc_exceeds_tol_*` "
            "theorems — recorded facts, not hidden failures.",
        ]
    else:
        lines.append("All bound properties are within tolerance.")
    lines += [
        "",
        "## Packet contents",
        "",
        "- `evidence/` — per-cell statics results (`*.json`) and calc-evidence "
        "payloads (`*.evidence.json`), references intentionally absent",
        "- `bound/` — the same evidence with reference targets bound "
        "(provenance hash unchanged)",
        "- `lean/` — machine-generated Lean modules, one per cell with bound "
        "properties",
        "- `binding_report.json` — per-property binding methods and Lean verdicts",
        "- `manifest.json` — config, environment pins, timestamps, per-cell wall times",
        "",
    ]
    return "\n".join(lines)


def assemble_packet(
    *,
    packet_dir: Path,
    tarball_path: Path,
    runs_dir: Path,
    bound_dir: Path,
    lean_dir: Path,
    binding_report_path: Path,
    manifest: dict,
    report_md: str,
) -> list[str]:
    """Build the packet directory from scratch and tar it; returns the member list."""
    if packet_dir.exists():
        shutil.rmtree(packet_dir)
    (packet_dir / "evidence").mkdir(parents=True)
    (packet_dir / "bound").mkdir()
    (packet_dir / "lean").mkdir()

    for path in sorted(runs_dir.glob("*.json")):
        shutil.copy2(path, packet_dir / "evidence" / path.name)
    if bound_dir.is_dir():
        for path in sorted(bound_dir.glob("*.json")):
            shutil.copy2(path, packet_dir / "bound" / path.name)
    if lean_dir.is_dir():
        for path in sorted(lean_dir.glob("*.lean")):
            shutil.copy2(path, packet_dir / "lean" / path.name)
    if binding_report_path.is_file():
        shutil.copy2(binding_report_path, packet_dir / "binding_report.json")

    (packet_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    (packet_dir / "REPORT.md").write_text(report_md, encoding="utf-8")

    tarball_path.parent.mkdir(parents=True, exist_ok=True)
    if tarball_path.exists():
        tarball_path.unlink()
    with tarfile.open(tarball_path, "w:gz") as tar:
        tar.add(packet_dir, arcname=packet_dir.name)

    members = sorted(
        str(path.relative_to(packet_dir)).replace("\\", "/")
        for path in packet_dir.rglob("*")
        if path.is_file()
    )
    return members


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python python/scripts/run_y_matrix_pipeline.py",
        description=__doc__.splitlines()[0],
    )
    parser.add_argument("--config", required=True, help="Demo config YAML path")
    parser.add_argument("--profile", required=True, help="Profile name inside the config")
    parser.add_argument(
        "--device", choices=("cuda", "cpu"), default=None,
        help="Override the profile's device",
    )
    parser.add_argument(
        "--skip-lake", action="store_true",
        help="Emit Lean modules without type-checking (reported as 'unchecked')",
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Re-run cells even when their outputs already exist",
    )
    parser.add_argument(
        "--python", default=sys.executable,
        help="Interpreter for the sweep/bind subprocesses (default: this one)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        config = load_demo_config(args.config)
        profile = select_profile(config, args.profile)
    except ConfigError as exc:
        log.error("error: %s", exc)
        return 2

    cells = plan_cells(profile)
    output_dir = resolve_path(profile.output_dir)
    runs_dir = output_dir / "runs"
    logs_dir = output_dir / "logs"
    bound_dir = output_dir / "bound"
    lean_dir = output_dir / "lean"
    binding_report_path = output_dir / "binding_report.json"
    packet_dir = output_dir / "packet" / profile.packet.name
    tarball_path = output_dir / f"{profile.packet.name}.tar.gz"

    started_at = datetime.now(timezone.utc).isoformat()
    t_start = time.perf_counter()

    log.info("profile %s: %d materials x %d models = %d cells -> %s",
             args.profile, len(profile.materials), len(profile.models), len(cells), output_dir)
    log.info("probing runner environment (%s) ...", args.python)
    probe = probe_runner_env(args.python)
    if "error" in probe:
        log.error("error: %s", probe["error"])
        return 2
    device_requested = args.device or profile.device
    try:
        device_used, device_fallback = resolve_device(
            device_requested, probe, profile.allow_cpu_fallback
        )
    except SystemExit as exc:
        log.error("error: %s", exc)
        return 2
    log.info(
        "runner: python %s | torch %s | CUDA %s | GPU %s -> device %s",
        probe.get("python"), probe.get("torch"), probe.get("cuda_version"),
        probe.get("gpu_name") or "n/a", device_used,
    )

    # ---- stage a: sweep -------------------------------------------------
    outcomes = run_sweep(
        cells,
        runs_dir=runs_dir,
        logs_dir=logs_dir,
        device=device_used,
        python_exe=args.python,
        run_label=f"{args.profile}",
        force=args.force,
    )
    failed = [o for o in outcomes if o.status == "failed"]
    if failed:
        log.error("sweep: %d/%d cells FAILED: %s",
                  len(failed), len(cells), ", ".join(o.cell.label for o in failed))

    # ---- stage b: bind + Lean + lake ------------------------------------
    have_evidence = any(runs_dir.glob("*.evidence.json"))
    if have_evidence:
        cmd = bind_command(
            python_exe=args.python,
            runs_dir=runs_dir,
            bound_dir=bound_dir,
            lean_dir=lean_dir,
            report_path=binding_report_path,
            targets_dir=resolve_path(profile.targets_dir),
            lean_spec_dir=resolve_path(profile.lean_spec_dir),
            tolerance_pct=profile.packet.tolerance_pct,
            skip_lake=args.skip_lake,
        )
        bind_returncode = run_bind(cmd=cmd, log_path=logs_dir / "bind.log")
    else:
        log.error("[bind] skipped: no evidence files were produced by the sweep")
        bind_returncode = None

    binding_report: dict | None = None
    if binding_report_path.is_file():
        try:
            binding_report = json.loads(binding_report_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            log.error("[bind] report unreadable: %s", exc)

    # ---- stage c: contribution packet ------------------------------------
    deviations = (
        compute_deviations(bound_dir, profile.packet.tolerance_pct)
        if bound_dir.is_dir()
        else {"within": 0, "exceeds": []}
    )
    finished_at = datetime.now(timezone.utc).isoformat()
    total_wall = time.perf_counter() - t_start
    manifest = build_manifest(
        profile_name=args.profile,
        profile=profile,
        config_path=str(args.config),
        invocation=list(argv) if argv is not None else sys.argv[1:],
        device_requested=device_requested,
        device_used=device_used,
        device_fallback=device_fallback,
        probe=probe,
        outcomes=outcomes,
        bind_returncode=bind_returncode,
        binding_report=binding_report,
        started_at=started_at,
        finished_at=finished_at,
        total_wall_time_seconds=total_wall,
    )
    report_md = render_report_md(manifest, deviations)
    members = assemble_packet(
        packet_dir=packet_dir,
        tarball_path=tarball_path,
        runs_dir=runs_dir,
        bound_dir=bound_dir,
        lean_dir=lean_dir,
        binding_report_path=binding_report_path,
        manifest=manifest,
        report_md=report_md,
    )

    log.info("")
    log.info("packet: %s (%d files)", packet_dir, len(members))
    log.info("tarball: %s (%.1f KiB)", tarball_path, tarball_path.stat().st_size / 1024)
    lean = manifest["lean_verdicts"]
    log.info(
        "summary: cells ok=%d cached=%d failed=%d | bound=%s unbound=%s | "
        "lean verified=%d failed=%d unchecked=%d | %.1fs total",
        manifest["sweep_counts"]["ok"], manifest["sweep_counts"]["cached"],
        manifest["sweep_counts"]["failed"],
        manifest["binding_totals"].get("bound", 0), manifest["binding_totals"].get("unbound", 0),
        lean["verified"], lean["failed"], lean["unchecked"], total_wall,
    )

    if failed or bind_returncode not in (0,):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
