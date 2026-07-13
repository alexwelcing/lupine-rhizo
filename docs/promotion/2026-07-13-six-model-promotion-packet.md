# Six-Model Promotion Packet — 2026-07-13

- **Schema (conceptual):** follows `lupine.mlip.local_to_cloud_promotion.v1` (`tools/mlip_local_promotion.py`), rendered as an operator packet because the three scopes below are statics/kinetics/defect panels, not 5x5x3 Distill triplets.
- **House rule:** local → packet → cloud. This packet **emits exact commands only; nothing here has been executed.** Cloud promotion starts from this packet, not from handwritten local settings.
- **Cloud constants:** project `shed-489901`, region `us-central1`, Cloud Run jobs `mlip-cell-sevennet` / `mlip-cell-orb` / `mlip-cell-uma` (allowlisted in `tasks-consumer`; production dispatch is Cloudflare → Cloud Tasks, canaries are direct `gcloud run jobs execute` per the promotion-tool contract).
- **Beat ingress:** `https://glim-think-v1.aw-ab5.workers.dev/feed/beats` (`lupine.mlip.cell_result.v1`, Google-OIDC signed).
- **Ledger:** D1 `glim-ledger` (binding `LEDGER`) — completed cells land in `mlip_baseline_cells` (via `recordMlipBaselineBeat`), ticker rows in `lab_beats`.
- **Artifacts:** `gs://shed-489901-atlas-outputs/...` (per-cell `cell_result.json` + `cell_checkpoint.json`); inputs in `gs://shed-489901-atlas-inputs/...`.
- **Variant scope:** `baseline` / `--distill-profile off` only. The Lupine enhancement under test in these campaigns is *post-hoc* per-class median de-bias applied locally to raw predictions; the runner's Distill runtime variants are out of scope for this packet.

## 1. Why promote — the six-model basis

Every local dispersion claim in the three panels below carries the standing **N_eff < 4 caveat**: the local lane runs 4 model ids (`chgnet`, `mace-mp-small`, `mace-mp-medium`, `mace-mpa-0-medium`), of which `mace-mp-small` and `mace-mp-medium` share both architecture and training data (2 of 4 are the same MACE family member twice; `mace-mpa-0-medium` shares the architecture on different training data). Cross-model dispersion is therefore partly ensemble spread, not independent-error spread.

Promotion through the three cloud-only backends lifts the headline dispersion basis to **six model ids across five independent architectures**:

| # | model id | architecture family | lane |
|---|---|---|---|
| 1 | `chgnet` | CHGNet | local (done) |
| 2 | `mace-mp-medium` | MACE (MP training) | local (done) |
| 3 | `mace-mpa-0-medium` | MACE (MPA-0 training) | local (done) |
| 4 | `sevennet` (7net-0) | SevenNet | **cloud — this packet** |
| 5 | `orb-v3` | ORB | **cloud — this packet** |
| 6 | `uma-s-1p1` | UMA (FairChem) | **cloud — this packet** |

`mace-mp-small` remains local ensemble color (redundant with `mace-mp-medium` for independence counting). `m3gnet` (`mlip-cell-m3gnet`) exists in the cloud lane and is a legitimate 7th model if a run needs one more family; it is not in scope here.

Local evidence motivating the fan-out (all N_eff < 4):

- **Round-1 candidate statics** (`data/candidates/round1/report.json`, 2026-07-13): 9 candidates × 4 local models, a0/B0/Cij vs pre-registered references (`docs/plans/2026-07-13-unbiased-accuracy-campaign.md`).
- **Migration-barrier panel** (`data/kinetics/barrier_panel/report.json`): forward-barrier relative dispersion 0.21 (NaCl) to 0.58 (LiI) across 4 local models.
- **Perovskite B-site vacancy panel** (`data/candidates/perovskite_vacancy_panel/report.json`): E_vac relative dispersion 0.48 (CsSnBr3) to 4.41 (CsGeI3 — sign disagreement between chgnet and MACE family).
- **Schottky panel** (`data/defects/schottky_panel/panel_summary.json`): pair-energy relative dispersion 0.21–0.86 plus one sign flip (LiI: chgnet −0.08 eV vs MACE +0.31…+0.5 eV).

The question each promoted scope answers: **does the dispersion (and the de-bias treatment effect) survive when the model set becomes architecturally independent?**

## 2. Cell-runner capability audit (read 2026-07-13)

`gcp/mlip-cell-runner/mlip_cell_runner.py` delegates all science to `lupine_distill.fixture_contract.run_row`; the supported row set is exactly (`fixture_contract.ROW_IDS`):

```
elastic_constants | energy_volume | forces | stress | relaxation_stability
```

The manifest contract (`lupine.mlip.fixture_manifest.v2`) fails closed: every row's cases must carry row-native **reference values** (`reference_keys` per `ROW_DEFAULTS`) and `reference_provenance`, or `run-cell` raises before any GPU work.

| capability needed by this packet | supported today? | evidence |
|---|---|---|
| Cij via strain cases vs literature `elastic_constants_gpa` | **yes** (`elastic_constants` row) | `ROW_DEFAULTS`, `evaluate_row` |
| relaxation stability of perturbed starts | **yes** (`relaxation_stability` row) | `relaxation_prediction` |
| a0/B0 via relax→EOS→BM3 vs *property-level* literature refs | **no** — `energy_volume` scores per-point energy MAE vs reference energies, which do not exist for the campaign candidates | GAP-1 (§3.2) |
| CI-NEB migration barrier | **no** — zero NEB/migration/barrier code paths in the runner or fixture contract | GAP-2 (§4) |
| vacancy / Schottky formation energies | **no** — no defect row; `lupine_distill.statics.defects` is local-only | GAP-3 (§5) |
| reference-free (descriptive) rows | **no** — validator requires reference keys per case | part of GAP-2/GAP-3 |
| per-model relaxed a0 as defect/NEB input | **n/a cloud-side** — local panels reuse a0 from local reports; sevennet/orb/uma have **no relaxed a0 anywhere yet** | sequencing note (§6) |
| warm-model fan-out | **yes** — `run-batch --batch-spec-url` (one Cloud Run execution per backend, cells share the loaded model; `depends_on_cell_id` supported) | `run_batch` |

A cell = one `(row_id, mlip_id, variant_id)` over **all** of that row's cases in the manifest. Checkpoints (`cell_checkpoint.json`, `--checkpoint-mode read-write`, default) make timeouts resumable per case.

## 3. Scope P1 — Round-1 candidate bulk statics × {sevennet, orb-v3, uma-s-1p1}

**Gate status: `promote_to_gcp_canary` for the works-today subset (Cij + relaxation legs); `hold_local` blockers on the a0/B0 legs (GAP-1).**

### 3.1 Works today (after one manifest build)

Targets: the 9 frozen candidates in `data/candidates/round1_targets.json` (4 HEA fcc-RSS + 5 halide perovskites).

- `elastic_constants` row — the 6 candidates with non-null Cij references (`hea-cocrni`, `hp-cssncl3`, `hp-cssnbr3`, `hp-cssni3`†, `hp-csgei3`, `hp-cspbi3-control`), ≥6 `strain_voigt` cases each (±0.5 % strains, `DEFAULT_STRAIN_DELTA`), literature `elastic_constants_gpa` as reference. † CsSnI3 Cij stays excluded from headline criteria per the prereg.
- `relaxation_stability` row — all 9 candidates, perturbed starts + `relaxation_force_threshold` references.

**Protocol deviation, declared:** the `elastic_constants` row strains a *fixed* builder-supplied lattice (reference/guess a0), not each model's own relaxed cell as `run_candidate_campaign.py` does (relaxed-ion Cij on the model-relaxed cell). Good for wiring + coarse Cij dispersion; **not claim-grade** for the prereg's Cij leg. Claim-grade needs GAP-1's `candidate_statics` row.

**Prerequisite (local, new tool — do NOT modify the locked campaign scripts):** a builder, e.g. `tools/build_candidate_manifest.py`, that emits a `lupine.mlip.fixture_manifest.v2` manifest with:
- HEA RSS structures built via `lupine_distill.statics.build_rss_supercell`, 3×3×3 conventional fcc (108 atoms), **RNG seed 20260713** (identical configuration to local Round 1);
- perovskite 5-atom cubic cells via `build_structure` at `lattice_guess_angstrom`;
- `reference_provenance` copied verbatim from `round1_targets.json` (source + kind + caveat per value);
- push: `gcloud storage cp manifest.json gs://shed-489901-atlas-inputs/mlip-campaigns/round1-candidates-v1/manifest.json`

### 3.2 GAP-1 — a0/B0 legs need a `candidate_statics` runner extension

The campaign's primary observables (relaxed a0, BM3 B0) are *derived properties scored against property-level literature references*. The runner has no such row, and `energy_volume` cannot be populated honestly (no per-point DFT energies exist for these candidates; inventing placeholder references would violate the freeze). Required extension — exact CLI contract, mirroring `run_candidate_campaign.py` steps 1–3:

```
mlip_cell_runner.py run-cell --row-id candidate_statics ...   # all standard flags unchanged
```

- new row id `candidate_statics` in `fixture_contract.ROW_IDS` + `ROW_DEFAULTS`:
  `{"min_cases": 1, "error_unit": "relative_error_median", "reference_keys": ("candidate_references",), "reference_optional_fields": true}`
- case shape (one case per candidate):
  ```json
  {
    "structure_id": "hea-cocrni", "row_id": "candidate_statics",
    "formula": "CoCrNi", "structure_type": "fcc-rss",
    "composition": {"Co": 1, "Cr": 1, "Ni": 1},
    "lattice_guess_angstrom": 3.56,
    "rss": {"supercell": 3, "seed": 20260713},
    "reference": {"candidate_references": {"a0": 3.56, "b0": 189.0, "c11": 249.0, "c12": 159.0, "c44": 138.0},
                   "kinds": {"a0": "exp", "...": "..."}}
  }
  ```
  (nulls allowed and excluded from scoring — never backfilled, per the freeze declaration)
- row spec: `{"ev_volume_span": 0.06, "ev_n_points": 11, "ev_max_recenter": 8, "strain_delta": 0.005, "elastic_fmax": DEFAULT_ELASTIC_FMAX, "elastic_max_steps": DEFAULT_ELASTIC_MAX_STEPS}`
- computation: cubic cell-based E-V scan + recentring + BM3 fit on the supplied Atoms (the `statics.ev_relax` mirror in `run_candidate_campaign.py`), then symmetric FD stress-strain Cij on the relaxed cell (relaxed-ion);
- prediction fields per case: `a0_angstrom`, `b0_gpa`, `e_per_atom_ev`, `c11_gpa`, `c12_gpa`, `c44_gpa`, `born_stable`, `n_ev_points`, `bm3_residual`, wall time;
- score: median |relative error| over the non-null references; per-property errors in `metrics`.

De-bias/gates remain **local post-processing** on the artifact predictions (per the prereg arms) — the runner stays generic.

### 3.3 Canary (one cell first)

Run id `mlip-cloud-20260713-cand-r1`. Canary = cheapest scoreable cell on the healthiest backend: `sevennet × elastic_constants × baseline`.

```powershell
gcloud run jobs execute mlip-cell-sevennet --project=shed-489901 --region=us-central1 --wait '--args=^|^run-cell|--run-id=mlip-cloud-20260713-cand-r1|--campaign-id=mlip-cloud-20260713-cand-r1|--cell-id=mlip-cloud-20260713-cand-r1:baseline:elastic_constants:sevennet|--row-id=elastic_constants|--mlip-id=sevennet|--variant-id=baseline|--distill-profile=off|--manifest-url=gs://shed-489901-atlas-inputs/mlip-campaigns/round1-candidates-v1/manifest.json|--artifact-prefix=gs://shed-489901-atlas-outputs/mlip-campaigns/mlip-cloud-20260713-cand-r1/baseline/elastic_constants/sevennet|--beat-emit-url=https://glim-think-v1.aw-ab5.workers.dev/feed/beats|--checkpoint-mode=read-write'
```

(Format is exactly `gcloud_args_for_cell` + `shell_join` from `tools/mlip_local_promotion.py`: `^|^`-delimited packed `--flag=value` args; cell id `run:variant:row:mlip`; artifact prefix `<root>/<run>/<variant>/<row>/<safe_id(mlip)>`.)

### 3.4 Fan-out (after canary acceptance) — 6 cells total

| job | cell id (`mlip-cloud-20260713-cand-r1:baseline:<row>:<mlip>`) | row | note |
|---|---|---|---|
| `mlip-cell-sevennet` | `...:elastic_constants:sevennet` | elastic_constants | = canary |
| `mlip-cell-sevennet` | `...:relaxation_stability:sevennet` | relaxation_stability | |
| `mlip-cell-orb` | `...:elastic_constants:orb-v3` | elastic_constants | |
| `mlip-cell-orb` | `...:relaxation_stability:orb-v3` | relaxation_stability | |
| `mlip-cell-uma` | `...:elastic_constants:uma-s-1p1` | elastic_constants | ⚠ UMA precondition below |
| `mlip-cell-uma` | `...:relaxation_stability:uma-s-1p1` | relaxation_stability | ⚠ |

Each non-canary cell command is the canary command with the job name, `--cell-id`, `--row-id`, `--mlip-id`, and the artifact-prefix `<variant>/<row>/<mlip>` tail substituted. Preferred fan-out form (amortizes cold start + model load): one `run-batch` per backend, batch spec pushed next to the manifest —

```powershell
gcloud run jobs execute mlip-cell-sevennet --project=shed-489901 --region=us-central1 --wait '--args=^|^run-batch|--batch-spec-url=gs://shed-489901-atlas-inputs/mlip-campaigns/round1-candidates-v1/batch-sevennet.json|--beat-emit-url=https://glim-think-v1.aw-ab5.workers.dev/feed/beats'
```

with `batch-sevennet.json` = `{"run_id": "mlip-cloud-20260713-cand-r1", "campaign_id": "mlip-cloud-20260713-cand-r1", "mlip_id": "sevennet", "defaults": {"manifest_url": "...", "variant_id": "baseline", "checkpoint_mode": "read-write"}, "batch_artifact_prefix": "gs://shed-489901-atlas-outputs/mlip-campaigns/mlip-cloud-20260713-cand-r1/batch/sevennet", "cells": [both cells with their cell_id/row_id/artifact_prefix]}` (same for `orb-v3`, `uma-s-1p1`).

**⚠ UMA precondition:** `facebook/UMA` returned gated-repo 403 until the HF account is authorized (backend catalog note; `HF_TOKEN` is already mounted via Secret Manager). Run the UMA canary only after access is confirmed; a 403 produces a failure beat, not silence.

### 3.5 Expected artifacts

```
gs://shed-489901-atlas-outputs/mlip-campaigns/mlip-cloud-20260713-cand-r1/baseline/<row>/<mlip>/cell_result.json
gs://shed-489901-atlas-outputs/mlip-campaigns/mlip-cloud-20260713-cand-r1/baseline/<row>/<mlip>/cell_checkpoint.json
```
`cell_result.json` = `lupine.mlip.cell_artifact.v1` with `fixture_contract`, `row_metrics`, per-case `predictions` (the raw stresses/energies the local de-bias arm consumes), `versions`, `execution` (image digest, CUDA facts, cold/warm timings).

### 3.6 Cost estimate (L4 @ ~$0.65/h, the repo's standing rate from `tools/mlip_sim_matrix.py`)

| cell class | content | est. GPU-min/cell | est. $/cell |
|---|---|---|---|
| elastic_constants | 1×108-atom HEA (6+ strains, relaxed-ion) + 5×5-atom perovskites | 15–40 | $0.16–0.43 |
| relaxation_stability | 4×108-atom + 5×5-atom relaxations | 10–30 | $0.11–0.33 |
| cold start (per execution) | image pull + model load | 1–3 | $0.01–0.03 |

**P1 total: 6 cells ≈ 1.5–3.5 GPU-h ≈ $1–2.30.** (With the future `candidate_statics` row: +3 cells, ≈ +$1–2.)

### 3.7 Acceptance check (what lands in D1/GCS)

1. `gcloud run jobs execute ... --wait` exits 0.
2. Artifact exists: `gcloud storage ls gs://shed-489901-atlas-outputs/mlip-campaigns/mlip-cloud-20260713-cand-r1/baseline/elastic_constants/sevennet/cell_result.json`
3. D1 row (from `glim-think/`):
   `npx wrangler d1 execute glim-ledger --remote --json --command "SELECT cell_id, status, accuracy_score, accuracy_unit, artifact_uri FROM mlip_baseline_cells WHERE run_id='mlip-cloud-20260713-cand-r1'"` — every fan-out cell `status='completed'`, non-null `accuracy_score` (`gpa_mae`-derived for elastic, `relaxation_penalty` for relax), `artifact_uri` pointing at §3.5; zero `failed` rows; corresponding `lab_beats` ticker entries exist.
4. Artifact sanity: `manifest_hash` identical across all 6 cells (sealed inputs); `execution.cloud_run_job` = expected job name.
5. Local merge (new analyzer, not the locked scripts): recompute per-candidate per-property dispersion on the six-model basis {chgnet, mace-mp-medium, mace-mpa-0-medium, sevennet, orb-v3, uma-s-1p1} and re-run the prereg §4 metrics with the cloud models as additional raw arms. Fixed-lattice Cij cells are labeled `protocol=fixed_lattice` and kept out of headline claims until `candidate_statics` lands.

## 4. Scope P2 — Migration-barrier panel (5 compounds) × {sevennet, orb-v3, uma-s-1p1}

**Gate status: `hold_local` — requires cell-runner NEB extension (GAP-2).** No NEB/CI-NEB/migration code exists in `mlip_cell_runner.py` or `fixture_contract.py` (verified by search: zero hits for neb/migration/barrier).

### 4.1 Required extension — exact CLI contract (mirrors `python/scripts/run_barrier_panel.py`)

```
mlip_cell_runner.py run-cell --row-id migration_barrier ...   # standard flags unchanged
```

- new row id `migration_barrier`; row spec defaults:
  `{"n_images": 5, "supercell": 2, "fmax": 0.05, "max_steps": 300, "climb": true, "neb_method": "improvedtangent", "interpolation": "idpp_linear_fallback", "optimizer": "FIRE", "min_cases": 1, "error_unit": "ev_mae", "reference_keys": ("barrier_ev",), "reference_optional": true}`
  — `reference_optional` is new validator behavior: a case without `barrier_ev` runs descriptively (score null, no fail-closed), because kinetics references are charged-hop enthalpies compared only with caveats (see `data/candidates/kinetics_targets.json` `convention_caveat`).
- case shape (one per compound):
  ```json
  {
    "structure_id": "LiF_rocksalt_cation_vacancy_hop", "row_id": "migration_barrier",
    "formula": "LiF", "structure_type": "rocksalt",
    "mechanism": "cation_vacancy_nn_110",
    "a0_angstrom": 4.063, "a0_provenance": "halide panel subjects[LiF_rocksalt].per_model[<mlip>].properties.a0 | covalent-radius estimate",
    "reference": {"barrier_ev": 0.66, "kind": "exp", "source": "Stoebe & Huggins 1966 (charged-hop caveat)"}
  }
  ```
- runner obligations: `lupine_distill.statics.build_cation_vacancy_hop` (deterministic first-cation vacancy, nearest <110> hop) → relax both endpoints → `compute_migration_barrier` (IDPP interpolation, two-stage climbing-image NEB, improved tangent, FIRE);
- prediction fields per case (exactly the local panel's cell payload): `forward_barrier_ev`, `backward_barrier_ev`, `barrier_asymmetry_ev`, `e_initial_ev`, `e_final_ev`, `e_saddle_ev`, `saddle_image_index`, `band_energies_ev`, `hop_distance_angstrom`, `a0_angstrom` + `a0_provenance`, `n_relax_steps_*`, `n_neb_steps`, `n_pre_climb_steps`, `n_force_calls`, `wall_time_seconds`;
- score: MAE of `forward_barrier_ev` vs `barrier_ev` over referenced cases; asymmetry surfaced in `metrics` as a convergence check.
- checkpoint scope: per-case raw predictions as today (a NEB case is atomic; endpoint-relax checkpointing is optional future work).

### 4.2 Post-extension commands (ready to paste once the row ships)

Run id `mlip-cloud-20260713-barrier`; manifest `gs://shed-489901-atlas-inputs/mlip-campaigns/barrier-panel-v1/manifest.json` (builder: same new tool as §3.1, kinetics targets from `data/candidates/kinetics_targets.json` `targets` block). Canary:

```powershell
gcloud run jobs execute mlip-cell-sevennet --project=shed-489901 --region=us-central1 --wait '--args=^|^run-cell|--run-id=mlip-cloud-20260713-barrier|--campaign-id=mlip-cloud-20260713-barrier|--cell-id=mlip-cloud-20260713-barrier:baseline:migration_barrier:sevennet|--row-id=migration_barrier|--mlip-id=sevennet|--variant-id=baseline|--distill-profile=off|--manifest-url=gs://shed-489901-atlas-inputs/mlip-campaigns/barrier-panel-v1/manifest.json|--artifact-prefix=gs://shed-489901-atlas-outputs/mlip-campaigns/mlip-cloud-20260713-barrier/baseline/migration_barrier/sevennet|--beat-emit-url=https://glim-think-v1.aw-ab5.workers.dev/feed/beats|--checkpoint-mode=read-write'
```

Fan-out: same command for `mlip-cell-orb` (`orb-v3`) and `mlip-cell-uma` (`uma-s-1p1`) — 3 cells total, each covering LiF/LiCl/LiBr/LiI/NaCl (5 CI-NEB cases).

- **Cost:** 64-atom supercell, 2 endpoint relaxations + ≤300-step CI-NEB × 5 compounds ≈ 40–90 GPU-min/cell → **3 cells ≈ 2–4.5 GPU-h ≈ $1.30–3.**
- **Artifacts:** `gs://shed-489901-atlas-outputs/mlip-campaigns/mlip-cloud-20260713-barrier/baseline/migration_barrier/<mlip>/cell_result.json`.
- **Acceptance:** same D1/GCS checks as §3.7 with `run_id='mlip-cloud-20260713-barrier'`; plus per-case `barrier_asymmetry_ev` < ~0.02 eV (symmetric hop convergence check) and 5/5 cases present per cell; local merge recomputes forward-barrier dispersion on the six-model basis vs the local values (LiF 0.32 → ?, LiI 0.58 → ?).

## 5. Scope P3 — Perovskite B-site vacancy + Schottky panels × {sevennet, orb-v3, uma-s-1p1}

**Gate status: `hold_local` — requires defect-formation runner extension (GAP-3).** Highest scientific priority after statics: the local panels show the largest dispersions (CsGeI3 E_vac 4.41 with a chgnet sign flip; LiI Schottky sign flip), which is exactly where the MACE-family caveat bites hardest.

### 5.1 Required extension — exact CLI contract (mirrors `run_perovskite_vacancy_panel.py` / `run_schottky_panel.py`)

Two new rows, both `reference_optional` (descriptive dispersion; no flag/refuse thresholds exist for defect energetics yet — deriving them is Round-3 calibration work):

- `vacancy_formation` — case: `{"formula": "CsSnI3", "structure_type": "perovskite", "vacancy_site": "B", "vacancy_species": "Sn", "supercell": [2,2,2], "chemical_potential_reference": "metal_rich", "reference_structure_override": "diamond", "a0_angstrom": <model a0>, "a0_provenance": "..."}`; runner calls `statics.compute_referenced_vacancy_formation` (E_vac = E_defect + mu − E_bulk, neutral cell, fixed-cell position relax; alpha-Sn diamond / diamond-Ge / fcc-Pb chemical potentials under the SAME calculator); prediction fields: `e_vac_ev`, `mu_ev`, `e_bulk_ev`, `e_defect_ev`, `n_atoms`, relax steps, wall time. Row spec carries the local panel's wall-time guard (`cell_budget_seconds: 240` per case, drop-order scope reduction recorded, not silent).
- `schottky_formation` — case: `{"formula": "LiF", "structure_type": "rocksalt", "supercell": [2,2,2], "a0_angstrom": ..., "a0_provenance": "..."}`; runner calls `statics.compute_schottky_formation` (charge-balanced pair, one formula unit removed, maximally separated under PBC, fixed-cell relax; E_pair = E_defect − (N−2)/N · E_bulk — no chemical potentials); prediction fields per `SchottkyFormationResult`. The `kinetics_targets.json` `schottky_formation_enthalpy` values are **context-only** (`kind: other`) and must not become scoring references.

### 5.2 Post-extension commands

Run id `mlip-cloud-20260713-defect`; manifest `gs://shed-489901-atlas-inputs/mlip-campaigns/defect-panels-v1/manifest.json` (vacancy cases: the 5 round-1 perovskites incl. CsPbI3 control; Schottky cases: LiF/LiCl/LiBr/LiI/NaCl/MgO). Canary = `sevennet × schottky_formation` (cheapest, most cases):

```powershell
gcloud run jobs execute mlip-cell-sevennet --project=shed-489901 --region=us-central1 --wait '--args=^|^run-cell|--run-id=mlip-cloud-20260713-defect|--campaign-id=mlip-cloud-20260713-defect|--cell-id=mlip-cloud-20260713-defect:baseline:schottky_formation:sevennet|--row-id=schottky_formation|--mlip-id=sevennet|--variant-id=baseline|--distill-profile=off|--manifest-url=gs://shed-489901-atlas-inputs/mlip-campaigns/defect-panels-v1/manifest.json|--artifact-prefix=gs://shed-489901-atlas-outputs/mlip-campaigns/mlip-cloud-20260713-defect/baseline/schottky_formation/sevennet|--beat-emit-url=https://glim-think-v1.aw-ab5.workers.dev/feed/beats|--checkpoint-mode=read-write'
```

Fan-out: 6 cells = {`vacancy_formation`, `schottky_formation`} × {`mlip-cell-sevennet`/`sevennet`, `mlip-cell-orb`/`orb-v3`, `mlip-cell-uma`/`uma-s-1p1`} (substitute row/job/mlip triple in the canary command, or one `run-batch` spec per backend as in §3.4).

- **Cost:** vacancy cell = 5 × (39-atom defect relax + 40-atom bulk + elemental mu) ≈ 15–40 GPU-min; Schottky cell = 6 × 64-atom pair relax ≈ 20–50 GPU-min → **6 cells ≈ 2–4.5 GPU-h ≈ $1.30–3.**
- **Artifacts:** `gs://shed-489901-atlas-outputs/mlip-campaigns/mlip-cloud-20260713-defect/baseline/<row>/<mlip>/cell_result.json`.
- **Acceptance:** §3.7 checks with `run_id='mlip-cloud-20260713-defect'`; per-cell case counts 5 (vacancy) / 6 (schottky); any wall-time-guard scope reduction must appear explicitly in `metrics.scope_reductions`; local merge recomputes E_vac / E_pair dispersion on the six-model basis and re-tests H3 (defect observables disperse more than bulk observables) with independent architectures.

## 6. Sequencing — the a0 dependency (applies to P2 and P3)

The local defect/NEB panels deliberately sit each cell on **that model's own relaxed a0** (from the halide-panel / round-1 reports). `sevennet`, `orb-v3`, and `uma-s-1p1` have never relaxed these lattices, so:

1. **Stage 0 (inside P1 or a small precursor manifest):** rocksalt (LiF/LiCl/LiBr/LiI/NaCl/MgO) + perovskite relaxations for the 3 cloud backends — either via the `candidate_statics` extension or a dedicated relaxation manifest; extract per-(compound, model) a0 from artifacts.
2. **Stage 1:** regenerate the P2/P3 manifests with per-model `a0_angstrom` + `a0_provenance` (the manifest builder takes a `--a0-report` input exactly as `run_barrier_panel.resolve_a0` does), falling back to `estimate_lattice_constant` with recorded provenance when a cell is missing.
3. **Stage 2:** P2/P3 canaries, then fan-out.

Running defect/NEB cells on estimate-a0 lattices is permitted for wiring canaries only; claim-grade dispersion requires stage 0/1.

## 7. Program totals and gate summary

| scope | status | blocker | cells | est. cost |
|---|---|---|---|---|
| P1 statics (Cij + relax legs) | **promote_to_gcp_canary** | manifest build + push (local) | 6 | $1–2.30 |
| P1 statics (a0/B0 legs) | hold_local | GAP-1 `candidate_statics` row | +3 | +$1–2 |
| P2 barriers | hold_local | GAP-2 NEB row (`migration_barrier`) | 3 | $1.30–3 |
| P3 defects | hold_local | GAP-3 defect rows (`vacancy_formation`, `schottky_formation`) + reference-optional validator | 6 | $1.30–3 |
| **whole program** | | | **18** | **≈ $5–10** |

Next actions: (1) build+push `round1-candidates-v1` manifest; (2) run the §3.3 canary, verify §3.7, fan out §3.4 (UMA last, after gated-repo access); (3) ship GAP-1/2/3 runner extensions behind the fail-closed fixture contract (new rows must not weaken validation for the existing five rows; `reference_optional` is per-row-spec opt-in); (4) stage-0 a0 relaxations for the cloud backends; (5) P2/P3 canaries + fan-out; (6) local six-model dispersion re-analysis and, if the dispersion structure holds, Round-3 threshold calibration for kinetics/defect properties.

## 8. Provenance (files read for this packet, 2026-07-13)

`tools/mlip_local_promotion.py` (packet/command contract) · `tools/mlip_sim_matrix.py` (cost model, $0.65/h L4) · `gcp/mlip-cell-runner/README.md`, `mlip_cell_runner.py`, `backend_catalog.json` (runner contract, jobs, UMA gating) · `python/lupine_distill/fixture_contract.py` (ROW_IDS, fail-closed validation) · `python/scripts/run_barrier_panel.py`, `run_perovskite_vacancy_panel.py`, `run_schottky_panel.py` (contracts mirrored; read-only — these and the locked campaign scripts were not modified) · `data/candidates/round1_targets.json`, `kinetics_targets.json`, `round1/report.json`, `perovskite_vacancy_panel/report.json` · `data/kinetics/barrier_panel/report.json` · `data/defects/schottky_panel/panel_summary.json` · `docs/plans/2026-07-13-unbiased-accuracy-campaign.md` (prereg; cloud promotion of deferred classes is contemplated there) · `glim-think/src/feed/beats.ts`, `src/research/mlipBaselineGrid.ts` (D1 acceptance surface).
