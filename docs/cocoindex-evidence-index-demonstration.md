# CocoIndex in the Lupine Research Stack: Evaluation, Measurement, and Improvement

**Status:** demonstration write-up, 2026-07-06
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
3. **Index the export bundle contract** — the `exports/library-content`
   articles ship to the public Library (lupine-ledger); indexing the *source*
   docs already covers their content, but indexing manifests would let agents
   answer "what is public?" semantically.
4. **Feed retrieval back into coordination**: the GCP memory flywheel
   already biases strategy choice on past traces; the corpus index enables
   the same for *written* evidence — an agent deciding what to measure next
   can first ask what the corpus already knows.
