# herdr bridge — dispatching research work to local machines

`glim-think` is the durable control plane; agents that do the actual work run
in [herdr](https://herdr.dev) (a terminal workspace multiplexer for coding
agents) on local machines. herdr has **no HTTP API and no inbound network
surface** — it speaks newline-delimited JSON-RPC over a Unix socket — so a
per-machine daemon bridges the two with outbound-only traffic.

## Scientific handoff upgrade (local code; not deployed)

Migration **0019** adds private scientific receipts and fenced claims. Stop old
bridge daemons before applying it: their result payloads lack the required
`machine_id` and `claim_token`, so they are deliberately incompatible. The updated local daemon forwards fenced results for general jobs, but blocks
scientific-role jobs before creating any workspace or agent. Those jobs require
a bounded scientific CLI worker with validated completion and enforced tool
limits. No daemon is started and no credentials, runtime configuration or cloud
resources are changed by this code.

The existing Orchestrator has three optional tools:

- `dispatch_mac_discovery`: Codex on the explicitly configured Mac; literature
  discovery and a falsifiable hypothesis.
- `dispatch_aledev_critique`: Claude on `aledev`; independent critique of a
  completed discovery receipt. `parentJobId` and a matching question are required;
  agenda/campaign linkage is inherited. The handoff saves the SHA-256 of that
  exact discovery receipt; a critique must identify that same job and hash.
- `get_scientific_job`: private, bounded result retrieval. Pending, claimed and
  uncertain outcomes are never represented as completed scientific work.

These tools are absent unless `SCIENTIFIC_BRIDGE_ENABLED` is exactly `true` and
`SCIENTIFIC_BRIDGE_MAC_MACHINE_ID` is a valid identifier distinct from `aledev`.
No enablement is committed. Handoffs persist in `herdr_bridge_jobs`, with optional
`agenda_task_id`, `campaign_id`, and `parent_job_id`; they do not automatically
complete an agenda task or resume a model conversation.

The structured receipt is validated on write and read:

```text
sources: [{id, title, url, excerpt}]   # 1–8, HTTPS, no embedded credentials
question, hypothesis, competingExplanation, falsifier, critique
optional: closestPriorArt, noveltyBoundary, controls[]
critique only: reviewedDiscovery: {jobId, receiptSha256}
cheapestExperiment: {proposal, successCriterion, execution: "not_started"}
decision: {recommendation: investigate|revise|reject|insufficient_evidence, reason}
```

Reasoning fields are bounded (normally 4,000 characters), receipts at 64 KiB,
and request bodies at 96 KiB. The exact exported contract is
`scientificReceiptSchema` in `src/bridge/jobs.ts`. Scientific completion requires
a receipt matching the saved question. The receipt records an agent's analysis;
schema acceptance does not prove source accuracy, novelty or experiment success.
No command, permission override or experiment execution field is accepted.
Instructions in the generated prompt are **not a sandbox**: the local runner must
enforce its permitted tools, repository, network and approval policy.

**Live-use gate:** the existing shared `HERDR_BRIDGE_TOKEN` still has no
machine-specific identity or role separation. Any holder can enqueue or claim
work for another machine. Fencing proves possession of a claim, not the identity
of the machine. Do not enable unattended remote scientific dispatch until
per-machine credentials and claim/result authorization are added. The private
hosted workspace preview currently exposes no bridge routes or bridge secret.

Scientific receipts and output stay in the private job ledger. Caller-supplied
public beats are rejected for scientific jobs, so research content is not sent
to `/feed/beats` or public CampaignConsole telemetry.

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
bridge ──POST /bridge/jobs/:id/result {machine_id, claim_token, status, output_excerpt?, scientific_receipt?, beat?}──▶ D1 (terminal) + lab_beats (+ console fan-in)
```

- One job at a time per bridge; each job gets a fresh herdr workspace
  labelled `bridge-<job prefix>`. Workspaces are closed on `done`, kept on
  anything else (`BRIDGE_KEEP_WORKSPACES`).
- Job status: `pending → claimed → done | failed | blocked | timeout`.
  Claims carry a fresh `claim_token` and a two-hour `claim_expires_at`; only the
  matching machine/token can close an unexpired claim. One active claim per
  machine is allowed. An expired claim becomes `timeout` with
  `result_uncertain=true` and is never automatically requeued.
  `blocked` means herdr saw an approval/question dialog; the workspace is
  left running for a human.
- `agent_kind` defaults to `hermes`. The prompt is sent verbatim through
  `agent.prompt` with an explicit `timeout_ms` (`BRIDGE_JOB_TIMEOUT_MS`).
- For legacy non-scientific jobs, an optional result beat carries `job_id`,
  `machine_id`, `campaign_id` (from the job row, not the bridge), `source="herdr-bridge"`, and lands via the same
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
| Bridge crashes mid-job | At the next claim or result/read operation, an expired claim becomes `timeout` with `result_uncertain=true`. It is never re-issued. Local work may still be running; reconcile it before explicitly creating any replacement job. |
| herdr unreachable (socket missing) | Telemetry resubscribes with capped exponential backoff + jitter. Dispatch reports the job `failed` with the socket error so the queue does not stall behind a dead runtime. |
| Worker unreachable | Poll and beat sends back off (≤ `BRIDGE_MAX_BACKOFF_MS`). Beats buffer in memory (bounded at 1000, oldest dropped and counted). Result posts retry indefinitely on 5xx/network; a 4xx (e.g. 409 already terminal) is logged and abandoned. |
| Agent blocked on a dialog | `agent.prompt` settles `blocked` → result `blocked`, workspace kept, excerpt included. |
| Prompt stalled | The existing daemon fails closed without sending another Enter or resubmitting the prompt. It may already have been delivered. |
| Job timeout | herdr `timeout` error → result `timeout`, excerpt salvaged from the pane. |
| Optional legacy result beat rejected | The fenced private result remains durably saved. The response contains a telemetry warning; failed optional telemetry cannot cause execution to be replayed. |

Idempotency: `beat_id`s are deterministic and `lab_beats` is
`ON CONFLICT DO NOTHING`. An identical result submitted with the original claim
is acknowledged with `duplicate=true`. Changed, foreign, expired or unfenced
results return 409 (missing required fields return 400). A conditional D1 update
fences races between validation and completion. Neither result retries nor
expiry execute the prompt again. Result delivery does not renew a claim.

## Storage and migration

`migrations/0017_herdr_bridge_jobs.sql` creates the original queue. Apply
`0019_scientific_bridge_claims.sql` before using this upgraded code; it adds claim
credentials, scientific linkage/receipts and uncertainty fields. Existing claimed
rows become uncertain timeouts because their owner cannot be authenticated under
the new protocol. Their history is preserved. This migration has not been applied
remotely as part of this change.

Migration 0018 belongs to the parked Progress feed and is separate from this
handoff implementation. The older `schema.sql` snapshot contains the base queue;
new databases still require migration 0019. Missing schema returns an explicit
500; it is not a successful empty queue.

## Operating

- Run: see `tools/herdr-bridge/README.md` (env vars, systemd unit example).
- Enqueue: `POST /bridge/jobs` with an Access JWT / `X-Internal-Token` /
  bridge bearer. This legacy generic endpoint retains its existing broader
  authority and is not the scientific role gate. Read privately with
  `GET /bridge/jobs/:id`; responses omit prompts, claim tokens and result hashes
  and use `Cache-Control: private, no-store`. Missing jobs return 404 and malformed
  saved receipts fail visibly with 500.
- Observe: bridge beats in `GET /feed/beats` (`metrics.source = "herdr-bridge"`),
  bridge stdout is JSON lines (`component`, `event`).

Remaining live-use gaps: machine-scoped credentials; compatible local runners
with enforced execution limits and durable result delivery; verified Codex/Claude
completion; artifact upload; automatic PI continuation. The updated `tools/herdr-bridge/` supports fenced general-job results and
rejects foreign, missing-token and expired claims. It deliberately reports
scientific jobs as blocked without launching them; the bounded local CLI cycle
is the scientific execution path. Local agent authentication is separate and must be checked without
copying credentials to the cloud. Do not infer scientific completion from a
terminal status or lifecycle beat alone.
