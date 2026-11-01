# Cloudflare coding execution for Rhizo

This runner executes an operator-authored coding task against an exact Git commit
in a dedicated Cloudflare Linux container. Rhizo's existing D1 agenda owns the
task. Each task has one immutable attempt; execution results and review acceptance
are different records. The runner does not admit new research or publish articles.

The separate `wrangler.coding.jsonc` deploys `lupine-coding-runner-v01`. It does not
redeploy `glim-think-v1` or `lupine-research-team-v02`. The runner uses a separate
private R2 bucket. Do not substitute Rhizo's public `ARTIFACTS` bucket.

## What a coding task can do

The guest has broad shell and filesystem access. An explicit `enableInternet`
flag permits package installation and network use. No operator token, Cloudflare
deployment credential, repository credential or model credential enters it.
The source arrives as a hash- and size-bound Git bundle streamed from private R2;
the guest verifies it before checking out the exact requested commit.

The initial image is the managed `cloudflare/debian-trixie` alias. This is not an
immutable image digest. Receipts record the selected alias and observed system
and tool versions. Online setup may install Git, Python and Bash; an offline task
must already have the required tools. These facts do not establish reproducible
package resolution or a universal network-isolation proof.

`mode: "code-execution"` is the implemented execution mode. The DSH prototype can
be evaluated as software by an authorized command, but this does not establish a
working DSH model route. There is no automatic provider invocation, subscription
credential import, API-credit fallback or Workers AI fallback.

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
there are no recurring check-ins or scheduled admissions.

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
