# When the geometry is right and the levels are wrong: model-guided sparse DFT for migration barriers, with machine-checked correction bounds

> **Draft v0.1 — 2026-07-20.** Frozen before results: every sentence of
> framing, theory, and protocol was written **before** the sparse-DFT
> measurements completed, so the narrative cannot drift toward the outcome.
> Result slots are marked `[PENDING-RESULTS]`; slots marked `[FINAL]` were
> measured and locked before this draft. Citations resolve to DOIs in-line.
> Lean theorem references: `lean-spec/OpenDistillationFactory/HonestErrors/CorrectionBoundary.lean` (merged, 3761-job build, zero `sorry`, zero new axioms).

## Abstract

Universal machine-learned interatomic potentials (uMLIPs) systematically underbind: across 30 chemistry-held-out lithium-conductor migration paths, four foundation models (CHGNet; MACE-MP small, medium, and MPA-0-medium) miss a 40 meV barrier-accuracy gate by 3.4–6× (MAE 135.0–242.5 meV), identically under float32 and float64, with every completed path under-predicting `[FINAL: Round-4]`. We show that this failure is not a deficit of geometry but of levels: the same models locate the transition state exactly on 82–86% of paths and within one image on 89–93% `[FINAL]`. We then prove the correction boundary in Lean 4: additive shifts cannot change any barrier (`barrier_shift_invariant`); a model's barrier error never exceeds its profile wobble, and the bound is tight (`barrier_error_le_wobble`); slope corrections help only under sign stability, with an explicit instability witness; and sparse anchors trade accuracy for model irrelevance at exactly two points (`anchor_impossibility_bound`, `two_point_anchor_exact`). Guided by these theorems we introduce **model-guided sparse DFT**: the model proposes extrema, a free DFT engine (GPAW/PBE) evaluates only those points. On the locked panel's reference profile the protocol returns barrier MAE 1.2–9.4 meV at ≈7 evaluations per path, versus ≈50–100 for full NEB `[FINAL, simulation]`. The preregistered physical campaign — its protocol, success criteria, and analysis plan frozen herein — reports `[PENDING-RESULTS]`. The loop this paper documents is the point: find the failure, bound it formally, and pass under preregistration or name precisely why not.

## 1. Introduction: the failure was measured first

AI-designed matter stands or falls on whether interatomic potentials can be trusted where it counts. Everywhere we looked, it could not — and we wrote it down before fixing it.

**Round-4 (frozen before execution).** On 30 chemistry-held-out DFT-NEB migration paths from the LiTraj nebDFT2k benchmark (DOI [10.1038/s41524-025-01571-z](https://doi.org/10.1038/s41524-025-01571-z); lock SHA-256 `192fe54a…`), executed on isolated Cloud Run jobs with hash-locked manifests, four available foundation models produced `[FINAL]`:

| Model | float32 MAE (meV) | float64 MAE (meV) | completed paths |
|---|---|---|---|
| mace-mpa-0-medium | 135.0 | 135.0 | 28/30 |
| mace-mp-small | 152.0 | 151.9 | 26/30 |
| mace-mp-medium | 174.7 | 174.7 | 29/30 |
| chgnet | 242.5 | 242.5 | 28/30 |

The verdict is precision-independent: a float32 protocol defect found in review (vendor guidance reserves float32 for geometry optimization) changed nothing. Signed errors are systematically negative — under-prediction, not scatter — consistent with the independently published record of systematic softening in uMLIPs (Deng et al., DOI [10.1038/s41524-024-01500-6](https://doi.org/10.1038/s41524-024-01500-6)) and with majority-underprediction across 574 literature-derived paths (Bheemaguli et al., DOI [10.1039/D5DD00534E](https://doi.org/10.1039/D5DD00534E)).

**The cheap corrections all fail honestly.** Global scalars, additive shifts, per-family shifts, and frozen deltas leave MAE at 139–160 meV or worse; a preregistered 12-path disjoint-training pilot abstained for every model because signed errors flip sign *within* every chemistry family — no low-dimensional correction is honest on this error field `[FINAL: Round-5 abstention record]`. Even a perfect best-of-four oracle — model selection with hindsight — only reaches 70 meV `[FINAL]`.

This paper is what happened next: instead of tuning harder, we asked what the models get *right*.

## 2. The correction boundary, machine-checked

The program's formal layer (Lean 4, `OpenDistillationFactory.HonestErrors.CorrectionBoundary`) proves, over sampled energy profiles `p : Fin n → ℝ` with `barrier p = max p − min p`:

- **`barrier_shift_invariant`.** `barrier (fun i ↦ p i + c) = barrier p`. Global additive shifts cannot change any barrier — the shift family's death certificate.
- **`barrier_error_le_wobble`.** `|barrier m − barrier r| ≤ wobble (m − r)`, where wobble is the range of the per-image deviation; with `barrier_error_le_wobble_tight` exhibiting equality. A model's barrier error is exactly its profile wobble; no information-free correction can beat the wobble.
- **Slope family.** A residual bound needing no sign hypothesis (`slope_correction_error_le`); one-signed slope ratios are exactly the condition under which the midrange certificate beats the raw one; `slope_instability_witness` gives the strongest true negative form (mixed-sign witnesses where every ratio correction degenerates to a shift and is killed by Theorem 1).
- **Anchor family.** `anchor_barrier_change_le` and `anchor_impossibility_bound` (anchoring a point removes at most that point's deviation; residual ≥ raw error − anchored deviation); `two_point_anchor_exact` — anchors at the sampled maximum and minimum reconstruct the barrier exactly, which is to say: accuracy costs precisely model irrelevance at two points. (A stronger "precise" bound from the design was found *false* and is refuted in-file, `anchor_wobble_lower_bound_refuted` — the boundary layer audits itself too.)

These are ideation-layer theorems: they freeze no gates; they map what any correction can and cannot achieve on this error field.

## 3. The observation: geometry right, levels wrong

Comparing model-predicted image-energy argmax against the reference profile's argmax on the locked panel `[FINAL]`:

| Model | exact saddle location | within ±1 image |
|---|---|---|
| chgnet | 24/28 (86%) | 26/28 (93%) |
| mace-mp-small | 23/26 (88%) | 23/26 (89%) |
| mace-mpa-0-medium | 23/28 (82%) | 25/28 (89%) |

The models' per-image energy *wobble* (~100–130 meV RMS along each path) destroys their barriers, but their *landscape shape* — where the saddle sits — is overwhelmingly right. Theorem 2 explains the failure; Theorem 4 names the fix: anchors at the true extrema reconstruct the barrier exactly. Put them together and the protocol is forced on us: **let the model choose the points; let DFT measure them.**

## 4. The sparse protocol (frozen)

Per model and path: the model proposes its predicted minimum and maximum images. A free DFT engine (GPAW, PBE) evaluates the reference-profile positions `{min, max ± 1}` plus both endpoints (±2 window as the declared short-path fallback). The sparse barrier is max − min over the anchor energies, compared against the locked reference barrier. **WIN: MAE ≤ 40 meV per model at ≤7 anchors/path. Strong WIN: MAE ≤ 15 meV.** Cost claim reported (target ≤10 DFT evaluations/path vs ≈50–100 for full NEB). Anchors beyond the frozen sets void the cost claim. GPAW-vs-VASP convention differences (functional, pseudopotential, k-points) are reported as their own line item, not silently absorbed.

**Simulation on the reference profile `[FINAL]`**: MAE 1.2–9.4 meV across all 82 model-path pairs at ≈7 points/path — under the 40 meV gate the raw models miss by 3.4–6×.

## 5. Results (preregistered analysis plan)

The following tables and figures are frozen in structure; numbers land as `[PENDING-RESULTS]`:

- **T1 — per-anchor convention offset:** GPAW energy vs VASP reference energy at each anchor point (mean, max |Δ|), per path class. `[PENDING-RESULTS]`
- **T2 — sparse vs reference barrier per model:** sparse MAE, WIN/strong-WIN verdicts, per-family breakdown with the no-harm check. `[PENDING-RESULTS]`
- **T3 — cost:** median DFT evaluations per path; ratio vs the frozen full-NEB protocol. `[PENDING-RESULTS]`
- **F1 — the correction boundary figure:** raw model error vs path wobble, sparse-corrected error vs the same, with Theorem 2's bound overlaid. `[PENDING-RESULTS]`
- **F2 — geometry-vs-levels:** saddle-location accuracy by model and path length. `[FINAL]`

## 6. Related work

Systematic softening in uMLIPs: Deng et al. (npj Comput. Mater. 2025, DOI [10.1038/s41524-024-01500-6](https://doi.org/10.1038/s41524-024-01500-6)) — energy/force underprediction attributed to near-equilibrium training bias; our barrier-level measurement is the same phenomenon at preregistered scale. Population-level underprediction: Bheemaguli et al. (Digital Discovery 2026, DOI [10.1039/D5DD00534E](https://doi.org/10.1039/D5DD00534E)). The one demonstrated barrier-specific fix is transition-state-targeted fine-tuning at ~3k labels (Lian et al., DOI [10.1039/D5TA05355B](https://doi.org/10.1039/D5TA05355B)) — effective but a training program; this paper's constraint is zero training. Δ-learning on embeddings and active Δ for global optimization (Christiansen & Hammer, DOI [10.1063/5.0268264](https://doi.org/10.1063/5.0268264); Pitfield et al., DOI [10.1039/D5CP04302F](https://doi.org/10.1039/D5CP04302F)) — the sparse protocol is their cost model taken to its limit: minimum anchors at model-chosen points. No published production runtime abstention policy exists (our China-lab review, in repo); the boundary theorems are, to our knowledge, the first machine-checked correction-impossibility bounds.

## 7. Limitations and honesty conditions

Panel paths are short (5–10 images); the sparse advantage grows with denser paths and is not claimed at long-path scale here. The ±2 short-path fallback is declared, not tuned. Simulation (§4) is exact arithmetic on the reference profile, not a physical measurement; the campaign decides. If geometry guidance degrades on denser paths, that failure is reported with the same prominence as a WIN. The abstention record of §1 stands: nothing in this paper re-opens the low-dimensional corrections already refuted.

## References

1. LiTraj nebDFT2k benchmark, npj Comput. Mater. (2025). DOI [10.1038/s41524-025-01571-z](https://doi.org/10.1038/s41524-025-01571-z)
2. Deng et al., Systematic softening in universal MLIPs, npj Comput. Mater. (2025). DOI [10.1038/s41524-024-01500-6](https://doi.org/10.1038/s41524-024-01500-6)
3. Bheemaguli, Xiao & Sai Gautam, Evaluation of foundational MLIPs for migration barrier predictions, Digital Discovery 5 (2026) 1809–1819. DOI [10.1039/D5DD00534E](https://doi.org/10.1039/D5DD00534E)
4. Lian et al., High-throughput NEB via fine-tuned CHGNet, J. Mater. Chem. A 13 (2025). DOI [10.1039/D5TA05355B](https://doi.org/10.1039/D5TA05355B)
5. Christiansen & Hammer, Δ-model correction of foundation models, J. Chem. Phys. 162, 184701 (2025). DOI [10.1063/5.0268264](https://doi.org/10.1063/5.0268264)
6. Pitfield, Christiansen & Hammer, Active Δ-learning with universal potentials, Phys. Chem. Chem. Phys. 28, 912–926 (2026). DOI [10.1039/D5CP04302F](https://doi.org/10.1039/D5CP04302F)
7. Batatia et al., A foundation model for atomistic materials chemistry (MACE-MP-0), arXiv:2401.00096
8. Deng et al., CHGNet, Nat. Mach. Intell. 5, 1031–1041 (2023). DOI [10.1038/s42256-023-00716-3](https://doi.org/10.1038/s42256-023-00716-3)

---

*Receipts: locked panels (`192fe54a…`, `4099f4fc…`), Round-4/5 artifacts under `gs://shed-489901-atlas-outputs/`, Lean module at PR #56, preregistrations in `docs/plans/`. Claims-registry entries for this campaign remain `unsupported` until ingestion.*
