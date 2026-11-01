# Cloudflare coding execution for Rhizo

This runner executes an operator-authored coding task against an exact Git commit
in a dedicated Cloudflare Linux container. Rhizo's existing D1 agenda owns the
task. Each task has one immutable attempt; execution results and review acceptance
are different records. The runner does not admit new research or publish articles.

The separate `wrangler.coding.jsonc` deploys `lupine-coding-runner-v01`. It does not
redeploy `glim-think-v1`. The model integration separately adds a binding-only broker to `lupine-research-team-v02`, preserving its public router and existing runtime bundles. The runner uses a separate
private R2 bucket. Do not substitute Rhizo's public `ARTIFACTS` bucket.

## What a coding task can do

The guest has broad shell and filesystem access. An explicit `enableInternet`
flag permits package installation and network use. No operator token, Cloudflare
deployment credential, repository credential or model credential enters it.
The source arrives as a hash- and size-bound Git bundle streamed from private R2;
the guest verifies it before checking out the exact requested commit.

Two source formats have distinct manifest identities. `source.kind: "git-bundle"`
retains the ordinary clone path; the runner never infers a shallow boundary for
it. A deliberately depth-one export must instead use
`source.kind: "git-shallow-bundle-v1"` and supply
`source.boundaryCommit` equal to `repository.commit`, alongside the same pinned
`artifactKey`, `sha256`, and `bytes` fields. The new path initializes an empty
repository and writes that exact boundary before local unbundling. It verifies
the checked-out commit, the single visible commit, the shallow marker, and
`git fsck --strict --no-reflogs` before admitting the coding command. The commit
object and current tree are preserved; unavailable ancestors are not recovered
or claimed as complete history. No remote fetch is performed by this import.
Changing the source format changes the full manifest hash and requires a new
authorized task; failed historical attempts remain unchanged.

The operator helper exports the pinned commit and its complete current tree
without cloning another working copy or including untracked files:

```sh
python3 scripts/coding-source-bundle.py /path/to/repository <40-hex-commit> /private/output/source.bundle
```

Its JSON output supplies the exact `git-shallow-bundle-v1` source fields. Keep the
bundle private, upload it under its content-addressed key, and bind those fields
to the agenda manifest before submission. Historical parents are deliberately
excluded. A failed export leaves a `.partial` file; it is never an admissible
completed bundle. The helper refuses existing output paths.

The initial image is the managed `cloudflare/debian-trixie` alias. This is not an
immutable image digest. Receipts record the selected alias and observed system
and tool versions. Online setup may install Git, Python and Bash; an offline task
must already have the required tools. These facts do not establish reproducible
package resolution or a universal network-isolation proof.

Version 1 keeps `mode: "code-execution"` unchanged. Version 2 adds `mode: "dsh-subscription"` with a fixed MiniMax included-plan model and explicit request/output limits. A private service binding owns provider credentials; the guest receives only a short-lived task capability. Actual hosted model access requires separate live evidence. There is no paid API or Workers AI fallback. See [the model recipe](../scripts/coding-dsh-model/README.md) and [broker installation](../integrations/research-coding-broker/README.md).

The separately versioned [corrected model recipe](../scripts/coding-dsh-model-v2/README.md)
excludes five unavailable inherited placeholder tools from each agent's visible
surface. It preserves all Runtime-owned tools and the available native read/bash
tools within the existing 16-tool limit. The original recipe and first failed
attempt remain frozen. Source-derived regressions cover the initial request and
its tool-result continuation; actual complete Harness execution remains a
separate live qualification. Missing reports receive explicit absence records
and cannot become successful assessments.

The [schema-compatible recipe](../scripts/coding-dsh-model-v3/README.md) additionally
projects the pinned Zod output at Runtime tool registration. It removes only
the identified nonenumerable `~standard` metadata after checking its descriptor
and origin; all JSON-schema content and execute-side argument validation remain
unchanged. Tests use actual pinned Zod and Harness utilities for all 20 Runtime
tool schemas. The first attempt's exact failing predicate was not captured;
the tool-count mismatch was reproduced with source-derived plain schemas. The
second attempt directly captured the hidden-metadata incompatibility. These
are separate findings, and both earlier recipes remain unchanged.

The [completion-budget recipe](../scripts/coding-dsh-model-v4/README.md) preserves
those three versions and adds a fixed 6/10 master/worker allocation within the
same sixteen-call ceiling. Only three master calls are available before a genuine
ready worker report. Exploration closes after global call eight; the worker then
uses a fixed assessment writer and the existing report tool. Tool results retain
immutable budget feedback without changing earlier conversation history or tool
schemas. A role's known pre-dispatch refusal does not spend the other role's
reserve; an unknown provider outcome still stops the entire transport.

The writer saves structured findings first and derives Markdown from them. It
checks the exact revision, eight domain records, three proposed improvements,
source-path existence, size limits and immutable readback of both artifacts.
Ready admission and final success recheck those artifacts. These checks do not
prove that every cited file was read or that a finding is true; independent
semantic review remains required. Noncompliance produces a failed/incomplete
record with available ticket, budget and artifact state. Reserved calls improve
completion control but cannot guarantee useful model output. See the
[dated live evidence](cloudflare-coding-validation-20261101.md) for actual outcomes.

## Install and verify

The small `coding-runner/` toolchain pins Wrangler and Container types separately
from the older Rhizo application dependencies:

```sh
cd glim-think/coding-runner
npm ci
npm run check
npm test
npm run build
```

Apply only `migrations/0026_coding_attempt_ledger.sql` to the existing ledger after
review. Do not run unrelated pending migrations. The existing
`intelligence_tasks` schema is a prerequisite. Source inspection, local checks,
deployment and live execution each need their own receipts.

## Submit and inspect

The dedicated `RUNNER_OPERATOR_TOKEN` authorizes the machine API. Keep its local
copy outside the repository in a mode-0600 file. Do not put it in a URL, manifest,
guest environment or shell argument. Requests never follow redirects.

Before submission, create a coding-domain agenda task whose
`payload.codingInputSha256` matches the validated, canonical task manifest. This
binds the authorization to its exact source, command, deadline and artifact list.
Upload the bundle to `sources/<sha256>.bundle` in the private bucket.
Until the main Rhizo release includes the generic-agenda coding exclusion,
reserve the task as `status='claimed'` with
`claimed_by='cloudflare-coding-runner'`. This separate deployment does not change
the existing main Worker's scheduler. See `src/coding/LEDGER.md`.

```sh
export LUPINE_CODING_ORIGIN=https://lupine-coding-runner-v01.aw-ab5.workers.dev
export LUPINE_CODING_TOKEN_FILE=/private/path/runner-operator-token
node scripts/coding-runner-client.mjs submit task.json submission-receipt.json
node scripts/coding-runner-client.mjs status attempt-id status-receipt.json
```

The client writes a new private receipt and prints only its path and HTTP status.
It refuses to replace an existing receipt. A submission timeout is an unknown
outcome: inspect the same attempt; do not create a fresh attempt to retry it.
Status reads never wake a container. Evidence reads require authentication and
are limited to the artifacts registered for that attempt.
The authenticated `POST /coding/tasks/<attempt-id>/reconcile` endpoint retries
only persistence of an already-frozen terminal record. It cannot execute code
or start the guest. Use it when storage acknowledgement was lost; it is not an
execution retry.

## Execution, recovery and acceptance

The runner saves its dispatch intent before starting a guest or issuing a
command. Duplicate identical submissions return existing metadata; changed
identities conflict. Reconstructed or uncertain execution never automatically
replays. The task deadline and cleanup alarm belong to this finite attempt;
there are no chat check-ins. The optional durable scheduler admits only exact authorized queue items within its configured limits. It creates no idle alarm and does not invent new tasks.

Bounded stdout and stderr are drained together. Requested artifact paths are
read with containment checks, hashed, written outside the guest, and read back.
Exit status, truncation/failure, archive verification and container cleanup are
separate facts. Unknown evidence or cleanup cannot produce a successful result.
The guest is destroyed after capture, including its descendant processes.

A terminal result blocks the agenda task pending separate review. The acceptance
API in `src/coding/ledger.ts` accepts only the exact successful terminal receipt;
it cannot promote a failed or unknown execution. No public HTTP acceptance route
is exposed. Keep negative and unknown receipts immutable.

## Private document review

This runner is not an arbitrary HTML proxy. In particular, uploading a private
document to the existing public `/artifacts/` route would expose it. A future
document review feature must use exact, inert, manifest-pinned files beneath an
authenticated workspace route or separately protected storage. Executable
previews need a separate origin so they cannot exercise workspace administrator
cookies. Browser URL-policy restrictions remain independent of guest permissions.

Observed release evidence: [Cloudflare source import and DeepSeek orchestration validation](cloudflare-coding-validation-20261101.md).

## Automatic queue dispatch

The operator-authenticated scheduler is one Durable Object. Configure it with an exact versioned policy and compare-and-swap `expectedPolicySha256`; enqueue `{task, authorizationId, expiresAtMs}`. Enqueue creates/preclaims the coding agenda row atomically, avoiding the old generic scheduler. A task authorization expires within seven days. The policy limits concurrency, daily/lifetime attempt counts, and full wall-time reservations. Reservations are not measured billing.

```sh
node scripts/coding-runner-client.mjs schedule-configure policy-request.json configure-receipt.json
node scripts/coding-runner-client.mjs schedule-enqueue authorization.json enqueue-receipt.json
node scripts/coding-runner-client.mjs schedule-status - scheduler-observation.json
```

Cloudflare alarms own dispatch and bounded terminal observation. A lost dispatch acknowledgement is never replayed. Unknown executions retain capacity. `schedule-stop` removes only an undispatched queue item; `schedule-reconcile` observes the exact existing attempt and cannot restart it. Disabling the policy stops future admission while active attempts retain cleanup supervision. Empty queues have no alarm.

An operator may attach a separately reviewed `release-confirmed-no-model-dispatch`
disposition to `schedule-reconcile`. This narrow exception requires matching
Runner and D1 terminal hashes, confirmed cleanup, and a closed task broker with
zero consumed or completed operations and no pending unknown. It applies only to
the versioned subscription command-evidence failure covered by the implementation.
The request binds an authorization ID, terminal hash, and independent review hash.
It releases the scheduler's concurrency hold only: the original unknown record,
attempt count, wall-time reservation, and absent acceptance remain unchanged.
The disposition is immutable and separately identified in scheduler status. It
does not establish zero arbitrary guest network traffic, and cannot authorize a
replay. A corrected command requires a distinct source, manifest and authorized
task within the remaining policy budget. Guest model capabilities cannot reach
this administrative action.

For subscription tasks, fresh credits-OFF evidence and authenticated quota remain required. An expired proof yields a wait, not a paid fallback. This route still depends on a real browser observation for credit-control freshness; enabling scheduling does not establish fully unattended subscription eligibility. Native/Claude scientific work and public Library publication are separate authorities.


## Diagnosing a model result that was withheld

The v5 guest recipe preserves the first broker failure and up to four later local
refusals separately. These bounded diagnostics do not establish a provider
terminal or authorize another dispatch. Incomplete delivery may include output
already yielded to Harness; do not equate it with no delivery.

A captured HTTP 200 response with a provider error stop can still leave the
account and coding attempt unknown. Inspect the exact archived outcome and
operation identity. Fresh sign-in or quota proof cannot clear ownership, and the
zero-model-dispatch disposition cannot release a task that already used models.
A new operator recovery action must be reviewed against the original receipt,
account revision, closed broker and confirmed guest cleanup. Preserve original
outcomes and reservations. See the dated validation for the current unresolved
v4 attempt and the locally reviewed, unexecuted v5 diagnostic recipe.
