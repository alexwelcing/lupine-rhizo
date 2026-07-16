# 3-family vs multi-architecture dispersion — Round-1 candidate Cij (cloud P1 merge)

- **Run:** `mlip-cloud-20260713-cand-r1` (packet `docs/promotion/2026-07-13-six-model-promotion-packet.md`, scope P1)
- **Generated:** 2026-07-13 by `compute_five_arch_dispersions.py`; data: `five_arch_dispersions.json`
- **Metric:** relative dispersion `(max − min) / |median|` (`lupine_distill.statics.gates.relative_dispersion`)
- **Bases:**
  - `local3` = {chgnet, mace-mp-medium, mace-mpa-0-medium} — 3 model ids, **2** independent architectures (CHGNet, MACE)
  - `merged` = local3 + {sevennet, orb-v3} — 5 model ids, **4** independent architectures (CHGNet, MACE, SevenNet, ORB)
- **⚠ UMA blocked:** `uma-s-1p1` failed pre-GPU with HF gated-repo 403 (`facebook/UMA` — mounted `HF_TOKEN` account `AlexWelcing` not in the authorized list; verified live against the exact checkpoint URL twice on 2026-07-13). Failure beats recorded in D1; retry withheld as deterministic. The target 6-model / 5-architecture basis becomes available by re-running the two `mlip-cell-uma` batch cells once access is granted — no other rework needed.
- **⚠ Protocol deviation (declared, packet §3.1):** cloud Cij cells strain a **fixed builder-supplied lattice** (reference/guess a0); local values are relaxed-ion Cij on each **model's own relaxed cell**. Every row below carries this mismatch — coarse-dispersion/wiring grade, **not claim-grade** until the `candidate_statics` row (GAP-1) lands. Part of the HEA widening in particular may be protocol, not architecture.
- `hp-cssni3` Cij stays **headline-excluded** per the prereg.

## Dispersion per candidate × property

| material | prop | local3 (3 models / 2 arch) | merged (5 models / 4 arch) | ratio | note |
|---|---|---|---|---|---|
| hea-cocrni | c11 | 0.111 | 0.300 | **2.70** | widened by SevenNet/ORB softening (193–265 GPa span) |
| hea-cocrni | c12 | 0.133 | 0.403 | **3.03** | orb-v3 115 GPa vs chgnet/MACE-MP ~175 GPa |
| hea-cocrni | c44 | 0.373 | 0.374 | 1.00 | local basis already spanned extremes |
| hp-csgei3 | c11 | 0.373 | 0.373 | 1.00 | |
| hp-csgei3 | c12 | 1.466 | 2.362 | **1.61** | chgnet 18.8 vs sevennet 3.3 GPa |
| hp-csgei3 | c44 | 0.625 | 0.562 | 0.90 | range unchanged; median denominator grew |
| hp-cspbi3-control | c11 | 0.467 | 0.598 | 1.28 | |
| hp-cspbi3-control | c12 | 0.465 | 0.498 | 1.07 | |
| hp-cspbi3-control | c44 | 1.552 | 1.636 | 1.05 | |
| hp-cssnbr3 | c11 | 0.475 | 0.645 | 1.36 | |
| hp-cssnbr3 | c12 | 1.545 | 1.287 | 0.83 | range unchanged; median denominator grew |
| hp-cssnbr3 | c44 | 1.465 | 1.465 | 1.00 | |
| hp-cssncl3 | c11 | 0.587 | 0.587 | 1.00 | |
| hp-cssncl3 | c12 | 0.232 | 0.417 | **1.80** | sevennet 12.5 GPa above local cluster 8.2–10.3 |
| hp-cssncl3 | c44 | 1.474 | 1.474 | 1.00 | |
| hp-cssni3 † | c11 | 0.756 | 0.867 | 1.15 | † headline-excluded |
| hp-cssni3 † | c12 | 0.341 | 0.372 | 1.09 | † |
| hp-cssni3 † | c44 | 1.206 | 1.206 | 1.00 | † |

Summary: 11/18 rows widen; median ratio 1.06; max ratio 3.03.

## The N_eff question — did family redundancy understate disagreement?

**Yes, selectively — worst exactly where the local grid looked most concordant.**

1. **HEA CoCrNi c11/c12 (ratio 2.7–3.0) is the headline N_eff hit.** The local basis (CHGNet + two MACE variants) agreed tightly on alloy stiffness (dispersion 0.11–0.13, the tightest cells in the local report), but that agreement was an artifact of a 2-architecture basis: SevenNet and ORB put c11 at 193–203 GPa vs the local 238–265 GPa cluster. Low local dispersion on the metallic candidate was family redundancy, not consensus. (Caveat: the fixed-lattice protocol plausibly inflates part of this specific gap — the HEA is the cell where relaxed-vs-guess a0 matters most.)
2. **Soft perovskite off-diagonals (c12) also widen** (CsGeI3 1.47→2.36, CsSnCl3 0.23→0.42): independent architectures disagree more on the weakest elastic responses, consistent with the local panels' pattern that soft/defect-adjacent observables disperse most.
3. **c44 rows barely move (ratio ≈ 1.00 in 5/6 materials).** Shear-constant disagreement was already fully visible inside the local basis (CHGNet vs the MACE family spans the merged extremes), so family redundancy did **not** understate c44 — the standing local c44 flags survive an architecture-independent basis unchanged.
4. The two ratios < 1 (CsGeI3 c44 0.90, CsSnBr3 c12 0.83) are **not** reduced disagreement: `max − min` never shrinks when models are added; the cloud values landed mid-range and moved the median denominator. Absolute spread is unchanged there.

## relaxation_stability (cloud-only; no local counterpart in `round1/report.json`)

| model | convergence rate | relaxation penalty | score |
|---|---|---|---|
| sevennet | 1.0 (9/9 candidates) | 0.0 | 1.0 |
| orb-v3 | 1.0 (9/9 candidates) | 0.0 | 1.0 |
| uma-s-1p1 | — blocked (HF 403) | — | — |

## Provenance

- Cloud artifacts: `gs://shed-489901-atlas-outputs/mlip-campaigns/mlip-cloud-20260713-cand-r1/baseline/<row>/<mlip>/cell_result.json`, mirrored under `baseline/` here; `manifest_hash` identical across all four artifacts (`sha256:ca9896a2…e2572f`, sealed inputs) and `execution.cloud_run_job` matches the packet's job map.
- Local raw values: `data/candidates/round1/report.json` `candidates.<id>.per_model.<model>.properties` (c11/c12/c44); `mace-mp-small` excluded from independence counting per the packet.
- Cloud (c11, c12, c44) extracted from the artifact's per-material 6×6 Voigt matrix by cubic symmetry-averaging (diagonal / off-diagonal / shear-diagonal means).
- D1 ledger rows: `mlip_baseline_cells` under `run_id='mlip-cloud-20260713-cand-r1'` (4 completed, 2 failed = UMA), ticker in `lab_beats`.
