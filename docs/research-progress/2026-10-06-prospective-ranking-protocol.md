# Proposed prospective test of fixed error-ranking scores

Date: 2026-10-06. **Status: PROPOSED — NOT_STARTED.**

This is a distinct proposed study with newly pinned predictors. No final panel has been selected, roster sealed, candidate force/error values inspected for this study, or predictions executed. The size, seed and decision rules below are concrete proposed choices. Publication of this proposal is not evidence that its prerequisites passed.

## Question and claim

For one fixed three-model roster and reference domain, do full disagreement and equal pair-rank fusion each capture more of the three-model mean prediction's force error than every individual pair?

The result would be descriptive for the selected panel. It would not establish significance, generalization, calibration, force-error reduction or cheaper two-model inference. Newly pinned checkpoints have their own identities; they cannot be relabeled as the unresolved historical weights.

The proposed families are **CHGNet, M3GNet and MACE-MP-small**. Exact checkpoint versions, weight/configuration hashes, loaded-state identities and execution settings are **not yet established** for this study.

The current offline repair is deliberately scoped to the **CHGNet 0.4.2 CPU baseline forces adapter**, using the legacy graph algorithm. Strict M3GNet and MACE adapters are not implemented and must fail closed. All three required adapters must implement and independently verify the strict provenance contract before this three-model study can start. Passing the synthetic CHGNet tests does not establish actual vendor-runtime acceptance or make the proposed roster executable; legacy/default loaders are not a fallback.

## Current evidence and unresolved gates

The [pinned-source recovery](./2026-10-06-pinned-source-overlap.md) found all five earlier pilot configurations in the candidate source, plus a further known material link to the MatPES panel. Known exclusions leave **9,304 structurally eligible rows in 8,844 linked components**. These are inventory counts, **not an approved holdout or proven independent materials**.

The candidate is the genuine test shard of `nimashoghi/mptrj`, revision `f88fbe46e16524223210654bad9e1b05a15c2adb`, file `data/test-00000-of-00001.parquet`, SHA-256 `cb77ce289ba73357be0cc375df40631d0df0541e7120913cb2e89a17aae19add`.

Components connect shared material IDs, shared task IDs and exact ordered geometries over the whole source before filtering, with namespaces separate. Exact geometry hashes do not cover atom permutation, rotation, periodic translation, lattice changes or numerical tolerance. An OMat24-to-Materials-Project material crosswalk remains unavailable.

Each prerequisite needs an affirmative, hashed record. Unknown evidence is not a pass.

| Gate | Required evidence |
| --- | --- |
| Prospective roster | Exactly three predictor entries; immutable checkpoint/configuration identities; measured hashes of actual weight/configuration bytes or a documented deterministic loaded-state identity; verified linkage from the requested identity to the loaded calculator. |
| Execution and cache | Frozen runner/code/environment, backend versions, dtype, device policy and relevant numerical settings. Cache acceptance binds these and the predictor identity to the reference manifest, retaining the immutable original prediction producer separately from a later emitter. |
| Reference compatibility | Primary evidence for force units/sign, geometry/PBC conventions and calculation settings sufficient for the claim, including available XC, Hubbard-U, pseudopotential and electronic/magnetic/convergence metadata. Explicitly document any intended differences from each model's target. |
| Development exposure | Exclusions covering all 805 inspected configurations and their linked components; freeze additional crosswalk/equivalence rules before selection. Unresolved mappings cannot become affirmative physical independence. |
| Model-training independence | For every exact checkpoint, candidate eligibility relative to training, validation, fine-tuning and model-selection data, with identifier coverage and revisions. A dataset named `test` is insufficient. |
| Outcome isolation | Selection uses frozen identities, geometry and provenance only. Candidate predictions/errors, force magnitude and stress/energy values cannot select or replace rows. |
| Resources and operations | Existing authorized resource limits, no overlapping invocation, and a recorded budget sufficient for the fixed panel. No new paid compute, spending increase, device action or deployment is authorized here. |

State fingerprints must document parameter/buffer names, shapes, dtypes, serialization and byte semantics, including excluded mutable state. They are not checkpoint-file hashes. Hashing an unrelated supplied file does not prove the calculator loaded it. Package versions and container digests are separate provenance fields.

Six historical execution records now identify container image digests. Exact historical loaded weights and original cache-producer weight identity remain unresolved. Historical failures and A6 **INCONCLUSIVE** stay unchanged.

Offline runner tests establish infrastructure behavior, not roster/reference/training eligibility. Execution can proceed when prerequisites are verified and the manifest is sealed within existing authorized bounds; no extra human approval gate is imposed on already authorized bounded work.

Unknown training independence **stops this validation claim**. An observational redesign would need an explicit different claim and protocol, not a relabeling of this study as passed.

## Proposed fixed panel and selection

Select **128 eligible components, one configuration per component**. This differs explicitly from the earlier 50-by-eight archived panels. The size is a manageable budget choice, not a power calculation.

Literal proposed seed:

`lupine-prospective-ranking-v1-20261006`

Freeze source, reference eligibility, development exclusions and training exclusions before sampling. Exclude an entire component if any member has a disqualifying link. Build components over the whole pinned source; an ineligible intermediate row must not split a component. Incorporate any additional identity links before sealing.

Use this deterministic rule once:

1. A source row is its zero-based physical row index in the pinned file. Hash compact sorted-key ASCII JSON with exactly the keys `schema`, `source_sha256` and `member_row_indices` to obtain the component key. The schema is `lupine.prospective_component.v1`; the indices are sorted integers for **all** component members.
2. Rank eligible components by SHA-256 of compact ASCII JSON array `["group", seed, source_sha256, component_key]`; break ties by component key. Take the first 128.
3. Within each selected component, rank eligible rows by SHA-256 of compact ASCII JSON array `["row", seed, component_key, source_row_index, ordered_geometry_sha256]`, with an integer row index; break ties by row index. Take the first row.
4. Save and hash the eligible-universe receipt, selected manifest, component/exclusion ledger, roster lock, numerical policy and final protocol version **before** opening candidate force values or producing predictions.

Structural bounds remain 2–80 atoms, integer atomic numbers 1–83, finite correctly shaped geometry, matching atom counts, valid PBC and nonempty material/task IDs. Provenance gates may shrink the inventory. If fewer than 128 components qualify, stop; do not lower the count or substitute a source.

There is no replacement list or second seed. The panel bounds **128 × 3 = 384 model/configuration evaluations**; batching does not change that count. Record wall-time, memory and existing resource limits before execution; panel size alone does not establish those budgets.

## Fixed prediction and scores

For atom \(i\), save all three force vectors \(F_{mi}\) and reference \(F_i^\ast\). Every score uses the same target:

\[
\bar F_i=(F_{1i}+F_{2i}+F_{3i})/3,\qquad y_i=\|\bar F_i-F_i^\ast\|^2.
\]

No two-model target, fitted weight, scale correction, calibration or threshold is introduced.

| Score | Definition |
| --- | --- |
| Three individual pairs | \(p_{ab,i}=\|F_{ai}-F_{bi}\|^2\), for 1–2, 1–3, 2–3 |
| Full disagreement | \(v_i=(p_{12,i}+p_{13,i}+p_{23,i})/9\), equal to mean squared deviation about \(\bar F_i\) |
| Magnitude control | \(s_i=\|\bar F_i\|^2\) |
| Equal pair-rank fusion | \(r_{ab,i}=2\#\{j:p_{ab,j}<p_{ab,i}\}+\#\{j:p_{ab,j}=p_{ab,i}\}+1\); sum the three integer doubled midranks |

Compute and preserve pair/full/control scores once under the frozen numerical policy. Exact equality of saved numerical scores defines ties; no tuned tolerance or favorable atom ordering. Rank descending. Fusion can introduce ties.

For \(N\) atoms, \(C(k)\) is the expected fraction of total \(y\) captured in the top \(k\), using uniform inclusion inside exact ties. Retain the prior area:

\[
A=\frac{1}{N-1}\sum_{k=1}^{N-1}[C(k)-k/N].
\]

Average the 128 configuration areas with equal component weight. Do not pool atoms to select a winner. Zero total error makes capture undefined: withhold the verdict without dropping or replacing the configuration.

## Proposed decisions

**Co-primary F:** full disagreement has strictly positive mean area increment over **each** of the three individual pairs.

**Co-primary R:** rank fusion has strictly positive mean area increment over **each** of the three individual pairs.

Report both claims separately. The joint primary criterion passes only if **all six** increments are strictly positive and integrity gates pass. A zero/negative increment fails its descriptive claim. An invalid or incomplete panel is **INCONCLUSIVE**. This is one new panel, not the previous two-panel criterion.

Fixed secondary reporting:

- Full, fusion and each pair versus magnitude control; fusion versus full.
- Full/fusion areas above uniform capture.
- Every specified configuration/group increment, mean, median, extrema and positive/zero/negative counts.
- All six scores' complete capture curves, tie groups and defined/undefined Spearman correlations with \(y\); introduced/removed fusion tie sets.
- Pooled ensemble SSE and Cartesian RMSE as target-integrity descriptions, not primary selectors.

Secondary advantages cannot rescue a failed co-primary claim. No p-values, confidence intervals, alarm calibration, selected subgroup or multiplicity-adjusted significance claim is proposed.

## Verification, failures and reporting

An independent implementation must verify hashes, roster/prediction joins, symbols, geometry/reference alignment, dimensions, finiteness and units; then reproduce every curve, correlation, mean and sign count.

Use exact rational or high-precision raw-force arithmetic and an independent expected tie-inclusion calculation. Separately reproduce saved-score tie semantics. Disclose all rank/tie or near-zero sign differences. An unresolved difference changing a primary decision withholds it; never choose the favorable implementation.

Stop before inference on missing/mismatched predictor or cache identity. Stop on incompatible/unverified reference provenance, new resource needs or overlap with another invocation. Model errors, timeouts, nonfinite output, incomplete roster or discovered leakage preserve a failed/blocked receipt and withhold the verdict. No automatic retries, model/row/source substitutions or post-outcome protocol changes.

A genuinely distinct follow-up requires a new brief. Never retry, rename or relabel a stopped invocation to evade its state.

Raw rows, identities, weights and predictions stay private. Reviewed public aggregates may include limitations, actual evidence timestamps and hashes. Proposal, offline implementation check, execution, arithmetic verification and scientific conclusion are separate states.

## Next bounded prerequisite task

Prepare **one candidate checkpoint/provenance package per proposed family**, plus **one pinned source reference/training-split packet**. Predeclare those four named sources; one attempt each within existing resource limits. Do not broaden this into historical-cache hunting or candidate predictions.

For each model, identify the immutable package, primary training/reference documentation, and evidence connecting future measured loaded state to that package. For the source, establish reference conventions and candidate-to-model training-split evidence. An advertised hash is unverified until actual bytes or documented loaded state are checked.

Deliver a four-packet **roster/reference readiness matrix** with every field evidenced or explicitly missing. Seal the roster and sampling manifest only if all gates pass. Otherwise name the missing field or incompatibility and stop, without another generic provenance search. This draft and the runner repair alone do not establish readiness.

## Evidence anchors

See the [pairwise study](./2026-10-06-pairwise-disagreement.md), [rank-fusion study](./2026-10-06-rank-fusion.md), [eligibility audit](./2026-10-06-validation-eligibility.md) and [source recovery](./2026-10-06-pinned-source-overlap.md).

| Preserved artifact | SHA-256 |
| --- | --- |
| Pairwise protocol | `87bd4fdb70a0e5b23205678bd48458e5f6bd5a2a0f879e064267e6f411a5a594` |
| Rank-fusion protocol | `ae65d93dfc87688f67e7b701988c905a8e0a37ef231cdee6e390b5bc0e803b84` |
| Known 805-case index | `56ca5907cf800521f300addeb348111688e03e304bf712f8e70a9a80b2b5bb61` |
| Candidate identity index | `1e05c5d08e4ca07e198727e3e63e4042f35268e528d176ef3822d573549bdb12` |
| Independent candidate agreement | `44dc4dcbd2dbf4df1e7c2bb56fd70669b719b8dba9971304b202c8ca7f5e847b` |
| Execution-provenance adjudication | `3186bcd7363d48dc3d566b0bc5a34f5f59c0c2e34bb23806b44d160a78278ea9` |

Hashes are traceability anchors, not access to private evidence. No completed model draft/review, selected-panel, launch or performance receipt is claimed.
