"""EXPLORATORY hypothesis test: does PREDICTION-HULL membership predict
correction success?

Label: EXPLORATORY (registered as such; no new measurements). This analysis
reuses existing Round-1/2/3 artifacts only — no GPU, no MLIP calls, no
reference re-sourcing. It does NOT amend any frozen registration; Round-3
results remain governed by ``docs/plans/2026-07-13-round3-preregistration.md``.

Motivation. The proven capped in-hull correction theorems
(``lean-spec/LupineEvidence/Shapes/Certificates.lean``,
``capped_inhull_correction_helps_inflation`` / ``_deflation``) license a
correction only under an IN-HULL hypothesis on the target's true ratio
r = pred/ref — which is unknowable at runtime (it needs the reference).
Question: is there a KNOWABLE-at-runtime proxy for that hypothesis?

Per (candidate X, model m, property p) cell where the frozen Round-3 rule
APPLIED, compute:

(a) outcome  — success iff |corrected - ref| < |raw - ref| (ties excluded,
    counted);
(b) true ratio r = raw_pred / ref (unknowable at runtime; descriptive);
(c) proxy    — is model m's RAW prediction for X inside the hull
    [min, max] of the OTHER models' raw predictions for X (knowable);
(c2) variant — is m's LOO-bias-CORRECTED prediction inside that same
    cross-model raw-prediction hull (knowable);
(d) oracle   — is r inside the calibration ratio hull
    [min(ratios_i), max(ratios_i)] over m's LOO calibration members
    (the theorems' in-hull hypothesis; unknowable at runtime — upper bound).

Association statistics: 2x2 contingency (predictor vs outcome), exact
two-sided Fisher test (hypergeometric, no scipy), per property and pooled;
plus per-stratum exact binomial sign p (success vs failure within each hull
stratum) for the degenerate-margin cases. Round-3 cells are PRIMARY;
Round-1/2 cells (re-evaluated under the same frozen Round-3 rule — NOT the
exploratory Round-2 sign gate) are SECONDARY.

Also emitted: a Round-4 cap preview — which applied cells would keep their
license under the PROVEN theorem caps (inflation: b - 1 > 2s; deflation:
1 - b > 3s AND b >= 0.5) — to inform the registered Round-4 cap change.

Inputs:  Round-3 campaign report + round3_analysis.json (cross-check),
         Round-1 campaign report, Round-2 report (raw/ref cross-check).
Outputs: data/candidates/round3/prediction_hull_analysis.json
         data/candidates/round3/PREDICTION_HULL_ANALYSIS.md
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping, Sequence

_HERE = Path(__file__).resolve()
_REPO_ROOT = _HERE.parents[2]
if str(_HERE.parent) not in sys.path:
    sys.path.insert(0, str(_HERE.parent))

import run_round3_analysis as r3  # noqa: E402  (frozen-rule implementation)

SCHEMA = "lupine.prediction_hull_analysis.v1"
LABEL = "EXPLORATORY"
PROPS = r3.PROPS
PREDICTORS: tuple[tuple[str, str], ...] = (
    (
        "proxy_raw_in_cross_model_hull",
        "(c) KNOWABLE: raw prediction of model m inside [min, max] of the "
        "other models' raw predictions for the same candidate/property",
    ),
    (
        "proxy_corrected_in_cross_model_hull",
        "(c2) KNOWABLE: LOO-bias-corrected prediction of model m inside the "
        "other models' raw-prediction hull",
    ),
    (
        "oracle_ratio_in_calibration_hull",
        "(d) UNKNOWABLE oracle: true ratio r = raw/ref inside "
        "[min, max] of m's LOO calibration ratios (the theorems' in-hull "
        "hypothesis)",
    ),
)
RAW_MATCH_TOLERANCE = 1e-9


class InputValidationError(ValueError):
    """Raised when an input artifact fails validation."""


# --------------------------------------------------------------------------
# exact statistics (stdlib only)
# --------------------------------------------------------------------------


def fisher_exact_two_sided(a: int, b: int, c: int, d: int) -> float | None:
    """Exact two-sided Fisher p for the 2x2 table [[a, b], [c, d]].

    Two-sided by summing hypergeometric outcomes no more probable than the
    observed table. None when the table is empty; 1.0 when a margin is
    degenerate (no association is testable).
    """
    if min(a, b, c, d) < 0:
        raise InputValidationError("contingency counts must be non-negative")
    n = a + b + c + d
    if n == 0:
        return None
    r1, c1 = a + b, a + c
    if r1 in (0, n) or c1 in (0, n):
        return 1.0
    lo = max(0, c1 - (n - r1))
    hi = min(r1, c1)
    denom = math.comb(n, c1)

    def pmf(k: int) -> float:
        return math.comb(r1, k) * math.comb(n - r1, c1 - k) / denom

    p_obs = pmf(a)
    total = sum(
        pmf(k) for k in range(lo, hi + 1) if pmf(k) <= p_obs * (1.0 + 1e-9)
    )
    return min(1.0, total)


def contingency(
    rows: Sequence[Mapping[str, object]], predictor: str
) -> dict[str, object]:
    """2x2 association of one boolean predictor vs success, over classified rows.

    Rows where the predictor is None (undefined) or the outcome is a tie are
    excluded and counted. Includes exact Fisher p and per-stratum exact
    binomial sign p (informative when a Fisher margin is degenerate).
    """
    n_undefined = sum(1 for r in rows if r[predictor] is None)
    n_ties = sum(1 for r in rows if r[predictor] is not None and r["tie"])
    usable = [r for r in rows if r[predictor] is not None and not r["tie"]]
    a = sum(1 for r in usable if r[predictor] and r["success"])
    b = sum(1 for r in usable if r[predictor] and not r["success"])
    c = sum(1 for r in usable if not r[predictor] and r["success"])
    d = sum(1 for r in usable if not r[predictor] and not r["success"])
    return {
        "n_cells": len(usable),
        "n_undefined_excluded": n_undefined,
        "n_ties_excluded": n_ties,
        "table": {
            "in_hull_success": a,
            "in_hull_failure": b,
            "out_hull_success": c,
            "out_hull_failure": d,
        },
        "success_rate_in_hull": a / (a + b) if (a + b) else None,
        "success_rate_out_hull": c / (c + d) if (c + d) else None,
        "fisher_p_two_sided": fisher_exact_two_sided(a, b, c, d),
        "binomial_sign_p_in_hull": r3.exact_binomial_sign_p(a, b),
        "binomial_sign_p_out_hull": r3.exact_binomial_sign_p(c, d),
    }


# --------------------------------------------------------------------------
# per-cell predictors
# --------------------------------------------------------------------------


def cross_model_hull(
    candidates: Mapping[str, Mapping],
    models: Sequence[str],
    cid: str,
    model: str,
    prop: str,
) -> tuple[float, float] | None:
    """[min, max] of the OTHER models' raw predictions for (cid, prop)."""
    others = [
        pred
        for om in models
        if om != model
        for pred in (r3.prediction(candidates[cid], om, prop),)
        if pred is not None
    ]
    if len(others) < 2:
        return None
    return (min(others), max(others))


def round4_cap_preview(ratios: Sequence[float]) -> dict[str, object]:
    """Would the PROVEN theorem caps license this cell's correction?

    Inflation side (all ratios > 1): licensed iff b - 1 > 2s.
    Deflation side (all ratios < 1): licensed iff 1 - b > 3s AND b >= 0.5.
    (b = median ratio, s = max - min; strict inequalities as in the Lean
    statements ``2 * s < b - 10000`` and ``3 * s < 10000 - b``, ``5000 <= b``.)
    """
    b = statistics.median(ratios)
    s = max(ratios) - min(ratios)
    if all(r > 1.0 for r in ratios):
        return {"side": "inflation", "licensed": (b - 1.0) > 2.0 * s}
    if all(r < 1.0 for r in ratios):
        return {
            "side": "deflation",
            "licensed": ((1.0 - b) > 3.0 * s) and (b >= 0.5),
        }
    return {"side": "mixed", "licensed": False}


def build_cell_rows(report: Mapping) -> tuple[dict[str, object], ...]:
    """One row per APPLIED frozen-rule cell, with outcome + hull predictors."""
    candidates: Mapping[str, Mapping] = report["candidates"]
    models: Sequence[str] = report["models"]
    groups: dict[str, list[str]] = {}
    for cid in sorted(candidates):
        groups.setdefault(str(candidates[cid]["group"]), []).append(cid)

    rows: list[dict[str, object]] = []
    for cell in r3.evaluate_cells(report, ()):
        if not cell["applied"]:
            continue
        cid = str(cell["candidate"])
        model = str(cell["model"])
        prop = str(cell["prop"])
        members = groups[str(cell["group"])]
        ratios = r3.calibration_ratios(candidates, members, cid, model, prop)
        if len(ratios) < r3.MIN_CALIBRATION_MEMBERS:  # applied guarantees this
            raise InputValidationError(
                f"applied cell {cid}/{model}/{prop} lacks calibration ratios"
            )
        raw = float(cell["raw"])
        corrected = float(cell["corrected"])
        ref = float(cell["reference"])
        ratio_r = raw / ref
        hull = cross_model_hull(candidates, models, cid, model, prop)
        ratio_lo, ratio_hi = min(ratios), max(ratios)
        raw_err = float(cell["raw_abs_err"])
        corr_err = float(cell["corrected_abs_err"])
        rows.append(
            {
                "group": cell["group"],
                "candidate": cid,
                "model": model,
                "prop": prop,
                "reference": ref,
                "raw": raw,
                "corrected": corrected,
                "b": cell["b"],
                "s": cell["s"],
                "n_calibration": cell["n_calibration"],
                "raw_abs_err": raw_err,
                "corrected_abs_err": corr_err,
                "success": corr_err < raw_err,
                "tie": corr_err == raw_err,
                "true_ratio_r": ratio_r,
                "cross_model_hull": list(hull) if hull else None,
                "proxy_raw_in_cross_model_hull": (
                    hull[0] <= raw <= hull[1] if hull else None
                ),
                "proxy_corrected_in_cross_model_hull": (
                    hull[0] <= corrected <= hull[1] if hull else None
                ),
                "calibration_ratio_hull": [ratio_lo, ratio_hi],
                "oracle_ratio_in_calibration_hull": (
                    ratio_lo <= ratio_r <= ratio_hi
                ),
                "round4_cap_preview": round4_cap_preview(ratios),
            }
        )
    return tuple(rows)


# --------------------------------------------------------------------------
# dataset summaries
# --------------------------------------------------------------------------


def summarize_dataset(rows: Sequence[Mapping[str, object]]) -> dict[str, object]:
    """Pooled + per-property contingency for every predictor, one dataset."""
    predictors: dict[str, dict[str, object]] = {}
    for name, definition in PREDICTORS:
        per_prop = {}
        for prop in PROPS:
            sub = [r for r in rows if r["prop"] == prop]
            if sub:
                per_prop[prop] = contingency(sub, name)
        predictors[name] = {
            "definition": definition,
            "pooled": contingency(rows, name),
            "per_property": per_prop,
        }
    preview = [r["round4_cap_preview"] for r in rows]
    licensed = [r for r in rows if r["round4_cap_preview"]["licensed"]]
    lic_in = [r for r in licensed if r["oracle_ratio_in_calibration_hull"]]
    lic_out = [r for r in licensed if not r["oracle_ratio_in_calibration_hull"]]
    return {
        "n_applied_cells": len(rows),
        "n_success": sum(1 for r in rows if r["success"]),
        "n_failure": sum(1 for r in rows if not r["success"] and not r["tie"]),
        "n_ties": sum(1 for r in rows if r["tie"]),
        "predictors": predictors,
        "round4_cap_preview": {
            "definition": (
                "cells whose Round-3 license survives the PROVEN caps "
                "(inflation b - 1 > 2s; deflation 1 - b > 3s AND b >= 0.5)"
            ),
            "n_licensed": len(licensed),
            "n_delicensed": len(rows) - len(licensed),
            "n_inflation_side": sum(
                1 for p in preview if p["side"] == "inflation"
            ),
            "n_deflation_side": sum(
                1 for p in preview if p["side"] == "deflation"
            ),
            "licensed_success": sum(1 for r in licensed if r["success"]),
            "licensed_failure": sum(
                1 for r in licensed if not r["success"] and not r["tie"]
            ),
            "theorem_consistency": {
                "definition": (
                    "the proven theorems guarantee success on cells that are "
                    "BOTH cap-licensed AND oracle in-hull; licensed "
                    "out-of-hull cells carry no guarantee"
                ),
                "licensed_in_hull_success": sum(
                    1 for r in lic_in if r["success"]
                ),
                "licensed_in_hull_failure": sum(
                    1 for r in lic_in if not r["success"] and not r["tie"]
                ),
                "licensed_out_hull_success": sum(
                    1 for r in lic_out if r["success"]
                ),
                "licensed_out_hull_failure": sum(
                    1 for r in lic_out if not r["success"] and not r["tie"]
                ),
            },
        },
    }


# --------------------------------------------------------------------------
# input cross-checks (no silent drift between artifacts)
# --------------------------------------------------------------------------


def verify_against_round3_analysis(
    rows: Sequence[Mapping[str, object]], analysis_path: Path
) -> dict[str, object]:
    """Cross-check recomputed applied cells against round3_analysis.json."""
    payload = json.loads(Path(analysis_path).read_text(encoding="utf-8"))
    cells = payload.get("cells")
    if not isinstance(cells, list):
        raise InputValidationError(f"{analysis_path}: missing 'cells' list")
    published = {
        (c["candidate"], c["model"], c["prop"]): c
        for c in cells
        if c.get("applied")
    }
    mine = {(r["candidate"], r["model"], r["prop"]): r for r in rows}
    if set(published) != set(mine):
        raise InputValidationError(
            "recomputed applied cells disagree with round3_analysis.json: "
            f"only_published={sorted(set(published) - set(mine))} "
            f"only_recomputed={sorted(set(mine) - set(published))}"
        )
    max_dev = max(
        (
            abs(float(published[k]["corrected"]) - float(mine[k]["corrected"]))
            for k in published
        ),
        default=0.0,
    )
    if max_dev > 1e-9:
        raise InputValidationError(
            f"corrected values deviate from round3_analysis.json by {max_dev}"
        )
    return {
        "n_applied_matched": len(published),
        "max_corrected_deviation": max_dev,
        "verified": True,
    }


def crosscheck_round2_report(
    round1_report: Mapping, round2_path: Path
) -> dict[str, object]:
    """Confirm Round-2 rows' raw/ref agree with the Round-1 campaign report."""
    payload = json.loads(Path(round2_path).read_text(encoding="utf-8"))
    round2_rows = payload.get("rows")
    if not isinstance(round2_rows, list):
        raise InputValidationError(f"{round2_path}: missing 'rows' list")
    candidates: Mapping[str, Mapping] = round1_report["candidates"]
    n_checked = 0
    for row in round2_rows:
        cid, model, prop = row["candidate"], row["model"], row["prop"]
        if cid not in candidates:
            raise InputValidationError(
                f"{round2_path}: candidate {cid!r} not in round-1 report"
            )
        pred = r3.prediction(candidates[cid], model, prop)
        ref = r3.reference(candidates[cid], prop)
        if pred is None or ref is None:
            raise InputValidationError(
                f"{round2_path}: {cid}/{model}/{prop} unresolvable in round-1"
            )
        if (
            abs(pred - float(row["raw"])) > RAW_MATCH_TOLERANCE
            or abs(ref - float(row["reference"])) > RAW_MATCH_TOLERANCE
        ):
            raise InputValidationError(
                f"{round2_path}: raw/ref mismatch at {cid}/{model}/{prop}"
            )
        n_checked += 1
    return {"n_rows_crosschecked": n_checked, "verified": True}


# --------------------------------------------------------------------------
# markdown
# --------------------------------------------------------------------------


def _fmt_p(p: object) -> str:
    return f"{float(p):.4g}" if isinstance(p, (int, float)) else "n/a"


def _fmt_rate(x: object) -> str:
    return f"{float(x) * 100:.0f}%" if isinstance(x, (int, float)) else "-"


def _predictor_table_lines(
    summary: Mapping[str, object], predictor: str
) -> list[str]:
    entry: Mapping[str, object] = summary["predictors"][predictor]
    lines = [
        "| scope | in&succ | in&fail | out&succ | out&fail | "
        "succ-rate in | succ-rate out | Fisher p |",
        "|---|---|---|---|---|---|---|---|",
    ]
    scopes = [("pooled", entry["pooled"])] + [
        (prop, entry["per_property"][prop])
        for prop in PROPS
        if prop in entry["per_property"]
    ]
    for scope, con in scopes:
        t = con["table"]
        lines.append(
            f"| {scope} | {t['in_hull_success']} | {t['in_hull_failure']} | "
            f"{t['out_hull_success']} | {t['out_hull_failure']} | "
            f"{_fmt_rate(con['success_rate_in_hull'])} | "
            f"{_fmt_rate(con['success_rate_out_hull'])} | "
            f"{_fmt_p(con['fisher_p_two_sided'])} |"
        )
    return lines


def build_markdown(payload: Mapping[str, object]) -> str:
    r3s = payload["datasets"]["round3_primary"]["summary"]
    r12s = payload["datasets"]["round1_2_secondary"]["summary"]
    lines = [
        "# Prediction-hull membership vs correction success — EXPLORATORY",
        "",
        f"> **Label:** {LABEL}. No new measurements; existing Round-1/2/3",
        "> artifacts only. Does not amend any frozen registration.",
        f"> Generated {payload['generated_at']} by",
        "> `python/scripts/analyze_prediction_hull.py`.",
        "",
        "## Hypothesis",
        "",
        "The proven capped in-hull correction theorems license a correction",
        "only under an in-hull hypothesis on the target's true ratio",
        "r = pred/ref — unknowable at runtime. Tested here: whether a",
        "KNOWABLE cross-model prediction hull is a usable proxy for it, on",
        "cells where the frozen Round-3 rule APPLIED.",
        "",
        "- **(c) proxy (knowable):** model m's raw prediction inside the",
        "  other models' raw-prediction hull for the same candidate/property.",
        "- **(c2) variant (knowable):** m's LOO-bias-corrected prediction",
        "  inside that same cross-model raw-prediction hull.",
        "- **(d) oracle (unknowable):** true ratio r inside m's LOO",
        "  calibration ratio hull — the theorems' hypothesis; upper bound.",
        "- **Outcome:** success iff |corrected err| < |raw err|.",
        "",
        "## Round-3 cells (PRIMARY): proxy (c) — raw prediction in hull",
        "",
        *_predictor_table_lines(r3s, "proxy_raw_in_cross_model_hull"),
        "",
        "## Round-3 cells: variant (c2) — corrected prediction in hull",
        "",
        *_predictor_table_lines(r3s, "proxy_corrected_in_cross_model_hull"),
        "",
        "## Round-3 cells: oracle (d) — true ratio in calibration hull",
        "",
        *_predictor_table_lines(r3s, "oracle_ratio_in_calibration_hull"),
        "",
        "## Round-1/2 cells (SECONDARY, same frozen rule re-applied)",
        "",
        "### proxy (c)",
        "",
        *_predictor_table_lines(r12s, "proxy_raw_in_cross_model_hull"),
        "",
        "### oracle (d)",
        "",
        *_predictor_table_lines(r12s, "oracle_ratio_in_calibration_hull"),
        "",
        "## Reading",
        "",
        *payload["reading"],
        "",
        "## Round-4 cap preview (informative only)",
        "",
        _cap_preview_line("Round-3", r3s),
        _cap_preview_line("Round-1/2", r12s),
        "",
        "## Honesty boundary",
        "",
        "Exploratory, small n, cells within a group share calibration members",
        "and are not independent; Fisher p-values are descriptive screening",
        "numbers, not confirmatory claims. Pooled tables mix properties with",
        "very different base rates (every applied a0 cell succeeds regardless",
        "of hull status, so a0 contributes no within-property association and",
        "the pooled oracle signal is carried by the property mix plus the",
        "elastic-property cells — see the per-property rows before quoting",
        "any pooled p). Any use of the proxy must be registered before",
        "Round-4 data exists (it was not — see the Round-4 preregistration,",
        "which registers the caps alone and records this null).",
        "",
    ]
    return "\n".join(lines)


def _cap_preview_line(name: str, summary: Mapping[str, object]) -> str:
    cap = summary["round4_cap_preview"]
    tc = cap["theorem_consistency"]
    return (
        f"- {name}: {cap['n_licensed']}/{summary['n_applied_cells']} applied "
        f"cells keep their license under the proven caps "
        f"({cap['n_inflation_side']} inflation-side, "
        f"{cap['n_deflation_side']} deflation-side applied cells); "
        f"licensed cells: {cap['licensed_success']} success / "
        f"{cap['licensed_failure']} failure. Theorem consistency: licensed & "
        f"oracle-in-hull {tc['licensed_in_hull_success']} success / "
        f"{tc['licensed_in_hull_failure']} failure (the theorems guarantee "
        f"0 failures here); licensed & out-of-hull "
        f"{tc['licensed_out_hull_success']} / "
        f"{tc['licensed_out_hull_failure']} (no guarantee)."
    )


def build_reading(
    r3_summary: Mapping[str, object], r12_summary: Mapping[str, object]
) -> list[str]:
    """Plain-language verdict lines derived from the computed tables."""

    def line(name: str, summary: Mapping[str, object], predictor: str) -> str:
        con = summary["predictors"][predictor]["pooled"]
        t = con["table"]
        return (
            f"- {name}: in-hull {t['in_hull_success']}/"
            f"{t['in_hull_success'] + t['in_hull_failure']} success vs "
            f"out-of-hull {t['out_hull_success']}/"
            f"{t['out_hull_success'] + t['out_hull_failure']}; Fisher "
            f"p = {_fmt_p(con['fisher_p_two_sided'])}."
        )

    return [
        line(
            "Round-3 proxy (c), pooled",
            r3_summary,
            "proxy_raw_in_cross_model_hull",
        ),
        line(
            "Round-3 variant (c2), pooled",
            r3_summary,
            "proxy_corrected_in_cross_model_hull",
        ),
        line(
            "Round-3 oracle (d), pooled",
            r3_summary,
            "oracle_ratio_in_calibration_hull",
        ),
        line(
            "Round-1/2 proxy (c), pooled",
            r12_summary,
            "proxy_raw_in_cross_model_hull",
        ),
        line(
            "Round-1/2 oracle (d), pooled",
            r12_summary,
            "oracle_ratio_in_calibration_hull",
        ),
    ]


# --------------------------------------------------------------------------
# assembly + entry point
# --------------------------------------------------------------------------


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    cand = _REPO_ROOT / "data" / "candidates"
    parser.add_argument(
        "--round3-report", default=str(cand / "round3" / "report.json")
    )
    parser.add_argument(
        "--round3-analysis",
        default=str(cand / "round3" / "round3_analysis.json"),
        help="published Round-3 analysis, used to cross-check recomputation",
    )
    parser.add_argument(
        "--round1-report", default=str(cand / "round1" / "report.json")
    )
    parser.add_argument(
        "--round2-report",
        default=str(cand / "round2" / "report.json"),
        help="Round-2 report, used to cross-check Round-1 raw/ref values",
    )
    parser.add_argument("--out-dir", default=str(cand / "round3"))
    return parser.parse_args(argv)


def build_payload(args: argparse.Namespace) -> dict[str, object]:
    round3_report = r3.load_report(Path(args.round3_report))
    round1_report = r3.load_report(Path(args.round1_report))
    round3_rows = build_cell_rows(round3_report)
    round12_rows = build_cell_rows(round1_report)
    r3_check = verify_against_round3_analysis(
        round3_rows, Path(args.round3_analysis)
    )
    r2_check = crosscheck_round2_report(round1_report, Path(args.round2_report))
    r3_summary = summarize_dataset(round3_rows)
    r12_summary = summarize_dataset(round12_rows)
    return {
        "schema": SCHEMA,
        "label": LABEL,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "hypothesis": (
            "PREDICTION-HULL membership (knowable at runtime) predicts "
            "frozen-rule correction success; the proven theorems' ratio "
            "in-hull condition (unknowable) is the oracle upper bound."
        ),
        "frozen_rule": r3.FROZEN_RULE_TEXT,
        "inputs": {
            "round3_report": args.round3_report,
            "round3_analysis": args.round3_analysis,
            "round1_report": args.round1_report,
            "round2_report": args.round2_report,
        },
        "crosschecks": {
            "round3_analysis_match": r3_check,
            "round2_raw_ref_match": r2_check,
        },
        "datasets": {
            "round3_primary": {
                "summary": r3_summary,
                "cells": [dict(r) for r in round3_rows],
            },
            "round1_2_secondary": {
                "note": (
                    "Round-1 campaign cells re-evaluated under the frozen "
                    "Round-3 rule (LOO within group), NOT the exploratory "
                    "Round-2 sign gate; Round-2 report used as raw/ref "
                    "cross-check only."
                ),
                "summary": r12_summary,
                "cells": [dict(r) for r in round12_rows],
            },
        },
        "reading": build_reading(r3_summary, r12_summary),
    }


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        payload = build_payload(args)
    except (InputValidationError, r3.InputValidationError) as exc:
        print(f"input error: {exc}", file=sys.stderr)
        return 2
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "prediction_hull_analysis.json").write_text(
        json.dumps(payload, indent=2), encoding="utf-8"
    )
    (out_dir / "PREDICTION_HULL_ANALYSIS.md").write_text(
        build_markdown(payload), encoding="utf-8"
    )
    for line in payload["reading"]:
        print(line)
    print(f"-> {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
