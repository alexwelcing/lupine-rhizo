# Three error-geometry objects and their evidence boundaries

A low participation ratio is a description of a specified sample in specified
coordinates. It does not by itself establish a model manifold, a physical cause,
a shared configuration-space core, or a useful correction.

## The three objects

| Object | Space and definition | What establishes it |
|---|---|---|
| A. Model manifold | Predictions `y(theta)` as parameters of a specified model vary | A parameterized prediction map, its metric and the sampled parameter domain |
| B. Error-cloud participation ratio | Eigenvalues of a specified centered error covariance; `PR = (sum lambda)^2 / sum lambda^2` | Pinned observations, row/column identities, normalization, selection and dependence rules |
| C. Configuration-space error core | A proposed shared low-dimensional core in atomic configuration space | Spatial error data and the explicit assumptions of the conditional tube theorem |

[Transtrum, Machta and Sethna](https://arxiv.org/abs/1010.1449) define a model
manifold through parameter-dependent predictions. An ensemble of different
potential families or a cross-material error table is not automatically a sample
from one such map. B can describe concentration in that table; identifying B with
A needs an additional sampling and representation argument. The A/B-to-C bridge
also remains conditional; see [keystone reconciliation](keystone-reconciliation.md).

For nonzero positive-semidefinite covariance, PR lies between 1 and its rank.
It equals the rank only when the nonzero eigenvalues are equal. Small PR is
variance concentration, not a proof of low topological dimension. A zero covariance
has no variance spectrum to interpret; the implementation returns 0 as a convention.

## Maintained calculation inspected on 4 November 2026

This is source inspection at Rhizo revision
`8965bc990803a0c87485e6682378a62dbd320c4d`, not a new execution or a reconstruction
of every historical result.

- [`build_error_vectors`](../../atlas-distill/src/manifold.rs) groups records by
  material and potential label, takes `predicted - reference`, selects the first
  matching record for each requested property, and excludes incomplete/nonfinite
  vectors. It does not itself resolve duplicate model artifacts, repeated
  references, incompatible units or provenance conflicts.
- `analyze_manifold` then groups by potential label. Its rows are **materials** and
  columns are properties, with at least three complete rows. This differs from
  an analysis of many potentials at a fixed material. Do not interchange those
  sampling units or assume a family label identifies one model artifact.
- [`stats::pca`](../../atlas-distill/src/stats.rs) centers columns and uses squared
  singular values divided by `n - 1`. This path does not standardize columns or
  apply a dimensionless physical scale. A common scalar scale leaves PR unchanged;
  separate column scales generally do not. Mixed property families require an
  explicit coordinate/weight contract.
- The centered sample rank is at most `min(p, n - 1)`. Comparisons must expose
  both sample size and complete-case selection, not only PR divided by `p`.
- The `is_hyper_ribbon` flag combines fractional PR and log-spectrum fit with
  monotonicity of an already descending spectrum. Strictly descending eigenvalues
  automatically have negative rank-trend statistic; that condition is not
  independent evidence for a physical mechanism.
- [`NullModelAgent`](../../atlas-distill/src/agents/null_model_agent.rs) matches
  the number of rows and columns, but draws independent **uniform** values at one
  common scale (despite a comment saying normal). It does not preserve the
  observed column variances, model/reference dependence or physical constraints.
  Passing this null would not exclude those explanations.

These are properties of this code path. No affected historical row count or new
scientific significance level was established by the inspection. Other archived
generators must be inspected separately before assigning their results this contract.

## Existing controls and outstanding interpretation

The [MEAM matched-sample comparison](../conjectures/meam-intrinsic-2d.md) already
retired the strong intrinsic-dimensionality claim. Do not repeat that bootstrap
just to produce another number. The [Born-screening review](../born-screening-re-audit.md)
keeps the old MLIP transfer count frozen. The
[A6 pilot](../glim-m3-upgrade/runs/a6-alignment-results.md) remains provisional;
its recorded signal does not establish a universal configuration-space core.
These are retained reports, not newly checked raw-data reproductions.

Adding a derived coordinate also needs care: cubic `B = (C11 + 2*C12)/3`,
when calculated from the same constants, adds no independent measurement.
An independently fitted equation-of-state bulk modulus is a distinct observation
whose protocol and relation to the elastic constants must be recorded.
Adding lattice constant or cohesive energy can broaden observables, but a low
joint PR alone does not rule out scale, sample-size or selection effects.

## What the Lean statement proves

[`HyperRibbonEmpirical.lean`](../../lean-spec/OpenDistillationFactory/Materials/Theory/HyperRibbonEmpirical.lean)
defines the Float constant `0.3981388474988096` and checks that it is below
`0.5` using `native_decide`. The statement has no dataset input, source digest,
PCA calculation, sampling model or physical universality quantifier. It checks
that numerical assertion; it does not certify the observations or their interpretation.
See the [corrected audit boundary](../formal-audit.md).

## Next discriminating step

Recover the pinned input and generator for the reported joint `Cij + a0` result
before interpreting its normalization. Freeze the observational unit, complete
common row set, independent model/reference identities and dimensionless scale
contract before any comparison. Compare the same retained observations under
that declared contract; do not manufacture extra independent evidence from
derived observables. An explanation by scale, selection or the appropriate
matched null retires the stronger extension and leaves only a descriptive result.

No new inference, simulation, source retry or corpus admission follows from this
plan. Demonstrated value still requires a separate task-specific decision or
held-out correction result; low PR alone supplies neither.
