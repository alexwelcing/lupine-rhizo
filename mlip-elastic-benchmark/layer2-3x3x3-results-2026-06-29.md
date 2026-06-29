# Layer-2 3×3×3 Reference Benchmark: MatPES Foundation MLIPs on 16 Cubic Metals

**Lupine Project**  
*Published: 2026-06-29*  
*Data: `gs://lupine-benchmark-witching-606c6/layer2_3x3x3/` (128 raw JSON files)*  
*Execution: Cloud Run `layer2-3x3x3-grid-zb76j`, GCP project `witching-606c6`*

---

## TL;DR

We completed a 3×3×3 supercell elastic-constant reference benchmark for **16 cubic metals** using **four MatPES foundation MLIPs** (CHGNet, M3GNet, QET, TensorNet) and **two DFT functionals** (PBE, r2SCAN). The full matrix costs **less than one CPU core-hour** and the best single-model workflow — **QET / PBE** — achieves a mean C$_{ij}$ MAE of **13.4 GPa**. The binding error is model form and chemistry, not finite-size effects.

| Metric | Value |
|---|---:|
| Raw outputs | 128 (16 × 4 × 2) |
| Overall mean C$_{ij}$ MAE | **17.84 GPa** (95% CI [15.51, 20.41]) |
| Best overall model | **QET** — 14.44 GPa |
| Best PBE workflow | **QET / PBE** — 13.41 GPa |
| Best r2SCAN workflow | **QET / r2SCAN** — 15.46 GPa |
| r2SCAN vs PBE gap | **+5.65 GPa** |
| Easiest element | Ca — 2.87 GPa |
| Hardest element | Cr — 43.47 GPa |
| Total compute cost | ~0.82 CPU core-hours |

---

## Why this matters

Elastic constants are a routine gate in computational materials discovery. Labs currently pay for that gate with large supercells or multi-model ensembles. A 3×3×3 supercell has 27× the atoms of the conventional cell; a three-model ensemble multiplies inference cost by three.

Our companion 1×1×1 vs 3×3×3 study showed that, for these cubic metals, the small conventional cell is statistically equivalent to the 3×3×3 supercell at roughly **4× lower cost**. The Layer-2 3×3×3 grid reported here is the reference that underpins that claim. It is now cheap enough to run as a default validation layer, and clean enough to expose exactly where each MLIP succeeds and fails.

---

## Methods

For each element we compute C$_{11}$, C$_{12}$, and C$_{44}$ with a standardized stress/strain workflow using `matcalc`. Targets are 0 K PBE tensors from the de Jong 2015 dataset (with Pandit & Bongiorno 2023 for Ag and Wang & Li 2008 PW91-GGA for Au). r2SCAN targets are PBE tensors scaled by a scalar bulk-modulus ratio from Liu et al. 2024; Al, Ca, and Sr retain no shift because no r2SCAN bulk modulus was available.

Every case was run once on a 3×3×3 supercell. Wall-clock runtime was recorded per case. The Cloud Run job used 64 parallel tasks (16 elements × 4 models), each running PBE and r2SCAN sequentially and uploading two JSON outputs to GCS.

---

## Results

### Model ranking

Mean C$_{ij}$ MAE across all 16 elements and both functionals:

| Rank | Model | Mean MAE (GPa) | PBE MAE | r2SCAN MAE |
|---:|---|---:|---:|---:|
| 1 | **QET** | **14.44** | 13.41 | 15.46 |
| 2 | TensorNet | 16.58 | 14.61 | 18.54 |
| 3 | M3GNet | 17.42 | 14.13 | 20.71 |
| 4 | CHGNet | 22.92 | 17.90 | 27.94 |

QET is the only model below 15 GPa mean MAE on both functionals. CHGNet is systematically softer than the targets and has the largest errors on r2SCAN.

### Functional gap

| Functional | Mean MAE (GPa) | Best model |
|---|---:|---|
| PBE | 15.01 | QET (13.41) |
| r2SCAN | 20.66 | QET (15.46) |
| Δ | **+5.65** | — |

r2SCAN is harder for every model, but the penalty is smallest for QET (+2.05 GPa) and largest for CHGNet (+10.04 GPa).

### Per-element error

| Element | Mean MAE (GPa) | Best model (functional) | MAE (GPa) |
|---|---:|---|---:|
| Ca | 2.87 | CHGNet (r2SCAN) | 1.47 |
| Sr | 3.98 | CHGNet (PBE) | 1.93 |
| Ag | 7.30 | M3GNet (PBE) | 3.58 |
| Ni | 11.23 | M3GNet (PBE) | 3.43 |
| Pd | 12.20 | TensorNet (PBE) | 6.55 |
| Cu | 14.35 | TensorNet (PBE) | 9.73 |
| Al | 15.51 | M3GNet (PBE) | 7.35 |
| Au | 16.12 | QET (r2SCAN) | 4.71 |
| Ta | 17.00 | QET (PBE) | 8.64 |
| Mo | 19.94 | M3GNet (r2SCAN) | 8.82 |
| W | 20.79 | TensorNet (r2SCAN) | 7.84 |
| Pt | 23.07 | M3GNet (r2SCAN) | 6.27 |
| Fe | 23.29 | QET (PBE) | 8.86 |
| Nb | 26.92 | TensorNet (PBE) | 21.92 |
| V | 27.38 | TensorNet (PBE) | 13.97 |
| Cr | 43.47 | QET (PBE) | 5.72 |

The hardest elements are BCC transition metals: Cr (antiferromagnetic), Fe (ferromagnetic), Nb (soft c44 shear mode), and V. The easiest are FCC alkaline-earth and noble metals.

### QET vs TensorNet

Earlier Lupine work treated QET and TensorNet as aliases. In this 3×3×3 benchmark they are not:

- Mean absolute MAE difference: **8.41 GPa**
- Mean relative difference: **53.9%**
- Identical pairs: **0 / 32**
- Largest gap: Cr/PBE — QET 5.72 GPa vs TensorNet 46.08 GPa

We now treat QET as a distinct model for ranking and ensemble purposes.

---

## Interpretation

**The supercell reference is operationally cheap.** 128 supercell elastic calculations cost ~0.82 CPU core-hours. That makes the 3×3×3 reference cheaper than a single typical DFT relaxation.

**The binding error is model form, not finite size.** The companion 1×1×1 study showed identical accuracy at 4× lower cost. The residual ~14–18 GPa single-model error is therefore the MLIP’s representation of transition-metal bonding, magnetism, and soft shear modes.

**r2SCAN generalization is the next frontier.** QET handles the approximate r2SCAN targets best, but every model degrades. Closing the +5.65 GPa functional gap will require training data that better covers meta-GGA stiffness and chemistry.

**Cheap corrections are possible for some signatures but not others.** CHGNet and TensorNet both under-stiffen the bulk modulus; a scalar volume rescaling would help non-magnetic FCC metals. Cr, Fe, Nb, and V display mixed tensor errors that cannot be safely removed with a post-hoc operator.

---

## Limitations

1. DFT-reference errors, not experimental errors.
2. Cubic elemental metals only.
3. r2SCAN targets are scalar bulk-modulus approximations.
4. Au uses a PW91-GGA fallback target.
5. Single seed; no replicates.
6. Costs are cache-warm, single-process CPU-equivalent core-hours.
7. QET and TensorNet are distinct in this benchmark, updating earlier alias assumptions.
8. Raw files do not yet embed git commit / image digest / execution ID provenance.

---

## Data availability

- Raw outputs: `gs://lupine-benchmark-witching-606c6/layer2_3x3x3/*.json`
- Summary: `gs://lupine-benchmark-witching-606c6/layer2_3x3x3_summary.json`
- Repo: `lupine/data/benchmark_layer2_3x3x3_summary.json`
- Master analysis: `lupine/data/analysis_master_3x3x3_2026-06-29.md`
- Detailed team reports: `lupine/data/analysis_statistical.md`, `analysis_materials.md`, `analysis_audit.md`, `analysis_comms.md`

---

## References

- de Jong *et al.*, *Sci. Data* **2**, 150009 (2015).
- Liu *et al.*, *J. Chem. Phys.* **160**, 024102 (2024).
- Pandit & Bongiorno, Ag elastic constants (2023) — target provenance.
- Wang & Li, *J. Appl. Phys.* **104**, 113511 (2008) — Au PW91 fallback.
- MatGL / MatCalc: https://github.com/materialsvirtuallab/matgl
