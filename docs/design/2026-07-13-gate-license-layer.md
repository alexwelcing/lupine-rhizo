# Gate license layer — design (2026-07-13)

> **Status:** DESIGN ONLY. No python is implemented by this document: the
> statics lane (`gates.py`, `run_elastic_baseline.py`, `build_class_corpus.py`,
> `migration.py`, `run_candidate_campaign.py`) is being edited concurrently by
> another team. Everything here is specified so implementation lands as a NEW
> module plus runner-side annotation, with zero edits to `gates.py`.
> **Companion (landed):** the capped in-hull correction theorems in
> `lean-spec/LupineEvidence/Shapes/Certificates.lean`
> (`capped_inhull_correction_helps_inflation` /
> `capped_inhull_correction_helps_deflation`), which are the Lean side of the
> same errata response.

## 1. Problem

The 2026-07-13 adversarial review (errata findings 4 and 6) established that a
concordance verdict does not automatically carry uncertainty content:

- **fcc B0 dispersion is ANTI-correlated with error** (Spearman rho = −0.63,
  n = 9): a "concordant" fcc B0 cell is, if anything, weak evidence of a
  *larger* error. B0 concordance was demoted to *descriptive* program-wide.
- **thresholds.v3's perovskite class was circular**: its rho = 1.0
  dispersion-error correlation was computed on the same five gated compounds,
  so it licenses nothing.
- Only **Born stability** (exact physics, needs no license) and **bcc a0**
  (rho = 0.89, n = 7) currently carry any empirical dispersion-error license.

Today this knowledge lives in prose notes (e.g.
`B0_CONCORDANCE_DESCRIPTIVE_NOTE` in `run_candidate_campaign.py`) and in
`data/discovery_gates/dispersion_vs_error_by_class.json`. The license layer
turns it into structured, versioned data that every report carries per verdict.

Orthogonality: `thresholds.v2/v3.json` say **where** the flag/refuse cuts sit
on the dispersion axis; the license registry says **what a zone means
epistemically** once a cell lands in it. A cell can be "concordant AND
descriptive": the arithmetic claim (models agree) stands, the uncertainty
claim (therefore the value is accurate) is not licensed.

## 2. The `GateLicense` runtime object

One immutable record per `(class, property)`, sourced from
`data/discovery_gates/dispersion_vs_error_by_class.json`
(schema `lupine.discovery_gates.dispersion_vs_error_by_class.v1`) via the
registry in §4. Lives in a NEW module `python/lupine_distill/statics/licenses.py`
(no `gates.py` edits; import surface mirrors `ConcordanceThresholds`).

```python
@dataclass(frozen=True)
class GateLicense:
    class_name: str            # e.g. "metals-bcc"
    property_name: str         # lowercase concordance key: "a0", "b0", "c11", ...
    status: str                # "licensed" | "descriptive" | "anti-correlated"
    rho: float | None          # Spearman rho as recorded; None if not computable
    n: int                     # materials in the dispersion-vs-error sample
    corpus: str                # evidence dir/report the rho was measured on
    corpus_kind: str           # "reference-bound" | "in-sample"
    caveats: tuple[str, ...]   # small-n warnings, model-family non-independence, ...
    registry: str              # registry path + schema + generated_at (provenance)
```

Status semantics (the registered derivation rule, constants in §4):

| status | rule | meaning in a report |
|---|---|---|
| `licensed` | rho ≥ +0.5 AND n ≥ 5 AND corpus_kind = reference-bound AND no program override | concordance level may be read as an uncertainty statement (low dispersion → empirically lower error, within the recorded rho/n) |
| `descriptive` | anything not meeting either other rule (\|rho\| < 0.5, or n < 5, or in-sample corpus, or program override) | concordance level is arithmetic about model agreement ONLY; no error claim |
| `anti-correlated` | rho ≤ −0.5 AND n ≥ 5 AND corpus_kind = reference-bound | low dispersion must NOT be read as low error; report carries an explicit warning |

`n ≥ 5` deliberately matches `_MIN_THRESHOLD_SAMPLES` in `gates.py`: below
five samples neither a threshold nor a license is a distribution statement.
Loading is fail-closed: a `(class, property)` absent from the registry gets
`descriptive` with caveat `"no license entry"`; schema id, status enum, rho
range [−1, 1], and n are validated at load and reject the file otherwise.

Current assignments implied by the 2026-07-13 data:

| class | property | rho | n | status | why |
|---|---|---|---|---|---|
| metals-fcc | a0 | +0.067 | 9 | descriptive | \|rho\| < 0.5 |
| metals-fcc | b0 | −0.633 | 9 | **anti-correlated** | rho ≤ −0.5, reference-bound (errata finding 4) |
| metals-bcc | a0 | +0.893 | 7 | **licensed** | the only positive license in the program today |
| metals-bcc | b0 | +0.321 | 7 | descriptive | \|rho\| < 0.5 (B0 ceiling also applies) |
| perovskites | a0 | −0.800 | 4 | descriptive | n < 5 (small_n_warning recorded; too small to certify even the negative) |
| perovskites | b0 | +1.000 | 5 | descriptive | corpus_kind = in-sample (errata finding 6 circularity) + B0 ceiling |

**B0 program-wide override (errata finding 4 / prereg fix 6):** the registry
carries `program_overrides` with a `license_ceiling: "descriptive"` on
property `b0` across ALL classes. A ceiling caps positive licensing only — it
can never erase an `anti-correlated` warning (fcc b0 stays anti-correlated;
the override just guarantees no class's B0 can be read as licensed until the
override is lifted by a registered decision).

## 3. Report annotation (`run_discovery_gates.py`, `run_candidate_campaign.py`)

The concordance **levels and verdict logic do not change**. In v1 the license
annotates; it never re-gates. (Making `anti-correlated` suppress or alter a
level would be an instrument change and belongs in a Round-4 registration,
not in this layer.)

Both runners, after building their per-property concordance gate dicts:

1. Load the registry once (path pinned by CLI flag, default
   `data/discovery_gates/licenses.v1.json`) and resolve the subject's
   calibration class (the campaign already maps structure type → class for
   bias selection; the discovery runner uses its thresholds class).
2. Attach to every concordance gate entry a `license` sub-object:

```json
"concordance": {
  "b0": {
    "gate": "concordance",
    "passed": true,
    "values": { "...": "unchanged GateVerdict fields" },
    "criteria": { "...": "unchanged" },
    "license": {
      "status": "anti-correlated",
      "rho": -0.633,
      "n": 9,
      "corpus": "data/y_matrix_runs/bound",
      "corpus_kind": "reference-bound",
      "source": "data/discovery_gates/licenses.v1.json"
    }
  }
}
```

3. Add one top-level `license_registry` block to the report (`path`,
   `schema`, `generated_at`, `derived_from`) so the report pins the registry
   version it used.
4. `REPORT.md`: the concordance table gains a `license` column; any
   `anti-correlated` cell adds a warning line under the table; the existing
   free-text `notes.b0_concordance_descriptive` in the campaign report is
   then GENERATED from the registry entries instead of hard-coded prose
   (the constant remains until this layer lands, then derives).
5. Verdict wording discipline: `CERTIFIED`/`FLAGGED`/`REFUSED` headlines in
   both runners append the license summary for the properties that drove
   them, e.g. `FLAGGED (b0 — descriptive: agreement arithmetic only, no
   uncertainty claim)`.

Implementation shape: pure functions in `licenses.py`
(`load_license_registry(path)`, `license_for(registry, class_name, prop)`,
`annotate_concordance(gates_dict, registry, class_name) -> new dict`) —
returning new dicts, never mutating verdicts; runner diffs are a few lines
each and touch no file the statics team is editing.

## 4. JSON registry format

`data/discovery_gates/licenses.v1.json` — generated by a (future) derivation
script from `dispersion_vs_error_by_class.json`, never hand-edited:

```json
{
  "schema": "lupine.discovery_gates.licenses.v1",
  "generated_at": "2026-07-13T...Z",
  "derived_from": {
    "path": "data/discovery_gates/dispersion_vs_error_by_class.json",
    "schema": "lupine.discovery_gates.dispersion_vs_error_by_class.v1",
    "generated_at": "2026-07-13T15:35:44.719143+00:00"
  },
  "derivation_rule": {
    "rho_metric": "spearman_rho_dispersion_vs_median_rel_error",
    "licensed_min_rho": 0.5,
    "anti_correlated_max_rho": -0.5,
    "n_min": 5,
    "corpus_kind_required_for_status": "reference-bound",
    "note": "descriptive is the fail-closed default for every other case"
  },
  "program_overrides": [
    {
      "property": "b0",
      "license_ceiling": "descriptive",
      "provenance": "2026-07-13 errata finding 4; Round-3 prereg fix 6 (fcc B0 rho=-0.63): B0 concordance descriptive program-wide",
      "lift_requires": "registered decision citing new reference-bound evidence"
    }
  ],
  "by_class": {
    "metals-bcc": {
      "a0": {
        "status": "licensed",
        "rho": 0.8928571428571429,
        "n": 7,
        "corpus": "data/y_matrix_runs/bound",
        "corpus_kind": "reference-bound",
        "caveats": [
          "n=7; 4 models with three non-independent MACE/CHGNet-era variants sharing training data"
        ]
      },
      "b0": { "status": "descriptive", "rho": 0.3214285714285715, "n": 7, "...": "..." }
    },
    "metals-fcc": { "...": "..." },
    "perovskites": {
      "a0": {
        "status": "descriptive",
        "rho": -0.7999999999999999,
        "n": 4,
        "corpus": "data/y_matrix_runs/bound",
        "corpus_kind": "reference-bound",
        "caveats": ["n=4 < 5: a single material determines the rank ordering"]
      },
      "b0": {
        "status": "descriptive",
        "rho": 0.9999999999999999,
        "n": 5,
        "corpus": "data/candidates/round1/report.json",
        "corpus_kind": "in-sample",
        "caveats": ["circular: rho computed on the gated candidates themselves (errata finding 6)"]
      }
    }
  }
}
```

Every entry records `rho` and `n` verbatim even when the status ignores them
(a `descriptive` perovskite b0 still shows its in-sample rho = 1.0 so the
reader sees exactly what was refused and why).

## 5. Update discipline

1. **Reference-bound corpora only.** A license status is (re)derived ONLY
   from corpora whose reference values are external and non-null
   (`data/y_matrix_runs/bound`, `class_corpus` dirs). NEVER from gated
   subjects: computing rho on the candidates a gate then judges is the
   errata-finding-6 circularity, and `corpus_kind: "in-sample"` exists
   precisely to record such data while barring it from conferring status.
2. **Immutable, versioned registries.** Rederivation writes
   `licenses.v2.json`, `v3`, ...; existing files are never mutated. Reports
   pin the registry version in `license_registry`, so an old report remains
   readable under the licenses it actually used.
3. **Upgrades are registered events.** `descriptive → licensed` requires an
   out-of-sample reference-bound corpus, n ≥ 5, rho ≥ +0.5, and the
   derivation registered (prereg- or errata-class doc) BEFORE the new corpus
   is measured. Downgrades (toward `descriptive`/`anti-correlated`) are
   fail-safe and may be applied as soon as evidence exists, with provenance.
4. **Overrides lift only by registered decision.** The B0 ceiling stays
   until a registered document cites new reference-bound evidence.
5. **Subjects can graduate.** A gated subject that later acquires external
   references may join a future corpus version; the registry entry documents
   the transition (it becomes reference-bound data from that version on).

## 6. Lean mirror shape (future `Shapes/Certificates.lean` addition)

Design only — NOT part of the 2026-07-13 Lean change (which added the capped
in-hull correction theorems). Same conventions as the rest of `Shapes`:
core-only, x10000 scaling, every predicate decidable.

```lean
/-- Empirical license status of one (class, property) concordance channel,
    mirroring lupine.discovery_gates.licenses.v1 statuses 1:1. -/
inductive LicenseTag where
  | licensed        -- reference-bound, n ≥ 5, rho ≥ +0.5, no ceiling
  | descriptive     -- agreement arithmetic only (fail-closed default)
  | antiCorrelated  -- low dispersion must NOT be read as low error
deriving Repr, DecidableEq

/-- A concordance window instance carrying its license evidence. -/
structure LicensedConcordanceWindow where
  window     : ConcordanceWindow
  tag        : LicenseTag
  rhoScaled  : Int   -- Spearman rho x10000, verbatim from the registry
  nMaterials : Nat
deriving Repr, DecidableEq

/-- Only a licensed tag bears uncertainty content. -/
def uncertaintyBearing (w : LicensedConcordanceWindow) : Prop :=
  w.tag = LicenseTag.licensed
```

Discipline the shape enforces: `outcome_trichotomy` and the migration laws
stay license-free (they certify arithmetic about zones and thresholds, and
say so). Any FUTURE theorem that concludes anything about *error* from a
dispersion zone must take `uncertaintyBearing w` as an explicit hypothesis —
so a generator emitting a Discovery instance for an fcc b0 cell (tag
`antiCorrelated`) can still kernel-check zone membership by `decide`, but
cannot instantiate an error claim at all. Generators fill `tag`/`rhoScaled`/
`nMaterials` from the same registry file the runners load, keeping the Lean
instances and the JSON reports pointwise consistent.

## 7. Non-goals

- No python in this change (statics lane files in flight elsewhere).
- No change to concordance levels, `overall_verdict`, `candidate_verdict`,
  or thresholds derivation — license annotates, never re-gates (v1).
- No new Lean structures yet; §6 is the registered shape for the follow-up.
- No retroactive relabeling of existing reports; the layer applies from the
  first registry version forward.
