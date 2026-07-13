"""Blind re-derivation of the Round-3 confirmatory analysis.

Written WITHOUT reading run_round3_analysis.py, round3_analysis.json,
ROUND3_REPORT.md, or prediction_hull_analysis.json.

Inputs (the only files consulted):
  - docs/plans/2026-07-13-round3-preregistration.md  (frozen protocol)
  - data/candidates/round3/report.json               (raw per-model predictions;
    ONLY candidates[*].per_model[*].properties and candidates[*].group used)
  - data/candidates/round3_targets.json              (reference values + kinds)

Frozen rule (prereg, verbatim logic):
  1. calibration = other same-group members with non-null, non-excluded
     reference (kind != 'other'); require >= 2 members, else ABSTAIN
  2. ratios_i = pred_i / ref_i over calibration members (same model, property)
  3. direction gate: ALL ratios strictly one side of 1, else ABSTAIN
  4. magnitude cap: b = median(ratios), s = max - min; ABSTAIN unless |b-1| > s
  5. corrected = pred / b, else corrected = pred

Statistics: exact two-sided binomial sign test (math.comb), Fisher exact
two-sided via hypergeometric (math.comb).  No scipy.
"""
import json
import math
import statistics
from pathlib import Path

RHIZO = Path(r"C:\Users\alexw\Downloads\lupine-rhizo")
OUT_DIR = RHIZO / "data" / "verification" / "blind_rederivation"
PROPS = ["a0", "b0", "c11", "c12", "c44"]


# ----------------------------------------------------------------- statistics
def sign_test_two_sided(wins: int, losses: int):
    """Exact two-sided binomial sign test, p0 = 1/2, ties already dropped."""
    n = wins + losses
    if n == 0:
        return None
    m = min(wins, losses)
    tail = sum(math.comb(n, i) for i in range(m + 1)) / 2 ** n
    return min(1.0, 2.0 * tail)


def fisher_exact_two_sided(a: int, b: int, c: int, d: int):
    """Two-sided Fisher exact for [[a,b],[c,d]] via hypergeometric.

    p = sum of P(table) over all tables with the same margins whose
    probability <= P(observed).  Integer arithmetic throughout.
    """
    r1, r2, c1, n = a + b, c + d, a + c, a + b + c + d
    if n == 0:
        return None
    lo, hi = max(0, c1 - r2), min(r1, c1)
    num = {k: math.comb(r1, k) * math.comb(r2, c1 - k) for k in range(lo, hi + 1)}
    obs = num[a]
    total = math.comb(n, c1)
    return sum(v for v in num.values() if v <= obs) / total


# ------------------------------------------------------------------- loading
def load_inputs():
    rep = json.loads((RHIZO / "data/candidates/round3/report.json").read_text())
    tgt = json.loads((RHIZO / "data/candidates/round3_targets.json").read_text())
    refs = {}   # (cand, prop) -> {"value": float, "kind": str} or None
    for cand in tgt["candidates"]:
        for p in PROPS:
            r = cand["references"].get(p)
            if r is None or r.get("value") is None:
                refs[(cand["id"], p)] = None
            else:
                refs[(cand["id"], p)] = {"value": r["value"], "kind": r["kind"]}
    preds = {}  # (cand, model, prop) -> float
    groups = {}
    models = rep["models"]
    for cid, c in rep["candidates"].items():
        groups[cid] = c["group"]
        for m in models:
            for p in PROPS:
                preds[(cid, m, p)] = c["per_model"][m]["properties"][p]
    return models, groups, refs, preds


def usable(ref):
    """Reference usable for criteria/calibration: non-null and not weak."""
    return ref is not None and ref["kind"] != "other"


# ------------------------------------------------------------- frozen rule
def evaluate_cell(cid, model, prop, group_members, refs, preds):
    """Apply the frozen correction rule to one (candidate, model, property)."""
    ref = refs[(cid, prop)]
    pred = preds[(cid, model, prop)]
    cal = [
        other for other in group_members
        if other != cid and usable(refs[(other, prop)])
    ]
    ratios = [preds[(o, model, prop)] / refs[(o, prop)]["value"] for o in cal]
    cell = {
        "candidate": cid, "model": model, "property": prop,
        "pred": pred, "ref": ref["value"], "ref_kind": ref["kind"],
        "calibration_members": cal, "calibration_ratios": ratios,
        "applied": False, "abstain_reason": None,
        "b_median_ratio": None, "s_spread": None,
    }
    if len(cal) < 2:
        cell["abstain_reason"] = "fewer_than_2_calibration_members"
    else:
        one_side = all(r > 1 for r in ratios) or all(r < 1 for r in ratios)
        b = statistics.median(ratios)
        s = max(ratios) - min(ratios)
        cell["b_median_ratio"], cell["s_spread"] = b, s
        if not one_side:
            cell["abstain_reason"] = "direction_gate_ratios_straddle_1"
        elif not (abs(b - 1.0) > s):
            cell["abstain_reason"] = "magnitude_cap_bias_not_exceed_spread"
        else:
            cell["applied"] = True
    corrected = pred / cell["b_median_ratio"] if cell["applied"] else pred
    rv = ref["value"]
    cell["corrected"] = corrected
    cell["raw_rel_err"] = abs(pred - rv) / abs(rv)
    cell["corr_rel_err"] = abs(corrected - rv) / abs(rv)
    return cell


# ----------------------------------------------------------------- pipeline
def run():
    models, groups, refs, preds = load_inputs()
    group_names = sorted(set(groups.values()))
    members = {g: [c for c, gg in groups.items() if gg == g] for g in group_names}

    cells = []
    for g in group_names:
        for prop in PROPS:
            for cid in members[g]:
                if not usable(refs[(cid, prop)]):
                    continue  # weak/null ref: excluded from ALL tables
                for m in models:
                    cell = evaluate_cell(cid, m, prop, members[g], refs, preds)
                    cell["group"] = g
                    cells.append(cell)

    # ---- (1) per group x property tables
    tables = {}
    for g in group_names:
        tables[g] = {}
        for prop in PROPS:
            cs = [c for c in cells if c["group"] == g and c["property"] == prop]
            if not cs:
                tables[g][prop] = {"n_cells": 0, "note": "no usable references"}
                continue
            applied = [c for c in cs if c["applied"]]
            wins = sum(1 for c in applied if c["corr_rel_err"] < c["raw_rel_err"])
            losses = sum(1 for c in applied if c["corr_rel_err"] > c["raw_rel_err"])
            ties = len(applied) - wins - losses
            p = sign_test_two_sided(wins, losses)
            tables[g][prop] = {
                "n_cells": len(cs),
                "n_applied": len(applied),
                "n_abstained": len(cs) - len(applied),
                "abstain_reasons": sorted(
                    {c["abstain_reason"] for c in cs if not c["applied"]}
                ),
                "median_abs_rel_err_raw_all_cells": statistics.median(
                    [c["raw_rel_err"] for c in cs]
                ),
                "median_abs_rel_err_corrected_all_cells": statistics.median(
                    [c["corr_rel_err"] for c in cs]
                ),
                "median_abs_rel_err_raw_applied_only": (
                    statistics.median([c["raw_rel_err"] for c in applied])
                    if applied else None
                ),
                "median_abs_rel_err_corrected_applied_only": (
                    statistics.median([c["corr_rel_err"] for c in applied])
                    if applied else None
                ),
                "sign_test": {
                    "wins_corrected_better": wins,
                    "losses_corrected_worse": losses,
                    "ties_dropped": ties,
                    "n_effective": wins + losses,
                    "p_two_sided_exact": p,
                },
            }

    # ---- (2) group PASS/FAIL + kill condition
    verdicts = {}
    for g in group_names:
        evaluable, prop_beats = [], []
        for prop in PROPS:
            t = tables[g][prop]
            if t.get("n_cells", 0) == 0:
                continue
            st = t["sign_test"]
            if st["n_effective"] == 0:
                continue  # no non-tied applied comparisons: not evaluable
            evaluable.append(prop)
            beats = (
                st["wins_corrected_better"] > st["losses_corrected_worse"]
                and st["p_two_sided_exact"] < 0.1
            )
            if beats:
                prop_beats.append(prop)
        n_ev, n_beat = len(evaluable), len(prop_beats)
        pass_fraction = n_ev > 0 and (n_beat / n_ev) >= 2 / 3
        pass_2of3 = n_beat >= 2  # literal "2 of 3" reading
        verdicts[g] = {
            "evaluable_properties": evaluable,
            "properties_where_corrected_beats_raw_p_lt_0.1": prop_beats,
            "n_evaluable": n_ev,
            "n_beats": n_beat,
            "PASS_fraction_reading (beats/evaluable >= 2/3)": pass_fraction,
            "PASS_literal_2_of_3_reading (beats >= 2)": pass_2of3,
            "verdict": "PASS" if pass_fraction else "FAIL",
        }
    both_fail = all(v["verdict"] == "FAIL" for v in verdicts.values())
    kill = {
        "both_groups_fail": both_fail,
        "kill_condition_triggered": both_fail,
        "consequence_if_triggered": (
            "correction-layer scope claim narrows to "
            "'same-class lattice constants only' in all public material"
        ),
    }

    # ---- (3) hull hypothesis on APPLIED cells
    applied_cells = [c for c in cells if c["applied"]]
    for c in applied_cells:
        others = [
            preds[(c["candidate"], m, c["property"])]
            for m in models if m != c["model"]
        ]
        c["success"] = c["corr_rel_err"] < c["raw_rel_err"]
        c["proxy_inside_other_models_hull"] = (
            min(others) <= c["pred"] <= max(others)
        )
        r_true = c["pred"] / c["ref"]
        rl, rh = min(c["calibration_ratios"]), max(c["calibration_ratios"])
        c["true_ratio"] = r_true
        c["oracle_inside_loo_ratio_hull"] = rl <= r_true <= rh

    def two_by_two(flag_key):
        a = sum(1 for c in applied_cells if c[flag_key] and c["success"])
        b = sum(1 for c in applied_cells if c[flag_key] and not c["success"])
        cc = sum(1 for c in applied_cells if not c[flag_key] and c["success"])
        d = sum(1 for c in applied_cells if not c[flag_key] and not c["success"])
        return {
            "inside_success": a, "inside_fail": b,
            "outside_success": cc, "outside_fail": d,
            "fisher_exact_p_two_sided": fisher_exact_two_sided(a, b, cc, d),
        }

    hull = {
        "n_applied_cells": len(applied_cells),
        "n_success": sum(1 for c in applied_cells if c["success"]),
        "proxy_vs_success": two_by_two("proxy_inside_other_models_hull"),
        "oracle_vs_success": two_by_two("oracle_inside_loo_ratio_hull"),
        "note": "hull membership inclusive of endpoints; "
                "proxy hull = other 3 models' raw predictions, same cand+prop; "
                "oracle hull = this cell's LOO calibration ratios",
    }
    hull["per_group"] = {}
    for g in group_names:
        gc = [c for c in applied_cells if c["group"] == g]
        hull["per_group"][g] = {
            "n_applied": len(gc),
            "n_success": sum(1 for c in gc if c["success"]),
        }

    results = {
        "schema": "lupine.round3_blind_rederivation.v1",
        "blinding": "produced before reading any Round-3 analysis output",
        "inputs": [
            "docs/plans/2026-07-13-round3-preregistration.md",
            "data/candidates/round3/report.json (per_model.properties + group only)",
            "data/candidates/round3_targets.json",
        ],
        "models": models,
        "excluded_reference_cells": [
            {"candidate": cid, "property": p, "reason": f"kind={r['kind']}"}
            for (cid, p), r in refs.items()
            if r is not None and not usable(r)
        ] + [
            {"candidate": cid, "property": p, "reason": "null"}
            for (cid, p), r in refs.items() if r is None
        ],
        "per_group_property": tables,
        "group_verdicts": verdicts,
        "kill_condition": kill,
        "hull_hypothesis": hull,
        "cells": cells,
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "results.json").write_text(json.dumps(results, indent=1))

    # console summary
    for g in group_names:
        print(f"\n=== {g} ===")
        for prop in PROPS:
            t = tables[g][prop]
            if t.get("n_cells", 0) == 0:
                print(f"  {prop}: no usable refs")
                continue
            st = t["sign_test"]
            print(
                f"  {prop}: n={t['n_cells']} applied={t['n_applied']} "
                f"abstain={t['n_abstained']} | med raw="
                f"{t['median_abs_rel_err_raw_all_cells']:.4f} "
                f"corr={t['median_abs_rel_err_corrected_all_cells']:.4f} | "
                f"appliedmed raw={t['median_abs_rel_err_raw_applied_only']} "
                f"corr={t['median_abs_rel_err_corrected_applied_only']} | "
                f"sign {st['wins_corrected_better']}W/"
                f"{st['losses_corrected_worse']}L p={st['p_two_sided_exact']}"
            )
        print("  verdict:", json.dumps(verdicts[g]))
    print("\nkill:", json.dumps(kill))
    print("\nhull:", json.dumps({k: v for k, v in hull.items() if k != 'per_group'}, indent=1))
    print("per-group applied:", json.dumps(hull["per_group"]))


if __name__ == "__main__":
    run()
