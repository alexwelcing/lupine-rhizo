# Amendment 01 to the Z1 sparse-DFT pilot preregistration

- **Base document:** `docs/plans/2026-07-20-sparse-dft-pilot-preregistration.md` (frozen 2026-07-20)
- **Amendment date:** 2026-07-21
- **Approved by:** owner, in conversation 2026-07-21 ("sounds like we need I approve of doing 1, 2, and 3")
- **Trigger evidence:** `path-7` (mp-770939_10_1_1_0_1) completed 2026-07-21 with absolute barrier error 118.8 meV vs the frozen ≤40 meV gate; per-anchor receipts show the GPAW↔VASP offset wanders ~139 meV across the four anchor images (−14.756, −14.698, −14.617, −14.666 eV). The earlier smoke path (mp-760344) shows ~122 meV wander with a 32.2 meV WIN. Two paths, two opposite verdicts, same wander magnitude → verdicts vs the VASP reference currently measure engine-convention luck, not protocol quality.

## A1. The comparison basis splits in two

The frozen prereg (line 32) already requires convention mismatch to be reported as its own line item. This amendment promotes that line item to a standalone experiment and moves the primary gate to a same-engine basis:

- **Primary gate (new):** sparse-GPAW barrier vs **dense same-engine GPAW static profile** — GPAW single-point energies at *every* image of the panel's recorded NEB geometries, barrier = max − min over the full profile. WIN ≤40 meV, strong WIN ≤15 meV, unchanged thresholds. This measures exactly one thing: does theorem/model-guided anchor selection recover the dense profile's barrier?
- **Secondary (retained, non-gating):** sparse-GPAW vs the panel's VASP reference, as originally frozen. Reported alongside every verdict.
- **T1 becomes its own experiment:** per path, report offset mean and **offset wander** (max − min of per-image GPAW−VASP offsets over evaluated images). The wander — not the mean — is the barrier-relevant quantity, because barriers difference energies at different images.

## A2. Rationale (one paragraph)

Barriers are energy *differences between different structures*, so any non-constant engine offset injects directly into the comparison. Measured wander (~122–139 meV) is ~3× the 40 meV gate, so under the original single-basis design the pilot would pass or fail on where the wander happens to land — an engine-equivalence question the pilot never claimed to answer. Splitting the basis makes each verdict measure one thing. Nothing about the MLIP-correction thesis changes: the sparse/union protocol stands or falls on same-engine recovery, and engine equivalence is documented honestly as T1 rather than silently contaminating verdicts.

## A3. Union-anchor execution (replaces per-model re-evaluation)

Anchors are model-independent GPAW evaluations; only the *selection* is model-guided. The pilot therefore now executes:

1. Per path, compute the **anchor universe** = union of all four models' anchor sets (per the frozen selection logic in `gcp/mlip-cell-runner/z1_sparse_dft.py`).
2. **Dense short paths:** all 23 active paths carry 5–7 images. For any path with ≤7 images the anchor universe is extended to *every image* — on short paths the union of four models already covers most images, so the dense same-engine profile costs ~0–3 extra evaluations per path and buys the A1 primary gate everywhere, not just on a subset.
3. Evaluate each unique anchor **once**, checkpointed per anchor (survives interruption; anchors importable across runs). Existing completed anchors (path-7's four; path-16's on landing) are imported, not recomputed.
4. Assemble per-model sparse barriers from the shared pool using the frozen selection logic; compute same-engine and VASP-referenced errors and T1 statistics from the same pool. One evaluation set, three measurements.

The per-model driver (`run_pilot.py`) is superseded for remaining paths; its completed results remain valid receipts.

## A4. What does NOT change

- Frozen GPAW settings: fd mode, h=0.18, kpts=(2,2,2), XC=PBE. Convergence-loosening remains a separate future amendment with its own one-path revalidation criterion.
- Thresholds: WIN ≤40 meV, strong WIN ≤15 meV (now applied to the same-engine basis).
- The seven deferred ≥159-atom paths (`data/candidates/z1-sparse-dft-deferred.json`): still `waiting`, verdicts PENDING, not excluded.
- No retraining, no fine-tuning: runtime correction only.
- Path-7's VASP-referenced FAIL (118.8 meV) stays in the record — as a T1 datapoint, not a protocol verdict.

## A5. Known operational risks (recorded, not yet solved)

- Memory: path-16 GPAW peaked at ~8.8 GB RSS on a 15 GB box; the 100+-atom cells later in the active set may OOM. Mitigation if hit: skip-and-record, do not silently loosen settings.
- Wall-time: measured pace on the second-smallest cell is ~1.5–2 h/anchor; the active panel is ~130–160 anchors total. Serial execution on this box is a multi-day effort by design (owner decision 2026-07-20: local over cloud).
