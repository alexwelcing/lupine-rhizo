"""Bind compiled reference targets onto Y-matrix sweep evidence, then optionally
emit + type-check Lean modules.

For each ``*.evidence.json`` (``lupine.mlip.calc_evidence.v1``) the binder:

1. resolves the crystal structure (sibling statics-run JSON, else filename);
2. binds reference targets from ``data/y_matrix_targets/*.json`` under the
   registered policy (DFT-PBE preferred, else experiment; unresolved leaves
   the property unbound) — see ``lupine_distill.binding``;
3. writes the bound payload to ``<out-dir>/<same-name>`` with provenance
   (``inputs_sha256``) byte-identical to the input;
4. with ``--emit-lean``: emits one Lean module per payload that has >= 1
   bound property to ``<lean-dir>/<Material>_<model>.lean`` (one payload per
   module; material + model uniquely names a sweep cell) and, when ``lake``
   is on PATH, type-checks each module via ``lake env lean <abs path>`` from
   the lean-spec workspace. Module vocabulary in the report: ``verified``
   (lake exit 0), ``failed`` (nonzero), ``unchecked`` (lake unavailable,
   ``--skip-lake``, or timeout) — an emitted-but-unchecked module is NEVER
   reported as verified.

A ``binding_report.json`` (schema ``lupine.y_matrix_binding_report.v1``) is
written next to the bound payloads: per file the bound/unbound/skipped counts,
the method used per property, and the Lean verdicts.

Default invocation (from the repo root) binds the whole sweep:

    python python/scripts/bind_y_matrix_references.py --emit-lean
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

_HERE = Path(__file__).resolve()
_REPO_ROOT = _HERE.parents[2]
for _p in (str(_HERE.parents[1]), str(_REPO_ROOT)):  # python/ ; repo root
    if _p not in sys.path:
        sys.path.insert(0, _p)

from lupine_distill.binding import (  # noqa: E402
    BindingConfig,
    UnmappedPropertyError,
    bind_evidence,
    load_targets,
    resolve_structure,
)
from lupine_distill.lammps_ingest import emit_lean_module  # noqa: E402
from lupine_distill.schemas import CALC_EVIDENCE_SCHEMA, CalcEvidence  # noqa: E402

REPORT_SCHEMA = "lupine.y_matrix_binding_report.v1"
LAKE_TIMEOUT_SECONDS = 600.0


def _safe(s: str) -> str:
    return "".join(c if c.isalnum() else "_" for c in s).strip("_")


def _load_calc_evidence(path: Path) -> CalcEvidence:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read evidence {path}: {exc}") from exc
    if not (isinstance(payload, dict) and payload.get("schema") == CALC_EVIDENCE_SCHEMA):
        raise ValueError(
            f"{path.name}: expected schema '{CALC_EVIDENCE_SCHEMA}', "
            f"got {payload.get('schema')!r}" if isinstance(payload, dict)
            else f"{path.name}: not a JSON object"
        )
    return CalcEvidence.model_validate(payload)


def _check_lean_module(lean_path: Path, lean_spec_dir: Path) -> tuple[str, str | None]:
    """Type-check one module via ``lake env lean``; never claims more than it ran.

    Returns ``(status, detail)`` with status in verified / failed / unchecked.
    """

    lake = shutil.which("lake")
    if lake is None:
        return "unchecked", "lake not found on PATH"
    if not lean_spec_dir.is_dir():
        return "unchecked", f"lean-spec workspace not found at {lean_spec_dir}"
    try:
        proc = subprocess.run(
            [lake, "env", "lean", str(lean_path.resolve())],
            cwd=str(lean_spec_dir),
            capture_output=True,
            text=True,
            timeout=LAKE_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        return "unchecked", f"lake env lean timed out after {LAKE_TIMEOUT_SECONDS:g}s"
    except OSError as exc:
        return "unchecked", f"lake could not be executed: {exc}"
    if proc.returncode == 0:
        return "verified", None
    detail = (proc.stderr or proc.stdout or "").strip()
    return "failed", detail[:2000] or f"lake env lean exited {proc.returncode}"


def _discover_evidence(args: argparse.Namespace) -> list[Path]:
    if args.evidence:
        return [Path(p) for p in args.evidence]
    evidence_dir = Path(args.evidence_dir)
    return sorted(evidence_dir.glob("*.evidence.json"))


def _bind_one(
    path: Path,
    targets,
    config: BindingConfig,
    out_dir: Path,
) -> tuple[dict, object]:
    """Bind one evidence file, write the bound payload, return (report entry, result)."""

    evidence = _load_calc_evidence(path)
    structure = resolve_structure(path, material=evidence.material)
    result = bind_evidence(evidence, structure=structure, targets=targets, config=config)

    out_path = out_dir / path.name
    out_path.write_text(
        json.dumps(result.evidence.model_dump(mode="json", by_alias=True), indent=2) + "\n",
        encoding="utf-8",
    )
    entry = {
        "evidence": path.name,
        "material": evidence.material,
        "structure": structure,
        "model_id": evidence.source.model_id,
        "counts": result.counts,
        "properties": [record.to_json_dict() for record in result.records],
        "output": str(out_path),
        "lean_module": None,
        "lean_status": None,
        "lean_detail": None if structure is not None else "structure unresolved; nothing bound",
    }
    return entry, result


def _emit_and_check_lean(
    entry: dict,
    result,
    lean_dir: Path,
    lean_spec_dir: Path,
    skip_lake: bool,
    tolerance_pct: float,
    emitted_this_run: set[str],
) -> None:
    if result.counts["bound"] == 0:
        entry["lean_status"] = "not_emitted"
        entry["lean_detail"] = "no bound properties; nothing to prove"
        return
    structure = entry.get("structure") or "unknown"
    module_name = (
        f"{_safe(entry['material'])}_{_safe(structure)}_{_safe(entry['model_id'])}.lean"
    )
    module_path = lean_dir / module_name
    # Overwriting a file left by a previous run is regeneration; only two
    # payloads mapping to one name within THIS run is a real collision.
    if str(module_path) in emitted_this_run:
        raise ValueError(
            f"Lean module name collision within this run: {module_path} "
            f"(material+structure+model no longer unique)"
        )
    emitted_this_run.add(str(module_path))
    emit_lean_module([result.evidence], module_path, tolerance_pct=tolerance_pct)
    entry["lean_module"] = str(module_path)
    if skip_lake:
        entry["lean_status"], entry["lean_detail"] = "unchecked", "--skip-lake requested"
    else:
        entry["lean_status"], entry["lean_detail"] = _check_lean_module(
            module_path, lean_spec_dir
        )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python python/scripts/bind_y_matrix_references.py",
        description=(
            "Bind compiled reference targets (lupine.y_matrix_targets.v1) onto sweep "
            "evidence (lupine.mlip.calc_evidence.v1); optionally emit and lake-check "
            "Lean modules. Registered policy: DFT-PBE preferred, else experiment; "
            "unresolved references leave properties unbound."
        ),
    )
    parser.add_argument(
        "evidence", nargs="*",
        help="evidence JSON file(s); default: all *.evidence.json in --evidence-dir",
    )
    parser.add_argument(
        "--evidence-dir", default=str(_REPO_ROOT / "data" / "y_matrix_runs"),
        help="directory scanned for *.evidence.json when no files are given",
    )
    parser.add_argument(
        "--targets-dir", default=str(_REPO_ROOT / "data" / "y_matrix_targets"),
        help="directory of lupine.y_matrix_targets.v1 files",
    )
    parser.add_argument(
        "--out-dir", default=None,
        help="bound payload output dir (default: <evidence-dir>/bound)",
    )
    parser.add_argument(
        "--report", default=None,
        help="binding report path (default: <out-dir>/binding_report.json)",
    )
    parser.add_argument(
        "--strict", action="store_true",
        help="fail fast on evidence property names missing from the mapping table",
    )
    parser.add_argument(
        "--tolerance-pct", type=float, default=5.0,
        help="percentage tolerance assumed by the near-zero floor rule and passed to "
        "Lean emission (default: 5.0)",
    )
    parser.add_argument(
        "--emit-lean", action="store_true",
        help="emit one Lean module per payload with >= 1 bound property",
    )
    parser.add_argument(
        "--lean-dir", default=None,
        help="Lean module output dir (default: <evidence-dir>/lean)",
    )
    parser.add_argument(
        "--lean-spec", default=str(_REPO_ROOT / "lean-spec"),
        help="lean-spec workspace used for 'lake env lean' type checks",
    )
    parser.add_argument(
        "--skip-lake", action="store_true",
        help="emit Lean modules without type-checking (reported as 'unchecked')",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        evidence_paths = _discover_evidence(args)
        if not evidence_paths:
            raise ValueError(f"no *.evidence.json files found in {args.evidence_dir}")
        targets = load_targets(args.targets_dir)
        config = BindingConfig(tolerance_pct=args.tolerance_pct, strict=args.strict)

        out_dir = Path(args.out_dir) if args.out_dir else Path(args.evidence_dir) / "bound"
        out_dir.mkdir(parents=True, exist_ok=True)
        lean_dir = Path(args.lean_dir) if args.lean_dir else Path(args.evidence_dir) / "lean"
        if args.emit_lean:
            lean_dir.mkdir(parents=True, exist_ok=True)

        files = []
        totals = {
            "files": 0, "bound": 0, "unbound": 0, "skipped": 0,
            "lean_verified": 0, "lean_failed": 0, "lean_unchecked": 0,
        }
        emitted_this_run: set[str] = set()
        for path in evidence_paths:
            entry, result = _bind_one(path, targets, config, out_dir)
            if args.emit_lean:
                _emit_and_check_lean(
                    entry, result, lean_dir, Path(args.lean_spec),
                    args.skip_lake, args.tolerance_pct, emitted_this_run,
                )
            files.append(entry)
            totals["files"] += 1
            for key in ("bound", "unbound", "skipped"):
                totals[key] += entry["counts"][key]
            if entry["lean_status"] in ("verified", "failed", "unchecked"):
                totals[f"lean_{entry['lean_status']}"] += 1
            lean_note = f" lean={entry['lean_status']}" if entry["lean_status"] else ""
            print(
                f"{path.name}: bound={entry['counts']['bound']} "
                f"unbound={entry['counts']['unbound']} "
                f"skipped={entry['counts']['skipped']}{lean_note}"
            )

        report = {
            "schema": REPORT_SCHEMA,
            "targets_dir": str(args.targets_dir),
            "out_dir": str(out_dir),
            "config": {
                "tolerance_pct": config.tolerance_pct,
                "strict": config.strict,
                "method_preference": list(config.method_preference),
                "tolerance_floors": dict(config.tolerance_floors),
            },
            "files": files,
            "totals": totals,
        }
        report_path = Path(args.report) if args.report else out_dir / "binding_report.json"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(
            f"report: {report_path} (files={totals['files']} bound={totals['bound']} "
            f"unbound={totals['unbound']} skipped={totals['skipped']})"
        )
        return 0
    except (UnmappedPropertyError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
