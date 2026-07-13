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
(ledger, site guides,     (memo=True)          │
 agent traces)                                 │
../docs/**/*.md, ../*.md  process_doc_file    ─┼─▶ RecursiveSplitter ─▶ per-chunk embed ─▶ ./evidence.db ─▶ build_vec_index.py
                          (memo=True)          │   (1000/200 tokens,    (bge-small-en)     (float[384])     (vec0 KNN + FTS5 BM25)
../exports/library-content/latest/articles/** │    markdown-aware)
                      ──▶ process_article_file ┘
```

- **Sources**:
  - JSONL files under `./data/`, one record per line:
    `{"id","kind","ref_id","text","metadata"}`. The `text` field is embedded.
    Produced by `export_evidence.py`/`evidence_activation.py` (ledger
    evidence), `fetch_site_content.py` (`kind="site_guide"`: the live
    `llms.txt` guides from https://library.lupine.science), and
    `fetch_phoenix_traces.py` (`kind="agent_trace"`: root-span summaries of
    agent runs pulled back from Phoenix/Arize telemetry).
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
  materializes two sidecars: the `vec0` KNN index (`evidence_chunks_vec_row`,
  ~15× faster than brute-force cosine at 2.9k chunks) for semantic search, and
  the FTS5 index (`evidence_chunks_fts`) for BM25 keyword ranking and the
  lexical leg of hybrid search.
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
./.venv/bin/python query.py --hybrid  "which coordination strategies beat the baseline" --limit 5
./.venv/bin/python query.py --keyword "C11 Cu elastic" --kind claim     # BM25, element symbols
./.venv/bin/python query.py --semantic "cell size effects on elastic constants" --kind document
./.venv/bin/python query.py --hybrid  "hyper-ribbon" --dedupe --json    # programmatic
```

Three modes: **`--hybrid`** (recommended) fuses semantic + BM25 by
reciprocal-rank fusion; **`--semantic`** embeds the query (real
bge-small-en-v1.5, or offline hash-vector fallback) and does nearest-neighbour
via the `vec0` sidecar; **`--keyword`** is BM25 over FTS5 (SQL-LIKE fallback if
the sidecar is absent). Add `--kind` to filter, `--dedupe` to collapse twins.
See `--help`.

**From the repo root**, `just` targets wrap the above:

```bash
just evidence-index                                    # build index + vec0 sidecar
just evidence-index-search q="which strategies worked" # semantic
just evidence-index-search q="aluminium" mode=keyword kind=hypothesis
just evidence-index-refresh                            # D1 → JSONL → re-index
just evidence-library-fetch                            # live site guides → re-index
just evidence-ledger-sync                              # deployed ledger + drift → re-index
just evidence-phoenix-fetch                            # Phoenix agent traces → re-index
just evidence-eval                                     # retrieval-quality eval
just evidence-test                                     # unit tests
```

CI: `evidence-index.yml` runs the unit suite on every `cocoindex/**` change;
`evidence-nightly.yml` refreshes all sources, rebuilds, and publishes the
retrieval-eval metrics + publication drift as artifacts each night.

## Measured retrieval quality

`eval_retrieval.py` scores a fixed gold set of 15 paraphrased questions
(documents, published articles, site guides, ledger records, and the
publication-drift record) against the full ~2,880-chunk index, real model,
warm. Ranking is twin-aware: retrieving either identity of the same content
(internal doc or its published article) counts. Default model:
**BAAI/bge-small-en-v1.5** (384-dim).

| mode | hit@1 | hit@3 | hit@5 | MRR |
| --- | --- | --- | --- | --- |
| keyword (BM25 / FTS5) | 0.53 | 0.80 | 0.80 | 0.64 |
| semantic | 0.40 | 0.60 | 0.67 | 0.51 |
| hybrid (RRF) | 0.53 | 0.80 | 0.93 | 0.67 |
| semantic + `--kind` | 0.73 | 0.80 | 0.93 | 0.80 |
| **hybrid + `--kind`** | **0.73** | **0.93** | **0.93** | **0.82** |

**hybrid is the recommended default mode** — it fuses the BM25 and semantic
legs by reciprocal-rank fusion, so exact terms (element symbols like `C`,
property names like `C11`) are anchored lexically while paraphrase is covered
semantically. Neither leg alone wins: BM25 beats plain semantic here (0.64 vs
0.51), and fusing them beats both.

Notes on why the numbers moved across generations:
- **bge-small vs the original all-MiniLM-L6-v2**: semantic MRR 0.51 vs 0.45,
  hybrid+kind 0.82 vs 0.75 — bge wins every semantic-involving mode *and*
  shares weights with Cloudflare Workers AI (`@cf/baai/bge-small-en-v1.5`),
  so local / GCP / edge tiers can use one 384-dim space. Swap models via
  `EVIDENCE_EMBED_MODEL`; the eval harness proved the win before adoption.
- **BM25 vs the old SQL-LIKE keyword**: 0.64 vs 0.11 MRR. FTS5 with real
  IDF ranking, and single-char tokens kept (element symbols matter here).
- Kind-filtered semantic runs an exact cosine scan restricted to the kind,
  not the global vec0 KNN (a post-filtered global top-k silently drops rare
  kinds — a 2-chunk kind never surfaces). Unfiltered queries use the vec0
  sidecar (1.4ms vs 20.9ms brute-force at ~2,880 chunks). bge query embedding
  is ~27ms warm; model load is a one-time ~7-11s per process.

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
| `fetch_phoenix_traces.py` | Pull recent agent-run root spans from Phoenix/Arize → `data/agent_traces.jsonl` (`kind="agent_trace"`); skips cleanly without credentials. |
| `build_vec_index.py` | Materialize the `vec0` KNN + FTS5 BM25 sidecars after each index build. |
| `eval_retrieval.py` | Gold-set retrieval eval: hit@k, MRR, latency across keyword/semantic/hybrid (±kind). `--json` for the nightly trend. |
| `test_pipeline.py` | pytest: record format, fallback embedder, query layer, vec0 sidecar. Runs in CI (`.github/workflows/evidence-index.yml`). |
| `data/` | Source JSONL (gitignored output target of seed/export). |
| `evidence.db`, `.cocoindex/` | Generated index + engine state (gitignored). |

## Why CocoIndex (vs a one-shot script)

The evidence corpus is constantly changing — new coordination traces every
run, hypotheses changing status, claims added. CocoIndex handles the
incremental bookkeeping (only re-embed what changed, by content fingerprint)
declaratively, so the index stays current without a full re-embed every time.
That's the property that makes the evidence tier cheap to keep live.
