# Round-5 preregistration v3 — executable grouping semantics and reference lock

> **Status:** FROZEN FOR REGISTRATION. The prospective registration event is
> the prerequisite-card creation time `2026-08-04T14:31:08Z`. No Round-5 model
> output had been inspected and no Round-5 cloud execution had been dispatched.
> V1 and v2 remain immutable. This v3 identity is required because defining the
> previously undefined grouping labels and separating the four grouping rules
> changes both panel selection and analysis.

## 1. Why v3 is a new identity

Round-5 v2 (`correction.round-5.sharp-license.v2`) froze calibration on the
exact tuple `(class, chemistry, structure_prototype,
composition_space_neighbourhood)`, but did not freeze how `chemistry` or
`composition_space_neighbourhood` were derived. It also did not define the
requested four grouping rules as four separate calibration analyses. Assigning
those values after model outputs existed would change group membership, hull
width, licensability, and potentially the empirical answer.

V2 is therefore preserved byte-for-byte as accepted historical registration,
but is not the executable identity for THEORY-3. V3 prospectively freezes:

- a versioned grouping vocabulary;
- a hash-locked executable derivation;
- four separate leave-one-out calibration rules;
- a class-grouped v3 primary correction endpoint;
- registered secondary comparisons for chemistry, structure prototype, and
  composition-space neighbourhood; and
- the v2 exact-tuple computation as an immutable diagnostic that may not be
  substituted for the v3 class endpoint.

No v1 or v2 file, hash, campaign ID, seed, timestamp, or registry entry is
changed by v3.

## 2. Fixed scientific units and panel

The campaign remains exactly 125 elastic structures by four registered models,
or 500 model×structure cells. It is not a LiTraj, NEB, CI-NEB, or barrier
campaign. The class quotas remain 63 `ionics-rocksalt` and 62
`perovskites`. Every cell measures `a0`, `C11`, `C12`, and `C44`; `B0` is
descriptive only.

The candidate source pool, raw reference query, and final panel must be locked
before dispatch. Selection uses only candidate metadata and accepted references,
never model outputs or correction outcomes. Within each class, candidates are
ranked by the frozen SHA-256 rule in
`data/candidates/round5_elastic_panel-selection.v3.lock.json`; the first exact
class quota is selected. Before dispatch, every selected structure must have at
least four other class peers with accepted references for every confirmatory
property, and every class×property must have at least 16 such structures. A
failure is `STRUCTURALLY_UNDERPOWERED_REFUSE`.

Secondary chemistry, prototype, neighbourhood, and legacy exact-tuple groups
are not forced to be large. Their insufficient occupancy is part of the
prospectively registered empirical result and is reported as
`INSUFFICIENT_GROUP_CALIBRATION`; it is never repaired by changing labels,
transferring structures, pooling rules, or selecting after model outputs.

## 3. Versioned grouping derivations

The normative vocabulary is
`data/contracts/round5-grouping-vocabulary.v1.json`. The normative executable is
`tools/round5_grouping.py`. Their SHA-256 values are bound by the v3 selection
contract and CampaignManifest.

Every candidate supplies `elemental_composition` as a JSON object from exact
element symbol to positive, non-boolean integer count. Counts are reduced by
their greatest common divisor. Empty compositions, unknown symbols, isotopes,
pseudo-species, Boolean counts, fractional counts, zero counts, and negative
counts refuse the candidate. Operator-supplied derived labels are forbidden.

### 3.1 Class

`class` is an exact vocabulary value. V1 allows only `ionics-rocksalt` and
`perovskites`. Case changes, whitespace changes, and aliases refuse. The class
group key is the exact value.

### 3.2 Chemistry

`chemistry` is the chemical-system key: unique element symbols from the reduced
composition, sorted by IUPAC atomic number, joined by one ASCII hyphen. Thus a
dictionary-order change or common stoichiometric multiple cannot change the
key. Atomic numbers are discrete and unique, so there is no boundary or tie.
Unknown or non-elemental symbols refuse.

### 3.3 Structure prototype

`structure_prototype` is an exact AFLOW-style vocabulary value, not a free-text
alias. V1 permits only `AB_cF8_225_a_b` for `ionics-rocksalt` and
`AB3C_cP5_221_a_c_b` for `perovskites`. Any class/prototype mismatch refuses.
The prototype group key is the exact value.

### 3.4 Composition-space neighbourhood

The neighbourhood is a prospective coarse cell in composition space, not a
claim of phase, oxidation-state, prototype, or chemical equivalence. Each
reduced composition is projected onto 12 atomic-number bands of width ten:
`Z001-010`, `Z011-020`, ..., `Z101-110`, `Z111-118`. Reduced stoichiometric
counts are summed in each occupied band, the band-count vector is reduced by
its own gcd, zero bands are omitted, and terms are emitted in ascending band
order. The key begins `csn-zband10-v1:`.

Boundaries are exact integer boundaries: atomic numbers 1 through 10 enter
`Z001-010`, 11 through 20 enter `Z011-020`, and so on through 118. There is no
nearest-neighbour search, floating-point rounding, or equidistance tie. The
integer floor rule assigns every boundary prospectively and uniquely.

## 4. Four separate hull and sharp-license rules

For held-out structure X, registered model m, property p, and one named rule,
form the calibration set from every other selected structure whose key for that
rule exactly equals X's key and whose p reference is accepted. X is always
excluded. The four v3 rules are:

1. `class` — v3 primary confirmatory correction rule;
2. `chemistry` — registered secondary rule;
3. `structure_prototype` — registered secondary rule; and
4. `composition_space_neighbourhood` — registered secondary rule.

The immutable v2 exact tuple is computed separately as a fifth diagnostic using
simultaneous equality on all four keys. It is not a v3 confirmatory endpoint.
No calibration structure or hull may be copied across rules.

Require at least four calibration structures. Otherwise emit
`INSUFFICIENT_GROUP_CALIBRATION` for the exact rule/model/structure/property.
For an admitted calibration set, convert each `pred_i/ref_i` to fixed-point
integer units `U = 10000` using decimal round-half-even. Set `lo` and `hi` to
the minimum and maximum and `b` to the median; an even median is the arithmetic
mean of the two central integers rounded decimal half-even. Record width
`hi-lo` in fixed-point units and `(hi-lo)/U` as an exact decimal/rational value,
not a binary-floating recomputation.

The direction gate is unchanged: continue only when every ratio is strictly
above U or every ratio is strictly below U. A mixed-side set or any equality to
U emits `DIRECTION_GATE_ABSTAIN`.

The machine-checked sharp conditions are unchanged:

- inflation (`U < lo`): `b * (2*U - lo) < lo * U`;
- deflation (`hi < U`): `hi * (U + b) < 2 * U * b`.

Equality refuses because the theorem proves strict improvement. Each rule
records its own `SHARP_LICENSED` or `SHARP_LICENSE_ABSTAIN`. Only the v3 primary
class rule applies the correction and contributes to primary correction wins.
The other rules answer whether their reference sets are narrow and one-sided
enough to license; they do not create substituted corrected predictions.

## 5. Primary and grouping-analysis endpoints

The primary sampling unit remains one distinct structure. For each
class×property, take the median fixed-point corrected-minus-raw absolute relative
error across registered models for which the v3 class rule applied. Negative is
improvement, positive is worsening, and exact zero is a dropped tie. Use the
two-sided exact binomial sign test under `p0=0.5` with strict `p < 0.1`. Require
at least 16 distinct non-tied applied structures. The v2 power calculation and
v3 sample requirement remain: minimum p at n=16 is
`0.000030517578125`, and the improvement-side rejection region begins at 12 of
16. Underpowered properties are `UNDERPOWERED_NOT_SCORABLE`, never losses.

A class succeeds only if at least three of four scorable properties win. Fewer
than three scorable properties yields `INCONCLUSIVE_UNDERPOWERED`. The theorem
consistency kill remains zero licensed, later-observed-in-hull worsened cells.

For every rule (including the immutable v2 tuple), class, and property, report:

- total distinct structures;
- distinct structures with complete four-model hulls;
- insufficient-calibration count;
- structure-median fixed-point and normalized hull width;
- direction-eligible model×structure cells;
- sharp-licensed model×structure cells; and
- the exact sharp-license numerator and denominator.

The registered inferential secondary family compares each of chemistry,
prototype, and neighbourhood against class for `C11`, `C12`, and `C44`, within
each of two classes: 18 contrasts. For each held-out structure and model, form
the alternative-rule width minus class-rule width. Require both widths. Require
all four registered model pairs, aggregate to one structure difference by the
fixed-point median with decimal half-even even-median rule, and drop exact-zero
ties. Test the one-sided narrower alternative with an exact sign test and Holm
step-down FWER 0.1 across all 18 contrasts. Require at least 16 non-tied
structures per contrast; otherwise report `UNDERPOWERED_NOT_SCORABLE`.

No unregistered subgroup, regrouping, threshold, contrast, pooled result, or
post-outcome label may be promoted to a confirmatory claim.

## 6. Materials Project elasticity reference disposition

Materials Project elasticity database version `2026-04-13` is
**conditionally admissible**, not blanket-admissible. The live discovery counts
of 266 Fm-3m AB and 413 Pm-3m ABC3 records are availability reconnaissance only:
they are neither registered inputs nor acceptance evidence, and they are not
used as Round-5 outcomes.

The raw API response must be saved at
`data/candidates/round5_materials-project-elasticity-2026-04-13.raw.lock.json`
and hash-locked. The source-pool lock must retain the exact API base URL, route,
client and version, requested field list, UTC retrieval time, raw-query hash,
all relevant `builder_meta`, material ID, update/deprecation/state/warning and
origin metadata, full structure, IEEE elastic tensor, optimization task,
deformation task IDs, and total strain-state count listed in the selection
contract.

A record is accepted only when all of the following hold:

- `builder_meta.database_version` equals `2026-04-13` exactly;
- `deprecated` is false, no deprecation reason exists, and `state` is
  `successful`;
- the elasticity tensor is finite, 6×6, and in `elastic_tensor.ieee_format`;
- the fitting provenance identifies the equilibrium optimization and
  deformation tasks and exactly 24 total strain-stress states;
- the candidate source ID is the exact Materials Project material ID;
- the same locked structure supplies candidate geometry and references;
- composition, space group, AFLOW prototype, and Wyckoff signature all match;
- there are no partial occupancies and no nearest-polymorph or formula-only
  substitutions;
- the conventional standardized lattice is cubic within relative length
  tolerance `1e-6` and absolute angle tolerance `1e-6` degree;
- cubic-equivalent entries of the IEEE tensor agree exactly at source precision;
- `a0`, `C11`, `C12`, and `C44` are finite and strictly positive;
- cubic Born checks `C11-C12 > 0`, `C11+2*C12 > 0`, and `C44 > 0` pass; and
- raw-query, structure, reference, and source-pool hashes all reconcile.

The reference convention is provider-relaxed equilibrium geometry plus
relaxed-ion elasticity in IEEE orientation and GPa. The Round-5 model runner
must independently use its own fully relaxed equilibrium cell, relax internal
coordinates at every symmetric finite strain, and convert to the same IEEE
orientation. A raw/POSCAR-orientation tensor, clamped-ion tensor, mixed phase,
prototype mismatch, missing task provenance, warning-laundered failed record,
non-cubic component disagreement, or digest mismatch refuses the record.

This disposition follows the Materials Project elasticity method and data
model: the public methodology describes 24 deformations and ionic relaxation;
`ElasticityDoc` distinguishes raw and IEEE tensors and records the underlying
strain/stress/task data. Historical context is de Jong et al., “Charting the
complete elastic properties of inorganic crystalline compounds,” Scientific
Data 2, 150009 (2015), DOI `10.1038/sdata.2015.9`, which reports the
high-throughput stress-strain workflow and IEEE tensor convention.

Source links locked for the registration narrative:

- https://docs.materialsproject.org/methodology/materials-methodology/elasticity
- https://docs.materialsproject.org/changes/database-versions
- https://www.nature.com/articles/sdata20159
- `materialsproject/emmet` commit
  `3f2daf4f897fc1551fd133ca26ce612e843ae0ae`,
  `emmet-core/emmet/core/elasticity.py` and base metadata models;
- `materialsproject/atomate2` commit
  `ceb8e4f92f432e591b68e27767880337328821ab`, elastic flow and
  internal-coordinate relaxation makers; and
- `materialsproject/api` commit
  `6c7e961624e12d16c0bdd53aed24fa7c94a16152`, elasticity API client route.

These method links do not replace record-level hashes or prove that a retrieved
record belongs to version 2026-04-13. The locked raw response and each record's
metadata must prove that at materialization time.

## 7. THEORY-1 landing gate

V2 said an equivalent reviewed theorem must be “landed.” V3 resolves this
without weakening it: the reviewed PR #112 head
`c0b52e709e66edc7cac2e14d86bb3270a8448a40`, or a byte-equivalent reviewed
successor, must be merged into `origin/main` before execution. The executor must
verify that the reviewed head is an ancestor of `origin/main` and that repository
formula/link checks pass. An open PR, green CI, or reviewer comment without a
merge is `EXECUTION_REFUSE_THEOREM_NOT_LANDED`. No worker may merge the PR under
this registration; owner approval remains required.

## 8. Execution and provenance boundary

Round 5 may run only on dedicated digest-pinned Cloud Run jobs with
`maxRetries: 0`. The drifted legacy Round-4 jobs and mutable image tags are
forbidden. Every result binds the v3 CampaignManifest content hash, selector,
grouping vocabulary, grouping executable, source pool, raw Materials Project
query, materialized panel, model artifact, runner image, attempt number, and
immutable artifact URI. Missing, duplicate, extra, retried, tag-only, stale, or
digest-mismatched evidence is a refusal.

The owner-approved spend ceiling is not a scientific result and not a public
economics claim. This campaign derives no dollar amount, ratio, multiplier,
annualization, wall-hour equivalent, or substitute economics.

Before any execution, v3 requires: immutable manifest/selector/preregistration
hashes in the registry; independent reviewer `ACCEPT`; the theorem landing gate;
a valid locked raw reference query, source pool, and materialized panel; exact
125-structure/500-cell cardinality; and dedicated job/image receipts. No model
output inspection, merge, deploy, or cloud dispatch is authorized by this
preregistration card.
