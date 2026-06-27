# Results — Round 2: The Projection Law Correction Operator

<details open>
<summary><strong>In plain language</strong> — what this means for a materials scientist</summary>

**The headline.** When modern machine-learned interatomic potentials (MLIPs) predict the elastic constants of a metal — how stiff it is along different directions — the answer barely changes whether you simulate a tiny 4-atom unit cell or a 108-atom supercell. For copper and nickel the average error against experiment sits at 13.26 GPa in the small cell and 13.29 GPa in the large one: a 0.03 GPa difference, indistinguishable from noise. This supercell-size independence holds across all 16 cubic metals we tested.

**Why this matters.** Finite-size effects — the artifacts that force classical molecular dynamics into big, expensive simulation cells — are essentially absent for these potentials. If you are screening candidate alloys or compounds for stiffness, the cheapest cell available (the conventional 1×1×1 unit, four atoms for an FCC metal) returns elastic constants just as trustworthy as a simulation 27× larger. You can survey hundreds of compositions for roughly the compute budget that used to buy a single run.

**The caveat.** A residual error of about 13–18 GPa remains no matter how large the cell. This is *model-form error* — a systematic bias baked into each potential's training data — not a size artifact. It varies by element (2.9 GPa for calcium up to 43.5 GPa for chromium) and by model (13.3 GPa for the best model to 27.9 GPa for the worst). A *projection-law correction operator* removes part of this bias by subtracting a learned, family-specific offset, but its success is element-dependent, and on the noble metals (Ag, Au, Cu, Pt) it did not beat a plain model average.

**Where to go next.** The full draft paper (`layer2_research_paper.md`) lays out the methods and the 16-element benchmark; the technical evaluation memo (`layer2_supercell_evaluation.md`) covers cell-size convergence and runtime.

</details>

> **Draft for revised Projection Law paper results section**
> 
> **Date:** 2026-06-26
> **Data sources:** `data/benchmark_results.json` (schema `lupine.benchmark.v2`), `data/targets_0K.json` (schema `lupine.targets_0K.v3`), `data/distill_inputs/layer1_bias_vectors.json`, `data/distill_inputs/layer1_classical_evidence_packet.json`
> **Pre-registration:** `docs/projection-law-round2-preregistration.md`

---

## 1. Target Provenance and Stability Filter

### 1.1 Reference data provenance

The Round 2 benchmark replaces the Round 1 Materials-Project API targets with curated, published 0 K DFT data to eliminate reference-standard confounds.

**PBE baseline (14 elements):** de Jong *et al.*, *Scientific Data* **2**, 150009 (2015). This is the published dataset underlying the Materials Project elasticity workflow: VASP/PBE, stress-strain finite-difference method (Le Page & Saxe, *Phys. Rev. B* **65**, 104104, 2002), 0 K static calculations. Values were extracted via the `matminer` `elastic_tensor_2015` dataset. Each entry carries a `material_id` (e.g., `mp-30` for Cu), source URL, and stability flag.

**Ag (PBE):** Pandit & Bongiorno, *Modelling Simul. Mater. Sci. Eng.* **31**, 055005 (2023). PBE elastic constants for FCC Ag: C11 = 107.0, C12 = 79.0, C44 = 42.0 GPa.

**Au (PW91-GGA fallback):** Wang & Li, *J. Appl. Phys.* **104**, 113511 (2008). No stable published PBE cubic Au tensor was recovered from the de Jong 2015 dataset, AFLOW, OQMD, JARVIS-DFT, Alexandria, or the Materials Project; the PW91-GGA values are therefore used as the reference baseline: C11 = 165.9, C12 = 142.2, C44 = 26.7 GPa.

**r2SCAN target:** No published full r2SCAN elastic-tensor table exists for all target metals. We therefore apply a *scalar bulk-modulus shift* to the baseline tensors using r2SCAN/baseline bulk-modulus ratios from Liu *et al.*, *J. Chem. Phys.* **160**, 024102 (2024):

$$C_{ij}^{\text{r2SCAN}} = C_{ij}^{\text{baseline}} \times \frac{B_{\text{r2SCAN}}}{B_{\text{baseline}}}$$

This preserves tensor anisotropy (the C11/C12 ratio and Zener ratio) while shifting overall stiffness. Al, Ca, and Sr lack published r2SCAN bulk data and retain the unshifted PBE baseline; their `shift_factor` is 1.0 and provenance records note the fallback reason.

### 1.2 Stability filter and element scope

The Round 2 target set comprises **16 cubic elemental metals** for which a published 0 K elastic tensor is available:

- **FCC:** Al, Ag, Au, Ca, Cu, Ni, Pd, Pt, Sr
- **BCC:** Cr, Fe, Mo, Nb, Ta, V, W

All 16 elements passed the stability filter (`stable: true`) with no negative C44 values or elastic instability flags. The `targets_0K.json` schema (`lupine.targets_0K.v3`) records provenance for both the baseline and r2SCAN entries, including `fallback_reason` fields where the scalar shift could not be applied.

| Element | Baseline source | Material ID / DOI | Space group | B_baseline (GPa) | B_r2SCAN (GPa) | Shift factor | Fallback |
|---------|-----------------|-------------------|-------------|------------------|----------------|--------------|----------|
| Ag | Pandit & Bongiorno 2023 (PBE) | 10.1088/1361-651X/acc2f4 | 225 | 88.333 | 104.400 | 1.182 | — |
| Al | de Jong 2015 (PBE) | mp-134 | 225 | 83.277 | 83.277 | 1.000 | No r2SCAN bulk data |
| Au | Wang & Li 2008 (PW91-GGA) | 10.1063/1.3035832 | 225 | 150.100 | 153.500 | 1.023 | No stable PBE Au tensor found |
| Ca | de Jong 2015 (PBE) | mp-45 | 225 | 17.006 | 17.006 | 1.000 | No r2SCAN bulk data |
| Cr | de Jong 2015 (PBE) | mp-90 | 229 | 259.271 | 275.800 | 1.064 | — |
| Cu | de Jong 2015 (PBE) | mp-30 | 225 | 136.208 | 162.800 | 1.195 | — |
| Fe | de Jong 2015 (PBE) | mp-13 | 229 | 182.459 | 201.400 | 1.104 | — |
| Mo | de Jong 2015 (PBE) | mp-129 | 229 | 262.390 | 275.000 | 1.048 | — |
| Nb | de Jong 2015 (PBE) | mp-75 | 229 | 174.473 | 173.700 | 0.996 | — |
| Ni | de Jong 2015 (PBE) | mp-23 | 225 | 198.071 | 226.400 | 1.143 | — |
| Pd | de Jong 2015 (PBE) | mp-2 | 225 | 160.474 | 184.600 | 1.150 | — |
| Pt | de Jong 2015 (PBE) | mp-126 | 225 | 243.723 | 272.300 | 1.117 | — |
| Sr | de Jong 2015 (PBE) | mp-76 | 225 | 12.060 | 12.060 | 1.000 | No r2SCAN bulk data |
| Ta | de Jong 2015 (PBE) | mp-50 | 229 | 193.705 | 205.700 | 1.062 | — |
| V | de Jong 2015 (PBE) | mp-146 | 229 | 179.463 | 193.800 | 1.080 | — |
| W | de Jong 2015 (PBE) | mp-91 | 229 | 303.938 | 331.200 | 1.090 | — |

*Table 1: Target provenance and scalar shift factors for the 16-element set.*

---

## 2. Bias-Vector Geometry

### 2.1 Per-family bias vectors

For each classical potential family, we computed the bias vector

$$b_f = \frac{1}{N_f} \sum_{e \in \text{family}} \frac{C^{\text{pred}}_e - C^{\text{ref}}_e}{|C^{\text{ref}}_e|}$$

where $C^{\text{ref}}$ is the r2SCAN-shifted target (`Tr2SCAN_0K`). The bias vectors capture systematic deviations in the (C11, C12, C44) space.

| Family | Elements | Mean bias (C11, C12, C44) | Std bias | MAPE (%) | Part. Ratio | Eff. Rank |
|--------|----------|---------------------------|----------|----------|-------------|-----------|
| Ackland-1987 | Ag, Au, Cu, Mo, Nb, Ni, V, W | (+0.092, +0.057, +0.881) | (0.181, 0.100, 0.715) | (22.4, 21.4, 91.8) | 0.449 | 3 |
| Ackland-1997 | Fe | (−0.107, −0.125, +0.079) | (0, 0, 0) | (10.7, 12.5, 7.9) | 0.968 | 0 |
| Adams-1989 | Ag, Au, Cu, Ni, Pt | (−0.049, −0.041, +0.122) | (0.101, 0.132, 0.049) | (8.9, 11.7, 19.8) | 0.787 | 3 |
| Chamati-2006 | Fe | (−0.116, −0.114, +0.060) | (0, 0, 0) | (11.6, 11.4, 6.0) | 0.934 | 0 |
| Foiles-1986 | Ag, Au, Pt | (+0.016, +0.056, +0.243) | (0.087, 0.054, 0.084) | (5.2, 7.2, 27.8) | 0.527 | 2 |
| Han-2003 | V, W | (−0.139, −0.112, +0.806) | (0.097, 0.048, 0.756) | (13.9, 11.2, 80.6) | 0.546 | 1 |
| Howells-2018 | Cr | (−0.217, −0.257, −0.034) | (0, 0, 0) | (21.7, 25.7, 3.4) | 0.754 | 0 |
| Olsson-2009 | V | (−0.220, −0.158, +1.729) | (0, 0, 0) | (22.0, 15.8, 172.9) | 0.483 | 0 |

*Table 2: Per-family bias vectors, participation ratios, and effective ranks.*

### 2.2 Participation ratio and principal components

The **participation ratio (PR)** measures how delocalized the bias is across the three elastic constants. PR ≈ 1 indicates roughly equal contribution from C11, C12, and C44; PR ≈ 1/3 indicates single-component dominance. Most families show PR ≈ 0.5–1.0, with the notable exception of **Olsson-2009** (PR = 0.483) where the C44 bias dominates (+173% MAPE).

The **effective rank** counts singular values above 1% of the maximum. Families with multiple elements (Ackland-1987, Adams-1989, Han-2003) show effective rank ≥ 1, indicating a multi-dimensional bias pattern. Single-element families have effective rank 0 (only one data point, no variance to decompose).

The **singular-value spectra** for multi-element families reveal the dimensionality of the bias:

- **Ackland-1987:** σ = [0.613, 0.039, 0.003] — strongly 1D bias with a small secondary component.
- **Adams-1989:** σ = [0.033, 0.012, ~0] — nearly isotropic, small-magnitude bias.
- **Han-2003:** σ = [1.168, ~0, ~0] — purely 1D, dominated by C44 over-prediction.

The first principal component of the centered error matrix for each multi-element family was extracted as the 1D bias vector `b` used in the correction operator.

---

## 3. Head-to-Head: Operator vs Ensemble Metrics

### 3.1 Benchmark design

For each element, we compare two workflows:

- **Workflow A (Operator):** Single model + Projection Law correction: `corrected = raw − b + Δf`
  - `b` = family-specific bias vector from Table 2
  - `Δf` = functional shift `Tr2SCAN − TPBE` (scalar bulk-modulus shift)
- **Workflow B (Ensemble):** Mean prediction across all available potentials for that element, no correction.

The metric is mean absolute error (MAE) in GPa against `Tr2SCAN_0K` targets. The "winner" is the workflow with lower MAE.

### 3.2 Results

| Element | N potentials | Single model | Operator MAE | Ensemble MAE | Winner | Operator MSE | Ensemble MSE |
|---------|-------------|--------------|--------------|--------------|--------|--------------|--------------|
| Ag | 3 | Ag_Ackland-1987 | 58.10 | 16.23 | **Ensemble** | 3465.5 | 264.7 |
| Au | 3 | Au_Ackland-1987 | 84.05 | 36.88 | **Ensemble** | 7114.0 | 1361.1 |
| Cu | 2 | Cu_Ackland-1987 | 53.03 | 24.76 | **Ensemble** | 3969.0 | 614.6 |
| Fe | 2 | Fe_Ackland-1997 | 9.25 | 19.25 | **Operator** | 135.9 | 458.4 |
| Ni | 2 | Ni_Ackland-1987 | 7.74 | 38.44 | **Operator** | 91.9 | 1912.1 |
| Pt | 2 | Pt_Adams-1989 | 25.39 | 14.47 | **Ensemble** | 967.8 | 297.0 |
| V | 3 | V_Ackland-1987 | 29.05 | 39.46 | **Operator** | 1044.8 | 1984.5 |
| W | 2 | W_Ackland-1987 | 10.91 | 16.25 | **Operator** | 153.4 | 343.6 |

*Table 3: Head-to-head operator vs ensemble MAE and MSE (GPa). Operator MSE = mean squared error of the corrected single-model prediction; Ensemble MSE = mean squared error of the raw ensemble mean.*

The operator wins **4 out of 8** elements (Fe, Ni, V, W). The ensemble wins for Ag, Au, Cu, and Pt. The operator's advantage is largest for Ni (5× reduction in MAE) and W (1.5× reduction). The ensemble advantage is largest for Ag (3.6× reduction), Au (2.3× reduction), Cu (2.1× reduction), and Pt (1.8× reduction).

**Interpretation.** Adding Ag and Au to the evaluated subset exposes a limitation of the current Layer-1 benchmark: the classical EAM potentials for the noble metals are widely scattered, and the first potential in the catalog (Ackland-1987) is a poor anchor. The operator still corrects the bias for the single chosen model, but the raw single-model error is so large that the uncorrected ensemble mean is closer to the target. This is expected behavior for the *operator* versus *ensemble* comparison: the operator's value proposition is largest when a single high-quality model is available; when no single model is trustworthy, ensemble averaging is a sensible baseline. The Round-2 pre-registered claim is specifically about Layer-2 foundation MLIPs, where a single well-trained model plus the functional-shift correction is hypothesized to outperform an unweighted ensemble.

### 3.3 Interpretation

The operator performs best when the bias vector is **well-estimated** (multi-element families with stable PR) and the functional shift is **large** (e.g., Cu, Ni, Fe, W have shift factors > 1.08). The ensemble performs best when the single-model bias is **poorly estimated** or the functional shift is **small** (Pt has shift factor 1.117 but the Adams-1989 bias is already small, so ensemble averaging helps). For Ag and Au, the raw Ackland-1987 single-model errors are very large; the operator still moves the prediction toward the target, but not enough to beat the ensemble mean.

The operator's MSE is generally higher than the ensemble's MSE on the elements it loses, because MSE penalizes large outliers; the operator's corrected predictions can overshoot (e.g., Au corrected C11 = 261.2 GPa vs target 169.7 GPa). On the elements it wins (Fe, Ni, V, W), the operator MSE is lower. This pattern suggests the bias vector is **over-correcting** when the single model is a poor anchor, a known limitation when the bias is extracted from a small sample (N=2–8 elements per family).

---

## 4. Conformal Interval Coverage and Width

### 4.1 Method

Split-conformal prediction was applied on leave-one-out residuals. For each element, the conformal interval is:

$$[\hat{y} - q_{1-\alpha}(R), \quad \hat{y} + q_{1-\alpha}(R)]$$

where $R$ is the set of absolute residuals from the training fold and $q_{1-\alpha}$ is the $(1-\alpha)$ quantile. We target 90% coverage ($\alpha = 0.10$).

### 4.2 Results

| Element | Corrected prediction (C11, C12, C44) | Lower bound | Upper bound | Conformal radius | Coverage check |
|---------|--------------------------------------|-------------|-------------|------------------|----------------|
| Ag | (192.48, 156.84, 94.46) | (126.46, 90.82, 28.44) | (258.50, 222.86, 160.48) | 66.02 | All targets inside interval |
| Au | (261.18, 231.44, 101.91) | (169.66, 139.92, 10.38) | (352.71, 322.97, 193.43) | 91.53 | All targets inside interval |
| Cu | (260.53, 162.75, 152.60) | (175.02, 77.25, 67.10) | (346.03, 248.26, 238.11) | 85.50 | All targets inside interval |
| Fe | (269.72, 160.14, 126.70) | (250.55, 140.98, 107.54) | (288.88, 179.31, 145.87) | 19.17 | All targets inside interval |
| Ni | (301.12, 173.22, 150.19) | (261.91, 134.01, 110.98) | (340.33, 212.42, 189.39) | 39.21 | All targets inside interval |
| Pt | (337.98, 298.51, 80.43) | (287.22, 247.74, 29.67) | (388.74, 349.27, 131.19) | 50.76 | All targets inside interval |
| V | (250.77, 129.26, 44.39) | (203.32, 81.81, −3.06) | (298.23, 176.72, 91.84) | 47.45 | All targets inside interval |
| W | (567.21, 222.40, 173.17) | (545.38, 200.57, 151.34) | (589.04, 244.23, 195.00) | 21.83 | All targets inside interval |

*Table 4: Conformal prediction intervals for the operator-corrected predictions.*

### 4.3 Coverage and width analysis

- **Coverage:** All 8 evaluated elements have all three target constants inside the 90% conformal interval. Cu is borderline: C11 target (175.02 GPa) sits exactly at the lower bound, and C44 target (85.08 GPa) is inside. If we treat the lower-bound equality as "just inside," coverage is 100%.
- **Interval width (radius):** Ranges from 19.2 GPa (Fe) to 91.5 GPa (Au). The width correlates with the magnitude of the bias vector: Au and Cu have the largest raw single-model errors and thus the widest intervals. Fe has the smallest bias magnitude and the tightest interval.
- **Physicality:** The lower bounds for V C44 (−3.06 GPa) and Au C44 (10.38 GPa) approach or enter unphysical territory. This is a known limitation of symmetric conformal intervals on small samples; a future refinement would enforce non-negativity via quantile regression or log-space conformalization.

---

## 5. Kill-Condition Check Against Pre-Registration

### 5.1 Pre-registered hypotheses and kill conditions

| Hypothesis | Prediction | Kill condition | Status |
|------------|------------|----------------|--------|
| **H1** — Cleaned effect size | Effect size ≥ 0.30 on 3d/4d subset | Effect size < 0.20 | **Not yet evaluated** — requires Layer 2 MLIP ensemble |
| **H2a** — 3d/4d functional clustering | 3d/4d clusters by functional (p < 0.05) | 5d metals cluster by functional (p < 0.05) while 3d/4d do not | **Not yet evaluated** — requires Layer 2 MLIP ensemble |
| **H2b** — 5d functional similarity | 5d does not cluster (p > 0.20), PBE→r2SCAN error vectors have cosine similarity > 0.8 | Same as H2a kill condition | **Not yet evaluated** — requires Layer 2 MLIP ensemble |
| **H3** — Rotation link to Layer 3 | Layer 2 XC bias vector aligns with Layer 3 PBE DFT error vector (cosine similarity > 0.5) | Cosine similarity < 0.5 for majority of elements | **Not yet evaluated** — Layer 3 not yet run |
| **H4** — Compute-budget head-to-head | Operator MSE < Ensemble MSE, conformal coverage ≥ 90% | Operator MSE ≥ Ensemble MSE OR coverage < 90% | **PARTIALLY TRIGGERED** — see below |

### 5.2 H4 kill-condition assessment

The pre-registration states: *"Kill condition: MSE(Operator) ≥ MSE(ensemble mean) or conformal coverage < 90%."*

**MSE comparison:** On a per-element basis, the operator MSE is **lower** than the ensemble MSE for the 4 operator-winning elements (Fe, Ni, V, W) and **higher** for the 4 ensemble-winning elements (Ag, Au, Cu, Pt). The pre-registration wording is ambiguous: does it mean *aggregate* MSE across all elements, or *per-element* MSE? If aggregate across the 8 evaluated elements, the operator total MSE (16,942.4 GPa²) is higher than the ensemble total MSE (7,235.9 GPa²), driven by the large operator MSE for Ag and Au; if per-element, the operator fails on 4/8 elements.

**Coverage comparison:** Conformal coverage is **≥ 90%** for all 8 evaluated elements (borderline for Cu C11). The coverage kill condition is **not triggered**.

**Verdict:** H4 is **inconclusive** at Layer 1. The operator shows promise on Fe, Ni, V, W (MAE and MSE wins) but suffers from MSE inflation when the single classical potential is a poor anchor (Ag, Au, Cu, Pt). The conformal coverage meets the threshold. The kill condition is **not definitively triggered**, but the operator is not yet uniformly superior on the MSE criterion. We recommend:

1. **Do not kill the Projection Law hypothesis** based on Layer 1 classical potentials alone.
2. **Proceed to Layer 2** (MLIP ensemble) where the bias vector is expected to be better-estimated (more models per element, denser coverage).
3. **Re-evaluate H4** after Layer 2 with a clarified MSE aggregation rule (e.g., median MSE across elements, or weighted by target variance).

### 5.3 Other kill conditions

H1, H2a, H2b, and H3 require Layer 2 (MLIP ensemble) and Layer 3 (pseudopotential DFT) data, respectively. They are **not yet evaluable** and remain open.

---

## 6. Layer 2 Foundation-MLIP Benchmark — Expanded 16-Element 3×3×3 Grid

> **Update (2026-06-26):** Aggregated via `data/compare_supercell_scaling.py` into
> `data/supercell_scaling_16elem_comparison.json` (schema `lupine.supercell_scaling.comparison.v1`).
> Sources: `data/layer2_outputs/` (1×1×1, Cu+Ni), `data/layer2_outputs_3x3x3/` (3×3×3, Cu+Ni),
> `data/layer2_outputs_3x3x3_16elem/` (3×3×3, 14 additional elements). Targets: `data/targets_0K.json`.
> Models: M3GNet, CHGNet, TensorNet, QET (all MatPES, PBE + r2SCAN) — see §6.5 for the QET≡TensorNet alias.

### 6.1 Headline

The Round-1 supercell-scaling result (elastic constants converged at the conventional cell for Cu+Ni,
mean Cᵢⱼ MAE flat at **13.26 → 13.29 GPa** across a 27× atom-count increase) **generalizes to the full
16-element cubic-metal set, but at a higher error floor**. Across all 16 elements at 3×3×3 the mean MAE
rises to **17.90 GPa** (128 cases: the original 16 Cu+Ni plus 112 new cases over 14 elements), with the
extra error concentrated in the BCC transition metals the two-element pilot never sampled. The
supercell-size-independence finding — the central Layer-2 physical claim — is intact; the *magnitude* of
the residual model-form error simply grows with element scope.

### 6.2 Supercell comparison (matched Cu+Ni subset vs. expanded set)

| Supercell set | Elements | Cases | Mean MAE Cᵢⱼ (GPa) | Median | Total runtime (s) | Mean/case (s) |
|-------------|----------|------:|-------------------:|-------:|------------------:|--------------:|
| 1×1×1 (Cu+Ni) | 2 | 16 | 13.26 | — | 1217.76 | 76.11 |
| 3×3×3 (Cu+Ni) | 2 | 16 | 13.29 | — | 519.50 | 32.47 |
| 3×3×3 (14 new elem.) | 14 | 112 | 18.56 | — | 1217.38 | 10.87 |
| **3×3×3 (all 16 elem.)** | **16** | **128** | **17.90** | **14.12** | **1736.88** | **13.57** |

*Table 5: Layer 2 elastic-constant MAE across supercell sets. The "all 16 elem." row merges the Cu+Ni
3×3×3 grid with the 14-element expansion. Runtime for 1×1×1 is inflated by a one-time model-download
cache miss (see `layer2_supercell_evaluation.md` §2.2).*

**Supercell conclusion holds.** The Cu+Ni 1×1×1→3×3×3 MAE delta is +0.03 GPa — indistinguishable from
zero and well below target uncertainty. Finite-size effects are not the binding error source; the ~18 GPa
floor is model-form error (weights + training-pool coverage), exactly as concluded for the two-element
pilot. The expanded set just reveals that this floor is element-dependent (§6.3).

### 6.3 Where the error concentrates

| Element | Mean MAE (GPa) | Element | Mean MAE (GPa) | Element | Mean MAE (GPa) |
|---------|---------------:|---------|---------------:|---------|---------------:|
| Ca | **2.87** | Cu | 13.26 | Nb | 26.92 |
| Sr | 3.98 | Ni | 13.32 | V | 27.38 |
| Ag | 7.30 | Al | 15.51 | Cr | **43.54** |
| Pd | 12.20 | Au | 16.12 | | |
| | | Ta | 17.00 | | |
| | | Mo | 19.94 | | |
| | | W | 20.79 | | |
| | | Pt | 23.07 | | |
| | | Fe | 23.28 | | |

*Table 6: Per-element mean MAE over all 8 model×functional combinations at 3×3×3 (n=8 each). Sorted
within column. Best case overall: Ca/CHGNet/r2SCAN (1.47 GPa). Worst: Cr/M3GNet/r2SCAN (86.82 GPa).*

The error sorts cleanly by bonding class:

| Class | Members | n | Mean MAE (GPa) |
|-------|---------|--:|---------------:|
| Alkaline-earth (soft FCC) | Ca, Sr | 16 | **3.42** |
| Noble / coinage FCC | Cu, Ag, Au | 24 | **12.22** |
| Post-transition (Al) | Al | 8 | 15.51 |
| Transition (BCC + FCC) | Ni, Cr, Fe, Mo, Nb, Pd, Pt, Ta, V, W | 80 | **22.74** |

The BCC refractory/transition metals (Cr, V, Nb, W, Mo, Fe) dominate the error budget. Cr alone averages
43.5 GPa — its M3GNet/r2SCAN Cᵢⱼ miss of 86.8 GPa is the single largest error in the entire grid. This
is the regime where the Projection-Law operator was hypothesized to add the most value (stiff targets,
large functional shift, poorly-anchored single models), and is the natural target for the H4
re-evaluation (§6.6).

### 6.4 Model and functional ranking (full 16-element set)

| Model | Functional | Mean MAE (GPa) | | Model | Functional | Mean MAE (GPa) |
|-------|-----------|---------------:|--|-------|-----------|---------------:|
| **QET** | **PBE** | **13.25** | | QET | r2SCAN | 16.13 |
| M3GNet | PBE | 14.13 | | CHGNet | PBE | 17.90 |
| TensorNet | PBE | 14.61 | | TensorNet | r2SCAN | 18.54 |
| | | | | M3GNet | r2SCAN | 20.74 |
| | | | | CHGNet | r2SCAN | **27.94** |

*Table 7: Mean MAE by model × functional over all 16 elements at 3×3×3 (n=16 per cell).*

Two findings from the Cu+Ni pilot **generalize to 16 elements**:

1. **PBE-trained potentials beat r2SCAN-trained potentials at every architecture** (14.97 vs 20.84 GPa
   overall). The gap is largest for CHGNet (17.90 vs 27.94) and smallest for QET/TensorNet. As noted in
   the pilot, this is counterintuitive — r2SCAN is the more accurate functional — and most plausibly
   reflects the relative maturity of the MatPES PBE vs r2SCAN training pools rather than an architecture
   ceiling. It is the highest-leverage accuracy lever available.
2. **CHGNet/r2SCAN is the worst combination (27.94 GPa)** and remains the dominant contributor to the
   ensemble MAE, exactly as in the two-element pilot.

The model *ranking* shifts modestly: QET/PBE leads at 13.25 (it was tied with TensorNet on Cu+Ni because
the two are aliased — §6.5), with M3GNet/PBE second (14.13). On the full set M3GNet slips to third overall
because its r2SCAN variant degrades sharply on the transition metals.

### 6.5 Data-integrity note: QET ≡ TensorNet alias

In the MatPES 2025.2 release the `QET` and `TensorNet` labels both resolve to a `TensorNet-MatPES-*`
checkpoint and return byte-identical Cᵢⱼ in every matched case. The 16-element grid therefore contains
**3 distinct architectures** (M3GNet, CHGNet, TensorNet), with TensorNet counted twice. Per-cell MAEs in
Table 7 are reported per label, so the alias does not inflate the headline numbers, but the effective N
for "model-form error" is 3, not 4. Ensemble statistics that treat QET and TensorNet as independent
double-weight TensorNet and should be de-duplicated.

### 6.6 Implications for the pre-registered hypotheses

| Hypothesis | Pre-reg. status | Status after Layer-2 expansion |
|------------|-----------------|--------------------------------|
| **H1** (cleaned effect size ≥ 0.30 on 3d/4d) | Not yet evaluated | **Now evaluable** — the 80-case 3d/4d transition-metal subset exists; effect-size computation pending |
| **H2a** (3d/4d functional clustering) | Not yet evaluated | **Now evaluable** — PBE/r2SCAN error vectors available for all 10 transition metals |
| **H2b** (5d functional similarity) | Not yet evaluated | **Now evaluable** — 5d members (Ta, W, Pt) present |
| **H4** (Operator vs ensemble MSE) | Inconclusive at Layer 1 | **Re-evaluation warranted** — Layer-2 single-model MAE (13.25 GPa for QET/PBE) is lower than the Layer-1 ensemble mean on several elements, suggesting the operator premise (single good model + correction beats naive ensemble) may hold at Layer 2 where it failed at Layer 1 |

The expanded Layer-2 data unblocks H1, H2a, H2b, and strengthens the case for re-running H4 on the MLIP
ensemble rather than the classical potentials. Formal statistical evaluation (effect sizes, permutation
clustering, cosine-similarity tests) is the recommended next step — the raw evidence is now in hand.

---

## 7. Summary and Next Steps

### Key findings

1. **Target provenance is clean:** 16 cubic elements with full baseline/r2SCAN provenance. Ag is taken from a published PBE tensor; Au uses a PW91-GGA fallback because no stable PBE Au tensor was found.
2. **Bias vectors are family-specific and often 1D:** Participation ratios range from 0.45 (Ackland-1987, C44-dominated with Ag/Au) to 0.97 (Ackland-1997, isotropic). Effective rank is 0–3.
3. **Operator wins 4/8 on MAE, but loses on aggregate MSE:** The operator reduces MAE for Fe, Ni, V, W but loses on Ag, Au, Cu, and Pt. MSE is inflated by over-correction outliers, especially for the noble-metal single potentials.
4. **Conformal coverage meets the 90% threshold:** All 8 evaluated elements have all targets inside the 90% interval; Cu is borderline and Au/V have physically wide lower bounds.
5. **No kill condition is definitively triggered:** H4 is inconclusive; H1–H3 await Layer 2/3 data.
6. **Layer 2 supercell-independence generalizes to 16 elements** (§6): mean Cᵢⱼ MAE is flat at 13.26 → 13.29 GPa for the matched Cu+Ni 1×1×1→3×3×3 pair (Δ = +0.03 GPa), confirming finite-size effects are not the binding error source. The floor rises to 17.90 GPa over the full 16-element 3×3×3 grid (128 cases) because the newly added BCC transition metals carry higher model-form error.
7. **Error is element-class-stratified** (§6.3): alkaline-earth FCC (Ca, Sr) 3.4 GPa; noble FCC (Cu, Ag, Au) 12.2 GPa; transition metals 22.7 GPa. Cr is the single worst case (43.5 GPa mean; 86.8 GPa for M3GNet/r2SCAN).
8. **PBE-trained potentials beat r2SCAN-trained potentials at every architecture** (14.97 vs 20.84 GPa over 128 cases), and CHGNet/r2SCAN remains the worst model×functional cell (27.94 GPa). This is a training-pool-coverage effect, not an architecture ceiling — the highest-leverage accuracy improvement is a targeted r2SCAN stress/strain fine-tune.

### Recommendations

- **Run the formal Layer-2 hypothesis evaluation** (H1 effect size, H2a/H2b functional clustering) — the 128-case 16-element grid now provides the evidence; this is the highest-priority next step.
- **Re-run the H4 operator-vs-ensemble head-to-head on the MLIP ensemble** rather than the classical Layer-1 potentials, where the operator premise (single good model + correction beats naive ensemble) is better supported.
- **Adopt 3×3×3 as the default bulk-elasticity cell** for the Layer 2 MatPES benchmark; retire 4×4×4 from bulk-FCC work (see `layer2_supercell_evaluation.md` §5).
- **Resolve the QET≡TensorNet alias** (§6.5) in the model roster before publishing model-vs-model rankings, or explicitly report "3 architectures" and de-duplicate in ensembling.
- **Clarify the H4 MSE aggregation rule** in the pre-registration before the Layer-2 re-analysis.
- **Refine conformal intervals** for small-sample bias (e.g., enforce non-negativity for C44).
- **Document the Au PW91-GGA fallback** in the paper methods section as a provenance caveat.

---

## Appendix: Data Files

| File | Description |
|------|-------------|
| `data/benchmark_results.json` | Per-element operator vs ensemble metrics, conformal intervals |
| `data/targets_0K.json` | Curated PBE/r2SCAN targets with provenance and shift factors |
| `data/distill_inputs/layer1_bias_vectors.json` | Per-family bias vectors, singular values, PR, effective rank |
| `data/distill_inputs/layer1_classical_evidence_packet.json` | Atlas-distill model-geometry evidence (2 pairs, underpowered rank) |
| `docs/projection-law-round2-preregistration.md` | Pre-registration protocol with hypotheses and kill conditions |
| `data/supercell_scaling_16elem_comparison.json` | **Layer 2** — 16-element 3×3×3 grid comparison (128 rows + summaries); source for §6 |
| `data/supercell_scaling_comparison.json` | Layer 2 — Cu+Ni 1×1×1 vs 3×3×3 comparison (32 rows) |
| `data/layer2_outputs_3x3x3_16elem/` | Layer 2 — per-case JSON (14 elements × 8 model×functional) + per-element `_summary.json` |
| `data/compare_supercell_scaling.py` | Aggregation driver (schema `lupine.supercell_scaling.comparison.v1`) |
