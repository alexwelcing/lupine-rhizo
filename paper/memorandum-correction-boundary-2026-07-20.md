# A Correction Boundary for Foundation Interatomic Potentials: Machine-Checked Limits, a Geometry–Levels Decomposition, and Model-Guided Sparse DFT

**Memorandum of theory, draft v0.2 — 2026-07-20.**

> **Frozen-before-results declaration.** Every sentence of framing, theory, and protocol was written before the sparse-DFT campaign completed. Result slots are marked `[PENDING]`; everything measured is locked `[FINAL]` with receipts. Claims carry an epistemic register (§9). Machine-checked theorems: `lean-spec/OpenDistillationFactory/HonestErrors/CorrectionBoundary.lean` — merged, 3761-job `lake build`, zero `sorry`, zero new axioms (`#print axioms` restricted to `propext`, `Classical.choice`, `Quot.sound`). Preregistrations and locked panels are content-addressed; the abstention record is included, not edited away.

**Intended readership.** Machine-learning venues (ICML track on science), computational-materials venues, and reviewers who must decide whether AI-designed matter can be trusted — including those who audit claims on behalf of institutions and states.

## Abstract

Foundation machine-learned interatomic potentials (uMLIPs) are being asked to carry materials decisions at national scale — battery electrolytes, catalysts, structural alloys — on the strength of speed claims that were never falsification-tested at the observables that matter. We report the first preregistered, hash-locked measurement of that trust question on migration barriers: across 30 chemistry-held-out lithium-conductor paths, four foundation models miss a 40 meV accuracy gate by 3.4–6× (MAE 135.0–242.5 meV), identically under two precision regimes, with systematic under-prediction rather than scatter `[FINAL]`. We then do three things the field has not done. First, we prove the *correction boundary* in Lean 4: additive shifts cannot move a barrier; a model's barrier error is exactly its profile wobble, with a tightness witness; slope corrections help only under sign stability; and anchors at the two true extrema reconstruct the barrier exactly — which is to say, accuracy costs precisely model irrelevance at two points (§3). Second, we show the failure decomposes: the models' energy *levels* are wrong while their energy *landscape geometry* — transition-state locations — is right on 82–86% of paths (89–93% within one image) `[FINAL]`. Third, from the theorems and the decomposition we derive **model-guided sparse DFT**: the model proposes extrema, a free DFT engine measures only those points. On the locked reference profile the protocol reproduces barriers with MAE 1.2–9.4 meV at ≈7 evaluations per path, against ≈50–100 for full NEB — under the same 40 meV gate the raw models miss by 3.4–6× `[FINAL, simulation]`. The physical campaign is frozen herein (protocol, success criteria, analysis plan; §5) and reports `[PENDING]`. Beyond the specific result, we present the process as a method for distilling physical laws from error structure: preregistration with content-addressed evidence, anti-laundering ingestion into machine-checked claims registries, and abstention as a first-class epistemic output (§7). The claims that could not survive this process — every cheap correction we tried — are preserved as a record.

## 1. Introduction

### 1.1 The trust question, asked properly

The public case for foundation interatomic potentials is throughput: screen thousands of candidates at MLIP speed, let DFT follow the winners. This case fails silently if the MLIP errs *systematically* — if every barrier it reports is low and every interface it reports is weak — because then the winners are chosen by a biased judge, and no amount of downstream DFT launders the choice. The correct response to a biased judge is not more screening; it is a boundary: a formal statement of where the judge can and cannot be believed, and a protocol that operates inside the boundary.

We build that boundary here, in three layers: measured failure (§2), machine-checked limits (§3), and a protocol that passes inside the limits (§4–§5). Each layer is constrained to be checkable by an adversarial reviewer: measurements are hash-locked before analysis, theorems are machine-checked, and anything not yet measured is explicitly marked pending.

### 1.2 Contributions

1. **A preregistered measurement of systematic underbinding** at migration barriers across 30 chemistry-held-out paths and four foundation models, in duplicate precision regimes, with all artifacts content-addressed (§2).
2. **The correction boundary**: to our knowledge the first machine-checked impossibility bounds for runtime correction of uMLIP observables — shift invariance, the wobble bound with tightness, slope-stability licensing, and anchor pricing with two-point exactness (§3).
3. **The geometry–levels decomposition**: the empirical separation of energy-level error from landscape-geometry accuracy, quantified per model (§4).
4. **Model-guided sparse DFT**, a protocol that passes the same gate the raw models fail, at an order-of-magnitude-lower DFT cost, with its cost and failure modes declared in advance (§5).
5. **The process itself** as a method for distilling physical laws from error structure: preregistration, anti-laundering evidence chains, machine-checked claims, and abstention-as-output (§7).

## 2. The measured failure

### 2.1 Protocol

Thirty migration paths, one per chemical system, drawn from the LiTraj nebDFT2k benchmark (npj Comput. Mater. 2025, DOI [10.1038/s41524-025-01571-z](https://doi.org/10.1038/s41524-025-01571-z)) and locked with SHA-256 `192fe54a…` before any model ran. The barrier convention — max(image energy) − min(image energy) — is identical on the reference and prediction sides; the panel builder validates the dataset's own barrier against the profile max−min within 0.5 meV. Execution: one Cloud Run cell per model on isolated jobs (NVIDIA L4), CI-NEB per path under a frozen protocol, per-path outcomes recorded without imputation; manifest and panel hashes validated fail-closed by the runner.

### 2.2 Results `[FINAL]`

| Model | float32 MAE (meV) | float64 MAE (meV) | completed | signed-error direction |
|---|---|---|---|---|
| mace-mpa-0-medium | 135.0 | 135.0 | 28/30 | 17/26 negative (mp-small f64) |
| mace-mp-small | 152.0 | 151.9 | 26/30 | all 26 negative (f32) |
| mace-mp-medium | 174.7 | 174.7 | 29/30 | mixed |
| chgnet | 242.5 | 242.5 | 28/30 | predominantly negative |

A float32 protocol defect found in review (vendor guidance reserves float32 for geometry optimization) changed the outcome by ≤0.1 meV per model: the failure is model error, not numerics. This replicates, at preregistered scale, the published softening record (Deng et al., DOI [10.1038/s41524-024-01500-6](https://doi.org/10.1038/s41524-024-01500-6); Bheemaguli et al., DOI [10.1039/D5DD00534E](https://doi.org/10.1039/D5DD00534E), who report 73–78% underprediction across 574 literature-derived paths).

### 2.3 Every cheap correction fails — and the record is kept

Global scalars, additive shifts, per-family shifts, and frozen six-point deltas leave MAE at 139–160 meV or worse. A preregistered disjoint-training pilot (12 paths, zero chemistry overlap) ended in universal abstention: signed errors flip sign *within* every chemistry family, so no low-dimensional correction is honest on this field. Even a perfect best-of-four oracle — hindsight model selection per path — reaches only 70 meV. We preserve these results because they are the evidence that the boundary in §3 is not optional.

## 3. Theory: the correction boundary

Definitions. A profile is a map `p : Fin n → ℝ` (sampled energies along a reaction path); `barrier p = max p − min p`; the per-image deviation `d = m − r` between model and reference profiles; the wobble `wobble d = max d − min d`. All theorems below are proved in Lean 4 (`CorrectionBoundary.lean`) with zero `sorry`.

**Theorem 3.1 (shift invariance).** For any constant `c`, `barrier (fun i ↦ p i + c) = barrier p`. *Global additive shifts cannot change a barrier.* This kills the entire family of level-shift corrections — not with an experiment, with a theorem.

**Theorem 3.2 (wobble bound).** `|barrier m − barrier r| ≤ wobble d`, and there exist profiles achieving equality (tightness witness `barrier_error_le_wobble_tight`). A model's barrier error is *exactly* its profile wobble; no correction operating on the model's own outputs can guarantee better. This is the no-free-lunch theorem of runtime correction.

**Theorem 3.3 (slope family).** For a single-ratio correction scaled by `σ`, the corrected error is bounded by the slope residuals (`slope_correction_error_le`); one-signed slope ratios are exactly the condition under which the midrange-ratio certificate strictly improves the raw one; and there exist mixed-sign profiles on which every ratio correction degenerates to a shift — whereupon Theorem 3.1 applies (`slope_instability_witness`). Note carefully what this says: slope corrections are *licensed only by sign stability*, a condition our training data violated everywhere (§2.3) — the abstention is a theorem's worth of honesty, not a conservative mood.

**Theorem 3.4 (anchor pricing).** Anchoring a single point `k` to its reference value changes the barrier by at most `|m k − r k|` (`anchor_barrier_change_le`), and the residual error is at least the raw error minus that amount (`anchor_impossibility_bound`). Anchors at the sampled maximum and minimum reconstruct the barrier exactly (`two_point_anchor_exact`). Read as a price list: accuracy costs exactly two anchors — and at two anchors the model contributes nothing but location. (A stronger "precise" bound proposed in the design was found false and is refuted in-file, `anchor_wobble_lower_bound_refuted`: the boundary layer audits itself.)

**Corollary 3.5 (routing bound).** Any model-selection rule restricted to a fixed model set inherits each member's wobble; hence the 70 meV oracle ceiling of §2.3 is a property of the set, not of the selector.

## 4. The geometry–levels decomposition `[FINAL]`

Theorem 3.2 says error lives in the wobble. Where does the wobble live? Comparing model-predicted and reference image-energy argmax on the locked panel:

| Model | exact saddle location | within ±1 image | along-path wobble (RMS) |
|---|---|---|---|
| chgnet | 24/28 (86%) | 26/28 (93%) | ~131 meV |
| mace-mp-small | 23/26 (88%) | 23/26 (89%) | ~103 meV |
| mace-mpa-0-medium | 23/28 (82%) | 25/28 (89%) | ~110 meV |

The models misprice the *level* of the landscape while correctly locating its *extrema*. This is the decomposition the whole program turns on: geometry is the model's skill; levels are its failure. The published softening record attributes level failure to near-equilibrium training bias (Deng et al.); our measurement adds that the *geometric* layer survives that bias.

## 5. Method: model-guided sparse DFT (frozen protocol)

Theorem 3.4 prices exactness at two anchors — provided they are the *true* extrema. §4 says the model supplies them 82–93% of the time. The protocol follows:

1. **Guide.** Each model evaluates the path's input images (single-point energies; no relaxation — the model only guides) and proposes predicted min/max image indices.
2. **Anchors.** A free DFT engine (GPAW, PBE [enkovaara2010gpaw; mortensen2005gpaw; perdue1996pbe]) evaluates the reference-profile positions `{min, max ± 1}` plus both endpoints; short paths (≤6 images) widen to ±2, declared.
3. **Measure.** Sparse barrier = max − min over anchor energies, scored against the locked reference barrier. **WIN: MAE ≤ 40 meV per model. Strong WIN: MAE ≤ 15 meV.**
4. **Honesty conditions.** Anchors beyond the frozen sets void the cost claim; GPAW-vs-VASP convention differences (functional, pseudopotential, k-points; [grimme2006d2; kresse1996vasp]) are reported as their own line item; any GPAW failure fails that path, recorded without imputation.

**Simulation on the reference profile `[FINAL]`**: across all 82 model-path pairs, MAE 1.2–9.4 meV at ≈7 anchors/path (±2: exact) — the same 40 meV gate the raw models miss by 3.4–6×, at ≈10× lower DFT cost.

## 6. Results (preregistered analysis plan)

- **T1 — convention offset**: GPAW vs VASP reference energy per anchor (mean, max |Δ|), per path class. `[PENDING]`
- **T2 — sparse MAE per model** with WIN/strong-WIN verdicts and per-family no-harm checks. `[PENDING]`
- **T3 — cost**: median anchors/path vs the frozen full-NEB protocol. `[PENDING]`
- **F1 — the boundary figure**: raw error vs wobble, sparse error vs wobble, Theorem 3.2 overlaid. `[PENDING]`

## 7. The process: distilling physical laws from error structure

The measurements in this memorandum were produced by a pipeline that treats *process* as a first-class scientific object: campaign manifests are content-addressed before execution; panels are SHA-locked; runners validate hashes fail-closed; measurement rows are RFC 8785-canonicalized and hash-chained; ingestion into the claims registry is derivation, not editing — status changes require bundle-hash changes, so no verdict can be laundered by hand; and the formal layer certifies the registry's outcomes in Lean (`z1_gate_refuted`, `z3_gate_refuted` — the machine-checked record of these same failures). Abstention is a first-class output: the registry of this program contains refuted claims and an abstained campaign, deliberately un-deleted. We claim this process — preregistration + hash-chained evidence + machine-checked claims + abstention — is itself a method for distilling physical laws from error structure, and the correction boundary of §3 is its first law.

## 8. Related work

**Softening and underbinding.** Deng et al., npj Comput. Mater. (2025), DOI [10.1038/s41524-024-01500-6](https://doi.org/10.1038/s41524-024-01500-6); Bheemaguli, Xiao & Sai Gautam, Digital Discovery 5 (2026) 1809–1819, DOI [10.1039/D5DD00534E](https://doi.org/10.1039/D5DD00534E). **Barrier-specific fine-tuning (the training route we exclude).** Lian et al., J. Mater. Chem. A 13 (2025), DOI [10.1039/D5TA05355B](https://doi.org/10.1039/D5TA05355B) — effective at ~3k labels; our constraint is zero training. **Δ-learning and active residual models.** Christiansen & Hammer, J. Chem. Phys. 162, 184701 (2025), DOI [10.1063/5.0268264](https://doi.org/10.1063/5.0268264); Pitfield et al., Phys. Chem. Chem. Phys. 28, 912–926 (2026), DOI [10.1039/D5CP04302F](https://doi.org/10.1039/D5CP04302F). **Foundation models.** MACE-MP-0: Batatia et al., arXiv:2401.00096; CHGNet: Deng et al., Nat. Mach. Intell. 5, 1031–1041 (2023), DOI [10.1038/s42256-023-00716-3](https://doi.org/10.1038/s42256-023-00716-3); DPA-1/DPA-2: Zhang et al., npj Comput. Mater. (2024), DOIs [10.1038/s41524-024-01278-7](https://doi.org/10.1038/s41524-024-01278-7), [10.1038/s41524-024-01493-2](https://doi.org/10.1038/s41524-024-01493-2); MatterSim: Yang et al., arXiv:2405.04967. **Benchmarks.** LiTraj nebDFT2k, DOI [10.1038/s41524-025-01571-z](https://doi.org/10.1038/s41524-025-01571-z); CatBench BM (GAME-Net lineage), Zenodo DOI [10.5281/zenodo.17157086](https://doi.org/10.5281/zenodo.17157086), npj/Nat. Comput. Sci. DOI [10.1038/s43588-023-00437-y](https://doi.org/10.1038/s43588-023-00437-y). **Method theory.** Sloppy-model/error-geometry foundations: Brown & Sethna, Phys. Rev. E 68, 021904 (2003). CI-NEB: Henkelman & Jónsson, J. Chem. Phys. 113, 9978 (2000). Conformal abstention: Vovk, Gammerman & Shafer (2005); Angelopoulos & Bates, arXiv:2107.07511. **Verification.** Lean 4: de Moura & Ullrich, CADE-28 (2021). Preregistration practice: Nosek et al., PNAS 115, 2600–2606 (2018). **Quantum engines.** GPAW: Enkovaara et al., J. Comput. Chem. 31, 2474 (2010); Mortensen et al., Phys. Rev. B 71, 035109 (2005). VASP: Kresse & Furthmüller, Phys. Rev. B 54, 11169 (1996). PBE: Perdew, Burke & Ernzerhof, Phys. Rev. Lett. 77, 3865 (1996). Grimme D2: J. Comput. Chem. 27, 1787 (2006).

## 9. Epistemic-status register

| Claim | Status | Receipt |
|---|---|---|
| Four models fail the 40 meV barrier gate, 135–243 meV | FINAL | Round-4 locks + artifacts, PRs #26–#31 |
| Precision-independence of the failure | FINAL | float64 chain, PR #32, #36 |
| All cheap corrections fail; pilot abstains universally | FINAL | R5 record, PRs #54, #55 |
| Routing oracle ceiling 70 meV | FINAL | R4 analysis (this repo) |
| Boundary theorems (3.1–3.4, Corollary 3.5) | MACHINE-CHECKED | `CorrectionBoundary.lean`, PR #56 |
| Geometry accuracy 82–86% exact / 89–93% ±1 | FINAL | R4 artifacts |
| Sparse protocol MAE 1.2–9.4 meV on reference profile | FINAL (simulation) | analysis of locked panel |
| Sparse pilot physical MAE, WIN verdicts, cost | PENDING | campaign per §5 |
| GPAW-vs-VASP convention offset | PENDING | T1 |

## 10. Limitations and honesty conditions

Panel paths are short (5–10 images); the sparse advantage grows with denser paths and is not claimed at long-path scale. The ±2 short-path fallback is declared, not tuned. Simulation (§5) is exact arithmetic on reference data, not physical measurement; the campaign decides, and if geometry guidance degrades on denser paths that failure is reported with the same prominence as a WIN. The abstention record of §2.3 stands; nothing here re-opens the corrections already refuted. All panel references are published DFT, not experiment; nothing here is error-against-experiment.

## References

[Resolved in §8 with DOIs; additional: Brown & Sethna PRE 68, 021904 (2003); Henkelman & Jónsson JCP 113, 9978 (2000); Vovk et al. (2005); Angelopoulos & Bates arXiv:2107.07511; de Moura & Ullrich, CADE-28 (2021); Nosek et al., PNAS 115 (2018); Enkovaara et al., JCC 31 (2010); Mortensen et al., PRB 71 (2005); Kresse & Furthmüller PRB 54 (1996); Perdew, Burke & Ernzerhof PRL 77 (1996); Grimme, JCC 27 (2006).]

---

*Receipts: locked panels (`192fe54a…`, `4099f4fc…`); Round-4/5 artifacts `gs://shed-489901-atlas-outputs/`; Lean module PR #56; preregistrations `docs/plans/2026-07-20-sparse-dft-pilot-preregistration.md`, `2026-07-20-round5-z1-correction-preregistration.md`, `2026-07-20-correction-boundary-theorems.md`; claims registry entries for this campaign remain `unsupported` until ingestion.*
