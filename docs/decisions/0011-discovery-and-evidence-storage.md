# Discovery and evidence storage

Date: 2026-10-17. Status: implemented components; deployment receipts are separate.

## Decision

Use fff for bounded local source discovery; SQLite FTS5 and pinned sqlite-vec
0.1.9 for the rebuildable local retrieval projection; and the existing D1 SQL
ledger for durable operational records and the reviewed public archive.
Knowledge graph views remain typed projections of versioned sources and claims.
D1 is a managed service, not an open-source database distribution. The local
SQLite, FTS5, sqlite-vec and fff components provide a portable open-source path.

The inspected collection has thousands of comparisons and 94 published articles.
This is not a measured retrieval benchmark or a universal database ranking.
The important requirements here are exact source identity, current postings,
compatible embedding spaces, immutable corrections, private/public separation,
and inexpensive incremental updates. Adding a second database server would not
by itself satisfy those requirements.

## Responsibilities

| Component | Owns | Does not establish |
| --- | --- | --- |
| fff adapter | Private candidate paths and hashes of actual bounded source reads | Source truth, full coverage, support edges, publication |
| SQLite FTS5 | Lexical retrieval over evidence chunks | Scientific relevance or validity |
| sqlite-vec | Exact KNN over a compatible, identified vector generation | Semantic quality, causation, statistical independence |
| D1 / existing claim contracts | Saved run/proposal receipts, claim states, immutable reviewed activity | Correctness of a scientific claim from storage alone |
| Library graph and search | Public articles, reviewed activity, source-bound graph passages | Permission to expose the private retrieval database |
| RUNS comparison preview | Task, competing arms, reference/protocol, decision and stopping rules | Dispatch authorization or an executed experiment |

The stable sqlite-vec release uses exact KNN here. Do not describe this path as
an ANN index or enable an experimental ANN release merely to use a newer label.
Hybrid retrieval combines lexical and compatible semantic rankings; its score
is a discovery signal, never evidence strength.

## From discovery back into the system

1. Run `cocoindex/discover_sources.py` against one authorized project. The private
   envelope supplies paths and current hashes, with explicit partial coverage.
2. Read the actual source and establish the finding, its assumptions, competing
   explanation and relation to existing terrain. Use existing stable source and
   claim IDs; a fuzzy match does not become a knowledge graph assertion.
3. For a saved RUNS proposal, resolve source hashes/anchors, comparison row IDs,
   shared task/reference/protocol, model identity and fitting exposure in its
   comparison contract. The authenticated preview reports missing conditions.
4. Execute only through the existing authorization, ownership and resource
   gates. Reconcile verified outcomes through the existing claim contracts and
   reviewed publication path. Keep unresolved or negative outcomes visible.
5. Library search indexes reviewed public text and corrections immediately;
   additional graph links require source-bound review. Public history uses an
   immutable ingestion sequence so late evidence dates cannot hide new records.

## Generation and recovery

Vector rows retain backend, model revision, dimension, normalization, query
prefix and splitter identity. A mutable model name is not a pinned revision.
Unknown, mixed, test-hash or incompatible generations use lexical retrieval.
Existing source rows are preserved; any re-index is a separate bounded action.
FTS and vector sidecars are replaced with their fingerprints in one transaction.
The failure test uses the actual pinned sqlite-vec extension and verifies that
the previous coherent sidecars survive rollback.

Public archive cursors refer to append-only sequence assignments. Roll back an
application version without dropping or renumbering that history. Incremental
Library refresh must finish its pinned snapshot before advancing the cursor.

## When to reconsider PostgreSQL + pgvector

PostgreSQL with pgvector is the preferred next server option if measured work
requires concurrent independent writers, centralized access control for multiple
operators, or retrieval/graph joins that exceed this embedded design. It supports
exact search, HNSW/IVFFlat and full-text/vector fusion. Before migration, measure
representative filtered queries for recall, p95 latency, write contention,
storage growth and recovery. Choose the index on those measurements. No new
server, paid service, model download or approximate index is part of this release.

Primary references reviewed for this decision:

- [SQLite FTS5](https://www.sqlite.org/fts5.html)
- [sqlite-vec 0.1.9](https://github.com/asg017/sqlite-vec/releases/tag/v0.1.9)
- [pgvector](https://github.com/pgvector/pgvector)
- [fff](https://github.com/dmtrKovalenko/fff)

This architecture decision is engineering judgment. It does not claim a novel
database method or benchmark superiority over other open-source systems.
