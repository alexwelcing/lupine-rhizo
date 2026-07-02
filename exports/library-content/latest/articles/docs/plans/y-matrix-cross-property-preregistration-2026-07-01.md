# Y-Matrix Pre-Registration — Cross-Property Error Geometry

> **Version:** 1.0 (2026-07-01)
> **Objective:** Determine whether foundation-MLIP error geometry spans property
> families — i.e., whether the low-dimensional structure previously measured
> inside elastic constants is a property of the *model* (a real ribbon in
> prediction space) or an artifact of the *property family's internal physical
> coupling* (Cauchy relation, stability constraints).
> **Registered before confirmatory analysis** of the first cross-property sweep
> (`data/y_matrix_runs/`, launched 2026-07-01). The sweep's machinery smoke
> tests (Ni/MACE-MP-small) were observed during development and are quarantined
> as exploratory — see §Exploratory quarantine.

## Revision history

| Date | Change | Author |
|------|--------|--------|
| 2026-07-01 | v1.0 — initial registration | squad (Claude + Alex Welcing) |

## Why this experiment is the critical one

All prior evidence in the ledger (~1,320 records) sits inside one property
family: 0 K cubic elastic constants. Elastic constants are physically coupled
to each other, so low-dimensional error structure measured within them cannot
distinguish "the model's error manifold is a hyper-ribbon" from "elasticity is
internally coupled." The Y-matrix adds property families with *different*
physical couplings — point defects, surfaces, planar faults, equations of
state, formation enthalpies — which breaks the degeneracy. Whatever the
outcome, the correction program ("the turbo") ships; this experiment determines
its **gearing** (one shared correction operator vs per-family operators).

## Systems

- **Tier 1 (metals):** Ni, Cu, Al (fcc — full battery incl. SFE); Fe, W (bcc —
  no SFE lane). Expansion to the full 16-metal set follows the same registered
  protocol.
- **Tier 3 (beyond metals):** Si (diamond); NiAl (B2); Ni3Al (L1₂).
- **Tier 2 (finite-T: thermal expansion, melting):** staged; NOT covered by
  this registration. A separate registration will follow.

## Property families (Y)

Per material, as structurally applicable:

| Family | Properties | Unit |
|---|---|---|
| Lattice/cohesion | a₀ | Å |
| EOS | B₀, B₀′ | GPa, — |
| Point defect | E_vac | eV |
| Surfaces | γ₁₀₀, γ₁₁₀, γ₁₁₁ (fcc); γ₁₀₀, γ₁₁₀ (bcc) | J/m² |
| Planar fault | γ_SFE (fcc only) | mJ/m² |
| Compound stability | ΔH_f (intermetallics) | eV/atom |

Computed by `python/lupine_distill/statics/` (226-test suite; bit-reproducible
≤1e-11), CLI `python/scripts/run_y_matrix_statics.py`, GPU lane pinned in
`python/requirements-gpu-lane.lock`.

## Model grid (X)

- MACE-MP-0 small, MACE-MP-0 medium (mace-torch 0.3.16)
- CHGNet 0.4.2

Explicit fail-fast model registry — no silent substitution (registered as a
design invariant after the torchsim model_id defect, fixed 2026-07-01).
Expansion models (M3GNet/TensorNet via matgl, Orb, SevenNet, UMA) join under
the same protocol when their lanes are pinned.

## Reference targets and binding policy

Reference values live exclusively in `data/y_matrix_targets/*.json`
(schema `lupine.y_matrix_targets.v1`), compiled under a **no-fabrication
rule**: every value carries a verified citation; unverifiable values are
recorded as unresolved gaps, and **properties whose reference is unresolved
are excluded from confirmatory hypothesis tests** (they may be reported
descriptively, labeled as such). Where DFT and experimental references both
exist they are separate entries; the confirmatory target per property is the
**DFT-PBE value when available, else experiment**, chosen now to match the
training-data provenance of the model grid (all MP/MPtrj-derived). Elastic
reference values additionally require resolution of the known
Family A/B discrepancy (audit finding, task #11) before elastic properties
join the cross-property vectors.

## Registered hypotheses and kill conditions

### H1 — Cross-property low dimensionality

For each model, assemble per-material error vectors across all
reference-resolved properties (normalization: signed relative error
(pred − ref)/|ref| per property; properties with |ref| below 10× its
compilation uncertainty use absolute error scaled by the family's median |ref|
— guard against near-zero-reference degeneracy, e.g. SFE). The participation
ratio of the material-by-property error covariance is **lower than the 95th
percentile of the coupling-aware null** (§Nulls).

**Kill:** PR within or above the null band → the elastic-era "ribbon" is not a
cross-property object; report as refutation of cross-property universality.

### H2 — Shared leading error mode across models

The leading principal error mode (from H1's covariance) has pairwise cosine
similarity > 0.7 across the three models, exceeding the 95th percentile of
the same statistic under the null.

**Kill:** similarity indistinguishable from null → error geometry is
model-specific; correction operators do not transfer across architectures.

### H3 — Training-distribution failure prediction

Properties underrepresented in MPtrj-style training data (E_vac, γ_SFE,
surfaces) show larger median |relative error| than bulk-adjacent properties
(a₀, B₀, ΔH_f) for **every** model, by at least a factor of 2.

**Kill:** any model where defect-family and bulk-family errors are comparable
(< 1.5×) → the weak-spot story is model-dependent, not distributional.

### H4 — Correction transfer (staged)

The elastic-trained scalar-bulk operator (v0.2, the Round-2 win), applied to
Y-matrix cells, reduces cross-property error norm. **Staged:** the operator
implementation is not currently in this repo (recovery/reimplementation
pending); H4 binds when it lands, before its transfer analysis runs.

**Kill:** operator improves elastic but degrades ≥ half of non-elastic
properties → correction is family-local; the turbo ships with per-family
gearing.

#### H4 binding addendum (2026-07-02, registered BEFORE the transfer analysis runs)

Context: H1/H2 were killed and H3 passed (see
`y-matrix-confirmatory-results-2026-07-01.md`), so the registered *expectation*
is now that transfer FAILS; observing transfer would be the surprising outcome.

- **Operator (reimplemented to the documented v0.2 definition, adapted to the
  Y-matrix):** per model, a single stiffness-rescaling scalar
  `s = median(B0_ref / B0_pred)` fitted **leave-one-material-out** over the
  primary matched set (15 metals; the held-out material never contributes to
  its own correction).
- **Application:** corrected prediction = `s × prediction` for
  energy/stiffness-like properties (B0, E_vac, gamma_100/110/111, gamma_SFE,
  dH_f); a0 is excluded from correction (a length, not an energy scale — the
  softening mechanism predicts no first-order a0 effect).
- **Metrics:** per (model, family): median |relative error| before vs after,
  LOO throughout, 1,000-draw bootstrap CI on the delta; seed 20260702.
- **Improvement/degradation:** a family improves/degrades if its median
  |rel. err.| moves by more than the bootstrap CI95 half-width; else unchanged.
- **H4 pass:** ≥ half of non-EOS families improve and none degrade.
  **H4 kill (registered expectation):** EOS-family improves while ≥ half of
  non-EOS families degrade or are unchanged.
- Fe stays in with its deficiency annotation; Cr stays out (matched-n);
  (Ni, mace-mp-small) quarantine does not apply to H4 (it was H3-specific).

## Round 2 registrations (2026-07-02, registered BEFORE the MPA-0 sweep runs)

### R2-H1 — Training-distribution causality (the softening story's direct test)

Published claim (Deng et al., npj Comput. Mater. 2024/25, arXiv:2405.07105;
corroborated arXiv:2410.12771): softening is data-distribution-driven — models
trained with off-equilibrium data (OMat24 lineage) largely eliminate it.
Registered prediction: **MACE-MPA-0 (medium-mpa-0), run through the identical
63-cell matrix and H3 analysis, shows a defect/bulk median-error ratio less
than HALF of MACE-MP-medium's (i.e., < 7.66 vs 15.32 on the primary matrix),**
and its per-model B₀ softening scalar s sits closer to 1 than any MPtrj model's.

**Kill:** MPA-0 ratio ≥ half of MACE-MP-medium's → distributional retraining
does not collapse the defect/bulk split on elemental metals; the contested
symmetry-related residual story (arXiv:2507.15190) gains weight.
*(Citation correction 2026-07-02, post-verdict: arXiv:2507.15190 is withdrawn
and its abstract never made the attributed claim; the kill's interpretation
clause should read simply "a residual beyond distributional bias exists,"
supported by our own R2 decomposition only.)*
Same seed/nulls/exclusions as Round 1; Fe deficiency annotation carries over
pending its per-model shape diagnostic.

## Nulls (coupling-aware — mandatory)

Naive permutation nulls lie when properties are internally coupled. The
registered null: **within-family structure preserved, cross-family alignment
broken** — for each property family independently, permute the material labels
of that family's error sub-vectors (1,000 draws; matched-n; per-material
completeness required — materials missing any confirmatory property are
excluded from the vector analysis rather than imputed). This preserves each
family's internal covariance (including elastic self-coupling) and destroys
only the cross-family correlation that H1/H2 claim.

## Exploratory quarantine

Observed during machinery development, before this registration, on
(Ni, MACE-MP-small): E_vac ≈ 1.02 eV vs ~1.45 eV PBE; γ_SFE ≈ −8 mJ/m² vs
~145 mJ/m² PBE; a₀/B₀/ΔH_f near reference. These observations motivated H3 and
are **excluded from H3's confirmatory test for that (material, model) cell**;
H3 is evaluated on the untested cells.

## Outputs and provenance

Every cell emits `lupine.mlip.calc_evidence.v1` (canonical-inputs sha256,
model id as-run, per-property values) to `data/y_matrix_runs/`; reference
annotation and Lean emission (`emit_lean_module`, within/exceeds encoded
either way) follow reference binding. Ledger landing is gated on the ingest
range fix (task #12) and does not gate the analysis.

## Deviations log

| Date | Deviation | Reason |
|------|-----------|--------|
| 2026-07-01 | **Fe excluded from confirmatory vectors** pending magnetic-state verification. | Sweep Fe/bcc B₀ came back 71–89 GPa across all three models (vs ~170 GPa experimental) — consistent with the calculators relaxing to the nonmagnetic branch because `statics.structures` sets no initial magnetic moments. This is a state-preparation issue, not model error; attributing it to the models would be a false negative-transfer claim. Fe rejoins after initial-magmom support is added and cells re-run. Logged before reference binding. |
| 2026-07-01 | **H1 criterion wording defect, logged at analysis time**: the registered sentence "lower than the 95th percentile of the coupling-aware null" is vacuous as written; the analysis implements the intended strict one-sided test `PR < null p05` and reports both readings. See `y-matrix-confirmatory-results-2026-07-01.md` §Deviations. | Wording error in v1.0; the strict reading is adverse to the hypothesis (H1 passes 2/6 under it vs ~6/6 under the vacuous literal reading), so the clarification cannot inflate the result. |
| 2026-07-01 | **AMENDMENT (same day, still before reference binding): Fe re-admitted to confirmatory vectors with a documented-model-deficiency annotation; the previous row's reason is empirically falsified.** | CPU investigation (scratchpad `fe_investigation/memo.md`): initial magnetic moments change the energy of neither calculator (ΔE = 0.0 eV exactly; MACE is spin-blind, CHGNet magmoms are outputs — it predicts FM Fe at 2.44 μB and is soft anyway). B₀ ≈ 70–90 GPa is fit-window-independent (±3% → ±15%: <1 GPa change for MACE-small) with a curvature anomaly (B₀′ = −12.9/−7.4 in the stored fits) matching the published PES-softening pathology of MPtrj-trained uMLIPs on magnetic Fe (Deng et al. arXiv:2405.07105; Springer J. Phase Equilib. Diffus. 2025; arXiv:2605.28395). The "magmom support + re-run" remedy is struck (provable no-op). Fe is therefore genuine negative-transfer evidence, exactly what the Y-matrix measures. Protocol additions: BM3 fits auto-flagged when B₀′ ∉ [1, 8]; magnetic elements (Fe, Cr, Mn, Co, Ni) get a one-shot wide-scan shape diagnostic before binding. Cr is NOT pre-excluded (its sweep-2 cell shows the opposite symptom: stiff, B₀′ normal). |
