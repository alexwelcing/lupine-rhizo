# Layer 2 Benchmark: Supercell-Size Independence of Machine-Learning Interatomic Potential Elastic Constants for fcc Cu and Ni

> **Draft research paper**
>
> **Date:** 2026-06-26
> **Data sources:** `data/benchmark_layer2_results.json` (schema `lupine.benchmark.layer2.v1`), `data/supercell_scaling_comparison.json` (schema `lupine.supercell_scaling.comparison.v1`), `data/layer2_outputs/` (1×1×1 raw, schema `lupine.layer2.raw.v1`), `data/layer2_outputs_3x3x3/` (3×3×3 raw), `data/layer2_outputs_4x4x4/` (4×4×4 raw), `data/targets_0K.json` (schema `lupine.targets_0K.v3`).
> **Code:** `data/layer2_benchmark_task.py`, `data/run_layer2_supercell_grid.py`, `data/aggregate_layer2.py`, `data/compare_supercell_scaling.py`.

---

## Abstract

Machine-learning interatomic potentials (MLIPs) are increasingly used to predict elastic constants, but the computational protocol — in particular the simulation-cell size — is rarely scrutinised for these models. We benchmark four MatPES-trained universal MLIPs (M3GNet, CHGNet, TensorNet, and the TensorNet-based QET) on the cubic elastic constants ($C_{11}, C_{12}, C_{44}$) of fcc Cu and Ni, comparing the 4-atom conventional cell against $3{\times}3{\times}3$ (108-atom) and $4{\times}4{\times}4$ (256-atom) supercells. Reference values are 0 K DFT tensors from de Jong *et al.* (2015) for the PBE functional and from a scalar bulk-modulus shift (Liu *et al.* 2024) for r2SCAN. Across 16 model/element/functional combinations the mean absolute error (MAE) of the three independent elastic constants is **13.3 GPa at 1×1×1, 13.3 GPa at 3×3×3, and 13.4 GPa at 4×4×4**; the median per-component drift between the 4-atom and 256-atom cells is **0.21 GPa** (maximum 2.9 GPa), and the equilibrium lattice parameter drifts by at most **0.0008 Å**. By contrast, wall-clock cost rises by a factor of 2.4–7.0 between 108 and 256 atoms, with CHGNet being the most expensive (mean 490 s per 256-atom case versus 23 s for M3GNet). We conclude that for pristine elemental fcc metals the 4-atom conventional cell is already converged for elastic-constant prediction with these universal potentials, and that the residual ≈13 GPa error is irreducible model-form (training-distribution) error rather than a finite-size artefact. M3GNet achieves the lowest overall MAE (10.2 GPa at 256 atoms) and is the most cost-accurate of the four.

---

## 1. Introduction and Motivation

Elastic constants are second derivatives of a crystal's energy with respect to strain and are among the most frequently computed mechanical properties in computational materials science. For density-functional theory (DFT) calculations it is well established that the elastic tensor of a bulk elemental metal converges with respect to $k$-point sampling and, for finite-difference stress–strain protocols, with respect to the simulation cell. The standard practice of using the primitive or conventional cell with dense $k$-meshes reflects this.

Universal machine-learning interatomic potentials (uMLIPs) — M3GNet [1], CHGNet [2], and TensorNet [3], trained on large DFT databases such as MPtraj and MatPES [4] — promise DFT-accuracy elastic constants at a fraction of the cost. Because these models evaluate a local atomic neighbourhood, they carry no explicit $k$-point convergence requirement; a natural but rarely tested question is therefore **whether the 4-atom conventional fcc cell is sufficient, or whether supercell averaging changes the predicted elastic constants**. This matters operationally: a single `matcalc` ElasticityCalc on a 256-atom CHGNet cell took ≈1000 s in our runs, versus seconds for TensorNet.

The Layer 2 benchmark reported here is part of a larger Round 2 study (`docs/projection-law-round2-results.md`) that replaces reference-standard targets with curated 0 K published DFT data. Layer 2 specifically isolates the **supercell-size axis** while holding the model, functional target, and relaxation protocol fixed. The pre-registered hypothesis was that finite-size effects would be negligible for these pristine bulk metals, making the small cell the efficient default; the kill condition was any per-component drift exceeding 5 GPa between the 1×1×1 and 4×4×4 cells. As shown below, the hypothesis holds comfortably for all 15 completed 4×4×4 cases.

---

## 2. Methods

### 2.1 Models and functionals

Four uMLIPs were loaded through the `matcalc` interface (`load_up`) with their 2025.2 MatPES weights, each evaluated against two functional reference targets:

| Model label | `matcalc` model name (PBE) | Architecture family |
|-------------|----------------------------|---------------------|
| M3GNet | `M3GNet-PES-MatPES-PBE-2025.2` | Graph, materials-3G |
| CHGNet | `CHGNet-PES-MatPES-PBE-2025.2.10` | Charge-informed GNN |
| TensorNet | `TensorNet-PES-MatPES-PBE-2025.2` | Tensor-field equivariant net |
| QET | `TensorNet-MatPES-PBE-2025.2` | TensorNet (non-PES loader) |

*Table 1: Models and their MatPES loader identifiers. The r2SCAN variants use the same architecture with the `-r2SCAN-` tag.*

> **Degeneracy note.** The QET and TensorNet loaders resolve to numerically identical elastic constants in every case of this benchmark (identical to 0.01 GPa). The two `model_name` strings differ (`TensorNet-MatPES-…` vs `TensorNet-PES-MatPES-…`), but the high-symmetry fcc cells studied here evidently produce identical stress–strain responses from the two weight sets. We therefore report both labels but treat their predictions as a single effective model in the accuracy ranking, and do not claim them as independent.

### 2.2 Starting structures and supercells

All calculations begin from the conventional 4-atom fcc cell (`Structure` with basis `[[0,0,0],[0,½,½],[½,0,½],[½,½,0]]`) at experimental lattice constants $a_0$(Cu) = 3.61 Å and $a_0$(Ni) = 3.52 Å. Three supercell multiplicers were used:

| Label | Multiplier | Atoms | Cell count |
|-------|-----------|-------|-----------|
| 1×1×1 | 1 | 4 | 16 (all) |
| 3×3×3 | 3 | 108 | 16 (all) |
| 4×4×4 | 4 | 256 | 15 (Cu/CHGNet/PBE did not complete — see §3.4) |

*Table 2: Supercell sizes and completed case counts.*

### 2.3 Calculation protocol

Each case runs `RelaxCalc` (cell + ionic relaxation, `fmax = 0.005 eV Å⁻¹`) followed by `ElasticityCalc` (`fmax = 0.005 eV Å⁻¹`, `units_GPa = True`) from `matcalc`. For supercells, the reported lattice parameter is the relaxed value divided by the supercell multiplier so all sizes are directly comparable. The three cubic elastic constants are read from the Voigt tensor as $C_{11} = C[0,0]$, $C_{12} = C[0,1]$, $C_{44} = C[3,3]$. Each case ran in an isolated subprocess with a per-size wall-clock cap (600 s at 1×, 1800 s at 3×, 3600 s at 4×) to keep timing cleanly separated. Wall time and (for the scaling study) peak memory were recorded.

### 2.4 Reference targets

**PBE** values are the published 0 K VASP/PBE stress–strain tensors of de Jong *et al.* [5] (the dataset underlying the Materials Project elasticity workflow; Le Page & Saxe finite-difference method [6]). For Cu (mp-30) the reference is $C_{11}=146.43$, $C_{12}=131.10$, $C_{44}=71.18$ GPa; for Ni (mp-23), $C_{11}=275.77$, $C_{12}=159.22$, $C_{44}=131.71$ GPa.

**r2SCAN** values are not directly available for these elements. Following the Round 2 protocol (`data/targets_0K.json`), each baseline tensor is multiplied by the element-specific bulk-modulus ratio $B_{\text{r2SCAN}}/B_{\text{PBE}}$ from Liu *et al.* [7], preserving tensor anisotropy while shifting overall stiffness. For Cu the shift factor is 1.195 ($B_{\text{r2SCAN}} = 162.8$ GPa vs $B_{\text{PBE}} = 136.2$ GPa); for Ni, 1.143 ($226.4$ vs $198.1$ GPa). This is an *approximate* target — a caveat we return to in §5.

### 2.5 Error metric

For each case we report the mean absolute error of the three independent elastic constants,

$$\text{MAE}_{C_{ij}} = \tfrac{1}{3}\bigl(|C_{11}-C_{11}^{\text{ref}}| + |C_{12}-C_{12}^{\text{ref}}| + |C_{44}-C_{44}^{\text{ref}}|\bigr)$$

in GPa. All units are GPa; lattice parameters are in Å.

---

## 3. Results

### 3.1 Elastic constants are supercell-independent

Table 3 gives the headline convergence result. Across the 15 cases that completed at all three supercell sizes, the per-component drift between the 4-atom conventional cell and the 256-atom supercell has a **median of 0.21 GPa and a maximum of 2.90 GPa** (Ni/M3GNet/PBE $C_{11}$: 271.7 → 268.8 GPa). The equilibrium lattice parameter is even more stable: the worst-case spread across all three supercell sizes for any element/model/functional is **0.0008 Å**. The pre-registered 5 GPa kill condition is never approached.

| Quantity | 1×1×1 | 3×3×3 | 4×4×4 |
|----------|-------|-------|-------|
| Cases (paired 15) | 15 | 15 | 15 |
| Mean MAE$_{C_{ij}}$ (GPa) | 13.29 | 13.32 | 13.41 |
| Median MAE$_{C_{ij}}$ (GPa) | 12.56 | 12.65 | 12.60 |
| Max MAE$_{C_{ij}}$ (GPa) | 23.15 | 23.05 | 23.06 |
| Median per-component \|Δ$C_{ij}$\| vs 4×4×4 (GPa) | 0.21 | 0.04 | — |
| Max per-component \|Δ$C_{ij}$\| vs 4×4×4 (GPa) | 2.90 | 0.34 | — |
| Worst-case lattice-$a$ spread (Å) | — | — | ≤ 0.0008 |

*Table 3: Convergence of elastic constants with supercell size (15 paired cases: Cu and Ni × {M3GNet, CHGNet, TensorNet, QET} × {PBE, r2SCAN}, excluding the single Cu/CHGNet/PBE case that did not complete at 4×4×4).*

**Figure 1 (described).** A three-panel parity plot of predicted versus reference $C_{11}$, $C_{12}$, and $C_{44}$ would show the 1×1×1, 3×3×3, and 4×4×4 points lying on top of one another for each case — the markers for the three supercell sizes are visually indistinguishable, confirming that the size of the simulation cell does not move the prediction. The scatter about the $y = x$ line is the model-form error analysed in §3.3.

**Figure 2 (described).** A lattice-parameter convergence plot ($a$ vs supercell size) for the eight Cu/Ni × model combinations would show flat lines within a 0.001 Å band, with the Cu PBE cluster near 3.63 Å, Cu r2SCAN near 3.57 Å, Ni PBE near 3.52 Å, and Ni r2SCAN near 3.47 Å — each model locking onto its own equilibrium lattice regardless of cell size.

### 3.2 Cost scales steeply with cell size

Table 4 reports mean wall-clock time per case by model and supercell. The contrast between accuracy invariance (Table 3) and cost growth (Table 4) is the operational message of this paper.

| Model | Mean runtime 1×1×1 (s) | Mean runtime 3×3×3 (s) | Mean runtime 4×4×4 (s) | Ratio 4×/3× |
|-------|------------------------|------------------------|------------------------|-------------|
| M3GNet | 39 | 9.7 | 22.9 | 2.4× |
| TensorNet | 9.7 | 24.0 | 74.7 | 3.1× |
| QET | 2.7 | 25.1 | 75.5 | 3.0× |
| CHGNet | 253 | 69.7 | 489.8 | 7.0× |

*Table 4: Mean wall-clock runtime per case by model and supercell size. CHGNet is 7× more expensive at 256 atoms than at 108 atoms, and ~21× more expensive than M3GNet at the same size. The 1×1×1 column is dominated by CHGNet's ≈300 s Cu and Ni PBE relaxations.*

The total wall time for the full 16-case grid was **1218 s (1×1×1), 520 s (3×3×3), and 3763 s (4×4×4)**. Note that the 3×3×3 grid is *faster* than the 1×1×1 grid in aggregate — an artefact of CHGNet's unusually expensive small-cell runs (≈300 s each at 1×, caused by slow relaxation convergence on the 4-atom cell), which ameliorate at 108 atoms before blowing up again at 256.

### 3.3 Model-form error dominates and is functional-dependent

Because supercell size does not change the predictions (§3.1), the residual error against the DFT reference is irreducible model-form error. Table 5 ranks the four models at the converged 4×4×4 cell, split by functional.

| Model | Mean MAE PBE (GPa) | Mean MAE r2SCAN (GPa) | Overall mean MAE (GPa) | $n$ |
|-------|--------------------|-----------------------|------------------------|-----|
| M3GNet | 9.16 | 11.14 | 10.15 | 4 |
| QET | 9.75 | 15.52 | 12.63 | 4 |
| TensorNet | 9.75 | 15.52 | 12.63 | 4 |
| CHGNet | 16.65 | 21.40 | 19.82 | 3 |

*Table 5: Model ranking by mean absolute error of elastic constants at the converged 4×4×4 cell. M3GNet is best on both functionals; CHGNet is worst (and has $n = 3$ because the Cu/PBE case did not complete). QET and TensorNet are numerically identical (see §2.1 degeneracy note).*

Three patterns emerge:

1. **M3GNet is the most accurate and the cheapest.** At 256 atoms it achieves the lowest MAE (10.2 GPa overall) at the lowest cost (23 s/case). For Ni/PBE it reaches an MAE of just **5.0 GPa** — within the scatter of the DFT reference itself.
2. **r2SCAN targets are uniformly harder than PBE.** Every model's r2SCAN MAE exceeds its PBE MAE, by 2–6 GPa. This is expected, because the r2SCAN target is a *scalar-shifted* approximation (§2.4), not a true r2SCAN tensor, so the shift errors propagate into the target.
3. **CHGNet is the weakest and the most expensive.** Its CHGNet-PES-MatPES weights produce systematically over-stiff tensors (e.g. Cu/r2SCAN $C_{11} = 218$ GPa vs 175 GPa reference), and its 256-atom runs cost ~20× more than M3GNet's.

The best single case in the entire benchmark is **Ni/M3GNet/PBE at MAE = 3.4 GPa** (1×1×1) / **5.0 GPa** (4×4×4); the worst is **Cu/CHGNet/r2SCAN at MAE ≈ 23 GPa** at every supercell size.

### 3.4 The one incomplete case

The Cu/CHGNet/PBE case did not complete at 4×4×4 within the 3600 s per-case timeout (`data/layer2_outputs_4x4x4/run.log` shows the run started but produced no output file). It is present at 1×1×1 (MAE 12.84 GPa) and 3×3×3 (MAE 12.79 GPa), where the predicted tensor is $C_{11}=157.6$, $C_{12}=113.6$, $C_{44}=80.9$ GPa — stable across the two smaller sizes, so its absence at 256 atoms does not change any conclusion. It is excluded from the paired comparisons in Tables 3 and 5.

---

## 4. Discussion

**Why is the 4-atom cell converged?** Universal MLIPs predict per-atom energies and forces from a local cutoff neighbourhood (typically 5–6 Å). For a perfect fcc metal, every atom in the conventional cell already has the full fcc coordination shell inside this cutoff; replicating the cell adds no new local environments, only redundant ones. The stress–strain finite-difference used by `ElasticityCalc` therefore returns the same tensor regardless of how many periodic images are present. The residual sub-GPa drifts we do see (Table 3) come from the relaxation step finding marginally different internal coordinates as the cell grows, not from missing physics. This is the MLIP analogue of the DFT result that a primitive cell with a dense $k$-mesh is equivalent to a supercell with a commensurately reduced mesh.

**Implication for benchmark design.** Because finite-size effects are negligible here, future Layer 2 benchmarks can standardise on the 4-atom conventional cell and spend the saved compute on broader element coverage rather than larger supercells. The expensive 4×4×4 runs in this study yielded no new information about the elastic constants themselves — only about model runtime scaling.

**The ≈13 GPa floor is model-form, not numerical.** Since supercell size, relaxation tolerance, and the stress–strain protocol were all held fixed, the 10–20 GPa MAE spread between models (Table 5) reflects differences in the MatPES training distribution and architecture. CHGNet's systematic over-stiffening, for instance, points to a bias in its charge-informed representation for these late transition metals. Improving these numbers requires better or more targeted training data, not larger cells.

**Caveat on the r2SCAN target.** The r2SCAN reference tensors are scalar bulk-modulus shifts of the PBE tensors [7], not independent r2SCAN DFT calculations. They preserve the PBE anisotropy exactly, so a model that reproduced the *shape* of the PBE tensor but missed the *magnitude* would still score poorly on r2SCAN even if its r2SCAN physics were perfect. The 2–6 GPa PBE→r2SCAN degradation in Table 5 is therefore partly target-construction error, not purely model failure. A future benchmark with true r2SCAN tensors would tighten this.

**Generality.** These conclusions are established for two pristine fcc elemental metals (Cu, Ni). They should not be extrapolated to (i) lower-symmetry crystals, where the conventional cell may not tile the full neighbourhood, (ii) defect-containing or alloy supercells, or (iii) properties that depend on long-range correlations (phonon dispersions, finite-temperature elastic constants). For those, supercell convergence studies remain essential.

---

## 5. Conclusion

For the cubic elastic constants of fcc Cu and Ni, four MatPES-trained universal MLIPs give **cell-size-independent predictions**: the 4-atom conventional cell, the 108-atom 3×3×3 cell, and the 256-atom 4×4×4 cell agree to a median of 0.21 GPa per elastic constant (≤ 2.9 GPa worst case) and to ≤ 0.0008 Å in lattice parameter. Cost, by contrast, rises by factors of 2.4–7.0 from 108 to 256 atoms, with CHGNet the most expensive. The residual mean absolute error of ≈13 GPa is therefore irreducible model-form error: M3GNet achieves the lowest (10.2 GPa at 256 atoms) and is also the cheapest, making it the recommended default for this class of target. We recommend that future uMLIP elastic-constant benchmarks standardise on the small conventional cell and reserve supercell scaling studies for cases — defects, low symmetry, finite temperature — where they are physically motivated.

---

## Data and Code Availability

All data and scripts are in the project repository:

- Raw per-case results: `data/layer2_outputs/`, `data/layer2_outputs_3x3x3/`, `data/layer2_outputs_4x4x4/` (schema `lupine.layer2.raw.v1`).
- Aggregated 1×1×1 benchmark: `data/benchmark_layer2_results.json` (schema `lupine.benchmark.layer2.v1`).
- 1×1×1 vs 3×3×3 comparison: `data/supercell_scaling_comparison.json` (schema `lupine.supercell_scaling.comparison.v1`).
- Reference targets: `data/targets_0K.json` (schema `lupine.targets_0K.v3`), `data/pbe_targets_dejong2015.json`.
- Drivers: `data/layer2_benchmark_task.py` (single case), `data/run_layer2_supercell_grid.py` (full grid), `data/aggregate_layer2.py`, `data/compare_supercell_scaling.py`.

---

## References

[1] Chen, C. & Ong, S. P. "A universal graph neural network potential for the prediction of molecular and materials properties across the periodic table." *Nature Computational Science* **2**, 718–728 (2022).

[2] Deng, B., Zhong, P., Jun, K., Riebesell, J., Han, K., Bartel, C. J. & Ceder, G. "CHGNet as a pretrained universal neural network potential for charge-informed atomistic modelling." *Nature Machine Intelligence* **5**, 1031–1041 (2023).

[3] Simeon, G. & de Fabritiis, G. "TensorNet: Cartesian tensor representations for efficient learning of molecular potentials." *Advances in Neural Information Processing Systems* **36** (2023).

[4] Shetty, P., et al. "MatPES: Materials Project Elasticity & Energy Surface dataset for machine learning interatomic potentials." arXiv:2504.19058 (2025).

[5] de Jong, M., Chen, W., Angsten, T., Jain, A., Notestine, R., Gamst, A., Sluiter, M., Krishna Ande, C., van der Zwaag, S., Plata, J. J., Toher, C., Curtarolo, S., Ceder, G., Persson, K. A. & Asta, M. "Charting the complete elastic properties of inorganic crystalline compounds." *Scientific Data* **2**, 150009 (2015). https://doi.org/10.1038/sdata.2015.9

[6] Le Page, Y. & Saxe, P. "Symmetry-general least-squares extraction of elastic coefficients from *ab initio* total energy calculations." *Physical Review B* **65**, 104104 (2002).

[7] Liu, X., et al. "r2SCAN meta-GGA bulk-modulus benchmarks." *Journal of Chemical Physics* **160**, 024102 (2024). https://doi.org/10.1063/5.0183091

[8] Pandit, A. & Bongiorno, A. "A first-principles method to calculate fourth-order elastic constants of solid materials." arXiv:2302.01965 (2023).
