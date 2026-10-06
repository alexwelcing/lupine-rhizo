# Uniform force offsets do not explain the archived common error

Date: 2026-10-06. **Archived descriptive control; independently checked arithmetic.**

## Question and numerical result

Can a single force-vector offset shared by every atom of a configuration account for most of the ensemble's common residual energy?

The fixed control finds a very small contribution: **less than 0.000001% on MatPES and 0.01746% on OMat24**, averaging each configuration's offset fraction with equal original group weights. Both are strictly below the predeclared 50% threshold. A uniform offset therefore cannot account for a majority of the common error on an average equally weighted configuration in either archived panel. The unresolved error is overwhelmingly in the atom-dependent component of the saved residual vectors.

| Panel | Configurations / original groups | Primary: average offset share | Secondary: pooled offset share |
| --- | --- | --- | --- |
| MatPES | 400 / 50 | <0.000001% | <0.000001% |
| OMat24 | 400 / 50 | 0.01746% | 0.002405% |

The primary is an equal-group average of within-configuration fractions, not a ratio of pooled errors. The balanced eight-configurations-per-group design also makes it the unweighted mean over all 400 configurations. The pooled secondary weights each configuration by its total common residual energy. Small MatPES values are rounded as bounds; these saved decimal arrays do not establish physical accuracy at that precision.

## Fixed full-configuration projection

This control was specified in the [prior checked common-error report](https://github.com/alexwelcing/lupine-rhizo/blob/28a0fb8e464b61a88aa158621850fe2366415c5e/docs/research-progress/2026-10-06-common-error.md), then frozen locally before this calculation. It uses the same three archived force predictors and reference on all 800 configurations, with no new predictions or row exclusions.

For each atom, let `c_i = mean_m(F_mi - F*_i)` be the ensemble residual. For a configuration with `N` atoms, set `b = mean_i(c_i)`. The exact decomposition is:

`sum_i ||c_i||² = N||b||² + sum_i ||c_i-b||²`.

The first term is the projection onto the uniform vector subspace; the second is the remaining atom-dependent component. Measure `T = N||b||² / sum_i ||c_i||²` on each full configuration, average the eight fractions per original group, then average the 50 groups equally per panel. The decision requires both means to be strictly below one half. Equality or an unmet condition leaves that claim unestablished; a zero denominator or unresolved decision-changing numerical ambiguity withholds the verdict.

The saved reference and each predictor's mean force vector are retained separately. No mask is recomputed, no masked-subset identity is substituted, and no centered vector is presented as a corrected prediction or improved model performance.

## Verification

A separate implementation reconstructed the calculation from the raw saved decimal force arrays using exact rational arithmetic. It retained all **800 configurations, 7,236 atoms and 100 original groups**, proved the energy decomposition and zero sum of the internal component for every configuration, and passed **60,344 numeric comparisons** against the primary binary64 calculation. Vectors, energies, fractions, group means, distributions and pooled values agree within the documented numerical comparison tolerance; primary decisions agree exactly. No zero denominator or decision discrepancy was found.

Both exact panel means are strictly below one half. The primary artifact retains its original pending-verification state; separate verification and PI adjudication record final acceptance. Exact arithmetic validates the saved numbers and calculation, not their physical provenance.

## What this closes and what remains open

The previous result established a substantial shared residual component relative to the supplied references. This control eliminates a simple uniform-offset majority explanation for that archived component under the fixed averaging rule. It does not establish a physical failure mechanism, distinguish shared model limitations from atom-dependent reference mismatch, or certify the historical checkpoints and training independence. Net-force vectors alone cannot identify where an offset originated.

These configurations have been repeatedly inspected. There is no independent holdout, significance test, calibrated alarm, new score or generalization claim. The projection does not change any model's predictions. Historical A6 remains **INCONCLUSIVE**, and the proposed independent MPtrj validation remains stopped before execution.

**This closes the archived diagnostic branch.** No further score variants or residual decompositions of these 800 cases are planned. A new empirical advance must introduce new reference or predictor evidence with a separately justified design.

## Next evidence — planned, not executed

Investigate a bounded paired-reference microstudy on new, exactly matched geometries with two documented reference calculation protocols. The question is whether reference choice itself produces material atom-dependent force differences. This would add new reference evidence without requiring a model-accuracy or training-independence claim. Source identity, geometry pairing, units, calculation conventions and exclusion of previously inspected cases must be checked before outcome selection or calculation. The concrete source and frozen protocol remain a future step.

## Evidence anchors

Detailed vectors and raw artifacts remain private; published hashes identify them without supplying public reproduction inputs.

- Frozen protocol: `fe02dc3c083c10f846766d7acea5ecdb696c24ecf722d7e076feab2d37707409`.
- Primary result: `7d2eb3ab2c12e50a5154ae41d313e65ba957782960b56cab920cb75342c4fd4b`.

- Independent exact-arithmetic verification: `cb5a0fdfa21dc1c2a666e6df54f96089e396afd92b50e397cb4ba03d534ee591`.
