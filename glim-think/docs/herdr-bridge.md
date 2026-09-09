# herdr bridge — dispatching research work to local machines

`glim-think` is the durable control plane; agents that do the actual work run
in [herdr](https://herdr.dev) (a terminal workspace multiplexer for coding
agents) on local machines. herdr has **no HTTP API and no inbound network
surface** — it speaks newline-delimited JSON-RPC over a Unix socket — so a
per-machine daemon bridges the two with outbound-only traffic.

## Components

| Role | Where | Responsibility |
| --- | --- | --- |
| Control plane | Cloudflare Worker `glim-think-v1` | Owns the job queue (D1 `herdr_bridge_jobs`), gates access, ingests beats, fans campaign beats into `CampaignConsole`. |
| Bridge | `tools/herdr-bridge/` — one daemon per machine, `MACHINE_ID` | Polls for jobs, drives herdr, posts results; subscribes to herdr events and forwards agent lifecycle as beats. |
| Agent runtime | `herdr` server (socket `~/.config/herdr/herdr.sock`) | Workspaces/panes, starts agents (`hermes`, `claude`, `codex`, `kimi`, …), detects `idle/working/blocked/done`. |

Scaling to N machines is one bridge process per machine with a distinct
`MACHINE_ID`; jobs are addressed to a `machine_id`, and every beat is tagged
with it. Nothing on the worker side is per-machine except rows.

## Flow 1 — dispatch (worker → bridge → herdr → worker)

```
operator/agent ──POST /bridge/jobs {machine_id, agent_kind?, prompt, campaign_id?}──▶ D1 (pending)
bridge ──GET /bridge/jobs/next?machine_id=X&wait_seconds=15──▶ worker claims oldest pending (atomic UPDATE…RETURNING)
bridge ──herdr: workspace.create → agent.start(kind) → agent.wait(idle) → settle
       ──herdr: agent.prompt(text, wait{timeout_ms}) → agent.read(recent_unwrapped)
bridge ──POST /bridge/jobs/:id/result {status, output_excerpt, beat}──▶ D1 (terminal) + lab_beats (+ console fan-in)
```

- One job at a time per bridge; each job gets a fresh herdr workspace
  labelled `bridge-<job prefix>`. Workspaces are closed on `done`, kept on
  anything else (`BRIDGE_KEEP_WORKSPACES`).
- Job status: `pending → claimed → done | failed | blocked | timeout`.
  `blocked` means herdr saw an approval/question dialog; the workspace is
  left running for a human.
- `agent_kind` defaults to `hermes`. The prompt is sent verbatim through
  `agent.prompt` with an explicit `timeout_ms` (`BRIDGE_JOB_TIMEOUT_MS`).
- The result beat carries `job_id`, `machine_id`, `campaign_id` (from the
  job row, not the bridge), `source="herdr-bridge"`, and lands via the same
  `ingestBeat` path as every other producer, so campaign jobs appear in the
  console with no extra wiring.

## Flow 2 — telemetry (herdr → bridge → /feed/beats)

The bridge keeps one long-lived `events.subscribe` connection for
`pane.agent_status_changed`. Every transition (`idle→working`, `working→done`,
…) becomes a beat:

```
beat_id  herdr:<machine_id>:<pane_id>:<seq>:<ts>       (idempotent on retry)
agent    herdr-bridge/<machine_id>
metrics  {source:"herdr-bridge", machine_id, pane_id, workspace_id, agent_kind,
          from_status, to_status, transition, job_id?, campaign_id?}
```

Beats are queued in memory and sent by a single sender so a worker outage
never stalls the herdr event loop. All agents on the machine are observed,
not only bridge-dispatched ones; panes owned by a job get `job_id`.

## Auth

`POST /feed/beats` authenticates GCP producers with a Google OIDC JWT whose
`email` must equal `TASKS_CONSUMER_INVOKER_SA`. A bridge host has no GCP
identity, so it uses a **dedicated shared secret**, `HERDR_BRIDGE_TOKEN`,
presented as `Authorization: Bearer …`. This mirrors `LUPINE_APP_TOKEN`
(scoped bearer for one route) rather than `INTERNAL_TASK_TOKEN` (global
`X-Internal-Token` bypass): a bridge machine should never be able to reach
`/admin/*` or `/run`.

- `middleware/access.ts`: `/bridge/*` is gated for every method except
  `OPTIONS` (`GET /bridge/jobs/next` is a claim, and prompts are not public).
  The bearer is accepted only under `/bridge/`; Access JWTs and
  `X-Internal-Token` still work there for operators.
- `feed/beats.ts`: the same bearer short-circuits OIDC verification; any
  other bearer goes through the Google JWKS path unchanged.
- Bridge env: `GLIM_BRIDGE_TOKEN` = the worker's `HERDR_BRIDGE_TOKEN`.
  Set it with `wrangler secret put HERDR_BRIDGE_TOKEN` (add to
  `docs/secrets.md` list). Rotate by setting the secret and restarting bridges.

## Failure and retry semantics

| Condition | Behaviour |
| --- | --- |
| Bridge down / machine off | Jobs stay `pending`; nothing is lost. On restart the bridge resumes polling. |
| Bridge crashes mid-job | Row stays `claimed`. After `STALE_CLAIM_SECONDS` (2h) with `attempts < 3` the claim query re-issues it; `attempts` is recorded on the result beat. After 3 attempts it stops being dispatched and needs an operator. |
| herdr unreachable (socket missing) | Telemetry resubscribes with capped exponential backoff + jitter. Dispatch reports the job `failed` with the socket error so the queue does not stall behind a dead runtime. |
| Worker unreachable | Poll and beat sends back off (≤ `BRIDGE_MAX_BACKOFF_MS`). Beats buffer in memory (bounded at 1000, oldest dropped and counted). Result posts retry indefinitely on 5xx/network; a 4xx (e.g. 409 already terminal) is logged and abandoned. |
| Agent blocked on a dialog | `agent.prompt` settles `blocked` → result `blocked`, workspace kept, excerpt included. |
| Prompt stalled (no activity within 5s) | Bridge sends one `enter` and waits for a settled state; observed with hermes when the prompt arrives during the initial redraw (hence `BRIDGE_AGENT_SETTLE_MS`). |
| Job timeout | herdr `timeout` error → result `timeout`, excerpt salvaged from the pane. |
| Result beat rejected by the worker | Job is left `claimed` (not closed), response is the beat error; the bridge retries only if it was 5xx. |

Idempotency: `beat_id`s are deterministic and `lab_beats` is
`ON CONFLICT DO NOTHING`; `POST …/result` on a terminal job returns 409.

## Storage and migration

`migrations/0017_herdr_bridge_jobs.sql` adds `herdr_bridge_jobs` (mirrored in
`schema.sql`). It is applied together with the pending **0015/0016 batch**
(`wrangler d1 migrations apply LEDGER`), not on its own — the three are one
deploy unit. Until applied, `/bridge/*` returns 500 from D1 and the bridge
backs off harmlessly.

## Operating

- Run: see `tools/herdr-bridge/README.md` (env vars, systemd unit example).
- Enqueue: `POST /bridge/jobs` with an Access JWT / `X-Internal-Token` /
  bridge bearer. Inspect: `SELECT … FROM herdr_bridge_jobs`.
- Observe: bridge beats in `GET /feed/beats` (`metrics.source = "herdr-bridge"`),
  bridge stdout is JSON lines (`component`, `event`).

Known gaps (next wiring, not passing state): no per-machine concurrency
(one job at a time); no `GET /bridge/jobs/:id` read route; job prompts are
plain text (no artifact upload yet — use the excerpt + workspace).
