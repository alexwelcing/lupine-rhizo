> **Provenance:** hermes kanban task `t_46e55864` (researcher profile, 2026-07-20) — posted as a comment per the durability rule after t_dc3e11a8's digest died with its workspace. Materialized verbatim by director.

# Certified inference for machine-learned interatomic potentials

**Scope:** 2022–2026 literature on uncertainty-triggered abstention, physical consistency at prediction time, and gate cost, with emphasis on work from the United States and China.  
**Evidence cut:** 2026-07-20.  
**Provenance rule:** Quantitative statements below come from the cited paper text or tables. “Derived” statements are simple consequences explicitly labeled as such. All arXiv citations retain the version actually read. PDFs for every item in the References were accessed locally; no unaccessed item is used as evidence.

## Executive result

The literature supports **per-structure/per-step gating**, but not yet a certified end-to-end MLIP runtime. Three findings matter for Lupine:

1. **A raw uncertainty score is not a refusal certificate.** Deep-ensemble variance can be badly overconfident under physical distribution shift: in a 30-member NequIP ensemble, defect formation-energy errors were around 1 eV and the DFT vacancy value was never inside the reported uncertainty interval [3]. Conformal calibration supplies finite-sample marginal coverage only under exchangeability/i.i.d. conditions; it does not certify a particular MD step or an adaptive trajectory [1,4].
2. **Coverage has a severe selectivity cost.** In the 3BPA study, near-unit true-positive rate and positive predictive value were simultaneously obtainable only with an uncertainty cutoff around the 30th percentile, thereby sending a majority of structures to DFT [2]. A useful refusal gate therefore needs an explicit risk–abstention curve, not only an AUROC or uncertainty/error correlation.
3. **The gate can dominate the model.** Latent-distance conformal inference ranged from 1.14% to 185% of one neural-network forward pass on QM9 as latent width grew from 8 to 64; at OC20 scale it cost 150 forward passes for a lightweight SNN and seven forward passes for GemNet-OC [1]. Conversely, single-pass GMM/evidential heads avoid an ensemble multiplier [2,6], but their outputs still need calibration and shift tests.

No paper located in the scoped search reports a **Lean/Coq/Isabelle-checked MLIP prediction pipeline**, a proved abstention gate, or machine-checked non-interference between a gate and accepted predictions. That is a genuine opening for the Lupine program.

## Mechanism / cost / coverage evidence

| Mechanism and locus | Geography | What is guaranteed or tested | Measured coverage / error–abstention tradeoff | Measured runtime cost | Runtime interpretation for a refusal gate |
|---|---|---|---|---|---|
| Latent- or feature-distance score + split conformal calibration [1] | US (Georgia Tech, Carnegie Mellon) | Marginal finite-sample coverage under i.i.d./exchangeability; no conditional or trajectory guarantee | On QM9, CP observed coverage stayed within 3 percentage points of nominal over broad hyperparameters; calibration-curve area was 0.008 (feature) and 0.009 (latent), versus 0.099 for an ensemble. At 95% coverage, latent distance was sharper than feature distance: 99.85 vs 111.30 meV/system. | QM9 CP cost: 0.0338, 0.3057, 0.8536, 4.4968 ms/image for latent widths 8, 16, 32, 64, respectively—1.14%, 9.94%, 27.0%, 185% of a forward pass. OC20: 106 ms/image for SNN (23% of fingerprint cost, ~150 forward passes); 378 ms/image for GemNet-OC (~7 forward passes). | Strong calibration layer for an already meaningful score. Per-step nearest-neighbor lookup can be negligible, comparable to, or dominant over the MLIP depending on descriptor cost and latent width. |
| Single-backbone Gaussian mixture model (GMM) on NequIP latent features [2] | US (Harvard/Bosch) | Empirical ranking/classification of high-force-error atoms; no formal coverage | GMM ranking was comparable to 10-network ensembles. Near-unit TPR and PPV together required a cutoff near the 30th uncertainty percentile, marking a majority for DFT. Active-learning gains were comparable to ensembles; some >200 meV/Å outlier RMSEs fell by >100 meV/Å. | One backbone instead of 10; authors report order-of-magnitude lower uncertainty cost. | Cheap enough for each MD step, but the measured abstention burden can overwhelm throughput through downstream DFT calls even when gate evaluation is cheap. |
| Equivariant neural-network ensemble disagreement [3] | China + Germany (Southeast University/NOMAD) | Empirical standard deviation only; no calibrated bound | Converged ensemble variance required ~30 members. Vacancy/interstitial errors were around 1 eV, and the DFT vacancy value was never inside the uncertainty interval. A ~2 meV/atom liquid-domain threshold would trigger retraining for all tested solid/defect cases, including some accurate ones. | Thirty model evaluations for converged variance; a four-member estimate differed by a multiplicative factor 2–2.5 from the plateau. | Direct evidence against treating committee spread as a sound refusal verdict under physical shift. It can be both unsafe (false accept) and nonselective (false refuse). |
| ACE parameter ensembles propagated through downstream silicon quantities + conformal rescaling [4] | UK | Approximate 95% marginal coverage on mixed atomic observations; propagated intervals for bulk modulus, elastic constants, vacancy energy, and migration barrier | With desired 95% coverage over energies, forces, and virials, energy-only coverage was 88% and 83% for two ACE models. Protocol used 100 ensemble members and a 72:8:20 train/calibrate/test split. Vacancy-energy half-width reached ±0.036 eV at polynomial degree 26, but the most complex overfit models lost coverage. | No wall-time benchmark reported; 100 complete potential evaluations per quantity-of-interest calculation. | Calibrating the observation vector does not imply per-channel or per-QoI coverage. A gate must name the licensed observable and calibration population exactly. |
| Misspecification-aware POPS ensemble [5] | US + France (Los Alamos/CNRS) | Empirical bounds designed to retain finite parameter spread under model misspecification | A 500-model qSNAP ensemble failed to bound test energies in 2.1% and forces in 3.3% of cases. Across the paper’s property suite, reported bounds contained all direct-DFT targets; MACE-MPA-0 energy errors across Materials Project were also bounded. These are empirical results, not a distribution-free theorem. | Building POPS cost ~2× scikit-learn Bayesian ridge; resampling the hypercube is O(P). Runtime propagation used 500 models unless implicit differentiation was used; no per-MD-step wall time reported. | Important separation: epistemic/data UQ alone misses model-form error. A runtime certificate should have a misspecification component or an explicit “unlicensed under shift” branch. |
| Evidential interatomic potential (eIP): one equivariant backbone predicts a Normal–Inverse-Gamma uncertainty distribution, with locality, directionality, and quantile regression [6] | China (Shanghai AI Lab, CAS, Zhejiang, Fudan, CUHK, ShanghaiTech) | Empirical OOD ranking and real-time UQ; no conformal coverage theorem | On silica, eIP reportedly exceeded the ensemble on ROC-AUC while maintaining low force error; exact silica figure values were not printed in the machine-readable text. For the universal MPtrj-trained potential, the printed Spearman coefficient was 0.76 and ROC-AUC was 0.914. | One forward pass. Four-model ensemble required 4× training; MC dropout required four inference runs. eIP training/inference time was reported comparable to a normal MLIP. | Best scoped evidence that a gate head can run every step without a committee. It still needs external calibration and adversarial physical-shift evaluation before it can license acceptance. |
| Energy-derived conservative forces and strain-derived stress; NVE energy-conservation audit [7] | US (Meta FAIR) | Architectural identity `F = -∇E`; stress as an energy derivative. NVE audit tests smoothness/bounded derivatives but does not prove them. | Audit averaged 81 inorganic and seven molecular NVE trajectories, each 100 ps. Direct-force Orb, eqV2, and CHGNet failed the conservation test; eSEN computes force/stress by backpropagation and was conservative up to numerical accuracy. | No cost of running the audit inline was reported. Conservative force evaluation needs a backward pass; direct-force prediction is faster but produced significant energy drift. | Enforce identities by construction where possible; use runtime audits for implementation/numerical failures. A cell-level gate can refuse direct-force or nonsmooth models before evaluating scientific claims. |
| Free-energy-first thermodynamics-consistent GNN [8] | Germany; adjacent thermodynamic-property literature, not an MLIP | Activity coefficients are derivatives of predicted excess Gibbs energy; Gibbs–Duhem consistency is imposed by construction | Gibbs–Duhem RMSE was exactly 0 on internal and external composition tests. Prediction RMSE was 0.068 on composition interpolation; on mixture extrapolation, consistency-preserving GE-GNN RMSE was 0.114 versus 0.105 for the best soft-constrained model. | No inference overhead reported; automatic differentiation is required. | Direct analogue for thermodynamic gates: derive observables from one scalar potential rather than post-hoc clipping inconsistent outputs. Shows a small accuracy/constraint tradeoff under mixture extrapolation. |

## What “abstention” currently means in atomistic ML

The literature rarely uses selective-prediction terminology. Operationally, the common loop is:

1. evaluate the MLIP and an uncertainty score at an integration step;
2. compare the score with a threshold;
3. if low, advance MD; if high, invoke DFT, add the structure, and retrain [2].

This is an **action policy**, not a statistical certificate. A threshold calibrated on exchangeable static structures can lose its meaning because an MD trajectory is dependent and because the gate changes which states are visited and labeled. Likewise, aggregate system-level energy coverage does not imply atom-level force coverage, and joint energy/force/virial coverage does not imply coverage of any one channel [4]. Lupine’s license should therefore bind:

- the model and weights hash;
- the observable (energy, force component, stress, or downstream quantity);
- the structural population and shift tests;
- the calibration set and nominal risk;
- the action on refusal;
- a cost budget and maximum allowed refusal rate.

## Physics-constraint enforcement at inference

### Constraints available by construction

- **Euclidean symmetry:** equivariant architectures make scalar energy invariant and vector/tensor features transform correctly. MACE explicitly uses O(3)-equivariant messages, while ACE includes SOAP as a special case of its invariant local representations [9]. This is an architectural guarantee modulo implementation and floating-point behavior, not a proof about learned accuracy.
- **Conservative forces:** computing `F = -∇E` prevents the model from emitting an independently inconsistent force field [7]. It is necessary but not sufficient for stable long-time MD: cutoff discontinuities, discretized spherical grids, and unbounded/high-order derivatives can still create energy drift.
- **Virial/stress consistency:** for periodic systems, stress can be obtained as the derivative of the same energy with respect to lattice parameters [7]. This is stronger than separately predicting stress and checking it afterward.
- **Thermodynamic differential consistency:** predicting a fundamental free energy and deriving activity coefficients by automatic differentiation produced zero Gibbs–Duhem residual in the evaluated GE-GNN [8]. This is outside MLIP proper but is the clearest 2022–2026 analogue for a hard thermodynamic constraint.

### Runtime checks that complement construction

A lightweight gate can check finiteness, permutation/rotation covariance on sampled transforms, force-sum/torque residuals, energy–force finite differences, and stress–strain finite differences. However, the scoped papers provide **no measured per-step overhead** for these checks and no theorem that a finite test implies the global identity. Expensive checks (finite differences, duplicated symmetry transforms, short NVE rollouts) are better treated as periodic audits or cell-entry checks; cheap algebraic checks can run every step.

Contact theorems were not found as runtime constraints in the scoped MLIP literature. They remain domain-specific validation targets for interfacial-fluid models rather than established universal MLIP gates.

## Runtime cost curve and dominance regimes

Measured evidence supports four regimes:

1. **Head-negligible:** eIP and a narrow (8–16 dimensional) CP latent head add approximately one-pass/no-noticeable cost or 1.14–9.94% of a forward pass [1,6].
2. **Comparable:** a 32-dimensional CP head cost 27% of a forward pass; a 64-dimensional head cost 185%, so the gate alone exceeded the predictor [1].
3. **Gate-dominant for fast backbones:** OC20 SNN latent search cost ~150 neural forward passes, although only 23% of the much more expensive fingerprint calculation [1]. What dominates depends on whether the descriptor is cached/shared.
4. **Committee-dominant:** 10- and 30-member ensembles imply approximately 10 and 30 model evaluations per step (derived from member count, ignoring batching), and 100- or 500-member propagated ensembles are not plausible as ordinary per-step MD gates [2–5].

The larger systems question is not just gate evaluation. At the reported 30th-percentile cutoff, **more than 70% sent to DFT is the derived fallback rate** (the paper itself says “a majority”) [2], so fallback dominates wall time by design. Thus the required benchmark is a three-part cost curve:

`total wall time = MLIP time + gate time + refusal_rate × fallback_cost`.

Papers usually report only the first two terms or active-learning quality, not the end-to-end curve.

## Gaps

1. **No machine-checked runtime:** no scoped paper couples an MLIP to a proof assistant, verifies the executed floating-point gate, or proves non-interference of accepted predictions.
2. **No trajectory-valid conformal guarantee:** published CP guarantees are marginal under exchangeability, while adaptive MD is dependent and gate-conditioned.
3. **Sparse selective-risk reporting:** one strong TPR/PPV result [2] exposes majority abstention, but coverage-versus-abstention curves and risk at fixed coverage are generally absent.
4. **Almost no in-loop wall-time data:** [1] is the exception. Most papers report member counts or qualitative “single pass” claims, not ns/day loss, hardware, batch size, system size, and fallback burden.
5. **Constraint checks are architecture claims, not certificates:** symmetry and derivative construction are strong, but implementation, neighbor-list discontinuities, precision, and integrator behavior are not formally linked.
6. **Stress/virial and contact constraints are underdeveloped as gates:** the literature trains on or differentiates virials but does not publish calibrated abstention rules for stress inconsistency or contact-theorem violations.
7. **Descriptor naming ambiguity:** the scoped search found ACE, SOAP, latent-distance, GMM, and D-optimality approaches, but no verifiable 2022–2026 MLIP UQ paper with a method explicitly named “DACE.” This digest does not silently expand or conflate that acronym; the intended DACE citation needs confirmation.

## Hypotheses for the Lupine program

1. **Two-stage gates will dominate single scores.** A cheap single-pass epistemic head (eIP/GMM) should screen every step; only borderline cells should pay for latent-distance CP, symmetry duplicates, or finite-difference audits. This should preserve most of the safety gain below the 27–185% gate-cost transition measured for wider latent spaces.
2. **Refusal licenses should be observable-specific.** Separate conformalizers for energy, force, and stress will give narrower and more truthful licenses than one joint score, because 95% joint energy/force/virial calibration yielded only 83–88% energy coverage in [4].
3. **Misspecification needs an independent veto.** Ensemble spread or evidential uncertainty should not license a structure when descriptor/domain or POPS-style model-form checks fail; the Si vacancy result—an error around 1 eV with the DFT value never inside the ensemble interval—is the key falsification target [3].
4. **A proved non-interference wrapper is publishably novel.** Formalize that the gate can only return `accept(original_prediction)` or `refuse`, never alter the accepted energy/force/stress payload. Combine that proof with hash-bound model/calibration artifacts and empirical coverage evidence. The literature has neither this theorem nor an equivalent machine-checked pipeline.
5. **Cost-optimal gating will be dominated by fallback rate, not arithmetic.** Optimize thresholds against `MLIP + gate + refusal × fallback` wall time and require a preregistered maximum false-accept risk. The 3BPA majority-refusal result predicts that improving score separation is more valuable than micro-optimizing an already single-pass gate.

## References

1. Y. Hu, J. Musielewicz, Z. W. Ulissi, and A. J. Medford, “Robust and scalable uncertainty estimation with conformal prediction for machine-learned interatomic potentials,” *Machine Learning: Science and Technology* **3**, 045028 (2022). DOI: [10.1088/2632-2153/aca7b1](https://doi.org/10.1088/2632-2153/aca7b1). arXiv: [2208.08337v2](https://arxiv.org/abs/2208.08337v2). **Accessed:** full arXiv v2 PDF.
2. A. Zhu, S. Batzner, A. Musaelian, and B. Kozinsky, “Fast uncertainty estimates in deep learning interatomic potentials,” *The Journal of Chemical Physics* **158**, 164111 (2023). DOI: [10.1063/5.0136574](https://doi.org/10.1063/5.0136574). arXiv: [2211.09866v1](https://arxiv.org/abs/2211.09866v1). **Accessed:** full arXiv v1 PDF.
3. S. Lu, L. M. Ghiringhelli, C. Carbogno, J. Wang, and M. Scheffler, “On the Uncertainty Estimates of Equivariant-Neural-Network-Ensembles Interatomic Potentials” (2023). arXiv: [2309.00195v1](https://arxiv.org/abs/2309.00195v1). Data DOI: [10.17172/NOMAD/2023.08.25-1](https://doi.org/10.17172/NOMAD/2023.08.25-1). **Accessed:** full arXiv v1 PDF; no journal DOI located, so this is cited as a preprint.
4. I. R. Best, T. J. Sullivan, and J. R. Kermode, “Uncertainty quantification in atomistic simulations of silicon using interatomic potentials,” *The Journal of Chemical Physics* **161**, 064112 (2024). DOI: [10.1063/5.0214590](https://doi.org/10.1063/5.0214590). arXiv: [2402.15419v1](https://arxiv.org/abs/2402.15419v1). **Accessed:** full arXiv v1 PDF.
5. D. Perez, A. P. A. Subramanyam, I. Maliyov, and T. D. Swinburne, “Uncertainty quantification for misspecified machine learned interatomic potentials,” *npj Computational Materials* **11**, 263 (2025). DOI: [10.1038/s41524-025-01758-4](https://doi.org/10.1038/s41524-025-01758-4). arXiv: [2502.07104v2](https://arxiv.org/abs/2502.07104v2). **Accessed:** full arXiv v2 PDF.
6. H. Xu, T. Cui, C. Tang, J. Ma, D. Zhou, Y. Li, X. Gao, X. Gong, W. Ouyang, S. Zhang, and M. Su, “Evidential deep learning for interatomic potentials,” *Nature Communications* **17**, 937 (2026; published online 20 December 2025). DOI: [10.1038/s41467-025-67663-y](https://doi.org/10.1038/s41467-025-67663-y). arXiv: [2407.13994v2](https://arxiv.org/abs/2407.13994v2). **Accessed:** full arXiv v2 PDF.
7. X. Fu, B. M. Wood, L. Barroso-Luque, D. S. Levine, M. Gao, M. Dzamba, and C. L. Zitnick, “Learning Smooth and Expressive Interatomic Potentials for Physical Property Prediction,” *Proceedings of the 42nd International Conference on Machine Learning*, PMLR **267**, 17875–17893 (2025). arXiv: [2502.12147v2](https://arxiv.org/abs/2502.12147v2). **Accessed:** full arXiv v2 PDF.
8. J. G. Rittig and A. Mitsos, “Thermodynamics-consistent graph neural networks,” *Chemical Science* **15**, 18504–18512 (2024). DOI: [10.1039/D4SC04554H](https://doi.org/10.1039/D4SC04554H). arXiv: [2407.18372v1](https://arxiv.org/abs/2407.18372v1). **Accessed:** full arXiv v1 PDF. **Scope note:** adjacent mixture-thermodynamics work, not an interatomic-potential paper.
9. I. Batatia, D. P. Kovács, G. N. C. Simm, C. Ortner, and G. Csányi, “MACE: Higher Order Equivariant Message Passing Neural Networks for Fast and Accurate Force Fields,” *Advances in Neural Information Processing Systems* **35** (2022). arXiv: [2206.07697v2](https://arxiv.org/abs/2206.07697v2). **Accessed:** full arXiv v2 PDF.

## Accessed-source integrity

The following SHA-256 digests identify the full PDFs used for this review. They were downloaded from the arXiv records linked above and converted with `pdftotext -layout` for claim-level search.

| Reference | Source artifact | SHA-256 |
|---|---|---|
| [9] | `2206.07697.pdf` | `3c4497aa9e90758797f6a846e700843c30496f193d2290cb4d54bc774a83a438` |
| [1] | `2208.08337.pdf` | `bb05779cd4429af86078be1b2e5fa4cdf123e97437451844e354ffc032d6e831` |
| [2] | `2211.09866.pdf` | `a8dd9cd744d6f72f07adbae35b31630aa6bff98791ba734eb18c85fc93c40594` |
| [3] | `2309.00195.pdf` | `5ff24505b0070996c815e3ea33a7d5fdd32dd9db00c4f3269c189ede9372ae38` |
| [4] | `2402.15419.pdf` | `de205c33fefc3ade3ec2c49c9fbbbf7c761ed90610757f0ca6e02443cdbcd32d` |
| [6] | `2407.13994.pdf` | `db645e9ae45cd046ea4f4cb0f0609ee75fa6745dd4bd3b5453e96692db93d4da` |
| [8] | `2407.18372.pdf` | `d46394e2c5207665ffb09e0eaddfd8b4a7e78642acf81adb7782d044a7f25885` |
| [5] | `2502.07104.pdf` | `2984365dcf44706e4ba132d75db1f91eb6976e571983d8347b7654ddf0123b9f` |
| [7] | `2502.12147.pdf` | `a82d5909a6b0a19d8a057fa33360c54fbfb0239bd5d210236359a0a5a1044c81` |

DOI metadata (title, journal, volume, article/page, and publication date) was cross-checked against the Crossref API on the evidence-cut date. Three DOI landing pages returned publisher anti-bot HTTP 403 responses to the automated link audit; their DOI records nevertheless resolved through Crossref, and matching arXiv full texts were accessed. The other 13 links checked by the same audit returned HTTP 200 after redirects.