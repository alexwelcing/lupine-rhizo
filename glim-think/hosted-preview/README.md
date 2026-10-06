# Isolated hosted research workspace

This is a separate `cf` project named **lupine-workspace-preview**. It reuses
the real ResearchWorkspace, Access middleware, model catalog and bundled UI.
It does not import `src/server.ts` or change the production Wrangler project.

Only new preview KV, D1, a SQLite Durable Object and Workers AI are bound.
Every HTTP route, asset, chat history request and WebSocket handshake requires
Access. The runtime discards extra keys, telemetry settings and authentication
bypass flags. **Auto · Clef planning** is enabled with a fixed preview policy;
manual model selections bypass Clef. The banner and system prompt identify
synthetic ledger data; model calls and conversation persistence are real.
Imported **Research runs** use separate private PI receipt records and can be
read by chat. Synthetic legacy evidence and report-analysis Progress remain
distinct from those actual research discussions; none proves a new experiment ran.

## Clef planning in this preview

Auto makes one batched call for model route, saved-evidence selection and
research-task triage. It maps `fast` to `workers-flash` and `deep`, `code`, and
`research` to `workers-deep`. Each choice is independently gated at confidence
`0.7` and probability margin `0.15`, with ties rejected. The deadline is `1500`
ms with no retry. A rejected route keeps `workers-flash`; independently accepted
evidence/task hints can still help the response. Clef does not expand tool access.

The latest user text is capped at 2,000 characters, retaining the beginning and
end when truncated. Matching tool continuations reuse the validated decision;
fresh user turns classify again. Each private conversation retains at most 20
decision metadata entries, visible under **Recent reply decisions**. Routing
metadata excludes raw prompts and classifier responses; ordinary chat history
is stored separately.

The policy is fixed by `workspacePreviewEnv`, not extra caller-supplied bindings.
Generic deployments remain disabled unless explicitly enabled. See
[routing behavior](../docs/clef-routing.md), the
[synthetic evaluation](../docs/clef-evaluation-2026-10-06.md) and the
[private evaluation runner](../scripts/testing/CLEF-ROUTING-EVAL.md). Classifier
label agreement does not establish generation quality or scientific certainty.

## Install the separate tooling

From `glim-think`, install its normal dependencies if needed. Then:

```sh
cd hosted-preview
npm ci --ignore-scripts --no-audit --no-fund
```

Node 22.18+ is required. The isolated lockfile pins `cf` 1.0.0-beta.12 and
Wrangler 4.136.0. The existing production package and lockfile are unchanged.
The newer Wrangler is used only as cf's bundler; deployment uses cf's existing
OAuth profile. No Wrangler login, auth-file reads or credential copying is needed.

## Provision preview resources and Access

First obtain the agreed Cloudflare account ID, preview hostname, operator email,
Access identity provider and session duration. Create a new Access application
covering the entire `lupine-workspace-preview.<account-subdomain>.workers.dev`
hostname, with an Allow policy limited to that operator. Record its audience.
The worker verifies the same team, audience and email itself, so it fails closed
until those settings and a valid Access JWT are present.

Resource commands below deliberately run from **glim-think**, outside this
directory: the new project's required configuration is not populated yet.
Set `CLOUDFLARE_ACCOUNT_ID` in that launching process to the confirmed account.
These commands create remote resources; run them only for the approved preview.

```sh
cd ..
node hosted-preview/node_modules/cf/bin/cf kv namespaces create --title lupine-workspace-preview-config
node hosted-preview/node_modules/cf/bin/cf d1 create --name lupine-workspace-preview-ledger
```

Record the returned KV `id` and D1 `uuid`. Verify both names and account before
using them. If a name already exists, inspect its purpose before reusing it;
do not delete or replace an existing resource to resolve the conflict.
Never use the production `CONFIG` or `LEDGER` IDs.

Seed only that new D1 database using the standalone fixture:

```sh
node hosted-preview/node_modules/cf/bin/cf d1 query "$PREVIEW_LEDGER_D1_ID" --sql "$(cat hosted-preview/seed.sql)"
```

The SQL contains three small tables and one synthetic row per table. It has
no production data and is safe to reapply to this preview database.

For the private Research runs surface, apply migration 0020 only to the approved
preview D1 database (inspect the ID/name/account first):

```sh
node hosted-preview/node_modules/cf/bin/cf d1 query "$PREVIEW_LEDGER_D1_ID" --sql "$(cat migrations/0020_workspace_research_runs.sql)"
```

This creates an empty private receipt table and index. It starts no work and
copies no production ledger. If the retained Progress feed is enabled, its
separate migration 0018 is also required. Import real local cycle snapshots
through the signed-in operator control described in
[research-workspace.md](../docs/research-workspace.md#private-local-research-receipts).
No service-token or machine authorization change is needed for this manual path.

## Supply runtime settings and build

Copy `.env.example` to `.env` in this directory and fill its six inputs with the
new resources and approved Access details. `.env` and `.cloudflare/` are ignored.
`PREVIEW_ACCESS_TEAM_DOMAIN` accepts either the team name or its
`<team>.cloudflareaccess.com` hostname. The scripts explicitly load these inputs;
cf's automatic `.env` handling alone does not load arbitrary preview variables.
Do not add provider API keys or Cloudflare tokens. cf reads its existing login.

```sh
cd hosted-preview
npm run build
npm run check:deploy
```

Both commands are local checks. The first also rebuilds the existing UI source.
The second validates the already-built output without uploading it.
Inspect `.cloudflare/output/v0/`: the Worker name must be
`lupine-workspace-preview`; bindings must be exactly `RESEARCH_WORKSPACE`,
`CONFIG`, `LEDGER`, `AI`, `CF_ACCESS_TEAM_DOMAIN`, `CF_ACCESS_AUD`, `ADMIN_EMAIL`.
There must be no cron/queue triggers, Workflows, production resource IDs,
provider secrets, tail consumers or telemetry exporters.

The five fixed Clef settings are injected inside the preview runtime adapter;
they are not additional deployment bindings or `.env` inputs. Inspect that the
built adapter preserves the Auto mapping, `0.7`/`0.15` gates and `1500` ms deadline.

**Rebuild after changing any setting.** `--prebuilt` deploys the values captured
in Build Output, not newly edited environment values. Placeholder IDs used in an
offline check are not deployment configuration.

After those checks and approval for the concrete resource/authentication setup:

```sh
npm run deploy
```

This deploys only this separately named Worker using the inspected Build Output.
Do not run the repository's production deployment workflow for this preview.

## Live acceptance

- Without Access, `/workspace`, `/workspace/app.js`, history and WebSockets must
  be rejected or redirected to sign-in before storage/model calls.
- With the approved operator, create a conversation and verify its actual
  provider/model identity, streaming, Stop reply and reload recovery.
- In Auto, inspect model route, accepted evidence/task hints, fallback status
  and classifier latency. Confirm manual model selection bypasses Clef, tool
  continuations reuse the turn decision, and recent metadata survives reload.
  Exercise a long request to check the beginning/end truncation notice. The
  private CLI evaluation is separate from these hosted checks.
- Open the same conversation URL on the other authorized device and confirm
  history continuity. This is a shared operator workspace, not per-user tenancy.
- Request synthetic evidence and verify record IDs and fixture labeling.
- Import a validated local cycle, refresh **Research runs**, and verify exact
  job/result fingerprints and honest pending/stopped/completed stage labels.
  Ask chat to read that run ID and distinguish the real recorded research
  discussion from an experiment proposal. An empty feed or successful import
  alone does not verify model quality or end-to-end remote execution.
- Keep model checks small. Account entitlement and generated content must be
  verified separately from a successful bundle or a configured model catalog.
- `/run`, `/fleet/run` and other agent namespaces must remain unavailable.

Private system validation comes first. Next, demonstrate useful evidence-backed
runs and prepare a series of reviewable progress clips. Explicit user acceptance
of the system and clips is required before any new Library publication, including
public Library previews. Clip creation remains follow-up work; this preview does
not create clips or automate publication.

Focused offline checks from `glim-think`:

```sh
npx vitest run src/workspace/__tests__/hostedPreview.test.ts
```

No production secrets, cron schedules, queue consumers or experiment resources
are needed. Removing this preview later requires a separately reviewed cleanup
of its Worker, Access application, KV and D1, without touching production.

References: [cf projects and prebuilt deployments](https://developers.cloudflare.com/cf/projects/),
[programmatic configuration](https://developers.cloudflare.com/cf/projects/cloudflare-config/),
[Wrangler build settings](https://developers.cloudflare.com/cf/wrangler/migrate/#build-settings).
