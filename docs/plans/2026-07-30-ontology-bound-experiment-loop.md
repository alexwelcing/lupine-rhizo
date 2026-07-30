# Architecture Plan: Ontology-Bound Experiment Loop (2 days)

**Date:** 2026-07-30 · **Author:** Coordinator (owner request `rms7nt6j2`) · **Status:** preregistration-grade plan
**Scope guardrail note:** the standing posture since 2026-07-20 is *local-first, cloud fleet cancelled* (`RESEARCH_COMMAND_CENTER.md`). This plan revisits that decision at the owner's explicit request (GCP scale, k8s or Cloud Run). It recommends **Cloud Run, not k8s**: per-job billing to zero, no cluster control plane to own, and every current dispatch seam (`glim-think/dispatch.ts` → Cloud Tasks → `tasks-consumer` → `jobs.run`) already terminates there. k8s becomes rational only at sustained >40% GPU utilization across ≥3 models; revisit then.

## North star

One closed loop, typed end to end:

**literature → typed hypotheses (T1–T7 / MC1–MC9 / C1–C11 / Z1–Z11 bound) → campaign manifests → scalable Cloud Run execution → hash-chained rows → EvidenceBundles → assumption registry + runtime gate + ontology status → re-prioritized literature.**

The two hard facts that shape everything:

1. **The ontology vocabulary already exists in Lean** — `lean-spec/OpenDistillationFactory/ErrorLandscape/{Types,Emblems,MasterMatrix}.lean`, `DiscoveryChains/Core.lean` + `Chain01..11.lean` (machine-checked `contract_valid` + `gate_clearance`), `HonestErrors/{Taxonomy,StageGates,Acceptance}.lean`. The new atlas JSON (`lupine-ontology.json`, vendored at `lupine-ledger/content/ontology/`) is the *publication* form of what the proof plane already carries. The missing piece is **identifier binding**: Lean has no literal `MC1..MC9`, and campaign artifacts don't carry ontology IDs.
2. **The lit→experiment hop is manual.** Literature ingestion exists (`glim-think/src/literature/*`, queue kind `literature`), hypothesis tables exist (`migrations/0001_hypotheses.sql`), and the evidence bridge is schema-complete (rows → bundles → contracts → registry → gate) — but nothing converts a paper into a typed, manifest-ready experiment.

## Workstream A (Day 1): Ontology binding layer

**A1. Bind MC IDs into the proof plane.** Add `MaterialClassId` (`MC1..MC9`) to `lean-spec/OpenDistillationFactory/DiscoveryChains/Core.lean` beside `ChainId`; add `classFor : ChainId → Option MaterialClassId` (C10 meta-chain → none; MC9 → {C6, C11}); `#guard` the master-matrix row count and the 1:1 `acceptanceFor`. Acceptance: `lake build` green, zero sorry, `check_assumption_links.py` parity.

**A2. Register the atlas as a versioned artifact.** Copy `lupine-ontology.json` into `registry/ontology/atlas.v1.json` with a `snapshots/ontology.lock.json` (sha256 + atlasDate 2026-07-30 + freshnessLayer). Add `tools/check_ontology_links.py`: every `materialClasses.chain` resolves, every `acceptanceTests.chain` is 1:1 with `discoveryChains`, readiness grades parse (handle `M (L→M boundary)` annotation), relation labels namespaced (`claim.correctedBy` vs `lever.correctedBy`). Wire into anti-laundering CI: **ontology status changes require new EvidenceBundle hashes, same rule as registry statuses.**

**A3. LiteratureHypothesis v1 schema.** New `schemas/literature-hypothesis.v1.schema.json`: `{source:{arxiv/openalex/ss id, doi, url, asOf}, claim_text, bindings:{errorTypes[], materialClasses[], chains[], acceptanceTests[]}, epistemicMarker: OBS|INF|TRN|PRP|FRC, readiness: H|M|L(+annotation), confidence: High|Medium, proposedExperiment:{metric, predicate (typed-measurement whitelist), panel_ref?, estimated_cells, estimated_gpu_hours}, status: proposed|accepted|rejected|superseded}`. D1 table via `glim-think/migrations/0012_literature_hypotheses.sql`. Acceptance: schema + migration + 3 example hypotheses hand-authored from `lit-review/synthesis-mlip-correction-2026-07-20.md` validate clean.

**A4. Lit→manifest converter (v0 deterministic).** `tools/lit_to_manifest.py`: hypothesis → `campaigns/v1/*.json` skeleton (preregistration block frozen_before_execution, target_premises from bindings.chains, acceptance_test from bindings.acceptanceTests, candidate_panel from the hypothesis panel_ref or the nearest locked panel). v0 is deliberately boring: no LLM judgment, just schema mechanics + allowlist enforcement. Agent review (hermes researcher card) happens between A3 intake and A4 conversion.

## Workstream B (Day 2): Execution fabric + feedback loop

**B1. Prove the unified runner in GCP.** `gcp/mlip-cell-runner/cloudbuild.unified.yaml` + `Dockerfile.unified` → `gcr.io/shed-489901/mlip-runner:mace` (one backend first). Run the 4-row Z2 abstention panel as the smoke campaign (zero scientific spend by design, full pipeline exercise). Checklist from `DECOMMISSION.md`; evidence: run id, artifact in `gs://shed-489901-atlas-outputs`, beat received.

**B2. Generalize dispatch.** `tasks-consumer` allowlist moves from env var to `gcp/mlip-cell-runner/backend_catalog.json` (already the catalog of record); new job onboarding = catalog entry + Cloud Run job, no consumer redeploy. Activate two `policies/` schedules: `nightly-baseline` (small fixed panel, cost-capped) and `on-proof-complete` (theorem re-pin → validation sweep). Budget guard: per-schedule daily GPU-hour cap in the policy file; `lupine-ops monitor_cloud_run` reports against cap; Z1 cost ledger ($14.65/129 anchors) is the reference unit for all estimates.

**B3. Close the loop nightly.** `evidence-nightly.yml` extension: (1) ingest day’s rows (`ingest_campaign_results.py`); (2) regenerate assumptions + runtime gate (`generate_assumptions.py`, `atlas_theorem_sync.py`); (3) **ontology status refresh** — hypotheses referencing refuted premises → `superseded`, chains clearing acceptance tests get readiness re-graded per §7.2 of the atlas (L→M→H only on dated defined evidence); (4) emit the literature re-prioritization queue — hypotheses whose bindings touch active chains with fresh evidence gaps, ordered by chain priority. Output is a D1 table + a hermes digest card each morning.

**B4. Telemetry parity.** Cloud cycles emit the same flywheel traces as local (known gap in AGENTS.md): `tasks-consumer` posts an OTLP envelope per cell to the glim-think relay; `mlip_phoenix_trace.py` accepts cloud-originated spans.

## Sequencing

| Day | Morning | Afternoon | Gate |
|---|---|---|---|
| 1 | A1 Lean binding + build | A2 atlas registry + CI check | `lake build` + anti-laundering CI green |
| 1 | A3 schema + migration | A4 converter + 3 example hypotheses | hermes researcher review of converter output |
| 2 | B1 unified image build + smoke | B2 catalog dispatch + 2 schedules | Z2 abstention panel green end-to-end in GCP |
| 2 | B3 nightly loop wiring | B4 telemetry + cost-cap report | one full nightly cycle on staging data |

## Explicitly out of scope

k8s (see guardrail); Z1 full-panel execution (deferred pending budget — this fabric makes it *ready*, not executed); new typed-measurement predicates beyond the barrier whitelist (schema change, separate preregistration); LLM-authored hypotheses (agent review stays human-ledgered via hermes cards).

## Risks

- **Ontology laundering** (status drift without evidence) → A2's CI rule is the entire defense; no exceptions.
- **Cost creep** → per-schedule caps + monitor; anything exceeding Z1-ledger unit cost ×10 needs an owner note, not a silent retry.
- **Split-brain evidence** (D1 vs repo bundles vs pgvector) → B3 writes through the existing migration/sync path only; no new stores.
