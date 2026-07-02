# Statistical hardening of the headline statistics (§3.3–3.4)

**Target:** `paper/environment-error-field-2026-07-02.md`, §3.3 (family-exponent
law, LOO correction comparisons) and §3.4 (blind γ₁₁₀ environment-field
prediction).
**Data:** `data/y_matrix_runs/bound/*.evidence.json` (84 cells,
`lupine.mlip.calc_evidence.v1`; error = model value − reference value) and
model-relaxed a₀ from `data/y_matrix_runs/*_fcc_*.json`
(`lupine.statics_run.v1`, `results.lattice.values.a0_angstrom`).
**Code:** `python/scripts/harden_stats.py` (stdlib + numpy 2.3.5, Python 3.14;
isotonic regression is a hand-rolled weighted PAVA — scipy deliberately not
used). All resampling seeded (base seed 20260702); 10,000 bootstrap draws and
10,000 permutations per test.
**Machine-readable results:**
`data/y_matrix_runs/analysis/statistical_hardening.json`.

**Bottom line.** The blind γ₁₁₀ prediction survives every honest test,
including a permutation null that is *not* centered at zero (null mean r =
0.44) and material-clustered CIs. Two of the three §3.3 claims must be
weakened: family-exponent *separation* is a point-ordering fact with only
partial statistical resolution (5/8 nominal, 1/8 after Holm), and
"log-affine beats isotonic LOO" is a point comparison whose paired-difference
CI includes zero — it should be restated as a parsimony claim, not a
significance claim. The weakened versions below are the ones that go in the
paper.

---

## 1. Blind γ₁₁₀ prediction with honest clustering

**Reconstruction.** Per (model, material) over the 9 fcc materials × 4 models:
Δε(8) = err(γ₁₀₀)·(a₀²/2)/16.0218, Δε(9) = err(γ₁₁₁)·(√3/4·a₀²)/16.0218,
Δε(11) = err(E_vac)/12 (eV); predicted γ₁₁₀ error =
(2Δε(8) − Δε(9) + Δε(11)) / (a₀²/√2/16.0218) J/m², with each cell's own
relaxed a₀. Reproduces the paper exactly: **overall r = 0.9064** (n = 36),
median |residual| = **0.0662** vs **0.1040** J/m² for predict-zero, and
**26 strict wins / 1 tie / 9 losses** at ×10⁴ integer precision (the single
tie is the same cell the Lean kernel rejected via `813 < 813`).

**(a) Per-model r (n = 9 each) — the cells are 4 models × 9 materials, not 36
independent draws:**

| model | r (n = 9) | within-model permutation p (one-sided, 10,000 perms) |
|---|---|---|
| chgnet | 0.858 | 0.0034 |
| mace-mp-small | 0.897 | 0.0002 |
| mace-mp-medium | **0.472** | **0.100 (not significant)** |
| mace-mpa-0-medium | 0.955 | 0.0014 |

**(b) Cluster-aware CI for the overall r.** Bootstrap resampling **materials**
(9 clusters; all 4 models' cells move together), 10,000 draws, seed 20260702:
**95% CI [0.818, 0.961]**, bootstrap median 0.914. Leave-one-material-out r
ranges 0.857 (drop Ni — the highest-leverage material) to 0.944 (drop Pt):
no single material carries the result.

**(c) Median-residual comparison, clustered.** Same material-clustered
bootstrap for Δ = median|residual| − median|error|: point −0.0378 J/m²,
**95% CI [−0.1117, −0.0014]**, bootstrap two-sided p = **0.036**. The
improvement over predict-zero survives clustering, but only marginally — the
CI nearly touches zero. Naive (unclustered) sign test on the 26/36 win count:
two-sided p = 0.0113; flagged as naive because cells within a material are
correlated.

**Honest permutation null.** Material labels of the *predictions* permuted
within each model (cross-model structure and all marginals preserved), 10,000
draws, seed 20260703: **null mean r = 0.439**, sd 0.128, p95 = 0.755,
p99 = 0.801, max = 0.868. Observed r = 0.9064 exceeds all 10,000 permutations:
**p = 1.0 × 10⁻⁴** (resolution floor 1/(N+1)).

**What goes in the paper (weakened version).** r = 0.906 stands, but (i) a
naive "r vs 0" framing overstates the evidence — roughly half the pooled
correlation (null mean 0.44) comes free from cross-model pooling of error
scales; the correct statement is "exceeds all 10,000 within-model material
permutations, p = 10⁻⁴, material-clustered 95% CI [0.82, 0.96]"; (ii) the
blind prediction is **not individually significant for mace-mp-medium**
(r = 0.47, p = 0.10, n = 9) — the field claim is carried by chgnet,
mace-mp-small, and mace-mpa-0-medium; (iii) the median-residual improvement is
significant under clustering but marginal (p = 0.036).

---

## 2. Family-exponent equality: separation vs constancy

**Fits.** α = OLS slope of log(pred) on log(ref). Surfaces: 41 points/model
(9 fcc × 3 facets + 7 bcc × 2 facets, γ₁₁₀ included — this reproduces the
paper's α ∈ [1.065, 1.138]); vacancies: 17 materials; B₀: 21 materials.

| model | α surfaces | α surfaces (excl. γ₁₁₀) | α vacancy | α B₀ |
|---|---|---|---|---|
| chgnet | 1.1375 | 1.1613 | 0.808 | 1.002 |
| mace-mp-small | 1.1287 | 1.1339 | 0.917 | 0.907 |
| mace-mp-medium | 1.0648 | 1.0515 | 0.857 | 0.901 |
| mace-mpa-0-medium | 1.0985 | 1.1102 | 0.894 | 1.019 |

**Family separation (paired bootstrap over materials, both slopes refit per
draw, 10,000 draws, seed 20260704).** Difference = α_surfaces − α_other:

| model | surf − vac [95% CI] | p | surf − B₀ [95% CI] | p |
|---|---|---|---|---|
| chgnet | +0.330 [−0.031, 0.666] | 0.074 | +0.135 [0.017, 0.304] | 0.028 |
| mace-mp-small | +0.212 [0.022, 0.405] | 0.024 | +0.221 [0.067, 0.323] | 0.014 |
| mace-mp-medium | +0.208 [0.026, 0.363] | 0.024 | +0.164 [−0.031, 0.263] | 0.081 |
| mace-mpa-0-medium | +0.204 [0.077, 0.342] | 0.0012 | +0.080 [−0.086, 0.194] | 0.385 |

All 8 point differences are positive (the kernel-checked point facts stand as
deterministic properties of this dataset), but **only 5/8 CIs exclude zero**,
and after Holm within the 8-test family **only mace-mpa-0-medium surf − vac
survives** (adjusted p = 0.0096). The 8 tests are strongly dependent (shared
materials and references), so no sign-binomial across models is valid.

**Cross-model constancy (variance decomposition).** Between-model variance of
the four surface α's: 1.08 × 10⁻³ (sd 0.033). Mean within-model bootstrap
variance: 2.79 × 10⁻³ (sd 0.053). **Ratio between/within = 0.39** — the
cross-model spread of the surface exponent is *smaller* than a single model's
statistical uncertainty.

**Precise statement of what IS supported — these are different claims:**

- **Family separation** ("surfaces have a larger exponent than vacancies/B₀
  within each model"): supported as a point-ordering on this dataset (8/8),
  *partially* resolved statistically (5/8 nominal at 95%, 1/8 after Holm).
  The paper's "kernel-checked point facts" wording is accurate; any wording
  implying eight independently significant differences is not.
- **Cross-model constancy** ("α ≈ 1.10 across four models"): the between-model
  spread (0.033) sits well inside single-model noise (0.053) — the data are
  *consistent with* a common surface exponent. This is compatibility (failure
  to detect a difference), not demonstrated identity; the paper's existing
  caveat "CI-overlap, not proven identity" is the right register and should
  be kept next to the ratio 0.39.

---

## 3. LOO correction comparisons (surfaces, per model)

**Setup.** Leave-one-(material, facet)-cell-out over the 41 surface points per
model. Log-affine: fit log P = log c + α log T on train, correct held-out via
T̂ = (P/c)^{1/α}. Isotonic (8-knot): 8 quantile bins of train P, bin means,
weighted PAVA, piecewise-linear interpolation clamped at the ends. Metric:
median relative error |T̂ − T|/T.

| model | raw | log-affine LOO | isotonic-8 LOO |
|---|---|---|---|
| chgnet | 27.96% | 10.04% | 14.16% |
| mace-mp-small | 12.05% | 7.45% | 8.86% |
| mace-mp-medium | 8.98% | 8.22% | 7.51% |
| mace-mpa-0-medium | **4.89%** | 6.80% | 5.99% |

Validation: raw (27.96%) and log-affine (10.0%, 7.45%) reproduce the paper's
numbers exactly, so the LOO protocol matches. **Caveat:** this isotonic
implementation is not the Lean one (paper: 11.2% / 7.79%; here 14.16% /
8.86%). Since the paper's isotonic is *better* than this one, the true paired
difference is smaller than measured here — which only strengthens the
non-significance finding below. mace-mpa-0-medium raw beats every correction,
confirming the paper's PASS-cell statement.

**Paired per-cell differences (median; material-clustered bootstrap CI,
10,000 draws, seed 20260705):**

| comparison | median Δ | 95% CI | p | excludes 0 |
|---|---|---|---|---|
| chgnet: isotonic − log-affine | +0.0243 | [−0.0430, +0.0476] | 0.447 | **no** |
| mace-mp-small: isotonic − log-affine | +0.0038 | [−0.0162, +0.0271] | 0.689 | **no** |
| chgnet: raw − log-affine | +0.2179 | [+0.1720, +0.2687] | 0.0004 | yes |
| mace-mp-small: raw − log-affine | +0.0483 | [−0.0041, +0.0942] | 0.061 | **no (marginal)** |

**What goes in the paper (weakened version).** "Two-parameter log-affine
beats 8-knot isotonic out-of-sample" is a **point comparison**; the paired
per-cell difference is not distinguishable from zero for either softened
model. Restate as: *the two-parameter form matches the 8-knot nonparametric
correction out-of-sample (paired-difference CIs include zero) with six fewer
parameters* — a parsimony claim, not a superiority claim. Correction-vs-raw
is decisive for CHGNet (median error 27.96% → 10.04%, p = 0.0004) but only
marginal for MACE-small under clustering (12.05% → 7.45%, CI [−0.004, +0.094],
p = 0.061); the paper should say "significantly for CHGNet; directionally for
MACE-small".

---

## 4. Multiple-testing policy

**Inventory (from the paper's Results as written).** ≈ 47 sampling-based
inferential statements — §3.1: 6 participation-ratio tests, 3 cosine-vs-null
tests, 3 defect/bulk ratio CIs; §3.2: ≈ 16 rank-correlation estimates; §3.3:
12 log-log fits, 2 LOO comparisons, 1 one-anchor transfer; §3.4: r, median
residual, win count; §3.6: 1 EAM-degradation comparison — plus ≈ 34
deterministic kernel-checked point facts (22 facet orderings, 8 strict
exponent inequalities, prefactor/warp orderings, the γ₁₁₁ exact permutation,
Zhou-vs-CHGNet cell counts). Deterministic facts are properties of the
measured dataset, carry no sampling claim, and need no correction; every
sampling-based inference belongs to a claim family.

**Policy defended: Holm step-down within each pre-specified claim family**
(pre-registered primaries stated per family; deterministic facts exempt).
Results on the three families hardened here:

- **Blind field (3 tests):** permutation r (adj. p = 3.0 × 10⁻⁴), win-count
  sign test (adj. p = 0.023), median-residual (adj. p = 0.036) — **all three
  survive Holm**. The headline permutation p = 10⁻⁴ also survives a
  paper-wide Bonferroni over all ≈ 47 sampling-based tests (threshold
  ≈ 0.00106).
- **Exponent separation (8 tests):** only mace-mpa-0-medium surf − vac
  survives (adj. p = 0.0096); the other seven have adjusted p ≥ 0.095.
- **LOO corrections (4 tests):** only chgnet raw − log-affine survives
  (adj. p = 0.0016).

**Do the headline claims survive?** The §3.4 blind-prediction claim survives
in full (all three tests, and the primary survives paper-wide Bonferroni).
The §3.3 claims survive only in their weakened forms stated above: family
separation as point-ordering plus one Holm-surviving difference; cross-model
constancy as compatibility-with-noise (ratio 0.39); log-affine-vs-isotonic as
parsimony, not superiority; correction-vs-raw as significant for CHGNet only.

---

*Reproduce: `python python/scripts/harden_stats.py` (writes
`statistical_hardening.json`; deterministic given the committed data and
seeds).*
