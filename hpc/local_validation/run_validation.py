#!/usr/bin/env python3
"""Local workstation validation driver for the MLIP cell runner.

Runs the offline cell-runner lane (gcp/mlip-cell-runner/mlip_cell_runner.py
run-cell) for every requested (row, mlip, device) combination on the local
box, times each leg with a wall clock, and aggregates the resulting
cell_result.json artifacts into a meeting-ready report.json + report.md.

Stdlib-only by design: the heavy dependencies (torch, ase, mace-torch, ...)
live in the subprocesses that execute the runner, never in this driver.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import platform
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
RUNNER_PATH = REPO_ROOT / "gcp" / "mlip-cell-runner" / "mlip_cell_runner.py"
MOCK_SHIM_PATH = Path(__file__).resolve().parent / "mock_backend_shim.py"
DEFAULT_MANIFEST = (
    REPO_ROOT / "gcp" / "mlip-cell-runner" / "fixtures" / "ni_fcc_eam_distill_support_v1.json"
)
DEFAULT_ROWS = ("energy_volume", "forces", "elastic_constants")
DEFAULT_MLIPS = ("mace-mp-0",)
REPORT_SCHEMA = "lupine.mlip.local_validation_report.v1"
CUDA_PROBE_TIMEOUT_S = 120
CELL_TIMEOUT_S = 3600


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the offline MLIP cell runner across (row, mlip, device) legs "
        "on this workstation and aggregate a local validation report."
    )
    parser.add_argument(
        "--mlip",
        action="append",
        default=None,
        help=f"MLIP backend id (repeatable; default: {', '.join(DEFAULT_MLIPS)}). "
        "Any id accepted by mlip_cell_runner.py works; ids starting with 'mock' "
        "use the deterministic mock backend shim (no MLIP install needed).",
    )
    parser.add_argument(
        "--row",
        action="append",
        default=None,
        help=f"Benchmark row id (repeatable; default: {', '.join(DEFAULT_ROWS)}).",
    )
    parser.add_argument(
        "--device",
        action="append",
        choices=("cpu", "cuda"),
        default=None,
        help="Device leg (repeatable). Default auto: cpu, plus cuda when "
        "torch.cuda.is_available() in this interpreter.",
    )
    parser.add_argument(
        "--manifest",
        default=str(DEFAULT_MANIFEST),
        help="Local fixture manifest path passed to the runner (default: %(default)s).",
    )
    parser.add_argument(
        "--out",
        default=None,
        help="Output directory for artifacts + report.json/report.md "
        "(default: tmp/local_validation_<run-id> under the repo root).",
    )
    parser.add_argument("--run-id", required=True, help="Run id stamped into every cell and report.")
    return parser.parse_args(argv)


def probe_cuda_available() -> bool:
    """Ask a subprocess whether torch sees a CUDA device (driver stays stdlib-only)."""
    try:
        proc = subprocess.run(
            [sys.executable, "-c", "import torch; print(int(torch.cuda.is_available()))"],
            capture_output=True,
            text=True,
            timeout=CUDA_PROBE_TIMEOUT_S,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return proc.returncode == 0 and proc.stdout.strip() == "1"


def resolve_devices(requested: list[str] | None) -> list[str]:
    if requested:
        deduped: list[str] = []
        for device in requested:
            if device not in deduped:
                deduped.append(device)
        return deduped
    devices = ["cpu"]
    if probe_cuda_available():
        devices.append("cuda")
    return devices


def runner_command(mlip_id: str) -> list[str]:
    script = MOCK_SHIM_PATH if mlip_id.startswith("mock") else RUNNER_PATH
    return [sys.executable, str(script)]


def leg_environment(device: str) -> dict[str, str]:
    env = dict(os.environ)
    if device == "cpu":
        # The runner auto-selects its device; hiding the GPUs forces the CPU path.
        env["CUDA_VISIBLE_DEVICES"] = ""
    return env


def extract_headline_metrics(artifact: dict[str, Any]) -> dict[str, Any]:
    accuracy = artifact.get("accuracy") or {}
    speed = artifact.get("speed") or {}
    execution = artifact.get("execution") or {}
    predictions = artifact.get("predictions")
    return {
        "accuracy_score": accuracy.get("score"),
        "primary_metric": accuracy.get("primary_metric"),
        "error": accuracy.get("error"),
        "error_unit": accuracy.get("error_unit"),
        "score_tolerance": accuracy.get("score_tolerance"),
        "speed_structures_per_second": speed.get("score"),
        "n_structures": len(predictions) if isinstance(predictions, list) else None,
        "model_load_seconds": execution.get("model_load_seconds"),
        "warm_inference_seconds": execution.get("warm_inference_seconds"),
    }


def run_leg(
    *,
    run_id: str,
    row_id: str,
    mlip_id: str,
    device: str,
    manifest_path: Path,
    out_dir: Path,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    cell_id = f"{run_id}:baseline:{row_id}:{mlip_id}:{device}"
    artifact_dir = out_dir / "cells" / row_id / mlip_id / device
    artifact_dir.mkdir(parents=True, exist_ok=True)
    command = [
        *runner_command(mlip_id),
        "run-cell",
        "--run-id", run_id,
        "--cell-id", cell_id,
        "--row-id", row_id,
        "--mlip-id", mlip_id,
        "--manifest-url", str(manifest_path),
        "--artifact-prefix", str(artifact_dir),
        # Offline flags only: local manifest, local artifacts, no --beat-emit-url.
        # Checkpoints off so every leg computes fresh predictions (honest timing).
        "--checkpoint-mode", "off",
    ]
    print(f"[run_validation] {cell_id} ...", file=sys.stderr, flush=True)
    started = time.monotonic()
    try:
        proc = subprocess.run(
            command,
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
            env=leg_environment(device),
            timeout=CELL_TIMEOUT_S,
        )
        exit_code: int | None = proc.returncode
        stdout, stderr = proc.stdout, proc.stderr
    except subprocess.TimeoutExpired as exc:
        exit_code = None
        stdout = (exc.stdout or b"").decode("utf-8", "replace") if exc.stdout else ""
        stderr = f"timeout after {CELL_TIMEOUT_S}s"
    wall_seconds = time.monotonic() - started
    (artifact_dir / "runner_stdout.json").write_text(stdout, encoding="utf-8")
    (artifact_dir / "runner_stderr.log").write_text(stderr, encoding="utf-8")

    artifact_path = artifact_dir / "cell_result.json"
    artifact: dict[str, Any] | None = None
    if artifact_path.exists():
        try:
            artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            artifact = None
    ok = exit_code == 0 and isinstance(artifact, dict)
    versions = (artifact or {}).get("versions") or {}
    record: dict[str, Any] = {
        "cell_id": cell_id,
        "row_id": row_id,
        "mlip_id": mlip_id,
        "device": device,
        "ok": ok,
        "exit_code": exit_code,
        "wall_seconds": round(wall_seconds, 3),
        "metrics": extract_headline_metrics(artifact) if isinstance(artifact, dict) else None,
        "cuda_available": versions.get("cuda_available"),
        "cuda_device": versions.get("cuda_device"),
        "artifact_path": str(artifact_path) if artifact_path.exists() else None,
    }
    if device == "cuda" and ok and versions.get("cuda_available") is False:
        record["device_mismatch"] = True
    if not ok:
        tail = "\n".join(stderr.strip().splitlines()[-8:])
        record["error"] = tail or f"runner exited with code {exit_code}"
    status = "ok" if ok else "FAILED"
    print(
        f"[run_validation] {cell_id} {status} in {wall_seconds:.1f}s",
        file=sys.stderr,
        flush=True,
    )
    return record, artifact


def compute_speedups(cells: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_leg: dict[tuple[str, str], dict[str, dict[str, Any]]] = {}
    for cell in cells:
        if cell["ok"]:
            by_leg.setdefault((cell["row_id"], cell["mlip_id"]), {})[cell["device"]] = cell
    speedups: list[dict[str, Any]] = []
    for (row_id, mlip_id), legs in sorted(by_leg.items()):
        cpu, cuda = legs.get("cpu"), legs.get("cuda")
        if not cpu or not cuda:
            continue
        entry: dict[str, Any] = {
            "row_id": row_id,
            "mlip_id": mlip_id,
            "cpu_wall_seconds": cpu["wall_seconds"],
            "cuda_wall_seconds": cuda["wall_seconds"],
            "wall_speedup": (
                round(cpu["wall_seconds"] / cuda["wall_seconds"], 2)
                if cuda["wall_seconds"] > 0
                else None
            ),
        }
        cpu_warm = (cpu.get("metrics") or {}).get("warm_inference_seconds")
        cuda_warm = (cuda.get("metrics") or {}).get("warm_inference_seconds")
        if isinstance(cpu_warm, (int, float)) and isinstance(cuda_warm, (int, float)) and cuda_warm > 0:
            entry["warm_inference_speedup"] = round(cpu_warm / cuda_warm, 2)
        speedups.append(entry)
    return speedups


def host_info(artifacts: list[dict[str, Any] | None]) -> dict[str, Any]:
    info: dict[str, Any] = {
        "hostname": socket.gethostname(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "python": platform.python_version(),
    }
    runtime_keys = (
        "python",
        "numpy",
        "ase",
        "torch",
        "mace-torch",
        "chgnet",
        "cuda_available",
        "cuda_device",
    )
    for artifact in artifacts:
        versions = (artifact or {}).get("versions") or {}
        if versions:
            info["runner_versions"] = {key: versions.get(key) for key in runtime_keys}
            if versions.get("cuda_device"):
                info["cuda_device"] = versions["cuda_device"]
            break
    return info


def _fmt(value: Any, digits: int = 4) -> str:
    if isinstance(value, bool) or value is None:
        return "-" if value is None else str(value)
    if isinstance(value, (int, float)):
        return f"{value:.{digits}g}"
    return str(value)


def build_notes(report: dict[str, Any], devices: list[str]) -> list[str]:
    cells = report["cells"]
    notes = [
        "Wall times are single-sample (one leg per combination, no repeats); "
        "treat small differences as noise.",
        "wall_seconds includes Python startup, manifest load, and model load; "
        "warm_inference_seconds isolates the inference loop.",
        "Checkpoints were disabled (--checkpoint-mode off) so every leg computed "
        "fresh predictions; no cached results inflate the speedups.",
        f"Fixture: {report['manifest']} — a distill *support* fixture, not the sealed "
        "evaluation fixture; scores are row-native 0-1 scores against its references.",
    ]
    failed = [cell for cell in cells if not cell["ok"]]
    if failed:
        ids = ", ".join(cell["cell_id"] for cell in failed)
        notes.append(f"FAILED legs (see runner_stderr.log next to each artifact): {ids}.")
    mismatched = [cell for cell in cells if cell.get("device_mismatch")]
    if mismatched:
        ids = ", ".join(cell["cell_id"] for cell in mismatched)
        notes.append(
            "CUDA legs where the runner reported cuda_available=false (they actually "
            f"ran on CPU — do not quote them as GPU numbers): {ids}."
        )
    if "cuda" not in devices:
        notes.append("No cuda leg was run on this host; cpu_vs_gpu speedups are unavailable.")
    mocked = sorted({cell["mlip_id"] for cell in cells if cell["mlip_id"].startswith("mock")})
    if mocked:
        notes.append(
            f"Mock backends ({', '.join(mocked)}) return constant energies and zero "
            "forces/stress; their metrics validate plumbing, not physics."
        )
    return notes


def render_markdown(report: dict[str, Any], devices: list[str]) -> str:
    lines = [
        "# Local MLIP validation report",
        "",
        f"- Run id: `{report['run_id']}`",
        f"- Generated: {report['created_at']}",
        f"- Host: {report['host'].get('hostname')} ({report['host'].get('platform')})",
    ]
    if report["host"].get("cuda_device"):
        lines.append(f"- GPU: {report['host']['cuda_device']}")
    runner_versions = report["host"].get("runner_versions") or {}
    if runner_versions:
        version_bits = ", ".join(
            f"{key} {value}" for key, value in runner_versions.items() if value is not None
        )
        lines.append(f"- Runner stack: {version_bits}")
    lines += [
        f"- Manifest: `{report['manifest']}`",
        "",
        "## Results",
        "",
        "| row | mlip | device | ok | metric | error | unit | score | n | wall s | warm s |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for cell in report["cells"]:
        metrics = cell.get("metrics") or {}
        lines.append(
            "| {row} | {mlip} | {device} | {ok} | {metric} | {error} | {unit} | {score} "
            "| {n} | {wall} | {warm} |".format(
                row=cell["row_id"],
                mlip=cell["mlip_id"],
                device=cell["device"],
                ok="yes" if cell["ok"] else "**no**",
                metric=metrics.get("primary_metric") or "-",
                error=_fmt(metrics.get("error")),
                unit=metrics.get("error_unit") or "-",
                score=_fmt(metrics.get("accuracy_score"), 3),
                n=_fmt(metrics.get("n_structures")),
                wall=_fmt(cell.get("wall_seconds"), 4),
                warm=_fmt(metrics.get("warm_inference_seconds"), 4),
            )
        )
    lines += ["", "## CPU vs GPU speedup", ""]
    if report["speedups"]:
        lines += [
            "| row | mlip | cpu wall s | cuda wall s | wall speedup | warm speedup |",
            "|---|---|---|---|---|---|",
        ]
        for entry in report["speedups"]:
            lines.append(
                "| {row} | {mlip} | {cpu} | {cuda} | {wall}x | {warm} |".format(
                    row=entry["row_id"],
                    mlip=entry["mlip_id"],
                    cpu=_fmt(entry["cpu_wall_seconds"], 4),
                    cuda=_fmt(entry["cuda_wall_seconds"], 4),
                    wall=_fmt(entry.get("wall_speedup"), 3),
                    warm=(
                        f"{_fmt(entry['warm_inference_speedup'], 3)}x"
                        if entry.get("warm_inference_speedup") is not None
                        else "-"
                    ),
                )
            )
    else:
        lines.append("No (row, mlip) had both a successful cpu leg and a successful cuda leg.")
    lines += ["", "## Notes", ""]
    lines += [f"- {note}" for note in build_notes(report, devices)]
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    rows = list(args.row) if args.row else list(DEFAULT_ROWS)
    mlips = list(args.mlip) if args.mlip else list(DEFAULT_MLIPS)
    devices = resolve_devices(args.device)
    manifest_path = Path(args.manifest).resolve()
    if not manifest_path.exists():
        print(f"[run_validation] manifest not found: {manifest_path}", file=sys.stderr)
        return 2
    out_dir = (
        Path(args.out).resolve()
        if args.out
        else REPO_ROOT / "tmp" / f"local_validation_{args.run_id}"
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    print(
        f"[run_validation] run_id={args.run_id} rows={rows} mlips={mlips} "
        f"devices={devices} out={out_dir}",
        file=sys.stderr,
    )

    cells: list[dict[str, Any]] = []
    artifacts: list[dict[str, Any] | None] = []
    for row_id in rows:
        for mlip_id in mlips:
            for device in devices:
                record, artifact = run_leg(
                    run_id=args.run_id,
                    row_id=row_id,
                    mlip_id=mlip_id,
                    device=device,
                    manifest_path=manifest_path,
                    out_dir=out_dir,
                )
                cells.append(record)
                artifacts.append(artifact)

    report = {
        "schema": REPORT_SCHEMA,
        "run_id": args.run_id,
        "created_at": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
        "manifest": str(manifest_path),
        "rows": rows,
        "mlips": mlips,
        "devices": devices,
        "host": host_info(artifacts),
        "cells": cells,
        "speedups": compute_speedups(cells),
        "summary": {
            "cells_total": len(cells),
            "cells_ok": sum(1 for cell in cells if cell["ok"]),
            "cells_failed": sum(1 for cell in cells if not cell["ok"]),
        },
    }
    report_json = out_dir / "report.json"
    report_json.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report_md = out_dir / "report.md"
    report_md.write_text(render_markdown(report, devices), encoding="utf-8")
    print(f"[run_validation] wrote {report_json}", file=sys.stderr)
    print(f"[run_validation] wrote {report_md}", file=sys.stderr)
    return 0 if report["summary"]["cells_failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
