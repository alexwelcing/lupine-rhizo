# Round-5 preregistration — powered sharp-license correction trial

> **Status:** FROZEN FOR REGISTRATION. The registration time is the driving
> board card's operator-supplied `created_at` event, `2026-08-04T13:17:40Z`.
> This document, its machine-readable panel-selection contract, and the
> CampaignManifest content hash must be present in `registry/campaigns.v1.json`
> before any Round-5 model output or reference outcome is inspected. Any change
> after registration creates a new campaign version; it may not overwrite this
> one.

## 1. Design correction and power calculation (performed first)

Round 4 used a two-sided exact sign test with `alpha = 0.1`. With only four
non-tied applied observations, even a perfect 4/4 result has minimum attainable
`p = 2 * 2^-4 = 0.125`, so the endpoint was mathematically incapable of
passing. Round 5 fixes the design rather than reinterpreting that negative
result.

The confirmatory sampling unit is one **distinct structure**, not one
model×structure cell. For a class×property stratum, a structure contributes one
paired sign after taking the median, across the registered models for which the
rule applied, of

`delta = absolute_relative_error_corrected - absolute_relative_error_raw`.

Negative delta is improvement, positive delta is worsening, and exact zero is
a dropped tie. This structure-level aggregation prevents four correlated model
outputs for one material from masquerading as four independent observations.

The frozen test is the two-sided exact binomial sign test under `p0 = 0.5`, with
strict `p < 0.1`. The required analyzable sample size is **at least 16 distinct,
non-tied applied structures per class×property**. At `n = 16`:

- minimum attainable two-sided p-value: `2 * 2^-16 = 0.000030517578125`;
- the improvement-side rejection region is at least 12 improved of 16;
- exact power at a prospectively chosen, practically meaningful improvement
  probability of 0.8 is `0.798249`; and
- the minimum p-value is 3,276.8 times below alpha.

The 0.8 alternative is a design target, not an estimate from Round-4 outcomes.
The sharp-gate replay of Round-4 outcomes was outcome-reading exploratory work:
it is a power calculation only, is not confirmatory evidence, and must never be
cited as a Round-5 result.

If any confirmatory class×property has fewer than 16 distinct non-tied applied
structures after all 500 registered cells complete, that property is
`UNDERPOWERED_NOT_SCORABLE`, cannot be called a win or loss, and cannot enter a
group denominator. There is no adaptive extension, replacement, early stop, or
post-outcome pooling.

## 2. Scientific units and fixed execution budget

The 500 units are **elastic-structure measurement cells**, not LiTraj or any
other NEB paths. The frozen panel contains 125 structures: 63
`ionics-rocksalt` and 62 cubic `perovskites`. Each structure is evaluated by all
four registered models, yielding exactly `125 * 4 = 500` model×structure cells.
Each cell measures `a0`, `C11`, `C12`, and `C44`; `B0` is descriptive only.
Barrier observables, LiTraj records, CI-NEB, and Z1 path machinery are excluded.

The exact candidate-selection algorithm, seed, quotas, required grouping
fields, and source/materialization refusal rules are frozen in
`data/candidates/round5_elastic_panel-selection.lock.json`. That contract is the
CampaignManifest's content-addressed `candidate_panel`. Before dispatch, the
executor must materialize its deterministic output as
`data/candidates/round5_elastic_panel.lock.json`, record the source-pool SHA-256,
panel SHA-256, parent selection-contract SHA-256, and parent CampaignManifest
content hash, and verify exactly 125 structures and 500 cells. Missing or
mismatched locks are a refusal.

## 3. Frozen correction rule

The theorem source used to freeze this rule is
`theory-artifacts/SharpLicense.lean` at Lupine meta-repo commit
`8bdedd6157f0504f06c7704beada262f6f7ff63b`, full-file SHA-256
`c638e9c097fa2d8aa14c2a0da04041b1fff7b160f648f0725a02d8b2ca252443`.
THEORY-1 must land an equivalent reviewed theorem in `lean-spec` before
execution; any formula or strictness mismatch refuses dispatch rather than
amending this registration.

For held-out structure X, model m, property p, and the calibration stratum
identified by the exact tuple `(class, chemistry, structure_prototype,
composition_space_neighbourhood)`:

1. The calibration set is every other panel structure in the same tuple with a
   non-null, provenance-accepted reference for p. X is always excluded. Require
   at least four calibration structures; otherwise ABSTAIN
   (`insufficient_calibration`).
2. Convert each `pred_i / ref_i` ratio to fixed-point integer units `U = 10000`
   using decimal round-half-even. Let `lo = min(ratios)`, `hi = max(ratios)`,
   and `b = median(ratios)`; for an even count, median is round-half-even of the
   two central integers' arithmetic mean.
3. **Direction gate, unchanged:** apply only if every calibration ratio is
   strictly above U or every ratio is strictly below U. A mixed-side set or any
   ratio equal to U ABSTAINS (`direction_gate`).
4. **Sharp license gate from THEORY-1:**
   - inflation (`U < lo`): license iff `b * (2*U - lo) < lo * U`;
   - deflation (`hi < U`): license iff `hi * (U + b) < 2 * U * b`.
   Otherwise ABSTAIN (`sharp_license`). There is no spread cap and no deflation
   floor.
5. If licensed, `corrected = pred / (b/U)`; otherwise the cell is abstained and
   excluded from the paired sign endpoint. The theorem's guarantee remains
   conditional on the held-out true ratio being in `[lo, hi]`; this oracle
   condition is never represented as runtime-knowable.

The direction gate is intentionally retained. The outcome-reading Round-4
observation that only 9 of 50 direction-gate abstentions were in-hull
improvements is motivation only, not confirmatory evidence and not an endpoint.

## 4. Measurements and reference discipline

All four confirmatory properties are measured at each model's own fully relaxed
equilibrium cell. Elastic constants use symmetric finite strains about that
cell with internal coordinates relaxed at every strain. The exact strain grid,
optimizer, force/stress tolerances, maximum steps, calculator precision, and
failure codes must be frozen in the materialized panel before dispatch. This
repairs Round 4's perovskite instrument defect; nearest-grid-volume,
clamped-ion elastic constants are not admissible.

References must be locked before model execution, carry per-property source
provenance, and match the same phase, structure prototype, thermodynamic
interpretation, and elastic convention. Missing, weak, mixed-phase, or
unmatched references remain null and are excluded without imputation. Round
1–4 structures and any structure used to choose or tune the sharp theorem are
excluded by the panel-selection contract.

## 5. Primary confirmatory endpoint

Properties are `a0`, `C11`, `C12`, and `C44` in each of the two registered
classes. A class×property is a WIN only when all conditions hold:

1. at least 16 distinct non-tied applied structures;
2. median structure-level delta is strictly negative; and
3. the two-sided exact sign-test p-value is strictly below 0.1.

A class succeeds when at least 3 of its 4 confirmatory properties WIN. A
property marked `UNDERPOWERED_NOT_SCORABLE` is not silently counted as a loss,
but if fewer than 3 properties are scorable the class verdict is
`INCONCLUSIVE_UNDERPOWERED`, not SUCCESS or FAILURE. Failed scorable properties
are reported verbatim.

The theorem-consistency kill condition is unchanged in meaning: among licensed
model×structure×property cells whose held-out ratio is later observed inside
its calibration hull, the worsened count must be zero. Any positive count is a
hard implementation/reference defect and kills promotion.

## 6. Registered secondary endpoint: hull-width hypothesis

The directional secondary hypothesis is that elastic-property calibration
hulls are wider than lattice-constant hulls within the same model, held-out
structure, and exact grouping tuple. Hull width is `(hi - lo) / U`. The required
fields on every candidate and result row are:

- `class`;
- `chemistry`;
- `structure_prototype`;
- `composition_space_neighbourhood`.

For each class and each elastic property (`C11`, `C12`, `C44`), pair its hull
width with the same cell's `a0` hull width. Pairs with a missing width are
excluded; zero/zero pairs are ties. Test the directional alternative
`elastic width > a0 width` with a one-sided exact sign test. Control the six
class×elastic tests with Holm step-down family-wise alpha 0.1. Report paired n,
wider/equal/narrower counts, median widths, median width ratio when the a0 width
is positive, raw p, and Holm-adjusted p. No subgroup may be promoted to a
confirmatory claim.

Round-4 exploratory spreads (`a0` 0.0098–0.039, `C11` 0.113–0.374, `C12`
0.100–0.649, with rocksalt `C12` not even one-sided) motivated this endpoint.
They are outcome-read historical observations, not evidence for Round 5 and
must not be pooled with it.

## 7. Execution and provenance gate

Round 5 may run only on new dedicated Cloud Run jobs. The four drifted legacy
Round-4 jobs and their current `z1-barrier-f64r2-20260719` tags are inadmissible.
Before dispatch, freeze for every model: dedicated job name, immutable image
digest (not a mutable tag), command/args, service account, region, CPU/memory,
timeout, and `maxRetries: 0`. Each result must record the manifest content hash,
selection-contract SHA-256, materialized-panel SHA-256, model artifact hash,
runner image digest, attempt number, and immutable artifact URI. Any retry,
missing digest, tag-only image, manifest mismatch, panel mismatch, duplicate
cell, missing cell, or extra cell is a refusal; no silent retry or imputation is
permitted.

The owner-approved execution budget is a ceiling, not evidence and not a public
economics claim. Approved public economics remain limited to the separate
guardrails; Round 5 derives no cost ratio, multiplier, annualization, or
substitute claim.

## 8. Registration boundary

The CampaignManifest, this preregistration document, and the panel-selection
contract are locked before execution. The registry entry is the registration
record. Execution code and its tests must be committed and reviewed before the
materialized panel is locked. The selection source pool and final panel may be
materialized after registration only by the frozen algorithm and before any
model output is inspected. Their hashes become immutable execution inputs; a
mismatch refuses dispatch rather than amending this preregistration.
