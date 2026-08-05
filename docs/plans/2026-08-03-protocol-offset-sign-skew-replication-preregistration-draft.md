# Protocol-offset sign-skew replication — preregistration draft

**Status:** DRAFT / NOT REGISTERED / NO EXECUTION AUTHORIZED

**Campaign:** `literature.protocol-offset-sign-skew.replication.v1`

**Driving card:** `t_1051dfa4`

**Epistemic marker:** `OBS`

**Current readiness:** `M`

**Target:** evidence sufficient for an independently reviewed `M → H` decision; this document does not itself change readiness.

This draft freezes the design choices that can be made before an owner spend decision. It is deliberately not a CampaignManifest: it has no invented registration timestamp, no candidate-panel digest, and no content hash. It must not be copied into `campaigns/v1/` or `registry/campaigns.v1.json` until every pre-execution gate below passes.

## Question and frozen hypotheses

The first campaign found a positive signed protocol offset when sparse-anchor GPAW(PBE, finite-difference mode, `h=0.20`, Gamma point) barriers were compared with LiTraj nebDFT2k PBE CI-NEB reference barriers. Does the sign and preregistered magnitude band replicate on a fully disjoint path and chemistry panel?

- **H1 (primary):** more than half of measured path-level signed errors are positive.
- **H2 (registered magnitude band):** the median measured path-level signed error is between `+400 meV` and `+600 meV`, inclusive.
- **Reduction:** for each path, take the median of the available per-model signed errors; then compute H1 and H2 over path medians.
- **Unit semantics:** per `(path, model)`, sparse-anchor GPAW barrier minus the pinned nebDFT2k reference barrier, in meV. Anchor sets are model-dependent. Failures are disclosed without imputation.

H1 and H2 preserve the existing registered acceptance/demotion semantics. No threshold, tail exclusion, outlier rule, or alternative reduction may be chosen after measurements exist.

## Independent panel lock

Use the pinned LiTraj nebDFT2k source already named by `tools/build_z1_barrier_panel.py`:

- paper: *Benchmarking machine learning models for predicting lithium ion migration*, DOI `10.1038/s41524-025-01571-z`;
- source repository: `https://github.com/AIRI-Institute/LiTraj`;
- source revision: `c3ca5c2afbc13ffc823306f546dcee24486ade2a`;
- source archive SHA-256: `b7a99d89337902e9e1da319f57547170fdb132bf15bf6ffef03a0140e2207d7f`.

The replication panel must contain exactly 30 official-test paths, one path per chemical system. Selection is deterministic:

1. Reproduce `chemistry_held_out_rows` from `tools/build_z1_barrier_panel.py`: one lexically first `(material_id, edge_id)` row per lexically ordered official-test chemical system.
2. Exclude every path ID, chemical system, and exact reference barrier present in `data/candidates/z1_nebdft2k_barriers.lock.json`. This is stronger than checking only the 23 measured rows in `data/candidates/z1-union-campaign.json`.
3. Take the first 30 remaining rows in the same lexical order.
4. Refuse if fewer than 30 rows survive or if any selected path ID, chemical system, or exact reference barrier overlaps either frozen Z1 artifact.

The seven previously deferred `>=159`-atom paths are not reused here. They belong to the original 30-path lock, provide only seven candidates, and therefore do not satisfy the stronger independent-panel design or the measured-path floor by themselves. Their existing `waiting` status remains unchanged.

The future lock path is:

`data/candidates/z1-sign-skew-replication-panel.lock.json`

It must validate against `schemas/sign-skew-replication-panel.v1.schema.json`, declare schema `lupine.z1.sign_skew_replication_panel.v1` and panel ID `z1-sign-skew-replication-v1`, and contain no unreviewed fields. It must have a current SHA-256 sidecar and preserve the source archive digest, revision, DOI, official-test split, frozen selection rule, selected systems, material/path IDs, executable images with nonsingular periodic cells, finite reference energies and barriers, and the `record failure without imputation` policy. The pre-execution checker must receive the pinned source archive and independently reconstruct the exact 30 selected full path records—including initial geometries, relaxed reference profile, saddle identity, and barrier—from the official-test source; self-declared panel metadata is not sufficient. The checker must use only the canonical repository baseline panel and its sidecar, first-campaign artifact and its sidecar, candidate-panel path and its sidecar, manifest path, and campaign registry; CLI substitution of those evidence roots is forbidden. Panel construction is preregistration preparation only: it may parse pinned public reference inputs, but it must not run any MLIP, GPAW, sparse-anchor, or analysis measurement.

## Model identity lock

All four models are required and are bound by exact `(model_id, artifact_hash, version)`:

| model_id | artifact_hash | version |
|---|---|---|
| `chgnet` | `sha256:27dbc19f3fa710bbb58b6f5e64e0fde5a6941edcb538f92d228b2d90e93f8890` | `chgnet 0.4.2` |
| `mace-mp-small` | `sha256:c69cbc43286d05a8e9974412a4fb5f4e28405f92ac15287537263475dfc3c694` | `mace-torch 0.3.16 / small` |
| `mace-mp-medium` | `sha256:1d80b5c4898b2d22d73dc82b17e1cabe1111d9cd6be4c2a7403dea6fa0ac83f3` | `mace-torch 0.3.16 / medium` |
| `mace-mpa-0-medium` | `sha256:59b5d1db18664525ad20358fe381b7ba71bdb260c8a3d6bbfe5fb5201e3be0d9` | `mace-torch 0.3.16 / mpa-0 medium` |

A missing or mismatched model does not permit substitution. Record its rows as failed and preserve the four-model scope.

## Execution protocol

After registration and review only:

1. Run fresh model guidance for all four locked models on all 30 paths.
2. Build each model-dependent sparse anchor set using the frozen Z1 selection logic. Evaluate the union once per path; do not add post-hoc anchors.
3. Run GPAW single-point evaluations on Cloud Run with PBE, finite-difference mode, `h=0.20`, `kpts=(1,1,1)`, and the same checkpoint parameter binding used by the first union campaign.
4. Compute each sparse barrier as `max(anchor energies) - min(anchor energies)` and subtract the locked reference barrier.
5. Write immutable per-anchor receipts, per-model failures, environment/image identities, Cloud Run execution IDs, and a hash-chained campaign result under a new replication-only artifact prefix. No first-campaign checkpoint or result may be imported.
6. Execute all 30 registered paths. A cost-cap stop or infrastructure interruption makes the campaign `INCONCLUSIVE`; it does not authorize optional stopping or panel replacement.

## Acceptance, demotion, and refusal

A readiness review may consider `M → H` only when all of the following hold:

- at least 22 paths have one or more measured model values;
- H1 passes: `signed_error_positive > 0.5` over path medians;
- H2 passes: `400 <= median_signed_error_mev <= 600`;
- all 30 candidates have a terminal measured-or-failed record, with no imputation;
- the exact panel, model identities, campaign manifest, Cloud Run image, receipts, and output bundle are hash-bound;
- the overlap guard reports zero shared path IDs, chemical systems, `(chemical_system, model)` pairs, and reference barriers;
- repository validators pass in two clean checkouts with byte-identical deterministic artifacts;
- CI and an independent Codex/reviewer-agent review pass; and
- a fresh EvidenceBundle hash supports the dated ontology/readiness decision.

If H1 fails, demote the sign-skew claim. If H2 falls outside the frozen band, demote the magnitude claim even when H1 passes. If fewer than 22 paths are measured, any digest differs, the panel overlaps, the owner cap stops execution, or required provenance is absent, return `INCONCLUSIVE` and do not change readiness.

## Registration transaction — must precede measurements

After the owner cap is recorded:

1. Build and independently inspect the candidate panel; compute its byte digest and sidecar.
2. Materialize `campaigns/v1/literature-protocol-offset-sign-skew-replication.campaign-manifest.v1.json` with:
   - the hypotheses and thresholds above;
   - the four exact model identities;
   - `execution.candidate_panel` bound to the new panel;
   - `preregistration.recorded_inputs` containing the same panel path and byte digest;
   - `preregistration.input_document` bound to the reviewed, non-draft source at `docs/plans/2026-08-03-protocol-offset-sign-skew-replication-preregistration.md`, whose status line must be exactly `**Status:** REVIEWED / READY TO REGISTER`;
   - an operator-supplied UTC RFC 3339 `registered_at` timestamp (never inferred); and
   - its RFC 8785 content hash, generated with the repository-pinned `rfc8785` implementation rather than ordinary sorted JSON.
3. Add the byte-identical manifest entry to `registry/campaigns.v1.json` and refresh the repository-owned registry snapshot/assumption outputs.
4. Run `python tools/check_sign_skew_replication_overlap.py --source-archive data/reference/litraj/nebDFT2k.zip --candidate-panel data/candidates/z1-sign-skew-replication-panel.lock.json --manifest campaigns/v1/literature-protocol-offset-sign-skew-replication.campaign-manifest.v1.json`; exit `0` is mandatory. The source archive must be materialized at that reviewed repository-relative path and must not be a symlink.
5. Run the repository campaign-schema, registry, assumptions, ingestion, and focused replication tests.
6. Open a feature-branch PR, obtain green CI and independent reviewer approval, and obtain Alex's explicit execution approval.
7. Only then create or launch Cloud Run executions.

Any model/GPAW result timestamp earlier than the registered manifest is a preregistration violation and voids confirmatory use.

## Owner spend decision

**Proposal:** authorize a separate **USD 146.50 hard administrative ceiling** for this replication campaign.

The exact proposal is taken from the checked-in `gcp/mlip-cell-runner/policies/cost-basis.json` owner-note gate rather than newly extrapolated here. That contract identifies the measured Z1 ledger at `docs/analysis/z1-union-cost-ledger.md`, locks its SHA-256 as `feca0f96b52508960bc9106ecb73c3488c0563a2702823ddb29558fa41ac0ca4`, records the approved public basis `$14.65 per 129 anchors`, and records the proposed owner-note gate as `multiple_of_verified_unit: 10` and `usd: 146.50`. The same contract preserves the conflicting owner-card figure `$4.65 per 129 anchors` with disposition `not used: no ledger artifact or calculation supports this value`; this preregistration does not resolve that conflict or use it to activate execution.

This is a stop-loss proposal, not an expected-cost estimate, public economics claim, or reuse of the separate Z2 or THEORY-3 authorizations. The launcher must refuse until Alex explicitly approves a replication-only cap and the preserved ledger conflict has passed the required owner/reviewer gate. It must not charge this campaign against another ceiling, must stop scheduling new work at the approved ceiling, and must not retry automatically beyond it.

Owner decision required: approve **USD 146.50**, replace it with another explicit ceiling backed by a reviewed source contract, or decline the campaign.
