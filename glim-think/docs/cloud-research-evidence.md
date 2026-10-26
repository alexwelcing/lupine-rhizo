# Cloud research evidence

Status: private object storage and database projection implemented; deployment, migration and live acceptance pending.

## Objective

Make the private cloud corpus the durable source for Lupine research. A researcher
should be able to find a model or material, inspect a reported observation,
trace its source and revisions, compare compatible evidence, and see what would
change a simulation decision. Local machines hold bounded working caches.

Glim Think remains the control plane. Reuse its existing operator Access identity
and agenda. Use a separate private D1 corpus database and a distinct private R2
bucket for evidence bytes. The
existing ARTIFACTS binding is served through a public /artifacts route and must
not receive private evidence. A prefix is not an access-control boundary.

## Scientific and engineering position

[OpenKIM's processing pipeline](https://arxiv.org/abs/2005.09062) already provides
standard model implementations, property tests, verification checks, dependency
resolution and distributed execution.
[NIST's Interatomic Potentials Repository](https://www.ctcms.nist.gov/potentials/)
provides potentials, associated files, references and evaluation tools.

Lupine should integrate those identities and results rather than duplicate their
simulation machinery. The proposed contribution is broader source-bound evidence:
published comparisons, reference and protocol differences, unknowns, corrections,
and task-specific decisions accessible through ordinary web APIs. Open-web
coverage, software architecture and scientific novelty are separate claims.
Novelty and comparative usefulness remain unestablished until evaluated.

The engineering choices are conventional: immutable objects, idempotent writes,
normalized records, explicit state transitions, indexed queries, incremental
ingestion, structured logs, access control and recovery tests. Measure their
value through usable scientific retrieval and decisions.

## Responsibilities

| Layer | Responsibility |
| --- | --- |
| Private R2 | Original bounded source bytes and immutable artifacts addressed by SHA-256 |
| Private D1 corpus | Observations, source/model identity projections, provenance, qualifications, import manifests and receipts; explicit comparison contracts remain next |
| Worker API | Authenticated ingestion/readback, bounded queries and source acquisition |
| Existing queues / agenda | Ownership, bounded work items, checkpoints and terminal outcomes |
| Library | Explicitly reviewed public projections |
| Local machine / SSD | Bounded computation cache and optional verified backup |

Keep large files out of D1 rows. D1 supports FTS5 and JSON, but has per-database
limits; shard only when measured load requires it. R2 total capacity does not
remove per-object, request, Worker memory/CPU or cost limits. Simulations needing
GPU or long compute remain on the separately authorized resource fabric.

## First slice implemented here

PUT /workspace/evidence-objects/<lowercase-sha256>
GET /workspace/evidence-objects/<lowercase-sha256>
HEAD /workspace/evidence-objects/<lowercase-sha256>

All methods independently require verified operator Access and reject
cross-origin browser requests. Legacy internal tokens and DEV_MODE cannot grant
this route access. Requests are handled before generic text parsing.

The optional PRIVATE_EVIDENCE binding must name a distinct private bucket.
PRIVATE_EVIDENCE_ENABLED must equal "true". Absent configuration returns 503;
the public ARTIFACTS binding is never a fallback. No bucket or binding is
provisioned automatically by this patch.

Uploads are capped at 25 MiB using both declared and streamed lengths. Only one
upload may buffer in an isolate at a time; another receives 429 without an
automatic retry. GET/HEAD do not buffer whole objects. The server
hashes the original bytes, rejects a mismatched identifier and supplies the
checksum to R2. A conditional create prevents overwrites. Exact duplicate bytes
can be acknowledged without another write; a conflicting or corrupt existing
object remains an error. A concurrent create returns 409 without automatic retry.

Responses use private/no-store and attachment/octet-stream headers. Object
storage acknowledges transport only: "stored" and "unreviewed" do not mean
scientifically checked or migrated. The client must hash GET bytes and record
a readback receipt before promoting migration state. A lost acknowledgement
is explicitly unknown; inspect with GET/HEAD before deciding any next action.

There is no list, delete, arbitrary source-fetch or publication endpoint here.
The route does not dispatch simulations or model calls. Content addresses enable
deduplication; source origin and scientific identity projections belong in the D1
slice, not in filenames or user-supplied object metadata.

Run focused checks from glim-think:

    node --test scripts/private-evidence-objects.test.mjs

These checks use the actual Access verifier with locally signed synthetic JWTs
and in-memory R2 doubles. They do not prove deployed Access/R2 behavior.

## Private database projection implemented

This revision adds a separately bound `PRIVATE_CORPUS` D1 database. The shared
`LEDGER` remains the runtime/agenda database: its public routes, agent tools and
storage instrumentation must not gain implicit access to private corpus rows.
The dedicated schema is in `corpus-migrations/0001_private_corpus.sql`, outside
the runtime ledger migration directory. No database or binding is provisioned
by this change. Set `PRIVATE_CORPUS_ENABLED=true` only after its targeted
migration, private binding review and deployed acceptance.

Both evidence-object and corpus routes dispatch **before** the automatic
request/binding telemetry wrapper. The ordinary handler receives an environment
copy before its telemetry wrappers mutate bindings. Private route errors are
sanitized and never logged with source content, SQL parameters or provider
exceptions. Deployed tracing/access behavior still requires verification.

| Method and path | Meaning |
| --- | --- |
| POST /workspace/corpus/objects/:sha256 | Read and hash private R2 bytes; save an immutable verification receipt |
| GET /workspace/corpus/objects/:sha256 | Collect the existing receipt, with its original verification time |
| PUT /workspace/corpus/imports/:id | Atomically commit one bounded import |
| GET /workspace/corpus/imports/:id | Read-only recovery after interruption or unknown acknowledgement |
| GET /workspace/corpus/observations | Filtered, paginated observation projections |
| GET /workspace/corpus/observation?record_id=...&record_sha256=... | Exact retained record and projection |
| GET /workspace/corpus/qualifications?record_id=...&record_sha256=... | Paginated original quarantine, annotation and correction events |

All endpoints require operator Access, the separate private bucket and the
separate private corpus database. No DEV_MODE or internal-token bypass applies.
The database and bucket identity checks reject obvious aliases; deployment
review must verify the actual resources, not merely different binding names.

### Import contract

The body is UTF-8 JSON with exactly `schema: "lupine-private-corpus-v1"`,
`observations` and `qualifications`. A batch contains at most 20 observations
and 20 qualification events, at least one entry overall, at most 16 distinct
source objects and at most 1 MiB of request bytes. Each original record JSON
string is capped at 64 KiB. These are ingestion bounds, not scientific quotas.

Each observation includes:

- `recordId`, `recordSha256` and `recordJson`: the original ID and the exact
  supplied JSON representation. SHA-256 must match the UTF-8 bytes of that
  string. Preserve the original object as R2 evidence even when the adapter
  must serialize a row out of a larger source.
- `evidenceSha256`, `sourceId`, `studyId`, `locator`: a verified R2 object,
  original source/study identities and table/figure/JSON-pointer anchor.
- `material`, `observable`, `unit`, `modelId`, `referenceKind`: supplied
  search projections; explicitly use null for unknown fields.
- `observedAt`, `reviewedAt`: original ISO timestamps with an explicit timezone, or null. Microsecond/nanosecond precision and offset notation are retained exactly. Import
  time is separate and never substitutes for an observation or review.
- `originalRowSha256`: retained legacy row fingerprint or null. Its original
  serialization algorithm is not inferred or silently replaced.
- `missingFields`: explicit missingness labels, retained without fabrication.

**Verification scope:** the server verifies object bytes and supplied record
bytes. It does not parse a paper to confirm the locator or extraction, verify
the legacy hash algorithm, or prove that projected metadata matches the source.
Responses label those provenance links `operator_supplied` and scientific
validation `not_assessed`. Original claim/evidence labels remain in recordJson.
A migration adapter must independently check source-to-row linkage and preserve
its receipts before claiming the corpus migration verified.

Object receipts retain their original time. Imports check current R2 metadata,
size and ETag against the receipt before committing. R2 and D1 do not share a
transaction: this assumes out-of-band writes to the content-addressed bucket
are prohibited. The implementation cannot prevent an external operator from
mutating R2 after the check.

### Immutable, idempotent publication

An import ID is bound to the SHA-256 of the exact request bytes. Exact replay
returns the existing receipt without writing; different bytes under that ID
conflict. After an unknown outcome, use GET before deciding any new action.
The handler never automatically retries an operation or launches a model or
simulation job.

One D1 batch transaction writes the import marker, observations, memberships
and events. A failed statement rolls the whole transaction back. SQL triggers
reject updates and deletions. The same record ID and byte hash can belong to
several imports without duplicating the observation. A divergent projection
for that same identity is rejected. The receipt's entry counts describe the
submitted batch; they are not counts of new distinct observations or studies.

Qualification events target exact record IDs and hashes. A correction event
retains the original and records the reason; it does not silently replace
values, remove quarantine or certify a replacement. A corrected representation
requires a separately identified revision with preserved lineage. Structured
field corrections and adjudicated replacement views remain future work.

### Bounded retrieval

The list supports exact `study_id`, `material`, `observable`, `model_id` and
`import_id` filters. Query values are bound SQL parameters. Pages default to 20
and cap at 50; use both returned `after_id` and `after_sha256` for the next
page. Qualification history uses `after_event_id`. List responses omit full
recordJson; fetch an individual revision for it.

Quarantined revisions are excluded by default. `include_quarantined=true`
returns them with explicit flags; original qualification events remain
accessible. General pagination is over a live append-only view, not a frozen
corpus-wide snapshot. `import_id` fixes membership; qualification visibility
can still change when a later event quarantines a record.

Indexes cover material/observable, study, observable and model filters.
No cross-study discrepancy is calculated by this endpoint. A declared
compatibility contract and scientific review still govern comparison.

Run the actual route, Access verifier and SQL schema against in-memory SQLite:

    node --test scripts/private-corpus.test.mjs

Tests cover real SQL constraints/transactions, rollback, duplicate/conflicting
imports, read-only recovery after lost acknowledgement, source integrity,
quarantine targeting, keyset paging, unknown metadata and private telemetry
dispatch. R2 and the D1 binding transport are doubles; these checks do not
establish live Cloudflare acceptance or a completed migration.

## Remaining slices and acceptance

1. **Private deployment boundary.** Verify that the selected bucket has no public
   custom domain or r2.dev access and is not bound to any public artifact reader.
   Configure an isolated acceptance environment within existing authority.
   Prove unauthenticated denial, authenticated PUT/GET hash agreement and no
   corresponding public artifact access. Do not infer privacy from an unknown
   object key. Production deployment requires its specific authorization.
2. **D1 corpus migration acceptance.** Exercise the implemented projection with real records; preserve existing row IDs and source IDs. Record the
   immutable source-object hash plus JSON pointer, original row hash, schema,
   original observation/review time, unit, observable, material/state, model,
   reference and missing fields. Preserve quarantine events as separate immutable
   rows targeting exact row hashes; never silently repair or delete originals.
   Keep imported observations distinct from executed or independently checked
   results. Include original OpenKIM/NIST identifiers and DOI aliases.
3. **Transactional manifest acceptance.** Exercise the implemented per-import transaction and extend it to a corpus-wide pinned view if needed. Upload/check objects first; publish
   D1 rows and a committed manifest only after object readback is verified.
   An interrupted import leaves the prior committed query view available.
   Use an ingestion ID plus payload hash: exact replay is a no-op, divergent
   reuse is a conflict. Recovery is read-only for unknown outcomes until their
   actual state is established; it must never replay stopped model/source jobs.
4. **Migration.** Walk the existing base-plus-delta manifest and its provenance
   closure, including sources referenced inside records. Do not assume top-level
   file membership alone is the whole corpus. Verify every source hash, preserve
   exact bytes, and transfer bounded batches without a second local snapshot.
   Reconcile counts, qualifications, row hashes and sample queries before switching
   the primary read path. Verify a restore/export before any approved local cleanup.
5. **Direct acquisition.** New permitted source acquisition writes bounded bytes
   to private cloud storage and records provenance without permanent local PDFs.
   Retain source-specific failures, redistribution scope and stop conditions.
   Public-source fetching needs URL/redirect validation, private-network denial,
   response limits and a persisted ownership record; arbitrary server-side URL
   fetching must not be bolted onto this byte-upload route.
6. **Useful retrieval and comparison.** Serve paginated/filterable API responses.
   Query several distinct studies by material, observable and reference. Return
   exact source/table/figure anchors, missingness and qualifications. Require a
   declared compatibility contract before calculating a cross-study comparison.
   Measure end-to-end retrieval quality, latency, transferred bytes and cost.
   Demonstrate a concrete simulation choice and its discriminating next evidence.
7. **Sustained operation.** Reuse durable agenda work across visits. Have retrieval,
   acquisition and scoped publication proceed without waiting on a theorem or
   whole-corpus audit. Continue error-geometry/formalization work when it advances
   the scientific decision. Do not turn each visit into a new architecture document.

Completion requires the verified source-to-observation-to-comparison-to-decision
path and a migrated, recoverable corpus. The implemented storage and projection routes alone
do not satisfy that objective.

## Resource and publication boundaries

Keep credentials, controller state and unrelated personal data out of research
imports. Cloud storage is not public publication. Preserve stopped job history
without granting those jobs replay authority. Use the existing reviewed public
projection for Library outputs.

Bound object and batch sizes; keep rate and spending ceilings explicit. A direct
cloud operation need not allocate a local archive. Local builds, downloads and
cache growth still use the existing volume-specific storage admission rules.
No paid-plan change, model substitution, automatic cleanup or deployment follows
from this implementation.
