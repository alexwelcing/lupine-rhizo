# Protocol-offset sign-skew replication — preregistration draft

**Status:** DRAFT / NOT REGISTERED / NO EXECUTION AUTHORIZED

**Campaign:** `literature.protocol-offset-sign-skew.replication.v1`

**Driving card:** `t_1051dfa4`

**Design card:** `t_295fa36d`

**Epistemic marker:** `OBS`

**Current readiness:** `M`

**Target:** evidence sufficient for an independently reviewed `M → H` decision; this document does not itself change readiness.

This draft freezes the design choices that can be made before an owner spend decision. It is deliberately not a registered CampaignManifest: it has no invented registration timestamp or content hash. The source-derived candidate panel is materialized and byte-locked below, and a non-registerable manifest draft records that input lock. Neither artifact may be copied into `campaigns/v1/` or `registry/campaigns.v1.json` until every pre-execution gate below passes.

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

The candidate lock is:

`data/candidates/z1-sign-skew-replication-panel.lock.json`

Its current byte digest is `sha256:1fe44e3ebf19a3af29621ccfcb02e5f5352745f63e53fc30113b340cabfbf770`. It was reconstructed from the pinned 68,583,182-byte source archive after its SHA-256 matched the frozen source digest. The archive contains 1,681 indexed rows and 103 lexically eligible official-test chemical systems; 73 systems remain after excluding every path ID, chemical system, and exact reference barrier in the original 30-path Z1 lock. The preregistered rule selects the first 30 of those 73.

### Frozen candidate list

Barrier values in the table are displayed to nine decimal places in eV; the JSON lock preserves the source float values used for exact overlap checks.

| # | path_id | material_id | chemical_system | reference barrier (eV) |
|---:|---|---|---|---:|
| 1 | `mp-34038_0_0_1_-1_0` | `mp-34038` | `Cl-Li-N` | 1.175040090 |
| 2 | `mp-25465_1_0_0_0_1` | `mp-25465` | `Co-F-Li-O-P` | 0.857966930 |
| 3 | `mp-764867_1_8_0_1_1` | `mp-764867` | `Co-Fe-Li-Mn-O-P` | 1.519494620 |
| 4 | `mp-761094_0_2_0_0_1` | `mp-761094` | `Co-Fe-Li-O` | 4.479324730 |
| 5 | `mp-778830_1_9_1_1_0` | `mp-778830` | `Co-Fe-Li-O-Ti` | 0.259047570 |
| 6 | `mp-1277613_2_0_0_0_1` | `mp-1277613` | `Co-Li-Mg-O` | 0.569500100 |
| 7 | `mp-1222510_2_2_0_1_0` | `mp-1222510` | `Co-Li-Mn-Ni-O` | 1.738020940 |
| 8 | `mp-1175624_0_3_0_1_0` | `mp-1175624` | `Co-Li-Mn-O` | 0.407103630 |
| 9 | `mp-771821_0_2_0_0_0` | `mp-771821` | `Co-Li-Nb-O` | 0.113873930 |
| 10 | `mp-1284600_2_7_0_0_0` | `mp-1284600` | `Co-Li-Ni-O` | 0.411957400 |
| 11 | `mp-1174212_5_7_0_0_0` | `mp-1174212` | `Co-Li-O` | 0.872763930 |
| 12 | `mp-774843_0_1_0_0_0` | `mp-774843` | `Co-Li-O-Sn-V` | 0.820140140 |
| 13 | `mp-1297766_1_5_1_-1_0` | `mp-1297766` | `Co-Li-O-Ti` | 2.696653170 |
| 14 | `mp-1177804_0_1_0_0_1` | `mp-1177804` | `Co-Li-O-V` | 1.688745690 |
| 15 | `mp-759082_0_2_0_0_0` | `mp-759082` | `Cr-F-Li-O-P-V` | 0.825259820 |
| 16 | `mp-768843_14_11_0_1_1` | `mp-768843` | `Cr-Li-Mn-O` | 0.381866880 |
| 17 | `mp-772613_0_1_0_0_0` | `mp-772613` | `Cr-Li-Ni-O` | 0.431553220 |
| 18 | `mp-757068_0_1_0_0_0` | `mp-757068` | `Cr-Li-Ni-O-P` | 0.049742020 |
| 19 | `mp-770861_11_9_0_1_0` | `mp-770861` | `Cr-Li-O` | 0.808866680 |
| 20 | `mp-26965_0_2_0_1_0` | `mp-26965` | `Cr-Li-O-P` | 0.298806100 |
| 21 | `mp-759753_4_0_0_0_1` | `mp-759753` | `Cr-Li-O-P-V` | 0.614104000 |
| 22 | `mp-757461_1_2_0_1_0` | `mp-757461` | `Cr-Li-O-Si` | 0.198076080 |
| 23 | `mp-777670_0_1_0_0_0` | `mp-777670` | `Cr-Li-O-Sn-V` | 0.741354060 |
| 24 | `mp-768421_3_7_0_0_0` | `mp-768421` | `Cr-Li-O-Ti` | 0.717093510 |
| 25 | `mp-755839_0_5_0_0_0` | `mp-755839` | `Cr-Li-O-V` | 0.547669930 |
| 26 | `mp-758720_0_3_1_0_0` | `mp-758720` | `Cu-F-Li` | 0.476001790 |
| 27 | `mp-26247_6_9_0_0_0` | `mp-26247` | `Cu-Li-O-P` | 0.614260960 |
| 28 | `mp-758793_0_1_0_0_0` | `mp-758793` | `Cu-Li-O-Si` | 0.228663910 |
| 29 | `mp-777279_19_7_1_0_0` | `mp-777279` | `F-Fe-Li-O` | 0.389350030 |
| 30 | `mp-759229_3_6_0_1_0` | `mp-759229` | `F-Fe-Li-O-P` | 0.616877330 |

A direct set comparison against both `data/candidates/z1_nebdft2k_barriers.lock.json` and `data/candidates/z1-union-campaign.json` gives zero shared path IDs, zero shared chemical systems, zero shared `(chemical_system, model)` pairs for the four canonical models, and zero exactly equal reference barriers. This establishes the requested candidate-level disjointness. It does not replace the registration-time gate, which must reconstruct every full path record from the pinned archive and verify the manifest, sidecars, registry, and reviewed source document together.

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

The non-registerable field-complete draft is `docs/plans/2026-08-03-protocol-offset-sign-skew-replication-campaign-manifest-draft.json`. Its `preregistration.recorded_inputs` lock binds the candidate panel and current byte digest. The wrapper deliberately records `registered_at: null` and omits `content_hash`; therefore it cannot validate as, or be mistaken for, a registered CampaignManifest. Registration must materialize only the inner manifest after replacing the draft source lock with the reviewed canonical document lock and supplying the operator timestamp and RFC 8785 hash.

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

### Cost model, per-path planning range, and contingency

- **Per-path planning basis:** the locked Z1 ledger contains 23 measured paths, each with 5 or 7 GPAW anchors. Observed per-path GPAW wall time spans `0.37–6.45 h`. This observed range—not a newly derived dollar-per-path claim—is the honest pre-measurement estimate for one replication path. Chemistry, cell size, SCF convergence, and the four model-dependent anchor proposals can move a new path anywhere within or beyond that range.
- **Total campaign basis:** all 30 frozen paths must reach a terminal measured-or-failed state. The exact anchor count is unknowable until the four locked models produce their preregistered guidance, so the campaign must not fabricate a point dollar estimate by multiplying a mean path or anchor count. The reviewed administrative source contract instead supplies the total ceiling: 10 verified Z1 ledger units, exactly **USD 146.50**.
- **Contingency:** the 10-unit ceiling is the explicit contingency envelope for path-size variance, SCF variance, model-guidance variance, and one-pass infrastructure overhead. It is a stop-loss, not permission to consume the full amount. The launcher records spend against this campaign alone, refuses new scheduling at the ceiling, and permits no silent retry.
- **Fail-closed estimate status:** there is no approved standalone dollar-per-path claim. If registration review requires one, the campaign remains blocked until a new source contract freezes the reviewed anchor cardinality, applicable Cloud Run rates, and arithmetic. No derived dollar or percentage from this section may be republished as public economics.

The existing **USD 100 Z2 ceiling is insufficient as authorization** even if actual replication spend might finish below it: it is scoped to a different campaign, cannot be transferred, and is below the replication-specific USD 146.50 owner-note ceiling required by the checked-in cost-basis contract. Combining or silently reusing the Z2 and THEORY-3 ceilings is prohibited.

This is a stop-loss proposal, not an expected-cost estimate, public economics claim, or reuse of the separate Z2 or THEORY-3 authorizations. The launcher must refuse until Alex explicitly approves a replication-only cap and the preserved ledger conflict has passed the required owner/reviewer gate. It must not charge this campaign against another ceiling, must stop scheduling new work at the approved ceiling, and must not retry automatically beyond it.

Owner decision required: approve **USD 146.50**, replace it with another explicit ceiling backed by a reviewed source contract, or decline the campaign.
