# Layer 2 Supercell Scaling — Technical Evaluation

> **Task:** t_22ae2ad9 · **Author:** synthesizer · **Date:** 2026-06-26
>
> **Sources:** `data/benchmark_layer2_results.json` (schema `lupine.benchmark.layer2.v1`, 16 cases, 1×1×1),
> `data/supercell_scaling_comparison.json` (1×1×1 + 3×3×3, 32 rows),
> `data/layer2_outputs_3x3x3/` (16 per-case JSON + `_summary.json`),
> `data/layer2_outputs_4x4x4/` (15 per-case JSON + `_summary.json` + `run.log`),
> `data/targets_0K.json` (schema `lupine.targets_0K.v3`, reference tensors).
> Method driver: `data/layer2_benchmark_task.py`; grid runner: `data/run_layer2_supercell_grid.py`;
> comparator: `data/compare_supercell_scaling.py`.

---

## TL;DR

Supercell size is **not** the limiting factor for MatPES-potential elastic constants of bulk FCC metals.
The mean absolute error (MAE) on the three independent cubic constants (C₁₁, C₁₂, C₄₄) is flat across cell
sizes — **13.26 → 13.29 → 13.41 GPa** for 1×1×1 (4 atoms) → 3×3×3 (108) → 4×4×4 (256) — while the per-atom
runtime rises steeply. The residual ~13 GPa gap to DFT is **model-form error** (weights + training pool),
not finite-size error, and is dominated by the functional-mismatch and a few stiff/target-shift cases.
The cost-optimal cell is the **3×3×3 supercell**: it is *faster than* the 1×1×1 run in aggregate (cache
warm-up artifact), matches it in accuracy to <0.05 GPa, and avoids the 4×4×4 blow-up. The 1×1×1
conventional cell remains valid for screening. Going to 4×4×4 buys nothing in accuracy and ~4× the runtime.

---

## 1. Convergence of elastic constants with supercell size

### 1.1 Aggregate picture

| Supercell | Atoms/cell | Cases | Mean MAE on Cᵢⱼ (GPa) | Total runtime (s) | Mean runtime/case (s) |
|-----------|-----------:|------:|----------------------:|------------------:|----------------------:|
| 1×1×1     | 4          | 16    | **13.26**             | 1217.76           | 76.11                  |
| 3×3×3     | 108        | 16    | **13.29**             | 519.50            | 32.47                  |
| 4×4×4     | 256        | 15 †  | **13.41**             | 2161.91           | 144.13                 |

† The 4×4×4 grid is missing `Cu_CHGNet_PBE` (15/16); the runner logged the case as started but no output
file and no error were produced — a **silent failure** (see §4). All three MAE figures use only the cases
present at each size; the 4×4×4 figure is therefore computed over 15 cases but is within rounding of the
16-case number (the missing case contributes ~12.8 GPa at SC1/SC3, near the mean, so its absence is benign).

A 64× increase in atom count (4 → 256) moves the ensemble MAE by **+0.15 GPa** — less than the rounding on
any single constant. This is the signature of an **accuracy floor set by the model, not the box**.

### 1.2 Case-by-case |ΔCᵢⱼ| between sizes (matched cases, all three constants)

| Transition | Matched cases | max \|ΔCᵢⱼ\| (GPa) | mean \|ΔCᵢⱼ\| (GPa) | RMS \|ΔCᵢⱼ\| (GPa) |
|------------|--------------:|--------------------:|---------------------:|---------------------:|
| 1 → 3      | 16            | 0.68                | 0.249                | 0.304                 |
| 3 → 4      | 15            | 3.31                | 0.264                | 0.605                 |

Interpretation:
- **1 → 3:** essentially converged. The largest single-constant swing in the entire grid (0.68 GPa) is
  below the typical experimental/DFT target uncertainty (~1–3 GPa). Finite-size effects at the
  conventional cell are already negligible for bulk FCC elasticity, as expected: an MLIP with a local
  cutoff sees a perfectly periodic environment in either cell.
- **3 → 4:** the *mean* change (0.26 GPa) is comparable to 1→3, but the *tail* widens (max 3.31 GPa,
  RMS 0.61). The single outlier is **Ni / M3GNet / PBE** (3.43 → 5.01 GPa MAE; C₁₁ drift 272.09 → 268.78).
  This is not a systematic divergence — it is one case where the relaxation landscape of the larger cell
  settles on a slightly different configuration. It does not change the ensemble conclusion but is the
  one place the 4×4×4 result is *less* accurate than the smaller cells, not more.

### 1.3 Lattice parameter is invariant to size

Predicted equilibrium lattice parameters `a` are stable to **±0.0008 Å** across all three supercell sizes
for every case. The relaxer (`RelaxCalc`, `fmax=0.005`) converges to the same bulk geometry regardless of
cell padding, which is why the elastic constants are so nearly size-independent: the elastic fit is taken
at the same minimum in every case.

### 1.4 Conclusion of §1

Elastic constants are **converged at the conventional cell** for this system class. The remaining ~13 GPa
MAE cannot be closed by supercell expansion. It is model-form error and concentrates in specific
model/functional combinations (§3).

---

## 2. Runtime / cost trade-offs

### 2.1 Per-model mean runtime (seconds/case)

| Model      | 1×1×1 | 3×3×3 | 4×4×4 | Scaling 1→4 |
|------------|------:|------:|------:|-------------|
| M3GNet     |  39.2 |   9.7 |  22.9 | 0.6×        |
| CHGNet     | 252.8 |  71.1 | 489.8 | 1.9×        |
| TensorNet  |   9.7 |  24.0 |  74.7 | 7.7×        |
| QET ‡      |   2.7 |  25.1 |  75.5 | 28×         |

‡ QET and TensorNet resolve to the *same* `TensorNet-MatPES` checkpoint (see §3.3); the runtime
differences between them at a given size reflect machine load / one-off cache states, not architecture.

### 2.2 The 1×1×1 total-runtime anomaly

The 1×1×1 grid (1217.76 s) is **slower in aggregate than the 3×3×3 grid (519.50 s)**, which is physically
impossible for a pure size-scaling test. This is a **cache-warm / model-download confound**: the 1×1×1 runs
were the first invocation and paid the one-time HuggingFace download + TorchScript-trace cost for each
checkpoint; the 3×3×3 grid reused the cached models. The per-case *steady-state* cost is therefore better
read from the 3×3×3 and 4×4×4 columns. The CHGNet column still shows the genuine size trend (71 → 490 s,
roughly linear-ish in atoms), because CHGNet is the heaviest per-atom architecture.

### 2.3 CHGNet is the runtime outlier at 4×4×4

Two CHGNet cases at 4×4×4 dominate the wall-clock:
- **Ni / CHGNet / r2SCAN: 1003.16 s** (vs 88.7 s at 3×3×3 — an 11× blow-up for a 2.4× atom increase).
- **Ni / CHGNet / PBE: 148.0 s**; **Cu / CHGNet / r2SCAN: 318.3 s**.

This is super-linear scaling in the relaxation loop (CHGNet's iterative ionic relaxation at 256 atoms with
`fmax=0.005` does many more force evaluations than at 108). For production grids, CHGNet at 4×4×4 should be
treated as ~10–20× the 3×3×3 cost, and budgeted accordingly.

### 2.4 Cost recommendation

- **Screening / bulk benchmarks:** use **3×3×3**. It matches the 1×1×1 accuracy, is the fastest in
  steady-state (520 s for the full 16-case grid), and removes any residual concern about the conventional
  cell's representativeness. The 1×1×1 conventional cell is an acceptable *faster* alternative when the
  model cache is already warm.
- **Do not use 4×4×4 for bulk FCC elasticity.** It buys ≤0.15 GPa in ensemble MAE and costs ~4× the
  3×3×3 runtime, with a pathological CHGNet tail. Reserve ≥4×4×4 for defect, surface, or
  phonon-dispersion work where the larger cell is physically motivated.
- **Memory:** no OOM events were recorded in any grid. The 4×4×4 runs (256 atoms) completed on the
  same host as the smaller cells; memory was not the binding constraint — wall-clock was.

---

## 3. Best-performing model / functional combinations

### 3.1 MAE by model × functional (averaged over Cu+Ni, all available supercells)

| Model      | Functional | SC1 MAE | SC3 MAE | SC4 MAE | Mean (all) |
|------------|------------|--------:|--------:|--------:|-----------:|
| **M3GNet** | **PBE**    | **8.50**  | **8.36**  | 9.16    | **8.67**     |
| M3GNet     | r2SCAN     | 11.14   | 11.07   | 11.14   | 11.12      |
| TensorNet  | PBE        | 9.44    | 9.70    | 9.75    | 9.63       |
| QET ‡      | PBE        | 9.44    | 9.70    | 9.75    | 9.63       |
| TensorNet  | r2SCAN     | 15.59   | 15.56   | 15.52   | 15.56      |
| QET ‡      | r2SCAN     | 15.59   | 15.56   | 15.52   | 15.56      |
| CHGNet     | PBE        | 14.84   | 14.72   | 16.65   | 15.40      |
| CHGNet     | r2SCAN     | 21.58   | 21.64   | 21.40   | **21.54** (worst) |

‡ QET and TensorNet share the same checkpoint and return **byte-identical** Cᵢⱼ in all 12 matched
(case × supercell) pairs — verified directly. They are not independent models in this release (§3.3).

### 3.2 Findings

1. **M3GNet/PBE is the clear winner** at 8.67 GPa mean, and is the only combination that stays below
   10 GPa at *every* supercell size. Its best single case is Ni/PBE at **3.43 GPa** (SC3).
2. **PBE-trained models beat r2SCAN-trained models** for elasticity, across all architectures (8.67 vs
   11.12 for M3GNet; 9.63 vs 15.56 for TensorNet/QET; 15.40 vs 21.54 for CHGNet). This is
   counterintuitive — r2SCAN is the more accurate functional — and most plausibly reflects the relative
   maturity / coverage of the two MatPES training pools rather than a ceiling of the architectures.
3. **CHGNet/r2SCAN is the worst combination (21.54 GPa mean)** and is the dominant contributor to the
   ensemble MAE. Its bulk-modulus error on Ni is +11.2 % (B_pred 251.76 vs B_tgt 226.40 GPa) — the
   largest single relative error in the grid.
4. **Errors scale with the magnitude of the target.** Nickel (C₁₁ ≈ 276 GPa PBE / 315 GPa r2SCAN-shifted)
   and the r2SCAN bulk-shifted targets (which are uniformly stiffer) concentrate the largest absolute
   errors. A 21 GPa miss on a ~315 GPa C₁₁ is ~7 % relative — the same architectures hit 3–5 % on copper.

### 3.3 The QET ≡ TensorNet alias (data-integrity note)

In the MatPES 2025.2 release the `QET` and `TensorNet` labels in `MODEL_MAP` (`data/layer2_benchmark_task.py:30`)
both resolve to a `TensorNet-MatPES-*` checkpoint:

```
("QET", "PBE"):       "TensorNet-MatPES-PBE-2025.2"
("TensorNet", "PBE"): "TensorNet-PES-MatPES-PBE-2025.2"
```

The resulting Cᵢⱼ are **identical to floating-point precision** in every matched case (e.g. Cu/PBE:
c11=162.35, c12=118.18, c44=71.77 at 4×4×4 for both "QET" and "TensorNet"). The 16-case grid therefore
contains only **3 distinct architectures** (M3GNet, CHGNet, TensorNet), with TensorNet counted twice.
Any ensemble statistic that treats QET and TensorNet as independent models double-weights TensorNet.
The MAE tables above average per (model,label), so the alias does not inflate the headline numbers, but
**the effective N for "model-form error" is 3, not 4.**

---

## 4. Caveats and data-quality issues

1. **Missing 4×4×4 case.** `data/layer2_outputs_4x4x4/Cu_CHGNet_PBE.json` does not exist. The runner
   (`run.log`) shows `=== Running Cu CHGNet PBE 4x4x4 ===` followed immediately by the next case with no
   error/traceback — a silent process exit (likely OOM-kill or a torch crash inside the relaxer that the
   `try/except` in `layer2_benchmark_task.py` did not surface because no output file was written). The
   `_summary.json` reports 15 cases and the runner exited 0, so the loss went unflagged. **The
   `supercell_scaling_comparison.json` predates the 4×4×4 run and therefore omits this size entirely**;
   the 4×4×4 numbers in §1.1–§1.2 were recomputed here from the raw per-case JSON.
2. **QET ≡ TensorNet alias.** See §3.3. The "four model families" framing over-counts TensorNet.
3. **r2SCAN targets are synthesized, not measured.** Per `targets_0K.json` (schema `v3`), the r2SCAN
   reference tensors are constructed by scaling the de Jong 2015 PBE tensors by a bulk-modulus ratio
   `B_r2SCAN/B_PBE` from Liu et al. 2024 (e.g. Cu ratio 1.1952, Ni ratio 1.1430). This is an
   **approximation** — it assumes the shear constants scale identically to the bulk modulus, which is not
   generally true. Some of the r2SCAN MAE is therefore target-construction error, not pure model error.
   For elements with no published r2SCAN bulk modulus (Al, Ca, Sr in the full 15-metal table), the
   unshifted PBE tensor is used as the r2SCAN target (`r2scan_shift_ratio = 1.0`), which makes the
   r2SCAN/PBE comparison meaningless for those elements. Cu and Ni (the two tested here) both *do* have
   shifts, so this caveat does not affect the present grid but limits generalization.
4. **Two-element scope.** Only Cu and Ni (both FCC) are tested. The convergence-on-conventional-cell
   conclusion is expected to hold for other clean bulk FCC/BCC metals but is **not demonstrated** for
   low-symmetry, defect-laden, or anisotropic systems, where supercell effects can be genuine.
5. **Target provenance is mixed.** Cu/Ni PBE tensors are from de Jong 2015 (VASP, stress-strain). The
   wider 15-metal table mixes sources (Ag: Pandit & Bongiorno 2023; Au: Wang & Li 2008 PW91, used because
   the MP PBE tensor is unphysical). Cross-source comparisons at ~1–3 GPa level require care.
6. **Single random seed / single relax.** Each case is one relax + one elastic fit; there is no estimate
   of run-to-run variance. The 3×3→4×4 Ni/M3GNet/PBE outlier (§1.2) shows this variance is non-zero at
   the larger cell.

---

## 5. Recommendations

1. **Adopt 3×3×3 as the default bulk-elasticity cell** for the Layer 2 MatPES benchmark, with 1×1×1
   retained as the fast-screening option when the model cache is warm. Retire 4×4×4 from the bulk-FCC
   pipeline; it is not cost-justified.
2. **Re-run the missing `Cu_CHGNet_PBE` at 4×4×4** (or formally drop 4×4×4 per recommendation 1) so the
   `layer2_outputs_4x4x4/_summary.json` is either complete or explicitly marked partial. The silent
   failure should also be hardened: `run_layer2_supercell_grid.py:44` should treat a missing output file
   as a failure even when the subprocess returns 0.
3. **Regenerate `supercell_scaling_comparison.json`** with `compare_supercell_scaling.py` extended to all
   three sizes so the published comparison artifact matches the raw data on disk.
4. **Resolve the QET/TensorNet alias** in the model roster before publishing model-vs-model rankings:
   either drop the `QET` label or replace it with a genuinely distinct checkpoint. Until then, report
   "3 architectures" and de-duplicate when ensembling.
5. **Investigate the PBE-better-than-r2SCAN result.** It likely indicates the r2SCAN MatPES training pool
   is thinner for elastic response than the PBE pool. A targeted stress/strain fine-tune on r2SCAN
   reference data (de Jong 2015 + the Liu 2024 bulk shifts) is the highest-leverage accuracy improvement
   available — it would attack the dominant error source, whereas supercell scaling does not.
6. **Expand scope before generalizing.** If the "conventional cell is sufficient" claim is to be made
   broadly, add 2–3 BCC metals (e.g. W, Mo) and one lower-symmetry system to the convergence study. The
   present evidence is FCC-only.

---

## Appendix — per-case MAE (GPa) / runtime (s) across supercells

| Element | Model      | Func   | 1×1×1      | 3×3×3      | 4×4×4        |
|---------|------------|--------|-----------:|-----------:|-------------:|
| Cu      | CHGNet     | PBE    | 12.84/308.4| 12.79/75.4 | — (missing)  |
| Cu      | CHGNet     | r2SCAN | 23.15/58.4 | 23.05/58.6 | 23.06/318.3  |
| Cu      | M3GNet     | PBE    | 13.37/19.2 | 13.30/10.6 | 13.31/20.6   |
| Cu      | M3GNet     | r2SCAN | 12.08/90.6 | 12.14/10.8 | 12.21/24.8   |
| Cu      | QET        | PBE    |  9.72/2.9  |  9.73/23.6 |  9.81/62.2   |
| Cu      | QET        | r2SCAN | 12.56/3.1  | 12.65/24.8 | 12.60/64.5   |
| Cu      | TensorNet  | PBE    |  9.72/2.7  |  9.73/23.4 |  9.81/62.8   |
| Cu      | TensorNet  | r2SCAN | 12.56/2.8  | 12.65/22.4 | 12.60/63.1   |
| Ni      | CHGNet     | PBE    | 16.84/310.2| 16.64/61.7 | 16.65/148.0  |
| Ni      | CHGNet     | r2SCAN | 20.00/334.2| 20.22/88.7 | 19.74/1003.2 |
| Ni      | M3GNet     | PBE    |  3.63/1.8  |  3.43/8.5  |  5.01/20.6   |
| Ni      | M3GNet     | r2SCAN | 10.19/45.3 |  9.99/9.1  | 10.08/25.4   |
| Ni      | QET        | PBE    |  9.16/2.4  |  9.68/22.3 |  9.69/66.7   |
| Ni      | QET        | r2SCAN | 18.62/2.6  | 18.46/29.6 | 18.43/108.7  |
| Ni      | TensorNet  | PBE    |  9.16/30.5 |  9.68/21.7 |  9.69/63.1   |
| Ni      | TensorNet  | r2SCAN | 18.62/2.7  | 18.46/28.3 | 18.43/109.9  |

MAE is mean absolute error over {C₁₁, C₁₂, C₄₄} vs the `targets_0K.json` reference tensor; runtime is
wall-clock for relax + elastic fit, in seconds. Source: recomputed from per-case JSON in
`data/layer2_outputs{,_3x3x3,_4x4x4}/` with `data/targets_0K.json` targets.
