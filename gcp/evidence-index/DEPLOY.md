# Deploying the evidence-index service

FastAPI service on Cloud Run: the always-warm live tier the glim-think
coordinator consults for memory (`consultMemory`/`emitTrace` in
`glim-think/src/agents/memoryClient.ts`). Same record schema as the offline
cocoindex index; Postgres + pgvector in prod, SQLite for dev/test.

## Embedding model — MUST match the cocoindex local index

The service defaults to **`BAAI/bge-small-en-v1.5`** (384-dim), the same model
the offline `cocoindex/` index uses, so the two tiers share one embedding
space. Overridable:

```
EVIDENCE_EMBED_MODEL   default BAAI/bge-small-en-v1.5
EVIDENCE_EMBED_DIM     default 384
```

### ⚠️ Changing the model requires a full re-embed (backfill)

Vectors from two different models are **not comparable even at the same
dimension** — a bge query vector against MiniLM-embedded stored vectors returns
garbage rankings. The pgvector column is `vector(384)` for both, so nothing
errors; the results silently degrade. So a model switch is a two-step,
ordered operation, not just a redeploy:

1. **Re-embed every stored row with the new model**, then
2. cut queries over to the new model.

Because ingest is idempotent by `id`, the safe procedure is:

```bash
# 0. Deploy the new model as the ACTIVE model (this build already defaults
#    to bge-small; set EVIDENCE_EMBED_MODEL to override).
just evidence-deploy        # gcloud builds submit ... cloudbuild.yaml

# 1. Re-ingest the full corpus so every vector is re-embedded with bge-small.
#    The collector re-POSTs every record; idempotent upsert overwrites the
#    stale MiniLM vector in place.
just evidence-live-ingest   # scripts/evidence_activation.py ingest (needs EVIDENCE_INGEST_TOKEN)

# 2. Verify: a known query should return its known answer near rank 1.
just evidence-health
curl -sS "$INGEST_URL/search?q=cell+size+effects+on+elastic+constants&mode=semantic&limit=3" \
  -H "Authorization: Bearer $EVIDENCE_INGEST_TOKEN" | jq '.results[].ref_id'
```

Until step 1 completes, the index holds a mix of MiniLM and bge vectors and
semantic search is unreliable. If you must avoid any degraded window, ingest
into a fresh index/table first and flip `EVIDENCE_INDEX_URL` once it's warm.

The deterministic hash-vector fallback (`_fallback_embed`) is model-independent
and only used when the real model can't load — it keeps `/health` and CI green,
but its "semantic" results are not real. `/health` reports which is active
(`embed_model`).

## Required config (secrets, not committed)

See `wrangler.toml`'s evidence-index notes for the worker side. The service
reads:

```
EVIDENCE_INGEST_TOKEN   bearer token gating POST /ingest (and authed /count)
DATABASE_URL            Postgres+pgvector DSN (prod); unset → SQLite dev store
EVIDENCE_EMBED_MODEL    (optional) override, default bge-small-en-v1.5
```

## Standard deploy

```bash
just evidence-deploy    # from repo root: gcloud builds submit --config gcp/evidence-index/cloudbuild.yaml .
```

No model change → no backfill; a plain redeploy is safe and warm-swaps.

## Tests

```bash
cd gcp/evidence-index && python -m pytest test_service.py -q
```

Covers ingest/search/keyword/kind-filter/idempotency and the BGE query-prefix
contract (query embeds get the instruction prefix; document embeds do not).
