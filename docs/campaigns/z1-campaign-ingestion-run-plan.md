# Z1 Campaign Ingestion Run Plan

## Scope

Z1 (Hard Materials Honest Errors Chain 1): barrier-accurate MLIPs for solid-state batteries. Acceptance test Z1: migration-barrier MAE ≤ 40 meV against DFT-NEB references across chemistries, with balanced signed errors.

## Locked Candidate Panel

Four cloud models, content-addressed:

| Model ID | Version | Constructor Selector | Artifact Hash |
|---|---|---|---|
| chgnet | round4-v1 | mlip-cell-chgnet | sha256:… |
| mace-mp-small | round4-v1 | mlip-cell-mace-mp-small | sha256:37b83d134c8e20e8f26603b50a4e8b0b4359632c2e2b2b2bc1dc553716315b53 |
| mace-mp-medium | round4-v1 | mlip-cell-mace-mp-medium | sha256:37b83d134c8e20e8f26603b50a4e8b0b4359632c2e2b2b2bc1dc553716315b53 |
| mace-mpa-0-medium | round4-v1 | mlip-cell-mace-mpa-0-medium | sha256:37b83d134c8e20e8f26603b50a4e8b0b4359632c2e2b2b2bc1dc553716315b53 |

## Measurement Set

- **Legacy anchors:** five charged-vacancy experimental references (LiF, LiCl, LiBr, LiI, NaCl) from the Round-3 corpus.
- **Campaign set:** 30 chemistry-held-out DFT-NEB paths locked at
  `data/candidates/z1_nebdft2k_barriers.lock.json` (SHA-256
  `192fe54a5579cc421f6644d5d76fb442c6dfb985f014dc4741549e29052efb68`).
  The panel takes one deterministic path from each of 30 distinct chemical
  systems in LiTraj's official nebDFT2k test split. Those systems and every NEB
  image are excluded from Z1 barrier-targeted fitting, calibration, model
  selection, and threshold tuning.

Each path includes the complete BVSE-preconditioned input image sequence, the
DFT-relaxed initial endpoint, saddle, and final endpoint, the full DFT energy
profile, reference barrier, and the frozen CI-NEB convergence protocol. Rebuild
from the source archive with:

```bash
uv run --with ase python tools/build_z1_barrier_panel.py \
  --source /path/to/nebDFT2k.zip
```

## Row Schema (JSONL)

Each measurement row is a JSON object with these fields:

| Field | Type | Unit | Description |
|---|---|---|---|
| campaign_manifest_hash | sha256 string | — | Content hash of the CampaignManifest |
| previous_row_hash | sha256 string or null | — | Hash chain link |
| row_hash | sha256 string | — | Content hash of this row |
| claim_predicate | string | — | e.g. `barrier_mae_mev<=40` |
| scope | object | — | structures, chemistries, conditions |
| metric | string | meV | `barrier_mae` |
| value | number | meV | Measured MAE |
| unit | string | — | `meV` |
| acceptance_test | object | — | comparator, threshold, outcome |
| sample_count | integer | — | Number of paths evaluated |
| model_id | string | — | MLIP identifier |
| model_version | string | — | Model version |
| artifact_uri | string | — | GCS URI of raw output |
| artifact_hash | sha256 string | — | Content hash of raw output |

## Hash Conventions

- `row_hash`: SHA-256 of the RFC 8785 canonical JSON of the row with `row_hash` omitted.
- `campaign_manifest_hash`: SHA-256 of the canonical CampaignManifest with `content_hash` omitted.
- `previous_row_hash`: `row_hash` of the previous row in the chain, or null for the first row.

## Ingestion

Run `tools/ingest_campaign_results.py` with the manifest and measurement rows. The tool validates scope compatibility, hash chains, and fail-closed on missing evidence.

## Blockers

- Cloud Run NEB optimization support is not yet implemented in deployed images;
  the locked panel is now directly resolvable from the Z1 CampaignManifest, so
  runner work no longer needs to source or choose candidates.
