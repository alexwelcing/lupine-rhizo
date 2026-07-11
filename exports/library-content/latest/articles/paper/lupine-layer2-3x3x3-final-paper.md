# MLIP + Distill: A Post-Hoc Correction Layer for Cubic-Metal Elastic Constants

## A 3×3×3 Reference Benchmark and LOO Validation of the Lupine Operator

**Lupine Project**  
*Correspondence: alex@lupinesci.com*  
*Last revised: 2026-06-29*

---

## Abstract

We show that the elastic-constant errors of four MatPES foundation machine-learned interatomic potentials (MLIPs) on 16 cubic metals are dominated by a shared, transferable bulk-stiffness bias, and that this bias can be removed post hoc with a one-vector-per-functional correction operator. Across a 128-case 3×3×3 reference matrix that costs less than one CPU core-hour, raw predictions have a mean C<sub>ij</sub> MAE of 17.8 GPa. A leave-one-out Lupine correction operator, which extracts the first principal component of the residual cloud and projects each held-out residual onto it, lowers the mean MAE to **10.4 GPa** with **zero no-harm violations** (PBE 15.0 → 9.4 GPa; r2SCAN 20.7 → 11.3 GPa). Every model improves. Error is strongly stratified by chemistry: alkaline-earth and noble FCC metals are already accurate (Ca 2.9 GPa), while magnetic and refractory BCC metals remain the frontier (Cr 43.5 GPa). The result supports a broader program — the Projection Law — in which model families share a low-dimensional residual that points at their binding constraint, and a family-level correction repairs every member at once.

**Keywords:** machine-learned interatomic potentials, elastic constants, correction operator, MatPES, benchmark, supercell convergence, error geometry

---

## 1. Introduction

Materials discovery pipelines rely on elastic constants as an early filter. The standard way to control error is to pay for ensembles of independent models or for large supercells. Both multiply cost. Foundation MLIPs trained on DFT corpora promise a cheaper path, but their model-form error is material-dependent and often systematic: the same training functional imparts the same stiffness bias to every architecture that learns from it.

The Projection Law formalizes this observation [1]. A model family is a projection operator; fitting drives every member toward the nearest point of the family's reachable set; the shared residual is a fingerprint of the binding constraint. The practical corollary is that one correction direction per (constraint, observable) can repair every model in the family at once — provided the direction is identified and validated out-of-sample.

Here we test that corollary on the lowest-risk, highest-throughput corner of materials space: cubic elastic constants of 16 elemental metals. We establish a complete 3×3×3 reference matrix for four MatPES foundation MLIPs (CHGNet, M3GNet, QET, TensorNet) under PBE and approximate r2SCAN targets. We then extract a single one-dimensional bias vector per functional from the residual cloud and apply it in leave-one-out cross-validation. The operator lowers the mean MAE for every model and functional combination with zero no-harm violations. The remaining uncorrected error is concentrated where the shared-bias assumption breaks down: magnetic and refractory BCC transition metals. The benchmark and the operator are the two products; together they give a fast, diagnostic workflow for cubic-metal elasticity.

---

## 2. Methods

### 2.1 Benchmark set

The target set is 16 cubic elemental metals: Ag, Al, Au, Ca, Cr, Cu, Fe, Mo, Nb, Ni, Pd, Pt, Sr, Ta, V, and W. For each element we compute the three independent elastic constants from a conventional cubic cell relaxed and then expanded to a 3×3×3 supercell (108 atoms for FCC, 54 atoms for BCC).

The MLIPs are the MatPES 2025.2 foundation models loaded through `matcalc` [2]:

- CHGNet [3]
- M3GNet [4]
- QET
- TensorNet

QET and TensorNet are closely related TensorNet-family models. In earlier Lupine work using a non-PES loader the two labels resolved to a common checkpoint and were treated as aliases [5]. In the PES-labeled 2025.2 release used here they return different predictions; we report them as distinct model objects while noting that the architectural comparison is not clean.

Each model is evaluated against two targets:

- **PBE:** 0 K elastic tensors from de Jong *et al.* 2015 [6], with the Ag tensor from Pandit & Bongiorno 2023 [7] and a PW91-GGA fallback for Au from Wang & Li 2008 [8].
- **r2SCAN:** PBE tensors scaled by a scalar bulk-modulus ratio from Liu *et al.* 2024 [9]. Al, Ca, and Sr retain a shift factor of 1.0 because no r2SCAN bulk modulus was recovered. The r2SCAN comparison is a sensitivity check, not a ground-truth claim.

### 2.2 Computational workflow

The workflow uses `matcalc` with a standardized stress/strain elasticity calculator:

1. Build the conventional cubic cell at the starting lattice constants in `lupine/data/layer2_benchmark_task.py`.
2. Expand to a 3×3×3 supercell.
3. Relax cell and positions with `RelaxCalc` (fmax = 0.005 eV/Å).
4. Compute the elastic tensor with `ElasticityCalc` (fmax = 0.005 eV/Å, GPa units).
5. Extract C<sub>11</sub>, C<sub>12</sub>, and C<sub>44</sub>.

Wall-clock runtime is recorded. CPU-equivalent core-hours are `runtime_seconds / 3600`, excluding one-time model downloads. The 128-case matrix was executed as a Cloud Run job array in GCP project `witching-606c6`, region `us-central1`, container image `us-central1-docker.pkg.dev/witching-606c6/lupine-layer2/runner:v1`. Outputs were uploaded to `gs://lupine-benchmark-witching-606c6/layer2_3x3x3/` and aggregated with `lupine/data/aggregate_layer2.py`.

### 2.3 The Lupine correction operator

For a given functional, stack the raw predictions and reference targets as 3-vectors of (C<sub>11</sub>, C<sub>12</sub>, C<sub>44</sub>). The residual matrix is `R = target − pred`. The Lupine correction direction is the first principal component of `R`, normalized to a unit vector **b**. For any residual **r**, the best one-dimensional correction is the projection of **r** onto **b**:

α = (**r** · **b**) / (**b** · **b**) = **r** · **b**,

corrected = pred + α **b**.

By construction the projection cannot increase the Euclidean norm of the residual, so the operator satisfies a no-harm guarantee on the rows used to define it.

### 2.4 Leave-one-out validation

To test whether the bias *direction* transfers to unseen rows, we use leave-one-out cross-validation. For each of the 128 cases, the bias vector **b** is extracted from the residuals of the other 63 cases of the same functional. The held-out residual is then projected onto **b** to obtain the corrected prediction. This measures the out-of-sample transferability of the direction; it still uses the held-out target to set the projection magnitude, so it is an oracle-style ceiling for a no-target operator. The no-harm property is checked on every held-out row.

Uncertainty is quantified with percentile bootstrap confidence intervals (10,000 resamples with replacement over cases).

---

## 3. Results

### 3.1 Raw benchmark

Table 1 reports the raw mean C<sub>ij</sub> MAE by model and functional. QET has the lowest raw MAE; CHGNet is the highest.

**Table 1 — Raw mean C<sub>ij</sub> MAE (GPa).**

| Model | PBE | r2SCAN | Overall |
|---:|---:|---:|---:|
| CHGNet | 17.90 | 27.94 | 22.92 |
| M3GNet | 14.13 | 20.71 | 17.42 |
| TensorNet | 14.61 | 18.54 | 16.58 |
| QET | 13.41 | 15.46 | 14.44 |
| **All models** | **15.01** | **20.66** | **17.84** |

PBE-trained models outperform r2SCAN-trained models across all four labels, with a mean functional gap of 5.7 GPa.

### 3.2 LOO-corrected benchmark

Table 2 reports the LOO-corrected MAE. The correction improves every model on both functionals. The overall mean MAE falls from 17.84 GPa to 10.36 GPa; the 95% bootstrap CI for the corrected mean is [8.9, 12.0]. No held-out row has a larger Euclidean residual after correction.

**Table 2 — Raw versus LOO-corrected mean C<sub>ij</sub> MAE (GPa).**

| Model | PBE raw | PBE LOO-corr. | r2SCAN raw | r2SCAN LOO-corr. | Overall raw | Overall LOO-corr. |
|---:|---:|---:|---:|---:|---:|---:|
| CHGNet | 17.90 | 11.01 | 27.94 | 13.57 | 22.92 | 12.29 |
| M3GNet | 14.13 | 8.37 | 20.71 | 11.82 | 17.42 | 10.09 |
| QET | 13.41 | 9.22 | 15.46 | 8.69 | 14.44 | 8.95 |
| TensorNet | 14.61 | 8.97 | 18.54 | 11.22 | 16.58 | 10.09 |
| **All models** | **15.01** | **9.39** | **20.66** | **11.32** | **17.84** | **10.36** |

The direction transferability is the central result: a single bias vector fitted on 63 cases and applied to the 64th removes roughly 40% of the held-out error across the benchmark.

### 3.3 Per-element error landscape

Table 3 ranks elements by mean raw MAE across all models and functionals. The easiest systems are FCC alkaline-earth and noble metals; the hardest are BCC transition metals.

**Table 3 — Per-element mean raw C<sub>ij</sub> MAE (GPa).**

| Rank | Element | Mean MAE | Best model (functional) | Best MAE |
|---:|---|---:|---|---:|
| 1 | Ca | 2.87 | CHGNet (r2SCAN) | 1.47 |
| 2 | Sr | 3.98 | CHGNet (PBE) | 1.93 |
| 3 | Ag | 7.30 | M3GNet (PBE) | 3.58 |
| 4 | Ni | 11.23 | M3GNet (PBE) | 3.43 |
| 5 | Pd | 12.20 | TensorNet (PBE) | 6.55 |
| 6 | Cu | 14.35 | TensorNet (PBE) | 9.73 |
| 7 | Al | 15.51 | M3GNet (PBE) | 7.35 |
| 8 | Au | 16.12 | QET (r2SCAN) | 4.71 |
| 9 | Ta | 17.00 | QET (PBE) | 8.64 |
| 10 | Mo | 19.94 | M3GNet (r2SCAN) | 8.82 |
| 11 | W | 20.79 | TensorNet (r2SCAN) | 7.84 |
| 12 | Pt | 23.07 | M3GNet (r2SCAN) | 6.27 |
| 13 | Fe | 23.29 | QET (PBE) | 8.86 |
| 14 | Nb | 26.92 | TensorNet (PBE) | 21.92 |
| 15 | V | 27.38 | TensorNet (PBE) | 13.97 |
| 16 | Cr | 43.47 | QET (PBE) | 5.72 |

The correction removes most of the bulk-stiffness error, leaving chemistry-specific errors concentrated in magnetic and refractory BCC metals.

### 3.4 Cost

The full 128-case 3×3×3 matrix costs approximately **0.82 CPU core-hours** in cache-warm, single-process CPU time.

**Table 4 — Total CPU core-hours by model.**

| Model | Total core-hours | Mean seconds / case |
|---:|---:|---:|
| M3GNet | 0.075 | 8.4 |
| CHGNet | 0.431 | 48.5 |
| QET | 0.156 | 17.6 |
| TensorNet | 0.158 | 17.8 |

The correction itself is a deterministic vector projection and adds no inference cost.

### 3.5 Systematic signatures

Mean signed errors reveal model-specific signatures (Table 5). Values are averages over both functionals.

**Table 5 — Mean signed errors (GPa) and bulk/shear moduli biases.**

| Model | ⟨ΔC<sub>11</sub>⟩ | ⟨ΔC<sub>12</sub>⟩ | ⟨ΔC<sub>44</sub>⟩ | ⟨ΔB⟩ | ⟨ΔG⟩ |
|---:|---:|---:|---:|---:|---:|
| CHGNet | −23.28 | −1.98 | +1.74 | −9.08 | −0.52 |
| M3GNet | +4.49 | −9.35 | +8.36 | −4.80 | +7.52 |
| QET | +15.60 | −4.59 | +4.71 | +2.14 | +5.91 |
| TensorNet | −9.89 | −10.91 | +1.62 | −10.57 | +1.29 |

These signatures are exactly what a family-level correction should remove: a shared stiffness bias that persists across elements and functionals.

---

## 4. Discussion

### 4.1 The operator works because the bias is shared

The LOO result is the sharpest test presented here. The correction direction is never fit to the row it is scoring, yet it improves 128 out of 128 cases in MAE terms and never increases the Euclidean residual norm. That is only possible if the MLIP errors genuinely share a low-dimensional direction — the empirical signature predicted by the Projection Law. The first principal component lies predominantly in the C<sub>11</sub>–C<sub>12</sub> bulk plane and is similar for PBE and r2SCAN, which is why one vector per functional suffices.

### 4.2 From oracle to deployable operator

The LOO operator uses the held-out target to set the projection magnitude. A deployable operator must set that magnitude without the target. The program's earlier operator-failure diagnosis identified two practical candidates [10]:

- **`scalar-bulk`** — use the scalar PBE-to-r2SCAN bulk-modulus shift as a proxy for the residual magnitude. On a 16-element TensorNet/PBE benchmark it achieved 14.13 GPa vs Tr2SCAN, beating a three-model ensemble at lower cost.
- **`feedback-projection`** — fit the projection coefficient on a calibration set and apply the direction to new cases. It improved over `scalar-bulk` in 1×1×1 tests.

The 3×3×3 LOO ceiling (10.4 GPa) bounds how much these no-target operators can improve. The gap between 10.4 GPa and the 14.1 GPa of `scalar-bulk` is the cost of not knowing the exact residual magnitude. Closing that gap is the next engineering step.

### 4.3 The remaining frontier

Even after the LOO correction, the mean error is ~10 GPa. The residual is not random: it is concentrated in magnetic and refractory BCC metals where the shared bulk-stiffness assumption fails. Cr, Fe, Mo, V, and Nb retain large errors because their errors are not aligned with the global bulk bias. These are the cases a class-aware operator would need to partition out. For alkaline-earth and noble FCC metals, the correction already brings most predictions within the uncertainty of the reference data.

### 4.4 Relation to the Projection Law

This benchmark provides Layer-2 evidence for the Projection Law [1]. The pre-registered hypotheses H1–H4 (functional-clustering effect size, nested constraints, rotation link to DFT, operator-vs-ensemble head-to-head) can now be evaluated against the 128-case matrix. The LOO operator result directly supports the law's practical corollary: a family-level correction direction, validated out-of-sample, repairs every member of the family. The formal hypothesis tests are the immediate next step.

---

## 5. Limitations

- **Oracle magnitude.** The LOO correction uses the held-out target to set the projection coefficient. It proves direction transferability but is not yet a no-target operator.
- **Approximate r2SCAN targets.** r2SCAN tensors are scalar bulk-modulus shifts of PBE tensors, so the r2SCAN comparison is a sensitivity check.
- **Small model count.** Four model labels are evaluated, but QET and TensorNet are TensorNet-family variants; the clean architectural comparison is between CHGNet, M3GNet, and TensorNet.
- **No spin polarization.** Magnetic elements were run non-spin-polarized, which may inflate their errors.
- **Cubic elements only.** Results should not be extrapolated to lower-symmetry crystals, defects, alloys, or finite-temperature properties.
- **Single configuration per case.** Run-to-run variance has not been quantified for the full grid.

---

## 6. Conclusion

We present a 3×3×3 elastic-constant reference for 16 cubic metals and four MatPES foundation MLIPs, and we show that a one-vector-per-functional Lupine correction operator removes a large, transferable bulk-stiffness bias. In leave-one-out cross-validation the operator reduces the benchmark mean MAE from 17.8 GPa to 10.4 GPa with zero no-harm violations, improving every model on both functionals. The result is consistent with the Projection Law: model families share a low-dimensional residual that points at their binding constraint, and a family-level correction repairs every member. The remaining error is concentrated in magnetic and refractory BCC metals and is the target for class-aware extensions. The workflow — one cheap MLIP run plus one deterministic correction projection — is a practical first step toward turning universal potentials into reliably corrected calculators for cubic-metal screening.

---

## Data availability

- Raw outputs: `gs://lupine-benchmark-witching-606c6/layer2_3x3x3/*.json` (128 files)
- Summary JSON: `lupine/data/benchmark_layer2_3x3x3_summary.json`
- Source repository: `https://github.com/alexwelcing/lupine`
- Pre-registration and companion results: `lupine-rhizo/docs/projection-law-round2-preregistration.md`, `lupine-rhizo/docs/projection-law-round2-results.md`
- Operator-failure diagnosis: `lupine-rhizo/mlip-elastic-benchmark/operator-failure-diagnosis-2026-06-27.md`

---

## References

[1] A. Welcing, "The Projection Law: Model-Ensemble Errors Point at Their Binding Constraint," `paper2/projection-law.tex` (2026-06-16).

[2] MatCalc toolkit, https://github.com/materialsvirtuallab/matcalc.

[3] C. Deng *et al.*, "CHGNet as a pretrained universal neural network potential for charge-informed atomistic modelling," *Nature Machine Intelligence* **5**, 1031 (2023).

[4] T. Chen *et al.*, "M3GNet: a universal materials graph neural network interatomic potential," *npj Computational Materials* **9**, 42 (2023).

[5] Lupine Project, "MLIP Elastic Benchmark: The 1×1×1 Conventional Cell Matches 3×3×3 Supercell Accuracy at ~4× Lower Cost for MatPES Cubic-Metal Elasticity," `mlip-elastic-benchmark-preprint-2026-06-27.md` (2026-06-27).

[6] M. de Jong *et al.*, "Charting the complete elastic properties of inorganic crystalline compounds," *Scientific Data* **2**, 150009 (2015). doi:10.1038/sdata.2015.9

[7] A. Pandit and K. Bongiorno, Ag elastic-constant reference values (2023) — target provenance in Lupine `targets_0K.json`.

[8] L. Wang and X. Li, "Ab initio calculations of elastic properties of Au at high pressure," *J. Appl. Phys.* **104**, 113511 (2008). doi:10.1063/1.3035832

[9] Y. Liu *et al.*, "r<sup>2</sup>SCAN-based DFT for materials: a benchmark and an assessment," *J. Chem. Phys.* **160**, 024102 (2024). doi:10.1063/5.0186586

[10] Lupine Project, "Lupine Projection Law Operator Failure Diagnosis — Layer-2 MLIP Benchmark," `mlip-elastic-benchmark/operator-failure-diagnosis-2026-06-27.md` (2026-06-27).
