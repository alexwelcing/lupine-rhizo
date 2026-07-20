# Z1 Barrier-Accurate MLIP Campaign — Round-4 Results (Two Precision Chains)

**Status:** completed campaign · verdict **refuted** — independently on two precision chains
**Campaign:** `discovery.round-4.z1-barriers.v1` · executed 2026-07-19 (float32 chain and float64 chain, same locked panel)
**Gate:** migration-barrier MAE ≤ 40 meV against published DFT-NEB references across 30 chemistry-held-out paths
**Verdict:** all four available models FAIL, 3.4–6× over threshold, with a systematic under-prediction bias — unchanged under float64

## Preregistered question

Can the declared available foundation MLIPs (chgnet 0.4.2; mace-torch 0.3.16 small / medium / mpa-0-medium) predict solid-state ion migration barriers accurately enough for battery-electrolyte screening — a mean absolute error of 40 meV or better against DFT-NEB references on 30 held-out chemical systems?

## Panel and protocol

- **Reference panel:** `data/candidates/z1_nebdft2k_barriers.lock.json` (SHA-256 `192fe54a…`) — 30 chemistry-held-out DFT-NEB paths, one deterministic path per official LiTraj nebDFT2k test chemistry (*npj Computational Materials*, 2025, DOI [10.1038/s41524-025-01571-z](https://doi.org/10.1038/s41524-025-01571-z); source revision and archive hash pinned; deterministic rebuild verified byte-for-byte). DFT-relaxed endpoints/saddles/full energy profiles, reference barriers 0.068–3.251 eV, frozen CI-NEB protocol (FIRE, climb, improved tangent, k = 5 eV/Å², fmax 0.1 eV/Å).
- **Basis honesty:** references are published DFT-NEB, not experiment. Barrier convention is max(image energy) − min(image energy) on both the reference and prediction sides; the panel builder validates the dataset's own barrier against the profile max−min within 0.5 meV.
- **Execution:** per model, one Cloud Run cell on an isolated Round-4 job (NVIDIA L4), CI-NEB per path, per-path predicted barriers/signed errors/failures recorded **without imputation**; manifest and panel SHA validation fail closed. Images `z1-barrier-20260719` (float32 chain) and `z1-barrier-f64r2-20260719` (float64 chain).

## Results: both precision chains

| Model | float32 MAE | float64 MAE | Paths (both chains) | Gate |
|---|---|---|---|---|
| mace-mpa-0-medium | 135.0 meV | 135.0 meV | 28/30 | ✗ |
| mace-mp-small | 152.0 meV | 151.9 meV | 26/30 | ✗ |
| mace-mp-medium | 174.7 meV | 174.7 meV | 29/30 | ✗ |
| chgnet | 242.5 meV | 242.5 meV | 28/30 | ✗ |

The first chain ran at float32 — against MACE vendor guidance for geometry optimization — a protocol defect found in post-execution review, fixed once (barrier row only; PR #32), and re-measured end-to-end at float64. **The verdict is precision-independent**: per-model MAEs are identical to within 0.1 meV. The miss is model error, not numerical artifact. Both chains stand as executed evidence with separate artifact prefixes (`z1/campaign/` and `z1/campaign-float64/`); checkpoint contexts bind calculator dtype (PR #36), so no float32 prediction can leak into a float64 record.

## The shape of the failure

- **Systematic under-prediction.** For mace-mp-small (float32 chain), all 26 completed paths have *negative* signed error (−13 to −467 meV): the models under-predict migration barriers — consistent with training distributions dominated by near-equilibrium structures and with this program's Z3 finding of underbound interfaces. One systematic direction, two observables.
- **Convergence failures are honest, not hidden.** 1–4 paths per model (the largest systems, 87–191 atoms) failed CI-NEB convergence under the frozen protocol and are recorded as failures — MAEs are computed on completed paths only, and `measurement_complete` is false everywhere because the protocol demands all 30.
- **Precision note.** The f64 signed-error distribution partially relaxes (17/26 negative, mean −23.7 meV for mace-mp-small) while the MAE is unmoved — per-path pairing analysis is registered follow-up.
- **Precedent replicated.** This confirms at 30-chemistry scale the Round-3 five-compound result (77.1 meV) whose claim was withdrawn: foundation MLIPs are not barrier-accurate, and the error is structural.

## Receipts

- Manifest: `campaigns/v1/z1.campaign-manifest.v1.json` (content hash `sha256:0a85044c…`, pins the panel lock); claim `registry/claims/discovery.z1.barrier-accuracy.v1.json` (unsupported pending ingestion; baseline bundle seeded).
- Panel + builder: `data/candidates/z1_nebdft2k_barriers.lock.json` (+ `.sha256`), `tools/build_z1_barrier_panel.py`.
- Raw artifacts: `gs://shed-489901-atlas-outputs/z1/campaign/<model>/` and `gs://shed-489901-atlas-outputs/z1/campaign-float64/<model>/` (`cell_result.json`, `cell_checkpoint.json`; execution metadata records `calculator_dtype`).
- Measurement rows: `data/candidates/z1/measurements.jsonl` (four RFC 8785 hash-chained aggregate fail rows, `tools/build_z1_measurement_rows.py`); float64 rows append through the same builder.
- Runner hardening from review (PRs #32, #36): float64 for barrier geometry optimization; non-finite energies fail the path; checkpoint dtype binding.
