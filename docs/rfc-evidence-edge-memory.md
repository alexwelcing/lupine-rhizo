# RFC: Edge-tier evidence memory (Cloudflare Vectorize) — deferred follow-on

**Status:** proposed, not started. Deferred from the 2026-07-07 retrieval
release by explicit decision ("don't move memory to edge today").
**Depends on:** the shipped cocoindex + GCP bge-small alignment (this release).
**Owner action required:** Cloudflare account access + the decisions in §4.

---

## 1. Why this exists

The coordinator's memory flywheel (`glim-think/src/agents/memoryClient.ts`)
consults the evidence index *before* choosing a strategy, on a strict 800ms
hot-path budget, via an HTTP call to the GCP Cloud Run service. That call pays
a cross-cloud hop with cold-start risk. Cloudflare Vectorize + Workers AI could
make the same lookup edge-local and in-process. This RFC captures the plan so
the work is turnkey when we choose to do it — it is **not** part of today's
release, which keeps memory on GCP.

## 2. Current state (verified by code read, 2026-07-07)

- **Live memory tier is GCP.** `consultMemory`/`emitTrace` hit
  `EVIDENCE_INDEX_URL` (Cloud Run). This release aligns that service to
  `bge-small-en-v1.5` (384-dim) so it shares the cocoindex embedding space.
- **A Vectorize integration already exists but is DORMANT.**
  `glim-think/src/literature/embed.ts` embeds the *paper corpus* into a
  `glim-corpus` Vectorize index (`env.CORPUS_INDEX`) using Workers AI
  `@cf/baai/bge-base-en-v1.5` (**768-dim**). Critically, `CORPUS_INDEX` is
  **not bound in `wrangler.toml`** — the code guards on `if (!env.CORPUS_INDEX)`
  and no-ops. So there is no live Vectorize index to break, and its intended
  model (bge-base 768) does **not** match this release's bge-small 384.
- `[ai]` binding (`env.AI`, Workers AI) IS present and used by the Literaturist
  and models.ts. So edge embedding is already available.

## 3. The dimension fork (the crux)

A Vectorize index has a fixed dimension at creation. Two models are in play:

| Use | Model | Dim | Status |
| --- | --- | --- | --- |
| cocoindex local + GCP service (this release) | bge-small-en-v1.5 | 384 | live |
| Literaturist corpus (dormant code) | bge-base-en-v1.5 | 768 | not bound |

Moving coordinator memory to the edge means picking ONE space for it. Options
are in §4. Note bge-small is served on Workers AI as
`@cf/baai/bge-small-en-v1.5`, so 384 is achievable at the edge too — the
dormant code just happens to have chosen bge-base.

## 4. Decisions required before implementation

1. **Which dimension for edge coordination-memory?**
   - (a) 384 / bge-small — unifies with the just-shipped local+GCP space; a new
     Vectorize index `glim-coord-memory` at 384. *Recommended*: one space for
     the memory flywheel across all tiers.
   - (b) 768 / bge-base — matches the dormant literature code; but then the
     memory tier diverges from local+GCP (384), or we re-standardize everything
     on 768 (re-opens the shipped A/B).
2. **Does the GCP service retire, or pivot?** If Vectorize takes the
   request-time flywheel, GCP pgvector's remaining edge is relational/metadata
   queries and public-Library search. Decide: retire, or repurpose as the
   Library search backend — not both by accident.
3. **Literaturist corpus:** leave dormant, activate at 768 as-is, or rebuild at
   384 to share the memory space. Independent of the flywheel decision.

## 5. Implementation sketch (once §4 is decided, assuming 4.1a)

1. `wrangler.toml`: add a Vectorize binding
   ```toml
   [[vectorize]]
   binding = "COORD_MEMORY"
   index_name = "glim-coord-memory"   # created at 384 dims, cosine
   ```
   and `wrangler vectorize create glim-coord-memory --dimensions=384 --metric=cosine`.
2. New `memoryClientEdge.ts` (or a backend switch inside `memoryClient.ts`):
   - `consultMemory`: `env.AI.run("@cf/baai/bge-small-en-v1.5", {text:[prefix+prompt]})`
     → `env.COORD_MEMORY.query(vec, {topK, filter:{kind:"coordination_trace"}})`
     → reuse the existing `_computeBias` unchanged.
   - `emitTrace`: embed + `env.COORD_MEMORY.upsert([{id, values, metadata}])`,
     fire-and-forget, alongside the existing D1 write (source of truth).
   - Keep the GCP path behind the same interface; select by binding presence so
     rollback is a config flip. Memory stays "uplift, never dependency" — all
     paths degrade to registry-only on error (preserve current behavior).
3. **Backfill:** one-time re-embed of `coordination_traces` from D1 into
   Vectorize (a Worker route or a scripted `upsert` loop) before cutting
   `consultMemory` over — same "re-embed before you query" discipline as the
   GCP runbook (`gcp/evidence-index/DEPLOY.md`).
4. Apply the query-side bge prefix (`Represent this sentence for searching
   relevant passages: `) — the same contract the cocoindex and GCP tiers use.

## 6. Verification plan (must pass before it's "done")

Cannot be verified from the offline build sandbox — needs the Cloudflare env:

- `wrangler dev` locally with the Vectorize binding; unit-test the bias math
  (already covered) + a live `query`/`upsert` round-trip in `src/agents/__tests__`.
- Golden check: seed a few known traces, confirm `consultMemory` returns a bias
  that steers strategy as expected (mirror `eval_retrieval.py`'s gold-query
  idea for the coordination domain).
- Hot-path budget: measure `consultMemory` p50/p95 vs the 800ms ceiling —
  the entire point is that edge-local beats the cross-cloud hop; prove it.
- Canary: deploy with the binding but flag `consultMemory` to log-compare
  edge vs GCP results on live traffic before making edge authoritative.

## 7. Related unlocked work (separate RFCs)

- **Agents consult the index before acting** (retrieval-augmented hypothesis
  generation) — the Literaturist is already a retrieval-augmented DO; the
  pattern extends to Theorist/Causal. Highest research value; independent of
  which tier serves the vectors.
- **Claim-lifecycle exporter + a `metadata` column on `EvidenceChunk`** so
  `--kind claim --status refuted` is a query. The one schema change the
  pipeline still wants.
