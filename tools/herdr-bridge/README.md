# herdr-bridge

Per-machine daemon that connects a local [herdr](https://herdr.dev) agent
runtime to the `glim-think` control plane. Architecture, auth and failure
semantics: `glim-think/docs/herdr-bridge.md`.

Two loops, both outbound-only:

- **telemetry** — `events.subscribe` on the herdr socket → one beat per agent
  status transition → `POST /feed/beats`.
- **dispatch** — poll `GET /bridge/jobs/next?machine_id=…` → herdr workspace
  → `agent start` → `agent prompt --wait` → `agent read` →
  `POST /bridge/jobs/:id/result`.

## Requirements

- Node ≥ 22.18 (runs `.ts` directly via type stripping; no build step).
  Node 26 on aledev.
- A running herdr server (`herdr` 0.9.0, protocol 22) and its socket.
- Zero runtime dependencies. `npm install` only pulls `typescript` +
  `@types/node` for `npm run typecheck`.

## Configuration (env)

| Variable | Required | Default | Meaning |
| --- | --- | --- | --- |
| `GLIM_WORKER_URL` | yes | — | e.g. `https://glim-think-v1.aw-ab5.workers.dev` |
| `GLIM_BRIDGE_TOKEN` | yes | — | The worker's `HERDR_BRIDGE_TOKEN` secret (bearer). |
| `MACHINE_ID` | no | hostname | Identity for job addressing and beat tagging. `[A-Za-z0-9][A-Za-z0-9._:-]{0,127}` |
| `HERDR_SOCKET_PATH` | no | `$XDG_CONFIG_HOME/herdr/herdr.sock` | herdr server socket. |
| `POLL_INTERVAL_SECONDS` | no | `15` | Sleep between polls when the queue is empty. |
| `BRIDGE_POLL_WAIT_SECONDS` | no | `15` | Server-side long-poll hint (worker caps at 20). |
| `BRIDGE_JOB_TIMEOUT_MS` | no | `1800000` | Explicit timeout for `agent.prompt` wait. |
| `BRIDGE_AGENT_START_TIMEOUT_MS` | no | `60000` | Readiness wait after `agent.start`. |
| `BRIDGE_AGENT_SETTLE_MS` | no | `3000` | Grace after first `idle` before prompting. |
| `BRIDGE_READ_LINES` | no | `80` | Lines of `recent_unwrapped` output for the excerpt. |
| `BRIDGE_KEEP_WORKSPACES` | no | `failed` | `always` / `failed` / `never` — keep the herdr workspace after a job. |
| `BRIDGE_WORKSPACE_CWD` | no | cwd | cwd for job workspaces (e.g. the repo checkout). |
| `BRIDGE_WORKSPACE_LABEL` | no | `bridge` | Workspace label prefix; jobs get `<prefix>-<job id prefix>`. |
| `BRIDGE_TELEMETRY` / `BRIDGE_DISPATCH` | no | `true` | Disable a loop. |
| `BRIDGE_MAX_BACKOFF_MS` | no | `300000` | Cap for reconnect/retry backoff. |
| `BRIDGE_LOG_LEVEL` | no | `info` | `debug` / `info` / `warn` / `error`. |

## Run

```bash
cd tools/herdr-bridge
export GLIM_WORKER_URL=https://glim-think-v1.aw-ab5.workers.dev
export GLIM_BRIDGE_TOKEN=...           # never commit; use an env file with 0600
export MACHINE_ID=aledev
export BRIDGE_WORKSPACE_CWD=/home/alex/Dev/lupine/lupine-rhizo
node src/main.ts
```

Logs are JSON lines on stdout (`component`, `event`, fields). A `stats`
line is emitted every minute. `SIGINT`/`SIGTERM` stop the loops, drain
buffered beats once, and exit 0.

Enqueue a job (operator side, any gated credential):

```bash
curl -sS -X POST "$GLIM_WORKER_URL/bridge/jobs" \
  -H "Authorization: Bearer $GLIM_BRIDGE_TOKEN" -H 'Content-Type: application/json' \
  -d '{"machine_id":"aledev","agent_kind":"hermes","prompt":"Reply with PONG.","campaign_id":null}'
```

### systemd (user unit, on demand — not enabled by default)

```ini
[Unit]
Description=herdr-bridge (glim-think ↔ herdr)
After=default.target

[Service]
EnvironmentFile=%h/.config/herdr-bridge/env
WorkingDirectory=%h/Dev/lupine/lupine-rhizo/tools/herdr-bridge
ExecStart=/usr/bin/node src/main.ts
Restart=on-failure
RestartSec=5
```

## Test

```bash
npm install          # dev deps only
npm run typecheck    # tsc, erasableSyntaxOnly (matches Node type stripping)
npm test             # node --test with a fake herdr socket server + fake worker fetch
```

## Smoke test against the live herdr

With the worker side pointed at `wrangler dev` (`DEV_MODE=true`, local D1
with migrations applied) or production:

```bash
GLIM_WORKER_URL=http://127.0.0.1:8787 GLIM_BRIDGE_TOKEN=dev MACHINE_ID=aledev \
BRIDGE_KEEP_WORKSPACES=always BRIDGE_LOG_LEVEL=debug node src/main.ts
```

Then enqueue a job for `aledev`; watch for `job_claimed`, `agent_ready`,
`job_reported` and a `bridge-…` workspace in `herdr workspace list`.

## Layout

```
src/config.ts     env → BridgeConfig
src/log.ts        JSON logger, sleep, backoff
src/herdr.ts      socket JSON-RPC client (one request per connection; streaming subscribe)
src/worker.ts     control-plane HTTP client (bearer auth)
src/telemetry.ts  events.subscribe → beats (buffered, retried, deduped)
src/dispatch.ts   poll → workspace → agent → prompt → result
src/main.ts       wiring, signals, stats
test/             node:test suites + helpers (fake herdr server, fake worker)
```
