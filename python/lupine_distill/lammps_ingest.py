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

``emit_lean_module`` also accepts ``lupine.mlip.calc_evidence.v1`` payloads
(:class:`~lupine_distill.schemas.CalcEvidence`, assembled by
:mod:`lupine_distill.calc_evidence`): ASE-calculator/GPU results route through
the same theorem-emission core, with ``calc_``-prefixed theorem names and
``inputs sha256`` provenance instead of ``log sha256``.

Tolerance semantics: by default a property is "within" when its absolute error
is at most ``tolerance_pct`` percent of ``|reference_value|``. A property may
carry an explicit absolute ``tolerance`` (same unit as the value), which then
replaces the percentage rule for that property — necessary for near-zero
references (5% of a ~10 mJ/m^2 stacking-fault energy, or of a 0.0 formation
enthalpy, is degenerate). The field is optional-with-None, so existing v1
payloads and the default percentage behavior are unchanged.

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
    CALC_EVIDENCE_SCHEMA,
    CalcEvidence,
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


@dataclass(frozen=True)
class _EvidenceView:
    """Lane-neutral projection of an evidence payload for Lean emission."""

    material: str
    source_label: str
    properties: tuple[LammpsPropertyValue, ...]
    provenance_line: str
    theorem_prefix: str  # "lammps" | "calc"
    evidence_note: str  # human wording used in header and theorem docs
    namespace_root: str


def _view(payload: LammpsEvidence | CalcEvidence) -> _EvidenceView:
    if isinstance(payload, LammpsEvidence):
        return _EvidenceView(
            material=payload.material,
            source_label=payload.source.potential_id,
            properties=tuple(payload.properties),
            provenance_line=(
                f"{payload.material}/{payload.source.potential_id} "
                f"log sha256 {payload.provenance.log_sha256[:12]}"
            ),
            theorem_prefix="lammps",
            evidence_note="LAMMPS log evidence",
            namespace_root="Lupine.LammpsEvidence",
        )
    if isinstance(payload, CalcEvidence):
        return _EvidenceView(
            material=payload.material,
            source_label=payload.source.model_id,
            properties=tuple(payload.properties),
            provenance_line=(
                f"{payload.material}/{payload.source.model_id} "
                f"inputs sha256 {payload.provenance.inputs_sha256[:12]}"
            ),
            theorem_prefix="calc",
            evidence_note="calculator evidence",
            namespace_root="Lupine.CalcEvidence",
        )
    raise TypeError(f"unsupported evidence payload type: {type(payload).__name__}")


def _emit_theorems(
    *,
    material: str,
    source_label: str,
    properties: Sequence[LammpsPropertyValue],
    theorem_prefix: str,
    evidence_note: str,
    tolerance_pct: float,
) -> list[str]:
    """Shared theorem-emission core for both evidence lanes.

    One decidable Nat-inequality theorem per reference-annotated property (abs
    error and tolerance both x1000-scaled). A property's explicit ``tolerance``
    (absolute, same unit) replaces the ``tolerance_pct``-of-``|reference|``
    default when set — see the module docstring for why.
    """

    theorems: list[str] = []
    for prop in properties:
        ref = prop.reference_value
        if ref is None:
            continue
        err = abs(prop.value - ref)
        if prop.tolerance is not None:
            tol, tol_label = prop.tolerance, "(explicit)"
        else:
            tol, tol_label = tolerance_pct / 100.0 * abs(ref), f"({tolerance_pct:g}%)"
        err_k, tol_k = int(round(err * 1000)), int(round(tol * 1000))
        safe = _safe(f"{material}_{source_label}_{prop.name}")
        cite = f" ({prop.reference_source})" if prop.reference_source else ""
        if err_k <= tol_k:
            name = f"{theorem_prefix}_within_tol_{safe}"
            prop_str = f"{err_k} ≤ {tol_k}"
            verdict = f"|err| {err:.4f} ≤ tol {tol:.4f} {prop.unit} {tol_label}"
        else:
            name = f"{theorem_prefix}_exceeds_tol_{safe}"
            prop_str = f"{tol_k} < {err_k}"
            verdict = f"|err| {err:.4f} EXCEEDS tol {tol:.4f} {prop.unit} {tol_label}"
        doc = (
            f"{material}/{source_label} {prop.name} = {prop.value:.4f} {prop.unit} "
            f"vs reference {ref:.4f}{cite}: {verdict}"
        )
        theorems.append(
            f"/-- {doc}. Machine-checked from {evidence_note} (abs error x1000). -/\n"
            f"theorem {name} : {prop_str} := by decide\n"
        )
    return theorems


def _module_origin(views: Sequence[_EvidenceView]) -> str:
    kinds = {v.theorem_prefix for v in views}
    if kinds == {"lammps"}:
        return "LAMMPS log evidence"
    if kinds == {"calc"}:
        return "calculator evidence"
    return "LAMMPS log and calculator evidence"


def _default_namespace(views: Sequence[_EvidenceView]) -> str:
    roots = {v.namespace_root for v in views}
    root = next(iter(roots)) if len(roots) == 1 else "Lupine.Evidence"
    return root + "." + _safe("_".join(sorted({v.material for v in views})))


def emit_lean_module(
    payloads: Sequence[LammpsEvidence | CalcEvidence],
    out_path: pathlib.Path | str,
    *,
    namespace: str | None = None,
    tolerance_pct: float = 5.0,
) -> pathlib.Path:
    """Write a Lean 4 module of decidable theorems from evidence payloads.

    Style mirrors ``tools/mlip_distill_atlas.py``: a machine-generated header
    naming the source tool and input hashes, one namespace, and one decidable
    Nat-inequality theorem per reference-annotated property (abs error and
    tolerance both x1000-scaled). A property inside its tolerance — explicit
    per-property ``tolerance`` when set, else ``tolerance_pct`` of the
    reference — yields ``within_tol``; outside it yields ``exceeds_tol`` — the
    verdict is encoded either way, never hidden.

    ``payloads`` may mix :class:`LammpsEvidence` and :class:`CalcEvidence`;
    theorem names are prefixed ``lammps_`` / ``calc_`` per payload lane, and
    the LAMMPS-only output is byte-identical to what this function emitted
    before calculator support existed.

    The module is written to ``out_path`` verbatim. Demos must target
    ``hpc/examples/generated/``; admission into ``lean-spec/`` is a reviewed
    step (see hpc/examples/README.md).
    """

    if tolerance_pct < 0.0:
        raise ValueError("tolerance_pct must be >= 0")
    views = [_view(p) for p in payloads]
    theorems: list[str] = []
    for view in views:
        theorems.extend(
            _emit_theorems(
                material=view.material,
                source_label=view.source_label,
                properties=view.properties,
                theorem_prefix=view.theorem_prefix,
                evidence_note=view.evidence_note,
                tolerance_pct=tolerance_pct,
            )
        )
    if not theorems:
        raise ValueError("no reference-annotated properties in the payload(s); nothing to prove")

    ns = namespace or _default_namespace(views)
    inputs = "; ".join(v.provenance_line for v in views)
    src = (
        f"/- AUTHORED by lupine_distill.lammps_ingest from {_module_origin(views)}.\n"
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
            "lammps_evidence.v1 / calc_evidence.v1 JSON payloads. Write under "
            "hpc/examples/generated/ or a scratch dir; admission into lean-spec/ is a "
            "reviewed step."
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


def _load_evidence(path: pathlib.Path) -> LammpsEvidence | CalcEvidence:
    """Validate an evidence JSON file, dispatching on its ``"schema"`` key."""

    try:
        payload = json.loads(_read_text(path))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path}: not valid JSON: {exc}") from exc
    if isinstance(payload, dict) and payload.get("schema") == CALC_EVIDENCE_SCHEMA:
        return CalcEvidence.model_validate(payload)
    return LammpsEvidence.model_validate(payload)


def _cmd_lean(args: argparse.Namespace) -> int:
    payloads = [_load_evidence(p) for p in args.evidence]
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
