# References — *The environment error field* manuscript

> Verified metadata for `environment-error-field-2026-07-02.md`. Every entry was
> confirmed this session (2026-07-02) by fetching the arXiv/DOI/publisher page or
> a search that returned an exact title+author+venue match. Each carries a
> one-line relevance note. Items that could not be verified are listed in
> §Unverified with what was found instead.
>
> Section counts: Foundation-MLIP lineage 10 · uMLIP benchmarks & datasets 10 ·
> Delta-ML / learned corrections 9 · Calibration & isotonic lineage 6 ·
> UQ for potentials & sloppy models 11 · Formal verification 7 ·
> Reference-data primaries 20 · Infrastructure 4. **Total 77 verified.**
> One item dropped (arXiv:2507.15190 — withdrawn on arXiv; see §Caution).

---

## 1. Foundation-MLIP architecture lineage

- **[behler2007]** J. Behler, M. Parrinello. *Generalized neural-network representation
  of high-dimensional potential-energy surfaces.* Phys. Rev. Lett. **98**, 146401 (2007).
  doi:10.1103/PhysRevLett.98.146401. — The origin of high-dimensional NN potentials; the
  atom-decomposed energy our correction also assumes.
- **[bartok2010]** A. P. Bartók, M. C. Payne, R. Kondor, G. Csányi. *Gaussian
  approximation potentials: the accuracy of quantum mechanics, without the electrons.*
  Phys. Rev. Lett. **104**, 136403 (2010). doi:10.1103/PhysRevLett.104.136403. — GAP; the
  kernel-based root of modern data-driven potentials.
- **[thompson2015snap]** A. P. Thompson, L. P. Swiler, C. R. Trott, S. M. Foiles,
  G. J. Tucker. *Spectral neighbor analysis method for automated generation of
  quantum-accurate interatomic potentials.* J. Comput. Phys. **285**, 316–330 (2015).
  doi:10.1016/j.jcp.2014.12.018. — SNAP; bispectrum descriptors, a linear-model reference
  point.
- **[drautz2019ace]** R. Drautz. *Atomic cluster expansion for accurate and transferable
  interatomic potentials.* Phys. Rev. B **99**, 014104 (2019).
  doi:10.1103/PhysRevB.99.014104 (erratum: Phys. Rev. B **100**, 249901 (2019)). — ACE; the
  complete body-ordered basis underlying MACE.
- **[batzner2022nequip]** S. Batzner, A. Musaelian, L. Sun, et al. *E(3)-equivariant
  graph neural networks for data-efficient and accurate interatomic potentials.*
  Nat. Commun. **13**, 2453 (2022); arXiv:2101.03164. doi:10.1038/s41467-022-29939-5. —
  NequIP; equivariant message passing, the architectural parent of MACE.
- **[batatia2022mace]** I. Batatia, D. P. Kovács, G. N. C. Simm, C. Ortner, G. Csányi.
  *MACE: Higher order equivariant message passing neural networks for fast and accurate
  force fields.* Adv. Neural Inf. Process. Syst. **35** (NeurIPS 2022); arXiv:2206.07697. —
  The MACE architecture; two of our four models are MACE variants.
- **[batatia2024macemp]** I. Batatia, S. Benner, Y. Chiang, et al. *A foundation model for
  atomistic materials chemistry.* J. Chem. Phys. **163**(18), 184110 (2025); arXiv:2401.00096
  (2024). doi:10.1063/5.0297006. — MACE-MP-0; the specific foundation checkpoints we benchmark
  and correct (now journal-published — cite both).
- **[deng2023chgnet]** B. Deng, P. Zhong, K. Jun, et al. *CHGNet as a pretrained universal
  neural network potential for charge-informed atomistic modelling.* Nat. Mach. Intell.
  **5**, 1031–1041 (2023); arXiv:2302.14231. doi:10.1038/s42256-023-00716-3. — CHGNet 0.4.2;
  our most strongly softened model, the field's clearest signal.
- **[chen2022m3gnet]** C. Chen, S. P. Ong. *A universal graph deep learning interatomic
  potential for the periodic table.* Nat. Comput. Sci. **2**, 718–728 (2022); arXiv:2202.02450.
  doi:10.1038/s43588-022-00349-3. — M3GNet; a foundation uMLIP cited as part of the family.
- **[barrosoluque2024omat24]** L. Barroso-Luque, M. Shuaibi, X. Fu, et al. *Open Materials
  2024 (OMat24) inorganic materials dataset and models.* arXiv:2410.12771 (2024).
  doi:10.48550/arXiv.2410.12771. — OMat24; the training lineage that moves the field's
  prefactor toward identity (MACE-MPA-0).

## 2. uMLIP benchmarks, datasets, and softening/defect failure

- **[deng2024softening]** B. Deng, Y. Choi, P. Zhong, et al. *Systematic softening in
  universal machine learning interatomic potentials.* npj Comput. Mater. **11**, 9 (2025);
  arXiv:2405.07105 (arXiv title: *Overcoming systematic softening in universal MLIPs by
  fine-tuning*). doi:10.1038/s41524-024-01500-6. — Documents systematic under-prediction in
  MPtrj-trained uMLIPs and a single-additional-data-point correction; the correction our field
  contains as its zeroth mode. **Wording note:** the abstract states "fine-tuning with a single
  additional data point"; the exact phrase "linear rescaling" was not confirmed from the
  abstract — verify against full text before quoting it.
- **[chipsff2025]** D. Wines, K. Choudhary. *CHIPS-FF: evaluating universal machine learning
  force fields for material properties.* ACS Materials Lett. **7**(6), 2105–2114 (2025);
  arXiv:2412.10516. doi:10.1021/acsmaterialslett.5c00093. — 16-MLFF benchmark over 104 materials
  (elastic/phonon/defect/surface); cross-check for small-displacement degradation. (Venue is
  ACS Materials Letters, not npj.)
- **[focassio2025surfaces]** B. Focassio, L. P. M. Freitas, G. R. Schleder. *Performance
  assessment of universal machine learning interatomic potentials: challenges and directions
  for materials' surfaces.* ACS Appl. Mater. Interfaces **17**(9), 13111–13121 (2025);
  arXiv:2403.04217. doi:10.1021/acsami.4c03815. — Large surface-energy errors from bulk-dominated
  training; independent evidence of systematic surface error.
- **[thoms2025nickel]** M. Thoms, H. Sun, L. K. Béland. *Benchmarking 34 OpenKIM nickel
  potentials with an emphasis on surfaces and extended defects.* arXiv:2510.18033 (2025).
  doi:10.48550/arXiv.2510.18033. — 47-metric Ni suite; PCA over classical potentials warns of
  partially orthogonal error components (the closest prior cross-property study).
- **[matbenchdiscovery2025]** J. Riebesell, R. E. A. Goodall, P. Benner, et al. *A framework
  to evaluate machine learning crystal stability predictions.* Nat. Mach. Intell. **7**, 836–847
  (2025); arXiv:2308.14920. doi:10.1038/s42256-025-01055-1. — Matbench Discovery; the live
  leaderboard (matbench-discovery.materialsproject.org, confirmed) situating our four models.
- **[matpes2025]** A. D. Kaplan, R. Liu, J. Qi, et al. *A foundational potential energy surface
  dataset for materials.* arXiv:2503.04070 (2025). doi:10.48550/arXiv.2503.04070. — MatPES
  (~400k PBE+r2SCAN structures); the dataset-provenance context for the family-exponent
  training-lineage argument.
- **[steels2025]** A. Mohandas, S. Echeverri Restrepo, M. H. F. Sluiter. *Fine-tuning universal
  machine-learned interatomic potentials for applications in the science of steels.* J. Phase
  Equilib. Diffus. (online 2025 / print 2026). doi:10.1007/s11669-025-01225-z. — Fine-tuning
  CHGNet/SevenNet/MACE on Fe causes catastrophic forgetting; a learned-correction contrast
  point. (Distinct from Echeverri Restrepo et al. in Modelling Simul. Mater. Sci. Eng.)
- **[feni2026]** A. Ramakrishna, Lokamani, A. Cangi. *Can MACE potentials accurately describe
  magnetism and phase stability in Fe-Ni alloys? A systematic benchmark.* arXiv:2605.28395
  (2026). doi:10.48550/arXiv.2605.28395. — MACE fails high-pressure magnetic collapse and the
  Ni-content transition-pressure trend; supports our Fe deficiency finding (B₀ ≈ 80 vs 173 GPa).
- **[fttutorial2026]** Y. Liu, W. Zeng, X. Luo, et al. *Fine-tuning universal machine-learned
  interatomic potentials: a tutorial on methods and applications.* J. Appl. Phys. **139**,
  041101 (2026); arXiv:2506.21935. doi:10.1063/5.0299305. — MACE-MP-0 fine-tuning tutorial.
  **Correction:** case studies use **molybdenum** stacking faults/dislocations, **not Fe** — the
  manuscript's "MACE-MP Fe dislocations" description of arXiv:2506.21935 is mistaken; re-cite or
  re-describe.
- **[shuang2025defects]** F. Shuang, Z. Wei, K. Liu, W. Gao, P. Dey. *Universal machine
  learning interatomic potentials poised to supplant DFT in modeling general defects in
  metals and random alloys.* Mach. Learn.: Sci. Technol. **6**, 030501 (2025);
  arXiv:2502.03578. doi:10.1088/2632-2153/adea2d. — uMLIP defect-modeling survey; frames the
  practical stakes of defect accuracy.

## 3. Delta-ML and learned corrections (the critical prior-art axis)

- **[ramakrishnan2015]** R. Ramakrishnan, P. O. Dral, M. Rupp, O. A. von Lilienfeld.
  *Big data meets quantum chemistry approximations: the Δ-machine learning approach.*
  J. Chem. Theory Comput. **11**(5), 2087–2096 (2015); arXiv:1503.04987.
  doi:10.1021/acs.jctc.5b00099. — The canonical Delta-ML paper: learn E_target − E_baseline
  from many reference points. Our direct contrast (learned vs measured correction).
- **[bogojeski2020]** M. Bogojeski, L. Vogt-Maranto, M. E. Tuckerman, K.-R. Müller,
  K. Burke. *Quantum chemical accuracy from density functional approximations via machine
  learning.* Nat. Commun. **11**, 5223 (2020). doi:10.1038/s41467-020-19093-1. — Density-based
  Δ-DFT correcting DFT→CCSD(T) on-the-fly; a learned energy correction with symmetry data
  reduction.
- **[nandi2021]** A. Nandi, C. Qu, P. L. Houston, R. Conte, J. M. Bowman. *Δ-machine
  learning for potential energy surfaces: a PIP approach to bring a DFT-based PES to CCSD(T)
  level of theory.* J. Chem. Phys. **154**, 051102 (2021). doi:10.1063/5.0038301. — Delta-ML
  for PESs via permutationally-invariant polynomials; a force-bearing learned correction.
- **[zheng2021aiqm1]** P. Zheng, R. Zubatyuk, W. Wu, O. Isayev, P. O. Dral.
  *Artificial intelligence-enhanced quantum chemical method with broad applicability.*
  Nat. Commun. **12**, 7022 (2021). doi:10.1038/s41467-021-27340-2. — AIQM1: semiempirical
  baseline + NN correction; a deployed baseline-plus-correction analogue.
- **[smith2019ani1ccx]** J. S. Smith, B. T. Nebgen, R. Zubatyuk, et al. *Approaching coupled
  cluster accuracy with a general-purpose neural network potential through transfer learning.*
  Nat. Commun. **10**, 2903 (2019). doi:10.1038/s41467-019-10827-4. — Transfer-learning-as-
  correction (DFT→CCSD(T)); the fine-tune-to-correct paradigm we contrast on data cost.
- **[oneill2025]** N. O'Neill, B. X. Shi, W. Baldwin, et al. *Towards routine condensed-phase
  simulations with delta-learned coupled cluster accuracy: application to liquid water.*
  arXiv:2508.13391 (2025). doi:10.48550/arXiv.2508.13391. — Delta-learning on an MLP baseline
  to CCSD(T) for condensed matter; nearest modern learned-correction to our setting.
- **[kaur2025]** H. Kaur, F. Della Pia, I. Batatia, et al. *Data-efficient fine-tuning of
  foundational models for first-principles quality sublimation enthalpies.* Faraday Discuss.
  **256**, 120–138 (2025). doi:10.1039/D4FD00107A. — Few-tens-of-structures fine-tuning of
  MACE-MP-0; the low-data end of learned correction (still per-system, still trained).
- **[huang2025crossfunctional]** X. Huang, B. Deng, P. Zhong, A. D. Kaplan, K. A. Persson,
  G. Ceder. *Cross-functional transferability in universal machine learning interatomic
  potentials.* arXiv:2504.05565 (2025). doi:10.48550/arXiv.2504.05565. — Transfer of a uMLIP
  across DFT functionals via elemental referencing; a transferability-of-correction study
  adjacent to (but not answering) our cross-property question.
- **[radova2025]** M. Radova, W. G. Stark, C. S. Allen, R. J. Maurer, A. P. Bartók.
  *Fine-tuning foundation models of materials interatomic potentials with frozen transfer
  learning.* arXiv:2502.15582 (2025). doi:10.48550/arXiv.2502.15582. — Frozen-weight fine-tuning
  reaching chemical accuracy with 10–20% of the data; the low-data fine-tune-as-correction end.

## 4. Calibration and isotonic-regression lineage

- **[ayer1955]** M. Ayer, H. D. Brunk, G. M. Ewing, W. T. Reid, E. Silverman. *An empirical
  distribution function for sampling with incomplete information.* Ann. Math. Statist.
  **26**(4), 641–647 (1955). doi:10.1214/aoms/1177728423. — Origin of the pool-adjacent-
  violators algorithm; the isotonic machinery our monotone correction lives in.
- **[barlow1972]** R. E. Barlow, D. J. Bartholomew, J. M. Bremner, H. D. Brunk. *Statistical
  Inference Under Order Restrictions: The Theory and Application of Isotonic Regression.*
  Wiley (1972). — The isotonic-regression monograph; the nonparametric baseline our
  two-parameter law beats out-of-sample.
- **[platt1999]** J. C. Platt. *Probabilistic outputs for support vector machines and
  comparisons to regularized likelihood methods.* In *Advances in Large Margin Classifiers*
  (MIT Press, 1999), 61–74. — Platt scaling; the parametric calibration counterpart to output-
  space rescaling.
- **[zadrozny2002]** B. Zadrozny, C. Elkan. *Transforming classifier scores into accurate
  multiclass probability estimates.* Proc. 8th ACM SIGKDD (KDD '02), 694–699 (2002).
  doi:10.1145/775047.775151. — Isotonic calibration in ML; establishes monotone recalibration
  as standard practice.
- **[niculescu2005]** A. Niculescu-Mizil, R. Caruana. *Predicting good probabilities with
  supervised learning.* Proc. 22nd ICML (ICML '05), 625–632 (2005).
  doi:10.1145/1102351.1102430. — Platt-vs-isotonic empirical comparison; our LOO comparison
  mirrors its methodology.
- **[guo2017]** C. Guo, G. Pleiss, Y. Sun, K. Q. Weinberger. *On calibration of modern neural
  networks.* Proc. 34th ICML, PMLR **70**, 1321–1330 (2017). arXiv:1706.04599. — Temperature
  scaling; modern-NN miscalibration, the deep-learning face of the rescaling question.

## 5. UQ for potentials, sloppy models, and error geometry

- **[brown2003]** K. S. Brown, J. P. Sethna. *Statistical mechanical approaches to models with
  many poorly known parameters.* Phys. Rev. E **68**, 021904 (2003).
  doi:10.1103/PhysRevE.68.021904. — Founding "sloppy model" paper; the low-dimensional-error
  intuition we relocate from parameter to environment space.
- **[waterfall2006]** J. J. Waterfall, F. P. Casey, R. N. Gutenkunst, et al. *Sloppy-model
  universality class and the Vandermonde matrix.* Phys. Rev. Lett. **97**, 150601 (2006).
  doi:10.1103/PhysRevLett.97.150601. — Sloppiness as a universality class; why we expect the
  same geometry across models.
- **[transtrum2010]** M. K. Transtrum, B. B. Machta, J. P. Sethna. *Why are nonlinear fits to
  data so challenging?* Phys. Rev. Lett. **104**, 060201 (2010). arXiv:0909.3884.
  doi:10.1103/PhysRevLett.104.060201. — The model-manifold hyper-ribbon; our error field is
  its nonlinear, environment-space image.
- **[transtrum2011]** M. K. Transtrum, B. B. Machta, J. P. Sethna. *Geometry of nonlinear
  least squares with applications to sloppy models and optimization.* Phys. Rev. E **83**,
  036701 (2011). arXiv:1010.1449. doi:10.1103/PhysRevE.83.036701. — Differential-geometry
  treatment of the ribbon; the widths hierarchy we invoke.
- **[machta2013]** B. B. Machta, R. Chachra, M. K. Transtrum, J. P. Sethna. *Parameter space
  compression underlies emergent theories and predictive models.* Science **342**, 604–607
  (2013). arXiv:1303.6738. doi:10.1126/science.1238723. — Why low effective dimensionality is
  expected; the theoretical warrant for a single field per model–material.
- **[transtrum2015]** M. K. Transtrum, B. B. Machta, K. S. Brown, B. C. Daniels, C. R. Myers,
  J. P. Sethna. *Perspective: sloppiness and emergent theories in physics, biology, and
  beyond.* J. Chem. Phys. **143**, 010901 (2015). arXiv:1501.07668. doi:10.1063/1.4923066.
  — The canonical review of the paradigm.
- **[frederiksen2004]** S. L. Frederiksen, K. W. Jacobsen, K. S. Brown, J. P. Sethna.
  *Bayesian ensemble approach to error estimation of interatomic potentials.* Phys. Rev.
  Lett. **93**, 165501 (2004). doi:10.1103/PhysRevLett.93.165501. — The first ensemble error
  estimation for potentials; the direct ancestor of data-driven potential UQ.
- **[kurniawan2022]** Y. Kurniawan, C. L. Petrie, K. J. Williams, et al. *Bayesian,
  frequentist, and information geometric approaches to parametric uncertainty quantification
  of classical empirical interatomic potentials.* J. Chem. Phys. **156**, 214103 (2022).
  arXiv:2112.10851. doi:10.1063/5.0084988. — OpenKIM-based UQ comparison; closest prior art on
  potential parametric UQ.
- **[wen2020dropout]** M. Wen, E. B. Tadmor. *Uncertainty quantification in molecular
  simulations with dropout neural network potentials.* npj Comput. Mater. **6**, 124 (2020).
  doi:10.1038/s41524-020-00390-8. — Dropout UQ for NN potentials; the NN-era UQ counterpart.
- **[tran2020uq]** K. Tran, W. Neiswanger, J. Yoon, Q. Zhang, E. Xing, Z. W. Ulissi. *Methods
  for comparing uncertainty quantifications for material property predictions.* Mach. Learn.:
  Sci. Technol. **1**, 025006 (2020). arXiv:1912.10066. doi:10.1088/2632-2153/ab7e1a. —
  Calibration/sharpness metrics for materials ML; the evaluation frame for output-space UQ.
- **[pernot2022]** P. Pernot. *The long road to calibrated prediction uncertainty in
  computational chemistry.* J. Chem. Phys. **156**, 114109 (2022). arXiv:2201.01511.
  doi:10.1063/5.0084302. — Calibration-sharpness applied to computational chemistry; positions
  post-hoc calibration against our energy-space correction.

## 6. Formal / machine-checked verification

- **[demoura2021lean4]** L. de Moura, S. Ullrich. *The Lean 4 theorem prover and programming
  language.* Automated Deduction — CADE-28, LNCS **12699**, 625–635 (2021).
  doi:10.1007/978-3-030-79876-5_37. — The proof assistant our claims are sealed in.
- **[mathlib2020]** The mathlib Community. *The Lean mathematical library.* Proc. 9th ACM
  SIGPLAN CPP 2020, 367–381 (2020). doi:10.1145/3372885.3373824. — The library our decidable
  theorems build on.
- **[hales2017kepler]** T. Hales, et al. *A formal proof of the Kepler conjecture.* Forum of
  Mathematics, Pi **5**, e2 (2017). arXiv:1501.02155. doi:10.1017/fmp.2017.1. — Flyspeck; the
  landmark machine-checked proof of a physically-motivated statement (precedent for kernel-
  sealed claims, but pure math).
- **[gonthier2008fourcolor]** G. Gonthier. *Formal proof — the four-color theorem.* Notices
  Amer. Math. Soc. **55**(11), 1382–1393 (2008). — Coq-checked; the reference example of
  machine-checked computation-heavy proof.
- **[tucker2002lorenz]** W. Tucker. *A rigorous ODE solver and Smale's 14th problem.* Found.
  Comput. Math. **2**(1), 53–117 (2002). doi:10.1007/s002080010018. — Interval-arithmetic
  proof about a physical (Lorenz) model; the closest classical precedent for rigorous
  computation on scientific quantities.
- **[leanbet2026]** E. D. Ugwuanyi, C. T. Jones, J. Velkey, T. R. Josephson. *LeanBET:
  formally-verified surface area calculations in Lean.* arXiv:2605.16169 (2026). — The single
  genuine precedent: a Lean-4-verified empirical materials-characterization (BET) data-analysis
  pipeline, agreeing with the reference implementation to machine precision. Our workflow is the
  same pattern applied to benchmark claims.
- **[assemblytheory2026]** *A machine-checked formalization of assembly theory in Lean 4.*
  (2026; 157 verified declarations). — Formalizes the mathematical core of assembly theory but
  explicitly not its empirical/statistical claims; confirms the empirical-verification gap our
  paper targets. (arXiv ID pending; found via ResearchGate 2026.)

## 7. Reference-data primaries (Y-matrix targets)

- **[tran2016surfaces]** R. Tran, Z. Xu, B. Radhakrishnan, D. Winston, W. Sun, K. A. Persson,
  S. P. Ong. *Surface energies of elemental crystals.* Sci. Data **3**, 160080 (2016).
  doi:10.1038/sdata.2016.80. — DFT-PBE surface energies (Dryad doi:10.5061/dryad.f2n6f); the
  γ₁₀₀/γ₁₁₀/γ₁₁₁ reference targets.
- **[dejong2015elastic]** M. de Jong, W. Chen, T. Angsten, et al. *Charting the complete
  elastic properties of inorganic crystalline compounds.* Sci. Data **2**, 150009 (2015).
  doi:10.1038/sdata.2015.9. — DFT elastic tensors for 1,181 compounds; elastic-family reference
  source.
- **[angsten2014vacancy]** T. Angsten, T. Mayeshiba, H. Wu, D. Morgan. *Elemental vacancy
  diffusion database from high-throughput first-principles calculations for fcc and hcp
  structures.* New J. Phys. **16**, 015018 (2014). doi:10.1088/1367-2630/16/1/015018. — DFT-PBE
  vacancy formation energies; the E_vac anchor source.
- **[zhang2018solids]** G.-X. Zhang, A. M. Reilly, A. Tkatchenko, M. Scheffler. *Performance
  of various density-functional approximations for cohesive properties of 64 bulk solids.*
  New J. Phys. **20**, 063020 (2018). doi:10.1088/1367-2630/aac7f0. — Lattice constants and
  bulk moduli (PBE + Exp. columns); a₀ and B₀ reference targets.
- **[csonka2009solids]** G. I. Csonka, J. P. Perdew, A. Ruzsinszky, et al. *Assessing the
  performance of recent density functionals for bulk solids.* Phys. Rev. B **79**, 155107
  (2009). arXiv:0903.4037. doi:10.1103/PhysRevB.79.155107. — PBE lattice/B₀/cohesive-energy
  benchmark; secondary bulk reference.
- **[ma2019bcc]** P.-W. Ma, S. L. Dudarev. *Universality of point defect structure in
  body-centered cubic metals.* Phys. Rev. Materials **3**, 013605 (2019).
  doi:10.1103/PhysRevMaterials.3.013605. — DFT-PBE Cr/Fe lattice constants and vacancy energies
  (magnetic bcc); the magnetic-metal reference source.
- **[dewaele2019eos]** A. Dewaele. *Equations of state of simple solids (including Pb, NaCl and
  LiF) compressed in helium or neon in the Mbar range.* Minerals **9**(11), 684 (2019).
  doi:10.3390/min9110684. — Rydberg-Vinet EOS fits; the NaCl and elemental B₀/B₀′ reference.
- **[li2016sfe]** R. Li, S. Lu, D. Kim, S. Schönecker, J. Zhao, S. K. Kwon, L. Vitos.
  *Stacking fault energy of face-centered cubic metals: thermodynamic and ab initio
  approaches.* J. Phys.: Condens. Matter **28**, 395001 (2016); arXiv:1511.08634.
  doi:10.1088/0953-8984/28/39/395001. — EMTO-PBE fcc SFE values; γ_SFE reference.
- **[linda2024sfe]** A. Linda, M. F. Akhtar, S. Pathak, S. Bhowmick. *Accelerating the
  prediction of stacking fault energy by combining ab initio calculations and machine
  learning.* Phys. Rev. B **109**, 214102 (2024); arXiv:2405.04876.
  doi:10.1103/PhysRevB.109.214102. — VASP-PBE SFE values; secondary γ_SFE reference.
- **[kim2017enthalpy]** G. Kim, S. V. Meschel, P. Nash, W. Chen. *Experimental formation
  enthalpies for intermetallic phases and other inorganic compounds.* Sci. Data **4**, 170162
  (2017). doi:10.1038/sdata.2017.162. — Calorimetric ΔH_f dataset; the intermetallic formation-
  enthalpy targets.
- **[ward2012eam]** L. Ward, A. Agrawal, K. M. Flores, W. Windl. *Rapid production of accurate
  embedded-atom method potentials for metal alloys.* arXiv:1209.0619 (2012). — arXiv-only;
  tabulates NiAl/Ni₃Al lattice, elastic, and APB reference values used in the intermetallics
  targets.
- **[chen2022apb]** E. Chen, A. Tamm, T. Wang, M. E. Epler, M. Asta, T. Frolov. *Modeling
  antiphase boundary energies of Ni₃Al-based alloys using automated density functional theory
  and machine learning.* npj Comput. Mater. **8**, 80 (2022). doi:10.1038/s41524-022-00755-1.
  — DFT-PBE APB energies for Ni₃Al; planar-fault reference for the L1₂ intermetallic.
- **[tysonmiller1977]** W. R. Tyson, W. A. Miller. *Surface free energies of solid metals:
  estimation from liquid surface tension measurements.* Surf. Sci. **62**(1), 267–276 (1977).
  doi:10.1016/0039-6028(77)90442-3. — Experimental polycrystalline surface energies; the
  experiment-column surface reference.
- **[vitos1998surfaces]** L. Vitos, A. V. Ruban, H. L. Skriver, J. Kollár. *The surface energy
  of metals.* Surf. Sci. **411**(1-2), 186–202 (1998). doi:10.1016/S0039-6028(98)00363-X. —
  FCD-LMTO surface-energy database for 60 metals; the compilation the experiment column is read
  from.
- **[ehrhart1991]** P. Ehrhart, P. Jung, H. Schultz; H. Ullmaier (ed.). *Atomic Defects in
  Metals.* Landolt-Börnstein New Series Group III, Vol. 25 (Springer, Berlin, 1991).
  doi:10.1007/b37800. — Evaluated experimental vacancy formation energies; the experiment-column
  vacancy reference.
- **[young2016isotherms]** D. A. Young, H. Cynn, P. Söderlind, A. Landa. *Zero-Kelvin
  compression isotherms of the elements 1 ≤ Z ≤ 92 to 100 GPa.* J. Phys. Chem. Ref. Data **45**,
  043101 (2016). doi:10.1063/1.4963086. — Evaluated 0 K P–V isotherms; Cr B₀ reference.
- **[dannefaer1986]** S. Dannefaer, P. Mascher, D. Kerr. *Monovacancy formation enthalpy in
  silicon.* Phys. Rev. Lett. **56**, 2195–2198 (1986). doi:10.1103/PhysRevLett.56.2195. —
  Positron-lifetime Si vacancy enthalpy (3.6 ± 0.2 eV); the Si defect reference.
- **[dorfman2012]** S. M. Dorfman, V. B. Prakapenka, Y. Meng, T. S. Duffy. *Intercomparison of
  pressure standards (Au, Pt, Mo, MgO, NaCl, and Ne) to 2.5 Mbar.* J. Geophys. Res. **117**,
  B08210 (2012). doi:10.1029/2012JB009292. — MgO reference-volume anchor for the oxide EOS.
- **[nashkleppa2001]** P. Nash, O. J. Kleppa. *Composition dependence of the enthalpies of
  formation of NiAl.* J. Alloys Compd. **321**(2), 228–231 (2001).
  doi:10.1016/S0925-8388(01)00952-5. — Direct-synthesis calorimetry ΔH_f(NiAl); the B2-NiAl
  formation-enthalpy reference. **Scope note: covers NiAl only, not Ni₃Al.**
- **[rusovic1977]** N. Rusović, H. Warlimont. *The elastic behaviour of β2-NiAl alloys.*
  Phys. Status Solidi A **44**(2), 609–619 (1977). doi:10.1002/pssa.2210440225. — Single-crystal
  elastic constants of B2-NiAl; the intermetallic B₀ reference.

## Infrastructure

- **[karls2020openkim]** D. S. Karls, M. Bierbaum, A. A. Alemi, R. S. Elliott, J. P. Sethna,
  E. B. Tadmor. *The OpenKIM processing pipeline: a cloud-based automatic material property
  computation engine.* J. Chem. Phys. **153**, 064104 (2020). doi:10.1063/5.0014267. — The
  reproducible property-computation pipeline model; OpenKIM UQ/verification context.
- **[tadmor2011openkim]** E. B. Tadmor, R. S. Elliott, J. P. Sethna, R. E. Miller, C. A.
  Becker. *The potential of atomistic simulations and the Knowledgebase of Interatomic Models.*
  JOM **63**(7), 17–17 (2011). doi:10.1007/s11837-011-0102-6. — Introduces OpenKIM; the
  standardized archiving/verification framework our workflow generalizes.
- **[lammps2022]** A. P. Thompson, H. M. Aktulga, R. Berger, et al. *LAMMPS — a flexible
  simulation tool for particle-based materials modeling at the atomic, meso, and continuum
  scales.* Comput. Phys. Commun. **271**, 108171 (2022). doi:10.1016/j.cpc.2021.108171. — The
  MD engine our run-time correction deploys in.
- **[zhou2004eam]** X. W. Zhou, R. A. Johnson, H. N. G. Wadley. *Misfit-energy-increasing
  dislocations in vapor-deposited CoFe/NiFe multilayers.* Phys. Rev. B **69**, 144113 (2004).
  doi:10.1103/PhysRevB.69.144113. — Source of the Zhou EAM parameterizations (16 metals); the
  classical potential that beats CHGNet on 20/24 matched surface cells (§3.6).

---

## Caution / needs correction (honest flags)

- **[residual2025] — DROPPED. arXiv:2507.15190** (Nong, Zhu, Ren, et al., *Energy
  underprediction from symmetry in machine-learning interatomic potentials*, 2025) **is marked
  WITHDRAWN on arXiv (v2, 13 Nov 2025).** It should not be cited as support. The manuscript's
  §Introduction / §3.3 claim that "a symmetry-related residual survives OMat24 training"
  (arXiv:2507.15190) needs a different source or must be softened — and the abstract did not
  mention OMat24, so even the paraphrase was unconfirmed. Recommend removing this citation and
  re-grounding the residual-softening remark on **[deng2024softening]** + our own R2 measurement.
- **[fttutorial2026] (arXiv:2506.21935)** is a fine-tuning tutorial whose case studies use
  **molybdenum**, not Fe dislocations. The manuscript's description "MACE-MP Fe dislocations"
  is wrong; correct the description or drop the reference.
- **[deng2024softening]** — verify the exact correction wording ("linear rescaling" vs
  "single-additional-data-point fine-tuning") against the full text before the positioning draft
  asserts "global linear force rescale." The positioning note in `prior-art-positioning.md`
  hedges this accordingly.
- **[nashkleppa2001]** verified for **NiAl** composition only — any Ni₃Al value attributed to it
  in `data/y_matrix_targets/intermetallics.json` should be re-sourced.
- **[ehrhart1991]** editor is **H. Ullmaier** (Ehrhart/Jung/Schultz are chapter authors); some
  `data/y_matrix_targets` citations list them as editors.
- **[ward2012eam]** never journal-published — cite as arXiv:1209.0619 (2012), not a journal.
- **[assemblytheory2026]** exact arXiv ID not pinned this session (title and 157-declaration
  claim confirmed via ResearchGate/search); verify the arXiv number before final submission.
