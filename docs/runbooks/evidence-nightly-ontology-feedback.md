# Nightly evidence-to-ontology feedback

The `ontology-feedback` job in `.github/workflows/evidence-nightly.yml` closes the
repository's existing evidence/D1 loop. It does not introduce another database.

## Production input

At 08:00 UTC the job reads the previous UTC day's directory from:

```text
gs://shed-489901-atlas-outputs/evidence-nightly/YYYY-MM-DD/
```

That directory must contain `cycle.json` and every manifest, JSONL row file, and
artifact named by those rows. `cycle.json` is:

```json
{
  "campaigns": [
    {"manifest": "relative/manifest.json", "measurements": "relative/rows.jsonl"}
  ]
}
```

Paths are relative to `cycle.json`. Evidence artifact paths inside measurement
rows remain repository-relative and must resolve inside the checked-out tree.
Missing input, broken row hashes, scope drift, or missing artifacts fail the job.

## Ordered stages

1. Production runs rehydrate the latest immutable ontology-corpus archive from
   `evidence-nightly/ontology-state/`. The archive contains the complete
   `registry/claims` and `evidence/v1/examples` corpus from the last successful
   D1 cycle, so independent demonstrations remain available across fresh runners.
2. `tools/run_nightly_cycle.py` ingests every row set through
   `ingest_campaign_results.py`, regenerates the assumption registry, and compiles
   the runtime gate through `atlas_theorem_sync.py`.
3. Wrangler applies D1 migrations and exports the current
   `literature_hypotheses` plus the set of bundle hashes already known to D1.
4. `tools/nightly_ontology_feedback.py` validates each asserted acceptance outcome
   against its typed comparator, measured value, and threshold before computing
   monotonic readiness upgrades. One passing campaign permits `L→M`; two
   independent passing campaigns permit `M→H`. A discovery-chain assumption with
   negative evidence supersedes hypotheses bound to that chain.
5. The generated SQL inserts the new EvidenceBundle, appends a `status_event`,
   updates the hypothesis, and refreshes `literature_reprioritization_queue` in
   one transaction. Queue rows follow `discoveryChains` order in atlas v2.
6. Before committing that SQL to D1, the job writes a run-addressed immutable
   corpus archive to the existing GCS output bucket. D1 can therefore never get
   ahead of the restorable claim/evidence corpus: a failed archive upload leaves
   the ledger untouched, while a failed D1 transaction leaves an unused immutable
   archive that a retry may safely supersede.
7. Wrangler applies the SQL to the existing `glim-ledger` D1 database. The job
   also uploads the SQL, queue JSON, runtime gate, complete claim/evidence corpus,
   staging evidence (when selected), Markdown digest, and machine-readable
   `hermes.digest-card.v1` card.

## Anti-laundering invariant

A status or readiness update is eligible only when its authorizing bundle was
created by the current ingest and was absent from D1 before the cycle. Migrations
0013–0014 require a matching append-only `status_event` and prevent a hypothesis
from reusing the same bundle hash for another transition. The event must be the
latest event appended for that hypothesis, so an older transition receipt cannot
authorize a repeated state edge. There is no manual override or exception path.

## Staging verification

Run **Evidence Index Nightly** manually with `staging_fixture=true`. The checked-in
Z1 fixture ingests four hash-chained rows, recompiles assumptions/gates,
supersedes the three C1 examples with the new negative receipt, and leaves the C2
gap fixture as priority 2 in the literature queue. Inspect
`nightly-output/staging-evidence.json` and `hermes-digest-card.json` in the
`ontology-feedback-2026-08-01` artifact.
