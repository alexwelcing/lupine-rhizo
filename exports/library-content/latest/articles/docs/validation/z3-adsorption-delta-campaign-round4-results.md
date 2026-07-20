# Z3 Δ-Learned Adsorption Accuracy — Round-4 Campaign Results

**Status:** completed campaign · verdict **refuted** (as preregistered)
**Campaign:** `discovery.round-4.z3-adsorption.v1` · executed 2026-07-19 (run `z3-20260719`)
**Gate:** corrected adsorption-energy MAE ≤ 0.1 eV against published DFT references on a 20-candidate holdout
**Verdict:** all four available models FAIL — corrected holdout MAE 2.27–5.91 eV; every validation-selected correction made the holdout *worse* than the raw baseline

## Preregistered question

Can a Δ-learned hybrid stack — a foundation MLIP plus a small correction model fitted on six chemistry-family training systems and selected on six validation systems — reach the ≤ 0.1 eV adsorption-energy accuracy catalyst screening requires, on 20 held-out adsorbate–surface pairs it never saw during fitting, selection, or tuning?

## Panel and protocol

- **Reference panel:** `data/candidates/z3_catbench_bm_adsorption.lock.json` (SHA-256 `b434de00…`) — 32 rows from the CatBench BM_dataset adsorption benchmark (Zenodo DOI [10.5281/zenodo.17157086](https://doi.org/10.5281/zenodo.17157086), CC BY 4.0), structures and energies from the GAME-Net study (DOI [10.1038/s43588-023-00437-y](https://doi.org/10.1038/s43588-023-00437-y); VASP 5.4.4 PBE+D2, 450 eV cutoff, PAW, 1e-5 eV SCF, 0.03 eV/Å forces). fcc(111) facets for Ag/Au/Cu/Ni/Pt, hcp(0001) for Ru. Three application families: biomass, plastics, polyurethanes.
- **Basis honesty:** references are published **DFT**, not experiment; nothing here is error-against-experiment. Per-row `uncertainty_ev` is a labeled 3×SCF-threshold proxy, not a statistical interval.
- **Frozen split:** deterministic, family-stratified by SHA-256 ordering — 6 `delta_train` / 6 `delta_validation` / 20 `confirmatory_test` (`z3_catbench_bm_delta_splits.lock.json`). Fit exclusion enforced in code: fit reads train only, selection reads validation only, scoring reads test only.
- **Execution:** 4 models × 32 candidates = 128 single-candidate Cloud Run cells (isolated jobs, defect-fixed images `z3-adsorption-fixed-20260719`, service account `atlas-distill-runner`). **128/128 completed, zero failures**, each artifact captured and identity-validated (model, row, candidate, finite energy) by `gcp/z3-campaign/run_measurement.py`.

## Baseline result: systematic underbinding, panel-wide

Signed error = model − reference (positive = underbound). Holdout = the 20 confirmatory candidates.

| Model | Full-panel MAE | Full-panel bias | Holdout MAE |
|---|---|---|---|
| chgnet | 1.67 eV | +1.13 eV | **0.69 eV** |
| mace-mp-medium | 3.43 eV | +3.42 eV | 2.11 eV |
| mace-mp-small | 4.29 eV | +4.28 eV | 3.24 eV |
| mace-mpa-0-medium | 5.31 eV | +5.29 eV | 4.27 eV |

Errors are not symmetric scatter: the MACE family underbinds essentially every system, with per-candidate errors from −1.1 eV to **+25.6 eV**, growing with adsorbate size and varying by family (plastics largest, polyurethanes smallest). The physical reading is dispersion blindness: the references stabilize large adsorbates partly through D2 dispersion, physics the foundation models' bulk-crystal training distribution does not contain. First datapoint anatomy (mace-mp-small × biomass_ni_mol1): gas molecule +1.39 eV, clean Ni(111) slab −12.45 eV, complex −1.24 eV — the slab/complex terms nearly cancel and the residual **+9.8 eV sits entirely in the interface bond**.

## Δ-correction: fitted, selected, scored — and refuted

A fixed correction menu was fitted per model on `delta_train` only and selected on `delta_validation` only (`tools/build_z3_delta_correction.py`; report `data/candidates/z3/delta-correction-report.json` + `.sha256`):

| Model | Selected form (by validation MAE) | Validation MAE | Baseline holdout MAE | **Corrected holdout MAE** | Gate |
|---|---|---|---|---|---|
| chgnet | C: family size-linear | 1.12 eV | 0.69 eV | **2.27 eV** | ✗ |
| mace-mp-medium | A: global constant | 3.26 eV | 2.11 eV | **5.01 eV** | ✗ |
| mace-mp-small | A: global constant | 3.98 eV | 3.24 eV | **5.00 eV** | ✗ |
| mace-mpa-0-medium | B: family constant | 4.03 eV | 4.27 eV | **5.91 eV** | ✗ |

**Every corrected holdout is worse than its own raw baseline.** A global shift overshoots the small-error families into large negative errors; family/size-linear fits trained on two giant plastics systems extrapolate badly across the size distribution. The conclusion is structural, not anecdotal: the baseline error is *not a uniform bias* — it is a structured, family- and size-dependent field spanning −1 to +26 eV — and a six-point fit budget cannot estimate a generalizable correction over it. The Z3 Δ-learning hypothesis **as preregistered** is refuted on the holdout it froze.

## What stands after refutation

- **chgnet raw** (0.69 eV holdout MAE) is the best bare foundation-model number on this panel — still 6.9× the screening gate. No current available uMLIP is catalyst-screening accurate on biomass/plastics-scale adsorbates.
- The underbinding law is now measured on **three independent observables** in this program: Z1 migration barriers (3.4–6× under-predicted), Z3 adsorption interfaces (up to +26 eV underbound), Round-4 elastic correction (confirmatory fail). One systematic direction — underbinding at transition states and at interfaces — across three preregistered campaigns.
- A viable corrected future run needs a materially larger fit budget (more than six train systems) or physics features (contact-atom counts, dispersion proxies) — a new preregistration, not a retune of this one.

## Receipts

- Manifest: `campaigns/v1/z3.campaign-manifest.v1.json` (content hash `sha256:49f5f20e…`); claim `registry/claims/discovery.z3.adsorption-accuracy.v1.json` (unsupported; baseline bundle PR #39).
- Panel/splits/fixtures: `data/candidates/z3_catbench_bm_*` (all `.sha256` sidecars); 32 candidate fixtures `gs://shed-489901-atlas-inputs/z3-campaign/catbench-bm-v1/`.
- Raw artifacts: `gs://shed-489901-atlas-outputs/z3-campaign/raw/z3-20260719/<model>/<candidate>/adsorption_energy/cell_result.json`.
- Analysis: `tools/build_z3_delta_correction.py`; report `data/candidates/z3/delta-correction-report.json` (SHA-256 sidecar); 7 tests covering form recovery, fallback guards, no-leakage, fail-closed hashing, gate arithmetic.
- Runner defects found and fixed before execution (PR #28): failed-checkpoint reuse; raw-energy loss on contribution overflow.
