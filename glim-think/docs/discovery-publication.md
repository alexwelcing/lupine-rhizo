# Hosted discovery publication

`ResearchPublication` is a named WorkerEntrypoint of `glim-think-v1`. Its only
operation is a fixed `POST /publish` with a canonical JSON
`lupine.discovery_publication.v1` envelope. Bind only the authorized
`lupine-research-team-v02` producer to this entrypoint. The default HTTP handler
does not route `/publish`. Existing operator imports still require their own
same-origin and Cloudflare Access verification; this does not add a bearer-token
bypass or give the producer a general Rhizo API capability.

The policy `accepted-discovery-public/v1` is an explicitly automated publication
lane for accepted, archived reports. The producer validates provenance and
applies the public projection policy before enqueuing immutable bytes. The
receiver checks the strict contract, hash joins and already-published lineage.
These checks do not establish scientific correctness, current source availability,
external peer review or empirical validation. Activity `completed` means this
individual report was produced and accepted. Verification remains `pending`.

The contract is implemented in `src/workspace/discoveryPublicationContracts.ts`.
Evidence preserves the complete bounded accepted report with public source
references, role/provider/model attribution, public topic and parent identities,
prior report links, and private artifact hash commitments. It excludes native
task/account identities, original private source references, private prompts and
raw model output. Unsafe text is quarantined, not silently sanitized or truncated.
The sole discovery-evidence path-token exception is the exact standalone
scientific package-family token `KOKKOS/GPU/OPENMP`. Validation masks that token
only for the path heuristic, preserving the original published bytes; paths,
extensions, neighboring letters and other slash strings remain rejected. The
older activity-v1 text validator is unchanged.
`parentPublicationId` and `parentQuestionIndex` are a paired exact origin link:
the child question must equal that indexed question in the published principal
report. Generic source-derived topics with no known question origin leave both
null; a known parent topic alone does not assert an exact question relationship.
The model identity is controller-reported. Private hashes do not make raw output
publicly reproducible. Queries and questions are proposals, not execution authority.

## Persistence and delivery

Apply additive migration `0024_discovery_publication.sql` after existing
`0021_public_research_activity.sql` and `0023_public_activity_archive.sql`. This
creates only the evidence metadata and publication membership tables; semantic
nodes, edges and events use the existing Rhizo knowledge store.

One D1 batch commits the activity, evidence, nodes, membership, edges and event.
The initial D1 session read uses `first-primary` when sessions are available and
readback stays in that session. Acknowledgement requires exact record, evidence
and projection readback. An unknown outcome does not authorize a new identity:
the producer retries the exact canonical bytes. Duplicate delivery repairs a
missing projection only when its immutable evidence and existing nodes match.
Conflicting IDs, source identities and terminal history are never overwritten.

`recordSha256` covers `JSON.stringify` of the normalized existing activity-v1
record, matching the activity archive. `evidenceSha256` covers sorted-key
canonical JSON, the exact bytes returned by the evidence endpoint.
`projectionSha256` covers sorted canonical public nodes and edges. Unicode values
are preserved; keys and projection arrays use explicit lexical ordering.

An accepted report has its own `discovery-<archiveSha256>` activity identity.
Earlier roles and an explicitly linked parent must already be published, hash
verified, and present in the knowledge store. Missing dependencies return
`409 publication_dependency_missing`; contradictory identities or claim indices
return `409 publication_conflict`. Storage ambiguity returns `503
publication_unavailable`. These delivery outcomes never retry research inference.
Every prior role must retain the exact ordered prefix of the current prior list.
All roles must retain the same complete topic question and parent origin. Reports
from different histories under one topic cannot be combined into a new assessment.

## Public reads and knowledge

- `GET /research/activity` and its existing archive expose the accepted record.
- `GET /research/activity/<publication-id>/evidence` returns the exact canonical
  evidence bytes pinned by the activity's unique `Public evidence` hash.
- `GET /research/knowledge?after=0&limit=10` returns immutable publication nodes
  and edges from `knowledge_documents` and `knowledge_edges`. Continue with the
  returned `nextAfter` and fixed `snapshot`; these are archive sequence cursors.
  The limit counts publications, at most ten per page. It is not a global graph
  completeness claim. Coverage describes only this publication namespace as of
  the pinned snapshot. The lookahead is validated before any successful page.

Public knowledge pages have schema `lupine.public_discovery_knowledge.v1`,
`publicationIds`, `nodes`, `edges`, `hashes`, `cursor`, and `coverage`.
Shared immutable source and topic nodes preserve exact identities. Claims,
concepts, assessments and questions retain publication provenance; concept names
are not silently merged or treated as synonyms. Assessment edges resolve an
actual claim in an earlier published report. Disposition is never converted to
support or contradiction. Cross-page edge targets can be resolved through the
linked exact evidence endpoints or by completing the snapshot traversal.
The `publication:derived-from` relation denotes cited source attribution only;
it does not assert logical derivation, empirical support, or independent validation.

The endpoint does not run generic ledger sync, read private research tables,
fetch cited sources, call models, create research work, or change scheduled jobs.
No general knowledge-library write authority is granted to the producer.

## Validation

The SQLite-backed tests execute the actual additive migrations and transactional
batch, including rollback, unknown acknowledgement, exact duplicate recovery,
projection repair, immutable history, privacy rejection, cross-report claim
validation, public snapshot pagination and the four accepted producer fixtures.

```sh
npm run build:workspace
node node_modules/vitest/vitest.mjs run src/workspace/__tests__/discoveryPublication.test.ts src/workspace/__tests__/researchActivity.test.ts
```

Local tests and a successful bundle do not prove the service binding is deployed,
the migration is installed remotely, the producer delivered an event, or the
Library rendered it. Verify those gates separately after release.

## Additive source availability notices

The same fixed `ResearchPublication` entrypoint accepts the separate
`lupine.discovery_source_withdrawal.v1` envelope. It contains only the producer,
notice and original publication identities, original record/evidence digests,
cited source semantic digest, and original withdrawal observation time. Its
`withdrawal-` identity is the SHA-256 of the canonical envelope without `id`.
The canonical envelope is capped at 2,048 bytes. Unknown fields, accessors,
noncanonical wire bytes, duplicate JSON keys, future timestamps and changed
identities are rejected before writes.

Migration `0025_discovery_source_availability.sql` adds immutable notice and
public graph-membership tables. The receiver verifies the original public
record, evidence, citation and existing graph projection. One D1 transaction
adds a standard activity record, the exact envelope, one notice node, two typed
edges, and an event. All of these, including the archive sequence, are read
back before acknowledgement. A lost acknowledgement permits an exact
idempotent retry; an unknown or incomplete readback never reports success.

The notice is available through the existing activity/archive endpoints and
`/research/activity/<withdrawal-id>/evidence`. Its activity hash label is
`Source availability notice`; the sidecar is the exact canonical withdrawal
envelope. The knowledge endpoint includes it in the same bounded archive
sequence pagination, linking the notice to the original report and cited
source. Edges originate at the new notice so the original report's graph
projection and all old hashes remain unchanged.

A feed withdrawal is an availability observation. It does not establish
publisher retraction, falsity, scientific invalidation or current source
inaccessibility. The notice is an additive activity with `supersedes: null`;
it does not replace or reopen the original report. The receiver derives every
public sentence and URL from a fixed template and the already public record;
the producer cannot submit arbitrary notice text or links.
