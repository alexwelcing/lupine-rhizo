"""LAMMPS classical (MEAM) leg of the candidate campaign — hea-fcc group.

Runs the SAME measurement instrument as the MLIP leg (measure_candidate from
run_candidate_campaign: identical RSS cells via seed/repeat, identical E-V
relax and FD stress-strain probes) with a classical MEAM calculator driven by
the native LAMMPS python module through ase.calculators.lammpslib. This is
the classical baseline arm of the pre-registered protocol: one deterministic
potential, no ensemble, no concordance gate — raw values + errors vs the
pre-registered references only.

Requires: PYTHONPATH includes C:\\lammps\\Python and PATH includes
C:\\lammps\\bin (liblammps.dll). CPU only.

Run:
    .venv-mlip312/Scripts/python python/scripts/run_lammps_classical_leg.py \
        --targets data/candidates/round1_targets.json
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

_HERE = Path(__file__).resolve()
for _p in (str(_HERE.parent), str(_HERE.parents[1]), str(_HERE.parents[2])):
    if _p not in sys.path:
        sys.path.insert(0, _p)

_REPO_ROOT = _HERE.parents[2]

from run_candidate_campaign import (  # noqa: E402
    load_targets,
    measure_candidate,
)

from lupine_distill.statics import StaticsError  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
log = logging.getLogger("lammps_classical_leg")

REPORT_SCHEMA = "lupine.campaign_lammps_leg.v1"

#: The MEAM parameter file indexes all seven library elements (zbl keywords),
#: so the full library list must load even when only a subset is simulated.
MEAM_LIBRARY_ELEMENTS = "Mo Co Ni V Fe Al Cr"
MEAM_COVERED = frozenset(MEAM_LIBRARY_ELEMENTS.split())
MEAM_LIBRARY = "C:/lammps/Potentials/library_2nn.meam"
MEAM_PARAMS = "C:/lammps/Potentials/MoCoNiVFeAlCr_2nn.meam"
POTENTIAL_ID = "MEAM MoCoNiVFeAlCr_2nn (Choi et al. 2NN MEAM; shipped with LAMMPS 30Mar2026)"


def build_meam_calculator(elements: list[str]) -> object:
    from ase.calculators.lammpslib import LAMMPSlib

    uncovered = [el for el in elements if el not in MEAM_COVERED]
    if uncovered:
        raise StaticsError(f"MEAM potential does not cover: {uncovered}")
    mapping = " ".join(elements)
    return LAMMPSlib(
        lmpcmds=[
            "pair_style meam",
            f"pair_coeff * * {MEAM_LIBRARY} {MEAM_LIBRARY_ELEMENTS} "
            f"{MEAM_PARAMS} {mapping}",
        ],
        atom_types={el: i + 1 for i, el in enumerate(elements)},
        keep_alive=True,
        log_file=None,
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--targets",
        default=str(_REPO_ROOT / "data" / "candidates" / "round1_targets.json"),
    )
    parser.add_argument(
        "--out-dir",
        default=str(_REPO_ROOT / "data" / "candidates" / "round1_lammps"),
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--repeat", type=int, default=2)
    parser.add_argument("--delta", type=float, default=0.5e-2)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    candidates = [
        c for c in load_targets(Path(args.targets)) if c.group == "hea-fcc"
    ]
    if not candidates:
        raise SystemExit("no hea-fcc candidates in targets file")

    results: dict[str, dict[str, object]] = {}
    t_run0 = time.perf_counter()
    for candidate in candidates:
        elements = sorted(candidate.composition_dict())
        log.info("%s x MEAM (%s)", candidate.id, ",".join(elements))
        try:
            calculator = build_meam_calculator(elements)
            record, _relaxed = measure_candidate(
                calculator,
                candidate,
                repeat=args.repeat,
                seed=args.seed,
                delta=args.delta,
            )
        except StaticsError as exc:
            log.info("  MEASUREMENT FAILED: %s", exc)
            results[candidate.id] = {"error": f"{type(exc).__name__}: {exc}"}
            continue
        errors: dict[str, float] = {}
        for prop, ref in dict(candidate.references).items():
            value = record["properties"].get(prop)
            if ref is not None and value is not None:
                errors[prop] = abs(value - ref) / abs(ref)
        record["abs_rel_error_vs_reference"] = errors
        results[candidate.id] = record

    report = {
        "schema": REPORT_SCHEMA,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "potential": POTENTIAL_ID,
        "parameters": {
            "seed": args.seed,
            "repeat": args.repeat,
            "elastic_delta": args.delta,
            "instrument": (
                "identical to the MLIP leg: run_candidate_campaign."
                "measure_candidate (same RSS cells, E-V relax, FD stress probe)"
            ),
        },
        "candidates": results,
        "total_wall_time_seconds": time.perf_counter() - t_run0,
    }
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "report.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    log.info(
        "classical leg: %d candidates in %.1f s -> %s",
        len(candidates),
        report["total_wall_time_seconds"],
        out_dir,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
