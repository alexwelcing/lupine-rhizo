# Lupine Refinement Sprint: Five Theorems, One Benchmark, Zero `sorry`

**Date:** 2026-06-27  
**Announcement type:** public / press / investor update  
**Canonical links:**
- Public library: <https://library.lupine.science>
- Lupine source: <https://github.com/alexwelcing/lupine>
- Rhizo mirror: <https://github.com/alexwelcing/lupine-rhizo>
- Ledger site source: <https://github.com/alexwelcing/lupine-ledger>

---

## TL;DR — what we shipped

1. **No-harm guarantee for the 1-D shared-error correction.** We proved in Lean that when the shared error lies on a 1-D manifold, the projected correction never increases the residual norm, then aligned the Rust `mlip_correct` coefficient exactly with the Lean `alpha`.
2. **Rank-k transferability bound for real alloys.** We extended the 1-D sine-of-principal-angle bound to rank-k subspaces and locked the Mg-Li / Al-Cu-style LOOCV reasoning behind a build-locked theorem.
3. **Active sampling acquisition contract.** We formalized the greedy residual-max rule and proved both a one-step optimality theorem and a rank-k sample-complexity bound.
4. **Composition optimizer hardening.** `mlip_optimize` now carries elastic-stability guards, moduli-consistency checks, R² refusal, jackknife RMSE, and an optimality-gap estimate.
5. **Epistemic provenance tags.** Every benchmark entry is now tagged `synthetic`, `nistIpr`, or `experiment`; the validation report warns when synthetic fixtures are present so they cannot be mistaken for empirical evidence.

All five areas compile: `lake build OpenDistillationFactory` is green and `cargo test` / `cargo clippy --all-targets -- -D warnings` pass.

---

## Why this matters

Machine-learned interatomic potentials (MLIPs) are being asked to predict elastic constants, defect energies, and phase stability for real alloys. Before we trust them for high-stakes materials decisions, three questions need rigorous answers:

- **Will a correction make any potential worse?** The 1-D no-harm theorem answers “no” for the shared-error case.
- **How much can we trust a correction trained on one alloy class when applied to another?** The rank-k transfer bound answers with `sin θ_k · ‖target‖`.
- **Which expensive simulation should we run next?** The active-sampling contract justifies the greedy residual-max heuristic with a proven bound.
- **Are recommended compositions physically sane?** The hardened optimizer refuses Born-unstable or statistically unsupported fits.
- **Are we calling synthetic tests empirical?** Provenance tags enforce honesty at the data-entry level, with Lean-backed checks for NIST-backed claims.

---

## The 3×3×3 Layer 2 benchmark campaign

We are now running the 56 element/model tasks of the Layer 2 3×3×3 16-element cubic-metal elastic-constant grid concurrently in isolated GCP runs (14 elements × 4 universal MLIPs: M3GNet, CHGNet, TensorNet, QET, each at PBE and r2SCAN). The 4×4×4 supercell comparison is postponed; the 3×3×3 grid gives the precision/cost ratio we need for the public preprint.

The benchmark artifacts are already in the public library:
- [MLIP Elastic Benchmark Preprint](https://library.lupine.science/articles/mlip-elastic-benchmark/mlip-elastic-benchmark-preprint-2026-06-27.html)
- [MLIP Elastic Benchmark Protocol](https://library.lupine.science/articles/mlip-elastic-benchmark/mlip-elastic-benchmark-protocol-2026-06-27.html)
- [Operator Failure Diagnosis](https://library.lupine.science/articles/mlip-elastic-benchmark/operator-failure-diagnosis-2026-06-27.html)

---

## For the press

### One-paragraph summary

Lupine, the open MLIP-distillation research platform, has completed a five-front formalization sprint that turns heuristic correction and sampling rules into machine-checked theorems, hardens the composition optimizer against physically impossible recommendations, and tags every benchmark entry with its epistemic source. The work is published in the project’s public library as the team launches a 56-run concurrent GCP benchmark of universal MLIPs across 14 cubic metals.

### Key talking points

- **Formal methods meet materials ML:** Lean 4 theorems now guard the core correction, transfer, and active-sampling logic.
- **Honest benchmarking:** Synthetic fixtures are explicitly labeled and cannot be cited as empirical evidence.
- **Open by default:** Source, specifications, and the public library are all version-controlled and linked.
- **Scale:** 56 isolated GCP runs are feeding the next public preprint and the Layer 2 research paper.

---

## Social media thread (ready to post)

```text
1/ We just shipped the Lupine refinement sprint: five formalization wins that make MLIP correction, transfer, sampling, optimization, and benchmarking more honest and rigorous.

2/ Theorem 1: a 1-D shared-error correction is *no-harm*. We proved in Lean that the corrected residual norm never exceeds the uncorrected one, then matched the Rust implementation to the proof.

3/ Theorem 2: rank-k alloy transferability. Projecting a target residual onto a source subspace leaves at most sin(θ_k)·‖target‖. Real-alloy LOOCV is now build-locked.

4/ Theorem 3: active sampling has a contract. Greedy residual-max selection is one-step optimal, and the number of informative observations is bounded by the residual subspace rank.

5/ Optimizer hardening: `mlip_optimize` now rejects Born-unstable fits, checks moduli consistency, refuses low R² surfaces, and reports a jackknife RMSE + optimality gap.

6/ Provenance tags: every benchmark entry is now synthetic / nistIpr / experiment, and the validation report warns if synthetic data is present. No more “synthetic fixture reported as empirical.”

7/ We are now running 56 concurrent GCP jobs for the 3×3×3 16-element universal-MLIP elastic-constant benchmark (M3GNet, CHGNet, TensorNet, QET × 14 metals).

8/ All theorems compile with zero `sorry`, and the Rust code passes `cargo test` + `cargo clippy -D warnings`.

9/ Read the public library: https://library.lupine.science
   Source: https://github.com/alexwelcing/lupine

10/ If you care about trustworthy materials ML, this is the kind of first-principles engineering that has to happen before high-stakes decisions. Thread. 🧵
```

---

## What changed in the repos

- `lean-spec/OpenDistillationFactory/Materials/Distillation/DirectionalCorrectionScheme.lean`
- `lean-spec/OpenDistillationFactory/Materials/Distillation/SubspaceCorrectionScheme.lean`
- `lean-spec/OpenDistillationFactory/Materials/Theory/AlloyResidualTransfer.lean`
- `lean-spec/OpenDistillationFactory/Materials/Theory/ActiveSampling.lean`
- `atlas-distill/src/commands/mlip_correct.rs`
- `atlas-distill/src/commands/mlip_optimize.rs`
- `atlas-distill/src/active_sampling.rs`
- `atlas-distill/src/manifold.rs`
- `atlas-distill/src/validation.rs`

All changes are live in `main` and mirrored to `lupine-rhizo` and `lupine-ledger`.

---

## Contact / how to follow

- Public library: <https://library.lupine.science>
- Source: <https://github.com/alexwelcing/lupine>
- This announcement: <https://library.lupine.science/articles/announcements/lupine-refinement-sprint-2026-06-27.html>
