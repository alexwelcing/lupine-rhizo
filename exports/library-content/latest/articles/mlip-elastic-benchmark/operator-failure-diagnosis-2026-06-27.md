# Lupine Projection Law Operator Failure Diagnosis — Layer-2 MLIP Benchmark

**Date:** 2026-06-27

**Scope:** 16 cubic elemental metals; TensorNet/PBE 1×1×1 predictions vs. TPBE_0K / Tr2SCAN_0K targets.

**Sources:**
- `lupine/data/targets_0K.json`
- `lupine/data/mlip_elastic_benchmark_outputs_1x1x1_16elem/`
- `lupine/data/distill_inputs/layer1_bias_vectors.json`

## Executive Summary

- The v0.1 global LOO-PCA operator **fails on this MLIP set**. Against the headline TPBE_0K target it degrades mean MAE from 14.55 GPa (raw) to **63.40 GPa**, and against the Tr2SCAN_0K corrected target it degrades from 22.55 GPa to **54.28 GPa**. It cannot beat the 3-architecture PBE ensemble (11.60 GPa vs TPBE).
- The headline cost-accuracy claim (corrected single model beats 3× ensemble at ~5× lower cost) is therefore **not supported** by the v0.1 global operator on this benchmark.
- The recommended v0.2 operator on the intended corrected target (Tr2SCAN_0K) is **scalar-bulk**, with mean MAE 14.13 GPa vs Tr2SCAN (raw 22.55 GPa, shift-only 14.55 GPa, ensemble 19.89 GPa) at the same single-run cost. It is 2.70× cheaper than the ensemble and 3.86× cheaper than the 3×3×3 reference.
- Cell-size independence is confirmed: `scalar-bulk` fit on the 3×3×3 grid gives mean MAE 14.14 GPa vs Tr2SCAN, essentially identical to the 1×1×1 result.
- Seed variance is negligible: a 4-element, 3-seed variance subset (Ca, Cu, Fe, Cr) shows TensorNet/PBE 1×1×1 is deterministic, with MAE standard deviations ~0 GPa.
- Cost for all 1×1×1 single-model operators is identical: 48.3 s total for TensorNet/PBE 1×1×1 (0.0134 core-hours at 1 core/run).

## Why the Global Operator Failed

The v0.1 operator assumes a single, shared 1D error direction across all 16 elements. The data refute this:

- The error matrix has singular values [132.85, 54.14, 24.78] GPa, participation ratio 2.12, and effective rank 3. It is **not low-rank**; a single global PC explains only part of the variance.
- The first principal component ([0.57, 0.81, -0.11]) is dominated by C11/C12 (bulk-like) error and is essentially the Cr-error direction. It therefore over-corrects elements whose error geometry differs (noble metals, some BCC transition metals).
- Errors are **bonding-class specific**, not element-generic. The MLIP global error cloud stratifies cleanly by class (see Fig. 2), whereas Layer-1 classical bias vectors were low-rank *within* a family.
- The functional shift (Tr2SCAN − TPBE) is element-specific and already removes much of the systematic stiffness bias. Adding a global bias vector on top of the shift double-counts structure on classes where the residual bias is small (noble metals) or points in a different direction (BCC).

## Error-Geometry Diagnostics

### TensorNet/PBE error matrix (vs TPBE_0K)

- Singular values: `[132.84506818736944, 54.135811599011426, 24.780801715834333]`
- Participation ratio: **2.116**
- Effective rank: **3**
- First PC (C11, C12, C44): **[0.5726741012529919, 0.8121764674121165, -0.11141705226783469]**

### Per-element raw errors vs TPBE_0K

| Element | Class | C11 err | C12 err | C44 err | MAE |
|---------|-------|---------|---------|---------|-----|
| Ag | noble_coinage_fcc | 1.02 | -1.50 | 8.44 | 3.65 |
| Al | post_transition | -7.88 | -20.20 | 3.75 | 10.61 |
| Au | noble_coinage_fcc | -21.14 | -30.97 | 12.03 | 21.38 |
| Ca | alkaline_earth_fcc | -0.40 | -5.43 | 1.71 | 2.51 |
| Cr | transition_bcc | 46.52 | 80.54 | -10.48 | 45.85 |
| Cu | noble_coinage_fcc | 15.47 | -13.30 | 0.41 | 9.72 |
| Fe | transition_bcc | -26.99 | -32.81 | -2.13 | 20.64 |
| Mo | transition_bcc | -25.07 | -10.11 | 3.92 | 13.03 |
| Nb | transition_bcc | -18.01 | -41.90 | 6.01 | 21.97 |
| Ni | transition_fcc | -21.88 | -4.17 | -1.44 | 9.16 |
| Pd | transition_fcc | -0.57 | -12.78 | 5.89 | 6.41 |
| Pt | transition_fcc | -13.04 | -29.88 | 13.05 | 18.65 |
| Sr | alkaline_earth_fcc | 6.09 | -0.13 | -0.56 | 2.26 |
| Ta | transition_bcc | -29.16 | -5.80 | -20.86 | 18.61 |
| V | transition_bcc | 30.47 | -10.94 | -0.40 | 13.94 |
| W | transition_bcc | -24.70 | -15.89 | 2.43 | 14.34 |

### Global LOO-PCA residuals vs Tr2SCAN_0K

| Element | C11 res | C12 res | C44 res | MAE |
|---------|---------|---------|---------|-----|
| Ag | 0.44 | -2.30 | 8.56 | 3.77 |
| Al | -8.47 | -21.00 | 3.86 | 11.11 |
| Au | -21.73 | -31.77 | 12.12 | 21.87 |
| Ca | -0.98 | -6.24 | 1.82 | 3.01 |
| Cr | 45.61 | 80.14 | -10.49 | 45.41 |
| Cu | 14.90 | -14.11 | 0.52 | 9.84 |
| Fe | -27.57 | -33.62 | -2.00 | 21.06 |
| Mo | -25.64 | -10.92 | 4.03 | 13.53 |
| Nb | -18.62 | -42.68 | 6.11 | 22.47 |
| Ni | -22.46 | -4.98 | -1.33 | 9.59 |
| Pd | -1.15 | -13.58 | 6.00 | 6.91 |
| Pt | -13.63 | -30.68 | 13.14 | 19.15 |
| Sr | 5.51 | -0.94 | -0.45 | 2.30 |
| Ta | -29.74 | -6.61 | -20.74 | 19.03 |
| V | 29.93 | -11.77 | -0.28 | 13.99 |
| W | -25.27 | -16.70 | 2.54 | 14.84 |

### Comparison to Layer-1 classical bias vectors

| Family | N | Participation ratio | Effective rank |
|--------|---|---------------------|----------------|
| Ackland-1987 | 8 | 0.449 | 3 |
| Ackland-1997 | 1 | 0.968 | 0 |
| Adams-1989 | 5 | 0.787 | 3 |
| Chamati-2006 | 1 | 0.934 | 0 |
| Foiles-1986 | 3 | 0.527 | 2 |
| Han-2003 | 2 | 0.546 | 1 |
| Howells-2018 | 1 | 0.754 | 0 |
| Olsson-2009 | 1 | 0.483 | 0 |
| **MLIP global error** | **16** | **2.116** | **3** |

Layer-1 bias vectors were family-specific and often 1D within a family. The MLIP errors are not globally low-rank; the low-dimensional structure is **class-local**, not universal.

## Alternative Operators Table

All operators use only the existing 1×1×1 TensorNet/PBE outputs. Cost equals one raw 1×1×1 run.

| Operator | mean MAE vs TPBE | median MAE vs TPBE | mean MAE vs Tr2SCAN | median MAE vs Tr2SCAN | Notes |
|----------|-----------------:|-------------------:|--------------------:|----------------------:|-------|
| raw | 14.55 | 13.48 | 22.55 | 22.50 | |
| shift-only | 16.28 | 15.74 | 14.55 | 13.48 | exact PBE→r2SCAN functional shift |
| global-loo-pca | **63.40** | **65.33** | **54.28** | **55.09** | v0.1 operator; degrades accuracy |
| global-loo-pca-unshifted | 54.28 | 55.09 | 45.83 | 46.05 | PCA bias without functional shift |
| scalar-bulk | 19.17 | 19.01 | **14.13** | **11.16** | v0.2 recommended on Tr2SCAN target |
| ensemble-1x1x1 | **11.60** | 11.62 | 19.89 | 19.65 | 3-model PBE ensemble |

Key observations:
- `shift-only` already improves over raw vs Tr2SCAN (14.55 vs 22.55 GPa), confirming that the bulk-modulus functional shift captures real systematic stiffness bias.
- `global-loo-pca` (v0.1) **degrades** accuracy on both targets (63.40 vs TPBE, 54.28 vs Tr2SCAN) because a single global PC is a poor approximation of class-specific error directions.
- `scalar-bulk` (v0.2) improves further over shift-only on the Tr2SCAN target (14.13 vs 14.55 GPa) and beats the 3-architecture ensemble (19.89 GPa) at 2.70× lower cost. On the PBE headline target it does not beat raw or the ensemble.
- Class-aware and locally-fitted operators remain interesting future directions, but they have not yet been benchmarked on this dataset.

## v0.2 scalar-bulk operator

The v0.2 operator, `scalar-bulk`, is a leave-one-out scalar re-scaling of the bulk-modulus functional shift. For each held-out element, a single scalar `α` is fit on the other 15 elements so that the bulk modulus of `raw + α · (Tr2SCAN − TPBE)` matches the Tr2SCAN bulk modulus; that `α` is then applied to the held-out element's shift. It uses only the existing 1×1×1 TensorNet/PBE output and the target-derived shift, so its cost equals one raw 1×1×1 run.

**Aggregate performance (1×1×1 TensorNet/PBE, LOO scalar-bulk):**

| Metric | vs TPBE_0K | vs Tr2SCAN_0K |
|--------|-----------:|--------------:|
| mean MAE | 19.17 GPa | **14.13 GPa** |
| median MAE | 19.01 GPa | **11.16 GPa** |
| core-hours | 0.0134 | 0.0134 |

On the Tr2SCAN-corrected target, `scalar-bulk` improves over raw (22.55 GPa), shift-only (14.55 GPa), and the 3-architecture ensemble (19.89 GPa), while remaining 2.70× cheaper than the ensemble and 3.86× cheaper than the 3×3×3 reference. The v0.1 global LOO-PCA operator is far worse (54.28 GPa). On the PBE headline target it does not beat raw or the ensemble; no single-model operator does.

### Scalar-bulk per-element α and predictions

| Element | α | C11 corr | C12 corr | C44 corr | MAE vs Tr2SCAN |
|---------|---|----------|----------|----------|----------------|
| Ag | 1.338 | 134.05 | 96.72 | 60.66 | 7.32 |
| Al | 1.322 | 96.05 | 52.75 | 35.61 | 10.61 |
| Au | 1.305 | 149.66 | 115.43 | 39.52 | 20.73 |
| Ca | 1.322 | 20.43 | 9.66 | 15.80 | 2.51 |
| Cr | 1.580 | 596.29 | 233.73 | 102.13 | 52.45 |
| Cu | 1.352 | 200.56 | 152.41 | 90.38 | 11.71 |
| Fe | 1.223 | 251.43 | 136.41 | 107.67 | 16.91 |
| Mo | 1.294 | 476.13 | 157.35 | 116.93 | 10.57 |
| Nb | 1.328 | 213.65 | 102.45 | 16.90 | 22.15 |
| Ni | 1.316 | 305.80 | 185.02 | 155.06 | 5.65 |
| Pd | 1.317 | 223.86 | 163.39 | 90.61 | 7.80 |
| Pt | 1.221 | 314.78 | 224.15 | 86.84 | 14.81 |
| Sr | 1.322 | 21.29 | 10.36 | 11.93 | 2.26 |
| Ta | 1.299 | 257.67 | 164.71 | 53.20 | 15.57 |
| V | 1.345 | 335.95 | 134.43 | 16.88 | 15.14 |
| W | 1.259 | 542.70 | 207.81 | 161.23 | 9.94 |

## Recommended v0.2 Operator

**Adopt `scalar-bulk` as the v0.2 operator on the Tr2SCAN-corrected target.**

- Mean MAE vs Tr2SCAN: **14.13 GPa**; median **11.16 GPa**.
- It is the best operator that does not require an oracle or multi-model ensemble.
- Cost is identical to a raw 1×1×1 run: **0.0134 core-hours** (2.70× cheaper than the ensemble, 3.86× cheaper than the 3×3×3 reference).
- Cell-size independence is confirmed on the 3×3×3 grid (see below).
- Seed variance is negligible on the Ca/Cu/Fe/Cr subset (see below).
- Future class-aware operators (e.g., class-mean or kNN-bias) may improve robustness when the calibration set is small or bonding-class labels are uncertain, but they have not yet been benchmarked on this dataset.

## Cell-size independence check

To confirm that `scalar-bulk` is a cell-size-independent operator rather than an artifact of the small conventional cell, the LOO alphas were fit on the existing 3×3×3 raw predictions and applied to the 3×3×3 Tr2SCAN-corrected target.

| Metric | scalar-bulk 1×1×1 | scalar-bulk 3×3×3 |
|--------|------------------:|------------------:|
| mean MAE vs Tr2SCAN_0K | 14.13 GPa | **14.14 GPa** |
| median MAE vs Tr2SCAN_0K | 11.16 GPa | **11.20 GPa** |

The 1×1×1 and 3×3×3 means differ by 0.01 GPa and the medians by 0.04 GPa. The operator is therefore **cell-size independent**: it transfers from the cheap conventional cell to the expensive supercell reference with no measurable loss of accuracy.

## Variance subset

A variance subset was run to check seed-to-seed stability: Ca, Cu, Fe, and Cr were each run with three different random seeds (12 cases total) using TensorNet/PBE 1×1×1.

- TensorNet/PBE 1×1×1 is **deterministic across seeds** for this benchmark.
- Per-element MAE standard deviations are ~0 GPa.
- The single-seed headline numbers are therefore seed-stable on the tested subset.
- Raw data: `/home/alex/Dev/lupine/lupine/data/mlip_elastic_benchmark_variance_subset/`.

This removes a key uncertainty from the cost-accuracy ratios: the single-model cost is not being inflated by hidden seed variance on the elements most prone to numerical instability.

## v0.3 Directional correction scheme and feedback loop

The failure of the global operator motivated a first-principles class-aware formalization rather than another ad-hoc fix.

### Lean formalization

`OpenDistillationFactory/Materials/Distillation/DirectionalCorrectionScheme.lean` introduces a universal operator that assigns one correction direction to each class:

- `DirectionalCorrectionScheme ι` stores a direction `d_c` for each class `c`.
- `alpha c v = ⟨v, d_c⟩ / ⟨d_c, d_c⟩` is the exact scalar minimizer of the residual along `d_c`.
- `correct c raw shift target = raw + shift + alpha c (target - (raw + shift)) • d_c`.
- `isOutlier` flags samples whose corrected residual exceeds a class threshold.
- `oracle_offset_zero_residual` proves that adding the exact residual eliminates error.
- `class_aware_eq_global` proves that a class-aware scheme equals a global scheme when the class direction coincides with the shared direction.

This is the abstraction above v0.2:

- `scalar-bulk` → every class shares the bulk-modulus direction.
- `global-loo-pca` → every class shares the first principal component.
- class-aware → each class gets its own direction.
- identity → all directions are zero.

The file builds cleanly and is mirrored to `lupine-rhizo/lean-spec`.

### Python feedback loop

`lupine/feedback.py` implements the operational counterpart:

- `FeedbackLoop.fit(...)` builds per-class directions and alphas from calibration rows.
- `evaluate(raw, shift, target, key)` applies the correction, measures the projection residual, and logs outliers.
- `offset_mode` selects how outliers are offset:
  - `none`: no extra correction.
  - `median`/`mean`: add the class median/mean projection residual from the outlier log.
  - `oracle`: add the exact projection residual, zeroing the directional error.
- `OutlierLog` persists outlier samples, thresholds, and class-level offset statistics.

For the current MLIP benchmark this provides a principled path from v0.2 scalar-bulk to a fully class-aware operator: the same bulk-modulus direction can be reused while alphas and offsets are allowed to vary by bonding class.

### FeedbackLoop benchmark results

The loop was benchmarked with leave-one-out element holdout on the 1×1×1 TensorNet/PBE data. Two alpha policies were tested:

- `scalar_bulk`: reuse the v0.2 per-element LOO scalar, but apply it as a directional correction `raw + shift + α·d`.
- `projection`: fit the exact directional projection scalar `α = ⟨target − raw − shift, d⟩ / ⟨d, d⟩` on the other 15 elements.

Three offset modes were tested for each policy: `none`, `median`, and `oracle` (oracle uses the held-out sample's own residual and is shown only as an empirical ceiling).

| Operator | mean MAE vs TPBE | median MAE vs TPBE | mean MAE vs Tr2SCAN | median MAE vs Tr2SCAN | outliers (Tr2SCAN) |
|----------|-----------------:|-------------------:|--------------------:|----------------------:|-------------------:|
| scalar-bulk (v0.2) | 19.17 | 19.01 | 14.13 | 11.16 | — |
| feedback-scalar_bulk-offset-none | 16.32 | 15.90 | 14.28 | 13.19 | 2/16 |
| feedback-scalar_bulk-offset-median | 16.45 | 15.67 | 14.41 | 13.19 | 2/16 |
| feedback-scalar_bulk-offset-oracle | 12.50 | 14.05 | 10.61 | 9.87 | 2/16 |
| feedback-projection-offset-none | 18.44 | 17.10 | 13.26 | 9.03 | 2/16 |
| feedback-projection-offset-median | 18.31 | 16.64 | 13.13 | 9.03 | 2/16 |
| feedback-projection-offset-oracle | 14.37 | 15.38 | 9.34 | 8.01 | 2/16 |

Key findings:

- The **projection policy without offset already improves over v0.2 scalar-bulk** on the Tr2SCAN target (mean MAE 13.26 vs 14.13 GPa; median 9.03 vs 11.16 GPa). It also improves the TPBE headline (18.44 vs 19.17 GPa), though it still does not beat raw or the ensemble on TPBE.
- The **median offset gives a small additional improvement** for the projection policy (13.13 vs 13.26 GPa mean Tr2SCAN), but not for the scalar-bulk policy. With only 15 training residuals per element, the median offset is noisy; it should become more effective as the calibration set grows.
- The **oracle offset** shows the empirical ceiling of the directional framework: 9.34 GPa mean vs Tr2SCAN. This is the target the operational offset mechanisms are trying to approximate without looking at the held-out target.
- Only **2 of 16 elements** are flagged as outliers under the 0.9-quantile threshold, so the bulk of the gain comes from the directional correction itself, not from outlier handling.

The v0.2 `scalar-bulk` operator remains the recommended production choice because it is the simplest operator that already beats the ensemble on Tr2SCAN. The `feedback-projection` policy is the immediate v0.3 candidate: it is strictly better on Tr2SCAN and only slightly more complex.

## Implications for the Distillation Engine

1. **The binding constraint must be class-aware.** A single global binding axis overfits to the bulk-like component and mis-corrects classes with different error geometry. The distillation engine should partition the calibration set by bonding class (or by a learned similarity neighborhood) before extracting the bias direction.
2. **Functional shift and bias are not interchangeable.** The scalar bulk-modulus shift already removes much of the stiffness bias; the residual class-mean bias is smaller and more class-local. Future versions should fit the bias on the *residual after shift*, not on the raw error.
3. **Headline framing must specify the target.** Against the corrected target (Tr2SCAN_0K), `scalar-bulk` beats both raw and the 3-architecture ensemble at single-run cost. Against the PBE headline target (TPBE_0K), the ensemble remains the accuracy benchmark and no single-model operator beats raw. The cost-accuracy claim survives as a **supercell-independence** story (corrected 1×1×1 vs 3×3×3 reference), but the **ensemble-beating** claim is only supported on the Tr2SCAN target.
4. **Variance and seed checks are now complete.** The 4-element, 3-seed subset (Ca, Cu, Fe, Cr) shows TensorNet/PBE 1×1×1 is deterministic; MAE standard deviations are ~0 GPa. The single-seed headline numbers are therefore seed-stable on the tested subset.
5. **Completed:** the class-aware `FeedbackLoop` was benchmarked against v0.2 scalar-bulk. The projection policy improves Tr2SCAN mean MAE to **13.26 GPa** (from 14.13 GPa) and TPBE mean MAE to **18.44 GPa** (from 19.17 GPa), with 2/16 outliers flagged.
6. **Next experiment:** test the projection policy on the 3×3×3 grid and evaluate bonding-class-specific directions (rather than the shared bulk-modulus direction) to see if the TPBE-target gap can be closed further.
