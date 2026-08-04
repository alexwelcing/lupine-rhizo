# Round-4 theorem-capped correction trial — acceptance audit draft

Date: 2026-08-03
Status: draft for review; no protocol amendment and no re-execution
Run audited: `correction-round4-20260719`
Candidate lock: `sha256:b7562637c860b15b92f64659f0b063bc6d2b6c0c12899e21f370359cccb914f1`

## Executive result

The requested experiment already executed on 2026-07-19 and is committed on `origin/main`. Re-executing it would conflict with the 2026-07-19 amendment, which says the raw artifacts are hash-locked and “authorizes no re-measurement.” This audit therefore verifies the committed evidence rather than generating a second, post-hoc Round-4 dataset.

All 32 registered model×material cells are present. Each cell has an energy-volume and an elastic-constants artifact, giving 64 hash-addressed row artifacts. All 64 recorded SHA-256 digests re-verified against the committed files on 2026-08-03. The four registered measurement executions are recorded as successful and bind to the locked images.

## Frozen protocol integrity

- Candidate lock file: `data/candidates/round4_targets.lock.json`.
- Recomputed lock SHA-256: `b7562637c860b15b92f64659f0b063bc6d2b6c0c12899e21f370359cccb914f1` — matches the preregistration.
- Model set: CHGNet, MACE-MP small, MACE-MP medium, MACE-MPA-0 medium.
- UMA remains `excluded_unavailable` and outside the registered model set.
- The committed amendment records a real preregistration defect: the analysis implementation was not frozen before evaluation data existed. The defect is not erased by this audit.
- The amendment also records the repaired execution binding, removes B0 from the confirmatory denominator, and marks perovskite C11/C12/C44 exploratory-only. This audit does not alter those dispositions.

## Registered endpoint score

| Group | Confirmatory properties | Wins | Registered verdict |
|---|---|---:|---|
| ionics-rocksalt | a0, C11, C12, C44 | 0/4 | FAIL |
| perovskites | a0 | 0/1 | FAIL |

The preregistered `>= 2/3` property-win criterion failed in both groups. The committed conclusion therefore stands: the public correction scope remains “same-class lattice constants only,” and further cap tuning is frozen absent a new proven theorem.

## No-harm / licensed-failure score

The frozen preregistration defines the risk endpoint as applied-and-worsened cells and separately requires zero worsened cells among cap-licensed cells that are oracle-in-hull.

Committed observed counts:

- ionics-rocksalt a0: 7 applied, 5 improved, 2 worsened;
- ionics-rocksalt C11: 1 applied, 0 improved, 1 worsened;
- perovskite a0: 4 applied, 4 improved, 0 worsened;
- descriptive perovskite B0: 6 applied, 5 improved, 1 worsened;
- exploratory perovskite C11/C12/C44: respectively 2/3/5 applied, with 2/2/2 worsened.

The broad empirical no-harm proposition is therefore false: some licensed corrections worsened held-out errors. The narrower theorem-consistency endpoint passed exactly: **0 cap-licensed, oracle-in-hull worsened cells**. This is the conditional guarantee the Lean theorem supports; it is not an unconditional runtime guarantee.

## Conformal coverage

**Not registered / not scorable.** The frozen Round-4 preregistration contains no conformal predictor, interval construction, nominal coverage level, calibration rule, or conformal coverage endpoint. Adding one after outcomes exist would violate the instruction to execute exactly under the frozen protocol. The `thermodynamic_condition_coverage` objects emitted by the generic runner are not conformal intervals and must not be relabeled as conformal evidence.

Accordingly, this audit reports conformal coverage as `not_registered`, not as pass, fail, zero, or missing-at-random. A conformal endpoint requires a new prospective preregistration and a separately locked evaluation set; it cannot be retrofitted onto Round 4.

## Execution receipts

- CHGNet: `mlip-cell-chgnet-round4-8bbp8` — success; locked image match.
- MACE-MP small: `mlip-cell-mace-round4-mp-small-k94mk` — success; locked image match.
- MACE-MP medium: `mlip-cell-mace-round4-mp-medium-mmcjq` — success; locked image match.
- MACE-MPA-0 medium: `mlip-cell-mace-round4-mpa-0-medium-6979j` — success; locked image match.

Canonical receipt: `data/candidates/round4/execution-receipt.json`.
Canonical machine-readable results: `data/candidates/round4/report.json`.
Canonical report: `data/candidates/round4/ROUND4_REPORT.md`.
Cost draft: `docs/analysis/round4-cloud-run-cost-ledger.md`.

## Publication language

Round 4 is a negative result under its registered confirmatory endpoints. The theorem-capped correction did not achieve the required property-win fraction in either material class. The theorem-consistency check nevertheless found no contradiction: every cap-licensed correction whose held-out ratio was later observed inside the calibration hull avoided worsening, exactly as the conditional theorem requires. No conformal coverage claim is available from this protocol.
