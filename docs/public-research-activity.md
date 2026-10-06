# Reviewed public research activity

`GET /research/activity?limit=20` serves a public projection from the separate
`public_research_activity` D1 table. It reads no private run, conversation,
progress, model-packet, or identity table. The default page is 20 activities;
the maximum is 50. Each item is the latest immutable reviewed record for one
activity, ordered by `observedAt` descending, then `id` descending. `truncated`
indicates additional activities. There is no automatic ingestion or generation.

`GET /research/activity/{id}` returns the same feed envelope containing one
historical public record. This makes a `supersedes` reference inspectable. GET
and OPTIONS permit credential-free CORS (`*`); other public methods return 405.
Clients should display text as text and render links from the explicit link
arrays. A malformed selected record fails the whole page closed with a generic
503 response; no malformed content or database diagnostic is returned.

Contracts live at:

- `schemas/public-research-activity.v1.schema.json`: strict record fields.
- `schemas/public-research-activity-feed.v1.schema.json`: consumer response.
- `glim-think/src/workspace/researchActivityContracts.ts`: authoritative runtime validator.

Records are limited to 16 KiB UTF-8. Strings, arrays, counts, links, identifiers
and timestamps are separately bounded. Import rejects unknown fields, local
paths, email/device identifiers, private/IP/tailnet URLs, userinfo, credential
query parameters and credential-shaped strings. Repository/release links are
restricted to the three public `alexwelcing/lupine`, `lupine-rhizo` and
`lupine-ledger` GitHub repositories. Other source links must be public HTTPS.
These checks prevent common accidental disclosure, but do not establish that a
webpage is public or that prose is scientifically true. The operator reviews
both before import. No URL is fetched by the importer.

## Evidence and time

`evidenceKind: archived_analysis` describes calculations on existing data; it
does not manufacture LLM draft, critique or decision receipts. `research_cycle`
is a separate kind for an explicitly reviewed cycle summary. Neither accepts
private packets or receipt/identity fields. `state` is one of `planned`,
`running`, `completed`, `failed`, or `blocked`. `verification` is a separate
claim: `pending`, `arithmetic_checked`, or `source_checked`. The checked states
require at least one public source or published hash reference. A hash may
identify a private artifact without making that artifact publicly reproducible;
say so in the record's limitations.

`observedAt` records when the stated research evidence/status was actually
observed; `reviewedAt` records the actual public-summary review. Both use UTC
with milliseconds. Review must not precede observation or lie in the future.
Imports and refreshes never replace either time. Responses have no generated
evidence timestamp. HTTP cache duration is 30 seconds; it is not evidence age.

## Authorized browser import

`POST /workspace/research-activity/import` accepts one complete reviewed record
with `Content-Type: application/json` and an Origin matching the worker origin.
The endpoint independently verifies the configured operator's Cloudflare
Access JWT with the configured audience/team. DEV_MODE, service/bearer tokens,
and legacy internal-token bypasses are not passed to that verification. A
missing Origin is denied, including for non-browser clients. The response is
private/no-store and contains only the record ID, activity ID, state and an
idempotent-duplicate flag.

IDs are immutable. An identical re-import succeeds without changing data.
An amendment uses a new ID, the same `activityId` and `evidenceKind`, and a
`supersedes` value naming the current record. Observation may stay unchanged;
review must advance. Completed and failed records can only be corrected into
the **same terminal state**, with a nonempty `correctionReason`. A failed
activity cannot be rewritten as completed. A genuinely distinct follow-up
requires a new brief and activity; never retry, rename, or relabel a stopped
invocation to evade its stop state. Running/blocked activities cannot rewind to planned. All
historical public records remain readable.

## Reviewed release import without browser credentials

An authorized release workflow can prepare inserts from an explicitly reviewed
public export. This is a separate operator publishing path using its existing
D1 authorization, not a new HTTP authentication bypass. It needs no private
database reads, exports, service tokens, or access to research packets.

From the repository root, validate without writing any output:

```sh
node glim-think/scripts/prepare-public-activity-import.mjs exports/research-activity/latest.json --check
```

Prepare files at previously unused output paths:

```sh
node glim-think/scripts/prepare-public-activity-import.mjs exports/research-activity/latest.json --sql /tmp/public-research-activity.sql --json /tmp/public-research-activity-statements.json
```

The CLI loads the actual runtime validator, requires a complete feed with
`truncated: false`, rejects duplicate/forked in-batch history and writes only
inserts into the separate public table. It makes no network calls. JSON output
preserves parameterized `sql`/`params` for D1 API clients. The SQL file uses
UTF-8 hex literals so reviewed text cannot inject SQL. Existing output files
are never overwritten.

Before publishing the worker, the authorized deployment applies only
`glim-think/migrations/0021_public_research_activity.sql`, then its prepared
public insert file to the chosen D1 binding. Database triggers independently
enforce immutable IDs, duplicate idempotency, current ancestry and same-state
terminal corrections, including for this offline path. A conflict aborts its
insert; the workflow must fail and review it rather than replacing history.
The preparation step alone is not a publication or proof of a remote import.

The worker and hosted-preview handlers both expose this reviewed projection.
An upstream Cloudflare Access application must allow `/research/activity*`
public reads while keeping `/workspace*` and `/agents/research-workspace/*`
protected. Worker routing cannot override an upstream Access policy.

Focused checks from `glim-think/`:

```sh
node node_modules/vitest/vitest.mjs run src/workspace/__tests__/researchActivity.test.ts src/workspace/__tests__/researchRuns.test.ts src/workspace/__tests__/hostedPreview.test.ts
node --test scripts/prepare-public-activity-import.test.mjs
```
