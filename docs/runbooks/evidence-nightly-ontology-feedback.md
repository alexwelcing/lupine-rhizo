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

1. `tools/run_nightly_cycle.py` ingests every row set through
   `ingest_campaign_results.py`, regenerates the assumption registry, and compiles
   the runtime gate through `atlas_theorem_sync.py`.
2. Wrangler applies D1 migrations and exports the current
   `literature_hypotheses` plus the set of bundle hashes already known to D1.
3. `tools/nightly_ontology_feedback.py` computes monotonic readiness upgrades
   from dated, typed acceptance outcomes. One passing campaign permits `L→M`;
   two independent passing campaigns permit `M→H`. A discovery-chain assumption
   with negative evidence supersedes hypotheses bound to that chain.
4. The generated SQL inserts the new EvidenceBundle, appends a `status_event`,
   updates the hypothesis, and refreshes `literature_reprioritization_queue` in
   one transaction. Queue rows follow `discoveryChains` order in atlas v2.
5. Wrangler applies that SQL to the existing `glim-ledger` D1 database. The job
   uploads the SQL, queue JSON, runtime gate, staging evidence (when selected),
   Markdown digest, and machine-readable `hermes.digest-card.v1` card.

## Anti-laundering invariant

A status or readiness update is eligible only when its authorizing bundle was
created by the current ingest and was absent from D1 before the cycle. Migration
0013 additionally requires a matching append-only `status_event` and prevents a
hypothesis from reusing the same bundle hash for another transition. There is no
manual override or exception path.

## Staging verification

Run **Evidence Index Nightly** manually with `staging_fixture=true`. The checked-in
Z1 fixture ingests four hash-chained rows, recompiles assumptions/gates,
supersedes the three C1 examples with the new negative receipt, and leaves the C2
gap fixture as priority 2 in the literature queue. Inspect
`nightly-output/staging-evidence.json` and `hermes-digest-card.json` in the
`ontology-feedback-2026-08-01` artifact.
