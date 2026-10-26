# Cloud research evidence

Status: first implementation slice; deployment, migration and live acceptance pending.

## Objective

Make the private cloud corpus the durable source for Lupine research. A researcher
should be able to find a model or material, inspect a reported observation,
trace its source and revisions, compare compatible evidence, and see what would
change a simulation decision. Local machines hold bounded working caches.

Glim Think remains the control plane. Reuse its D1 ledger and existing operator
Access identity. Use a distinct private R2 bucket for evidence bytes. The
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
| D1 | Source/model identities, observations, units, provenance pointers, qualifications, contracts, manifests and receipts |
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
deduplication; source origin and scientific identities belong in the next D1
slice, not in filenames or user-supplied object metadata.

Run focused checks from glim-think:

    node --test scripts/private-evidence-objects.test.mjs

These checks use the actual Access verifier with locally signed synthetic JWTs
and in-memory R2 doubles. They do not prove deployed Access/R2 behavior.

## Next slices and acceptance

1. **Private deployment boundary.** Verify that the selected bucket has no public
   custom domain or r2.dev access and is not bound to any public artifact reader.
   Configure an isolated acceptance environment within existing authority.
   Prove unauthenticated denial, authenticated PUT/GET hash agreement and no
   corresponding public artifact access. Do not infer privacy from an unknown
   object key. Production deployment requires its specific authorization.
2. **D1 corpus projection.** Preserve existing row IDs and source IDs. Record the
   immutable source-object hash plus JSON pointer, original row hash, schema,
   original observation/review time, unit, observable, material/state, model,
   reference and missing fields. Preserve quarantine events as separate immutable
   rows targeting exact row hashes; never silently repair or delete originals.
   Keep imported observations distinct from executed or independently checked
   results. Include original OpenKIM/NIST identifiers and DOI aliases.
3. **Transactional manifest publication.** Upload/check objects first; publish
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
path and a migrated, recoverable corpus. This initial private byte route alone
does not satisfy that objective.

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
