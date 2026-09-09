# TMS 2027 classical error-geometry recomputation

## Scope and reconstruction

The committed 42-group JSON defines the included author/year short-label lineages and expected material counts. The script rebuilds each C11/C12/C44 signed-residual vector from `atlas-distill/benchmarks/nist_populated_all.csv`, using that file's per-row reference values. It collapses duplicate short-label/material/property rows by first CSV occurrence, matching the current Rust `build_error_vectors` behavior. This exactly reproduces every committed absolute-gauge PR (maximum absolute difference 8.882e-16). The 559 model-element tensors are therefore not treated as 559 independent lineages.

The separate `replication/error-geometry/references.py` table is hash-recorded for comparison but is not substituted: its values do not reproduce the committed 42-group object. The per-row CSV references remain the source-bound convention for this recomputation.

## Gauges

1. `absolute_gpa`: predicted minus reference Cij, in GPa.
2. `relative_to_reference`: absolute residual divided componentwise by the same row's reference Cij.
3. `standardized_global_sd`: absolute residual divided by the componentwise sample SD across all 559 retained model-element tensors. The frozen scales are C11=39093.689, C12=31294.1063, and C44=2605.48162 GPa; these large values reflect retained extreme rows and are not robust scales.

For every gauge, the estimand is the participation ratio of the centered 3x3 covariance matrix.

## Matched null

Within each short-label lineage, property columns are independently permuted relative to C11. This preserves lineage membership, n, d=3, the exact missingness mask (zero missing cells here), and each marginal distribution/scale while breaking cross-property alignment. For n=3, all 3!^2=36 relative permutations are enumerated; larger groups use 10,000 draws with frozen seed 20260909 and lineage/gauge-specific SHA-256-derived seeds. A stratum clears at one-sided lower-tail p <= 0.05. The strict claim requires every gauge-by-n stratum to clear.

## Results by sample-size stratum

| Gauge | n | Groups | Observed median PR | Null median PR | Lower-tail p | Clears 0.05? |
|---|---:|---:|---:|---:|---:|:---:|
| absolute_gpa | 3 | 21 | 1.0256 | 1.2862 | 0.05405 | no |
| absolute_gpa | 4 | 3 | 1.0619 | 1.4123 | 0.0049 | yes |
| absolute_gpa | 5 | 5 | 1.1450 | 1.4567 | 0.0024 | yes |
| absolute_gpa | 6 | 3 | 1.1785 | 1.6838 | 0.0009999 | yes |
| absolute_gpa | 7 | 3 | 1.3381 | 1.6849 | 0.0123 | yes |
| absolute_gpa | 8 | 2 | 1.6453 | 2.1046 | 0.008499 | yes |
| absolute_gpa | 9 | 3 | 1.0883 | 2.3253 | 9.999e-05 | yes |
| absolute_gpa | 12 | 2 | 1.0890 | 1.4338 | 9.999e-05 | yes |
| relative_to_reference | 3 | 21 | 1.0338 | 1.2087 | 0.05405 | no |
| relative_to_reference | 4 | 3 | 1.5752 | 1.4457 | 0.7325 | no |
| relative_to_reference | 5 | 5 | 1.3990 | 1.6990 | 0.06419 | no |
| relative_to_reference | 6 | 3 | 1.9690 | 1.7894 | 0.7616 | no |
| relative_to_reference | 7 | 3 | 1.2077 | 2.0382 | 0.0049 | yes |
| relative_to_reference | 8 | 2 | 1.0398 | 1.4838 | 9.999e-05 | yes |
| relative_to_reference | 9 | 3 | 1.8713 | 1.8912 | 0.4368 | no |
| relative_to_reference | 12 | 2 | 1.1374 | 1.5030 | 9.999e-05 | yes |
| standardized_global_sd | 3 | 21 | 1.0050 | 1.0550 | 0.05405 | no |
| standardized_global_sd | 4 | 3 | 1.0187 | 1.0600 | 0.06709 | no |
| standardized_global_sd | 5 | 5 | 1.0811 | 1.1098 | 0.1818 | no |
| standardized_global_sd | 6 | 3 | 1.0740 | 1.0878 | 0.2212 | no |
| standardized_global_sd | 7 | 3 | 1.1152 | 1.1009 | 0.9265 | no |
| standardized_global_sd | 8 | 2 | 1.0090 | 1.0265 | 0.0002 | yes |
| standardized_global_sd | 9 | 3 | 1.0053 | 1.0261 | 9.999e-05 | yes |
| standardized_global_sd | 12 | 2 | 1.0350 | 1.0684 | 0.0017 | yes |

## Rank-limit and verdict

Exactly 21 of 42 groups have n=3. Mean-centering n=3 observations forces covariance rank <= n-1=2; all three gauges satisfy that bound for all 21 groups, and the same rank limit is present in their matched nulls. The n=3 strata do not clear the exact null (observed lower-tail p=2/37=0.05405 for each gauge).

The strict cross-stratum hyper-ribbon criterion is **not supported**. Absolute-GPa anisotropy clears most n>3 strata, but not n=3; relative and standardized gauges fail multiple strata. Report descriptive anisotropic elastic-error covariance, not a universal or strict hyper-ribbon.

Machine-readable details, all group-level spectra, null quantiles, p-values, source hashes, duplicate-cell audit, and the frozen verdict are in `tms2027-geometry-recompute.json`.
