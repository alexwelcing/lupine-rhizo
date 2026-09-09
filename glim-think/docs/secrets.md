# glim-think deployment secrets

`wrangler.toml` must not contain production runtime values in `[vars]`. Put every value below in Cloudflare Worker secrets (or bind them from Cloudflare Secrets Store) before deploying `glim-think-v1`.

Cloudflare Worker secrets are encrypted and are not overwritten by `wrangler deploy`. If the Worker is recreated, re-run the same `wrangler secret put` commands.

## Required production secrets

### Model and provider credentials

- `OPENAI_API_KEY`
- `ANTHROPIC_API_KEY`
- `GOOGLE_API_KEY`
- `ZAI_API_KEY`
- `MINIMAX_API_KEY`
- `HF_API_KEY`

### Cloudflare Access gate

- `CF_ACCESS_TEAM_DOMAIN` — team subdomain only, for example `example` for `example.cloudflareaccess.com`
- `CF_ACCESS_AUD` — Access application audience tag
- `ADMIN_EMAIL` — allowed administrator email for gated write/admin routes
- `INTERNAL_TASK_TOKEN` — shared secret for internal queue-to-Worker subrequests

Do not set `DEV_MODE` in production. Use `DEV_MODE=true` only in local `.dev.vars`.

### Phoenix / telemetry

- `PHOENIX_COLLECTOR_ENDPOINT`
- `PHOENIX_API_KEY`
- `PHOENIX_PROJECT_NAME`
- `PHOENIX_SYNC_TOKEN`
- `PHOENIX_RELAY_URL`
- `PHOENIX_RELAY_TOKEN`
- `ATLAS_TELEMETRY_CONFIG` or its discrete fallbacks `ATLAS_REVISION` and `MATHLIB_REVISION`

### GCP research dispatch and MLIP runtime config

These values include project ids, service-account emails, Cloud Run URLs, and GCS paths. Treat them as deployment secrets/config and keep them out of git.

- `WORKER_URL`
- `TASKS_CONSUMER_URL`
- `TASKS_CONSUMER_AUDIENCE`
- `TASKS_CONSUMER_INVOKER_SA`
- `GCP_SA_KEY`
- `GCP_PROJECT_ID`
- `GCP_TASKS_LOCATION`
- `GCP_TASKS_QUEUE`
- `MLIP_BASELINE_MANIFEST_URL`
- `MLIP_BASELINE_OUTPUT_PREFIX`
- `MLIP_DISTILL_SUPPORT_MANIFEST_URL`
- `MLIP_5X5X3_OUTPUT_PREFIX`
- `MLIP_DISTILL_POLICY_ENGINE`
- `MLIP_DISTILL_RIBBON_VERSION`
- `MLIP_DISTILL_POLICY_URL`
- `MLIP_DISTILL_POLICY_URLS_JSON`

### Evidence index

- `EVIDENCE_INDEX_URL`
- `EVIDENCE_INGEST_TOKEN`

## Migration commands

Run from `glim-think/` with `CLOUDFLARE_API_TOKEN` set in the shell. Enter each value interactively when prompted; do not paste values into committed files.

```bash
export CLOUDFLARE_API_TOKEN=... # do not commit or print this value

for name in \
  OPENAI_API_KEY ANTHROPIC_API_KEY GOOGLE_API_KEY ZAI_API_KEY MINIMAX_API_KEY HF_API_KEY \
  CF_ACCESS_TEAM_DOMAIN CF_ACCESS_AUD ADMIN_EMAIL INTERNAL_TASK_TOKEN \
  PHOENIX_COLLECTOR_ENDPOINT PHOENIX_API_KEY PHOENIX_PROJECT_NAME PHOENIX_SYNC_TOKEN PHOENIX_RELAY_URL PHOENIX_RELAY_TOKEN \
  ATLAS_TELEMETRY_CONFIG ATLAS_REVISION MATHLIB_REVISION \
  WORKER_URL TASKS_CONSUMER_URL TASKS_CONSUMER_AUDIENCE TASKS_CONSUMER_INVOKER_SA GCP_SA_KEY \
  GCP_PROJECT_ID GCP_TASKS_LOCATION GCP_TASKS_QUEUE \
  MLIP_BASELINE_MANIFEST_URL MLIP_BASELINE_OUTPUT_PREFIX MLIP_DISTILL_SUPPORT_MANIFEST_URL \
  MLIP_5X5X3_OUTPUT_PREFIX MLIP_DISTILL_POLICY_ENGINE MLIP_DISTILL_RIBBON_VERSION \
  MLIP_DISTILL_POLICY_URL MLIP_DISTILL_POLICY_URLS_JSON \
  EVIDENCE_INDEX_URL EVIDENCE_INGEST_TOKEN
 do
  npx wrangler secret put "$name"
done
```

Verify presence without printing values:

```bash
npx wrangler secret list --name glim-think-v1
```

Cloudflare resource binding identifiers that Wrangler requires for KV, D1, R2, Queues, Durable Objects, and Workflows remain in `wrangler.toml`; those are binding coordinates, not runtime secrets.
