# A Sub-Core-Hour 3×3×3 Elastic-Constant Reference for MatPES Foundation MLIPs on 16 Cubic Metals

**Lupine Project**  
*Correspondence: alex@lupinesci.com*  
*Last revised: 2026-06-29*

---

## Abstract

We report a 3×3×3 supercell reference calculation of the cubic elastic constants (C<sub>11</sub>, C<sub>12</sub>, C<sub>44</sub>) for 16 elemental metals using four publicly available MatPES foundation machine-learned interatomic potentials (MLIPs): CHGNet, M3GNet, QET, and TensorNet. The full 128-case matrix costs less than one CPU core-hour. Against published 0 K PBE references and approximate scalar-shifted r2SCAN targets, the raw benchmark mean absolute error (MAE) is 17.8 GPa (95% bootstrap CI [15.5, 20.4]). Error is strongly stratified by chemistry: alkaline-earth and noble FCC metals are well described (Ca 2.9 GPa, Sr 4.0 GPa, Ag 7.3 GPa mean MAE), while BCC transition metals dominate the tail (Cr 43.5 GPa). PBE-trained models outperform r2SCAN-trained models by a mean functional gap of 5.7 GPa. QET has the lowest raw MAE (14.4 GPa; CI [11.0, 18.1]). An exploratory in-sample recalibration with one bias vector per functional lowers the calibration-set MAE to 9.9 GPa; this is an upper bound on correctable shared bias, not a validated out-of-sample operator. The primary contribution is a cheap, reproducible reference layer and an honest error map for cubic-metal elasticity with current universal MLIPs.

**Certification status:** Every corrected C<sub>ij</sub> MAE reported here is an in-sample diagnostic and is **uncertified** as a correction license. An aggregate would require independent valid licenses for C11, C12, and C44 on each target. All derived elastic quantities—including B, G, C′, Cauchy pressure, and anisotropy—are likewise **uncertified** because componentwise licenses do not license differences, mixed-direction combinations, or general composites.

**Keywords:** machine-learned interatomic potentials, elastic constants, MatPES, benchmark, supercell convergence, error geometry

---

## 1. Introduction

Elastic constants are a first filter in high-throughput materials discovery. Until recently, that filter was paid for either with large supercells or with ensembles of independent models, both of which multiply cost. Foundation machine-learned interatomic potentials (MLIPs) trained on large DFT corpora now offer an inexpensive alternative, but their accuracy and convergence behavior for mechanical properties are still being established.

In a companion study we showed that, for 16 cubic metals, elastic constants computed from the conventional 1×1×1 cell and a 3×3×3 supercell are statistically indistinguishable, with a mean MAE delta of order 0.1 GPa [1]. That result removes finite-size error as the binding problem and points to model-form error in the MLIP training distribution. The present paper establishes the 3×3×3 reference matrix itself: a complete, reproducible, and inexpensive set of elastic-constant predictions that other models, correction schemes, and training sets can be compared against.

We deliberately limit the scope. This is not a claim that universal MLIPs are ready for all transition-metal elasticity, nor that a generic post-hoc correction fixes them. It is a reference measurement with explicit caveats: approximate r2SCAN targets, no spin-polarized calculations, cubic elements only, and an in-sample correction analysis whose out-of-sample validity remains to be tested.

---

## 2. Methods

### 2.1 Benchmark set

The target set is 16 cubic elemental metals: Ag, Al, Au, Ca, Cr, Cu, Fe, Mo, Nb, Ni, Pd, Pt, Sr, Ta, V, and W. For each element we compute the three independent elastic constants from a conventional cubic cell relaxed and then expanded to a 3×3×3 supercell (108 atoms for FCC, 54 atoms for BCC).

The MLIPs are the MatPES 2025.2 foundation models loaded through `matcalc` [2]:

- CHGNet [3]
- M3GNet [4]
- QET
- TensorNet

Each model is evaluated against two targets:

- **PBE:** 0 K elastic tensors from de Jong *et al.* 2015 [5], with the Ag tensor from Pandit & Bongiorno 2023 [6] and a PW91-GGA fallback for Au from Wang & Li 2008 [7].
- **r2SCAN:** PBE tensors scaled by a scalar bulk-modulus ratio from Liu *et al.* 2024 [8]. Al, Ca, and Sr retain a shift factor of 1.0 because no r2SCAN bulk modulus was recovered. The r2SCAN comparison is therefore a sensitivity check, not a headline accuracy claim.

### 2.2 Computational workflow

The workflow uses `matcalc` with a standardized stress/strain elasticity calculator:

1. Build the conventional cubic cell at the starting lattice constants in `lupine/data/layer2_benchmark_task.py`.
2. Expand to a 3×3×3 supercell.
3. Relax cell and positions with `RelaxCalc` (fmax = 0.005 eV/Å).
4. Compute the elastic tensor with `ElasticityCalc` (fmax = 0.005 eV/Å, GPa units).
5. Extract C<sub>11</sub>, C<sub>12</sub>, and C<sub>44</sub>.

Wall-clock runtime is recorded. CPU-equivalent core-hours are `runtime_seconds / 3600`, assuming one CPU process and excluding one-time model downloads.

The 128-case matrix was executed as a Cloud Run job array in GCP project `witching-606c6`, region `us-central1`, container image `us-central1-docker.pkg.dev/witching-606c6/lupine-layer2/runner:v1`. Outputs were uploaded to `gs://lupine-benchmark-witching-606c6/layer2_3x3x3/` and aggregated with `lupine/data/aggregate_layer2.py`.

### 2.3 Error metric and uncertainty

For each case the metric is

MAE<sub>Cij</sub> = (|C<sub>11</sub> − C<sub>11</sub><sup>ref</sup>| + |C<sub>12</sub> − C<sub>12</sub><sup>ref</sup>| + |C<sub>44</sub> − C<sub>44</sub><sup>ref</sup>|) / 3,

in GPa. All reported means are simple averages over the relevant subset. Uncertainty is quantified with percentile bootstrap confidence intervals (10,000 resamples with replacement). The bootstrap resamples cases, preserving the correlation structure among the three elastic constants within each case.

### 2.4 In-sample recalibration

To estimate how much of the benchmark error is a shared systematic bias rather than model-specific noise, we fit one first-principal-component bias vector per functional to the full residual matrix and project it onto each residual. This is identical to the `atlas-distill mlip-correct` projection operator run with `--training {functional} --target {functional}`. The no-harm property (corrected residual norm ≤ raw residual norm) holds by construction on the calibration set.

Because the bias vector is extracted from the same residuals used to score it, the corrected MAE is an **in-sample upper bound** on the correctable shared bias. It is not a validated out-of-sample correction operator. Earlier work in this program showed that a single global 1-D PCA operator can degrade accuracy on MLIPs because errors are bonding-class specific [9]. The in-sample recalibration here is best read as a diagnostic: it identifies the magnitude of the shared bulk-stiffness bias and the chemical classes where that bias no longer describes the error.

---

## 3. Results

### 3.1 Raw model ranking

Table 1 reports mean C<sub>ij</sub> MAE with 95% bootstrap confidence intervals. QET has the lowest raw MAE, followed by TensorNet, M3GNet, and CHGNet. The confidence intervals overlap substantially, so the ordering should be read as suggestive rather than definitive.

**Table 1 — Raw mean C<sub>ij</sub> MAE (GPa) by model.**

| Model | Mean MAE | 95% CI | n |
|---:|---:|---:|---:|
| QET | 14.4 | [11.0, 18.1] | 32 |
| TensorNet | 16.6 | [12.8, 20.7] | 32 |
| M3GNet | 17.4 | [12.6, 23.4] | 32 |
| CHGNet | 22.9 | [17.5, 28.8] | 32 |
| **All models** | **17.8** | **[15.5, 20.4]** | **128** |

By functional, PBE-trained models are more accurate than r2SCAN-trained models (Table 2). The gap is largest for CHGNet and smallest for QET.

**Table 2 — Raw mean C<sub>ij</sub> MAE (GPa) by functional.**

| Functional | Mean MAE | 95% CI | n |
|---:|---:|---:|---:|
| PBE | 15.0 | [12.6, 17.5] | 64 |
| r2SCAN | 20.7 | [16.7, 24.9] | 64 |

### 3.2 Per-element error landscape

Table 3 ranks elements by mean MAE across all models and functionals. The error is not uniform: the easiest systems are FCC alkaline-earth and noble metals; the hardest are BCC transition metals, especially magnetic Cr and Fe and low-shear Nb.

**Table 3 — Per-element mean C<sub>ij</sub> MAE (GPa).**

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

This pattern points to local electronic structure — magnetism, d-band bonding, Fermi-surface nesting — as the dominant residual error source, not finite-size effects.

### 3.3 Cost

The full 128-case 3×3×3 matrix costs approximately **0.82 CPU core-hours** in cache-warm, single-process CPU time. Table 4 breaks this down by model.

**Table 4 — Total CPU core-hours by model (PBE + r2SCAN, 16 elements each).**

| Model | Total core-hours | Mean seconds / case |
|---:|---:|---:|
| M3GNet | 0.075 | 8.4 |
| CHGNet | 0.431 | 48.5 |
| QET | 0.156 | 17.6 |
| TensorNet | 0.158 | 17.8 |

### 3.4 QET vs TensorNet

Earlier Lupine work treated QET and TensorNet as aliases because both labels resolved to a common TensorNet-MatPES checkpoint in the configuration used at that time [1]. In the present 3×3×3 run the two PES labels return different predictions in every (element, functional) pair:

- Mean absolute MAE difference: 8.41 GPa
- Mean relative difference: 53.9%
- Identical (element, functional) pairs: 0 / 32
- Largest gap: Cr/PBE, QET 5.72 GPa vs TensorNet 46.08 GPa

We therefore report them as distinct model objects. Whether this reflects genuinely distinct architectures or two weight sets from the same architecture family remains unresolved; the comparison should be treated as a model-label comparison, not a clean architectural comparison.

### 3.5 Systematic biases

Mean signed errors (predicted − target) reveal systematic model signatures (Table 5). Values are averages over both functionals.

**Table 5 — Mean signed errors (GPa) and bulk/shear moduli biases.**

| Model | ⟨ΔC<sub>11</sub>⟩ | ⟨ΔC<sub>12</sub>⟩ | ⟨ΔC<sub>44</sub>⟩ | ⟨ΔB⟩ | ⟨ΔG⟩ |
|---:|---:|---:|---:|---:|---:|
| CHGNet | −23.28 | −1.98 | +1.74 | −9.08 | −0.52 |
| M3GNet | +4.49 | −9.35 | +8.36 | −4.80 | +7.52 |
| QET | +15.60 | −4.59 | +4.71 | +2.14 | +5.91 |
| TensorNet | −9.89 | −10.91 | +1.62 | −10.57 | +1.29 |

CHGNet and TensorNet systematically under-stiffen the bulk modulus; QET slightly over-stiffens it; M3GNet over-stiffens shear while under-stiffening C<sub>12</sub>.

### 3.6 In-sample recalibration upper bound

Table 6 reports the raw and 1-D-corrected calibration-set MAE for each model and functional. The correction lowers MAE for every model on both functionals because it extracts the shared bulk-stiffness component of the residuals. The overall calibration-set MAE falls from 17.8 GPa to 9.9 GPa.

**Table 6 — Raw versus 1-D in-sample corrected mean C<sub>ij</sub> MAE (GPa).**

| Model | PBE raw | PBE corrected | r2SCAN raw | r2SCAN corrected | Overall raw | Overall corrected |
|---:|---:|---:|---:|---:|---:|---:|
| CHGNet | 17.90 | 10.33 | 27.94 | 12.47 | 22.92 | 11.40 |
| M3GNet | 14.13 | 8.18 | 20.71 | 11.48 | 17.42 | 9.83 |
| QET | 13.41 | 8.56 | 15.46 | 8.55 | 14.44 | 8.56 |
| TensorNet | 14.61 | 8.69 | 18.54 | 11.14 | 16.58 | 9.91 |
| **All models** | **15.01** | **8.94** | **20.66** | **10.91** | **17.84** | **9.92** |

This is an upper bound, not a deployed operator. The first principal component explains 60% of the PBE residual variance and 72% of the r2SCAN residual variance; the remaining variance is concentrated in the BCC transition metals and is not captured by a single global bias direction.

---

## 4. Discussion

### 4.1 A cheap reference layer

The main practical result is that a 3×3×3 elastic-constant reference for 16 cubic metals can be generated for less than one CPU core-hour. Together with the companion 1×1×1 result, this means that inexpensive MLIP calculations can replace supercell-based DFT gates for this class of materials, provided one accepts the residual model-form error documented here.

The reference is reproducible: the container image, the model versions, the target provenance, and the raw outputs are all pinned. New model releases can be re-benchmarked against the same targets at negligible cost.

### 4.2 Model recommendation

QET is the most accurate model in this benchmark on both functionals, although its advantage over TensorNet and M3GNet is within the bootstrap uncertainty. M3GNet is the fastest and remains competitive. CHGNet is systematically soft and is the least accurate for r2SCAN-derived moduli of heavy d metals. For high-throughput cubic-metal screening where speed matters, M3GNet is a reasonable default; for highest raw accuracy, QET.

### 4.3 The r2SCAN frontier

The mean PBE-to-r2SCAN degradation of 5.7 GPa is the largest unresolved accuracy gap. It is not simply a scalar-target artifact: the largest bulk-modulus shifts (Cu, Ag, Pd, Ni) are not the worst r2SCAN failures. The hardest r2SCAN cases are magnetic and refractory BCC metals (Cr, Fe, Mo) and heavy FCC Pt. Closing this gap will require training data with better meta-GGA stress/strain coverage, magnetic ground states, and Fermi-surface-sensitive properties.

### 4.4 Outlook for correction operators

The in-sample recalibration shows that a shared bulk-stiffness bias exists across the benchmark and is removable when the bias direction is known. A production operator must satisfy three additional conditions:

1. **Out-of-sample validity.** The bias direction must be fit on held-out (element, model) folds, not on the same residuals it scores.
2. **Class-awareness.** Errors are bonding-class specific [9]; a single global direction will mis-correct classes whose residual geometry differs.
3. **Target specificity.** The r2SCAN target is approximate; any operator trained on it inherits that approximation.

The `scalar-bulk` and `feedback-projection` candidates identified in the earlier operator-failure diagnosis are the natural starting points for a validated operator [9]. Until such validation is complete, the 9.9 GPa figure should be treated as a calibration-set upper bound, not a deployable accuracy.

### 4.5 Relation to the Projection Law

This benchmark was designed to supply data for the Layer-2 tests of the Projection Law (H1–H4) [10]: functional-clustering effect size, nested constraints, and operator-vs-ensemble head-to-heads. The raw results are consistent with the law’s expectation that errors organize by training functional and bonding class, but the formal pre-registered hypothesis tests are not reported here. The contribution of this paper is the reference matrix and error map; the hypothesis tests are the next step.

---

## 5. Limitations

We list the main limitations explicitly so the result can be evaluated fairly:

- **Approximate r2SCAN targets.** r2SCAN tensors are constructed by scalar bulk-modulus scaling of PBE tensors. The r2SCAN numbers are sensitivity checks, not ground-truth benchmarks.
- **In-sample correction.** The 1-D corrected MAEs are fit and evaluated on the same 128 cases. They bound the correctable shared bias but do not validate an out-of-sample operator.
- **Small effective model count.** Four model labels are evaluated, but QET and TensorNet are closely related; the clean architectural comparison is between CHGNet, M3GNet, and the TensorNet family.
- **No spin polarization.** Magnetic elements (Cr, Fe, Ni, V) were run with non-spin-polarized inference. Some of their large errors may reflect the spin protocol rather than the potential itself.
- **Cubic elements only.** Results should not be extrapolated to lower-symmetry crystals, defects, surfaces, alloys, or finite-temperature properties.
- **Single configuration per case.** Each (element, model, functional) case is one relax plus one elastic fit; run-to-run variance has not been quantified for the full grid.

---

## 6. Conclusion

We present a complete, inexpensive 3×3×3 elastic-constant reference for 16 cubic metals and four MatPES foundation MLIPs. The raw benchmark has a mean MAE of 17.8 GPa, with errors concentrated in BCC transition metals and r2SCAN targets. QET is the most accurate model in the set, and the full matrix costs less than one CPU core-hour. An in-sample recalibration shows that roughly half of the benchmark error is a shared bulk-stiffness bias, but a deployable correction operator requires out-of-sample, class-aware validation. The primary deliverable is a reproducible error map that researchers can use to judge whether current universal MLIPs are adequate for a given cubic-metal screening task and where the next generation of models and training data must improve.

---

## Data availability

- Raw outputs: `gs://lupine-benchmark-witching-606c6/layer2_3x3x3/*.json` (128 files)
- Summary JSON: `lupine/data/benchmark_layer2_3x3x3_summary.json`
- Source repository: `https://github.com/alexwelcing/lupine`
- Pre-registration and companion results: `lupine-rhizo/docs/projection-law-round2-preregistration.md`, `lupine-rhizo/docs/projection-law-round2-results.md`
- Operator-failure diagnosis: `lupine-rhizo/mlip-elastic-benchmark/operator-failure-diagnosis-2026-06-27.md`

---

## References

[1] Lupine Project, "MLIP Elastic Benchmark: The 1×1×1 Conventional Cell Matches 3×3×3 Supercell Accuracy at ~4× Lower Cost for MatPES Cubic-Metal Elasticity," `mlip-elastic-benchmark-preprint-2026-06-27.md` (2026-06-27).

[2] MatCalc toolkit, https://github.com/materialsvirtuallab/matcalc.

[3] C. Deng *et al.*, "CHGNet as a pretrained universal neural network potential for charge-informed atomistic modelling," *Nature Machine Intelligence* **5**, 1031 (2023).

[4] T. Chen *et al.*, "M3GNet: a universal materials graph neural network interatomic potential," *npj Computational Materials* **9**, 42 (2023).

[5] M. de Jong *et al.*, "Charting the complete elastic properties of inorganic crystalline compounds," *Scientific Data* **2**, 150009 (2015). doi:10.1038/sdata.2015.9

[6] A. Pandit and K. Bongiorno, Ag elastic-constant reference values (2023) — target provenance in Lupine `targets_0K.json`.

[7] L. Wang and X. Li, "Ab initio calculations of elastic properties of Au at high pressure," *J. Appl. Phys.* **104**, 113511 (2008). doi:10.1063/1.3035832

[8] Y. Liu *et al.*, "r<sup>2</sup>SCAN-based DFT for materials: a benchmark and an assessment," *J. Chem. Phys.* **160**, 024102 (2024). doi:10.1063/5.0186586

[9] Lupine Project, "Lupine Projection Law Operator Failure Diagnosis — Layer-2 MLIP Benchmark," `mlip-elastic-benchmark/operator-failure-diagnosis-2026-06-27.md` (2026-06-27).

[10] A. Welcing, "The Projection Law: Model-Ensemble Errors Point at Their Binding Constraint," `paper2/projection-law.tex` (2026-06-16).
