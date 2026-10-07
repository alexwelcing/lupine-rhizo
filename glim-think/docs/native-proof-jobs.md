# Native Cloudflare proof jobs

Proof drafting now has a native cloud execution path: the private workspace →
Cloudflare service binding → Glim Worker + D1 → Anthropic Message Batches API.
There is no Mac process, SSH session, Claude CLI, or laptop worker in this path.
This is proof-candidate generation; it does not run Lean or certify a theorem.

## Operation

Open **Proof jobs** in the private workspace. Supply a newly reviewed mathematical
brief, investigation ID, reason for the next step, and output allowance. One active
job is permitted per investigation ID. The ID must remain stable for the same
investigation; using another ID to bypass an unknown job is not authorized.
Existing local attempts remain separate immutable records and must be checked
before dispatching related cloud work. No archive upload or automatic migration
of those attempts is provided.

The existing five-minute Cloudflare cron submits a queued request once, then reads
its provider status on subsequent visits. D1 records submission intent before the
POST. A lost acknowledgement is **completion_unknown**, retains its reservation,
and never causes another inference request. Polls and result collection are GETs;
these can recover after a temporary network outage. A 25-second HTTP control-call
deadline is distinct from model reasoning: inference runs at the provider after
submission, with no five-minute inference deadline. Anthropic's batch expiration
(currently 24 hours) still applies. There is no invented live reasoning progress.

Cancellation is requested once and remains pending until a provider result confirms
its outcome. A completed candidate may win a race with cancellation. A lost cancel
acknowledgement does not authorize sending it repeatedly. For a lost submission
acknowledgement, **Recover an existing provider result** reads the original batch
ID and requires its finished result to match the exact saved job ID. An unrelated
or still-processing batch cannot clear the reservation. Recovery never submits.

Only `claude-opus-5-5` is accepted. Tools and provider fallback are absent. The API
requires an output-token maximum; each request must fit the deployment ceiling.
The final JSON candidate is bounded separately from reasoning, strictly validated,
fingerprinted and retained with allowlisted usage/identity receipts. Thinking blocks
are not stored. `candidate_ready` always has `compilation: not_run`: checking the
source against the pinned Lean/Mathlib project remains a separate evidence gate.
Failed, cancelled, expired and rejected results remain immutable. A distinct
follow-up uses a new ID, same investigation, parent job and scientific justification.

## Deployment and privacy

Apply `migrations/0022_proof_jobs.sql` to the existing Glim ledger before activating
this feature. The normal reviewed deployment workflow includes this additive
migration. It does not modify historical local ledgers or existing research tables.

Production uses its existing `ANTHROPIC_API_KEY`. Set these runtime settings using
the existing authenticated Cloudflare tooling; keep values out of git:

- `PROOF_JOBS_ENABLED`: `true` enables new submissions; explicit `false` pauses
  submissions while collecting existing batches. Unset means not installed.
- `PROOF_API_MAX_TOKENS`: authorized per-request ceiling (1024–128000).
- `PROOF_ACCESS_TEAM_DOMAIN`, `PROOF_ACCESS_AUD`, `PROOF_ADMIN_EMAIL`: the reviewed
  private workspace's operator Access configuration, scoped only to proof routes.
  Generic deployments may use their existing `CF_ACCESS_*` and `ADMIN_EMAIL`.

The preview's fixed `PROOF_SERVICE` binding targets `glim-think-v1`. Only exact
`/workspace/proof-jobs` routes are forwarded after operator and same-origin checks.
The backend independently verifies the original JWT and operator. Preview chat
retains its isolated database, Workers AI models and lack of provider secrets.
No generic proxy, experiment dispatcher, public proof feed, or auth bypass is added.
Candidates and briefs are private and excluded from public Library exports.

Enabling configuration does not prove API entitlement, live inference, or Lean
correctness. Record deployment, signed-in UI, one separately authorized small API
validation job, provider collection, and Lean validation as distinct gates.

## Verification

`npx vitest run src/workspace/__tests__/proofJobs.test.ts src/workspace/__tests__/hostedPreview.test.ts`
exercises real SQLite lifecycle transitions with mocked provider calls, including
concurrent ticks, lost POSTs, read recovery, cancellations, malformed/oversized
results, exact model checks, and Access/service boundaries. These are offline tests.

Provider references (reviewed 2026-10-07):
[Message Batches](https://platform.claude.com/docs/en/build-with-claude/batch-processing),
[model identifiers](https://platform.claude.com/docs/en/models/overview).
