# CocoIndex in the Lupine Research Stack: Evaluation, Measurement, and Improvement

**Status:** demonstration write-up, 2026-07-06; §9 (published Library, ledger deploy-truth, drift) + §10 (retrieval upgrades: bge-small, hybrid BM25+vector, Phoenix traces, automation, tier architecture), 2026-07-07
**Source of truth:** `lupine-rhizo/cocoindex/` (pipeline), `lupine-rhizo/docs/rfc-omnigents-cocoindex.md` (design RFC)
**Audience:** Lupine Science readers; anyone deciding whether an incremental indexing framework earns its place in a research workflow

---

## 1. Summary

Lupine's research control plane produces evidence continuously: multi-model
coordination traces, hypotheses with changing statuses, benchmark claims, and
a living markdown corpus of ~150 research documents. We use
[CocoIndex](https://cocoindex.io) — an open-source incremental data-indexing
framework — to keep a semantic search index over all of it current without
ever re-embedding what didn't change.

This write-up documents a full evaluation pass over that usage: what the
pipeline did before, what we measured, what we improved, and the numbers
after. Headline results, all measured on real runs (CPU-only, 384-dim
all-MiniLM-L6-v2 embeddings):

| Measurement | Result |
| --- | --- |
| Cold build: 151 sources → 1,672 chunks | 45 s |
| Re-run, nothing changed | **0.1 s** |
| Re-run, one document edited | ~7 s, re-embeds only that file (`1 reprocessed, 147 unchanged`) |
| Semantic retrieval (gold set, MRR) | **0.59** vs 0.16 for keyword LIKE |
| Semantic + kind filter (MRR) | **0.85** (hit@1 = 0.80) |
| KNN search latency (vec0 sidecar) | 1.0 ms vs 11.3 ms brute-force (~11×) |

The incremental property is the whole argument for CocoIndex over a one-shot
embedding script: the corpus changes daily, and the index now costs seconds a
day to keep live instead of a full re-embed.

## 2. What CocoIndex is doing for us

CocoIndex is a declarative dataflow framework: you define *sources* (files,
tables), *transforms* (chunking, embedding), and *targets* (here, SQLite with
a vector column), and the engine handles the bookkeeping — content
fingerprinting, memoization, and live re-processing — so a re-run only does
the work that changed. Our app (`cocoindex/main.py`, ~250 lines) declares:

```
./data/*.jsonl   ──▶ process_file     ─┐
(ledger evidence)    (memo=True)       ├─▶ RecursiveSplitter ──▶ per-chunk embed ──▶ evidence.db ──▶ vec0 KNN sidecar
docs/**/*.md     ──▶ process_doc_file ─┘   (1000/200 tokens,     (all-MiniLM-L6)     (float[384])
root *.md            (memo=True)            markdown-aware)
```

Two source families feed one table, `evidence_chunks(id, source_file, kind,
ref_id, text, embedding, chunk_start, chunk_end)`:

- **Ledger evidence** (`kind` ∈ `coordination_trace | hypothesis | claim |
  research_question`): JSONL exported from the glim-think D1 ledger — the
  Cloudflare worker that runs multi-model coordination writes a trace row per
  call (`coordinatorTraces.ts`), and research agents write hypotheses and
  claims. `export_evidence.py` / `scripts/evidence_activation.py` are the
  wire.
- **Research corpus** (`kind = document`, *added in this pass*): the repo's
  markdown — `docs/**/*.md` plus root-level `*.md`, 148 files, ~1.1 MB of
  prose — chunked markdown-aware, with the repo-relative path as the stable
  `ref_id`.

One semantic query therefore spans *what the agents did* (traces), *what the
program believes* (hypotheses, claims), and *what the humans wrote* (docs).

### Where it sits in the architecture

The Python/Workers boundary is real: Cloudflare Workers cannot run the
embedder or sqlite-vec, so the layers split by runtime and the same record
schema flows through all three:

| Layer | Runtime | Role |
| --- | --- | --- |
| glim-think worker | TypeScript / Cloudflare | *Produces* evidence → D1; `GET /evidence/recent` for a live non-vector view |
| **cocoindex** (this) | Python, local/scheduled | *Indexes* evidence + corpus → `evidence.db`; `query.py` serves semantic search |
| gcp/evidence-index | Python / Cloud Run | Always-warm live index (Postgres + pgvector) the coordinator consults mid-request |

## 3. What we evaluated, and what we found

We ran the v1 pipeline end-to-end, read every integration point, and audited
promise-vs-reality. Five findings drove the work:

1. **The fast path never fired.** `query.py` had a code path for a sqlite-vec
   `vec0` KNN table, but nothing ever created that table — CocoIndex's SQLite
   connector writes the vector column only. Every semantic query silently
   fell back to brute-force cosine over all rows.
2. **The corpus was missing.** The index covered only ledger evidence
   (6 seed records in dev). The 148-file markdown research corpus — the
   densest retrieval target in the repo — wasn't indexed, despite the repo
   positioning the tier as "corpus export/query loops."
3. **Nothing measured retrieval quality.** There was no way to answer "does
   semantic search actually beat keyword here?" with a number.
4. **No CI.** Neither the pipeline's tests nor the evidence service's ran in
   any workflow or verify gate.
5. **Doc drift.** The README used Windows-only venv paths and claimed the
   vec0 table existed; the RFC's "Hermes skill wraps the index" was
   aspirational.

## 4. What we changed

All changes are in `lupine-rhizo` branch `claude/coco-index-optimization-fvozz0`.

### 4.1 Indexed the research corpus (`main.py`)

A second memoized processor, `process_doc_file`, mounts `docs/**/*.md` and
root `*.md` as `kind="document"` rows, chunked with the splitter's
markdown-aware mode so chunks break on headings and offsets stay valid.
`EVIDENCE_INDEX_CORPUS=0` restores the evidence-only index. This grew the
index from 6 chunks to 1,672 — which is what makes the measurements below
meaningful rather than toy-scale.

### 4.2 Activated the KNN fast path (`build_vec_index.py`)

A small idempotent post-build step materializes the `vec0` virtual table
(`evidence_chunks_vec_row`) keyed by rowid — exactly the table `query.py`'s
fast path already expected. Build cost: 0.06 s for 1,672 vectors. The
`just evidence-index*` targets now chain it automatically. We also fixed a
latent bug in the fast path: the `--kind` filter applies *after* the KNN, so
filtered queries now over-fetch (k×10) before filtering rather than
returning fewer than the requested number of results.

### 4.3 Built a retrieval evaluation (`eval_retrieval.py`)

A fixed gold set of 10 natural-language questions, each with one
known-correct target (a document path or ledger record id). Queries are
deliberately paraphrased — "how do vibrational frequencies test the curvature
of a potential energy surface", not "phonon frequency spectrum" — so string
matching can't win by accident. Ranks are computed over *distinct sources*
(multiple chunks of one document collapse to its best rank). Reported per
mode: hit@1/3/5, MRR, and latency. `just evidence-eval` runs it.

### 4.4 Wired CI and verify targets

`.github/workflows/evidence-index.yml` runs the 8-test unit suite
(record contract, fallback embedder, query layer, vec0 sidecar) on every
change under `cocoindex/**` — no model download, seconds to run. New
`just evidence-test` and `just evidence-eval` targets make both gates
one-command local operations.

### 4.5 Corrected the docs

README rewritten against measured reality: cross-platform venv paths, the
real pipeline diagram, the corpus source, the vec0 step, and the measured
numbers below.

## 5. Measurements

Environment: Linux container, CPU only, Python 3.11, cocoindex 1.0.16,
`sentence-transformers/all-MiniLM-L6-v2` (384-dim), sqlite-vec sidecar.
Corpus: 148 markdown documents (~1.1 MB) + 3 seed evidence files → **1,672
chunks, 6.9 MB database**.

### 5.1 Incremental indexing (the core CocoIndex claim)

| Scenario | Engine report | Wall time |
| --- | --- | --- |
| Cold build (everything new) | `148 added` + `3 added` | 45 s |
| Re-run, no changes | `151 unchanged` | **0.1 s** |
| One document edited | `1 reprocessed, 147 unchanged` | ~7 s (mostly model load) |

The engine fingerprints file content, not timestamps: touching a file
without changing bytes does nothing; editing one doc re-embeds only its
chunks. This is the property that makes a *daily-changing* corpus cheap to
keep queryable — the steady-state cost of freshness is per-change, not
per-corpus.

### 5.2 Retrieval quality (gold set, n=10, real model, warm)

| mode | hit@1 | hit@3 | hit@5 | MRR | median s/query |
| --- | --- | --- | --- | --- | --- |
| keyword (SQL LIKE) | 0.10 | 0.10 | 0.30 | 0.16 | 0.012 |
| semantic, unfiltered | 0.50 | 0.60 | 0.70 | 0.59 | 0.009 |
| semantic + `--kind` filter | **0.80** | **0.90** | **0.90** | **0.85** | 0.009 |

Reading the misses is as informative as the hits:

- Keyword search collapses on paraphrase (MRR 0.16) — it cannot connect
  "government grants" to a document titled "Federal Funding Programs."
- Unfiltered semantic search's failures are *crowding*, not confusion: the
  short ledger records (a one-line benchmark claim) get outranked by 1,666
  topically-adjacent document chunks. The kind filter — metadata the pipeline
  carries on every chunk — recovers them, which is the practical argument for
  indexing heterogeneous evidence into one table *with* typed metadata rather
  than either one undifferentiated soup or separate silos.
- The one residual miss (the Bayesian active-learning report) ranks its
  sibling reports above the gold target — a genuine near-duplicate-content
  issue, not a retrieval bug.

### 5.3 Query latency

| Component | Cost |
| --- | --- |
| Embedding model load | ~11 s, once per process |
| Query embedding, warm | ~8 ms |
| KNN search, vec0 sidecar | **1.0 ms** median |
| KNN search, brute-force cosine | 11.3 ms median |

At 1,672 chunks the 11× vec0 speedup is invisible next to model load; the
reason to activate it now is scaling shape — brute force is O(rows) per
query, the vec0 sidecar is not, and the corpus + trace volume only grows.
The one-time model-load cost is also why the *always-warm* GCP service
exists for request-time consumers (the coordinator's memory flywheel), while
this local index serves offline analysis and agent tooling.

## 6. Honest limitations

- **The gold set is small (n=10) and author-written.** Good enough to
  separate 0.16 from 0.85 MRR; not a benchmark. Growing it from real agent
  queries is cheap and worth doing.
- **The offline hash-vector fallback keeps CI and sandboxes green but is not
  a semantic embedding.** The eval harness detects and flags fallback mode
  so its numbers can't be mistaken for real retrieval quality.
- **The D1 → index refresh is on-demand, not scheduled.** The RFC's cron
  backfill remains open; today `just evidence-index-refresh` is a manual (or
  externally scheduled) step.
- **Local index and GCP service are fed by the same collector but not
  guaranteed in sync** — they are two backends of one schema, not one store.

## 7. Reproduce it

```bash
cd lupine-rhizo/cocoindex
uv venv --python 3.11 .venv && VIRTUAL_ENV=$(pwd)/.venv uv pip install -e . pytest
export COCOINDEX_DB="$(pwd)/.cocoindex/db"
python seed_data.py                      # sample ledger evidence
./.venv/bin/cocoindex update main.py     # build (45s cold; 0.1s re-run)
./.venv/bin/python build_vec_index.py    # vec0 KNN sidecar (0.06s)
./.venv/bin/python query.py --semantic "cell size effects on elastic constants" --kind document
./.venv/bin/python eval_retrieval.py     # the table in §5.2
./.venv/bin/python -m pytest test_pipeline.py -q
```

Or from the repo root: `just evidence-index-seed`, `just evidence-eval`,
`just evidence-test`.

## 8. Where this goes next

1. **Grow the gold set from real usage** and track MRR across model or
   chunking changes — the eval harness makes retrieval quality a regression
   test, not a vibe.
2. **Schedule the refresh loop** (cron: `evidence_activation.py collect` →
   `cocoindex update` → `build_vec_index.py`) so the index is never more
   than a day stale without human action.
3. ~~**Index the export bundle contract**~~ — done; see §9.
4. **Feed retrieval back into coordination**: the GCP memory flywheel
   already biases strategy choice on past traces; the corpus index enables
   the same for *written* evidence — an agent deciding what to measure next
   can first ask what the corpus already knows.

## 9. Addendum (2026-07-07): indexing the published Library

The Library at <https://library.lupine.science> is the program's public
corpus, so "what have we published, and what does it say?" should be a
one-query question. This addendum extends the index to cover it.

### 9.1 Design decision: index the contract, not the rendered site

The live Library is a single-page app — every URL returns the app shell, and
article bodies are not individually fetchable. Scraping rendered HTML would
be brittle and would duplicate content the repo already holds in exact form:
`exports/library-content/latest/` is the `library-content.v1` bundle that
lupine-ledger verifies and renders, and its manifest records the generating
commit and a sha256 per article. Indexing the bundle therefore *is* indexing
the published Library, with provenance the site itself doesn't expose. Two
new sources:

- **`published_article`** (73 articles, 958 chunks): the bundle's
  `articles/**`, with `ref_id = "library:<bundle path>"` so results visibly
  distinguish the public corpus from internal docs.
- **`site_guide`** (2 records): the one thing the live site *does* serve as
  plain text — its `llms.txt` / `llms-full.txt` agent-guide files — fetched
  by `fetch_site_content.py`. The fetcher rewrites its JSONL only when the
  live content actually changed, so an unchanged fetch keeps the re-index a
  no-op; and it sends an honest identifying user-agent, since the site's
  edge rejects the default Python one.

The index now spans 226 sources → **2,665 chunks** (15.8 MB), still with a
0.2 s no-change rerun.

### 9.2 What the published corpus did to retrieval — and the twin problem

Re-running the eval (now 13 gold queries) surfaced a real phenomenon:
~50 published articles are exports of internal docs, so the same content
exists under two identities. Queries returned both copies at identical
scores — burning result slots and, in the eval, pushing gold targets down:

```
[1] document/docs/layer2_supercell_evaluation.md            (score -0.795)
[2] published_article/library:docs/layer2_supercell_evaluation.md  (-0.795)
```

The bundle manifest maps every published article to its repo source, which
gives a principled fix: **twin-aware dedup**. `query.py --dedupe` collapses
a published article onto its source doc (keeping the best-ranked of the
pair), and the eval treats retrieving either identity as retrieving the
content. With that in place, on the grown index:

| mode | hit@1 | hit@3 | hit@5 | MRR |
| --- | --- | --- | --- | --- |
| keyword (LIKE) | 0.08 | 0.08 | 0.23 | 0.12 |
| semantic | 0.46 | 0.54 | 0.62 | 0.52 |
| semantic + `--kind` filter | 0.62 | 0.77 | 0.77 | 0.70 |

These are not directly comparable to §5.2 (the gold set gained three harder,
near-duplicate-heavy targets and the index grew 60%), but the ordering and
the gaps hold. Search-only latency at 2,665 chunks: vec0 1.4 ms vs
brute-force 19.2 ms — the gap widens with scale, as expected.

### 9.3 What this buys in practice

The public corpus is now a typed slice of one index:

```bash
# "What has the program published about error geometry?"
python query.py --semantic "what has lupine published about error geometry" \
    --kind published_article
# Cross-everything, one hit per source:
python query.py --semantic "supercell size and elastic constants" --dedupe
# Refresh the live-site guides, incremental:
just evidence-library-fetch
```

An agent can now answer "is this claim public, and where?" by filtering to
`published_article`, or "what does the live site tell agents about us?" via
`site_guide` — all against the same 384-dim space as the internal evidence.

### 9.4 Follow-up: "published" should mean *deployed* (sourcing from lupine-ledger)

§9.1 indexed this repo's export bundle as the published corpus. That was
subtly wrong, and making it right produced the best finding of the exercise.

The bundle in rhizo is what the program *intends* to publish; the public
[lupine-ledger](https://github.com/alexwelcing/lupine-ledger) repo is what
library.lupine.science *actually serves*. Diffing the two manifests
(per-article sha256) showed real drift at the moment of measurement:

| drift class | count | example |
| --- | --- | --- |
| pending publication (local only) | 5 | the environment-error-field paper |
| deployed but dropped from the regenerated bundle | 1 | `projection-law-round2-final.md` |
| content changed since deploy | 23 | `layer2_research_paper.md` |
| in sync | 45 | — |

So the index had been claiming five unpublished articles were public.
`sync_ledger.py` now shallow-clones the ledger and `main.py` prefers its
`content/latest` as the `published_article` source (local bundle as offline
fallback) — "published" carries the ledger's deploy commit as provenance.
CocoIndex's reconciliation made the switch legible in one engine report:
`1 added, 68 reprocessed, 5 deleted` — the five pending articles stopped
claiming to be published, and the one deployed-only article appeared.

Two companion changes keep the pending content findable and the drift
itself queryable:

- The internal-doc corpus now also mounts the dirs that feed the bundle
  (`paper/`, `mlip-elastic-benchmark/`), so a pending paper is retrievable
  as `kind="document"` — correctly labeled as internal, not public.
- `sync_ledger.py --drift` writes the manifest diff as a
  `kind="publication_drift"` evidence record (deterministic, rewritten only
  on change), so *"which articles are awaiting publication?"* is now a
  semantic query answered by the index itself.

### 9.5 The eval catches a real bug: rare kinds and post-KNN filtering

Adding the drift record (2 chunks among 2,875) to the gold set exposed a
genuine retrieval bug: kind-filtered semantic search ran the global vec0
KNN and filtered afterwards, so any kind too small to reach the global
top-k was silently unfindable. The fix inverts the strategy — a kind filter
now triggers an exact cosine scan restricted to that kind (correct at any
cardinality, still ~17ms), while unfiltered queries keep the vec0 fast
path. On the 15-query gold set against the ledger-sourced 2,875-chunk
index: keyword 0.11 / semantic 0.45 / **semantic + kind 0.75** MRR.
This is the eval harness doing its job: a retrieval defect surfaced as a
failing gold query before any agent hit it in production.

## 10. Addendum (2026-07-07): retrieval quality, agent telemetry, and the tier architecture

Sections 1-9 made the corpus *searchable*. This phase makes the retrieval
*good*, adds the agents' own telemetry as a source, automates freshness, and
settles the question the multi-tier design had left implicit: which vector
store is responsible for what. Every quality claim below is a measured
before/after on the same 15-query gold set — the eval harness is the
instrument that made these decisions rather than guesses.

### 10.1 A better embedding space that also unifies the stack

The v1 pipeline used `all-MiniLM-L6-v2` (a 2020-era 384-dim model). I A/B'd it
against `BAAI/bge-small-en-v1.5` by building a full parallel index
(`EVIDENCE_EMBED_MODEL` + `EVIDENCE_DB_PATH` make this a two-env-var run) and
scoring both:

| mode | MiniLM MRR | bge-small MRR |
| --- | --- | --- |
| semantic | 0.45 | **0.51** |
| hybrid | 0.53 | **0.67** |
| semantic + kind | 0.75 | **0.80** |
| hybrid + kind | 0.75 | **0.82** |

bge-small wins every semantic-involving mode. The decisive property beyond the
numbers: **Cloudflare Workers AI serves the identical weights**
(`@cf/baai/bge-small-en-v1.5`), and both are 384-dim — the current column
width. So adopting it means one embedding space across all three tiers
(local sqlite-vec, GCP pgvector, edge Vectorize) with no schema change. bge is
now the default; the swap was a one-line change plus a ~5-min reprocess, and
the harness verified the win before anything shipped. (bge uses a query-side
instruction prefix; the query path applies it automatically.)

### 10.2 Hybrid retrieval — and BM25 alone was the quiet win

The v1 keyword mode was SQL `LIKE` (MRR 0.11-0.16 — nearly useless). Replacing
it with an FTS5/BM25 sidecar was the single largest quality jump in the whole
exercise: **keyword MRR 0.11 → 0.64.** Real IDF ranking connects "C11 Cu
elastic" to the exact claim that plain semantic search buried. A subtlety the
domain forced: I keep single-character tokens in the BM25 query (the v1 code
dropped tokens shorter than 3 chars), because element symbols — `C`, `N`, `O`,
`H` — are meaningful search terms in a materials corpus.

`--hybrid` then fuses the semantic and BM25 legs by reciprocal-rank fusion.
It's the best mode because the legs fail differently: BM25 anchors exact terms
(symbols, property names, IDs), semantic covers paraphrase. Fused, they beat
either alone, and hybrid+kind tops the table at **0.82 MRR, 0.93 hit@5**.
Recommended default is now hybrid.

| mode (bge-small) | hit@1 | hit@3 | hit@5 | MRR |
| --- | --- | --- | --- | --- |
| keyword (BM25) | 0.53 | 0.80 | 0.80 | 0.64 |
| semantic | 0.40 | 0.60 | 0.67 | 0.51 |
| hybrid | 0.53 | 0.80 | 0.93 | 0.67 |
| semantic + kind | 0.73 | 0.80 | 0.93 | 0.80 |
| **hybrid + kind** | **0.73** | **0.93** | **0.93** | **0.82** |

### 10.3 The agents' own telemetry becomes an evidence source

The stack already *emits* OpenInference spans to Phoenix (Arize) from the
glim-think worker and the GCP runners — but nothing read them back. Phoenix is
where "what did the Theorist actually conclude?" and "which agent runs failed
last night, and why?" already live as structured traces; they just weren't
queryable alongside the research corpus. `fetch_phoenix_traces.py` pulls recent
**root** spans via Phoenix's REST API, summarizes each into a prose record
(`kind="agent_trace"`: name, status, model, tokens, latency, input/output
snippet), and writes JSONL for the pipeline. Same-index retrieval means one
query can now span a hypothesis, the published paper that tests it, *and* the
agent run that produced it. The exporter is offline-tolerant (skips cleanly
without credentials) and the record-shaping is unit-tested; the live pull
against a credentialed Phoenix is the one path I could not exercise from the
build sandbox, so it is wired and tested but not yet run end-to-end here.

### 10.4 Automation: freshness and quality as monitored signals

Everything above was still manual. `evidence-nightly.yml` runs the full loop on
a schedule: collect live worker evidence, sync the deployed Library + compute
drift, fetch site guides and Phoenix traces (each best-effort — a missing
secret or an unreachable service warns, never fails), rebuild the index and
sidecars, and run the eval. It publishes two things as artifacts and a job
summary: the **retrieval-eval metrics** (so a model, chunking, or corpus change
that degrades MRR shows up as a trend, not a surprise) and the **publication
drift** (so "N articles awaiting publication, M changed since deploy" is a
standing report). The index itself isn't committed — it's gitignored and
rebuildable; the *signal* is the deliverable.

### 10.5 The tier architecture, made explicit

Indexing the same schema into more than one vector store is only coherent if
each store has a stated job. Three exist or are planned; here is the division I
recommend, now that they share one embedding space:

| Tier | Store | Role | Freshness |
| --- | --- | --- | --- |
| **local** | sqlite-vec + FTS5 | offline analysis, the eval ground truth, agent tooling via `query.py` | on-demand / nightly |
| **service** | GCP Cloud Run + pgvector | request-time coordinator memory *today*; natural home for public Library search | warm, always-on |
| **edge** (planned) | Cloudflare Vectorize | in-process agent memory at request time — no cross-cloud hop for `consultMemory`'s 800ms budget | live on `emitTrace` |

The shared bge-small space is what makes the edge tier newly feasible: Workers
AI can embed *and* Vectorize can store 384-dim vectors in-process, so the
coordinator's memory flywheel — which today pays a cross-cloud hop to Cloud Run
with cold-start risk — could become an edge-local lookup. That is a
Cloudflare-side change I've specced but deliberately not deployed blind from
here; it belongs in the RFC as the next unit, with the open decision being
whether the GCP service then retires or pivots to backing public Library
search (not both by accident). The Literaturist agent is already a
retrieval-augmented Durable Object, so the pattern for giving Theorist/Causal
an evidence-lookup tool is proven in-tree.

### 10.6 Where the ceiling is now

With retrieval solid and telemetry flowing, the highest-value remaining move is
the one the whole index was built to enable: **agents consulting it before they
act** — retrieval-augmented hypothesis generation, so an agent proposing a test
first asks whether the corpus (or a past agent trace, or a refuted claim)
already answers it. That plus a `claim`-lifecycle exporter (real
proposed/supported/refuted status, which needs the one schema change this
pipeline still wants: a metadata column so `--kind claim --status refuted`
becomes a query) is what turns the evidence index from a search tool into part
of the research loop itself.
