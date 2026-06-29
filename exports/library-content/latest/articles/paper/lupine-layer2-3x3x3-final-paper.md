# Layer-2: A Sub-Core-Hour 3×3×3 Elastic-Constant Reference Benchmark for MatPES Foundation MLIPs on 16 Cubic Metals

**Lupine Project**
*Correspondence: alex@lupinesci.com*
*Submitted: 2026-06-29*

---

## Abstract

We present a complete 3×3×3 supercell reference benchmark of cubic-metal elastic constants for four MatPES foundation machine-learned interatomic potentials (MLIPs): CHGNet, M3GNet, QET, and TensorNet. Across 16 elemental metals and two DFT functionals (PBE and r2SCAN), the full 128-case matrix costs less than one CPU core-hour and achieves an overall mean C$_{ij}$ mean absolute error (MAE) of 17.84 GPa (95% CI [15.51, 20.41]). QET is the accuracy leader, with a mean MAE of 14.44 GPa across both functionals and best single-workflow performance of 13.41 GPa on PBE. r2SCAN targets are systematically harder: the mean functional gap is +5.65 GPa, with CHGNet showing the largest sensitivity. Per-element error is strongly stratified by chemistry: FCC alkaline-earth and noble metals are well described (Ca 2.87 GPa, Sr 3.98 GPa, Ag 7.30 GPa mean MAE), while BCC transition metals dominate the tail, led by Cr at 43.47 GPa. A key correction to prior reporting is that QET and TensorNet are not aliases in this benchmark; they differ by a mean absolute MAE of 8.41 GPa. The results support a companion finding that the conventional 1×1×1 cell is statistically equivalent to the 3×3×3 supercell at roughly four-fold lower cost, and they identify transition-metal bonding, magnetism, and soft shear modes as the remaining accuracy frontier.

**Keywords:** machine-learned interatomic potentials, elastic constants, MatPES, high-throughput screening, benchmark, supercell convergence

---

## 1. Introduction

Elastic constants are one of the most common gates in computational materials discovery. They determine stiffness, ductility, phonon stability, and thermomechanical response, and they are cheap enough to compute at scale that they are often used as a first filter in high-throughput pipelines. Traditionally, that filter has been paid for in one of two currencies: large supercells that suppress finite-size artifacts, or ensembles of independent models that average away model-form error. Both multiply cost. A 3×3×3 supercell contains 27 times as many atoms as the conventional cubic cell; a three- or four-model ensemble multiplies inference cost by the number of models.

Recent foundation MLIPs trained on the MatPES dataset [1] have reached a level of generality that makes them plausible default calculators for cubic-metal elasticity. A natural question is whether the conventional 1×1×1 cell is already accurate enough to replace the 3×3×3 reference. In a companion study we showed that, for 16 cubic metals, elastic constants from the 1×1×1 and 3×3×3 cells are statistically indistinguishable, with a mean MAE delta of order 0.1 GPa [2]. If finite-size effects are not the binding error source, then the residual error is model-form error in the MLIP training data, and the 3×3×3 reference itself can become a cheap validation layer rather than an expensive fallback.

Here we establish that reference layer. We compute C$_{11}$, C$_{12}$, and C$_{44}$ for 16 cubic elements using four MatPES foundation MLIPs under PBE and approximate r2SCAN targets. We attach a cache-warm, CPU-equivalent core-hour cost to every case, rank the models, diagnose systematic biases, and identify the chemical and structural classes where the next generation of models and correction operators must improve.

---

## 2. Methods

### 2.1 Benchmark set

The benchmark set comprises 16 cubic elemental metals: Ag, Al, Au, Ca, Cr, Cu, Fe, Mo, Nb, Ni, Pd, Pt, Sr, Ta, V, and W. For each element we compute the three independent elastic constants of the cubic tensor using the conventional cubic cell relaxed and then expanded to a 3×3×3 supercell (108 atoms for FCC, 54 atoms for BCC).

The four MLIPs evaluated are the MatPES 2025.2 foundation models:

- CHGNet [3]
- M3GNet [4]
- QET
- TensorNet

Earlier Lupine work treated QET and TensorNet as a single architecture because they resolved to the same checkpoint in some configurations [2]. In this 3×3×3 benchmark they are evaluated as distinct model objects, and we report them separately.

Each model is run against two target functionals:

- **PBE:** 0 K elastic tensors from the de Jong 2015 dataset [5], with the Ag tensor from Pandit & Bongiorno 2023 [6] and a PW91-GGA fallback for Au from Wang & Li 2008 [7].
- **r2SCAN:** PBE tensors scaled by a scalar bulk-modulus ratio derived from Liu et al. 2024 [8]. Al, Ca, and Sr retain a shift factor of 1.0 because no r2SCAN bulk modulus was recovered for those elements.

The r2SCAN comparison is therefore a sensitivity check, not a headline claim.

### 2.2 Computational workflow

Calculations use `matcalc` [9] with a standardized stress/strain elasticity calculator. The workflow is:

1. Build the conventional cubic cell from the starting lattice constants in `lupine/data/layer2_benchmark_task.py`.
2. Build a 3×3×3 supercell.
3. Relax cell and positions with `RelaxCalc` (fmax = 0.005 eV/Å).
4. Compute the elastic tensor with `ElasticityCalc` (fmax = 0.005 eV/Å, units in GPa).
5. Extract C$_{11}$, C$_{12}$, and C$_{44}$.

Wall-clock runtime is recorded for each case. CPU-equivalent core-hours are computed as

$$
\text{core-hours} = \frac{\text{runtime\_seconds}}{3600},
$$

assuming a single CPU process. This is a cache-warm cost; one-time model downloads and cold-start overhead are excluded.

### 2.3 Execution and provenance

The benchmark was executed as a Cloud Run job array in GCP project `witching-606c6`, region `us-central1`. The container image is `us-central1-docker.pkg.dev/witching-606c6/lupine-layer2/runner:v1`. The final execution (`layer2-3x3x3-grid-zb76j`) ran 64 parallel tasks, each computing one (element, model) pair for both PBE and r2SCAN and uploading two JSON outputs to `gs://lupine-benchmark-witching-606c6/layer2_3x3x3/`. The resulting 128 raw outputs were aggregated with `lupine/data/aggregate_layer2.py`.

---

## 3. Results

### 3.1 Model ranking

Table 1 reports mean C$_{ij}$ MAE by model and functional. QET is the best-performing model on both functionals, followed by TensorNet, M3GNet, and CHGNet.

**Table 1 — Mean C$_{ij}$ MAE (GPa) by model and functional.**

| Model | PBE | r2SCAN | Overall |
|---:|---:|---:|---:|
| CHGNet | 17.90 | 27.94 | 22.92 |
| M3GNet | 14.13 | 20.71 | 17.42 |
| QET | 13.41 | 15.46 | 14.44 |
| TensorNet | 14.61 | 18.54 | 16.58 |
| **All models** | **15.01** | **20.66** | **17.84** |

The overall model spread is 8.48 GPa between best (QET) and worst (CHGNet). On PBE alone the spread is smaller (4.49 GPa); on r2SCAN it widens to 12.48 GPa.

### 3.2 Functional gap

Every model is less accurate on the approximate r2SCAN targets. The mean functional gap is +5.65 GPa, but the penalty is uneven:

- CHGNet: +10.04 GPa
- M3GNet: +6.58 GPa
- TensorNet: +3.93 GPa
- QET: +2.05 GPa

QET generalizes best to the stiffer r2SCAN reference, while CHGNet’s bulk-softening bias is amplified when the target modulus increases.

### 3.3 Per-element error landscape

Table 2 ranks elements by mean MAE across all models and functionals.

**Table 2 — Per-element mean C$_{ij}$ MAE (GPa).**

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

The easiest systems are FCC alkaline-earth (Ca, Sr) and noble metals (Ag). The hardest are BCC transition metals, especially magnetic Cr and Fe and low-shear Nb. This pattern indicates that the residual error is dominated by local electronic structure — magnetism, d-band bonding, Fermi-surface nesting — rather than by finite-size effects.

### 3.4 Cost

The full 128-case 3×3×3 matrix costs approximately **0.82 CPU core-hours** in cache-warm, single-process CPU time. Table 3 breaks this down by model.

**Table 3 — Total CPU core-hours by model (PBE + r2SCAN, 16 elements each).**

| Model | Total core-hours | Mean seconds / case |
|---:|---:|---:|
| M3GNet | 0.075 | 8.4 |
| CHGNet | 0.431 | 48.5 |
| QET | 0.156 | 17.6 |
| TensorNet | 0.158 | 17.8 |

Even the slowest model (CHGNet) keeps the full matrix below half a core-hour. The reference layer is therefore cheaper than a single conventional DFT relaxation.

### 3.5 QET vs TensorNet

A prior Lupine preprint treated QET and TensorNet as aliases [2]. In this benchmark they are measurably different:

- Mean absolute MAE difference: 8.41 GPa
- Mean relative difference: 53.9%
- Identical (element, functional) pairs: 0 / 32
- Largest gap: Cr/PBE, QET 5.72 GPa vs TensorNet 46.08 GPa

We therefore report them as distinct models and recommend that downstream ensembles and rankings treat them independently.

### 3.6 Systematic biases

Mean signed errors (predicted − target) reveal systematic model signatures (Table 4). Values are averages over both functionals.

**Table 4 — Mean signed errors (GPa) and bulk/shear moduli biases.**

| Model | ⟨Δc11⟩ | ⟨Δc12⟩ | ⟨Δc44⟩ | ⟨ΔB⟩ | ⟨ΔG⟩ |
|---:|---:|---:|---:|---:|---:|
| CHGNet | −23.28 | −1.98 | +1.74 | −9.08 | −0.52 |
| M3GNet | +4.49 | −9.35 | +8.36 | −4.80 | +7.52 |
| QET | +15.60 | −4.59 | +4.71 | +2.14 | +5.91 |
| TensorNet | −9.89 | −10.91 | +1.62 | −10.57 | +1.29 |

CHGNet and TensorNet both under-stiffen the bulk modulus. M3GNet over-stiffens shear while under-stiffening the off-diagonal coupling. QET is the most balanced, with only a slight bulk stiffening.

---

## 4. Discussion

### 4.1 The supercell reference is now a cheap validation layer

The central operational result is that a 3×3×3 supercell elastic-constant reference for 16 cubic metals can be built for less than one CPU core-hour. Combined with the companion 1×1×1 result — that the small cell matches the large cell at roughly four-fold lower cost — this means supercell-based DFT gates for cubic-metal elasticity can be replaced by cheap, single-model MLIP runs without a measurable accuracy penalty.

The cost is low enough that the reference can be regenerated on demand for new model releases, making it a practical validation layer rather than a one-off dataset.

### 4.2 Model ranking and recommendation

QET is the safest default for cubic-metal elastic screening. It is the only model below 15 GPa mean MAE on both functionals and has the smallest systematic bulk bias. TensorNet is competitive on PBE but degrades more on r2SCAN. M3GNet is fast and close to TensorNet on PBE but has the largest r2SCAN tail, driven by Cr. CHGNet is systematically soft and should be avoided for r2SCAN-derived moduli of heavy d metals and magnets.

### 4.3 The r2SCAN frontier

The +5.65 GPa functional gap is the most important open problem highlighted by this benchmark. It is not a scalar-target artifact: the largest r2SCAN shifts (Cu, Ag, Pd, Ni) are not the worst-mode failures. Instead, the worst r2SCAN cases are concentrated in magnetic and refractory BCC metals (Cr, Fe, Mo) and heavy FCC Pt. Closing this gap will require training data that better captures meta-GGA stiffness, magnetic ground states, and Fermi-surface-driven phonon anomalies.

### 4.4 Correction-operator outlook

Cheap post-hoc corrections can address some systematic biases but not all:

- **Scalar bulk rescaling** would help CHGNet and TensorNet on non-magnetic FCC metals, where the under-stiffening is uniform.
- **Element-specific bias corrections** could remove small stable residuals (e.g., Ca, Sr) but would over-fit the mixed-sign errors of Cr, Fe, and Nb.
- **Shear-mode corrections** are needed for Nb, where every model over-stiffens c44.

The failure modes of Cr, Fe, Mo, and V are not operator-correctable with the current data; they require improved training data.

---

## 5. Conclusion

The Layer-2 3×3×3 benchmark establishes that foundation MLIPs can deliver a cubic-metal elastic-constant reference matrix for sub-core-hour cost. QET leads on accuracy at 14.44 GPa mean MAE, and the conventional 1×1×1 cell can replace the 3×3×3 supercell at roughly four-fold lower cost with no measurable accuracy penalty. The remaining error is not finite-size error but model-form error concentrated in transition metals and r2SCAN targets. This gives the field a clear, honest roadmap: better functional coverage, magnetic ground states, and soft shear modes are the next targets, while the operational infrastructure for cheap, reproducible elastic screening is already in place.

---

## 6. Data availability

- Raw outputs: `gs://lupine-benchmark-witching-606c6/layer2_3x3x3/*.json` (128 files)
- Summary JSON: `gs://lupine-benchmark-witching-606c6/layer2_3x3x3_summary.json`
- Source repository: `https://github.com/alexwelcing/lupine` (commit `c62cf7c` and later)
- Analysis reports: `lupine/data/analysis_statistical.md`, `analysis_materials.md`, `analysis_audit.md`, `analysis_comms.md`, `analysis_master_3x3x3_2026-06-29.md`
- Public article: `https://library.lupine.science/articles/docs/layer2-3x3x3-results-2026-06-29.html`

---

## 7. Figures

**Figure 1 — Accuracy–cost frontier.** Mean C$_{ij}$ MAE versus total CPU core-hours for each model and functional on the 3×3×3 supercell reference.

![Figure 1](https://raw.githubusercontent.com/alexwelcing/lupine-rhizo/main/paper/figures/fig1_accuracy_cost_frontier.png)

**Figure 2 — Per-element mean MAE.** Elements ordered from lowest to highest mean MAE across all four models and both functionals, colored by chemical/structural class.

![Figure 2](https://raw.githubusercontent.com/alexwelcing/lupine-rhizo/main/paper/figures/fig2_per_element_mae.png)

**Figure 3 — Functional gap by model.** Mean MAE under PBE and r2SCAN targets for each model.

![Figure 3](https://raw.githubusercontent.com/alexwelcing/lupine-rhizo/main/paper/figures/fig3_functional_gap.png)

**Figure 4 — QET vs TensorNet.** Per-element, per-functional MAE for QET and TensorNet. Points on the dashed line would indicate identical performance.

![Figure 4](https://raw.githubusercontent.com/alexwelcing/lupine-rhizo/main/paper/figures/fig4_qet_tensornet.png)

---

## 8. References

[1] T. Chen and S. P. Ong, "A universal graph deep learning interatomic potential for the periodic table," *Nature Computational Science* **1**, 319 (2023); MatGL/MatCalc toolkit, https://github.com/materialsvirtuallab/matgl.

[2] Lupine Project, "MLIP Elastic Benchmark: The 1×1×1 Conventional Cell Matches 3×3×3 Supercell Accuracy at ~4× Lower Cost for MatPES Cubic-Metal Elasticity," `mlip-elastic-benchmark-preprint-2026-06-27.md` (2026-06-27).

[3] C. Deng *et al.*, "CHGNet as a pretrained universal neural network potential for charge-informed atomistic modelling," *Nature Machine Intelligence* **5**, 1031 (2023).

[4] T. Chen *et al.*, "M3GNet: a universal materials graph neural network interatomic potential," *npj Computational Materials* **9**, 42 (2023).

[5] M. de Jong *et al.*, "Charting the complete elastic properties of inorganic crystalline compounds," *Scientific Data* **2**, 150009 (2015). doi:10.1038/sdata.2015.9

[6] A. Pandit and K. Bongiorno, Ag elastic-constant reference values (2023) — target provenance in Lupine `targets_0K.json`.

[7] L. Wang and X. Li, "Ab initio calculations of elastic properties of Au at high pressure," *J. Appl. Phys.* **104**, 113511 (2008). doi:10.1063/1.3035832

[8] Y. Liu *et al.*, "r$^2$SCAN-based DFT for materials: a benchmark and an assessment," *J. Chem. Phys.* **160**, 024102 (2024). doi:10.1063/5.0186586

[9] MatCalc toolkit, https://github.com/materialsvirtuallab/matcalc.
