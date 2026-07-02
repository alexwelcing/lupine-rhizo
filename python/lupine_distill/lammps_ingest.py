"""LAMMPS log ingestion: standard log files -> versioned evidence -> Lean theorems.

Entry point for external LAMMPS users: they bring the log files their campaigns
already produce (the ``examples/ELASTIC`` driver output, plain thermo logs) and
this module turns them into schema-validated ``lupine.mlip.lammps_evidence.v1``
payloads and machine-checked Lean 4 modules in the exact style authored by
``tools/mlip_distill_atlas.py`` (the production path into ``lean-spec/``).

Three layers, usable independently:

  1. ``parse_elastic_log`` / ``parse_thermo_log`` — tolerant text parsers.
  2. ``build_evidence`` — assemble a :class:`LammpsEvidence` payload; provenance
     is the sha256 of the log text, and ``parsed_at`` is recorded only when the
     caller supplies it (this module never reads the clock).
  3. ``emit_lean_module`` — decidable Nat-inequality theorems (abs error x1000
     vs reference) written wherever the caller says. Demos write under
     ``hpc/examples/generated/`` — never into ``lean-spec/`` directly.

CLI (``python3 -m lupine_distill.lammps_ingest --help``):

    python3 -m lupine_distill.lammps_ingest parse log.lammps \\
        --material Ni --potential Ni_u3.eam \\
        --ref C11=246.5 --ref C12=147.3 --ref C44=124.7 \\
        --ref-source "Simmons & Wang 1971" -o evidence.json
    python3 -m lupine_distill.lammps_ingest lean evidence.json -o Module.lean
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import sys
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime

from .schemas import (
    LammpsEvidence,
    LammpsPropertyValue,
    LammpsProvenance,
    LammpsSource,
    LammpsTrajectorySummary,
)

_FLOAT = r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?"

# "Elastic Constant C11all = 1143.9 GPa" — the examples/ELASTIC driver's final block.
_RE_ELASTIC_CONSTANT = re.compile(
    rf"^\s*Elastic Constant (C\d\d)all\s*=\s*({_FLOAT})\s*(\S+)", re.MULTILINE
)
_RE_BULK = re.compile(rf"^\s*Bulk Modulus\s*=\s*({_FLOAT})\s*(\S+)", re.MULTILINE)
_RE_SHEAR = re.compile(rf"^\s*Shear Modulus (\d)\s*=\s*({_FLOAT})\s*(\S+)", re.MULTILINE)
_RE_POISSON = re.compile(rf"^\s*Poisson Ratio\s*=\s*({_FLOAT})", re.MULTILINE)
# Setup-script prints, e.g. "Lattice constant (Angstroms) = 3.52".
_RE_LATTICE = re.compile(rf"lattice constant[^=\n]*=\s*({_FLOAT})", re.IGNORECASE)
_RE_COHESIVE = re.compile(rf"cohesive energy[^=\n]*=\s*({_FLOAT})", re.IGNORECASE)
# LAMMPS banner, e.g. "LAMMPS (2 Aug 2023 - Update 3)".
_RE_BANNER = re.compile(r"^LAMMPS \(.+\)\s*$", re.MULTILINE)

# The cubic constants every ELASTIC run must report; anything else is a bonus.
_REQUIRED_ELASTIC = ("C11", "C12", "C44")


@dataclass(frozen=True)
class ParsedProperty:
    """One raw (name, value, unit) triple extracted from a log, pre-reference."""

    name: str
    value: float
    unit: str


def parse_elastic_log(text: str) -> dict[str, ParsedProperty]:
    """Parse the standard LAMMPS ``examples/ELASTIC`` driver output.

    Tolerant of surrounding noise (thermo blocks, echoed input commands): only
    the recognized summary lines are read. Returns properties keyed by name
    (``C11``..``C66``, ``bulk_modulus``, ``shear_modulus_1``/``_2``,
    ``poisson_ratio``, plus ``lattice_constant`` / ``cohesive_energy`` when the
    driver printed them). Raises ``ValueError`` naming exactly what required
    output was not found.
    """

    props: dict[str, ParsedProperty] = {}
    for match in _RE_ELASTIC_CONSTANT.finditer(text):
        name, value, unit = match.group(1), float(match.group(2)), match.group(3)
        props[name] = ParsedProperty(name=name, value=value, unit=unit)
    bulk = _RE_BULK.search(text)
    if bulk:
        props["bulk_modulus"] = ParsedProperty("bulk_modulus", float(bulk.group(1)), bulk.group(2))
    for match in _RE_SHEAR.finditer(text):
        name = f"shear_modulus_{match.group(1)}"
        props[name] = ParsedProperty(name, float(match.group(2)), match.group(3))
    poisson = _RE_POISSON.search(text)
    if poisson:
        props["poisson_ratio"] = ParsedProperty(
            "poisson_ratio", float(poisson.group(1)), "dimensionless"
        )
    lattice = _RE_LATTICE.search(text)
    if lattice:
        props["lattice_constant"] = ParsedProperty(
            "lattice_constant", float(lattice.group(1)), "Angstrom"
        )
    cohesive = _RE_COHESIVE.search(text)
    if cohesive:
        props["cohesive_energy"] = ParsedProperty(
            "cohesive_energy", float(cohesive.group(1)), "eV"
        )

    missing = [name for name in _REQUIRED_ELASTIC if name not in props]
    if missing:
        raise ValueError(
            f"not a recognizable LAMMPS ELASTIC output: missing {missing} "
            "(expected lines like 'Elastic Constant C11all = 1143.9 GPa' from the "
            "examples/ELASTIC driver)"
        )
    return props


def parse_thermo_log(text: str) -> LammpsTrajectorySummary:
    """Summarize the first thermo section of a LAMMPS log.

    A thermo section is a header row starting with ``Step`` followed by rows
    that are all-numeric and column-aligned; the first non-matching row ends
    it. This is a modest summary (row count, first/final values, raw energy
    drift per step), deliberately not a full log parser.
    """

    lines = text.splitlines()
    columns: list[str] = []
    rows: list[list[float]] = []
    for i, line in enumerate(lines):
        tokens = line.split()
        if not tokens or tokens[0] != "Step" or len(tokens) < 2:
            continue
        section: list[list[float]] = []
        for row_line in lines[i + 1 :]:
            values = row_line.split()
            if len(values) != len(tokens):
                break
            try:
                section.append([float(v) for v in values])
            except ValueError:
                break
        if section:
            columns, rows = tokens, section
            break
    if not rows:
        raise ValueError(
            "no thermo section found: expected a 'Step ...' header row followed by "
            "at least one all-numeric data row"
        )

    energy_column = next((c for c in ("PotEng", "TotEng") if c in columns), None)
    initial = final = drift = None
    first_step, last_step = int(rows[0][0]), int(rows[-1][0])
    if energy_column is not None:
        j = columns.index(energy_column)
        initial, final = rows[0][j], rows[-1][j]
        if last_step > first_step:
            drift = (final - initial) / (last_step - first_step)
    return LammpsTrajectorySummary(
        n_rows=len(rows),
        first_step=first_step,
        last_step=last_step,
        columns=columns,
        energy_column=energy_column,
        initial_energy=initial,
        final_energy=final,
        energy_drift_per_step=drift,
        final_values={c: rows[-1][j] for j, c in enumerate(columns) if c != "Step"},
    )


def _detect_lammps_version(text: str) -> str | None:
    banner = _RE_BANNER.search(text)
    return banner.group(0).strip() if banner else None


def build_evidence(
    log_text: str,
    *,
    material: str,
    potential_id: str,
    properties: Iterable[ParsedProperty] | None = None,
    trajectory: LammpsTrajectorySummary | None = None,
    references: Mapping[str, float] | None = None,
    reference_source: str | None = None,
    input_script: str | None = None,
    log_name: str | None = None,
    parsed_at: datetime | None = None,
) -> LammpsEvidence:
    """Assemble a ``lupine.mlip.lammps_evidence.v1`` payload.

    ``properties`` defaults to :func:`parse_elastic_log` over ``log_text``.
    ``references`` maps property names to caller-supplied reference values (same
    unit as the parsed value); an unknown name is an error so a typo'd reference
    never silently vanishes. ``provenance.log_sha256`` is the sha256 of
    ``log_text``; ``parsed_at`` is recorded only if given (never the clock).
    """

    parsed = (
        list(properties) if properties is not None else list(parse_elastic_log(log_text).values())
    )
    refs = dict(references or {})
    unknown = sorted(set(refs) - {p.name for p in parsed})
    if unknown:
        raise ValueError(
            f"reference(s) {unknown} do not match any parsed property "
            f"(parsed: {sorted(p.name for p in parsed)})"
        )
    return LammpsEvidence(
        material=material,
        source=LammpsSource(
            potential_id=potential_id,
            lammps_version=_detect_lammps_version(log_text),
            input_script=input_script,
        ),
        properties=[
            LammpsPropertyValue(
                name=p.name,
                value=p.value,
                unit=p.unit,
                reference_value=refs.get(p.name),
                reference_source=reference_source if p.name in refs else None,
            )
            for p in parsed
        ],
        trajectory=trajectory,
        provenance=LammpsProvenance(
            log_sha256=hashlib.sha256(log_text.encode("utf-8")).hexdigest(),
            log_name=log_name,
            parsed_at=parsed_at,
        ),
    )


def _safe(s: str) -> str:
    return "".join(c if c.isalnum() else "_" for c in s).strip("_")


def emit_lean_module(
    payloads: Sequence[LammpsEvidence],
    out_path: pathlib.Path | str,
    *,
    namespace: str | None = None,
    tolerance_pct: float = 5.0,
) -> pathlib.Path:
    """Write a Lean 4 module of decidable theorems from evidence payloads.

    Style mirrors ``tools/mlip_distill_atlas.py``: a machine-generated header
    naming the source tool and input hashes, one namespace, and one decidable
    Nat-inequality theorem per reference-annotated property (abs error and
    tolerance both x1000-scaled). A property inside ``tolerance_pct`` of its
    reference yields ``within_tol``; outside it yields ``exceeds_tol`` — the
    verdict is encoded either way, never hidden.

    The module is written to ``out_path`` verbatim. Demos must target
    ``hpc/examples/generated/``; admission into ``lean-spec/`` is a reviewed
    step (see hpc/examples/README.md).
    """

    if tolerance_pct < 0.0:
        raise ValueError("tolerance_pct must be >= 0")
    theorems: list[str] = []
    for payload in payloads:
        pot = payload.source.potential_id
        for prop in payload.properties:
            ref = prop.reference_value
            if ref is None:
                continue
            err = abs(prop.value - ref)
            tol = tolerance_pct / 100.0 * abs(ref)
            err_k, tol_k = int(round(err * 1000)), int(round(tol * 1000))
            safe = _safe(f"{payload.material}_{pot}_{prop.name}")
            cite = f" ({prop.reference_source})" if prop.reference_source else ""
            if err_k <= tol_k:
                name = f"lammps_within_tol_{safe}"
                prop_str = f"{err_k} ≤ {tol_k}"
                verdict = f"|err| {err:.4f} ≤ tol {tol:.4f} {prop.unit} ({tolerance_pct:g}%)"
            else:
                name = f"lammps_exceeds_tol_{safe}"
                prop_str = f"{tol_k} < {err_k}"
                verdict = f"|err| {err:.4f} EXCEEDS tol {tol:.4f} {prop.unit} ({tolerance_pct:g}%)"
            doc = (
                f"{payload.material}/{pot} {prop.name} = {prop.value:.4f} {prop.unit} "
                f"vs reference {ref:.4f}{cite}: {verdict}"
            )
            theorems.append(
                f"/-- {doc}. Machine-checked from LAMMPS log evidence (abs error x1000). -/\n"
                f"theorem {name} : {prop_str} := by decide\n"
            )
    if not theorems:
        raise ValueError("no reference-annotated properties in the payload(s); nothing to prove")

    ns = namespace or (
        "Lupine.LammpsEvidence." + _safe("_".join(sorted({p.material for p in payloads})))
    )
    inputs = "; ".join(
        f"{p.material}/{p.source.potential_id} log sha256 {p.provenance.log_sha256[:12]}"
        for p in payloads
    )
    src = (
        f"/- AUTHORED by lupine_distill.lammps_ingest from LAMMPS log evidence.\n"
        f"   Inputs: {inputs}.\n"
        f"   Decidable Nat facts (abs error vs reference, x1000) — 0 sorry. -/\n\n"
        f"namespace {ns}\n\n" + "\n".join(theorems) + f"\nend {ns}\n"
    )
    out = pathlib.Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(src, encoding="utf-8")
    return out


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #


def _read_text(path: pathlib.Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        raise SystemExit(f"error: cannot read {path}: {exc}") from exc


def _parse_refs(pairs: Sequence[str]) -> dict[str, float]:
    refs: dict[str, float] = {}
    for pair in pairs:
        name, sep, value = pair.partition("=")
        if not sep or not name:
            raise ValueError(f"--ref expects NAME=VALUE, got '{pair}'")
        try:
            refs[name] = float(value)
        except ValueError:
            raise ValueError(f"--ref '{pair}': '{value}' is not a number") from None
    return refs


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m lupine_distill.lammps_ingest",
        description=(
            "Turn LAMMPS log files into versioned lupine.mlip.lammps_evidence.v1 JSON "
            "payloads and machine-checked Lean 4 modules."
        ),
    )
    sub = parser.add_subparsers(dest="command", required=True)

    parse_cmd = sub.add_parser(
        "parse",
        help="parse a LAMMPS log into a lammps_evidence.v1 JSON payload",
        description=(
            "Parse a LAMMPS log (examples/ELASTIC driver output, or a plain thermo log "
            "with --kind thermo) into a schema-validated evidence payload."
        ),
    )
    parse_cmd.add_argument("log", type=pathlib.Path, help="LAMMPS log file to parse")
    parse_cmd.add_argument("--material", required=True, help="element / material, e.g. Ni")
    parse_cmd.add_argument("--potential", required=True, help="potential id, e.g. Ni_u3.eam")
    parse_cmd.add_argument(
        "--kind",
        choices=("elastic", "thermo"),
        default="elastic",
        help="'elastic' parses the ELASTIC driver summary; 'thermo' summarizes a thermo "
        "section only (default: elastic)",
    )
    parse_cmd.add_argument(
        "--ref",
        action="append",
        default=[],
        metavar="NAME=VALUE",
        help="reference value for a parsed property, repeatable (e.g. --ref C11=246.5)",
    )
    parse_cmd.add_argument("--ref-source", default=None, help="citation for the reference values")
    parse_cmd.add_argument(
        "--thermo-log",
        type=pathlib.Path,
        default=None,
        help="separate thermo log to summarize as the payload's trajectory",
    )
    parse_cmd.add_argument("--input-script", default=None, help="driver script name, e.g. in.elastic")
    parse_cmd.add_argument(
        "--parsed-at",
        default=None,
        help="ISO-8601 timestamp recorded as provenance.parsed_at (omitted when not given; "
        "the tool never reads the clock)",
    )
    parse_cmd.add_argument(
        "-o", "--output", type=pathlib.Path, default=None, help="output JSON path (default: stdout)"
    )

    lean_cmd = sub.add_parser(
        "lean",
        help="emit a Lean 4 module from evidence JSON payload(s)",
        description=(
            "Emit decidable theorems (abs error x1000 vs reference) from one or more "
            "lammps_evidence.v1 JSON payloads. Write under hpc/examples/generated/ or a "
            "scratch dir; admission into lean-spec/ is a reviewed step."
        ),
    )
    lean_cmd.add_argument("evidence", nargs="+", type=pathlib.Path, help="evidence JSON payload(s)")
    lean_cmd.add_argument("-o", "--output", type=pathlib.Path, required=True, help=".lean output path")
    lean_cmd.add_argument(
        "--namespace", default=None, help="Lean namespace (default: Lupine.LammpsEvidence.<material>)"
    )
    lean_cmd.add_argument(
        "--tolerance-pct",
        type=float,
        default=5.0,
        help="within/exceeds tolerance as %% of |reference| (default: 5.0)",
    )
    return parser


def _cmd_parse(args: argparse.Namespace) -> int:
    log_text = _read_text(args.log)
    refs = _parse_refs(args.ref)
    parsed_at = datetime.fromisoformat(args.parsed_at) if args.parsed_at else None
    if args.kind == "thermo":
        properties: list[ParsedProperty] = []
        trajectory = parse_thermo_log(log_text)
    else:
        properties = list(parse_elastic_log(log_text).values())
        trajectory = parse_thermo_log(_read_text(args.thermo_log)) if args.thermo_log else None
    evidence = build_evidence(
        log_text,
        material=args.material,
        potential_id=args.potential,
        properties=properties,
        trajectory=trajectory,
        references=refs,
        reference_source=args.ref_source,
        input_script=args.input_script,
        log_name=args.log.name,
        parsed_at=parsed_at,
    )
    payload = json.dumps(evidence.model_dump(mode="json", by_alias=True), indent=2)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload + "\n", encoding="utf-8")
        print(f"wrote {args.output}", file=sys.stderr)
    else:
        print(payload)
    return 0


def _cmd_lean(args: argparse.Namespace) -> int:
    payloads = [LammpsEvidence.model_validate_json(_read_text(p)) for p in args.evidence]
    out = emit_lean_module(
        payloads, args.output, namespace=args.namespace, tolerance_pct=args.tolerance_pct
    )
    print(f"wrote {out}", file=sys.stderr)
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        if args.command == "parse":
            return _cmd_parse(args)
        return _cmd_lean(args)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "ParsedProperty",
    "build_evidence",
    "emit_lean_module",
    "main",
    "parse_elastic_log",
    "parse_thermo_log",
]
