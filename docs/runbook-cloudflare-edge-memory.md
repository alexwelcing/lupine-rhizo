# Runbook: Cloudflare edge-memory (Vectorize) for the coordinator flywheel

Operational companion to `docs/rfc-evidence-edge-memory.md`. This is the
step-by-step for moving the coordinator's `consultMemory` lookup from the
cross-cloud GCP hop to an **edge-local Vectorize + Workers AI** path — safely,
behind a shadow-mode flag, with a report checkpoint after every step.

**Design principle: nothing here affects live coordination until we explicitly
flip to `active`.** Every step is additive, binding-guarded, and reversible.
Memory stays "uplift, never a dependency" — all failure paths fall back to the
current GCP behavior.

---

## Decision to confirm before you start

**Embedding dimension: 384 / `@cf/baai/bge-small-en-v1.5` (recommended).**
This matches the space we just shipped (cocoindex local + GCP service), so all
tiers are comparable. The only alternative is 768/bge-base to match the dormant
Literaturist code — but that diverges from the shipped release. **This runbook
assumes 384.** If you want 768, stop and tell me; I'll adjust the code and the
`--dimensions` flag.

## Ownership legend

- 👤 **You** — run in the Cloudflare CLI/dashboard, paste the output back.
- 🤖 **Me** — a code change I land in a follow-on PR before your next step.
- 🔁 **Checkpoint** — paste the noted output; I confirm before you proceed.

All 👤 commands run from `glim-think/` with a logged-in `wrangler`
(`npx wrangler login`, or `CLOUDFLARE_API_TOKEN` set). Use `npx wrangler` to
match the repo's pinned version.

---

## Phase A — Recon (👤, read-only, ~5 min)

Confirms the live state my plan assumes. Zero risk.

```bash
# A1. Confirm the worker + account, and the Workers AI binding is live.
npx wrangler whoami
npx wrangler deployments list --name glim-think-v1 | head

# A2. List existing Vectorize indexes. I expect NO coordination index yet,
#     and want to see whether 'glim-corpus' (the dormant Literaturist index)
#     actually exists or is only in code.
npx wrangler vectorize list

# A3. Confirm the live coordinator memory setting (GCP). Names only, not values.
npx wrangler secret list --name glim-think-v1
```

🔁 **Checkpoint A.** Paste the output of A1–A3 (redact any tokens/URLs you
don't want shared — I only need: which Vectorize indexes exist, and whether
`EVIDENCE_INDEX_URL` / `EVIDENCE_INGEST_TOKEN` appear in the secret list).

---

## Phase B — Create the Vectorize index (👤, ~5 min, reversible)

Creates infrastructure only. No code references it yet, so it's inert.

```bash
# B1. Create the coordination-memory index at 384 dims, cosine.
npx wrangler vectorize create glim-coord-memory --dimensions=384 --metric=cosine

# B2. Create the metadata index for `kind` filtering.
#     IMPORTANT: metadata indexes must exist BEFORE vectors are upserted, or
#     those vectors won't be filterable. consultMemory filters kind=
#     "coordination_trace", so this must be done now, before any backfill.
npx wrangler vectorize create-metadata-index glim-coord-memory \
  --property-name=kind --type=string

# B3. Confirm.
npx wrangler vectorize get glim-coord-memory
npx wrangler vectorize list-metadata-index glim-coord-memory
```

🔁 **Checkpoint B.** Paste B3's output — I need to see `dimensions: 384`,
`metric: cosine`, and the `kind` metadata index present. **Rollback if
abandoning:** `npx wrangler vectorize delete glim-coord-memory`.

---

## Phase C — Code lands (🤖, follow-on PR)

Once Checkpoint B is green, I open a PR that adds:

1. **`wrangler.toml` binding** (you'll deploy it in Phase D):
   ```toml
   [[vectorize]]
   binding = "COORD_MEMORY"
   index_name = "glim-coord-memory"
   ```
2. **`src/agents/memoryClientEdge.ts`** — `consultMemory`/`emitTrace` over
   `env.AI` (`@cf/baai/bge-small-en-v1.5`, query-side prefix applied) +
   `env.COORD_MEMORY.query/upsert`, reusing the existing `_computeBias`
   unchanged.
3. **A `COORD_MEMORY_MODE` switch** in `memoryClient.ts`:
   - `off` (default) — today's GCP behavior, untouched.
   - `shadow` — compute the edge result *alongside* GCP, log both + latencies,
     **act on GCP**. No behavior change; pure measurement.
   - `active` — act on the edge result; GCP becomes the fallback.
   Selected by binding presence + a `COORD_MEMORY_MODE` var, so removing the
   binding or setting `off` is an instant revert.
4. **An Access-gated backfill route** `POST /admin/coord-memory/backfill`
   (the `/admin/*` prefix is already Access-gated by `middleware/access.ts`).
   It pages `getRecentCoordinationTraces` from D1 (`env.LEDGER`), embeds each
   via Workers AI, and upserts to Vectorize — the "re-embed before you query"
   step. D1 remains the source of truth, so this is safe to re-run.
5. **Unit tests** for the edge bias math + a `wrangler dev` integration test of
   a query/upsert round-trip.

I'll post the PR link here. **Nothing in it changes live behavior** — it ships
in `off` mode.

---

## Phase D — Deploy + backfill (👤, ~15 min)

After the Phase C PR merges:

```bash
# D1. Deploy the worker with the new binding (still COORD_MEMORY_MODE=off).
npx wrangler deploy

# D2. Backfill: re-embed the coordination traces from D1 into Vectorize.
#     Uses the internal token the other admin routes use. I'll give the exact
#     header in the PR; shape:
curl -sS -X POST https://glim-think-v1.aw-ab5.workers.dev/admin/coord-memory/backfill \
  -H "Authorization: Bearer $GLIM_INTERNAL_TOKEN" \
  -H "Content-Type: application/json" -d '{"limit": 500}'

# D3. Confirm the vectors landed.
npx wrangler vectorize get glim-coord-memory   # vectorsCount should be > 0
```

🔁 **Checkpoint D.** Paste the backfill response (it reports `embedded` /
`skipped` / `errors`) and D3's `vectorsCount`. **Rollback:** the deploy is
inert in `off` mode; to fully revert, redeploy the prior version
(`npx wrangler rollback`) — the index just sits unused.

---

## Phase E — Shadow mode: measure before trusting (👤, 1–2 days)

```bash
# E1. Turn on shadow mode (measurement only; live picks still use GCP).
npx wrangler deploy --var COORD_MEMORY_MODE:shadow
#   (or set it in the dashboard / [vars]; I'll wire whichever you prefer.)

# E2. Watch the compare logs as real coordination happens. Each consultMemory
#     logs: edge_latency_ms, gcp_latency_ms, and whether the two agreed on the
#     top-biased strategy.
npx wrangler tail --name glim-think-v1 --format json | grep coord_memory_shadow
```

Let it run over real traffic (a day is plenty given hourly broadcasts + the
nightly sweep). We want two things from the logs:

- **Latency:** edge p50/p95 vs GCP p50/p95 against the 800ms `consultMemory`
  budget. The whole point is that edge-local wins here.
- **Agreement:** how often edge and GCP pick the same top strategy. High
  agreement + lower latency = safe to promote.

🔁 **Checkpoint E.** Paste ~20–50 `coord_memory_shadow` log lines (or a
`wrangler tail` capture). I'll summarize the latency percentiles and agreement
rate, and we decide together whether to flip to `active`.

---

## Phase F — Activate + canary (👤 + 🤖, joint)

Only after Checkpoint E looks good:

```bash
# F1. Flip to active. Edge now drives; GCP is the fallback on any edge error.
npx wrangler deploy --var COORD_MEMORY_MODE:active

# F2. Verify a known query end-to-end via the debug route (added in Phase C):
curl -sS "https://glim-think-v1.aw-ab5.workers.dev/admin/coord-memory/query?q=high-stakes+synthesis+across+models" \
  -H "Authorization: Bearer $GLIM_INTERNAL_TOKEN" | jq '{latency_ms, top: .bias}'

# F3. Watch for edge errors falling back to GCP.
npx wrangler tail --name glim-think-v1 --format json | grep coord_memory
```

🔁 **Checkpoint F.** Paste F2 + a few minutes of F3. If error-fallback rate is
near zero and latency holds, edge memory is live. **Instant rollback at any
time:** `npx wrangler deploy --var COORD_MEMORY_MODE:shadow` (or `:off`) — no
data migration, the binding just goes quiet.

---

## After it's live — decisions for a later pass (not blocking)

- **Does the GCP `evidence-index` service retire or pivot?** With the flywheel
  on the edge, GCP pgvector's remaining edge is relational/metadata queries and
  public-Library search. Decide deliberately (RFC §4.2) — don't leave two live
  memory tiers by accident.
- **Keep `emitTrace` dual-writing** (D1 + Vectorize, and optionally GCP) until
  GCP's role is decided, so no history is stranded.
- **Literaturist `CORPUS_INDEX`** (768-dim, still dormant) is untouched by this
  runbook and independent of it.

## What to report back, in one line per phase

`A: <indexes present? EVIDENCE_* secrets present?>` ·
`B: <get output: dims/metric/metadata index>` ·
`D: <backfill embedded/errors, vectorsCount>` ·
`E: <tail capture>` ·
`F: <query latency + fallback rate>`

I turn each report into the next code step or a go/no-go.

## Cost note

Trace volume is small (≤500 recent traces × 384 dims), so Vectorize storage and
query cost is negligible, and `@cf/baai/bge-small-en-v1.5` on Workers AI is in
the low/free neuron tier at this volume. Backfill is a one-time ~500-vector
embed. No meaningful ongoing cost beyond what the worker already incurs.
