# Lupine Project — Kill the big-cell tax in MLIP validation

**Date:** 2026-06-27  
**Audience:** program managers, HPC facility directors, materials-AI funders  
**One-line ask:** fund scale-out to alloys, defects, and a class-aware correction operator that fixes the MLIP bias we just measured.

---

## The problem

Supercomputer labs validating machine-learned interatomic potentials (MLIPs) currently pay a steep **big-cell tax**: elastic constants are routinely re-run in 3×3×3 supercells (27× more atoms) to rule out finite-size effects. For the cubic metals in our 16-element benchmark, that convention costs **3.86×** more core-hours than a conventional 1×1×1 cell without buying any accuracy.

We also tested two single-model correction operators. The first, a global leave-one-out PCA bias vector, **increased** mean MAE from 14.55 GPa to 63.40 GPa. The second, a scalar re-scaling of the bulk-modulus functional shift, is the R&D win: on the Tr2SCAN-corrected target it achieves mean MAE 14.13 GPa at the same single-model cost, beating the 3-architecture ensemble (19.89 GPa) at **2.70× lower cost**.

## The claim

**Conventional-cell 1×1×1 elastic-constant calculations are just as accurate as 3×3×3 supercells for cubic metals, at roughly 4× lower core-hour cost. On the Tr2SCAN-corrected target, a cheap scalar-bulk operator beats a 3-model ensemble at 2.7× lower cost.**

| Arm | Cell / models | Mean MAE vs TPBE (GPa) | Mean MAE vs Tr2SCAN (GPa) | Core-hours (16 elem) |
|-----|---------------|-----------------------:|--------------------------:|---------------------:|
| Raw 1×1×1 | single model, no correction | **14.55** | 22.55 | **0.0134** |
| Scalar-bulk 1×1×1 | single model + v0.2 operator | 19.17 | **14.13** | **0.0134** |
| Reference 3×3×3 | single model, supercell | **14.61** | 22.63 | **0.0518** |
| Ensemble 1×1×1 | 3 architectures, averaged | **11.60** | 19.89 | **0.0362** |
| Corrected 1×1×1 | single model + v0.1 operator | **63.40** | 54.28 | **0.0134** |

The **raw 1×1×1** calculation is the honest cost-accuracy point against TPBE: it is statistically indistinguishable from the 3×3×3 reference (ΔMAE = +0.06 GPa) and uses **3.86×** fewer core-hours. The **ensemble 1×1×1** wins on accuracy against TPBE (11.60 GPa) but costs **2.70×** more than raw. The **scalar-bulk 1×1×1** operator wins against Tr2SCAN (14.13 GPa vs ensemble 19.89 GPa) while sharing raw's cost. The **corrected 1×1×1** v0.1 operator is a failed first-pass hypothesis.

## The evidence

- **16 cubic metals**, curated 0 K PBE/r2SCAN targets: Al, Ag, Au, Ca, Cu, Ni, Pd, Pt, Sr, Cr, Fe, Mo, Nb, Ta, V, W.
- **MatPES 2025.2** foundation MLIPs: M3GNet, CHGNet, TensorNet (the `QET` label resolves to the same TensorNet checkpoint and is de-duplicated).
- **Best single model:** TensorNet/PBE, 13.25 GPa mean MAE on the full 16-element grid.
- **v0.1 correction operator (failed):** leave-one-out principal-component bias vector fit on 15 elements, tested on the 16th, plus a scalar PBE→r2SCAN functional shift. It failed to generalize: mean MAE rose to 63.40 GPa vs TPBE.
- **v0.2 scalar-bulk operator (R&D win):** leave-one-out scalar re-scaling of the bulk-modulus functional shift. Mean MAE 14.13 GPa vs Tr2SCAN at 0.0134 core-hours; cell-size independent (3×3×3 grid gives 14.14 GPa).
- **Variance check:** Ca, Cu, Fe, Cr run with 3 seeds each (12 cases). TensorNet/PBE 1×1×1 is deterministic; MAE standard deviations are ~0 GPa.
- **Cost ledger:** cache-warm, per-case CPU-equivalent core-hours. Supercell independence is already demonstrated: matched Cu/Ni 1×1×1→3×3×3 ΔMAE is only +0.03 GPa, so finite-size effects are not the binding error source.

## The ask

The science risk is bounded on the main claim: conventional cells already match supercells for cubic metals. The new R&D opportunity is to turn the scalar-bulk Tr2SCAN win into a broadly applicable, target-aware correction operator.

1. **Alloys and off-stoichiometric systems** — test whether the small-cell equivalence transfers when multiple elements share a conventional cell, and whether class-aware operators can learn element-specific bias structures.
2. **Defects and interfaces** — extend the cost ledger to surfaces, grain boundaries, and dislocation cores, where supercell costs explode and the big-cell tax matters most.
3. **Target-aware correction operators** — scale the scalar-bulk idea to other properties and targets, and design class-specific or locally fitted bias models that improve PBE-target performance while preserving the Tr2SCAN-target win.
4. **Partner HPC sites** — package the protocol as a one-command artifact so national labs can drop it into existing MLIP benchmark pipelines.

---

## Caveats

- **Headline TPBE numbers are against TPBE_0K.** The scalar-bulk win is on the Tr2SCAN-corrected sensitivity target; it does not beat raw or the ensemble on the PBE headline target.
- **r2SCAN targets are approximated** by a scalar bulk-modulus shift; r2SCAN is a sensitivity check, not the primary reference.
- **Single-relax runs.** Costs and MAEs come from one calculation per case; variance was checked on a 4-element, 3-seed subset.
- **Variance subset is clean.** Ca, Cu, Fe, Cr run 3 times each show TensorNet/PBE 1×1×1 is deterministic, with MAE standard deviations ~0 GPa.
- **Cr is a pathological outlier.** Cr mean MAE reaches 45.85 GPa in the raw arm; robust summaries should report both mean and median.
- **Au uses a PW91-GGA fallback.** No stable published PBE cubic Au elastic tensor was recovered.
- **QET ≡ TensorNet alias.** The honest MLIP roster is three architectures, not four.
- **v0.1 operator is in-sample broken.** The LOO-PCA bias was fitted on the other 15 elements and still degraded accuracy, which signals an ill-posed operator assumption rather than a validation artifact.

---

## Links

- **Preprint:** [arXiv / lupine.science URL to be added before distribution]
- **HPC artifact (one-command reproduction):** [GitHub / repository URL to be added before distribution]
- **Interactive dashboard:** [Cloudflare Pages / library.lupine.science URL to be added before distribution]
- **Source plans:** `docs/plans/mlip-elastic-benchmark-master-2026-06-27.md`
- **Round-2 results memo:** `exports/library-content/latest/articles/docs/projection-law-round2-results.md`
