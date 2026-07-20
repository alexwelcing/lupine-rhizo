# MLIP-Guided Sparse-DFT Barrier Pilot — Preregistration (2026-07-20)

**Status:** FROZEN before execution · **Owner:** Alex Welcing (director)
**Campaign id:** `discovery.round-5.z1-sparse-dft.v1`
**Theorems engaged:** `barrier_error_le_wobble` (+ tightness), `anchor_impossibility_bound`, `two_point_anchor_exact` (`OpenDistillationFactory/HonestErrors/CorrectionBoundary.lean`, PR #56)

## Premise (measured on the locked Z1 panel, 2026-07-20)

- Foundation MLIPs misprice barrier *levels* (MAE 135–243 meV, Round-4) — Theorem 2's wobble bound made concrete.
- The same models' energy *landscape geometry* is accurate: predicted saddle location exact on 82–86% of paths (24/28, 23/26, 23/28), within ±1 image on 89–93%.
- **Simulation of the sparse protocol on the reference profile:** evaluating DFT only at model-chosen extrema reproduces the reference barrier with MAE 1.2–9.4 meV (±1 window) and 0.0 meV (±2) across all 82 model-path pairs — at ~7 points/path instead of ~50–100 for full NEB.
- Caveat on record: panel paths are short (5–10 images); the sparse advantage grows with denser paths.

## Frozen protocol

1. **Guide:** each available model (chgnet, mace-mp-small, mace-mp-medium, mace-mpa-0-medium) proposes per path: predicted min image, predicted max image.
2. **Anchors (per model-path):** DFT (GPAW, PBE) single-points at the reference profile positions `{model-min, model-max ± 1}` + both endpoints. ±2 window only as the declared fallback when the path has ≤6 images (window covers >half the path — recorded, not tuned).
3. **Measurement:** sparse barrier = max(anchor energies) − min(anchor energies). Compared against the locked reference barrier (max−min over the full DFT profile).
4. **Panels:** the frozen 30-path Z1 test panel (`192fe54a…`). No refitting, no relocking.
5. **Compute:** GPAW on Cloud Run jobs (same isolated jobs; new image with `gpaw` added — version-locked and recorded in the execution environment manifest).

## Success criteria

- **WIN:** sparse-DFT barrier MAE ≤ 40 meV per model (the Z1 screening gate) at ≤7 anchors/path.
- **Strong WIN:** MAE ≤ 15 meV per model (the simulated ±1 result would hold).
- **Cost claim:** median DFT evaluations/path ≤ 10 (vs ~50–100 for full NEB, estimated from panel image counts and frozen protocol steps); the claim is reported, not gated.

## Kill / honesty conditions

- If any model's geometry guidance degrades on denser paths (measured saddle-location error >15%), that failure is reported with the same prominence as a WIN.
- Anchors beyond the frozen sets are forbidden (that is the full-NEB escape hatch and voids the cost claim).
- GPAW vs VASP/PBE reference convention differences (functional, pseudopotential, k-points) are documented as a systematic-offset analysis, not silently absorbed: the sparse protocol's comparison is against the panel's own VASP references, so convention mismatch must be reported as its own line item.

## Publication

Library research report with per-path tables and receipts either way; lupine.science field note if a WIN holds. This is the pilot where the loop either passes the gate or names exactly why it cannot yet.
