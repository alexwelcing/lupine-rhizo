"""Round-1 prereg S4 criteria evaluation (Round-3 registered instrument fix 3).

Computes the preregistered Round-1 primary statistic EXACTLY as frozen in
``docs/plans/2026-07-13-unbiased-accuracy-campaign.md`` section 4 (2026-07-13,
before any Round-1 prediction ran) — the statistic that was never computed at
the time (2026-07-13 errata finding 8):

* Per group x property leg: **median (and mean) |relative error|** vs the
  preregistered reference, raw arm vs Lupine-corrected (cross-class de-bias)
  arm. The corrected arm is Round 1's ``corrected_arm`` — identical, cell for
  cell, to the Round-2 report's ``cross_class`` arm (cross-checked here).
* **Directional sign test**: exact two-sided binomial over held-out
  (candidate, model) cells — does the correction move the prediction toward
  the reference more often than away; ties (corrected == raw, i.e. the bias
  abstained or never loaded) are DROPPED.
* **Success criterion per group**: corrected reduces median |rel err| on
  >= 2 of the 3 preregistered property legs (a0, B0, Cij) with sign-test
  p < 0.1. PASS/FAIL reported verbatim.
* **Preregistered exclusions** (S4, flagged pre-run in the targets file):
  CsSnI3 Cij and CsGeI3 a0 are excluded from all headline numbers here.
* **Silent Cij degradation** (errata finding 8): the Cij bias arm silently
  failed to load in Round 1, so every Cij corrected value equals raw. The
  3-leg denominator is KEPT — the Cij leg is evaluated (all ties, no
  evidence of improvement, criterion not met), not dropped, so the
  preregistered 2-of-3 cannot silently degrade to 2-of-2.

Writes ``data/candidates/round1/criteria_evaluation.json`` (the Round-1
report itself is a frozen artifact and is not modified).

Run (no GPU, no calculators):
    .venv-mlip312/Scripts/python python/scripts/evaluate_round1_criteria.py
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Final, Mapping

import numpy as np

_HERE = Path(__file__).resolve()
for _p in (str(_HERE.parent), str(_HERE.parents[1]), str(_HERE.parents[2])):
    if _p not in sys.path:
        sys.path.insert(0, _p)

_REPO_ROOT = _HERE.parents[2]

from lupine_distill.statics import InputValidationError  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
log = logging.getLogger("round1_criteria")

SCHEMA: Final[str] = "lupine.round1_criteria_evaluation.v1"
ROUND1_SCHEMA: Final[str] = "lupine.candidate_campaign.v1"
ROUND2_SCHEMA: Final[str] = "lupine.campaign_round2.v1"
PREREG_PATH: Final[str] = "docs/plans/2026-07-13-unbiased-accuracy-campaign.md"

PROPERTIES: Final[tuple[str, ...]] = ("a0", "b0", "c11", "c12", "c44")

#: The three preregistered property legs of the S4 success criterion
#: ("Properties: a0, B0, C11/C12/C44 (where reference exists)"; "reduces
#: median |rel err| for >= 2 of 3 properties per group").
LEGS: Final[Mapping[str, tuple[str, ...]]] = {
    "a0": ("a0",),
    "b0": ("b0",),
    "cij": ("c11", "c12", "c44"),
}

#: Preregistered S4 exclusions, frozen BEFORE any prediction ran:
#: "CsSnI3 Cij and CsGeI3 a0 are excluded from headline criteria (weak/null
#: references, flagged pre-run in the targets file)." (CsGeI3 a0 is null in
#: the targets file, so its exclusion is doubly enforced.)
PREREG_EXCLUSIONS: Final[frozenset[tuple[str, str]]] = frozenset(
    {
        ("hp-cssni3", "c11"),
        ("hp-cssni3", "c12"),
        ("hp-cssni3", "c44"),
        ("hp-csgei3", "a0"),
    }
)

SIGN_TEST_ALPHA: Final[float] = 0.1
MIN_LEGS_TO_PASS: Final[int] = 2

SILENT_CIJ_DEGRADATION_NOTE: Final[str] = (
    "Silent Cij-bias degradation (2026-07-13 errata finding 8): the Round-1 "
    "Cij bias arm silently failed to load (the model_biases.v1 artifact "
    "carried no cij biases: 'cij available: False'), so every Cij corrected "
    "value equals raw. Under the preregistered rules those cells are ties "
    "and are dropped from the sign test; the Cij leg therefore has zero "
    "effective cells, shows no median reduction, and its criterion is NOT "
    "met. The 3-leg denominator is kept: the preregistered '>= 2 of 3 "
    "properties' criterion is evaluated as written, not silently degraded "
    "to 2-of-2."
)


# --------------------------------------------------------------------------
# statistics
# --------------------------------------------------------------------------


def exact_binomial_two_sided_p(k: int, n: int) -> float:
    """Exact two-sided binomial sign-test p-value (p0 = 0.5).

    ``k`` successes out of ``n`` non-tie trials. Two-sided as twice the
    smaller tail (equivalently, for the symmetric p0=0.5 null, the minimum-
    likelihood method), capped at 1.
    """
    if not isinstance(k, int) or not isinstance(n, int) or n < 1 or not 0 <= k <= n:
        raise InputValidationError(f"need 0 <= k <= n with n >= 1, got k={k}, n={n}")
    tail_start = max(k, n - k)
    upper_tail = sum(math.comb(n, i) for i in range(tail_start, n + 1)) / 2.0**n
    return min(1.0, 2.0 * upper_tail)


# --------------------------------------------------------------------------
# cell extraction
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Cell:
    """One held-out (candidate, model, property) measurement with reference."""

    group: str
    candidate: str
    model: str
    prop: str
    reference: float
    raw: float
    corrected: float
    was_corrected: bool

    @property
    def abs_rel_err_raw(self) -> float:
        return abs(self.raw - self.reference) / abs(self.reference)

    @property
    def abs_rel_err_corrected(self) -> float:
        return abs(self.corrected - self.reference) / abs(self.reference)


def _load_report(path: Path, expected_schema: str) -> dict[str, object]:
    """Read + schema-validate a report JSON at a trust boundary (fail fast)."""
    if not path.is_file():
        raise InputValidationError(f"report does not exist: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise InputValidationError(f"cannot read report {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise InputValidationError(f"{path}: report root must be a JSON object")
    schema = payload.get("schema")
    if schema != expected_schema:
        raise InputValidationError(
            f"{path}: expected schema {expected_schema!r}, got {schema!r}"
        )
    return payload


def collect_cells(
    round1: Mapping[str, object],
) -> tuple[list[Cell], list[dict[str, str]]]:
    """(included cells, excluded-cell records) from the Round-1 report.

    A cell exists when the candidate carries a non-null, non-zero reference
    for the property and the model measurement succeeded. Cells on the
    preregistered exclusion list are returned separately (never pooled).
    """
    candidates = round1.get("candidates")
    if not isinstance(candidates, Mapping) or not candidates:
        raise InputValidationError("round1 report has no 'candidates' mapping")
    cells: list[Cell] = []
    excluded: list[dict[str, str]] = []
    for cid, sub in sorted(candidates.items()):
        if not isinstance(sub, Mapping):
            raise InputValidationError(f"candidate {cid!r} malformed")
        group = str(sub.get("group", ""))
        references = sub.get("references")
        per_model = sub.get("per_model")
        arm = sub.get("corrected_arm")
        if not isinstance(references, Mapping) or not isinstance(per_model, Mapping):
            raise InputValidationError(f"candidate {cid!r}: missing references/per_model")
        if not isinstance(arm, Mapping):
            raise InputValidationError(f"candidate {cid!r}: missing corrected_arm")
        for prop in PROPERTIES:
            reference = references.get(prop)
            if reference is None or float(reference) == 0.0:
                continue
            for model, record in sorted(per_model.items()):
                if not isinstance(record, Mapping) or "error" in record:
                    continue
                if (cid, prop) in PREREG_EXCLUSIONS:
                    excluded.append(
                        {
                            "candidate": cid,
                            "model": str(model),
                            "prop": prop,
                            "reason": "preregistered S4 exclusion "
                            "(weak/null reference, flagged pre-run)",
                        }
                    )
                    continue
                corrected_entry = arm.get(model, {}).get("values", {}).get(prop)
                if not isinstance(corrected_entry, Mapping):
                    raise InputValidationError(
                        f"candidate {cid!r}: corrected_arm missing {model}/{prop}"
                    )
                cells.append(
                    Cell(
                        group=group,
                        candidate=cid,
                        model=str(model),
                        prop=prop,
                        reference=float(reference),
                        raw=float(record["properties"][prop]),
                        corrected=float(corrected_entry["value"]),
                        was_corrected=bool(corrected_entry["corrected"]),
                    )
                )
    if not cells:
        raise InputValidationError("no evaluable (candidate, model, property) cells")
    return cells, excluded


# --------------------------------------------------------------------------
# evaluation
# --------------------------------------------------------------------------


def _pool_stats(pool: list[Cell]) -> dict[str, object]:
    """Median/mean |rel err| raw vs corrected + exact sign test over cells."""
    raw_errors = [c.abs_rel_err_raw for c in pool]
    corrected_errors = [c.abs_rel_err_corrected for c in pool]
    n_improved = sum(
        1 for c in pool if c.abs_rel_err_corrected < c.abs_rel_err_raw
    )
    n_worsened = sum(
        1 for c in pool if c.abs_rel_err_corrected > c.abs_rel_err_raw
    )
    n_effective = n_improved + n_worsened
    p_value = (
        exact_binomial_two_sided_p(n_improved, n_effective)
        if n_effective > 0
        else None
    )
    median_raw = float(np.median(raw_errors))
    median_corrected = float(np.median(corrected_errors))
    return {
        "n_cells": len(pool),
        "n_corrected_cells": sum(1 for c in pool if c.was_corrected),
        "median_abs_rel_err_raw": median_raw,
        "median_abs_rel_err_corrected": median_corrected,
        "mean_abs_rel_err_raw": float(np.mean(raw_errors)),
        "mean_abs_rel_err_corrected": float(np.mean(corrected_errors)),
        "reduces_median": bool(median_corrected < median_raw),
        "sign_test": {
            "n_improved": n_improved,
            "n_worsened": n_worsened,
            "n_ties_dropped": len(pool) - n_effective,
            "p_two_sided_exact": p_value,
        },
    }


def evaluate_group(group: str, cells: list[Cell]) -> dict[str, object]:
    """S4 verdict for one group: 3 property legs, >= 2 must improve at p < 0.1."""
    group_cells = [c for c in cells if c.group == group]
    per_property = {
        prop: _pool_stats(pool)
        for prop in PROPERTIES
        if (pool := [c for c in group_cells if c.prop == prop])
    }
    legs: dict[str, object] = {}
    n_met = 0
    for leg, props in LEGS.items():
        pool = [c for c in group_cells if c.prop in props]
        if not pool:
            legs[leg] = {
                "properties": list(props),
                "evaluable": False,
                "criterion_met": False,
                "note": "no cells with a non-null preregistered reference",
            }
            continue
        stats = _pool_stats(pool)
        p_value = stats["sign_test"]["p_two_sided_exact"]
        criterion_met = bool(
            stats["reduces_median"]
            and p_value is not None
            and p_value < SIGN_TEST_ALPHA
        )
        entry: dict[str, object] = {
            "properties": list(props),
            "evaluable": True,
            **stats,
            "criterion": (
                f"median |rel err| corrected < raw AND exact two-sided "
                f"binomial sign test p < {SIGN_TEST_ALPHA} (ties dropped)"
            ),
            "criterion_met": criterion_met,
        }
        if leg == "cij" and stats["n_corrected_cells"] == 0:
            entry["note"] = SILENT_CIJ_DEGRADATION_NOTE
        legs[leg] = entry
        n_met += int(criterion_met)
    return {
        "per_property": per_property,
        "legs": legs,
        "n_legs_met": n_met,
        "n_legs_required": MIN_LEGS_TO_PASS,
        "verdict": "PASS" if n_met >= MIN_LEGS_TO_PASS else "FAIL",
    }


def cross_check_round2(
    cells: list[Cell], round2: Mapping[str, object]
) -> dict[str, object]:
    """Verify Round-1 corrected_arm == Round-2 cross_class arm, cell by cell."""
    rows = round2.get("rows")
    if not isinstance(rows, list) or not rows:
        raise InputValidationError("round2 report has no 'rows' list")
    by_key = {(c.candidate, c.model, c.prop): c for c in cells}
    n_checked = 0
    mismatches: list[str] = []
    for row in rows:
        if not isinstance(row, Mapping):
            raise InputValidationError("round2 rows must be objects")
        key = (str(row["candidate"]), str(row["model"]), str(row["prop"]))
        cell = by_key.get(key)
        if cell is None:  # excluded or null-reference cell; not evaluated here
            continue
        n_checked += 1
        for label, mine, theirs in (
            ("raw", cell.raw, float(row["raw"])),
            ("cross_class", cell.corrected, float(row["cross_class"])),
        ):
            if not math.isclose(mine, theirs, rel_tol=1e-9, abs_tol=1e-12):
                mismatches.append(f"{'/'.join(key)}: {label} {mine} != {theirs}")
    if n_checked == 0:
        raise InputValidationError("round2 cross-check matched zero cells")
    return {
        "arm": "cross_class",
        "n_cells_checked": n_checked,
        "n_mismatches": len(mismatches),
        "mismatches": mismatches[:20],
        "consistent": not mismatches,
    }


def gates_descriptive(round1: Mapping[str, object]) -> dict[str, object]:
    """S4 gates statement (descriptive, reported either way, within-group).

    Median raw |rel err| pooled over included cells, split by the candidate's
    gate verdict (issued = CERTIFIED/FLAGGED vs REFUSED). Descriptive only —
    per errata finding 3, no pooled cross-class efficacy ratio is computed.
    """
    candidates = round1["candidates"]
    verdicts = {
        cid: str(sub["verdict"]) for cid, sub in candidates.items()
    }
    cells, _ = collect_cells(round1)
    out: dict[str, object] = {}
    for group in sorted({c.group for c in cells}):
        split: dict[str, list[float]] = {"issued": [], "refused": []}
        for cell in cells:
            if cell.group != group:
                continue
            kind = "refused" if verdicts[cell.candidate] == "REFUSED" else "issued"
            split[kind].append(cell.abs_rel_err_raw)
        out[group] = {
            kind: {
                "n_cells": len(errors),
                "median_abs_rel_err_raw": (
                    float(np.median(errors)) if errors else None
                ),
            }
            for kind, errors in split.items()
        }
    out["note"] = (
        "Descriptive only (preregistered as report-either-way); within-group "
        "split, no pooled cross-class ratio (2026-07-13 errata finding 3)."
    )
    return out


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--round1-report",
        default=str(_REPO_ROOT / "data" / "candidates" / "round1" / "report.json"),
        help="Round-1 candidate-campaign report (raw + corrected_arm source)",
    )
    parser.add_argument(
        "--round2-report",
        default=str(_REPO_ROOT / "data" / "candidates" / "round2" / "report.json"),
        help="Round-2 report whose cross_class arm cross-checks the corrected arm",
    )
    parser.add_argument(
        "--out",
        default=str(
            _REPO_ROOT / "data" / "candidates" / "round1" / "criteria_evaluation.json"
        ),
        help="criteria_evaluation.json output path",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        round1 = _load_report(Path(args.round1_report), ROUND1_SCHEMA)
        round2 = _load_report(Path(args.round2_report), ROUND2_SCHEMA)
        cells, excluded = collect_cells(round1)
        cross_check = cross_check_round2(cells, round2)
    except InputValidationError as exc:
        log.error("criteria evaluation failed: %s", exc)
        return 1
    if not cross_check["consistent"]:
        log.error(
            "Round-1 corrected_arm and Round-2 cross_class arm DISAGREE on "
            "%d cells; refusing to evaluate against an inconsistent arm",
            cross_check["n_mismatches"],
        )
        return 1

    groups = sorted({c.group for c in cells})
    evaluation = {group: evaluate_group(group, cells) for group in groups}

    artifact = {
        "schema": SCHEMA,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "preregistration": PREREG_PATH,
        "round1_report": Path(args.round1_report).as_posix(),
        "round1_generated_at": str(round1.get("generated_at")),
        "criteria_text": (
            "S4 (frozen 2026-07-13, pre-run): 'De-bias: reduces median "
            "|rel err| for >= 2 of 3 properties per group, with sign-test "
            "p < 0.1.' Properties/legs: a0, B0, C11/C12/C44 (where reference "
            "exists); directional sign test = exact two-sided binomial over "
            "(candidate, model) cells, ties dropped; exclusions: CsSnI3 Cij "
            "and CsGeI3 a0."
        ),
        "corrected_arm": (
            "Round-1 corrected_arm (per-class median-bias de-bias) == "
            "Round-2 'cross_class' arm; verified cell-by-cell below"
        ),
        "round2_cross_check": {
            "round2_report": Path(args.round2_report).as_posix(),
            **cross_check,
        },
        "excluded_cells": excluded,
        "groups": evaluation,
        "notes": [
            SILENT_CIJ_DEGRADATION_NOTE,
            "This evaluation was computed on 2026-07-13 as a Round-3 "
            "registered instrument fix (errata finding 8: Round-1's "
            "preregistered primary statistic was never computed at the "
            "time). References and exclusions are exactly the frozen S4 "
            "set; no post-hoc choices were made.",
        ],
        "gates_descriptive": gates_descriptive(round1),
    }
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(artifact, indent=2), encoding="utf-8")

    for group in groups:
        result = evaluation[group]
        log.info(
            "%s: %s (%d/%d legs met)",
            group,
            result["verdict"],
            result["n_legs_met"],
            len(LEGS),
        )
        for leg, entry in result["legs"].items():
            if not entry.get("evaluable"):
                log.info("  %s: not evaluable (%s)", leg, entry.get("note"))
                continue
            sign = entry["sign_test"]
            log.info(
                "  %s: median raw %.4f -> corr %.4f | improved %d / worsened %d "
                "(ties dropped %d) | p=%s | criterion %s",
                leg,
                entry["median_abs_rel_err_raw"],
                entry["median_abs_rel_err_corrected"],
                sign["n_improved"],
                sign["n_worsened"],
                sign["n_ties_dropped"],
                "n/a" if sign["p_two_sided_exact"] is None
                else f"{sign['p_two_sided_exact']:.4f}",
                "MET" if entry["criterion_met"] else "NOT MET",
            )
    log.info("criteria evaluation -> %s", out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
