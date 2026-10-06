# Shared, aligned residuals carry most error on the archived panels

Date: 2026-10-06. **Archived descriptive analysis; independently checked arithmetic.**

## Question and result

Do atoms whose common residual energy exceeds model contrast, with all three residual pairs pointing in positively aligned directions, carry a majority of ensemble squared force error on an average equally weighted archived configuration?

The fixed descriptive criterion passes on both reused panels: **71.00% on MatPES and 76.52% on OMat24**, exceeding the predeclared 50% threshold. This documents a substantial common-residual component that model spread does not measure directly: substantial error against the saved reference occurs where the common residual outweighs model spread. It does not identify the cause of that common residual or establish a calibrated alarm.

| Panel | Configurations / original groups | Atoms satisfying mask / all atoms | Primary: equal-group mean error fraction | Secondary: pooled error fraction |
| --- | --- | --- | --- | --- |
| MatPES | 400 / 50 | 2,061 / 3,324 | 70.9982% | 84.9321% |
| OMat24 | 400 / 50 | 2,488 / 3,912 | 76.5205% | 86.8382% |

The primary averages eight configuration fractions within each original group, then gives each of the 50 groups equal weight. Because group sizes are equal, it also equals the mean of the 400 configuration fractions. The pooled secondary instead weights configurations by their total squared error. Neither is an error reduction or a statistical significance test.

## Fixed calculation

The [previous source-audit report](https://github.com/alexwelcing/lupine-rhizo/blob/29bf23d9ea1bb4b1a8e84c2c2dc301519ac9d505/docs/research-progress/2026-10-06-roster-readiness.md) specified this test before this visit. The local protocol was frozen at **19:48:50 UTC**, before the current calculation. This is not a claim of independent preregistration or outcome blindness to the repeatedly inspected archives.

For each atom, retain the three saved predictor vectors and reference vector. Define residuals `e_m = F_m - F*`, their mean `c`, common energy `y = ||c||²`, and contrast `v = mean(||e_m-c||²)`. The squared quantities use the archive's squared eV/angstrom force units.

Verify two algebraic identities per atom:

- `mean(||e_m||²) = y + v`.
- `mean(pairwise e_a dot e_b) = y - v/2`.

Use exactly one mask: **`y > v` and every one of the three pairwise residual dot products is strictly positive**. For each configuration, divide masked `sum(y)` by unchanged total `sum(y)`. The primary criterion requires both panel means to be strictly greater than one half; equality fails. A zero denominator or unresolved numerical ambiguity affecting the decision withholds the verdict. No case may be removed or replaced.

The `y > v` condition already implies a positive *average* pairwise dot product; requiring all three pairs to be positive is stricter. Neither condition is an absolute force-error threshold. The calculation uses the original grouping labels without claiming that every group is a physical trajectory.

## Verification

An independent implementation parsed the saved decimal force values as exact rational numbers, reconstructed every residual and mask from raw inputs, and verified both algebraic identities for all **7,236 atoms**. It preserved all **800 configurations and 100 original groups**, compared all 7,236 masks exactly, and passed **292,766 numeric comparisons** against the separately calculated binary64 result, including configuration and group fractions, pooled totals and threshold counts. No mask or decision discrepancy and no zero-total-error configuration was found. Both exact panel means exceed one half.

The primary result was preserved in its original pending-verification state; a separate verification and PI adjudication record establish final acceptance. Source hashes matched the recovered archives. Exact arithmetic checks the saved values and implementation; it does not validate the physical references or historical model identities.

## Interpretation and limits

This result describes aligned residuals relative to the supplied references. Model spread is reference independent, while common error and residual alignment depend on those references. Shared model limitations and reference conventions or data quality remain competing explanations. The result does not prove shared training bias, identify a physical failure mechanism, show every model has large error on each masked atom, or prove that disagreement is uninformative.

These are the same historical, correlated configurations used in earlier analyses. Historical names `chgnet`, `m3gnet` and `mace-mp-small` identify archived records, not verified exact loaded checkpoints. Training independence and full reference provenance remain incomplete. No new inference, training, candidate MPtrj outcome inspection, calibrated uncertainty model, holdout validation or methodological novelty is claimed. Historical A6 remains **INCONCLUSIVE** and the proposed independent MPtrj validation stays stopped before execution.

## Next discriminating control — planned, not started

Test one specific competing explanation: whether a uniform force offset across the atoms of each configuration could account for most common-error energy. With `b = mean_atoms(c_i)`, verify the exact full-configuration decomposition:

`sum_i ||c_i||² = N||b||² + sum_i ||c_i-b||²`.

Freeze the test before calculating it. Measure `T = N||b||² / sum_i ||c_i||²` with the same equal-configuration/equal-group primary weighting and pooled secondary. Record the separate predictor and reference mean force vectors. If both primary panel means are strictly below one half, uniform offsets do not account for a majority of common-error energy on an average equally weighted configuration in either panel. Equality or a failed condition leaves that claim unestablished; zero denominators or unresolved numerical ambiguity withhold the verdict. Do not apply the identity only to masked atoms, change the mask, or present centered vectors as corrected predictions.

This control cannot rule out atom-dependent reference mismatch or establish causation. Complete it in one bounded visit, then close this archived diagnostic branch regardless of outcome. Further empirical advancement should add new reference or predictor evidence under a separately justified design, rather than another decomposition of these same cases.

## Evidence anchors

Raw predictions, detailed results and verification records stay private. Published hashes identify local artifacts; they do not provide public reproduction inputs.

- Frozen protocol: `840f1f1010c8a0ab26abf83d4fa31f72c8717354713ab83a0e5b2a0275d0c632`.
- Primary result: `2fd6c3a97d3685800cd6cde2b27a1fcfdc5628d66f7e344029068d0ac0a3abdf`.

- Independent exact-arithmetic verification: `05e63759dd4da805522b08d56b76d01878b52d6f496f3b6a61dba5345e397934`.
