# Round-3 preregistration — licensed corrections, out-of-sample

> **Status:** REGISTERED 2026-07-13, before any Round-3 measurement or
> reference sourcing for the evaluation set. Frozen by this document; changes
> after evaluation data exists void the registration.
> **Prior state:** Round 1 (preregistered, cross-class correction FAILED),
> Round 2 (exploratory rule selection on Round-1 data — NOT confirmatory),
> adversarial review dispositions in
> `2026-07-13-errata-and-red-team-dispositions.md`.

## Frozen correction rule (verbatim from Round-2 exploration + registered cap)

For a held-out candidate X, model m, property p, class C:
1. Calibration set = other class-C members with a non-null reference
   (never X). Require >= 2 members, else ABSTAIN.
2. ratios_i = pred_i / ref_i over calibration members.
3. Direction gate: apply only if ALL ratios are strictly on one side of 1,
   else ABSTAIN.
4. **Magnitude cap (new, closes the FeNi gap):** let b = median(ratios),
   s = max(ratios) - min(ratios). ABSTAIN unless |b - 1| > s. (The learned
   bias must exceed the calibration scatter; prevents wrong-direction and
   overshoot application when the class signal is weaker than its noise.)
5. corrected = pred / b; else corrected = pred (abstention, risk-free).

## Evaluation set (out-of-sample; references to be sourced AFTER registration,
by the same provenance discipline, and locked before any GPU run)

- Perovskites (never used in any calibration): CsPbBr3, CsPbCl3, RbSnBr3,
  KSnCl3 (fallbacks if references unfindable: CsCaF3, KMgF3 — classic cubic
  fluoroperovskites with measured Cij).
- Ionic rocksalts (out-of-sample vs thresholds-v3 ionics): KCl, KBr, RbCl,
  NaF (all with experimental a0/B0/Cij in the alkali-halide literature).
- Properties: a0, B0, C11, C12, C44 (weak/null references excluded from
  criteria AT REGISTRATION when sourced, and excluded from ALL report tables).

## Primary statistic and criteria (computed, not just stated)

- Per group x property (references non-null): median |rel err| raw vs
  corrected; exact binomial sign test over held-out cells (ties dropped).
- SUCCESS per group: corrected beats raw on >= 2/3 evaluable properties with
  sign-test p < 0.1. FAILURE otherwise, reported verbatim.
- KILL condition: if the frozen rule fails both groups, the correction
  layer's scope claim narrows to "same-class lattice constants only" in all
  public material until new evidence.
- Gates reported as within-class risk-coverage tables; control false
  refusals tabulated. No pooled cross-class efficacy ratios.

## Registered instrument fixes (before Round-3 runs)

1. Dispersion metric: denominator floor at 0.1x the class-median |value| per
   property (C44 sign-crossing pathology); regenerate thresholds.v2/v3 under
   the fixed metric; audit V and Cr calibration cells.
2. thresholds.v3 perovskite class marked provisional/in-sample; Round-3
   perovskite evidence creates the first out-of-sample perovskite corpus.
3. Round-1 criteria evaluation script appended to round1 report (honest
   PASS/FAIL, including the silent Cij-bias degradation).
4. NEB: one 3x3x3 scaling point per compound (one model) bounds finite-size
   error before any kinetics threshold derivation; endpoint-vs-band-minimum
   convergence check replaces the symmetric-asymmetry check.
5. Defect energies: absolute-spread headlines; negative formation energies
   flagged invalid, never pooled; family-restricted rows labeled.
6. B0 concordance demoted to descriptive program-wide (fcc rho = -0.63);
   only Born and bcc a0 currently carry a dispersion-error license.

## Honesty boundary

n per group remains small (4-6); this remains a methodology demonstration.
Reference conventions (RT vs athermal; charged vs neutral) are recorded per
value and, for a0, decomposed where published expansion data allows.
