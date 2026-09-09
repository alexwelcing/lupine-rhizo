# Geometry recompute — 42-group classical error geometry

Committed generator for the classical covariance geometry audited in the TMS
2027 proceedings draft (lupine-rhizo PR #133). That draft records two
provenance gaps: "no committed generator reproduces the 42-group file from
the CSV" and "the stored monotonicity statistics do not match the current
implementation for strictly descending spectra". This directory closes the
first gap and pins down the second.

Registered open item: `docs/plans/2026-09-09-tms-manuscript-sprint.md`
("Geometry recompute" row). Not a dependency of the proceedings submission.

## Files

- `recompute_geometry.py` — deterministic generator (seed 20260909).
- `results/geometry_recompute_results.json` — full results: SHA-256 of every
  input, per-group rows for both computed gauges, per-group diff against the
  committed file, matched-null distributions (2,000 reps per group per
  gauge), strata summaries, claim verdict.
- `figures/geometry_recompute_pr_vs_n.{pdf,png}` — PR vs n with the null
  p05 band, both lineage resolutions.

Run: `python3 recompute_geometry.py`. Verify freshness:
`python3 recompute_geometry.py --check` (byte-compares a regeneration;
exit 0 iff the committed results JSON is current). Runtime ~2 min.

## Inputs (read-only; the generator never writes to them)

| input | rows | SHA-256 |
|---|---|---|
| `atlas-distill/benchmarks/kim_elastic_results_all.csv` | 559 | `927be85f…3d77da6` |
| `atlas-distill/benchmarks/nist_populated_all.csv` | 1,677 | `527f72ef…28c1156` |
| `replication/error-geometry/data/classical/manifold_revalidation_42potentials.json` | 42 groups | `ee280efa…f7c7e649` |

The two CSVs are byte-identical to the copies in the `lupine` corpus repo.
The committed 42-group JSON exists in both repos; the copies are
byte-different but semantically identical (0 field diffs across all 42
groups). The `lupine` copy (`7dd5d8ca…dd823b2`) is the hash locked in
`paper/tms2027-proceedings/results.json`; either copy reproduces identically.

## What the committed file is (reconstruction result)

Grouping: potential families (`short_label`) in the NIST-populated corpus
with complete C11/C12/C44 over ≥ 3 materials → exactly the committed 42
groups (21 with n = 3, whose centered spectra are rank-limited to two
eigenvalues).

- **PRs reproduce exactly: 42/42 to < 1e-9.** Median PR 1.0863 (manuscript:
  1.09); n = 3 median 1.0256 (manuscript: 1.03); n ≥ 4 median 1.1595
  (manuscript: 1.16).
- **Eigenvalue normalization differs by a documented factor.** The committed
  eigenvalues equal S²/n (population variance); the current implementation
  (`atlas-distill/src/stats.rs::pca`) uses S²/(n−1). Ratio (n−1)/n per
  group; eigenvalues match to 5e-12 once the normalization is aligned. All
  PR-derived quantities are scale-invariant and unaffected.
- **Duplicate rows resolved first-wins.** The NIST-populated CSV has 231
  duplicate (potential, material, property) keys (several KIM model
  implementations report the same family on the same element), 103 with
  conflicting values. First occurrence in file order reproduces all 42
  committed PRs; last-write-wins or averaging each give only 34/42. Affected
  groups and keys are listed per group in the results JSON.
- **Stored CI bounds are not reproducible.** They come from an unseeded
  bootstrap in the original one-off run. Seeded 2,000-rep CIs are reported
  alongside in every group row.

## The monotonicity discrepancy (second gap)

The committed `decay_monotonicity` field is the **Pearson correlation
between eigenvalue magnitude and PC index**, not the Mann-Kendall tau that
the current Rust implementation (`stats::mann_kendall_tau`) computes. For a
strictly descending spectrum MK tau is identically −1, so the current
implementation reports −1 for all 42 groups, while the stored values range
−1.0 to −0.866. The Pearson statistic matches the stored values exactly
(42/42). The 21 k = 3 groups are where the two definitions disagree
(stored ≈ −0.87…−1.0 vs MK −1); for the 21 two-eigenvalue groups both give
−1 by construction — which is exactly the "passes by construction" caveat
the manuscript raises for rank-limited spectra.

## Gauges

1. **absolute** (GPa residuals): the gauge of the committed file; results
   above.
2. **relative** (residual / reference): computed; median PR 1.1745 over the
   42 groups; per-group values in the results JSON.
3. **standardized** (residual / reference uncertainty): **ABSTAIN**. No
   reviewed per-reference uncertainty exists in the corpus: the CSV carries
   no uncertainty column and the Simmons & Wang references propagated
   through NIST IPR are point values. No denominator is invented.

## Matched nulls (the frozen null)

Per group, column-wise permutation of the residual matrix across materials
within the group's lineage, uniform over permutations whose implied tensors
remain Born-admissible (cubic criteria; drawn by backtracking search —
naive rejection is structurally infeasible for the Girifalco-Weizer Morse
families whose residual scale approaches the reference scale). This
preserves n, d, missingness (none — complete cases), per-column marginal
scales exactly, Born admissibility, and lineage, while destroying the
cross-property correlation under test. 2,000 reps per group per gauge at
both lineage resolutions:

- **short_label lineage (42 groups)**: 15/42 groups fall below the null 5th
  percentile (absolute gauge). Per-stratum fractions: n=3 → 3/21 (14%),
  n=4 → 1/3, n=5 → 3/5, n=6 → 1/3, n=7 → 1/3, n=8 → 1/2, n=9 → 3/3,
  n=12 → 2/2. Every stratum beats the 5% false-positive level.
- **model_id lineage (18 KIM IDs with ≥ 3 elements)**: fails at n = 6 —
  the EMT_Asap Jacobsen-Stoltze-Norskov universal potential has PR 1.509
  against a null p05 of 1.175.

## Verdict

**Hyper-ribbon claim: NOT CLEARED.** Clearing requires every stratum of n
to beat the 5% false-positive level against the frozen null at both lineage
resolutions. The short_label resolution clears all strata; the model_id
resolution does not (n = 6 stratum). The proceedings draft's stated
position — no strict hyper-ribbon claim until the recompute clears the
frozen null across strata — therefore stands, now with a committed
generator and a reproducible null behind it.

## Scope notes

- `paper/tms2027-proceedings/results.json` is untouched (its quoted block is
  revised only if the manuscript is revised post-submission).
- The committed 42-group JSON is a read-only diff target; nothing in this
  directory overwrites it.
