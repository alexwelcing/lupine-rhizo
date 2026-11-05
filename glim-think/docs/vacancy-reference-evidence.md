# Vacancy-label error components

A centered vacancy-energy score can be zero even when every formation label
has a uniform error. The synthetic shared fixture adds 0.1 eV to three labels:
centered MSE is exactly 0, while full MSE is exactly 1/100 eV².

## Exact specification

For a nonempty set of sites partitioned into nonempty species groups, let
S replace each value by its species mean and J by the overall site mean.
With equal site weights, H = I - S. For any label-error vector d,

    ||d||²/n = ||Hd||²/n + mean(d)² + ||Sd - Jd||²/n.

S and J are symmetric idempotents with SJ = JS = J. Therefore H, J and S-J
have mutually orthogonal ranges, proving the decomposition. The components
measure within-species variation, overall bias and species-mean imbalance.
Unequal species counts retain site weights; this is not equal weighting of
species or structures. Printed values are never rounded or projected.

For the explicitly chosen self-consistent reference construction,

    F(x,E0) = (I-S+J)x - ((n-1)/n) E0 1,

where x contains every single-vacancy total energy for an n-atom pristine
cell, I-S+J is a rank n-k+1 projector. Its kernel consists of species-constant
vectors with zero overall mean. Consistent elemental energy-zero shifts
cancel; they are legitimate gauge freedom, not physical model errors.
For known E0, cᵀx is identifiable precisely when the species averages of c
coincide. With unknown E0 and n>1, each species sum of c must be zero.
This is standard linear algebra, not a novelty or physical-validity claim.

Centering labels also discards the overall formation-energy level. A
within-species score cannot certify absolute formation-energy accuracy or
vacancy concentrations. A concentration decision additionally requires a
qualified thermodynamic model and reservoir convention.

## Rust checker

From the repository root:

    cargo run --manifest-path distill/Cargo.toml --bin distill -- \
      vacancy-reference --input distill/tests/fixtures/vacancy_uniform_bias.input.json

The fixture intentionally exits nonzero **after** emitting its descriptive JSON
report because the selected centered score is incompatible with the requested
formation-energy task. With a full score or a within-species task, successful
arithmetic remains descriptive; it never grants physical acceptance.

The command accepts at most 512 KiB, 4096 unique sites and 128 species.
Values are bounded decimal strings (at most 64 characters; no exponent,
NaN or infinity), evaluated with exact BigRational arithmetic. Numeric JSON
values are rejected to avoid silently importing binary floating-point values.
MSEs and signed mean bias are reduced numerator/denominator strings; irrational
square roots are not mislabeled as exact RMSEs.

The result fingerprints the exact input bytes and, separately, the sorted
(site ID, species, reference lexeme) tuples. It retains declared source,
parent, complete cohort and prediction identities. Partial subsets remain
marked as subsets and never redefine chemical potentials. A complete cohort
declaration checks counts, not independently verified source membership.

No network, provider, simulator, database mutation or output-file creation
occurs in this command. Stdout may contain private identifiers; publish only
material authorized for its destination. Tests use synthetic inputs only.

## Private report inspection

The private RUNS page includes **Inspect a vacancy error report**, available even
when no run snapshots have been saved. Select one checker result JSON file of
at most 512 KiB. The page validates its declared arithmetic in memory and shows
full MSE, within-species MSE, overall bias squared, species-mean imbalance and
signed mean error. Exact short decimals are displayed when possible; other
values remain fractions, so a tiny nonzero component cannot appear as zero.

The inspection-task selector keeps the original report's intended task visible
and recomputes the score warning for the chosen decision. Synthetic/reported
input, incomplete cohorts, unknown references and unverified source membership
remain explicit. A full score never grants physical or concentration acceptance.

The file is read locally and is not uploaded, persisted, attached to a run or
published. Clearing it or choosing another file invalidates any pending read.
The inspector neither executes the original checker input nor verifies source
authenticity. The separate server preview still requires genuine saved-run and
model-arm bindings.

## Existing RUNS preview

The existing private verification-preview request accepts an optional sibling
`vacancyEvidence` beside `runId` and `contract`. It contains:

- `schemaVersion: 1` and the exact `comparisonContractSha256`;
- `task`: within_species_variation, formation_energy or vacancy_concentration;
- one `{ modelId, result }` entry per existing comparison arm.

In the existing **Preview a verification task** control, prepare and review a
comparison from a saved proposal, then open **Optional vacancy evidence attachment**
and paste the attachment JSON. A blank field sends no attachment. The complete
request is bounded by the existing 192 KiB route limit; the contract retains its
96 KiB client limit. Each attachment must cover the comparison's actual model
arms and bind its canonical contract fingerprint. Do not use a single standalone
report or invent another model to fill this interface.

The client checks the supplied component arithmetic and model/contract binding
before sending. The server independently repeats the attachment checks against
the saved run and source contract. The client accepts only the corresponding
contract and attachment fingerprints with unexecuted, unpublished and unverified
scientific states. Editing either input, choosing another proposal or preparing
a replacement draft invalidates the previous preview; replacing the proposal or
draft clears the attachment. Pasting does not send anything. Only the explicit
preview click makes the existing same-origin request.

The typed observable must respectively be `within_species_vacancy_variation`,
`vacancy_formation_energy` or `vacancy_concentration`; input label units remain
`eV_per_vacancy`. A concentration request assesses applicability of energy
evidence; it does not compute a concentration or assert its units.

The preview binds model names, reference rows, source/cohort/parent identities,
task, source finding and contract hash. It independently checks the supplied
component arithmetic, group weighting and selected score with bounded BigInt
fractions. It recomputes applicability instead of trusting a producer's status.
The attachment hash includes its contract binding and all supplied results.

This verifies consistency of the supplied report, **not execution of its input
artifact**, model identity, training independence or source authenticity.
Every attachment keeps scientific support unasserted. Centered-only absolute
claims are blockers. Existing Access, same-origin, saved-discovery and
distinct-model requirements remain in effect; the preview does not write,
schedule, import or publish.

The checker can describe one model or a source-only synthetic example without
a provider run. Attaching to RUNS still requires a genuine saved run and its
actual distinct model arms. Do not invent a run or turn species into models
to satisfy that separate interface.

## Calibration and evaluation provenance

Optional `context.reference_protocol` records parent species counts, an evaluation
cohort digest, separate reference and prediction calibration cohorts, and a
declared shared or unknown elemental energy-zero alignment. Missing protocol
metadata remains unknown; existing v1 reports remain readable. Parent and
calibration cohort digests may be null when unavailable, independently of known
counts or weights. Their absence remains visible and cannot certify shared
structure identity. Do not manufacture a digest to enable an arithmetic check.
Each calibration
records its digest, site count, per-species site counts and exact rational
species weights. The shared synthetic protocol fixture documents the JSON shape.

The checker validates unique species, count totals and parent membership when
known, normalized nonnegative weights, and calibration coverage of evaluated
species for a self-consistent reference. Exact weight parsing is bounded to
64 digits per numerator/denominator and 4096 digits per intermediate. Hashes
bind declarations; they do not authenticate structures or prove disjointness.
Separate prediction calibration is allowed; a multi-model attachment must
share the same declared reference calibration and evaluated reference cohort.

For the printed construction
`F_s = E_test,s - mean_cal,s(E_defect) + sum_t w_t mean_cal,t(E_defect)
       - (N-1)/N E_parent`,
adding an arbitrary elemental energy zero `a_s` to every atom of species `s`
changes every formation label by
`sum_s (n_s/N - w_s) a_s`.
Thus invariance to every elemental shift is equivalent to
`w_s = n_s/N` for all parent species. This condition concerns the weights in
the calibration mean, not the number of rows displayed in an evaluation table.
The checker reports mismatches without projecting labels, changing weights
or recomputing chemical potentials. Matching declared weights is an algebraic
check, not physical reservoir validation.

A common elemental shift applied to both compared methods cancels in their
residuals. Independent model/reference energy-zero choices require the stated
alignment convention. An external reservoir needs its own qualification;
this self-consistent weight test does not certify it. This calibration
argument is separate from the existing Lean finite loss proof.

The inspector reports the within-species contrast dimension `rows - groups`
and identifies singleton species. If all groups are singletons, within-species
MSE is identically zero and provides no test of within-species variation.
This is a deterministic dimension count, not a count of statistically
independent measurements.

## Lean specification

`OpenDistillationFactory.Materials.Theory.VacancyReference` defines the species
means, overall mean, full MSE, within-species MSE and species-mean imbalance
directly on a finite nonempty family of nonempty site groups. Its
`loss_decomposition` statement covers unequal species sizes with equal site
weights. The weighted-mean premises are derived from those definitions.

`centered_does_not_bound_full` states the obstruction for every real multiplier:
a nonzero constant label error has zero within-species MSE and positive full
MSE. It is a statement about the information discarded by a score, not a
physical claim about an interatomic potential.

The existing formal CI builds this module explicitly before the full package,
checks the no-placeholder gate and reports the two main theorems' axiom
dependencies. The job has a 20-minute ceiling. The original PR #158 receipts
used Lean 4.29.0; the current package uses Lean 4.35.0 with dependency pins in
lean-spec/lean-toolchain and lean-spec/lake-manifest.json. The combined branch
requires its own build receipt. The maintained generator supplies the source
declaration inventory; declaration counts alone do not prove compilation.

This real-arithmetic specification does not certify Rust/TypeScript execution,
input parsing, source premises or physical accuracy. The projector-rank and
raw-energy identifiability statements above are still mathematical arguments,
separate from this finite loss formalization.

## Verification and remaining work

Rust and TypeScript consume the same synthetic expected-result fixture.
Tests cover the uniform-bias counterexample, unequal counts, exact small
differences, ordering, malformed/oversized inputs, duplicate sites/fields,
reference/task/model binding, forged arithmetic and a read-only D1 preview.
CLI tests check JSON output and exit status.

The runtime checks are executable contract tests, separate from the Lean
specification and from a materials benchmark.
The checker and preview do not recover missing raw defect geometries, magnetic
states, convergence evidence, reservoir alignment or independent test exposure.
The client-to-route test imports a synthetic receipt-validated run into in-memory
SQLite, sends the actual client request through the actual preview route, checks
the centered-score blocker and attachment fingerprint, and prohibits preview
writes. Separate Chrome controls use the actual preview component with a stated
response double to check attachment transport, invalidation and rejection.
These are application integration checks, not acceptance of a genuine operator
run, authenticated production behavior or publication of a research result.

For ordering among a fixed list of structures, use the separate
[candidate-order report](candidate-order-evidence.md). It preserves signed gaps
and endpoint ties without requiring interstitials to be labeled as vacancies.
