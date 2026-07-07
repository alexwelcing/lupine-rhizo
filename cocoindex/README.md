# cocoindex — glim-think evidence + research-corpus index

An incremental data-processing pipeline ([CocoIndex](https://cocoindex.io) v1)
that indexes the glim-think control plane's evidence — **coordination traces,
hypotheses, claims** — AND the repo's **living markdown research corpus**
(`docs/**/*.md` + root `*.md`) into a local SQLite store with vector
embeddings for semantic search.

This is the "evidence tier" that closes the loop between the Cloudflare
coordination layer (`glim-think/src/agents/coordinator.ts`, the Omnigents
implementation) and offline analysis: every coordination call, research
artifact, and research document becomes queryable by meaning, not just by id.

## What it does

```
./data/*.jsonl        ──▶ process_file        ─┐
(ledger + site guides)    (memo=True)          │
../docs/**/*.md, ../*.md  process_doc_file    ─┼─▶ RecursiveSplitter ──▶ per-chunk embed ──▶ ./evidence.db ──▶ build_vec_index.py
                          (memo=True)          │   (1000/200 tokens,     (all-MiniLM-L6)     (float[384])      (vec0 KNN sidecar)
../exports/library-content/latest/articles/** │    markdown-aware)
                      ──▶ process_article_file ┘
```

- **Sources**:
  - JSONL files under `./data/`, one record per line:
    `{"id","kind","ref_id","text","metadata"}`. The `text` field is embedded.
    Produced by `export_evidence.py`/`evidence_activation.py` (ledger
    evidence) and `fetch_site_content.py` (`kind="site_guide"`: the live
    `llms.txt` / `llms-full.txt` guides from https://library.lupine.science).
  - The repo's markdown corpus: `docs/**/*.md` plus root-level `*.md`,
    indexed as `kind="document"` with the repo-relative path as `ref_id`.
    Set `EVIDENCE_INDEX_CORPUS=0` for the evidence-only (v1) index.
  - The **published Library** (`kind="published_article"`,
    `ref_id="library:<bundle path>"`): the DEPLOYED `library-content.v1`
    content from the public [lupine-ledger](https://github.com/alexwelcing/lupine-ledger)
    repo — what https://library.lupine.science actually serves — synced into
    `./.cache/lupine-ledger` by `sync_ledger.py` (ledger commit = provenance).
    Falls back to this repo's export bundle (`exports/library-content/latest`,
    i.e. what rhizo intends to publish next) when no cache exists; override
    with `EVIDENCE_LIBRARY_ROOT`. `sync_ledger.py --drift` also diffs the two
    manifests and indexes the result (`kind="publication_drift"`), so "what is
    awaiting publication?" is a semantic query. `query.py --dedupe` collapses
    a published article onto its repo source doc (twin-aware, via the active
    manifest). Internal-doc coverage includes the dirs that feed the bundle
    (`paper/`, `mlip-elastic-benchmark/`), so pending content stays findable
    as `kind="document"`.
- **Transform**: read → parse → recursive-split into ~1000-token chunks
  (markdown-aware for documents) → embed each.
- **Target**: `./evidence.db`, table `evidence_chunks(id, source_file, kind, ref_id, text, embedding, chunk_start, chunk_end)`.
  `embedding` is a 384-dim float32 vector column. `build_vec_index.py` then
  materializes the `vec0` KNN sidecar (`evidence_chunks_vec_row`) that
  `query.py`'s fast path uses — measured ~11× faster than brute-force cosine
  at 1.7k chunks (1.0ms vs 11.3ms search-only).
- **Incremental**: CocoIndex memoizes all processors by content fingerprint.
  Measured on the full corpus (245 sources → 2,875 chunks): no-change rerun
  0.2s, single-doc edit re-embeds only that file (~7s wall, dominated by
  model load). `fetch_site_content.py` and `sync_ledger.py --drift` rewrite
  their JSONL only when content actually changed, so a no-op fetch keeps the
  re-index a no-op too.

## Setup

```bash
cd cocoindex
uv venv --python 3.11 .venv
VIRTUAL_ENV=$(pwd)/.venv uv pip install -e .              # cocoindex + sentence-transformers + sqlite-vec
VIRTUAL_ENV=$(pwd)/.venv uv pip install pytest             # for the tests
```

Venv binaries live in `.venv/bin/` on Linux/macOS and `.venv/Scripts/` on
Windows; the commands below use the Linux form.

## Run

```bash
export COCOINDEX_DB="$(pwd)/.cocoindex/db"   # v1 local state path (required)
python seed_data.py                           # populate ./data with sample records
./.venv/bin/cocoindex update main.py          # catch-up; process what changed
./.venv/bin/python build_vec_index.py         # materialize the vec0 KNN sidecar
./.venv/bin/cocoindex update main.py -L       # live mode: watch sources for changes
./.venv/bin/cocoindex update main.py --full-reprocess   # reprocess everything
```

Verified output (real run: seed evidence + the repo markdown corpus):

```
✅ process_file: 3 total | 3 added
✅ process_doc_file: 148 total | 148 added
⏳ Elapsed: 44.9s
→ evidence.db: 1,672 rows (6.9 MB), embedding bytes = 1536 (= 384 float32 dims) per row
```

Rerun is incremental:

```
✅ process_file: 3 total | 3 unchanged
✅ process_doc_file: 148 total | 148 unchanged
⏳ Elapsed: 0.1s
```

Editing a single doc re-embeds only that doc (`1 reprocessed, 147 unchanged`).

### Offline / CI without HF Hub access

The embedder falls back to a deterministic hash-vector if the model can't be
downloaded (`_fallback_vector` in `main.py`). This keeps the index buildable
and testable anywhere; it is **not** a real semantic embedding (clearly logged).
The real model is used whenever it's reachable.

## Wiring to the live ledger

`export_evidence.py --from-d1` reads the glim-ledger D1 via `wrangler d1
execute --remote --json` and writes `./data/*.jsonl` in the format above. Then
`cocoindex update main.py` indexes it. So the full refresh loop is:

```bash
python export_evidence.py --from-d1     # D1 → JSONL
./.venv/Scripts/cocoindex update main.py # JSONL → embedded index
```

`coordination_traces` rows come from the Omnigents coordinator
(`glim-think/src/agents/coordinatorTraces.ts`); `hypotheses`/`claims` come from
the existing research ledger.

## Querying

`evidence.db` is a standard SQLite database with the `sqlite-vec` extension
loaded by CocoIndex on write. Two query interfaces:

**`query.py`** (this dir) — semantic + keyword search CLI:

```bash
./.venv/bin/python query.py --semantic "which coordination strategies beat the baseline" --limit 5
./.venv/bin/python query.py --keyword "aluminium cohesive" --kind hypothesis
./.venv/bin/python query.py --semantic "cell size effects on elastic constants" --kind document
./.venv/bin/python query.py --semantic "hyper-ribbon" --json   # programmatic
```

Semantic mode embeds the query (real all-MiniLM-L6-v2, or offline hash-vector
fallback) and does nearest-neighbour over the index — via the `vec0` KNN
sidecar when `build_vec_index.py` has run, else brute-force cosine; keyword
mode is plain SQL LIKE (always works). See `--help`.

**From the repo root**, `just` targets wrap the above:

```bash
just evidence-index                                    # build index + vec0 sidecar
just evidence-index-search q="which strategies worked" # semantic
just evidence-index-search q="aluminium" mode=keyword kind=hypothesis
just evidence-index-refresh                            # D1 → JSONL → re-index
just evidence-library-fetch                            # live site guides → re-index
just evidence-ledger-sync                              # deployed ledger + drift → re-index
just evidence-eval                                     # retrieval-quality eval
just evidence-test                                     # unit tests
```

## Measured retrieval quality

`eval_retrieval.py` scores a fixed gold set of 15 paraphrased questions
(documents, published articles, site guides, ledger records, and the
publication-drift record) against the full 2,875-chunk index, real model,
warm. Ranking is twin-aware: retrieving either identity of the same content
(internal doc or its published article) counts.

| mode | hit@1 | hit@3 | hit@5 | MRR | median s/query |
| --- | --- | --- | --- | --- | --- |
| semantic | 0.40 | 0.47 | 0.53 | 0.45 | 0.009 |
| semantic + `--kind` filter | 0.67 | 0.80 | 0.80 | 0.75 | 0.017 |
| keyword (LIKE) | 0.07 | 0.07 | 0.20 | 0.11 | 0.020 |

(Earlier generations: 10-query gold on the 1,672-chunk pre-Library index —
semantic 0.59 / +kind 0.85 / keyword 0.16 MRR; each corpus growth added
harder, near-duplicate-heavy targets.)

Kind-filtered semantic search runs an exact cosine scan restricted to the
kind rather than the global vec0 KNN — a global top-k that's post-filtered
silently drops rare kinds (a 2-chunk kind never surfaces). Unfiltered
queries use the vec0 sidecar. Model load is a one-time ~11s per process;
after that queries are ~9-17ms. Search-only latency at 2,875 chunks: vec0
KNN 1.4ms vs brute-force 20.9ms.

## Architecture: worker vs cocoindex (the honest split)

Cloudflare Workers cannot run Python cocoindex (Pyodide can't load
`sqlite-vec` / `sentence-transformers`), and glim-think has no Vectorize
binding. So the two layers split cleanly by runtime:

| Layer | Runtime | Role |
| --- | --- | --- |
| **glim-think worker** | TypeScript / Cloudflare | **Produces** evidence → D1 (`coordination_traces`, `hypotheses`, `claims`). Exposes `GET /evidence/recent` for a live, non-vector view. |
| **cocoindex** | Python / local-or-scheduled | **Indexes** that evidence → `evidence.db`, and `query.py` does the semantic search the worker can't. |

Don't try to merge these — the Python/Worker boundary is real. The worker is
the live producer; cocoindex is the offline indexer + query layer.

## Tests

```bash
./.venv/bin/python -m pytest test_pipeline.py -q
```

Unit-tests the record-format contract, the deterministic fallback embedder,
the query layer, and the vec0 sidecar builder. These run in CI on every
change to `cocoindex/**` (`.github/workflows/evidence-index.yml`). The full
engine run is exercised manually (above) — it needs `COCOINDEX_DB` and the
CLI, so it isn't part of the pytest suite.

## Files

| File | Purpose |
| --- | --- |
| `main.py` | The CocoIndex `App`: `EvidenceChunk` schema, `process_file`/`process_doc_file`/`process_chunk`, embedder + SQLite lifespan, `app_main`. |
| `pyproject.toml` | Deps: cocoindex≥1.0, sentence-transformers, sqlite-vec. |
| `seed_data.py` | Populate `./data/` with sample evidence (local dev / CI). |
| `export_evidence.py` | D1 → JSONL exporter (the live-ledger wire). |
| `fetch_site_content.py` | Live-site guide fetcher (llms.txt from library.lupine.science) → `data/site_guides.jsonl`; rewrites only on change. |
| `sync_ledger.py` | Sync the deployed Library content from the public lupine-ledger repo into `.cache/`; `--drift` diffs pending vs deployed manifests → `data/publication_drift.jsonl`. |
| `build_vec_index.py` | Materialize the `vec0` KNN sidecar after each index build. |
| `eval_retrieval.py` | Gold-set retrieval eval: hit@k, MRR, latency (semantic vs keyword). |
| `test_pipeline.py` | pytest: record format, fallback embedder, query layer, vec0 sidecar. Runs in CI (`.github/workflows/evidence-index.yml`). |
| `data/` | Source JSONL (gitignored output target of seed/export). |
| `evidence.db`, `.cocoindex/` | Generated index + engine state (gitignored). |

## Why CocoIndex (vs a one-shot script)

The evidence corpus is constantly changing — new coordination traces every
run, hypotheses changing status, claims added. CocoIndex handles the
incremental bookkeeping (only re-embed what changed, by content fingerprint)
declaratively, so the index stays current without a full re-embed every time.
That's the property that makes the evidence tier cheap to keep live.
