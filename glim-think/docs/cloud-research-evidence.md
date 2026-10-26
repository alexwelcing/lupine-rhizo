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
  original source/study identities (explicit null when unknown) and table/figure/JSON-pointer anchor.
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

## Read-only Rust migration planner

The `corpus-migrate` binary in `atlas-distill` prepares bounded request plans from
a pinned v2 base-plus-deltas manifest. It uses the existing crate and dependencies;
it has no network client, credential handling, upload, retry, simulation dispatch
or file-writing path. Run the installed binary after any required build has passed
its storage admission gate:

    corpus-migrate --root /trusted/research/root \
      --manifest /trusted/research/root/manifest.json \
      --manifest-sha256 <original-manifest-sha256>

The default report contains counts and verification scope. Add `--batch-index 0`
to emit one **private** request plan. Its `payload` string is the exact UTF-8
request body to send through the authorized private API; do not reserialize its
embedded rows. Hash that string and check `payloadSha256`. stdout may contain
private evidence, so do not publish it or redirect it into a growing local archive
without storage admission.

The planner reads at most 100 MiB total, at most 25 MiB per component and at most
10,000 rows. Relative paths resolve against the explicit root. It rejects paths
outside that root, `..`, symlinks, nonregular files, duplicate JSON keys, changed
hashes or lengths, duplicate IDs and preannotated originals. Row strings preserve
their exact original JSON tokens and interior whitespace, including numeric
spelling, Unicode escapes and timestamp precision. The container hash plus JSON
pointer anchors those bytes. Search projections use string fields only; null
remains unknown, including absent source and study identities. Missing identities
are not filled with invented identifiers, and do not count as distinct known studies.

Each plan satisfies the endpoint's 20-row, 20-event, 16-object and 1 MiB limits.
A target row and its existing quarantine are emitted in the same atomic request,
so a partially completed migration cannot briefly expose that row without its
known exclusion. Original qualification packets and their evidence are also
hash-checked. The import ID embeds the full original manifest hash and the exact
payload hash; qualification anchors retain the packet hash, pointer and original
target digest. Preserve all `allRequiredArchiveObjects`, including the original
manifest and qualification packets, and verify private readback before publishing
any planned import. This prerequisite is a migration-executor obligation; the API
only enforces the object receipts directly referenced by its observation rows.

Legacy qualification digests are **not** replaced by new row-byte hashes. The
planner checks compact sorted JSON with original numeric lexemes; a second,
value-preserving candidate pads exponent spelling (for example `e-9` to `e-09`).
A candidate is accepted only when its full digest matches the retained original
qualification hash. The method is included in the mapping receipt. This is not a
general Python JSON serializer: unsupported legacy representations stop planning
and require an explicit checked mapping. No numerical value is changed.
Observation time is never relabeled review time.

Plans include a GET recovery path. After an unknown upload/import outcome, collect
its actual receipt read-only and match the exact payload hash; emitting the same
deterministic plan is not authorization to replay a stopped operation.

**Import-plan scope:** the planner checks row containers, qualification packets
and their direct structured evidence. The separate reference audit below traverses
additional declared links; it does not change import eligibility or promote a
scientific claim. Every report labels provenance closure `not_verified` and
scientific validation `not_assessed`; projected rows retain a matching missingness
flag. Source-to-row attribution checks, a cloud executor, fixed corpus publication
and export/restore remain required before switching the primary path.

### Read-only declared-reference audit

Add `--provenance` to the same pinned-manifest command to audit supported local
file references instead of preparing imports. Add `--provenance-details` only
when private per-reference paths, hashes and JSON pointers are needed. The default
report contains counts and limits, without file paths. Neither mode makes network
requests, uploads, writes files, retries downloads or executes source content.
Detailed output is private and requires storage admission before redirection.

The audit follows `path/sha256`, `local_source/source_sha256`,
`local_path/sha256`, `file/sha256`, `pdf_path/pdf_sha256`,
`text_path/text_sha256`, `tool_text/tool_text_sha256` and legacy
`files: {filename: digest}` maps. Nested JSON references include supporting
artifacts and historical manifests. Original declaring-object hashes and escaped
JSON pointers identify each edge; declarations are retained even when unresolved.
Relative paths always use the explicit trusted root. A basename is never guessed
from another directory or searched for automatically.

The reader rejects paths outside the root, symlinks and non-regular files. It
checks the remaining byte budget before opening a file and bounds the read if the
file grows. The audit independently verifies returned hashes; conflicting size
declarations remain separate outcomes even when the same bytes are shared.
Repeated identical path/hash attempts, including failures, are collected once
without another read. JSON content is expanded once per verified hash, with
duplicate keys rejected. Only files named `.json` are parsed; PDFs, HTML, text,
JSONL and other opaque objects are hashed without interpreting their contents.

Limits are 25 MiB per file, 100 MiB of local reads including the root manifest,
512 distinct path/hash attempts, 20,000 reference declarations and 1,000,000 JSON
nodes. Bounded reads use at most one additional byte to detect a file that grows
past the remaining budget; rejected bytes still consume the read allowance. Budget exhaustion, malformed JSON, missing pins, unreadable files and
unrecognized reference fields are explicit outcomes. `truncated` indicates a
traversal limit. Outcome counts can exceed declarations when a file is hash
verified but its JSON traversal is rejected. `returnedBytesIncludingManifest`
counts bytes returned to the audit; the filesystem reader also counts bytes read
before a failed verification.

URLs, DOIs and tool receipts remain unresolvable anchors in this local audit.
Unfamiliar path fields are reported without following them. Supported-field
coverage is deliberately explicit: no detected gaps does **not** establish
complete provenance. Hash agreement establishes retained-byte integrity, not
source attribution, independence, extraction correctness or physical validity.
The audit cannot authorize upload, substitute for a compatible comparison
contract, or clear a quarantine.

Run focused synthetic tests:

    cargo test --locked --manifest-path atlas-distill/Cargo.toml --bin corpus-migrate

The existing Verify workflow compiles and tests this binary in its Rust workspace
job. Public fixtures are synthetic; private corpus files never enter CI.

## Per-source knowledge and semantic analysis

The private evidence layer is the source of record. Semantic extraction is a
versioned derived view over exact source revisions, not a replacement for the
original bytes or an automatic scientific review.

Implemented read surface:

    GET /workspace/corpus/observations?source_id=<exact-identity>
    GET /workspace/corpus/source-context?source_id=<exact-identity>&limit=10

The source-context route requires operator Access, uses a dedicated source index,
and returns at most 20 projections and 256 KiB. It includes quarantined rows with
their status so an analysis cannot silently omit contradictory or excluded data.
Each node retains its exact row revision, evidence-container hash and locator,
original times, units, missingness, immutable-original directive, and links to the
original row and paginated qualification history. An evidence container is not
implicitly the primary paper. Missing source/study identities are never invented.

The v2 bundle has a SHA-256 fingerprint of its exact serialized context, including
each returned record's qualification revision. It is not a persisted corpus
snapshot. Import membership can be pinned; qualification state remains live, and
full history must be fetched separately. The response explicitly reports analysis
not run, zero model calls, no inferred relations, unassessed comparability/calibration
and unknown token count. A byte ceiling is not a token ceiling. This is an analysis
input, not a complete source summary.

Apply `corpus-migrations/0002_review_revisions.sql` after 0001 in the dedicated
private database before using these queries. It backfills a per-record-version
review counter from immutable events and advances it in the same transaction as
each new annotation, correction or quarantine. A duplicate event or rolled-back
import does not advance the counter. A counter is invalidation metadata, not a
quality score or a cryptographic digest of the review text.

This closes a demonstrated gap in v1: an annotation/correction could leave the
quarantine bit unchanged and therefore leave the context fingerprint unchanged.
The v2 fingerprint changes for every new qualification on a returned record,
including events inserted before a previously read pagination cursor.

Conditional read checks are available:

    GET /workspace/corpus/source-context?source_id=<id>&expected_context_sha256=<sha>
    GET /workspace/corpus/qualifications?record_id=<id>&record_sha256=<sha>&expected_revision=<n>

A stale expectation returns HTTP 409 `context_changed`, without writes or an
automatic retry. Source-context links and qualification-page cursors carry the
expected review revision. The history page and its current revision are selected
in one SQL read snapshot, including empty pages. The indexed page query avoids
scanning the full review history at request time.

These are read-time checks, **not commit leases or general MVCC**. They cover only
the returned source page and each explicitly pinned record history. They do not
detect changes to omitted records, prove complete source membership, or prevent a
new review after the read returns. A future semantic-assertion writer must compare
its full dependency revisions atomically with its commit. Unknown import outcomes
remain recoverable through existing read-only receipts; a newer revision is not
authorization to repeat a stopped model or source job.

The next semantic layer should preserve these contracts:

- **Anchored extraction:** keep source identity, source SHA-256, extractor and
  rule versions, original passage/table coordinates, and derived claims distinct.
  Use typed byte, page/region and temporal anchors only when that modality has a
  verified normalizer. Record unknowns instead of fabricating page coordinates.
- **Versioned interpretation:** append proposed, reviewed, rejected and superseded
  semantic assertions with their exact input revisions. A new extraction cannot
  overwrite observations or clear a quarantine. Changes invalidate dependent
  interpretations; they do not require repeating unchanged acquisition.
- **Typed relations:** distinguish reports, cites, supports, contradicts and
  derived-from links from subject similarity. A shared source or citation does
  not establish independent evidence. Protocol compatibility requires an explicit
  material/state/observable/reference contract.
- **Deterministic orchestration:** keep mutation validation separate from external
  inference. Responses carry request identity and expected input revision; stale
  responses cannot commit against a newer source. Time and lease expiry are
  explicit transition inputs. Reuse Glim ownership and terminal outcomes.
- **Bounded context:** retain required anchors, qualifications and exclusions in
  any selected subgraph. Report omitted nodes and actual tokenizer/version when
  enforcing token limits. A greedy k-hop selection is a heuristic unless an exact
  optimization method and its assumptions are established.

The supplied knowledge-tree design is a useful direction, with several guarantees
that must be verified rather than inherited:

1. Evidence identity remains SHA-256. FNV is a
   [non-cryptographic hash](https://datatracker.ietf.org/doc/html/rfc9923);
   any FNV acceleration would be a disposable hint with collision-safe validation.
2. A containment tree requires root reachability and exactly one parent for each
   non-root node. An acyclic graph with at most one parent can be a disconnected
   forest. Semantic citation/contradiction edges have separate cycle rules.
3. A cached root comparison is constant time; building hashes and parsing changed
   content are additional work. Logarithmic behavior needs stated tree-shape and
   incremental-update assumptions. No millisecond performance claim is made here.
4. Reverse-operation journals alone do not establish concurrency isolation.
   Commit authority needs an atomic expected-revision check, complete rollback
   coverage and read/write conflict rules. Existing bounded D1 import transactions
   do not yet implement a general knowledge-graph MVCC engine.
5. A probability threshold is not evidence of calibration or truth. Validate
   classification and abstention on reviewed examples before enabling promotion.
   This change does not activate external inference, automatic locks or providers.
   For code, ast-grep metavariables match
   [syntax nodes](https://ast-grep.github.io/advanced/pattern-parse.html), not
   universally single lexical tokens; multimodal matchers need their own contract.

The existing literature similarity search and reviewed Library passage bindings
are integration points. Their runtime/public storage and embedding calls must not
be repurposed as the private corpus authorization boundary. No kgtree package,
global hook, local snapshot store or daemon is installed by this work.

## Isolated private acceptance entrypoint

The existing `deploy-glim-think.yml` applies runtime-ledger migrations, deploys
the research Worker and publishes reviewed public activity. It is not a private
evidence preflight. Do not dispatch it merely to test these routes.

`src/privateEvidenceAcceptance.ts` reuses the same object, corpus and operator
Access handlers through a minimal entrypoint. It has only a fetch handler and
returns 404 for unrelated public, research, agent and execution routes. An exact
binding allow-list rejects accidental runtime ledger, public artifact, provider,
queue and bypass configuration before touching storage. Errors stay private and
sanitized. The narrower `PrivateEvidenceEnv` type also makes the required
capabilities explicit without importing the main research server.

`wrangler.private-evidence-acceptance.json` is a standalone **disabled**
configuration. It declares no resource bindings, routes, crons, queues, Durable
Objects, provider credentials, schema migrations or workspace UI build. Both
storage flags are false; workers.dev and preview URLs are false; automatic
observability is disabled. PR CI typechecks and dry-run builds this entrypoint:

    npx wrangler deploy --config wrangler.private-evidence-acceptance.json --dry-run

That command is verification, not an acceptance deployment. Local execution still
requires the build storage guard. The ordinary research deployment configuration
and workflow are unchanged.

Before an authorized activation, review a complete private deployment
configuration and the **live** account state: exact account/Worker, distinct
private bucket and D1 identities, current included capacity, existing route and
preview settings, and coverage by the existing operator Access identity. A new
Worker does not inherit another Worker's Access configuration or policy. Do not
copy provider secrets or broaden the authorized operator population. This
entrypoint has no login UI, credential copying, provisioning or deployment action.

The allow-list cannot discover that an allowed private binding points to a public
bucket or runtime database. Inspect bucket r2.dev/custom-domain access and all
readers, database identity, service bindings, and existing dashboard routes before
activation. Apply both private corpus migrations explicitly to the reviewed
private database. Do not apply the runtime/public migrations as part of this path.

Acceptance remains bounded: first synthetic denial/readback and unknown-outcome
checks; then the reviewed retained-evidence pilot, exact source and row hashes,
qualification-aware queries, and a live export/restore into an isolated private
target. A passing in-memory rehearsal or dry-run build is not a deployed privacy,
capacity, backup or physical-validation receipt. Stop after an unknown write
outcome and collect it read-only. Disabling this entrypoint must preserve its
evidence objects and immutable database history.

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
