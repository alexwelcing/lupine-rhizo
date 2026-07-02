# Y-Matrix Confirmatory Results — Round 1 (2026-07-01)

> **Process note (2026-07-02):** these two rounds ran with pass/kill
> thresholds on questions that were, in truth, exploratory cartography — and
> R2-H1's "KILL by 2.6%" against an arbitrary threshold shows the cost: the
> verdict frame can bury the finding (bias eliminated, variance persists).
> Going forward, registration with thresholds is reserved for claims where we
> are the interested party (uplift claims about our own correction operator)
> and for publication-bound claims. Exploratory results are reported as
> descriptive findings with coupling-aware nulls and uncertainty — the
> statistics stay, the verdict theater goes. The rounds below are preserved
> as recorded, per the retraction-preserving discipline.

> Registered protocol: `y-matrix-cross-property-preregistration-2026-07-01.md`.
> Data: 57 GPU cells (19 materials × MACE-MP-small / MACE-MP-medium / CHGNet),
> 345 reference-bound properties, **57/57 evidence-derived Lean modules
> type-checked** (`data/y_matrix_runs/bound/binding_report.json`).
> Analysis artifacts: `data/y_matrix_runs/analysis/confirmatory_*.json`
> (seed 20260701, 1,000 null draws, 1,000 bootstrap).
> Matrices: **primary** 15 metals × {a₀, B₀, E_vac, γ₁₀₀, γ₁₁₀} (Cr dropped by
> matched-n — coarse B₀ reference; Fe included per the registered amendment);
> **secondary** 7 fcc metals × 7 properties (+γ₁₁₁, γ_SFE).

## Scoreboard

| Hypothesis | Verdict | Detail |
|---|---|---|
| **H1** cross-property low dimensionality | **NOT CONFIRMED** (2/6 pass) | PR mostly *within* the coupling-aware null band. Primary: MACE-small 2.76 (null p05 2.34), MACE-medium 2.36 (2.11) — fail; **CHGNet 2.00 < 2.17 — pass**. Secondary: **MACE-medium 1.47 < 1.50 — pass**; others fail. |
| **H2** shared leading error mode | **KILLED** (0/3 pairs, both matrices) | Raw cosines up to **0.96** — but the family-permutation null's p95 reaches **0.98**: the apparent shared mode is carried by within-family magnitude structure, which the null preserves. No pair exceeds its null. |
| **H3** defect ≫ bulk errors | **PASSED, all models, both matrices** | Median \|rel. err.\|: bulk ~0.5–0.8%, defect ~11–31%. Ratios: MACE-small **18.9×**, MACE-medium **15.3×**, CHGNet **57.0×** (primary; secondary 21×/16×/62×). Registered threshold 2×; kill 1.5×. All bootstrap CI95 lower bounds > 1. |

## Deviations / analysis notes (logged with results)

1. **H1 criterion clarification.** The registration's sentence "lower than the
   95th percentile of the coupling-aware null" is vacuous as written (a typical
   null draw satisfies it). The harness implemented the evidently intended
   one-sided 5% test, `PR < null p05`, which is stricter. Under the literal
   (flawed) wording H1 would "pass" nearly everywhere; under the intended test
   it passes 2/6. We report the intended test as primary and record the wording
   defect here rather than silently choosing the favorable reading.
2. Cr excluded by matched-n (only a 2-significant-figure CRC B₀ reference;
   flagged in the compilation). Si/NiAl/Ni₃Al are outside the metal matrix by
   construction (no defect/surface lanes); their bound properties are reported
   in the descriptive layer and the Lean modules.

## What the answers mean

**The turbo's gearing is per-family.** The elastic-era low-dimensionality does
not extend across property families as a universal ribbon: once within-family
coupling is granted to the null, only isolated (model, matrix) combinations
show compression below it, and no shared cross-model mode survives H2. A
correction operator learned on one family should not be assumed to transfer
across families via a shared low-dimensional mode. This refutes the strongest
form of the cross-property universality thesis for this X×Y slice — and it is
a *result*, registered in advance, with the kill conditions doing their job.

**What IS universal is the training-distribution split.** H3 is the cleanest
effect this program has measured: every model, both matrices, defect-family
errors 15–60× bulk-family errors, consistent with the published PES-softening
pathology of MPtrj-trained potentials. Bulk properties (a₀ at ~0.5%, ΔH_f at
~3%) are essentially solved by current foundation models; defect physics
(vacancies, surfaces, stacking faults) is where they fail, predictably and
enormously. The correction program's highest-ROI target is therefore
family-targeted defect corrections, not a global mode.

**The coupling-aware null prevented two false positives.** A naive analysis
would have reported cosine 0.96 cross-model mode alignment and "low" PRs as
confirmation of universality. Both are inside their null bands. The
methodological discipline — registered before data, nulls that preserve
within-family structure — is itself a result worth publishing alongside the
physics.

## H4 result (2026-07-02, run under the registered binding addendum)

**INCONCLUSIVE — neither the registered pass nor the registered kill fired,
for any model.** The kill's precondition failed everywhere: the LOO stiffness
scalar (s = 1.057 / 1.081 / 1.125 for MACE-small / MACE-medium / CHGNet) does
not improve even the EOS family it was fitted on — per-material B₀ softening
is too heterogeneous (Fe ≈ 2×, most metals 1.03–1.15) for any single
per-model scalar. No family significantly degrades; two isolated
bootstrap-significant improvements (CHGNet surfaces 0.285→0.215; MACE-medium
planar fault 0.682→0.665) are candidate gears requiring replication before
routing. Substantive finding: **the correction structure is finer-grained
than (model) or (model, family) — at least (model, family, material-class).**
Artifact: `analysis/h4_transfer.json` (seed 20260702, deviations: none);
verdict theorems: `lean/Round1_H4.lean` (type-checked).

## Literature positioning (2026-07-02, from the adversarially-verified synthesis)

A 104-agent deep-research pass (25 claims verified 3-0 or merged; 22 primary
sources; full artifact in the session transcript) situates Round 1:

- **H3 is the published softening pathology, quantified on our instrument.**
  Deng et al. (npj Comput. Mater. 2024/25; arXiv:2405.07105) document >90%
  softening prevalence in MPtrj-trained uMLIPs across surfaces, defects,
  phonons, and barriers. Our 15–60× defect/bulk ratios are that phenomenon
  under a pre-registered, coupling-aware protocol.
- **H1/H2's kills answer the field's open question.** The synthesis found NO
  published study of cross-property error-correlation for foundation MLIPs
  (the closest: PCA over 47 metrics × 34 *classical* Ni potentials,
  arXiv:2510.18033, which itself warns of partially orthogonal components).
  Round 1 is, to the limit of this search, the first pre-registered answer:
  for MACE-MP-small/medium and CHGNet across 15 metals, cross-property error
  structure does not compress below a family-coupling-aware null.
- **H4 is the first transferability-of-correction study.** Verbatim from the
  synthesis's open questions: "No published transferability-of-correction
  study surfaced." The published rescaling correction that works (single DFT
  anchor, ~15% force-MAE recovery) is *per-system* — consistent with H4's
  finding that a per-model scalar has no traction. The correction grain the
  field's method implies is the grain our kill measured.
- **Caveats adopted:** the classical-Ni PCA must not be silently generalized
  to foundation models; leaderboard numbers are model-version-specific.
  *(Citation correction 2026-07-02: this list previously cited
  arXiv:2507.15190 for a "residual survives OMat24" claim; that preprint is
  withdrawn and its abstract never made the attributed claim. Struck.)*
- **Protocols adopted for Round 2+:** MatCalc `PESCalculator.load_universal()`
  as the X-axis expansion path (7+ architectures, one interface); CPS-style
  multi-property scoring; the 47-metric Ni suite as an external cross-check
  for our Ni cells; fixed-and-reported displacement magnitudes for any
  phonon lane (ORB/eqV2 degrade at small displacements, arXiv:2412.10516).

## R2-H1 result (2026-07-02, MACE-MPA-0 through the identical matrix)

**Registered verdict: KILL — by 2.6%** (ratio 7.86 vs registered threshold
7.66). The decomposition, reported alongside because both halves are decidable
facts (`lean/Round2_Verdicts.lean`, type-checked):

- Defect median |rel err| **collapsed 2.6×** (4.65% vs MACE-MP-medium's
  12.13%) — the numerator behaved exactly as the distributional story
  predicts.
- Bulk median also improved (0.59% vs 0.79%) — the registered *ratio* missed
  its halving because the model got better everywhere. (Lesson for future
  registrations: ratios move with both ends; register absolute family errors
  as co-primary next time.)
- Softening **bias eliminated**: s = 0.970 (MPtrj models: 1.057–1.125); Fe
  flipped from 2× soft to 13% stiff. But per-metal spread persists
  (0.85–1.39), now centered on 1 — **OMat24 retraining removed the bias, not
  the variance**. *(Citation correction 2026-07-02: an earlier version cited
  arXiv:2507.15190 as corroboration; that preprint is withdrawn and did not
  support the paraphrase. The variance-persistence claim is our own
  measurement, standing alone.)*

Artifact: `analysis/r2_mpa0_confirmatory.json` (joint 4-model run, matched
15-metal set unchanged).

## Registered next tests

1. **H4 follow-up:** class-resolved operators — fit scalars per
   (model, family, structure/magnetic class) with LOO inside each class; the
   two isolated H4 improvements (CHGNet/surfaces, MACE-medium/planar-fault)
   are the first replication targets on new materials.
2. **CHGNet-primary and MACE-medium-secondary H1 passes** are follow-up leads,
   not confirmations (2/6 at the 5% level is compatible with chance): a
   replication set (new materials — hcp metals; MgO/NaCl now have references)
   is the honest next test.
3. **Fe/Cr magnetic-element lane**: Fe (soft, B₀′ < 0) and Cr (stiff) anchor a
   dedicated magnetic-failure study per the investigation memo.
4. Ledger landing of the 345 bound records + 57 verified theorem modules
   (blocked on task #12, the ingest-range fix).
