#!/usr/bin/env python3
"""Direction-shift accuracy validation for the Lupine correction operator.

Honest out-of-sample (leave-one-material-out) evaluation of whether the
correction operator's shifted direction improves accuracy, per the
prespecified protocol of 2026-07-13.

Data provenance (the WSL repo holding lupine/data/targets_0K.json and
python/lupine/feedback.py is NOT present on this machine):
- Raw / ensemble / v0.1-corrected per-element predictions: recorded in
  lupine-rhizo/data/mlip-elastic-benchmark/mlip_elastic_benchmark_results.json
  (schema lupine.mlip_elastic_benchmark.v1, run 2026-06-27).
- TPBE_0K targets: reconstructed exactly as raw - raw_error, using the
  per-element raw-error table in operator-failure-diagnosis-2026-06-27.md
  (errors quoted to 0.01 GPa).
- Tr2SCAN_0K targets: per the preprint caveat, Tr2SCAN tensors are the TPBE
  tensors scaled componentwise by a per-element scalar bulk-modulus ratio
  (factor = 1.0 for Al, Ca, Sr). The factor is recovered from the diagnosis
  scalar-bulk table via shift = (corrected - raw) / alpha and a least-squares
  scalar fit of shift against TPBE.
- v0.2 LOO alphas (reference): feedback_loop_benchmark.json.

Everything else (shift-only, v0.2 scalar-bulk, v0.3 directional) is
reimplemented from the Lean specs ScalarBulkOperator.lean and
DirectionalCorrectionScheme.lean and re-fit under leave-one-material-out.

Deterministic; numpy seed set for hygiene.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np

np.random.seed(20260713)

HERE = Path(__file__).parent
RHIZO = HERE.parent.parent
RESULTS_JSON = RHIZO / "data" / "mlip-elastic-benchmark" / "mlip_elastic_benchmark_results.json"
FEEDBACK_JSON = RHIZO / "mlip-elastic-benchmark" / "feedback_loop_benchmark.json"
OUT_JSON = HERE / "results.json"

PROPS = ["c11", "c12", "c44"]

# Per-element raw TensorNet/PBE 1x1x1 errors vs TPBE_0K
# (operator-failure-diagnosis-2026-06-27.md, table "Per-element raw errors vs TPBE_0K")
ERR_RAW_TPBE = {
    "Ag": (1.02, -1.50, 8.44), "Al": (-7.88, -20.20, 3.75), "Au": (-21.14, -30.97, 12.03),
    "Ca": (-0.40, -5.43, 1.71), "Cr": (46.52, 80.54, -10.48), "Cu": (15.47, -13.30, 0.41),
    "Fe": (-26.99, -32.81, -2.13), "Mo": (-25.07, -10.11, 3.92), "Nb": (-18.01, -41.90, 6.01),
    "Ni": (-21.88, -4.17, -1.44), "Pd": (-0.57, -12.78, 5.89), "Pt": (-13.04, -29.88, 13.05),
    "Sr": (6.09, -0.13, -0.56), "Ta": (-29.16, -5.80, -20.86), "V": (30.47, -10.94, -0.40),
    "W": (-24.70, -15.89, 2.43),
}

# Scalar-bulk corrected predictions (diagnosis table "Scalar-bulk per-element alpha and predictions")
SCALAR_BULK_CORRECTED = {
    "Ag": (134.05, 96.72, 60.66), "Al": (96.05, 52.75, 35.61), "Au": (149.66, 115.43, 39.52),
    "Ca": (20.43, 9.66, 15.80), "Cr": (596.29, 233.73, 102.13), "Cu": (200.56, 152.41, 90.38),
    "Fe": (251.43, 136.41, 107.67), "Mo": (476.13, 157.35, 116.93), "Nb": (213.65, 102.45, 16.90),
    "Ni": (305.80, 185.02, 155.06), "Pd": (223.86, 163.39, 90.61), "Pt": (314.78, 224.15, 86.84),
    "Sr": (21.29, 10.36, 11.93), "Ta": (257.67, 164.71, 53.20), "V": (335.95, 134.43, 16.88),
    "W": (542.70, 207.81, 161.23),
}

CLASSES = {
    "Ag": "noble_coinage_fcc", "Al": "post_transition", "Au": "noble_coinage_fcc",
    "Ca": "alkaline_earth_fcc", "Cr": "transition_bcc", "Cu": "noble_coinage_fcc",
    "Fe": "transition_bcc", "Mo": "transition_bcc", "Nb": "transition_bcc",
    "Ni": "transition_fcc", "Pd": "transition_fcc", "Pt": "transition_fcc",
    "Sr": "alkaline_earth_fcc", "Ta": "transition_bcc", "V": "transition_bcc",
    "W": "transition_bcc",
}

ELEMENTS = sorted(ERR_RAW_TPBE)

# Reference numbers from the 2026-06-27 diagnosis, for reproduction gates.
DIAG = {
    "raw_vs_tpbe": (14.55, 13.48), "raw_vs_tr2scan": (22.55, 22.50),
    "shift_vs_tpbe": (16.28, 15.74), "shift_vs_tr2scan": (14.55, 13.48),
    "v01_vs_tpbe": (63.40, 65.33), "v01_vs_tr2scan": (54.28, 55.09),
    "v01_unshifted_vs_tpbe": (54.28, 55.09), "v01_unshifted_vs_tr2scan": (45.83, 46.05),
    "scalar_bulk_vs_tpbe": (19.17, 19.01), "scalar_bulk_vs_tr2scan": (14.13, 11.16),
    "ensemble_vs_tpbe": (11.60, 11.62), "ensemble_vs_tr2scan": (19.89, 19.65),
    "feedback_projection_none_vs_tr2scan": (13.26, 9.03),
}


def load_recorded_arms() -> dict:
    with open(RESULTS_JSON, encoding="utf-8") as f:
        data = json.load(f)
    arms: dict[str, dict[str, np.ndarray]] = {}
    for row in data["per_element"]:
        arm = arms.setdefault(row["arm"], {})
        arm[row["element"]] = np.array([row["c11"], row["c12"], row["c44"]], dtype=float)
    return arms


def load_v02_alphas() -> dict[str, float]:
    with open(FEEDBACK_JSON, encoding="utf-8") as f:
        fb = json.load(f)
    det = fb["per_element_details"]["feedback-scalar_bulk-offset-none"]
    return {el: det[el]["alpha"] for el in ELEMENTS}


def load_feedback_reference() -> dict:
    with open(FEEDBACK_JSON, encoding="utf-8") as f:
        fb = json.load(f)
    return fb["operator_scorecard"]


def reconstruct_targets(raw: dict, v02_alphas: dict) -> tuple[dict, dict, dict, dict]:
    """Return (tpbe, tr2scan, shift, factors)."""
    tpbe = {el: raw[el] - np.array(ERR_RAW_TPBE[el]) for el in ELEMENTS}
    shift, factors = {}, {}
    for el in ELEMENTS:
        shift_est = (np.array(SCALAR_BULK_CORRECTED[el]) - raw[el]) / v02_alphas[el]
        if np.linalg.norm(shift_est) < 0.5:
            factors[el] = 1.0
        else:
            factors[el] = 1.0 + float(shift_est @ tpbe[el] / (tpbe[el] @ tpbe[el]))
        shift[el] = (factors[el] - 1.0) * tpbe[el]
        resid = float(np.max(np.abs(shift[el] - shift_est)))
        if resid > 0.35:
            raise AssertionError(f"{el}: scalar-factor shift model violated (max dev {resid:.3f} GPa)")
    tr2scan = {el: tpbe[el] + shift[el] for el in ELEMENTS}
    return tpbe, tr2scan, shift, factors


def bulk(v: np.ndarray) -> float:
    return float((v[0] + 2.0 * v[1]) / 3.0)


def mae(pred: np.ndarray, target: np.ndarray) -> float:
    return float(np.mean(np.abs(pred - target)))


def agg(preds: dict, target: dict) -> tuple[float, float, dict]:
    per_el = {el: mae(preds[el], target[el]) for el in ELEMENTS}
    vals = np.array(list(per_el.values()))
    return float(vals.mean()), float(np.median(vals)), per_el


# ------------------------------ arms (LOO) ------------------------------

def arm_shift_only(raw: dict, shift: dict) -> dict:
    return {el: raw[el] + shift[el] for el in ELEMENTS}


def arm_scalar_bulk(raw: dict, shift: dict, tr2scan: dict) -> tuple[dict, dict]:
    """v0.2: LOO least-squares scalar on the bulk projection (ScalarBulkOperator.lean fit)."""
    preds, alphas = {}, {}
    for held in ELEMENTS:
        train = [el for el in ELEMENTS if el != held]
        num = sum((bulk(tr2scan[el]) - bulk(raw[el])) * bulk(shift[el]) for el in train)
        den = sum(bulk(shift[el]) ** 2 for el in train)
        a = 0.0 if den == 0 else num / den
        alphas[held] = a
        preds[held] = raw[held] + a * shift[held]
    return preds, alphas


def arm_directional(raw: dict, shift: dict, tr2scan: dict,
                    direction: str = "bulk", alpha_scope: str = "global") -> tuple[dict, dict]:
    """v0.3 directional (DirectionalCorrectionScheme.lean), LOO.

    pred = raw + shift + alpha * d, alpha least-squares-fit on training rows:
    alpha = sum_i <r_i, d> / (n_train * <d, d>), r_i = tr2scan_i - raw_i - shift_i.
    direction: 'bulk' -> d = (1, 2, 0); 'pc1' -> first right-singular vector of
    the uncentered training residual matrix; 'class_mean' -> mean training
    residual of the held-out element's class.
    alpha_scope: 'global' fits on all training rows, 'class' on same-class rows.
    """
    preds, alphas = {}, {}
    for held in ELEMENTS:
        train = [el for el in ELEMENTS if el != held]
        res = {el: tr2scan[el] - raw[el] - shift[el] for el in train}
        if direction == "bulk":
            d = np.array([1.0, 2.0, 0.0])
        elif direction == "pc1":
            mat = np.array([res[el] for el in train])
            _, _, vh = np.linalg.svd(mat, full_matrices=False)
            d = vh[0]
            if d @ np.array([1.0, 2.0, 0.0]) < 0:
                d = -d
        elif direction == "class_mean":
            rows = [res[el] for el in train if CLASSES[el] == CLASSES[held]]
            d = np.mean(rows, axis=0) if rows else np.array([1.0, 2.0, 0.0])
            if np.linalg.norm(d) < 1e-9:
                d = np.array([1.0, 2.0, 0.0])
        else:
            raise ValueError(direction)
        pool = train if alpha_scope == "global" else \
            ([el for el in train if CLASSES[el] == CLASSES[held]] or train)
        dd = float(d @ d)
        a = sum(float(res[el] @ d) for el in pool) / (len(pool) * dd)
        alphas[held] = a
        preds[held] = raw[held] + shift[held] + a * d
    return preds, alphas


def try_v01_reimplementation(raw: dict, shift: dict, tpbe: dict,
                             v01_recorded: dict) -> dict:
    """Attempt to reproduce the recorded v0.1 global-LOO-PCA predictions
    (which correspond to the UNSHIFTED bias correction raw + bias) from
    scratch; report best-matching variant. The exact WSL implementation is not
    on this machine, so this is a hypothesis scan, not ground truth."""
    variants = {}
    for centered in (False, True):
        for coeff_sign in (+1, -1):
            preds = {}
            for held in ELEMENTS:
                train = [el for el in ELEMENTS if el != held]
                errs = np.array([raw[el] - tpbe[el] for el in train])
                mat = errs - errs.mean(axis=0) if centered else errs
                _, _, vh = np.linalg.svd(mat, full_matrices=False)
                b = vh[0]
                c = float(np.mean(errs @ b))
                preds[held] = raw[held] - coeff_sign * c * b
            name = f"pca(centered={centered},sign={coeff_sign:+d})"
            dev = max(float(np.max(np.abs(preds[el] - v01_recorded[el]))) for el in ELEMENTS)
            variants[name] = dev
    best = min(variants, key=variants.get)
    return {"variants_max_abs_dev_gpa": variants, "best": best,
            "best_max_abs_dev_gpa": variants[best]}


# --------------------------- directional stats ---------------------------

def binom_two_sided(k: int, n: int) -> float:
    if n == 0:
        return float("nan")
    pk = math.comb(n, k) * 0.5 ** n
    p = sum(math.comb(n, i) * 0.5 ** n for i in range(n + 1)
            if math.comb(n, i) * 0.5 ** n <= pk + 1e-12)
    return min(1.0, p)


def directional_stats(raw: dict, preds: dict, target: dict) -> dict:
    """Property-level (16 x 3 cases): did the applied correction move the
    prediction toward the target AND shrink the absolute error?"""
    toward_and_improved = improved = worsened = ties = toward = n_active = 0
    per_class: dict[str, list[int]] = {}
    for el in ELEMENTS:
        for p in range(3):
            delta = float(preds[el][p] - raw[el][p])
            gap = float(target[el][p] - raw[el][p])
            before = abs(gap)
            after = abs(float(target[el][p] - preds[el][p]))
            if abs(delta) < 1e-9:
                ties += 1
                continue
            n_active += 1
            tw = (delta > 0) == (gap > 0) and gap != 0
            imp = after < before - 1e-12
            wor = after > before + 1e-12
            toward += tw
            improved += imp
            worsened += wor
            toward_and_improved += tw and imp
            per_class.setdefault(CLASSES[el], []).append(int(tw and imp))
    n_eff = improved + worsened
    return {
        "n_property_cases": 48, "n_active_corrections": n_active, "n_ties_zero_correction": ties,
        "frac_toward_target": toward / n_active if n_active else float("nan"),
        "frac_toward_and_improved": toward_and_improved / n_active if n_active else float("nan"),
        "n_improved": improved, "n_worsened": worsened,
        "sign_test_two_sided_p": binom_two_sided(improved, n_eff),
        "per_class_frac_toward_and_improved": {
            c: sum(v) / len(v) for c, v in sorted(per_class.items())
        },
    }


def material_level_improvement(raw: dict, preds: dict, target: dict) -> dict:
    wins = [el for el in ELEMENTS if mae(preds[el], target[el]) < mae(raw[el], target[el]) - 1e-12]
    losses = [el for el in ELEMENTS if mae(preds[el], target[el]) > mae(raw[el], target[el]) + 1e-12]
    n_eff = len(wins) + len(losses)
    return {"n_materials_improved": len(wins), "n_materials_worsened": len(losses),
            "improved_elements": wins,
            "sign_test_two_sided_p": binom_two_sided(len(wins), n_eff)}


def class_mae(preds: dict, target: dict) -> dict:
    out: dict[str, list[float]] = {}
    for el in ELEMENTS:
        out.setdefault(CLASSES[el], []).append(mae(preds[el], target[el]))
    return {c: float(np.mean(v)) for c, v in sorted(out.items())}


# --------------------------------- main ---------------------------------

def gate(name: str, got: tuple[float, float], want: tuple[float, float],
         tol: float, gates: list) -> None:
    ok = abs(got[0] - want[0]) <= tol and abs(got[1] - want[1]) <= tol
    gates.append({"gate": name, "got_mean_median": [round(got[0], 3), round(got[1], 3)],
                  "expected_mean_median": list(want), "tol_gpa": tol, "pass": bool(ok)})
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}: got ({got[0]:.2f}, {got[1]:.2f}) "
          f"expected {want} (tol {tol})")


def main() -> None:
    recorded = load_recorded_arms()
    raw = recorded["raw-1x1x1"]
    ensemble = recorded["ensemble-1x1x1"]
    v01 = recorded["corrected-1x1x1"]
    v02_alphas_ref = load_v02_alphas()
    fb_ref = load_feedback_reference()

    tpbe, tr2scan, shift, factors = reconstruct_targets(raw, v02_alphas_ref)
    print("Reconstructed Tr2SCAN/TPBE scale factors:")
    for el in ELEMENTS:
        print(f"  {el:2s} {factors[el]:.4f}")

    # Arms
    arms: dict[str, dict] = {
        "raw": dict(raw),
        "shift-only": arm_shift_only(raw, shift),
        "scalar-bulk-v0.2": None,
        "directional-v0.3-bulk-global": None,
        "v0.1-global-loo-pca-unshifted(recorded)": dict(v01),
        "v0.1-global-loo-pca(recorded+shift)": {el: v01[el] + shift[el] for el in ELEMENTS},
        "ensemble-1x1x1(recorded)": dict(ensemble),
    }
    sb_preds, sb_alphas = arm_scalar_bulk(raw, shift, tr2scan)
    arms["scalar-bulk-v0.2"] = sb_preds
    dir_preds, dir_alphas = arm_directional(raw, shift, tr2scan, "bulk", "global")
    arms["directional-v0.3-bulk-global"] = dir_preds

    # Extra directional variants (hypothesis scan vs the recorded FeedbackLoop numbers)
    dir_variants = {}
    for dname in ("bulk", "pc1", "class_mean"):
        for scope in ("global", "class"):
            preds, _ = arm_directional(raw, shift, tr2scan, dname, scope)
            m, md, per_el = agg(preds, tr2scan)
            ref = fb_ref["feedback-projection-offset-none"]["vs_Tr2SCAN"]["per_element"]
            dev = max(abs(per_el[el] - ref[el]) for el in ELEMENTS)
            dir_variants[f"{dname}/{scope}"] = {
                "mean_mae_vs_tr2scan": round(m, 3), "median_mae_vs_tr2scan": round(md, 3),
                "max_per_element_dev_from_recorded_feedback_gpa": round(dev, 3),
            }

    # Reproduction gates
    print("\nReproduction gates vs 2026-06-27 diagnosis:")
    gates: list = []
    checks = [
        ("raw vs TPBE", arms["raw"], tpbe, DIAG["raw_vs_tpbe"], 0.05),
        ("raw vs Tr2SCAN", arms["raw"], tr2scan, DIAG["raw_vs_tr2scan"], 0.10),
        ("shift-only vs TPBE", arms["shift-only"], tpbe, DIAG["shift_vs_tpbe"], 0.10),
        ("shift-only vs Tr2SCAN", arms["shift-only"], tr2scan, DIAG["shift_vs_tr2scan"], 0.10),
        ("scalar-bulk vs TPBE", arms["scalar-bulk-v0.2"], tpbe, DIAG["scalar_bulk_vs_tpbe"], 0.15),
        ("scalar-bulk vs Tr2SCAN", arms["scalar-bulk-v0.2"], tr2scan, DIAG["scalar_bulk_vs_tr2scan"], 0.15),
        ("v0.1-unshifted (recorded preds) vs TPBE", arms["v0.1-global-loo-pca-unshifted(recorded)"], tpbe, DIAG["v01_unshifted_vs_tpbe"], 0.15),
        ("v0.1-unshifted (recorded preds) vs Tr2SCAN", arms["v0.1-global-loo-pca-unshifted(recorded)"], tr2scan, DIAG["v01_unshifted_vs_tr2scan"], 0.15),
        ("v0.1 (recorded+shift) vs TPBE", arms["v0.1-global-loo-pca(recorded+shift)"], tpbe, DIAG["v01_vs_tpbe"], 0.15),
        ("v0.1 (recorded+shift) vs Tr2SCAN", arms["v0.1-global-loo-pca(recorded+shift)"], tr2scan, DIAG["v01_vs_tr2scan"], 0.15),
        ("ensemble vs TPBE", arms["ensemble-1x1x1(recorded)"], tpbe, DIAG["ensemble_vs_tpbe"], 0.05),
        ("ensemble vs Tr2SCAN", arms["ensemble-1x1x1(recorded)"], tr2scan, DIAG["ensemble_vs_tr2scan"], 0.10),
    ]
    for name, preds, tgt, want, tol in checks:
        m, md, _ = agg(preds, tgt)
        gate(name, (m, md), want, tol, gates)

    alpha_dev = max(abs(sb_alphas[el] - v02_alphas_ref[el]) for el in ELEMENTS)
    ok = alpha_dev < 0.01
    gates.append({"gate": "scalar-bulk LOO alphas match recorded v0.2 alphas",
                  "max_abs_dev": alpha_dev, "tol": 0.01, "pass": bool(ok)})
    print(f"  [{'PASS' if ok else 'FAIL'}] scalar-bulk LOO alphas vs recorded: max dev {alpha_dev:.5f}")

    v01_reimpl = try_v01_reimplementation(raw, shift, tpbe, v01)
    print(f"\nv0.1 reimplementation scan: best variant {v01_reimpl['best']} "
          f"max-abs-dev {v01_reimpl['best_max_abs_dev_gpa']:.2f} GPa vs recorded")

    # Final metrics
    results = {"protocol": {
        "date": "2026-07-13",
        "primary_target": "Tr2SCAN_0K", "secondary_target": "TPBE_0K",
        "evaluation": "leave-one-material-out over 16 cubic metals",
        "properties": PROPS,
        "aggregation": "per-element MAE over C11/C12/C44; mean and median across elements",
        "directional_agreement": "property-level: sign(correction)==sign(target-raw) AND |err_after|<|err_before|; two-sided exact sign test on improved-vs-worsened",
    }, "target_reconstruction": {
        "tpbe": {el: [round(x, 4) for x in tpbe[el]] for el in ELEMENTS},
        "tr2scan": {el: [round(x, 4) for x in tr2scan[el]] for el in ELEMENTS},
        "tr2scan_over_tpbe_factor": {el: round(factors[el], 5) for el in ELEMENTS},
    }, "reproduction_gates": gates, "arms": {}, "directional_variant_scan": dir_variants,
        "v01_reimplementation_scan": v01_reimpl,
        "scalar_bulk_alphas": {el: round(sb_alphas[el], 5) for el in ELEMENTS},
        "directional_v03_alphas": {el: round(dir_alphas[el], 4) for el in ELEMENTS},
        "recorded_feedback_projection_none_vs_tr2scan": fb_ref["feedback-projection-offset-none"]["vs_Tr2SCAN"],
    }

    print("\nPer-arm results:")
    for name, preds in arms.items():
        entry: dict = {}
        for tname, tgt in (("vs_Tr2SCAN_0K", tr2scan), ("vs_TPBE_0K", tpbe)):
            m, md, per_el = agg(preds, tgt)
            entry[tname] = {
                "mean_mae_gpa": round(m, 3), "median_mae_gpa": round(md, 3),
                "per_element_mae": {el: round(v, 3) for el, v in per_el.items()},
                "per_class_mean_mae": {c: round(v, 3) for c, v in class_mae(preds, tgt).items()},
            }
            if name != "raw":
                entry[tname]["directional_agreement"] = directional_stats(raw, preds, tgt)
                entry[tname]["material_level"] = material_level_improvement(raw, preds, tgt)
            print(f"  {name:34s} {tname:14s} mean {m:6.2f}  median {md:6.2f}")
        entry["predictions"] = {el: [round(x, 4) for x in preds[el]] for el in ELEMENTS}
        results["arms"][name] = entry

    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=1)
    print(f"\nWrote {OUT_JSON}")


if __name__ == "__main__":
    main()
