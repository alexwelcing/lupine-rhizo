# The Monotone Reparameterization Hypothesis (MRH)

> Status: unified statement, 2026-07-02. Every numeric claim below is drawn
> from provenance-hashed artifacts in `data/y_matrix_runs/` and sealed as
> type-checked Lean modules (`lean/Round1..6_*.lean`). Novelty claims are
> bounded by two adversarially-verified deep-research sweeps (≈200 sources,
> 3-vote verification); community replication is the final arbiter.

## The claim, in one sentence

**Foundation interatomic potentials learn the physics of a property family up
to a single monotone warp of the property axis: they get the *order* of
nature right and the *size* wrong, in a way that is one invertible distortion
per (model, property family) — measurable with a handful of anchors,
invertible with proof, and provably absent where training data was too thin
to fix even the order.**

In plain language: ask a foundation model *which* metal has the higher
surface energy and it almost never lies; ask it *how much* and it is wrong by
a warp — the same warp for every metal and every facet in the family. Warps
can be measured and undone. Scrambles cannot — and we can prove, in a proof
checker, which one you have.

## Formal statement

For model M and property family F, there exists a strictly increasing map
w_{M,F} such that predictions satisfy P ≈ w_{M,F}(T) across materials, where
T is the reference value. Corollaries:

1. **Ordinal invariance** — rankings of T are preserved by P (the
   invertibility condition for w).
2. **Family-level warp** — one w serves all properties in F (facets of a
   surface share w; the family, not the property, is the warp's domain).
3. **Training-distribution control** — w's distance from identity is set by
   training-data bias, not architecture; better-distributed retraining moves
   w toward identity without changing what is ordered.
4. **Correction = inversion** — calibration is w⁻¹, computable from a few
   anchor (P, T) pairs by isotonic regression; it lives in the monotone
   group.
5. **The boundary** — where training data was insufficient to fix even the
   order, no monotone correction exists (provably), and the model's output
   for that (M, F) must be discarded, not calibrated.

## Evidence (all measured on the 21-material × 4-model Y-matrix, this repo)

| # | Observation | Where sealed |
|---|---|---|
| 1 | Rankings survive where magnitudes fail: ρ = 0.82–1.00 across surfaces, vacancies, B₀; 22/22 facet orderings; MPA-0's γ₁₁₁ ranking is *exactly* the reference permutation | `Round3_Ordinal.lean` (23 thms — kernel checks the order itself) |
| 2 | Scalar (affine) corrections fail at every grain — per-model, per-material, within-family | `Round1_H4.lean`; H4 artifact |
| 3 | Monotone correction succeeds where MRH says it must: CHGNet surfaces 36→9%, MPA-0 γ₁₁₁ 9→2% (LOO); the correction computed in-kernel for the flagship (Pt: 12.9→0.6%) | `Round4_Isotonic.lean` |
| 4 | **Family-level warp (confirmed prediction):** γ₁₀₀-fitted map corrects unseen γ₁₁₀/γ₁₁₁ — CHGNet 26.8→9.9%, MACE-small 13.0→6.7% — *beating same-facet calibration* | `Round6_MRH.lean` |
| 5 | **Warp→identity ordering (confirmed prediction):** pooled warp magnitude 0.051 < 0.099 < 0.120 < 0.388 strictly orders MPA-0 < MACE-med < MACE-small < CHGNet by training lineage | `Round6_MRH.lean` |
| 6 | Bias/variance split: OMat retraining removes warp bias (s 1.08→0.97, Fe flips soft→stiff) but not per-material variance | R2 artifact; `Round2_Verdicts.lean` |
| 7 | The boundary is real and provable: MPtrj SFE rank inversion ⇒ **no monotone correction exists** (quantified impossibility theorem, not policy) | `Round4_Isotonic.lean` (`sfe_mptrj_uncorrectable`) |
| 8 | The warp is a *single-model* object: separately-fitted potential families (EAM, 5 and 24-cell tests) do not share a warp and are not family-calibratable | this session's EAM artifacts |

## Relation to the hyper-ribbon program

Round-1's registered H1/H2 "kills" refuted **linear** low-dimensionality
(participation ratio, leading-mode cosines — linear instruments). MRH locates
the structure those instruments could not see: the error manifold is
low-dimensional **after allowing monotone reparameterization** — one curved
degree of freedom per family. **The ribbon is real, and it is curved.** The
Transtrum–Sethna sloppiness picture survives in nonlinear form; the linear
kills were the necessary step that forced the nonlinear formulation.

## Relation to published work (honestly bounded)

- PES softening (Deng et al. 2024/25) documents systematic *underprediction*
  and corrects with per-system linear rescaling. MRH subsumes it: softening
  is the bias component of a monotone warp; our data show the warp is
  neither linear nor per-system-scalar (H4, evidence #2) but family-monotone
  (#4).
- Our two verified literature sweeps found **no published
  transferability-of-correction study and no ordinal/cardinal decomposition
  of foundation-model error** — the field's own open questions list asks for
  exactly these. To the limit of that search, evidence #1–5 and the
  impossibility-gate methodology (#7) are new.
- Machine-checked certificates for benchmark claims, corrections computed in
  the proof kernel, and compile-time applicability gates have no precedent
  we could find in any materials-simulation toolchain.

## v2 — The refined law: the family exponent (2026-07-02, later the same day)

Exploration past the nonparametric statement found the warp's **form**:

> **pred ≈ c · T^α** — log-affine, R² = 0.93–0.98 (surfaces, B₀).
> **The exponent α belongs to the property family; the prefactor c belongs to
> the model.**

Evidence (sealed in `Round7_FamilyExponent.lean`; CIs in the analysis run):

- α clusters by family across all four models: surfaces ≈ 1.10 (bootstrap CIs
  1.07–1.22 / 1.06–1.19 / 1.00–1.13 / 1.05–1.15, all overlapping), B₀ ≈ 0.95,
  vacancies ≈ 0.87 (wider CIs). Every model's surface exponent exceeds every
  model's vacancy and B₀ exponent (point facts, kernel-checked).
- Training moves c toward 1 and barely moves α: CHGNet surfaces c = 0.66 →
  MPA-0 c = 0.98, while α stays ~1.1. This *is* Round 2's bias/variance split,
  now with named parameters.
- The two-parameter correction **beats 8-knot isotonic** LOO on the softened
  models (CHGNet 10.0% vs 11.2%; MACE-small 7.45% vs 7.79%) — the minimal
  form is the better estimator.
- **One anchor suffices**: family α from *other* models + a single measured
  (P, T) pair halves CHGNet's surface error (27.96% → 14.3%).

Every earlier result is a corollary: scalar corrections fix c while α ≠ 1
(H4's failure); monotone maps contain power laws (isotonic's success); facets
share both numbers (family transfer); rank preservation is what any power law
does; and the SFE impossibility marks where even the power-law form collapsed.

Honest bounds: three families, four models, one lab; vacancy CIs are wide
(CHGNet's spans 0.44–1.19); α family-constancy is CI-overlap, not proven
identity; MPA-0's surfaces remain a PASS cell (raw beats every correction).

## What would kill MRH (registered, in the typed-claim-shape sense)

- A property family with high rank-fidelity whose fitted warp *fails* to
  transfer within-family on new materials (hcp metals, alloys are queued).
- Warp non-monotonicity appearing at interpolation densities where ranks are
  preserved (would break corollary 4).
- A model whose warp distance orders *against* its training-data quality.

## Practical consequence (the part a lab uses tomorrow)

- Screening decisions (which candidate is best) are already trustworthy at
  ρ ≥ 0.9 — no correction needed; we certify the ordering itself.
- Certification decisions (what is the number) need k anchor measurements
  per (model, family) — k ≈ 8 sufficed here — then w⁻¹ delivers up to 4×
  error reduction at zero additional simulation, inside existing LAMMPS
  workflows via log post-processing.
- Where no correction can exist, the system refuses with a proof — before a
  core-hour is spent. (`Round5_LammpsValue.lean` holds the cost-accuracy
  facts: a classical potential beating CHGNet 20/24 cells at ~6× less
  compute, no GPU.)
