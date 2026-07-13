"""Round-3 confirmatory analysis: FROZEN-rule licensed corrections, out-of-sample.

Implements, verbatim, the frozen correction rule and criteria registered in
``docs/plans/2026-07-13-round3-preregistration.md`` (REGISTERED 2026-07-13,
frozen before any Round-3 measurement or reference sourcing). Quoting the
registration:

    ## Frozen correction rule (verbatim from Round-2 exploration + registered cap)

    For a held-out candidate X, model m, property p, class C:
    1. Calibration set = other class-C members with a non-null reference
       (never X). Require >= 2 members, else ABSTAIN.
    2. ratios_i = pred_i / ref_i over calibration members.
    3. Direction gate: apply only if ALL ratios are strictly on one side of 1,
       else ABSTAIN.
    4. **Magnitude cap (new, closes the FeNi gap):** let b = median(ratios),
       s = max(ratios) - min(ratios). ABSTAIN unless |b - 1| > s. (The learned
       bias must exceed the calibration scatter; prevents wrong-direction and
       overshoot application when the class signal is weaker than its noise.)
    5. corrected = pred / b; else corrected = pred (abstention, risk-free).

    ## Primary statistic and criteria (computed, not just stated)

    - Per group x property (references non-null): median |rel err| raw vs
      corrected; exact binomial sign test over held-out cells (ties dropped).
    - SUCCESS per group: corrected beats raw on >= 2/3 evaluable properties with
      sign-test p < 0.1. FAILURE otherwise, reported verbatim.
    - KILL condition: if the frozen rule fails both groups, the correction
      layer's scope claim narrows to "same-class lattice constants only" in all
      public material until new evidence.

Sign test: over held-out cells where the rule APPLIED, improved = corrected
|rel err| < raw |rel err|; ties dropped; with k = improved count and
X ~ Bin(n, 1/2), p = 2 * min(P(X <= k), P(X >= k)) capped at 1 (exact, via
math.comb — no scipy).

Registered-exclusion semantics: references excluded AT REGISTRATION (weak
references recorded but registered as excluded) are removed from the primary
statistic and from ALL report tables. The frozen rule's calibration set is
defined only by "non-null reference", so exclusion does NOT alter calibration
— changing that would amend the frozen rule.

Inputs:  --report      run_candidate_campaign report on the OOS candidates
                       (schema lupine.candidate_campaign.v1)
         --exclusions  optional registered-exclusions JSON:
                       {"exclusions": [{"candidate": id | "group": g,
                                        "property": p}, ...]}
Outputs: <out-dir>/round3_analysis.json and <out-dir>/ROUND3_REPORT.md.
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

PROPS: tuple[str, ...] = ("a0", "b0", "c11", "c12", "c44")
PROPERTY_UNITS: dict[str, str] = {
    "a0": "Angstrom",
    "b0": "GPa",
    "c11": "GPa",
    "c12": "GPa",
    "c44": "GPa",
}
# Frozen by the registration — not CLI-tunable.
MIN_CALIBRATION_MEMBERS = 2
ALPHA = 0.1
SUCCESS_WINS_NUMERATOR = 2
SUCCESS_WINS_DENOMINATOR = 3
PREREG_PATH = "docs/plans/2026-07-13-round3-preregistration.md"
KILL_TEXT = (
    "if the frozen rule fails both groups, the correction layer's scope claim "
    'narrows to "same-class lattice constants only" in all public material '
    "until new evidence."
)
FROZEN_RULE_TEXT = (
    "For a held-out candidate X, model m, property p, class C: "
    "(1) calibration set = other class-C members with a non-null reference "
    "(never X), require >= 2 members else ABSTAIN; "
    "(2) ratios_i = pred_i / ref_i over calibration members; "
    "(3) direction gate: apply only if ALL ratios are strictly on one side "
    "of 1, else ABSTAIN; "
    "(4) magnitude cap: b = median(ratios), s = max(ratios) - min(ratios), "
    "ABSTAIN unless |b - 1| > s; "
    "(5) corrected = pred / b; else corrected = pred (abstention, risk-free)."
)


class InputValidationError(ValueError):
    """Raised when an input artifact fails validation."""


# --------------------------------------------------------------------------
# input loading
# --------------------------------------------------------------------------


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--report",
        default=str(_REPO_ROOT / "data" / "candidates" / "round3" / "report.json"),
        help="run_candidate_campaign report.json on the Round-3 OOS candidates",
    )
    parser.add_argument(
        "--out-dir",
        default=str(_REPO_ROOT / "data" / "candidates" / "round3"),
        help="directory for round3_analysis.json and ROUND3_REPORT.md",
    )
    parser.add_argument(
        "--exclusions",
        default=None,
        help=(
            "optional registered-exclusions JSON "
            '({"exclusions": [{"candidate"|"group": ..., "property": ...}]}); '
            "excluded cells are removed from criteria and ALL report tables"
        ),
    )
    return parser.parse_args(argv)


def load_report(path: Path) -> dict:
    """Load and structurally validate a candidate-campaign report."""
    path = Path(path)
    if not path.is_file():
        raise InputValidationError(f"report file does not exist: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise InputValidationError(f"cannot read report {path}: {exc}") from exc
    if not isinstance(payload, Mapping):
        raise InputValidationError(f"{path}: report must be a JSON object")
    models = payload.get("models")
    if not isinstance(models, list) or not all(isinstance(m, str) for m in models):
        raise InputValidationError(f"{path}: 'models' must be a list of strings")
    candidates = payload.get("candidates")
    if not isinstance(candidates, Mapping) or not candidates:
        raise InputValidationError(
            f"{path}: 'candidates' must be a non-empty mapping"
        )
    for cid, cand in candidates.items():
        if not isinstance(cand, Mapping):
            raise InputValidationError(f"{path}: candidate {cid!r} must be an object")
        if not isinstance(cand.get("group"), str) or not cand["group"]:
            raise InputValidationError(
                f"{path}: candidate {cid!r} needs a non-empty 'group'"
            )
        if not isinstance(cand.get("references"), Mapping):
            raise InputValidationError(
                f"{path}: candidate {cid!r} needs a 'references' mapping"
            )
        if not isinstance(cand.get("per_model"), Mapping):
            raise InputValidationError(
                f"{path}: candidate {cid!r} needs a 'per_model' mapping"
            )
    return dict(payload)


def load_exclusions(path: Path | None) -> tuple[dict[str, str], ...]:
    """Load registered exclusions as ({'candidate'|'group': ..., 'property': p}, ...)."""
    if path is None:
        return ()
    path = Path(path)
    if not path.is_file():
        raise InputValidationError(f"exclusions file does not exist: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise InputValidationError(f"cannot read exclusions {path}: {exc}") from exc
    entries = payload.get("exclusions") if isinstance(payload, Mapping) else None
    if not isinstance(entries, list):
        raise InputValidationError(
            f"{path}: expected an object with an 'exclusions' list"
        )
    out: list[dict[str, str]] = []
    for entry in entries:
        if not isinstance(entry, Mapping):
            raise InputValidationError(f"{path}: exclusion entries must be objects")
        prop = entry.get("property")
        if prop not in PROPS:
            raise InputValidationError(
                f"{path}: exclusion property must be one of {PROPS}, got {prop!r}"
            )
        has_candidate = isinstance(entry.get("candidate"), str)
        has_group = isinstance(entry.get("group"), str)
        if has_candidate == has_group:
            raise InputValidationError(
                f"{path}: each exclusion needs exactly one of 'candidate' or "
                f"'group', got {dict(entry)!r}"
            )
        key = "candidate" if has_candidate else "group"
        out.append({key: str(entry[key]), "property": str(prop)})
    return tuple(out)


def is_excluded(
    exclusions: Sequence[Mapping[str, str]], cid: str, group: str, prop: str
) -> bool:
    return any(
        e["property"] == prop
        and (e.get("candidate") == cid or e.get("group") == group)
        for e in exclusions
    )


# --------------------------------------------------------------------------
# frozen rule
# --------------------------------------------------------------------------


def _finite(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value) if math.isfinite(float(value)) else None


def prediction(candidate: Mapping, model: str, prop: str) -> float | None:
    rec = candidate.get("per_model", {}).get(model)
    if not isinstance(rec, Mapping) or "error" in rec:
        return None
    props = rec.get("properties")
    if not isinstance(props, Mapping):
        return None
    return _finite(props.get(prop))


def reference(candidate: Mapping, prop: str) -> float | None:
    ref = _finite(candidate.get("references", {}).get(prop))
    if ref is None or ref == 0.0:
        return None  # null / non-finite / zero references cannot form ratios
    return ref


def calibration_ratios(
    candidates: Mapping[str, Mapping],
    members: Sequence[str],
    held_out: str,
    model: str,
    prop: str,
) -> tuple[float, ...]:
    """ratios_i = pred_i / ref_i over the other group members (never held_out)."""
    ratios: list[float] = []
    for other in members:
        if other == held_out:
            continue
        ref = reference(candidates[other], prop)
        pred = prediction(candidates[other], model, prop)
        if ref is not None and pred is not None:
            ratios.append(pred / ref)
    return tuple(ratios)


def apply_frozen_rule(
    pred: float, ratios: Sequence[float]
) -> dict[str, object]:
    """Apply the frozen registered rule to one held-out cell.

    Returns an immutable-per-call dict:
    corrected, applied, abstain_reason (None | 'insufficient_calibration' |
    'direction' | 'magnitude_cap'), b, s, n_calibration.
    """
    n = len(ratios)
    if n < MIN_CALIBRATION_MEMBERS:
        return {
            "corrected": pred,
            "applied": False,
            "abstain_reason": "insufficient_calibration",
            "b": None,
            "s": None,
            "n_calibration": n,
        }
    b = statistics.median(ratios)
    s = max(ratios) - min(ratios)
    one_side = all(r > 1.0 for r in ratios) or all(r < 1.0 for r in ratios)
    if not one_side:
        reason = "direction"
    elif not (abs(b - 1.0) > s):
        reason = "magnitude_cap"
    else:
        reason = None
    return {
        "corrected": pred / b if reason is None else pred,
        "applied": reason is None,
        "abstain_reason": reason,
        "b": b,
        "s": s,
        "n_calibration": n,
    }


# --------------------------------------------------------------------------
# exact sign test (no scipy)
# --------------------------------------------------------------------------


def exact_binomial_sign_p(n_improved: int, n_worsened: int) -> float | None:
    """Exact two-sided sign-test p; ties already dropped.

    X ~ Bin(n, 1/2), k = n_improved:
    p = 2 * min(P(X <= k), P(X >= k)), capped at 1. None when n == 0.
    """
    if n_improved < 0 or n_worsened < 0:
        raise InputValidationError("sign-test counts must be non-negative")
    n = n_improved + n_worsened
    if n == 0:
        return None
    k = n_improved
    total = 2**n
    p_le = sum(math.comb(n, i) for i in range(0, k + 1)) / total
    p_ge = sum(math.comb(n, i) for i in range(k, n + 1)) / total
    return min(1.0, 2.0 * min(p_le, p_ge))


# --------------------------------------------------------------------------
# cell evaluation and per-(group x property) summaries
# --------------------------------------------------------------------------


def evaluate_cells(
    report: Mapping, exclusions: Sequence[Mapping[str, str]]
) -> tuple[dict[str, object], ...]:
    """One row per evaluable held-out cell (candidate x model x property).

    Evaluable = the held-out candidate's own reference is non-null and the
    (candidate, property) is not excluded at registration; excluded cells are
    omitted from criteria and ALL report tables per the registration.
    """
    candidates: Mapping[str, Mapping] = report["candidates"]
    models: Sequence[str] = report["models"]
    groups: dict[str, list[str]] = {}
    for cid in sorted(candidates):
        groups.setdefault(str(candidates[cid]["group"]), []).append(cid)

    cells: list[dict[str, object]] = []
    for group in sorted(groups):
        members = groups[group]
        for cid in members:
            for prop in PROPS:
                if is_excluded(exclusions, cid, group, prop):
                    continue
                ref = reference(candidates[cid], prop)
                if ref is None:
                    continue
                for model in models:
                    pred = prediction(candidates[cid], model, prop)
                    if pred is None:
                        continue
                    ratios = calibration_ratios(candidates, members, cid, model, prop)
                    outcome = apply_frozen_rule(pred, ratios)
                    corrected = float(outcome["corrected"])  # type: ignore[arg-type]
                    raw_rel = abs(pred - ref) / abs(ref)
                    corr_rel = abs(corrected - ref) / abs(ref)
                    cells.append(
                        {
                            "group": group,
                            "candidate": cid,
                            "model": model,
                            "prop": prop,
                            "unit": PROPERTY_UNITS[prop],
                            "reference": ref,
                            "raw": pred,
                            "corrected": corrected,
                            "applied": outcome["applied"],
                            "abstain_reason": outcome["abstain_reason"],
                            "b": outcome["b"],
                            "s": outcome["s"],
                            "n_calibration": outcome["n_calibration"],
                            "raw_abs_rel_err": raw_rel,
                            "corrected_abs_rel_err": corr_rel,
                            "raw_abs_err": abs(pred - ref),
                            "corrected_abs_err": abs(corrected - ref),
                        }
                    )
    return tuple(cells)


def summarize_group_property(
    cells: Sequence[Mapping[str, object]], group: str, prop: str
) -> dict[str, object] | None:
    """Arm summary for one (group x property); None when no evaluable cells."""
    sel = [c for c in cells if c["group"] == group and c["prop"] == prop]
    if not sel:
        return None
    applied = [c for c in sel if c["applied"]]
    n_improved = sum(
        1 for c in applied if c["corrected_abs_rel_err"] < c["raw_abs_rel_err"]
    )
    n_worsened = sum(
        1 for c in applied if c["corrected_abs_rel_err"] > c["raw_abs_rel_err"]
    )
    n_ties = len(applied) - n_improved - n_worsened
    p = exact_binomial_sign_p(n_improved, n_worsened)
    med_raw = statistics.median(c["raw_abs_rel_err"] for c in sel)
    med_corr = statistics.median(c["corrected_abs_rel_err"] for c in sel)
    beats = med_corr < med_raw
    win = beats and p is not None and p < ALPHA
    if win:
        verdict = "WIN"
    elif beats:
        verdict = "IMPROVED-NS"
    elif med_corr == med_raw:
        verdict = "NO-CHANGE"
    else:
        verdict = "WORSE"
    reasons = {"insufficient_calibration": 0, "direction": 0, "magnitude_cap": 0}
    for c in sel:
        if c["abstain_reason"] is not None:
            reasons[str(c["abstain_reason"])] += 1
    return {
        "n_materials": len({c["candidate"] for c in sel}),
        "n_cells": len(sel),
        "n_applied": len(applied),
        "n_abstained": len(sel) - len(applied),
        "abstain_reasons": reasons,
        "unit": PROPERTY_UNITS[prop],
        "median_abs_rel_err_raw": med_raw,
        "median_abs_rel_err_corrected": med_corr,
        "median_abs_err_raw": statistics.median(c["raw_abs_err"] for c in sel),
        "median_abs_err_corrected": statistics.median(
            c["corrected_abs_err"] for c in sel
        ),
        "sign_test": {
            "n_applied": len(applied),
            "n_improved": n_improved,
            "n_worsened": n_worsened,
            "n_ties_dropped": n_ties,
            "n_effective": n_improved + n_worsened,
            "p_two_sided": p,
        },
        "beats_raw": beats,
        "win": win,
        "verdict": verdict,
    }


def group_success(properties: Mapping[str, Mapping[str, object]]) -> dict[str, object]:
    """Registered criterion: WIN on >= 2/3 of evaluable properties."""
    n_eval = len(properties)
    n_wins = sum(1 for entry in properties.values() if entry["win"])
    passed = (
        n_eval > 0
        and SUCCESS_WINS_DENOMINATOR * n_wins >= SUCCESS_WINS_NUMERATOR * n_eval
    )
    return {
        "n_evaluable_properties": n_eval,
        "n_wins": n_wins,
        "criterion": (
            "corrected beats raw (median |rel err|) on >= 2/3 of evaluable "
            f"properties with sign-test p < {ALPHA}"
        ),
        "verdict": "PASS" if passed else "FAIL",
    }


def group_risk_coverage(
    candidates: Mapping[str, Mapping], group: str
) -> dict[str, object] | None:
    """Within-group risk-coverage from campaign gate verdicts, when present."""
    verdicts = [
        str(c["verdict"])
        for c in candidates.values()
        if c.get("group") == group and isinstance(c.get("verdict"), str)
    ]
    if not verdicts:
        return None
    n = len(verdicts)
    n_certified = verdicts.count("CERTIFIED")
    n_flagged = verdicts.count("FLAGGED")
    n_refused = verdicts.count("REFUSED")
    return {
        "n_candidates": n,
        "n_certified": n_certified,
        "n_flagged": n_flagged,
        "n_refused": n_refused,
        "n_issued": n_certified + n_flagged,
        "coverage_issued_fraction": (n_certified + n_flagged) / n,
    }


# --------------------------------------------------------------------------
# analysis assembly
# --------------------------------------------------------------------------


def build_analysis(
    report: Mapping,
    exclusions: Sequence[Mapping[str, str]],
    report_path: str,
    exclusions_path: str | None,
) -> dict[str, object]:
    cells = evaluate_cells(report, exclusions)
    group_names = sorted({str(c["group"]) for c in cells})
    groups: dict[str, dict[str, object]] = {}
    for group in group_names:
        properties: dict[str, dict[str, object]] = {}
        for prop in PROPS:
            entry = summarize_group_property(cells, group, prop)
            if entry is not None:
                properties[prop] = entry
        groups[group] = {
            "properties": properties,
            **group_success(properties),
            "risk_coverage": group_risk_coverage(report["candidates"], group),
        }
    all_fail = bool(groups) and all(g["verdict"] == "FAIL" for g in groups.values())
    kill = {
        "registered_text": KILL_TEXT,
        "n_groups_evaluated": len(groups),
        "triggered": all_fail,
        "note": (
            "KILL condition triggered: the frozen rule failed all evaluated groups."
            if all_fail
            else "KILL condition not triggered: at least one group PASSED."
        )
        if groups
        else "No evaluable groups; KILL condition not evaluated.",
    }
    return {
        "schema": "lupine.round3_analysis.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "report": report_path,
        "preregistration": PREREG_PATH,
        "frozen_rule": FROZEN_RULE_TEXT,
        "alpha": ALPHA,
        "min_calibration_members": MIN_CALIBRATION_MEMBERS,
        "exclusions": {
            "file": exclusions_path,
            "entries": [dict(e) for e in exclusions],
        },
        "groups": groups,
        "kill_condition": kill,
        "cells": [dict(c) for c in cells],
    }


# --------------------------------------------------------------------------
# markdown report
# --------------------------------------------------------------------------


def _fmt_pct(x: object) -> str:
    return f"{float(x) * 100:.2f}%" if isinstance(x, (int, float)) else "-"


def _fmt_abs(x: object, unit: str) -> str:
    return f"{float(x):.4g} {unit}" if isinstance(x, (int, float)) else "-"


def _fmt_p(p: object) -> str:
    return f"{float(p):.4g}" if isinstance(p, (int, float)) else "n/a"


def build_markdown(analysis: Mapping[str, object]) -> str:
    groups: Mapping[str, Mapping[str, object]] = analysis["groups"]  # type: ignore[assignment]
    lines = [
        "# Round-3 confirmatory analysis — frozen-rule corrections, out-of-sample",
        "",
        f"Generated {analysis['generated_at']} from `{analysis['report']}`.",
        f"Preregistration (FROZEN): `{analysis['preregistration']}`.",
        "",
        f"Frozen rule: {analysis['frozen_rule']}",
        "",
        "## Per-material n (materials, NOT cells — read this first)",
        "",
        "Cells multiply materials by models; the material count below is the",
        "honest sample size per group x property.",
        "",
        "| group | " + " | ".join(PROPS) + " |",
        "|---|" + "---|" * len(PROPS),
    ]
    for group, gdata in groups.items():
        props: Mapping[str, Mapping[str, object]] = gdata["properties"]  # type: ignore[assignment]
        lines.append(
            f"| {group} | "
            + " | ".join(
                str(props[p]["n_materials"]) if p in props else "0" for p in PROPS
            )
            + " |"
        )
    lines += [
        "",
        "## Arm table (per group x property)",
        "",
        "Medians over evaluable held-out cells; sign test over cells where the",
        "rule APPLIED (ties dropped). Absolute-unit deltas alongside relative.",
        "",
        "| group | prop | n_mat | n_cells | n_applied | n_abstained | "
        "median \\|rel err\\| raw | median \\|rel err\\| corrected | "
        "median \\|abs err\\| raw | median \\|abs err\\| corrected | "
        "sign-test p | verdict |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for group, gdata in groups.items():
        props = gdata["properties"]  # type: ignore[assignment]
        for prop, e in props.items():
            unit = str(e["unit"])
            lines.append(
                f"| {group} | {prop} | {e['n_materials']} | {e['n_cells']} | "
                f"{e['n_applied']} | {e['n_abstained']} | "
                f"{_fmt_pct(e['median_abs_rel_err_raw'])} | "
                f"{_fmt_pct(e['median_abs_rel_err_corrected'])} | "
                f"{_fmt_abs(e['median_abs_err_raw'], unit)} | "
                f"{_fmt_abs(e['median_abs_err_corrected'], unit)} | "
                f"{_fmt_p(e['sign_test']['p_two_sided'])} | {e['verdict']} |"
            )
    lines += [
        "",
        "## Registered criteria — group verdicts",
        "",
    ]
    for group, gdata in groups.items():
        lines.append(
            f"- **{group}: {gdata['verdict']}** — {gdata['n_wins']} WIN of "
            f"{gdata['n_evaluable_properties']} evaluable properties "
            f"(criterion: {gdata['criterion']})."
        )
    kill: Mapping[str, object] = analysis["kill_condition"]  # type: ignore[assignment]
    lines += [
        "",
        "## Registered KILL evaluation",
        "",
        f"- Registered condition: {kill['registered_text']}",
        f"- Outcome: **{'TRIGGERED' if kill['triggered'] else 'NOT TRIGGERED'}** "
        f"— {kill['note']}",
        "",
        "## Within-group risk-coverage (gate verdicts)",
        "",
    ]
    coverage_rows = [
        (group, gdata["risk_coverage"])
        for group, gdata in groups.items()
        if gdata["risk_coverage"] is not None
    ]
    if coverage_rows:
        lines += [
            "| group | n | certified | flagged | refused | issued coverage |",
            "|---|---|---|---|---|---|",
        ]
        for group, rc in coverage_rows:
            lines.append(
                f"| {group} | {rc['n_candidates']} | {rc['n_certified']} | "
                f"{rc['n_flagged']} | {rc['n_refused']} | "
                f"{_fmt_pct(rc['coverage_issued_fraction'])} |"
            )
    else:
        lines.append("No gate verdict data present in the campaign report.")
    lines += [
        "",
        "## Abstention reasons (per group x property)",
        "",
        "| group | prop | insufficient_calibration | direction | magnitude_cap |",
        "|---|---|---|---|---|",
    ]
    for group, gdata in groups.items():
        props = gdata["properties"]  # type: ignore[assignment]
        for prop, e in props.items():
            r = e["abstain_reasons"]
            lines.append(
                f"| {group} | {prop} | {r['insufficient_calibration']} | "
                f"{r['direction']} | {r['magnitude_cap']} |"
            )
    exclusions: Mapping[str, object] = analysis["exclusions"]  # type: ignore[assignment]
    entries = exclusions["entries"]
    lines += [
        "",
        "## Registered exclusions",
        "",
        (
            "None registered."
            if not entries
            else "Excluded from criteria and ALL tables above: "
            + "; ".join(
                f"{e.get('candidate', e.get('group'))} x {e['property']}"
                for e in entries  # type: ignore[union-attr]
            )
        ),
        "",
        "## Honesty boundary",
        "",
        "n per group is small (see per-material table); this is a methodology",
        "demonstration under the registered rule, not a general efficacy claim.",
        "",
    ]
    return "\n".join(lines)


# --------------------------------------------------------------------------
# entry point
# --------------------------------------------------------------------------


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        report = load_report(Path(args.report))
        exclusions = load_exclusions(
            Path(args.exclusions) if args.exclusions else None
        )
    except InputValidationError as exc:
        print(f"input error: {exc}", file=sys.stderr)
        return 2
    analysis = build_analysis(report, exclusions, args.report, args.exclusions)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "round3_analysis.json").write_text(
        json.dumps(analysis, indent=2), encoding="utf-8"
    )
    (out_dir / "ROUND3_REPORT.md").write_text(
        build_markdown(analysis), encoding="utf-8"
    )
    groups: Mapping[str, Mapping[str, object]] = analysis["groups"]  # type: ignore[assignment]
    for group, gdata in groups.items():
        print(
            f"{group}: {gdata['verdict']} "
            f"({gdata['n_wins']}/{gdata['n_evaluable_properties']} WIN)"
        )
    kill: Mapping[str, object] = analysis["kill_condition"]  # type: ignore[assignment]
    print(
        "KILL condition: "
        + ("TRIGGERED" if kill["triggered"] else "not triggered")
        + f" -> {out_dir}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
