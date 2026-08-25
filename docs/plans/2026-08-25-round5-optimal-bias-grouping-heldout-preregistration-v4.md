# Round-5 preregistration v4 — fixed held-out grouping experiment

> **Status:** REGISTERED, REVIEW PENDING. Registered at
> `2026-08-25T21:24:09Z`, before any Round-5 execution or model-output
> inspection. Independent reviewer ACCEPT remains an execution prerequisite.
> V1, v2, and optimal-bias v3 remain immutable. Any decision-bearing change to
> this document, its selector, grouping executable, or CampaignManifest requires
> a new campaign identity.

## 1. Why v4 exists

The accepted v2 lock required `chemistry` and
`composition_space_neighbourhood` but did not define their derivation. It also
constructed one calibration hull from the exact four-field tuple while THEORY-3
asks which of four separate grouping rules yields narrow, direction-eligible,
license-admissible hulls. Optimal-bias v3 changed the correction estimator but
retained the undefined labels and exact-tuple leave-one-out design.

A later machine-checked result showed that leave-one-out escape rate is
structurally forced by group size: each non-tied finite group contributes its
minimum and maximum as the two escapes. It therefore cannot answer whether a
physical grouping transfers to unseen structures. V4 replaces leave-one-out
with one prospective class-stratified calibration/test split. The same held-out
targets are reused for every grouping rule, so a target contributes to no
calibration hull and all paired rule comparisons use identical targets.

This is a distinct identity:
`correction.round-5.optimal-bias-grouping-heldout.v4`. No predecessor file,
hash, endpoint, timestamp, or result is rewritten or reclassified. The v2
exact-tuple grouping is retained only as an explicitly non-confirmatory
predecessor diagnostic under the v4 held-out split; it is not called a v2
replay.

## 2. Fixed panel and split

The campaign remains exactly 125 elastic structures by four registered models:
500 model×structure cells. It is not LiTraj, NEB, CI-NEB, or a barrier campaign.
Class quotas are 63 `ionics-rocksalt` and 62 `perovskites`. Every cell measures
`a0`, `C11`, `C12`, and `C44`; `B0` is descriptive only.

Panel selection uses only locked candidate metadata and accepted reference
provenance. Within each class, candidates are ranked by the selector's SHA-256
rule and the first exact quota is selected. After the 125 structures are fixed,
`tools/round5_grouping.py` assigns one immutable role using seed
`round5-grouping-heldout-20260825-v4` and rank
`SHA256(seed + NUL + class + NUL + source_structure_id)`, with bytewise source
ID as the collision tie-break. In each class the first `floor(2*n/3)` are
calibration structures and the rest are targets:

- ionics-rocksalt: 42 calibration, 21 held-out targets;
- perovskites: 41 calibration, 21 held-out targets;
- total: 83 calibration, 42 held-out targets.

The role is reused under every grouping rule. Role changes, duplicate IDs,
missing IDs, model-output-dependent assignment, target inclusion in any
calibration set, and leave-one-out substitution refuse the campaign.

## 3. Versioned grouping derivations

The normative vocabulary is
`data/contracts/round5-grouping-vocabulary.v1.json`; the normative executable is
`tools/round5_grouping.py`. Their file hashes are bound by the v4 selector and
manifest. Candidates provide raw `elemental_composition`, `class`, and
`structure_prototype`; operator-supplied `chemistry` or
`composition_space_neighbourhood` refuses.

### 3.1 Class

`class` must be exactly `ionics-rocksalt` or `perovskites`. Case, whitespace,
and aliases refuse. The key is the exact value.

### 3.2 Chemistry

`elemental_composition` is an object from exact element symbol to positive,
non-Boolean integer count. Counts are gcd-reduced. `chemistry` is the unique
set of element symbols sorted by atomic number and joined by one ASCII hyphen.
A dictionary-order change or common stoichiometric multiple cannot change the
key. Atomic numbers are discrete and unique, so there is no boundary or tie.
Empty compositions, unknown symbols, isotopes, pseudo-species, Boolean counts,
fractional counts, zero, and negative counts refuse.

### 3.3 Structure prototype

`structure_prototype` is an exact AFLOW-style vocabulary value, not free text.
V1 permits `AB_cF8_225_a_b` only for ionics-rocksalt and
`AB3C_cP5_221_a_c_b` only for perovskites. Any mismatch or alias refuses.

### 3.4 Composition-space neighbourhood

This is a prospective coarse operational cell, not a claim of phase,
oxidation-state, prototype, or chemical equivalence. Each reduced composition
is projected onto atomic-number bands `Z001-010`, `Z011-020`, through
`Z111-118`. Stoichiometric counts are summed within occupied bands, the band
vector is gcd-reduced, zero bands are omitted, and terms are emitted in band
order after prefix `csn-zband10-v1:`.

Boundaries use integer floor division: Z=1..10 enters `Z001-010`, Z=11..20
enters `Z011-020`, and so on through Z=118. There is no floating-point nearest
neighbour or equidistance tie.

## 4. Four independent held-out hulls and licenses

For held-out target X, model m, property p, and one rule, select only structures
whose immutable role is `calibration` and whose key for that rule exactly equals
X's key. Require at least four. Otherwise emit
`INSUFFICIENT_GROUP_CALIBRATION` for that exact rule/model/target/property. The
four rules are:

1. `class` — v4 primary confirmatory correction rule;
2. `chemistry` — registered secondary;
3. `structure_prototype` — registered secondary;
4. `composition_space_neighbourhood` — registered secondary.

The predecessor exact four-key tuple is computed as a fifth, non-confirmatory
diagnostic on the same fixed roles. Calibration data, hulls, or license states
may not be copied across rules.

Calibration ratios `pred_i/ref_i` are converted to integer U=10000 by decimal
round-half-even. Each rule gets its own `lo`, `hi`, width `hi-lo`, direction
gate, regime-optimal bias, and THEORY-4 rounding-robust license. The registered
optimal-bias implementation remains
`python/lupine_distill/statics/optimal_bias.py`. Only the class rule may apply a
correction or contribute a primary win. Secondary licenses answer whether a
reference grouping is admissible; they do not substitute corrected predictions.

For the later held-out target ratio r, escape is `r < lo` or `hi < r`; equality
is in-hull. Overshoot is `lo-r` below or `r-hi` above, otherwise zero. Report
the exact escape numerator and denominator and the complete sorted positive
overshoots. Nearest-rank p50 and p90 use one-indexed rank
`max(1, ceil(q*n))`; max is exact. With no positive overshoots, quantiles are
null and state is `NO_ESCAPES_OBSERVED`. No Wilson or binomial confidence
interval is computed: this is the finite registered panel, not an IID binomial
sample.

## 5. Endpoints and claim boundaries

The primary sampling unit is one distinct held-out target. For each
class×property, aggregate the four registered-model corrected-minus-raw absolute
relative-error differences by fixed-point median. Exact zero is a tie. Use the
two-sided exact sign test with strict `p < 0.1`; require at least 16 distinct
non-tied applied targets. Underpowered properties are
`UNDERPOWERED_NOT_SCORABLE`, not losses. A class succeeds only if at least three
of four scorable properties win; fewer than three scorable properties is
`INCONCLUSIVE_UNDERPOWERED`.

For every rule, class, and property report target count, complete four-model
hull count, insufficient-calibration count, width summaries, direction and
license counts, exact license fraction, exact held-out escape fraction, and
overshoot distribution.

The registered inferential secondary family compares chemistry, prototype, and
neighbourhood widths against class for C11, C12, and C44 within two classes: 18
contrasts. Pair within the same target and model, require all four model pairs,
aggregate to one target difference by fixed-point median, drop exact-zero ties,
and use a one-sided exact sign test for the narrower alternative with Holm FWER
0.1. Require at least 16 non-tied targets per contrast. No unregistered
subgroup, regrouping, pooled result, threshold, or post-outcome label may become
a confirmatory claim.

## 6. Materials Project reference disposition

Materials Project elasticity dataset version `2026-04-13` is **conditionally
admissible**, never blanket-admissible. The API client exposes the
`materials/elasticity` route and returns `ElasticityDoc` records.[5] The pinned
Emmet data model distinguishes the structure-orientation and IEEE-orientation
elastic tensors in GPa and carries deformation, optimization-task, and total
strain/stress-state fitting provenance.[4] Materials Project separately
publishes elasticity methodology and database-version guidance.[1][2]

The reconnaissance counts of 266 nondeprecated successful Fm-3m AB records and
413 Pm-3m ABC3 records with at most 40 sites are availability observations only.
They are not registered inputs, acceptance evidence, or outcomes.

Before selection, save the exact raw response at
`data/candidates/round5_materials-project-elasticity-2026-04-13.raw.lock.json`.
Lock API base URL and route, client identity/version, requested fields, UTC
retrieval time, raw-query digest, all relevant `builder_meta`, material ID,
update/deprecation/state/warning/origin metadata, full structure, IEEE tensor,
optimization task, deformation task IDs, and total strain-state count.

A record is admissible only when every selector condition passes, including:
exact `builder_meta.database_version == 2026-04-13`; successful, nondeprecated,
unwarned state; finite 6×6 IEEE tensor; exactly 24 recorded strain/stress states
with optimization and deformation task provenance; exact source material ID;
same locked phase, prototype, Wyckoff signature, composition, and structure for
candidate geometry and references; no partial occupancy; cubic standardization
within the frozen tolerances; source-precision cubic-component agreement;
positive finite a0/C11/C12/C44; cubic Born stability; and complete digest
reconciliation. The exact 24-state requirement is an acceptance rule: a record
that does not prove it refuses, regardless of general methodology.

The convention is provider-relaxed equilibrium geometry plus relaxed-ion
elasticity in IEEE orientation and GPa. The model runner must independently
fully relax its equilibrium cell, relax internal coordinates at every symmetric
finite strain, and convert to the same IEEE orientation. Raw orientation,
clamped-ion elasticity, mixed phase, nearest polymorph, formula-only matching,
missing provenance, warned/failed records, and digest mismatch refuse.

Historical context is de Jong et al., “Charting the complete elastic properties
of inorganic crystalline compounds,” Scientific Data 2, 150009 (2015), DOI
`10.1038/sdata.2015.9`.[3] Historical method and current schema links do not
prove that any retrieved record belongs to database version 2026-04-13; the raw
response and record metadata must prove that at materialization time.

## 7. Landed-theorem gate

V2 required the reviewed equivalent theorem to be “landed.” V4 preserves and
makes that gate executable. PR #112 was squash-merged as
`512ee8af744b42cc2f727ffdc37cdd45570a76b9`; the reviewed head's
`SharpLicense.lean` is byte-equivalent to the merged path. PR #117's
rounding-soundness merge is `799eacb2b389ff4c8d3537eb3b16d92869942e83`,
and PR #118's proof-revision merge is
`a102e806eb6c97251c1075d4c16f8981fa42e8d9`.

Immediately before execution, all three merge commits must be ancestors of the
fetched `origin/main`, the reviewed-to-merged path comparison must be empty, and
repository formula/link tests must pass. An open PR, green CI, reviewer comment,
nonancestor commit, path drift, or formula mismatch is
`EXECUTION_REFUSE_THEOREM_NOT_LANDED`. No worker may merge under this
registration; owner approval remains required.

## 8. Immutable execution boundary

Round 5 may run only on dedicated digest-pinned Cloud Run jobs with
`maxRetries: 0`. Legacy Round-4 jobs and mutable tags are forbidden. Every cell
binds the v4 manifest, selector, vocabulary, grouping executable, source pool,
raw query, materialized panel, split assignment, calibration implementation,
model artifact, runner image, attempt, and immutable artifact URI.

Before any execution: the immutable v4 files and hashes must be registered;
independent review must ACCEPT; theorem landing must pass; raw query, source
pool, panel, and split must validate; cardinality must be exactly 125 structures,
83 calibration structures, 42 held-out targets, and 500 model cells; dedicated
job/image receipts must reconcile. Missing, stale, contradictory, unverified,
out-of-schema, retried, or digest-mismatched evidence is a refusal.

No Round-5 model output was inspected, no model was executed, no cloud job was
dispatched, and no cloud budget was spent while registering v4.

## Sources

[1] https://docs.materialsproject.org/methodology/materials-methodology/elasticity
[2] https://docs.materialsproject.org/changes/database-versions
[3] https://www.nature.com/articles/sdata20159
[4] https://raw.githubusercontent.com/materialsproject/emmet/3f2daf4f897fc1551fd133ca26ce612e843ae0ae/emmet-core/emmet/core/elasticity.py
[5] https://raw.githubusercontent.com/materialsproject/api/6c7e961624e12d16c0bdd53aed24fa7c94a16152/mp_api/client/routes/materials/elasticity.py
