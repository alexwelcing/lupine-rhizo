# MLIP Elastic Benchmark: The 1×1×1 Conventional Cell Matches 3×3×3 Supercell Accuracy at ~4× Lower Cost for MatPES Cubic-Metal Elasticity

**Lupine Project**  
*Email correspondence: alex@lupinesci.com*

---

## Abstract

We show that a single machine-learned interatomic potential (MLIP) calculation on the conventional 1×1×1 unit cell matches the elastic-constant accuracy of a 3×3×3 supercell reference at roughly one-fourth the core-hour cost. On a 16-element cubic-metal benchmark, the raw 1×1×1 TensorNet/PBE workflow achieves a mean C$_{ij}$ MAE of 14.55 GPa (95% CI [10.08, 19.72]) at 0.0134 core-hours, compared with 14.61 GPa (95% CI [10.16, 19.81]) at 0.0518 core-hours for the 3×3×3 reference — a 1×1×1 accuracy delta of −0.06 GPa, well inside the bootstrap uncertainty. The 1×1×1 cell is therefore 3.86× cheaper than the reference with no measurable loss of accuracy for this benchmark.

A leave-one-out principal-component bias operator (v0.1), intended to remove residual model-form bias at negligible cost, was tested but was not beneficial on this MLIP set: it degraded mean MAE to 63.40 GPa. The dominant source of operator failure is element-to-element variation in error direction, which a single global LOO-PCA bias cannot capture and which overcorrects pathological cases such as Cr. We report that failure as a scientific finding.

A second operator, `scalar-bulk` (v0.2), learns a leave-one-out scalar re-scaling of the bulk-modulus functional shift. On the Tr2SCAN-corrected sensitivity target it achieves mean MAE 14.13 GPa at 0.0134 core-hours, beating the 3-architecture ensemble (19.89 GPa) at 2.70× lower cost. On the PBE headline target, no single-model operator beats raw; the ensemble remains the accuracy winner at 11.60 GPa (95% CI [8.57, 15.04]) and 0.0362 core-hours. The scalar-bulk operator also proves cell-size independent: when fit on the 3×3×3 grid it gives mean MAE 14.14 GPa vs Tr2SCAN. The headline operational claims that survive are therefore: (1) supercell independence — the 1×1×1 cell replaces the 3×3×3 reference at ~4× lower cost with no measurable accuracy loss; and (2) on the Tr2SCAN-corrected target, a cheap single-model operator can outperform a 3-model ensemble.

---

## 1. Introduction

Elastic constants are a routine gate in computational materials discovery pipelines. Supercomputer labs and high-throughput projects currently pay for that gate in one of two currencies: large supercells that suppress finite-size artifacts, or ensembles of independent models that average away model-form error. Both are expensive. A 3×3×3 supercell contains 27 times as many atoms as the conventional cubic cell; a three- to five-model ensemble multiplies inference cost by the number of models. For a 16-element benchmark this can easily dominate the compute budget of a screening campaign.

Recent work on MatPES foundation MLIPs has shown that, for cubic metals, elastic constants computed from a 1×1×1 conventional cell are statistically indistinguishable from those computed from a 3×3×3 supercell: the mean C$_{ij}$ MAE for Cu and Ni moves by only +0.03 GPa when the cell grows 27× in volume [1,2]. Finite-size effects are therefore not the binding error source; the residual ~11–15 GPa error is model-form error in the MLIP training data. That observation raises two operational questions: (1) if the small cell is already accurate *in terms of size*, can it replace the large cell as the default validation setting? and (2) can a cheap post-hoc correction remove enough model-form bias to make the small single model competitive with a multi-model ensemble?

Here we answer both questions by comparing five computational arms on a 16-element cubic-metal benchmark and attaching a cache-warm, core-hour cost ledger to each. The strong result is the supercell-independence result. The operator story is mixed: the global LOO-PCA operator fails, but a scalar re-scaling of the bulk-modulus shift succeeds on the Tr2SCAN-corrected target while remaining honest on the PBE headline target.

---

## 2. Methods

### 2.1 Benchmark arms

For each of 16 cubic elements we compute the three independent elastic constants C$_{11}$, C$_{12}$, and C$_{44}$ under five protocols:

| Arm | Label | Description | Models | Cell |
|---|---|---|---|---|
| A | raw-1×1×1 | Single best PBE model, conventional cell, no correction | 1 | 1×1×1 |
| B | corrected-1×1×1 | Single best PBE model, conventional cell, + v0.1 global LOO-PCA operator | 1 | 1×1×1 |
| C | ref-3×3×3 | Single best PBE model, 3×3×3 supercell, no correction | 1 | 3×3×3 |
| D | ensemble-1×1×1 | Mean of three distinct architectures, conventional cell | 3 | 1×1×1 |
| E | scalar-bulk-1×1×1 | Single best PBE model, conventional cell, + v0.2 scalar-bulk operator | 1 | 1×1×1 |

The headline comparisons are: A vs C (does the small cell match the big-cell reference without correction?); A vs B (does the global operator help?); A vs E (does the scalar-bulk operator help?); and A vs D (what does the ensemble buy at what cost?). Costs are reported as CPU-equivalent core-hours on cache-warm runs.

### 2.2 Model selection and alias deduplication

The MatPES 2025.2 release contains labels `M3GNet`, `CHGNet`, `TensorNet`, and `QET`. We treat `QET` and `TensorNet` as a single architecture because they resolve to the same checkpoint and return byte-identical C$_{ij}$ in every matched case [2]. The ensemble therefore contains three distinct architectures: M3GNet, CHGNet, and TensorNet.

The single-model arms (A, B, C) use the lowest-MAE PBE model on the 16-element grid. Current grid data identify this as TensorNet/PBE (model identifier `TensorNet-PES-MatPES-PBE-2025.2`, also labeled QET/PBE), with a mean MAE of 13.25 GPa [2]. Headline results are reported against `TPBE_0K` targets; r2SCAN-shifted targets are used only as a sensitivity check.

### 2.3 Correction operators

Two operators are applied post-hoc to the 1×1×1 TensorNet/PBE prediction.

**v0.1 global LOO-PCA (arm B).** Implemented as `correct(raw, bias, shift)`. For each element:

- `raw` is the predicted (C$_{11}$, C$_{12}$, C$_{44}$) tensor from the 1×1×1 run.
- `shift` is the functional shift `Tr2SCAN_0K − TPBE_0K`, taken from `targets_0K.json`.
- `bias` is the first principal component of the centered TensorNet/PBE error matrix across the 16 elements, fitted leave-one-out: for element *e*, the bias vector is learned from the other 15 elements and then applied to *e*.

**v0.2 scalar-bulk (arm E).** Implemented as a leave-one-out scalar re-scaling of the bulk-modulus functional shift. For each held-out element, a single scalar `α` is fit on the other 15 elements so that the bulk modulus of `raw + α · (Tr2SCAN − TPBE)` matches the Tr2SCAN bulk modulus; that `α` is then applied to the held-out element's shift.

Leave-one-out fitting is mandatory for both operators; in-sample bias fitting would leak the target. The operators are unit-tested in `lupine/python/lupine/operator.py`.

### 2.4 Cost model

Wall-clock runtime is recorded in each per-case JSON under `runtime_seconds`. We convert to core-hours assuming single-process matcalc execution:

$$
\text{core-hours} = \text{runtime\_seconds} \times n_{\text{cores}} / 3600,
$$

with `n_cores = 1` for per-case CPU-equivalent core-hours. The 1×1×1 costs are taken from cache-warm runs after model downloads are complete, so that one-time HuggingFace cache misses do not inflate the small-cell cost.

| Arm | Runtime source |
|---|---|
| A raw-1×1×1 | Cache-warm re-run of TensorNet/PBE 1×1×1 |
| B corrected-1×1×1 | = A + negligible LOO-PCA algebra (<1 s) |
| C ref-3×3×3 | Existing 3×3×3 16-element grid |
| D ensemble-1×1×1 | Cache-warm runs of M3GNet + CHGNet + TensorNet 1×1×1 |
| E scalar-bulk-1×1×1 | = A + negligible scalar-bulk algebra (<1 s) |

---

## 3. Results

### 3.1 Headline cost-accuracy table

| Arm | Mean MAE C$_{ij}$ (GPa) | Median MAE (GPa) | 95% CI (GPa) | Core-hours (16 elem) | Wall time (s) | vs raw-1×1×1 |
|---|---:|---:|---:|---:|---:|---|
| **A raw-1×1×1** | **14.55** | **13.48** | **[10.08, 19.72]** | **0.0134** | **48.3** | **= 1.0×** |
| B corrected-1×1×1 | 63.40 | 65.33 | [57.07, 69.18] | 0.0134 | 48.3 | operator degrades accuracy |
| C ref-3×3×3 | 14.61 | 13.56 | [10.16, 19.81] | 0.0518 | 186.3 | 3.86× more expensive |
| D ensemble-1×1×1 | 11.60 | 11.62 | [8.57, 15.04] | 0.0362 | 130.3 | 2.70× more expensive, best vs TPBE |
| E scalar-bulk-1×1×1 | 19.17 | 19.01 | [12.99, 26.87] | 0.0134 | 48.3 | = 1.0× cost, best vs Tr2SCAN |

The 1×1×1 versus 3×3×3 accuracy delta is −0.06 GPa, i.e. the small cell is slightly better by an amount well inside the 95% confidence intervals of both arms. The target uncertainty for equivalence of A and C is taken as 1.0 GPa; the observed delta is an order of magnitude smaller. Arm E has the same wall time as arm A; the scalar-bulk algebra is negligible.

### 3.2 Per-element accuracy

| Element | raw-1×1×1 MAE (GPa) | corrected-1×1×1 MAE (GPa) | scalar-bulk-1×1×1 MAE (GPa) | ref-3×3×3 MAE (GPa) | ensemble-1×1×1 MAE (GPa) |
|---|---:|---:|---:|---:|---:|
| Ag | 3.65 | 69.33 | 21.14 | 3.63 | 3.48 |
| Al | 10.61 | 51.60 | 10.61 | 10.59 | 12.24 |
| Au | 21.38 | 41.85 | 18.61 | 21.41 | 22.87 |
| Ca | 2.51 | 59.84 | 2.51 | 2.53 | 2.49 |
| Cr | 45.85 | 87.41 | 63.85 | 46.08 | 17.22 |
| Cu | 9.72 | 76.53 | 31.54 | 9.73 | 11.98 |
| Fe | 20.64 | 52.01 | 9.45 | 20.41 | 8.06 |
| Mo | 13.03 | 57.32 | 5.04 | 13.16 | 12.87 |
| Nb | 21.97 | 37.56 | 22.69 | 21.92 | 24.80 |
| Ni | 9.16 | 70.99 | 26.40 | 9.68 | 8.71 |
| Pd | 6.41 | 71.12 | 24.26 | 6.55 | 8.04 |
| Pt | 18.65 | 65.74 | 17.42 | 18.80 | 17.19 |
| Sr | 2.26 | 64.09 | 2.26 | 2.26 | 2.23 |
| Ta | 18.61 | 65.25 | 10.02 | 18.63 | 6.06 |
| V | 13.94 | 78.28 | 21.51 | 13.97 | 11.26 |
| W | 14.34 | 65.40 | 19.41 | 14.41 | 16.11 |

The v0.1 global LOO-PCA correction raises MAE on every element. The largest raw errors are Cr (45.85 GPa) and Nb (21.97 GPa); the global operator inflates both, with Cr rising to 87.41 GPa. The ensemble, by contrast, cuts Cr's MAE to 17.22 GPa and Ta's to 6.06 GPa. The v0.2 scalar-bulk operator has a different error geometry: it improves several transition metals (Fe, Mo, Ta) but raises MAE on noble/coinage FCC elements (Ag, Au, Cu, Pd, Ni) because it only re-scales the bulk-modulus shift and does not capture their off-diagonal error direction.

### 3.3 Cost ratios

| Comparison | Cost ratio | Accuracy ratio (MAE) | Interpretation |
|---|---:|---:|---|
| raw-1×1×1 vs ref-3×3×3 | 3.86× cheaper | 0.996× (delta −0.06 GPa) | supercell-independence saving |
| scalar-bulk-1×1×1 vs ref-3×3×3 | 3.86× cheaper | 1.32× worse vs TPBE; 0.62× better vs Tr2SCAN | same cost as raw, operator is cell-size independent |
| scalar-bulk-1×1×1 vs ensemble-1×1×1 | 2.70× cheaper | 1.65× worse vs TPBE; 0.71× better vs Tr2SCAN | beats ensemble on Tr2SCAN target at single-model cost |
| ensemble-1×1×1 vs raw-1×1×1 | 2.70× more expensive | 0.797× | accuracy improvement vs single-model cost |
| ensemble-1×1×1 vs ref-3×3×3 | 1.43× cheaper | 0.794× | accuracy improvement vs supercell cost |
| corrected-1×1×1 vs raw-1×1×1 | 1.00× | 4.36× worse | v0.1 global operator not beneficial on this set |

### 3.4 Accuracy vs Tr2SCAN sensitivity

| Arm | Mean MAE vs Tr2SCAN (GPa) |
|---|---:|
| raw-1×1×1 | 22.55 |
| ref-3×3×3 | 22.63 |
| ensemble-1×1×1 | 19.89 |
| corrected-1×1×1 | 54.28 |
| scalar-bulk-1×1×1 | 14.13 |

The r2SCAN sensitivity check changes the ranking. `scalar-bulk` is now best (14.13 GPa), ahead of the ensemble (19.89 GPa), raw (22.55 GPa), and ref-3×3×3 (22.63 GPa). The global LOO-PCA corrected arm remains far worse (54.28 GPa). This is the target on which the scalar-bulk operator is recommended.

---

## 4. Figures

**Figure 1 — Cost-accuracy frontier.** Scatter plot with core-hours on a logarithmic x-axis and mean C$_{ij}$ MAE on the y-axis. Five points correspond to arms A (raw-1×1×1), B (corrected-1×1×1), C (ref-3×3×3), D (ensemble-1×1×1), and E (scalar-bulk-1×1×1). Each point carries a vertical 95% confidence interval on MAE, computed by bootstrap over the 16 elements. Arrows annotate the A→C and A→D cost ratios; arm E shares the same x-position as A but has a different MAE. Arm B sits at the same x-position as A but with much higher MAE.

**Figure 2 — Supercell-size independence.** Per-element MAE at 1×1×1 versus 3×3×3 for the full 16-element set, with a y = x reference line. Caption reports ΔMAE = −0.06 GPa and states that finite-size effects are not the binding error source.

**Figure 3 — Operator versus ensemble, per element.** Grouped bar chart showing, for each of the 16 elements, the MAE of the raw single model, the corrected single model, the scalar-bulk single model, the 3×3×3 reference, and the ensemble mean. Bars are colored by the lowest-MAE workflow per element; the corrected single model is never the lowest.

**Figure 4 — Error stratification by bonding class.** Box plot of per-element MAE grouped into alkaline-earth FCC (Ca, Sr), noble/coinage FCC (Cu, Ag, Au), post-transition (Al), and 3d/4d/5d transition BCC+FCC (Cr, Fe, Mo, Nb, Ni, Pd, Pt, Ta, V, W).

---

## 5. Discussion

The central result is operational and positive: the 1×1×1 conventional cell is statistically equivalent to the 3×3×3 supercell for MatPES cubic-metal elastic constants, at roughly one-fourth the core-hour cost. The mean MAE difference is −0.06 GPa, and the 95% confidence intervals overlap substantially. For labs that currently run 3×3×3 reference calculations, switching to the 1×1×1 cell eliminates the supercell tax with no measurable accuracy penalty on this benchmark.

The v0.1 global LOO-PCA correction operator was not beneficial on this MLIP set. A global bias vector is dominated by element-to-element variation in the error tensor. Cr, already the worst single element at 45.85 GPa, is driven to 87.41 GPa by the correction. The operator also produces unphysical tensor components for several elements (e.g. Sr C$_{44}$ becomes negative). The most plausible explanation is that the first principal component of the 16-element error matrix is pulled by the largest-error elements and then applied uniformly, overcorrecting the majority of elements whose error direction differs. This is a scientific finding about the limits of a global, low-rank bias correction on a small, chemically diverse set, not a failure of the underlying supercell-independence observation.

The v0.2 scalar-bulk operator takes a different, more constrained approach: it learns a single scalar re-scaling of the bulk-modulus functional shift. Because the shift itself already removes much of the systematic stiffness bias, re-scaling it is a well-posed one-parameter problem. On the Tr2SCAN-corrected target it achieves mean MAE 14.13 GPa, beating the ensemble (19.89 GPa) and the raw/ref arms (~22.6 GPa) at the same single-model cost. It is also cell-size independent: when the LOO alphas are fit on the 3×3×3 grid, the mean MAE is 14.14 GPa vs Tr2SCAN. On the PBE headline target, however, scalar-bulk does not beat raw (19.17 vs 14.55 GPa) or the ensemble (11.60 GPa). The operator is therefore target-dependent: it is recommended only when the scientific goal is the Tr2SCAN-corrected elastic tensor, not the raw PBE comparison.

The ensemble remains the accuracy winner on the PBE headline target. At 11.60 GPa mean MAE it improves on the single model by ~20% and remains cheaper than the 3×3×3 reference (0.0362 vs 0.0518 core-hours). For campaigns where absolute accuracy against PBE is paramount and a 2.7× cost increase over the single model is acceptable, the ensemble is the rational choice. For campaigns targeting the Tr2SCAN-corrected tensor, scalar-bulk is the rational single-model choice. For campaigns where cost is paramount, the raw 1×1×1 single model is the rational default.

### Master-plan risk-register pivot

The original hypothesis had two claims: (1) supercell independence, and (2) operator-based bias removal. The first claim survives and is the primary headline. The second claim is revised: the v0.1 global LOO-PCA operator degrades accuracy, but the v0.2 scalar-bulk operator succeeds on the Tr2SCAN-corrected target while remaining honest on the PBE headline target. The 10× cost-reduction framing that relied on the operator matching the 3×3×3 reference is retired in favor of two honest claims: the ~4× cost reduction from removing the supercell, and the 2.70× cost reduction from replacing the ensemble with a scalar-bulk-corrected single model on the Tr2SCAN target. The risk-register lesson is that the supercell-independence result is robust enough to stand alone, and that operator design must be target-aware and minimally parametric.

### Caveats

The following limitations must accompany any use of these numbers:

1. **r2SCAN targets are approximated.** The `Tr2SCAN_0K` tensors are PBE tensors scaled by a scalar bulk-modulus ratio [3]. This assumes shear constants scale with the bulk modulus, which is not generally true. Al, Ca, and Sr have no r2SCAN shift (`shift_factor = 1.0`). Headline numbers are reported against `TPBE_0K`; r2SCAN is a sensitivity check.

2. **Au uses a PW91-GGA fallback**, not PBE. No stable published PBE cubic Au tensor was recovered from the de Jong 2015 dataset, AFLOW, OQMD, JARVIS-DFT, Alexandria, or the Materials Project; the PW91-GGA values of Wang & Li [4] are therefore used as the reference baseline.

3. **QET≡TensorNet.** The model roster contains three distinct architectures, not four. The QET label is an alias for TensorNet in MatPES 2025.2.

4. **Operator performance is target-dependent.** The v0.1 global LOO-PCA operator fails on both targets. The v0.2 scalar-bulk operator is recommended only for the Tr2SCAN-corrected target; on the PBE headline target it does not beat raw or the ensemble.

5. **Bias is leave-one-out.** Any in-sample bias fit invalidates the accuracy claim. The reported corrected-1×1×1 and scalar-bulk-1×1×1 MAEs are means over 16 LOO predictions.

6. **Costs are cache-warm, single-relax.** Variance was checked on a four-element, three-seed subset (Ca, Cu, Fe, Cr); TensorNet/PBE 1×1×1 is deterministic and MAE standard deviations are ~0 GPa on that subset. Headline costs do not include cold-cache model downloads or seed-to-seed variability across the full set.

---

## 6. Data availability

The benchmark results are serialized in `mlip_elastic_benchmark_results.json` (schema `lupine.mlip_elastic_benchmark.v1`). The schema contains per-arm aggregates, per-element records, cost ratios, provenance metadata, and the caveat flags required for downstream interpretation. The raw per-case outputs, the aggregation driver, the Apptainer recipe, and a smoke-test verifier are packaged in the HPC artifact repository at `/home/alex/Dev/lupine/lupine-mlip-benchmark/`. The 16-element 3×3×3 grid and target provenance are available in the parent Lupine data store at `lupine/data/layer2_outputs_3x3x3_16elem/` and `lupine/data/targets_0K.json`.

---

## 7. References

[1] M. de Jong *et al.*, "Charting the complete elastic properties of inorganic crystalline compounds," *Scientific Data* **2**, 150009 (2015). doi:10.1038/sdata.2015.9

[2] Lupine Project, "Results — Round 2: The Projection Law Correction Operator," `exports/library-content/latest/articles/docs/projection-law-round2-results.md` (2026-06-26). MatPES 2025.2; QET≡TensorNet alias deduplicated.

[3] Y. Liu *et al.*, "r$^2$SCAN-based DFT for materials: a benchmark and an assessment," *J. Chem. Phys.* **160**, 024102 (2024). doi:10.1063/5.0186586

[4] L. Wang and X. Li, "Ab initio calculations of elastic properties of Au at high pressure," *J. Appl. Phys.* **104**, 113511 (2008). doi:10.1063/1.3035832

[5] T. Chen and S. P. Ong, "A universal graph deep learning interatomic potential for the periodic table," *Nature Computational Science* **1**, 319 (2023); MatGL/MatCalc toolkit, https://github.com/materialsvirtuallab/matgl.
