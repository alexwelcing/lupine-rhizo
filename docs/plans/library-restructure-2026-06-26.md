# Lupine Library — Organization Audit & Restructure Plan

**Author:** synthesizer profile
**Date:** 2026-06-26
**Status:** Proposal — awaiting human approval before implementation
**Scope:** `library.lupine.science` (61 articles, 13 categories, 2 languages)

---

## 0. Executive summary

The library has grown to 61 articles organically, and the home page now front-loads **twelve promoted items** (3 hard-coded banners + 9 featured callouts) before the first category shelf. A first-time visitor scrolling the landing page sees a wall of equally-weighted "Featured" boxes with no indication of where to start, what is settled versus open, or how the corpus fits together.

This plan proposes:

1. **Consolidate 13 categories → 8** by merging the three overlapping orientation buckets (`meta` / `foundations` / `decisions`) and folding the four sub-3-article categories (`references`, `ecosystem`, `reviews`, `partnerships`) into coherent neighbors.
2. **Add a "Start Here" guided-journey layer** — not a new shelf, but curated reading paths for four reader personas, surfaced above the shelves.
3. **Cap featured at 4** and give each a defined role (anchor, newest result, counter-example, replication kit) instead of the current undifferentiated stack of 9.
4. **Promote the status facet to a first-class navigation axis** with a one-line gloss so "Supported vs. Live vs. Refuted" is legible to newcomers.
5. **Governance rules** for `featured`, `status`, `group`, and the intake checklist that prevents regression to chaos.

URL stability is preserved: no article `id` changes. The taxonomy change is a `category` field reassignment in `library-content-catalog.js`, exported through the existing `export_library_content.mjs` pipeline.

---

## 1. Audit of the current corpus

### 1.1 Inventory by category (n = 61)

| Category | n | Notes |
|---|---|---|
| `validation` | 10 | Largest, healthiest. Includes the 4 new Round-2 MatPES articles. |
| `conjectures` | 9 | Well-governed: every entry has a `status` and `group: hypotheses`. |
| `changelog` | 8 | Narrative spine, but mixes paper announcements with build updates. |
| `foundations` | 7 | Overlaps with `meta`. `methodology` belongs with the methods cluster. |
| `meta` | 6 | 3 of 6 are extraction logs (`extraction-complete/report/notes`) — build provenance, not reader content. |
| `uq` | 5 | Methodological. Natural pair with `theory`. |
| `formalization` | 5 | Coherent Lean/formal-spec cluster. |
| `theory` | 4 | Methodological. Natural pair with `uq`. |
| `reviews` | 2 | Too thin to stand alone. |
| `references` | 2 | Too thin to stand alone. |
| `decisions` | 1 | Single ADR. |
| `partnerships` | 1 | Single article. |
| `ecosystem` | 1 | Single funding-landscape article. |

### 1.2 Structural problems observed

**P1 — Three-way orientation overlap.** `foundations`, `meta`, and `changelog` all claim to be "start here" / "how this works." A newcomer cannot tell which to read first. Specifically:
- `public-approach` (changelog) describes corpus organization — that is a foundations topic.
- `operating-system` and `resource-fabric` (meta) describe how the system works — foundations-adjacent.
- The extraction trilogy (`extraction-complete/report/notes`, meta) is build provenance, not science.

**P2 — Four singleton-or-pair categories.** `decisions` (1), `partnerships` (1), `ecosystem` (1), `references` (2), `reviews` (2) each occupy a full shelf header for almost no content. Five shelves for 7 articles is shelf-header noise.

**P3 — Methods are split across three shelves.** `theory` (4), `uq` (5), and the `methodology` article (foundations) are all "how we measure and bound error." A reader interested in the methodological core must visit three shelves.

**P4 — Featured inflation.** 9 of 61 articles (15 %) are `featured: true`. The home page renders all 9 as full-width callout boxes before any shelf. Combined with the 3 hard-coded banners (preprint, interactive report, live lab), the top of the page is **12 promoted tiles** with no hierarchy.

**P5 — No guided entry.** There is no "Start Here" path. The status filter exists but is unlabeled — a newcomer sees `Supported · 8` with no explanation of what "Supported" means relative to "Proven (Lean)."

**P6 — `group` is underused.** Only the `conjectures` entries and `formal-proof-ledger` use `group: hypotheses`. The 7 validation articles that form the "MLIP flywheel" arc (`mlip-cloud-baseline-distill`, `mlip-ni-paired-accuracy-live`, `mlip-ni-zero-point-policy-replay`, `mlip-mptrj-broad-dft-canary`, `projection-law-round2-*`, `layer2-*`) are not grouped, so their narrative sequence is invisible.

---

## 2. Proposed taxonomy (13 → 8 categories)

All article `id`s are preserved. Only the `category` field changes. Migration is a single edit pass in `library-content-catalog.js`.

### 2.1 New category definitions

| # | Category ID | Label (en) | n | Blurb |
|---|---|---|---|---|
| 1 | `foundations` | **Foundations & Vision** | 7 | Orientation, shared vocabulary, data provenance, and the research agenda. Start here if you are new. |
| 2 | `conjectures` | **Conjectures & Proofs** | 9 | Every claim we have tested, its lifecycle status, and the evidence behind it. The hypothesis ledger. |
| 3 | `methods` | **Methods & Theory** | 10 | How we measure, bound, and reason about potential error — from sloppy-model geometry to Bayesian active learning. |
| 4 | `validation` | **Validation & Evidence** | 10 | Benchmarks, live-lab results, and the MLIP flywheel evidence chain. |
| 5 | `formalization` | **Formalization** | 5 | Lean-backed theorem proofs, build-locking contracts, and the formal proof ledger. |
| 6 | `changelog` | **Progress Log** | 7 | What changed, why, and what is next. The narrative spine of the project. |
| 7 | `references` | **Reviews & References** | 5 | External literature lineage, funding landscape, and adversarial peer reviews. |
| 8 | `operations` | **Build & Operations** | 8 | How this library was built and how to reproduce every result. Extraction logs, ADRs, and infrastructure. |

**Total: 61** (reconciled)

### 2.2 Full article-to-category migration map

Legend: `id` — *current category* → *new category*. `=` means unchanged.

#### `foundations` → Foundations & Vision (7)
| ID | Change | Rationale |
|---|---|---|
| `readme` | = | Project entry point. |
| `glossary` | = | Shared vocabulary. |
| `research-index` | = | Document catalog. |
| `navigation` | = | Repo codemap. |
| `data-provenance` | = | Source-of-truth for every number. |
| `internal-science-program` | = | Research agenda. |
| `public-approach` | `changelog` → `foundations` | This *is* the corpus-organization manifesto; it belongs with foundations, not the progress log. |

#### `conjectures` → Conjectures & Proofs (9, unchanged)
`conjecture-ledger`, `hyp-hyper-ribbon-universality`, `hyp-hyper-ribbon-mlip-transfer`, `hyp-cross-mlip-orthogonal-errors`, `hyp-au-mlip-escape`, `hyp-fe-persistent-outlier`, `hyp-dband-correlation`, `hyp-meam-intrinsic-2d`, `hyp-bccfcc-causal-shield`. No changes — this shelf is the best-governed part of the corpus.

#### `methods` → Methods & Theory (10) — **new category, merges theory + uq + methodology**
| ID | From | Rationale |
|---|---|---|
| `methodology` | `foundations` | Matched-n, contamination gating — this is method, not orientation. |
| `rg-coarsegraining` | `theory` | = |
| `sloppy-models` | `theory` | = |
| `error-geometry-objects` | `theory` | = |
| `info-theoretic` | `theory` | = |
| `glimmer-multifidelity-uq` | `uq` | = |
| `bayesian-active-learning` | `uq` | = |
| `weather-climate-ensembles` | `uq` | = |
| `gnn-error-prediction` | `uq` | = |
| `tda-error-landscapes` | `uq` | = |

**Blurb:** *Coarse-graining, sloppy-model geometry, Fisher information, Bayesian active learning, and topological data analysis — the methodological core of how we bound and predict potential error.*

**Suggested internal order** (theory-first, so a reader descends from abstraction to application):
1. `error-geometry-objects` — disambiguates the three objects.
2. `sloppy-models` — Fisher-information eigenvalue analysis.
3. `rg-coarsegraining` — systematic coarse-graining.
4. `info-theoretic` — Kolmogorov/Shannon bounds.
5. `methodology` — the reusable experimental discipline.
6. `glimmer-multifidelity-uq` — cross-potential meta-analysis.
7. `bayesian-active-learning` — GP surrogates for potential selection.
8. `weather-climate-ensembles` — ensemble transfer from climate science.
9. `gnn-error-prediction` — structure-topology error prediction.
10. `tda-error-landscapes` — persistent homology of error surfaces.

#### `validation` → Validation & Evidence (10, unchanged)
All 10 stay. See §2.3 for the `group` additions that surface the flywheel arc.

#### `formalization` → Formalization (5, unchanged)
`formal-vision`, `formal-methodology`, `formal-audit`, `formal-hypotheses`, `formal-proof-ledger`.

#### `changelog` → Progress Log (7)
| ID | Change | Rationale |
|---|---|---|
| `changelog` | = | Master changelog. |
| `working-papers` | = | Paper-suite announcement. |
| `research-evolution` | = | Self-correction narrative. |
| `phoenix-observability` | = | Observability build update. |
| `mlip-flywheel-readiness` | = | Flywheel readiness gate. |
| `born-screening-re-audit` | = | Public correction. |
| `foundation-model-trust-layers` | = | Next-round target memo. |

(`public-approach` moves to foundations.)

#### `references` → Reviews & References (5) — **merges reviews + references + ecosystem**
| ID | From | Rationale |
|---|---|---|
| `references` | `references` | External literature lineage (35 works). |
| `lit-review-error-structure` | `references` | 30-reference synthesis. |
| `academic-review-projection-law` | `reviews` | Adversarial academic review. |
| `adversarial-review-projection-law` | `reviews` | Second-pass review. |
| `funding-landscape` | `ecosystem` | Federal funding landscape — the "who funds this" context. |

**Blurb:** *The literature we build on, the funding context, and the adversarial reviews our claims passed before going public.*

#### `operations` → Build & Operations (8) — **new category, merges meta + decisions + partnerships**
| ID | From | Rationale |
|---|---|---|
| `operating-system` | `meta` | How the loop fits together. |
| `resource-fabric` | `meta` | Infrastructure fabric. |
| `reproduce` | `meta` | Reproduction commands. |
| `extraction-complete` | `meta` | Build provenance. |
| `extraction-report` | `meta` | Build provenance. |
| `extraction-notes` | `meta` | Build provenance. |
| `adr-0001-storage` | `decisions` | Architecture decision record. |
| `partnerships` | `partnerships` | Pilot/alignment — public layer. |

**Blurb:** *How this library was built, how to reproduce every claim, and the infrastructure behind it. Extraction logs, ADRs, and operational fabric.*

### 2.3 Categories removed

| Removed category | n | Absorbed into |
|---|---|---|
| `meta` | 6 | `operations` (6) |
| `theory` | 4 | `methods` (4) |
| `uq` | 5 | `methods` (5) |
| `decisions` | 1 | `operations` (1) |
| `partnerships` | 1 | `operations` (1) |
| `ecosystem` | 1 | `references` (1) |
| `reviews` | 2 | `references` (2) |

**Net: 13 → 8 categories.** No article is deleted. No `id` changes.

---

## 3. Reader journeys

Four personas, each a curated sequence surfaced on the home page as a "path" card. These are **not** new shelves — they are ordered reading lists that pull from multiple categories.

### 3.1 Path A — "I'm new here" (New visitor, ~20 min)

Goal: understand what Lupine is, what it claims, and why it matters, without drowning in methods.

1. `readme` (foundations) — *What is the error-geometry program?*
2. `glossary` (foundations) — *Vocabulary reference (skim).*
3. `error-geometry-objects` (methods) — *The three objects, disambiguated.*
4. `conjecture-ledger` (conjectures) — *Every claim at a glance, with status.*
5. `hyp-hyper-ribbon-universality` (conjectures) — *The flagship supported claim.*
6. `mlip-cloud-baseline-distill` (validation) — *Concrete evidence: first 5×5 results.*
7. `research-evolution` (changelog) — *How the loop caught its own errors.*

**Kill condition for the journey:** if a reader finishes items 1–4 and cannot state what "the hyper-ribbon" is, the foundations shelf has failed and needs rewriting.

### 3.2 Path B — "Show me the physics" (Materials scientist)

Goal: evaluate the scientific claims against the evidence.

1. `data-provenance` (foundations) — *Where every number comes from.*
2. `sloppy-models` (methods) — *Fisher-information geometry.*
3. `error-geometry-objects` (methods) — *Manifold vs. PR measure vs. core.*
4. `hyp-hyper-ribbon-universality` (conjectures) — *PR 1.05–1.86 claim.*
5. `hyp-cross-mlip-orthogonal-errors` (conjectures) — *Ensemble precondition.*
6. `projection-law-round2-results` (validation) — *16-element MatPES benchmark.*
7. `layer2-research-paper` (validation) — *Draft paper with full methods.*
8. `academic-review-projection-law` (references) — *Adversarial review of the above.*
9. `references` (references) — *35-work literature lineage.*

### 3.3 Path C — "I build MLIPs" (MLIP builder / practitioner)

Goal: understand the flywheel, the correction operator, and how to use the validation infrastructure.

1. `working-papers` (changelog) — *The projection-law paper suite.*
2. `mlip-cloud-baseline-distill` (validation) — *5×5 baseline + first Distill wins.*
3. `mlip-ni-paired-accuracy-live` (validation) — *Ni fcc paired-accuracy evidence.*
4. `mlip-mptrj-broad-dft-canary` (validation) — *MPtrj broad-DFT results.*
5. `projection-law-round2-preregistration` (validation) — *Pre-registered protocol.*
6. `projection-law-round2-results` (validation) — *The correction operator on MatPES.*
7. `bayesian-active-learning` (methods) — *GP surrogates for potential selection.*
8. `gnn-error-prediction` (methods) — *Predicting failure from crystal topology.*
9. `reproduce` (operations) — *How to regenerate every result.*

### 3.4 Path D — "Is this rigorous?" (Funder / reviewer / program manager)

Goal: assess epistemic discipline, self-correction culture, and formal backing.

1. `internal-science-program` (foundations) — *The research agenda.*
2. `methodology` (methods) — *Matched-n, contamination gating, stratification.*
3. `conjecture-ledger` (conjectures) — *2 refuted + 2 self-corrected = we falsify our own claims.*
4. `hyp-dband-correlation` (conjectures) — *A refuted claim (sample-size confounder).*
5. `hyp-bccfcc-causal-shield` (conjectures) — *A self-corrected claim (1.5 % contamination).*
6. `formal-proof-ledger` (formalization) — *Which claims have Lean proofs.*
7. `formal-audit` (formalization) — *Split verdict on Simpson's paradox vs. hyper-ribbon.*
8. `funding-landscape` (references) — *Where this sits in the federal landscape.*
9. `phoenix-observability` (changelog) — *The research loop is observable.*

---

## 4. Home-page structure

### 4.1 Current problems (measured from the live DOM)

The current `renderHome()` in `lupine-ledger/src/app.js:175` emits, in order:
1. Hero (title + 3 stats) — *fine.*
2. Preprint banner — hard-coded HTML.
3. Interactive theorem-report banner — hard-coded, 6 sub-links.
4. Live Lab banner — hard-coded.
5. **9 featured callouts** — all `featured: true` entries, full-width, undifferentiated.
6. Continue-reading (only if progress exists).
7. Status filter chips (8 chips, unlabeled).
8. 13 category shelves.

**Total promoted surface before the first shelf: 12 tiles.** On mobile this is roughly 12 screen-heights of equally-weighted boxes.

### 4.2 Proposed structure (top to bottom)

```
┌─────────────────────────────────────────────┐
│ HERO                                         │
│  Title · 3 stats · 1-line "what is this"    │
│  [EN | 中文] toggle top-right                │
├─────────────────────────────────────────────┤
│ START HERE — guided journeys                 │
│  4 path cards (compact, side-scroll on mob): │
│  [New here] [Physicist] [MLIP builder]      │
│  [Funder/reviewer]                           │
│  Each card: persona label + 1-line desc +   │
│  arrow into the first article of the path.   │
├─────────────────────────────────────────────┤
│ FEATURED (max 4, curated roles)              │
│  [Anchor result] [Newest evidence]           │
│  [Counter-example / self-correction]         │
│  [Replication kit / paper]                   │
├─────────────────────────────────────────────┤
│ STATUS FILTER (with 1-line gloss)            │
│  All · 61 | Supported · 8 | Live · 2 |       │
│  Open · 6 | Proven · 1 | Proposed · 1 |      │
│  Self-corrected · 2 | Refuted · 2            │
│  └ gloss line: "Supported = evidence-backed; │
│     Live = continuously refreshed;           │
│     Refuted = we falsified our own claim"    │
├─────────────────────────────────────────────┤
│ SHELVES (8 categories, new taxonomy)         │
│  Each shelf: H2 + blurb + card grid          │
│  Cards show: title, subtitle, status badge,  │
│  read-time, tags. Group-ribbon on flywheel.  │
├─────────────────────────────────────────────┤
│ FOOTER                                       │
│  Reproduce link · License · Last-updated     │
└─────────────────────────────────────────────┘
```

### 4.3 Specific changes to `renderHome()`

| Change | Current | Proposed | Location |
|---|---|---|---|
| Hard-coded preprint banner | Full-width callout | Fold into Featured "Anchor" slot OR keep as a thin dismissible ribbon. Remove from renderHome; move to a `banners` config array. | `app.js:199–206` |
| Hard-coded report banner (6 sub-links) | Full-width + 6 links | Move to a dedicated `#/reports` route; link from the hero or a single "Interactive demos" card. | `app.js:208–224` |
| Hard-coded Live Lab banner | Full-width callout | Keep, but restyle as the Featured "Newest evidence" slot with explicit role. | `app.js:226–234` |
| Featured loop | Renders all 9 `featured:true` | Cap at 4; require a `featuredRole` field (`anchor` / `newest` / `counter` / `replication`) to differentiate. | `app.js:236–247` |
| Status filter | 8 unlabeled chips | Add a gloss `<p>` below the chips explaining the lifecycle. | `app.js:266–288` |
| Shelves | 13 categories | 8 categories (new taxonomy). | `app.js:290–302` |
| **New: Start Here section** | Does not exist | Insert between hero and featured. 4 path cards driven by a `journeys` config in the catalog. | New code block |
| Group ribbon | Not rendered | If articles in a shelf share a `group`, render a thin labeled connector ("MLIP Flywheel arc →") above them. | New code block |

### 4.4 The `journeys` and `featuredRole` additions to the catalog

These are **optional fields** on catalog entries. The export pipeline already clones arbitrary fields (`cloneJson`), so no schema change is needed — only additions to `library-content-catalog.js`.

```js
// New top-level catalog key:
journeys: [
  { id: 'new-here', label: { en: "I'm new here", zh: '初次访问' },
    description: { en: 'Start with the big picture.', zh: '从全局开始。' },
    path: ['readme','glossary','error-geometry-objects','conjecture-ledger', ...] },
  // ...3 more (see §3)
],

// New optional field on entries:
// featuredRole: 'anchor' | 'newest' | 'counter' | 'replication'
```

---

## 5. Governance rules

### 5.1 `featured` — when an article gets promoted

**Rule: maximum 4 featured articles at any time.** Each must carry a `featuredRole`:

| Role | Meaning | Example |
|---|---|---|
| `anchor` | The single most important result a visitor should see. | `projection-law-round2-results` |
| `newest` | The most recent evidence update (rotates). | `layer2-research-paper` |
| `counter` | A self-correction or refutation — shows epistemic honesty. | `born-screening-re-audit` |
| `replication` | The paper / replication kit entry point. | `working-papers` |

When a new article is featured, the maintainer must **demote** the previous holder of that role. Featured status is reviewed at every release (see `docs/release-checklist.md`).

**Current state:** 9 featured. Target: 4. The 5 to demote: `phoenix-observability`, `mlip-cloud-baseline-distill`, `mlip-ni-paired-accuracy-live`, `mlip-ni-zero-point-policy-replay`, `mlip-mptrj-broad-dft-canary`. These remain in their shelves and in the flywheel `group`; they just lose the home-page callout.

### 5.2 `status` — lifecycle taxonomy

The existing 7-value taxonomy is sound and should be kept. The fix is **legibility**, not restructuring:

| Status | Definition (to add as a gloss) | Count |
|---|---|---|
| `proposed` | A conjecture we intend to test; no evidence yet. | 1 |
| `supported` | Evidence-backed but not formally proven. | 8 |
| `open` | Under active investigation; could go either way. | 6 |
| `refuted` | We tested it and falsified it ourselves. | 2 |
| `self-corrected` | We published it, then found a confounder and retracted the strong form. | 2 |
| `proven` | Backed by a machine-checked Lean proof. | 1 |
| `live` | Continuously refreshed evidence (live-lab canary). | 2 |

Add these definitions to `catalog.statuses` as a `gloss` sub-field and render them in the status-filter gloss line.

### 5.3 `group` — narrative arcs

Currently only `conjectures` uses `group: hypotheses`. Extend to:

| Group ID | Articles | Purpose |
|---|---|---|
| `hypotheses` | 9 conjectures + `formal-proof-ledger` | Existing. |
| `mlip-flywheel` | `mlip-cloud-baseline-distill`, `mlip-ni-paired-accuracy-live`, `mlip-ni-zero-point-policy-replay`, `mlip-mptrj-broad-dft-canary`, `projection-law-round2-results`, `layer2-research-paper` | Surface the flywheel arc on the validation shelf. |
| `extraction` | `extraction-complete`, `extraction-report`, `extraction-notes` | Collapse the three build-provenance logs into a single expandable on the operations shelf. |

### 5.4 Intake checklist (new article)

Before a new article is added to the catalog:

- [ ] Stable `id` that will never change (URL contract).
- [ ] `source` path exists in the repo and is committed.
- [ ] `category` matches one of the 8 (not a new category without team approval).
- [ ] `status` set to one of the 7 lifecycle values; `proposed` if unsure.
- [ ] If `featured: true`, a `featuredRole` is assigned and the previous holder is demoted.
- [ ] Title and subtitle are bilingual (`en` / `zh`) if the article has i18n variants.
- [ ] If the article is part of an arc, assign a `group`.
- [ ] `npm run content:verify` passes locally.
- [ ] The article is mentioned in the next `CHANGELOG.md` entry.

---

## 6. Gap analysis

Content that is missing or needs rewriting to make the library self-contained.

### 6.1 Missing content

| Gap | Priority | Why it matters | Suggested assignee |
|---|---|---|---|
| **No "What is an interatomic potential?" primer** | High | A newcomer hitting `glossary` sees jargon (EAM, MLIP, DFT) with no gentle on-ramp. Path A needs this as item 0. | `researcher` |
| **No plain-language summary of the projection law** | High | The flagship result (`projection-law-round2-results`) is dense. A 300-word "what this means for a materials scientist" box is needed. | `synthesizer` |
| **No i18n (zh) for any article body** | Medium | The UI chrome is bilingual but all 61 article bodies are English-only. The `zh` audience gets a half-translated experience. Either commit to body translation or remove the language toggle from article view. | `researcher` |
| **No data-availability statement per article** | Medium | Each validation article should link to its raw JSON (several exist under `src/reports/assets/mlip/`). | `researcher` |
| **`mlip-flywheel-readiness` has no successor** | Low | It says "ready for scientist review before the next Distill campaign" — the outcome of that review is not captured. | `researcher` |
| **The three extraction logs are redundant** | Low | `extraction-complete`, `extraction-report`, `extraction-notes` overlap heavily. Consolidate into one with the others as tabs/sections. | `synthesizer` |

### 6.2 Rewriting needed

| Article | Issue | Fix |
|---|---|---|
| `public-approach` | Currently in `changelog`; describes the corpus model. | Rewrite subtitle to emphasize it as a foundations document; move to `foundations`. |
| `operating-system` | Title says "GLIM Operating System" — stale brand. | Update to "Lupine Operating System" or "Research Loop Architecture". |
| `resource-fabric` | Same stale "GLIM" brand. | Rename to "Infrastructure Fabric". |
| `born-screening-re-audit` | Strong article, but its `featured` role should be `counter` (self-correction showcase), not generic featured. | Add `featuredRole: 'counter'`. |
| Category blurbs | Inconsistent scope (some describe method, some describe audience). | Standardize all 8 blurbs to the pattern: "[What this shelf contains]. [Who should read it]." |

### 6.3 What is already strong (do not break)

- **The conjectures shelf** is exemplary: every entry has `status` and `group`. This is the template for the rest of the corpus.
- **The status taxonomy** is well-designed and should be kept; only its presentation needs work.
- **The content-contract / export pipeline** (`export_library_content.mjs` → `content/latest/manifest.json` → `app.js`) is clean and should not be re-architected. The taxonomy change is a data edit, not a pipeline change.
- **The Round-2 MatPES articles** (`projection-law-round2-preregistration`, `projection-law-round2-results`, `layer2-supercell-evaluation`, `layer2-research-paper`) form a tight, well-sequenced evidence chain. Assign `group: mlip-flywheel`.

---

## 7. Implementation backlog (kanban tickets)

The following child tickets should be created on the `lupine` board under this planning card. Each is scoped so it can be picked up independently.

### 7.1 Content / catalog changes (route to `researcher` or `synthesizer`)

| Ticket | Assignee | Depends on |
|---|---|---|
| **T1: Apply the 8-category taxonomy** — reassign `category` fields for the 22 articles that move; add the `methods` and `operations` category definitions; remove the 5 merged categories. Single PR against `lupine-rhizo/scripts/library-content-catalog.js`. | `synthesizer` | — |
| **T2: Add `group` fields** — `mlip-flywheel` (6 articles) and `extraction` (3 articles). | `synthesizer` | T1 |
| **T3: Add status glosses** — add `gloss` sub-field to each of the 7 statuses in the catalog. | `synthesizer` | — |
| **T4: Demote 5 featured articles, add `featuredRole` to the remaining 4.** | `synthesizer` | T1 |
| **T5: Write the `journeys` config** — 4 persona paths as a top-level catalog key. | `synthesizer` | T1 |
| **T6: Rewrite category blurbs** — standardize all 8 to the "[contents]. [audience]." pattern, bilingual. | `synthesizer` | T1 |
| **T7: Write "What is an interatomic potential?" primer** (new article, Path A item 0). | `researcher` | — |
| **T8: Write plain-language projection-law summary box** (300 words). | `synthesizer` | — |
| **T9: De-brand "GLIM" → "Lupine"** in `operating-system` and `resource-fabric` titles/subtitles. | `synthesizer` | — |
| **T10: Consolidate the three extraction logs** into one expandable. | `synthesizer` | T2 |

### 7.2 Frontend / rendering changes (route to `software-engineer`)

| Ticket | Assignee | Depends on |
|---|---|---|
| **F1: Add "Start Here" journeys section** to `renderHome()` — render the `journeys` config as 4 compact path cards between hero and featured. | `software-engineer` | T5 |
| **F2: Cap featured at 4 and render `featuredRole` labels.** | `software-engineer` | T4 |
| **F3: Extract hard-coded banners** (preprint, report, live-lab) into a config array; remove from `renderHome` body. | `software-engineer` | — |
| **F4: Add status-gloss line** below the filter chips. | `software-engineer` | T3 |
| **F5: Render `group` ribbons** on shelves (thin labeled connector above grouped articles). | `software-engineer` | T2 |
| **F6: Add `#/reports` route** for the interactive theorem demos (currently hard-coded 6-link banner). | `software-engineer` | F3 |

### 7.3 Build / pipeline (route to `devops`)

| Ticket | Assignee | Depends on |
|---|---|---|
| **D1: Re-export the content bundle** (`npm run content:export` in `lupine-rhizo`, sync to `lupine-ledger/content/latest`). | `devops` | T1–T6 |
| **D2: Verify the bundle** (`npm run content:verify` in `lupine-ledger`) and run `npm run build`. | `devops` | D1 |
| **D3: Deploy** to `library.lupine.science` and smoke-test all 61 `#/read/<id>` URLs resolve. | `devops` | D2, F1–F6 |

### 7.4 Visual QA (route to `visual-tester`)

| Ticket | Assignee | Depends on |
|---|---|---|
| **V1: Visual regression of the new home page** — verify the journeys section, capped featured, status gloss, and group ribbons render correctly on mobile (375px) and desktop (1280px). Check both `en` and `zh` locales. | `visual-tester` | D3 |

### 7.5 Dependency graph

```
T1 (taxonomy) ─┬─ T2 (groups) ────── F5 (group ribbons)
               ├─ T4 (featured) ──── F2 (featured cap)
               ├─ T5 (journeys) ──── F1 (start here)
               ├─ T6 (blurbs)
               └─ T3 (gloss) ── T2 ── F4 (status gloss)

T7, T8, T9, T10 (independent content)

F3 (banner extraction) ── F6 (reports route)

All T* + F* ── D1 (re-export) ── D2 (verify) ── D3 (deploy) ── V1 (visual QA)
```

**Critical path:** T1 → T5 → F1 → D1 → D2 → D3 → V1.

---

## 8. Risk and rollback

| Risk | Mitigation |
|---|---|
| **Broken `#/read/<id>` URLs** | No `id` changes. The taxonomy edit is `category`-field-only. Verified by the URL smoke-test in D3. |
| **Status filter breaks** | The 7 statuses are unchanged; only a `gloss` sub-field is added. `app.js:268` reads `m.statuses` which will include the new field transparently. |
| **i18n regression** | All new fields (`gloss`, `featuredRole`, `journeys`) use the existing `{en, zh}` pattern. |
| **Rollback** | The taxonomy change is a single commit in `library-content-catalog.js`. Revert + re-export to roll back. |

---

## 9. Files touched

| File | Change | Repo |
|---|---|---|
| `scripts/library-content-catalog.js` | Category reassignment (22 entries), new category defs, `group` fields, `featuredRole`, `gloss`, `journeys`, blurb rewrites | `lupine-rhizo` |
| `src/app.js` | New journeys section, featured cap, banner extraction, status gloss, group ribbons, reports route | `lupine-ledger` |
| `src/i18n.js` | Journey labels and status gloss strings (en + zh) | `lupine-ledger` |
| `src/styles.css` | Journey-card, group-ribbon, and status-gloss styles | `lupine-ledger` |
| `content/latest/manifest.json` | Regenerated by export pipeline | `lupine-ledger` |
| New article(s) | Primer, projection-law summary | `lupine-rhizo/docs/` |

---

*End of plan. See §7 for the kanban ticket breakdown.*
