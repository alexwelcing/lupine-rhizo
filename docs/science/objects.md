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

- [`build_error_vectors`](https://github.com/alexwelcing/lupine-rhizo/blob/8965bc990803a0c87485e6682378a62dbd320c4d/atlas-distill/src/manifold.rs) groups records by
  material and potential label, takes `predicted - reference`, selects the first
  matching record for each requested property, and excludes incomplete/nonfinite
  vectors. It does not itself resolve duplicate model artifacts, repeated
  references, incompatible units or provenance conflicts.
- `analyze_manifold` then groups by potential label. Its rows are **materials** and
  columns are properties, with at least three complete rows. This differs from
  an analysis of many potentials at a fixed material. Do not interchange those
  sampling units or assume a family label identifies one model artifact.
- [`stats::pca`](https://github.com/alexwelcing/lupine-rhizo/blob/8965bc990803a0c87485e6682378a62dbd320c4d/atlas-distill/src/stats.rs) centers columns and uses squared
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
- [`NullModelAgent`](https://github.com/alexwelcing/lupine-rhizo/blob/8965bc990803a0c87485e6682378a62dbd320c4d/atlas-distill/src/agents/null_model_agent.rs) matches
  the number of rows and columns, but draws independent **uniform** values at one
  common scale (despite a comment saying normal). It does not preserve the
  observed column variances, model/reference dependence or physical constraints.
  Passing this null would not exclude those explanations.

These are properties of this code path. No affected historical row count or new
scientific significance level was established by the inspection. Other archived
generators must be inspected separately before assigning their results this contract.

## Glim's distinct joint-property path

The separate [Glim Manifold agent](../../glim-think/src/agents/manifold.ts) uses
relative errors, not the raw-error Rust path above. Its inspected pre-fix revision
`3c3f6bffab815481e084b67978f2df8e25e85784` inserted zero whenever an observable was
missing or its reference was zero. This treated an unknown measurement as a
perfect prediction. It also merged matching labels without retaining element or
supplied model identity in the row key.

A synthetic reproduction executed the actual class with I/O doubles: three labels,
two properties, but only one complete row yielded PR 1.6, `hyper_ribbon=true` and
a claim write. This demonstrates a consumer defect, not an observed historical
scientific result or evidence that any particular published PR used those records.

The current
[observed-matrix contract](../../glim-think/src/research/observedManifoldMatrix.ts)
is shared by the tool and deterministic entry points. It keeps the input property
set fixed, retains only complete finite rows with nonzero references, rejects
conflicting repeated cells, and separates elements and supplied potential IDs.
Label fallback is disclosed; it does not verify model-artifact equivalence.
True measured zero residuals remain zero. Missing values are never filled.

Both paths expose sample selection, relative-error scaling and the centered-rank
ceiling. Insufficient complete observations, no observed variation or more than
five properties cause abstention; the existing eigenvalue routine must not report
full-spectrum PR after computing only five components. Only included records
become claim evidence. Legacy caches do not acquire the new contract by relabeling
a scalar PR; explicit recomputation is required. Regression checks exercise the
actual tool and deterministic paths with synthetic inputs and I/O doubles.

This fixes fabricated observations and row-key collisions. It does not eliminate
complete-case selection bias, establish compatible reference states, verify
independent model artifacts, certify the approximate eigensolver, or calibrate
the retained confidence heuristic. Results remain descriptive.

## Existing controls and outstanding interpretation

The [MEAM matched-sample comparison](../conjectures/meam-intrinsic-2d.md) already
retired the strong intrinsic-dimensionality claim. Do not repeat that bootstrap
just to produce another number. The [Born-screening review](../born-screening-re-audit.md)
keeps the old MLIP transfer count frozen. The
[A6 pilot](../glim-m3-upgrade/runs/a6-alignment-results.md) remains provisional;
its recorded signal does not establish a universal configuration-space core.
These are retained reports, not newly checked raw-data reproductions.

The [retained ribbon-sprint report](../ribbon-sprint/00-preregistration.md)
already records a negative joint-property control: its four-property, 42-row panel
has reported PR 2.16 versus null 2.24, p=0.30. The named raw result/input files were
not located by the bounded workspace filename search in this review. Treat this
as a reported control, not a newly reproduced result, and do not equate its cohort
with the older 45-record seed or rerun it merely because the summary was missed.

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


## The separate HTTP manifold calculation

The `POST /run` calculation was a third implementation, separate from the
Manifold agent's tool and deterministic paths. Source inspection at
`708404a6d31675de88bac5da0bc9c612fed316be` found a diagonal-only denominator:
`(tr C)^2 / sum_i C_ii^2`. For a symmetric covariance, participation ratio
instead uses `(tr C)^2 / sum_ij C_ij^2`. On the actual former route block,
three synthetic rows with errors (-0.1,-0.1,-0.1), (0,0,0), (0.1,0.1,0.1)
produced covariance 0.01 times the all-ones matrix and reported PR=3.
Its eigenvalues are (0.03,0,0), so the correct PR is 1. This is an
implementation counterexample, not a new physical observation or proof that
a particular historical result used this path.

The route now calls [runManifold.ts](../../glim-think/src/research/runManifold.ts).
It keeps the declared C11/C12/C44 basis and uses the shared observed-matrix
selection by element and model identity. Repeated conflicts exclude a row;
missing columns cannot shrink the basis; the route retains its three-complete-row
minimum. Selection counts describe rows after the explicit property, element and style
filters, not the entire ledger. Finite signed observations remain present; this
route does not add a stability filter. The PR calculation uses all covariance entries, with a
common scale to avoid overflow or underflow when squaring finite entries.
Known-spectrum, rotated-basis and scale controls test this formula.

The article prompt carries complete-case counts and descriptive limits.
The legacy power-iteration direction is only an estimate; an orthogonal seed
returns unavailable, and no largest-eigenvalue certificate is claimed.
No reference compatibility, artifact independence, held-out performance or
historical-impact count follows from these corrections.

The preceding `708404a` CI run passed all eight agent observation runtime cases
but was cancelled before the worker typecheck completed. The cancelled run is
preserved. A Linux CI diagnostic now runs that same worker test tsconfig with a
180-second timeout and bounded trace files before the normal test suite;
the complete typechecking requirement and 12-minute workflow limit remain.
