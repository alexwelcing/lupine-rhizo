# Coding attempts in the Rhizo agenda

`ledger.ts` uses the canonical `LEDGER` D1 database and its existing
`intelligence_tasks` table. Apply migration `0026_coding_attempt_ledger.sql`
after the agenda schema exists. It does not create another scheduler, seed
tasks, execute commands, call providers or publish results.

An authorized task must have `domain='coding'` and JSON payload
`{"codingInputSha256":"<SHA256 of exact canonical manifest JSON>"}`. The
runner passes that same manifest string and digest. Admission accepts either
a queued, unowned task or a task already claimed by the exact configured
`CODING_AGENT_ID`. The task becomes running in the same D1 batch that appends
its immutable attempt. A task permits one lifetime attempt; no timeout,
failure, unknown result or manual generic requeue creates another allowance.

**Separate rollout requirement:** deploying only the dedicated coding Worker
does not release this checkout's generic-agenda exclusion to the existing
Rhizo Worker. Until that main integration is released, reserve each live task
with `status='claimed'` and `claimed_by` equal to the dedicated Worker's exact
`CODING_AGENT_ID` (normally `cloudflare-coding-runner`) before submission.
Pin its payload digest at the same time. This prevents the older generic
scheduler from acquiring a queued coding task. The updated generic
`claimAgendaTasks` excludes the coding domain without changing other domains.

## Internal interface

- `admitCodingAttempt(db, {taskId, attemptId, ownerId, inputSha256, manifestJson})`
  returns `admission: 'created' | 'replay'` and the stored attempt. Only a fresh
  admission may allow the runner's already-durable dispatch intent to proceed.
  A replay reconciles metadata and never authorizes execution.
- `getCodingAttempt(db, attemptId)` returns stored identity, raw terminal
  receipt and separate acceptance, or null. It has no runtime wake side effect.
- `recordCodingTerminal(db, terminal)` appends a raw receipt and atomically
  projects the agenda to blocked. The raw receipt bytes must hash correctly
  and carry the exact `taskId`, `attemptId` and `inputSha256`. `succeeded`
  requires exit zero, a verified archived-evidence reference and confirmed
  cleanup. An unknown result remains unknown even if cleanup later succeeds.
- `recordCodingAcceptance(db, review)` requires the exact terminal hash,
  identity and reviewer. Only a separately accepted raw success marks the
  coding task done. Rejection remains blocked. Neither decision constitutes
  scientific acceptance, merge, deployment or Library publication.

The terminal and acceptance functions are internal trusted-runner/reviewer
interfaces. Their booleans are not authenticated by TypeScript: do not expose
an endpoint allowing clients to supply arbitrary terminal or acceptance
records. The runner must actually establish archive readback and cleanup.

All three ledger tables forbid update/delete. Agenda triggers preserve owner,
input and exact post-terminal status/result/artifact/completion projections.
Exact duplicate records return replay; changed identities or evidence conflict.
A generic pre-terminal block does not strand an exact-owner terminal receipt.
Lost D1 acknowledgement requires readback or exact metadata reconciliation,
never another command execution. R2 and D1 are not a distributed transaction;
the runner must retain uncertain archive/commit outcomes and its consumed
dispatch intent.

## Focused local verification

From `glim-think`:

```sh
node node_modules/vitest/vitest.mjs run --config src/coding/__tests__/vitest.config.mjs src/coding/__tests__/ledger.test.ts src/__tests__/agendaClaims.test.ts --maxWorkers=1
node coding-runner/node_modules/typescript/bin/tsc -p tsconfig.coding.json
```

The ledger tests use actual Node SQLite transactions with injected commit
acknowledgement loss and rollback, not a live Cloudflare database. Runtime,
platform deployment, protected access and actual coding execution remain
separate validation gates.
