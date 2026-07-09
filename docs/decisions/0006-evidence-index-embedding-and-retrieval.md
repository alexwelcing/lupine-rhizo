# ADR-0006: Standardize the evidence index on bge-small-en-v1.5 + hybrid retrieval; keep coordinator memory on GCP

**Status:** Accepted
**Date:** 2026-07-07
**Author:** Research lead (evidence-index optimization pass)
**Supersedes:** the implicit `all-MiniLM-L6-v2` choice in the original
cocoindex pipeline and `gcp/evidence-index`.

---

## 1. Context

The evidence index (offline `cocoindex/` + live `gcp/evidence-index` Cloud Run
service) had grown to cover coordination traces, the research-doc corpus, the
published Library, and agent telemetry. Two questions were unanswered with
data: which embedding model, and which retrieval strategy. A separate question
was raised by discovering a **dormant** Cloudflare Vectorize integration in
`glim-think/src/literature/embed.ts` (bge-base 768, `CORPUS_INDEX` unbound):
should request-time coordinator memory move to the edge now?

## 2. Decision

1. **Embedding model: `BAAI/bge-small-en-v1.5` (384-dim)** across both the
   offline cocoindex index and the GCP service — one shared space. Chosen by
   A/B on a 15-query gold set (`cocoindex/eval_retrieval.py`): bge-small beats
   the prior all-MiniLM-L6-v2 on every semantic mode, and its weights are
   served identically by Cloudflare Workers AI (`@cf/baai/bge-small-en-v1.5`),
   keeping a future edge tier in the same 384-dim space. Overridable via
   `EVIDENCE_EMBED_MODEL`.
2. **Retrieval: hybrid (BM25 + vector, reciprocal-rank fusion) is the default.**
   An FTS5/BM25 sidecar replaced SQL-LIKE keyword search (MRR 0.11 → 0.64);
   fused with the semantic leg it reaches 0.82 MRR / 0.93 hit@5 with a kind
   filter. Single-character tokens are kept (element symbols matter).
3. **Coordinator memory stays on GCP for now — not Cloudflare Vectorize.**
   The GCP service is realigned to bge-small so local↔GCP share one space.
   Edge Vectorize memory is deferred to a verified follow-on
   (`docs/rfc-evidence-edge-memory.md`) because it needs Cloudflare-env
   verification and an unresolved dimension decision (the dormant edge code is
   768-dim).

## 3. Consequences

- **Positive:** measured retrieval lift; one embedding space across the offline
  and live tiers; the edge path remains open at 384 dims without rework;
  retrieval quality is now a regression signal (nightly eval).
- **Cost / risk:** switching the GCP service's model requires a full re-embed
  backfill before cutover — bge and MiniLM vectors are incomparable even at the
  same dimension. The procedure is documented in
  `gcp/evidence-index/DEPLOY.md`; the redeploy+backfill is a deliberate op, not
  a plain push.
- **Deferred:** edge-memory latency win (cross-cloud hop remains on the 800ms
  hot path until the follow-on); the `EvidenceChunk` metadata column that would
  make `--kind claim --status refuted` a query.

## 4. Verification

- `cocoindex/eval_retrieval.py` — the A/B and mode comparison (real model).
- `cocoindex/test_pipeline.py` (15) and `gcp/evidence-index/test_service.py`
  (7, incl. the BGE query-prefix contract) — both green.
- Edge-memory claims are explicitly **not** verified here; the follow-on RFC
  carries a verification plan that must run in the Cloudflare env.
