# Round-3 confirmatory analysis — frozen-rule corrections, out-of-sample

Generated 2026-07-13T19:10:32.477859+00:00 from `data/candidates/round3/report.json`.
Preregistration (FROZEN): `docs/plans/2026-07-13-round3-preregistration.md`.

Frozen rule: For a held-out candidate X, model m, property p, class C: (1) calibration set = other class-C members with a non-null reference (never X), require >= 2 members else ABSTAIN; (2) ratios_i = pred_i / ref_i over calibration members; (3) direction gate: apply only if ALL ratios are strictly on one side of 1, else ABSTAIN; (4) magnitude cap: b = median(ratios), s = max(ratios) - min(ratios), ABSTAIN unless |b - 1| > s; (5) corrected = pred / b; else corrected = pred (abstention, risk-free).

## Per-material n (materials, NOT cells — read this first)

Cells multiply materials by models; the material count below is the
honest sample size per group x property.

| group | a0 | b0 | c11 | c12 | c44 |
|---|---|---|---|---|---|
| ionics-rocksalt-oos | 4 | 4 | 4 | 4 | 4 |
| perovskite-oos | 4 | 4 | 4 | 3 | 4 |

## Arm table (per group x property)

Medians over evaluable held-out cells; sign test over cells where the
rule APPLIED (ties dropped). Absolute-unit deltas alongside relative.

| group | prop | n_mat | n_cells | n_applied | n_abstained | median \|rel err\| raw | median \|rel err\| corrected | median \|abs err\| raw | median \|abs err\| corrected | sign-test p | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|
| ionics-rocksalt-oos | a0 | 4 | 16 | 16 | 0 | 1.60% | 0.33% | 0.1012 Angstrom | 0.01939 Angstrom | 3.052e-05 | WIN |
| ionics-rocksalt-oos | b0 | 4 | 16 | 2 | 14 | 11.30% | 14.02% | 1.924 GPa | 2.855 GPa | 0.5 | WORSE |
| ionics-rocksalt-oos | c11 | 4 | 16 | 4 | 12 | 14.53% | 17.18% | 5.99 GPa | 6.968 GPa | 0.625 | WORSE |
| ionics-rocksalt-oos | c12 | 4 | 16 | 2 | 14 | 23.97% | 27.61% | 1.786 GPa | 2.104 GPa | 0.5 | WORSE |
| ionics-rocksalt-oos | c44 | 4 | 16 | 2 | 14 | 21.11% | 21.11% | 1.372 GPa | 1.372 GPa | 0.5 | NO-CHANGE |
| perovskite-oos | a0 | 4 | 16 | 16 | 0 | 1.75% | 0.74% | 0.0852 Angstrom | 0.03607 Angstrom | 3.052e-05 | WIN |
| perovskite-oos | b0 | 4 | 16 | 3 | 13 | 9.28% | 15.08% | 4.475 GPa | 4.668 GPa | 0.25 | WORSE |
| perovskite-oos | c11 | 4 | 16 | 2 | 14 | 20.33% | 20.33% | 15.73 GPa | 15.73 GPa | 0.5 | NO-CHANGE |
| perovskite-oos | c12 | 3 | 12 | 0 | 12 | 17.53% | 17.53% | 5.032 GPa | 5.032 GPa | n/a | NO-CHANGE |
| perovskite-oos | c44 | 4 | 16 | 2 | 14 | 13.29% | 13.29% | 1.296 GPa | 1.296 GPa | 1 | NO-CHANGE |

## Registered criteria — group verdicts

- **ionics-rocksalt-oos: FAIL** — 1 WIN of 5 evaluable properties (criterion: corrected beats raw (median |rel err|) on >= 2/3 of evaluable properties with sign-test p < 0.1).
- **perovskite-oos: FAIL** — 1 WIN of 5 evaluable properties (criterion: corrected beats raw (median |rel err|) on >= 2/3 of evaluable properties with sign-test p < 0.1).

## Registered KILL evaluation

- Registered condition: if the frozen rule fails both groups, the correction layer's scope claim narrows to "same-class lattice constants only" in all public material until new evidence.
- Outcome: **TRIGGERED** — KILL condition triggered: the frozen rule failed all evaluated groups.

## Within-group risk-coverage (gate verdicts)

| group | n | certified | flagged | refused | issued coverage |
|---|---|---|---|---|---|
| ionics-rocksalt-oos | 4 | 0 | 1 | 3 | 25.00% |
| perovskite-oos | 4 | 2 | 1 | 1 | 75.00% |

## Abstention reasons (per group x property)

| group | prop | insufficient_calibration | direction | magnitude_cap |
|---|---|---|---|---|
| ionics-rocksalt-oos | a0 | 0 | 0 | 0 |
| ionics-rocksalt-oos | b0 | 0 | 3 | 11 |
| ionics-rocksalt-oos | c11 | 0 | 6 | 6 |
| ionics-rocksalt-oos | c12 | 0 | 12 | 2 |
| ionics-rocksalt-oos | c44 | 0 | 7 | 7 |
| perovskite-oos | a0 | 0 | 0 | 0 |
| perovskite-oos | b0 | 0 | 9 | 4 |
| perovskite-oos | c11 | 0 | 12 | 2 |
| perovskite-oos | c12 | 0 | 8 | 4 |
| perovskite-oos | c44 | 0 | 10 | 4 |

## Registered exclusions

Excluded from criteria and ALL tables above: pv-cspbbr3 x c12

## Honesty boundary

n per group is small (see per-material table); this is a methodology
demonstration under the registered rule, not a general efficacy claim.
