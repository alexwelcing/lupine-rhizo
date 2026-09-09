# TMS 2027 Networking Brief — MLIP Landscape and Institution Map

Compiled 2026-09-09 (asOf date for all web-sourced claims unless noted). Quantitative
leaderboard data: Matbench Discovery snapshot captured 2026-09-09.[1] TMS logistics
verified against tms.org and ProgramMaster on 2026-09-09.[33][34][35] Claims that could
not be verified against a captured source in this sweep are marked [unverified] rather
than silently asserted.

---

# Part 1 — MLIP landscape review

## 1.0 How to read the current standings

Matbench Discovery has evolved into a multi-task benchmark (Discovery, Geometry
Optimization, Phonons, Molecular Dynamics, Diatomics presets) and now ranks models by
CPS (Combined Performance Score = F1 50% + kappa_SRME 40% + RMSD 10%).[1][2] The
leaderboard itself warns CPS is not a stable metric and recommends quoting the benchmark
version (CPS v1) when used in papers.[1]

Three structural facts dominate the September 2026 snapshot:[1]

1. **The OAM training mix rules the board.** The top 10 entries are all trained on the
   ~6.6M-crystal (113M-frame) "OAM" mix of MPtrj + OMat24 + sAlex. Data, not
   architecture, is currently the biggest single lever: the same architectures rank
   dramatically lower in their MPtrj-only variants (e.g. EquiformerV3+DeNS 0.902 OAM vs
   0.830 MPtrj; GRACE-2L 0.837 OAM vs 0.681 MPtrj; eSEN-30M 0.888 vs 0.797).[1]
2. **Discovery F1 has saturated near the ceiling.** Best F1 is 0.931
   (EquiformerV3+DeNS-OAM) with DAF ~6.07 against a theoretical maximum of ~6.54 given
   the 15.3% stable-crystal rate of the WBM unique-prototype test set.[1] Marginal GRR
   on the discovery task is now small; the frontier has moved to phonons
   (kappa_SRME), geometry robustness (RMSD), and MD stability.[1]
3. **Classic "household" universal potentials are now mid-table or worse.** MACE-MPA-0
   ranks 21st (CPS 0.795), MatterSim v1 5M 24th (0.767), MACE-MP-0 34th (0.637), M3GNet
   40th (0.428), CHGNet 41st (0.400) in the Discovery preset — all still usable, none
   competitive for discovery-style ranking tasks without fine-tuning.[1]

Caveat on absence: the leaderboard table virtualizes rows, so "model X is not on the
board" claims from a page-text search are inconclusive (a NequIP-GNoME row likewise
"disappeared" from a text search while being present in the captured table).[1]

## 1.1 Model-by-model review

### MACE family (MACE-MP-0, MACE-MPA-0, MACE-MP-0b)

- **Training data.** MACE-MP-0 (2023) trained on the MPtrj dataset (~146k relaxed
  structures, 1.58M frames) of Materials Project GGA/GGA+U trajectories;[1][4]
  MACE-MPA-0 (Dec 2024) on an enlarged ~3.5M-crystal mix of MPtrj + sAlex (~12M
  frames), which its release states achieves state-of-the-art Matbench accuracy at the
  time.[3][1]
- **Architecture.** Higher-order equivariant message passing built on the atomic
  cluster expansion (ACE) ideas of the "foundation model for atomistic materials
  chemistry" line (Batatia/Kovacs/Csanyi and co-workers).[4]
- **Benchmark standing.** MACE-MPA-0 CPS 0.795 (rank 21), F1 0.852, DAF 5.58; MACE-MP-0
  CPS 0.637 (rank 34), F1 0.669 — the latter now mostly of historical interest for
  discovery tasks. MACE-MP-0b was not visible in the captured Discovery view.[1]
- **License.** Code MIT. Foundation-model weights are licensed separately from code;
  the materials line (MP-0/MPA-0) is permissive and free for commercial use per
  third-party packaging docs.[76][3] [unverified for the exact weight-license text of
  every checkpoint]
- **Production readiness.** The most-deployed MLIP family in practice: first-class ASE
  integration, mature fine-tuning story (the MACE codebase is the standard
  fine-tuning substrate in the 2026 literature), small (4.7–9M) parameter counts that
  run on modest GPUs.[3][76][25]
- **Weaknesses.** No explicit long-range electrostatics/dispersion in the base MP
  models (the newer MACE-POLAR-1 line adds electrostatics [74]); local cutoff (6 A)
  limits ionic/layered systems; low-energy-configuration bias inherited from MPtrj
  relaxation data; kappa_SRME 0.412 shows phonon limitations versus 2026 leaders.[1][9][74]

### CHGNet

- **Training data.** MPtrj (146k structures / 1.58M frames), i.e. all GGA/GGA+U
  calculations from the September 2022 Materials Project.[23][24]
- **Architecture.** Graph neural network that is *charge-informed*: it predicts and
  consumes atomic magnetic moments as a proxy for charge state, enabling
  charge-constrained simulations and charge inference; supports energy/forces/stress/
  magmoms (EFSGM targets on the leaderboard).[21][22][24][1]
- **Benchmark standing.** CPS 0.400 (rank 41 of 42), F1 0.613 — discovery accuracy is
  obsolete by 2026 standards.[1]
- **License.** Open source, MIT-licensed repo (Ceder group / LBL).[23]
- **Production readiness.** ASE + LAMMPS interfaces, charge-informed MD via ASE out of
  the box; still the pragmatic choice when magnetic-moment/charge proxies matter more
  than leaderboard rank.[21][23]
- **Weaknesses.** Age shows in raw accuracy; small (413k params) capacity; magnetic
  moments are a proxy, not a physical charge model; trained only on PBE-level
  relaxation data.[1][24]

### M3GNet

- **Training data.** MPF-2021 (~62.8k structures / 188k frames) — Materials Project
  relaxations since 2012.[75][1]
- **Architecture.** Graph neural network with explicit three-body interactions; the
  original "universal graph deep learning interatomic potential for the periodic
  table" (Chen & Ong, UCSD).[75]
- **Benchmark standing.** CPS 0.428 (rank 40), F1 0.569; the 2022-era baseline
  everyone benchmarks against.[1]
- **License.** The standalone repo now lives under a commercial org (materialyzeai)
  after starting open; the maintained successor within the same ecosystem is the matgl
  package.[75] [unverified on current license terms]
- **Production readiness.** Widely integrated via matgl/ASE historically; superseded
  technically.[75]
- **Weaknesses.** Accuracy far below current SOTA; no stress/magmom sophistication;
  effectively legacy.[1]

### ORB family (Orbital Materials — Orb v2, Orb v3)

- **Training data.** Orb v2 MPA: MPtrj + Alex (~3.25M crystals / 32.1M frames); ORB v3:
  ~6.47M crystals (133M frames) of MPtrj + Alex + OMat24.[1]
- **Architecture.** Graph-transformer lineage (GemNet-style) with denoising-style
  auxiliary training; Orb v3 adds direct-force prediction with noise augmentation and
  PyTorch 2.6 compilation for large-batch GPU throughput — the release claims the
  performance-speed-memory Pareto frontier and stable mesoscale (million-atom)
  simulation.[5][6][7]
- **Benchmark standing.** ORB v3 CPS 0.860 (rank 14), F1 0.905, DAF 5.91; ORB v2 MPA
  CPS 0.528 — the v2 phonon penalty (kappa_SRME 1.734) was the famous weakness that
  v3 largely fixes (0.210).[1]
- **License.** Code and weights distributed via the orb-models repo; the team invites
  commercial engagement.[5] [unverified on the exact weights license — treat as
  commercial-friendly but confirm before production use]
- **Production readiness.** Best-in-class inference engineering (compile support,
  memory-lean batching for million-atom cells); pip-installable, ASE-compatible.[5][6][7]
- **Weaknesses.** kappa_SRME 0.210 still trails ACE-lineage leaders; direct-force
  (non-conservative-gradient) prediction can matter for some phonon/vibrational
  workflows; closed-company roadmap.[1][6]

### MatterSim (Microsoft Research)

- **Training data.** ~17M DFT-generated frames spanning wide temperature/pressure via
  a generative-sampling workflow over the potential-energy surface, explicitly
  targeting finite-T/P realism rather than only zero-K relaxations.[8][29]
- **Architecture.** Deep-learning atomistic model in the GNN-with-attention lineage
  (M3GNet-flavored backbone with graph attention); 5M-parameter released checkpoint.[8][1]
- **Benchmark standing.** MatterSim v1 5M CPS 0.767 (rank 24), F1 0.862, DAF 5.85 —
  mid-table on discovery, notable for its unusually high DAF per parameter.[1]
- **License.** MIT (code and repo), actively maintained with community engagement.[27]
- **Production readiness.** Microsoft-maintained docs and packaging, Azure-adjacent
  ecosystem; straightforward ASE-style use.[27][28]
- **Weaknesses.** 5M-param checkpoint underfits versus 2026 leaders; PBE-level labels;
  finite-T emphasis helps MD but not phonon ranking (kappa_SRME 0.575).[1] A MatterSim
  v2 was not verifiable in this sweep [unverified].

### GNoME-derived potentials (Google DeepMind data)

- **Training data.** NequIP-GNoME trained on the GNoME dataset (6M structures / 89M
  frames) of AI-discovered candidate crystals.[1]
- **Architecture.** NequIP E(3)-equivariant message passing fitted on GNoME
  data.[1][48]
- **Benchmark standing.** No CPS (missing kappa data); F1 0.829, DAF 5.52, Acc 0.948 —
  respectable discovery metrics, which was the headline finding that GNoME-style data
  transfers to stable-structure prediction.[1]
- **License / availability.** GNoME structures were released openly (via the GNoME
  dataset / Materials Project distribution); model fits are community artifacts rather
  than a supported product. [unverified on current distribution terms]
- **Production readiness.** Research artifact; not a maintained production path.
- **Weaknesses.** OOD-heavy training data means error geometry is uneven — exactly the
  regime where per-structure error prediction (the commissioning user's interest)
  matters most; no stress/phonon columns on the board.[1]

### PET-MAD (and the PET lineage)

- **Training data.** MAD combine: stable inorganic solids (MP + Alexandria organic
  subset) systematically modified to enhance atomic diversity; deliberately mixes
  inorganic and organic chemistry.[9][77]
- **Architecture.** Parallel Equivariant Transformer (PET) — attention-based
  equivariant architecture, ~3M parameters ("lightweight" is the paper's framing).[9]
- **Benchmark standing.** PET-MAD itself does not appear in the captured Discovery
  preset; a community OAM-trained PET-OAM-XL (730M params) ranks 5th with CPS
  0.898 — evidence the architecture scales, distinct from the official MAD
  checkpoint.[1]
- **License.** Open release with dataset on figshare/Springer Nature; code in the
  COSMO-lab ecosystem.[77] [unverified on exact license text]
- **Production readiness.** Small enough for laptop-class inference; LoRA fine-tuning
  demonstrated in the paper (the BTO dielectric-response experiment fine-tunes PET-MAD
  with LoRA); good few-shot adaptation substrate.[9]
- **Weaknesses.** Paper's own motivation: universal models are biased toward
  low-energy configurations; MAD diversity helps but kappa/phonon performance is
  unproven on the leaderboard; multi-domain training can dilute domain-specific
  accuracy.[9]

### SevenNet (SNU MDIL)

- **Training data.** SevenNet-0/l3i5 on MPtrj (146k/1.58M); SevenNet-Omni-i12
  (Jan 2026) on the 243M-frame COSMOSDataset — one of the largest training mixes on
  the board; Omni is multi-task across mpa (PBE+U), MatPES r2SCAN, OMol25
  (omegaB97M-V) and ~10 further task heads.[1][11][12]
- **Architecture.** NequIP-based scalable equivariant GNN, adapted for multi-GPU
  parallel MD; multi-task heads per dataset domain.[11][12]
- **Benchmark standing.** SevenNet-Omni-i12 CPS 0.873 (rank 11), F1 0.906; older
  SevenNet-l3i5 0.714 (rank 31).[1]
- **License.** Open-source repo; pretrained checkpoints documented in the
  docs.[11][12] [unverified on weight-license specifics]
- **Production readiness.** Multi-GPU MD is a first-class design goal; LAMMPS-adjacent
  workflows and ASE support documented.[11]
- **Weaknesses.** kappa_SRME 0.192 mid-pack; multi-task training across mixed DFT
  levels requires care at inference (task-head selection); SNU group pace means
  checkpoint lineage churn.[1][12]

### GRACE (GRACE-1L/2L/3L, GRACE-FS)

- **Training data.** Official GRACE-2L production models trained on their own
  curated DFT mix; the leaderboard's strong GRACE entries are OAM-mix fits
  (GRACE-3L-OAM-L rank 4, CPS 0.900; GRACE-2L-OAM-L rank 13, 0.865; GRACE-2L-OAM
  rank 17, 0.837) plus a new GRACE-FS (foundational) line with S/M/L variants.[1][61][62]
- **Architecture.** Graph Atomic Cluster Expansion: non-linear ACE on a graph —
  linear-cost evaluation with high body order, fitted via the gracemaker
  toolchain.[61][62][63]
- **Benchmark standing.** GRACE-3L-OAM-L CPS 0.900 with the best kappa_SRME of the top
  group after Equiformer (0.121 vs 0.118) and strong CMDS/CDS — the ACE lineage
  remains phonon-competitive at far lower cost than transformers.[1]
- **License.** gracemaker is documented open tooling; production GRACE-2L was released
  for community use. [unverified on license text; developed at Los Alamos National
  Laboratory per community knowledge — affiliation not captured this sweep]
- **Production readiness.** LAMMPS-centric (gracemaker integration), fast CPU/GPU
  evaluation, designed for production MD in metals/alloys; million-atom multicomponent
  alloy simulations demonstrated in the 2026 follow-up literature.[61][63]
- **Weaknesses.** Fixed-body-order descriptors cap expressivity on exotic chemistry;
  magnetic/charge physics not native; the OAM fits depend on Meta's OMat24 data
  provenance.[1][61]

### DeePMD / DPA-2, DPA-3, DPA-4 (DeepModeling / DP Technology)

- **Training data.** DPA-2 on multi-domain DeePMD data; DPA-3.1-3M on the OpenLAM
  dataset collection (163M frames on the leaderboard row); DPA-4.0.1-Pro on MPtrj —
  OpenLAM is the "conquer the periodic table" community data program.[1][67][68]
- **Architecture.** Deep Potential with attention-based descriptors and multi-task
  heads; DPA-3 introduced a new GNN "for the era of large atomistic models"; DeePMD-kit
  v3.2.0 (2026) introduces the DPA-4 family targeting accuracy and efficiency
  frontiers.[67][68][69]
- **Benchmark standing.** DPA-4.0.1-Pro-MPtrj CPS 0.840 (rank 15, June 2026);
  DPA-3.1-3M-FT CPS 0.802 (rank 19). DPA-2 itself is not on the captured Discovery
  view.[1]
- **License.** DeePMD-kit is open source (LGPL-family repo); models via deepmodeling
  community releases on Hugging Face.[15][68] [unverified on each checkpoint's terms]
- **Production readiness.** Arguably the deepest production MD stack in the field:
  LAMMPS-native, GPU-optimized, active-learning tooling (DeePMD-kit's on-the-fly
  learning), the AI for Science Institute Beijing ecosystem behind it.[15][68]
- **Weaknesses.** MPtrj-only DPA-4 entry trails OAM-mix models (data-bound, like
  everyone); multitask head selection complexity; kappa_SRME 0.211/0.469.[1]

### NequIP / Allegro (Harvard MIR group)

- **Training data.** Frameworks rather than fixed models; 2025-26 leaderboard
  instances are community fits: Nequip-OAM-XL (rank 9, CPS 0.886), Allegro-OAM-L
  (rank 16, 0.840), with weaker MPtrj-only fits (ranks 28/30).[1]
- **Architecture.** NequIP: E(3)-equivariant message passing (the original); Allegro:
  strictly local equivariant architecture optimized for GPU-parallel large-scale
  MD.[47][48][49]
- **Benchmark standing.** See above — architecture remains competitive when retrained
  on OAM data, confirming the data-over-architecture story.[1]
- **License.** MIT-family repos, well-documented extension ecosystem.[48][49]
- **Production readiness.** Mature training frameworks; Allegro's all-pair local
  design maps well to compiled GPU kernels; used widely for bespoke system-specific
  potentials.[48][49]
- **Weaknesses.** Locality (Allegro especially) limits long-range physics; frameworks
  need per-project training investment rather than drop-in universality; phonon
  metrics mid-pack (Allegro-OAM-L kappa 0.319).[1][49]

### AIMNet2 (CMU, Isayev lab)

- **Training data.** ~20M DFT calculations covering 14 chemical elements, spanning
  neutral and charged molecular species (anions/cations/zwitterions) in one
  model.[18][42]
- **Architecture.** Atoms-in-molecules neural network potential with implicit
  charge handling (NQC: neutral/quasi/charged species unified); 2025 checkpoint
  ensembles on Hugging Face (~9MB per ensemble member — genuinely tiny).[17][18]
- **Benchmark standing.** Molecular-domain model — not present (nor expected) on the
  periodic-table Discovery board.[1]
- **License.** Weights published via isayevlab Hugging Face; AIMNetCentral adds
  long-range electrostatics + D3 dispersion and simulation integrations.[17][44]
- **Production readiness.** High for molecular/chemistry workloads: tiny footprint,
  cloud inference options, AIMNetCentral simulation wrapper; NVIDIA NIM packaging
  references it.[44]
- **Weaknesses.** Not a periodic/solid-state potential; molecular training
  distribution; 14-element coverage only.[18]

### Meta FAIR: OMat24 + UMA (+ eSEN)

- **Training data.** UMA trained on roughly 500M unique 3D atomic configurations
  spanning materials (OMat24/MPtrj), molecules (OMol25/SPICE), and catalysis (OCx)
  domains — the largest openly documented training mix; OMat24 alone (~118M frames of
  inorganic MD + relaxations) is now the single most load-bearing public dataset:
  most of the top-10 leaderboard entries are "OAM" fits built on it.[1][13][14][64][66]
- **Architecture.** UMA-Small/Medium use a mixture-of-linear-experts (MoLE) design —
  capacity without proportional inference cost (UMA-Medium ~1.4B params at a fraction
  of naive cost); FAIR's eSEN is a scale-equivariant architecture whose 30M OAM-trained
  instance (eSEN-30M-OAM) ranks 7th (CPS 0.888).[13][65][1] [unverified on eSEN
  architecture details — the eSEN paper was not captured in this sweep]
- **Benchmark standing.** UMA itself does not appear in the captured Discovery-preset
  rows; note the virtualization caveat above — treat as "not observed in this
  snapshot," not as absence. UMA's reported strengths are cross-domain generality and
  OMat-bench-style evaluation rather than the WBM discovery task.[1][13]
- **License.** fairchem code is MIT; "models/checkpoint licenses vary by application
  area" per the repo — catalysis checkpoints historically non-commercial; verify per
  checkpoint before commercial deployment.[64]
- **Production readiness.** fairchem is the supported inference/fine-tuning library;
  OMat24 weights are the community's default fine-tuning substrate; heavy (medium
  tier) for single-GPU shops but the small tier is deployable.[64]
- **Weaknesses.** Massive multi-domain training raises domain-interference and
  calibration questions; checkpoint licensing friction; discovery-task standing not
  independently established in this snapshot.[13][64][1]

### 2026 entrants observed on the leaderboard

From the 2026-09-09 snapshot (all OAM-mix trained unless noted):[1]

- **TECE-OAM-RRA-1.0** (Jul 2026, 222M params) — rank 1, CPS 0.908. No primary source
  captured; architecture lineage [unverified].
- **EquFlash / EquFlashV2** (Jun 2025 / Jun 2026, ~29-45M params) — ranks 8/2, CPS
  0.888/0.907; name suggests the Equiformer lineage [unverified].
- **EquiformerV3+DeNS** (Apr 2026, 30.3M) — rank 3, CPS 0.902, best F1 0.931.
  Third-generation SE(3)-equivariant graph attention transformer with
  denoising-noise-support (DeNS) training; MIT-licensed reference code from the
  atomic architects group.[19][20]
- **TACE-OAM-L** (Apr 2026, 83M) — rank 6, CPS 0.889 [no captured source].
- **MatRIS-10M** (Oct 2025) — ranks 10/22; notable as one of only three models
  predicting magmoms (EFSGM targets) alongside CHGNet.[1]
- **AlphaNet-v1-OAM** (May 2025, 4.7M) — rank 23, CPS 0.769 with strong DAF 5.75;
  AlphaNet originates in the UCSD Materials Virtual Lab ecosystem [unverified this
  sweep].[1]
- **Nequix / Eqnorm / HIENet / BAM-MP-core** — 2025-26 community fits filling the
  mid/low table (CPS 0.55-0.76); HIENet (Jul 2025) and Nequix (Jan 2026, with
  Hessian targets + MDR-MP omega_q data) show the benchmark absorbing new prediction
  targets.[1]

## 1.2 Summary comparison table (Matbench Discovery, 2026-09-09 snapshot)[1]

| Model | Architecture family | Training data | CPS (rank) | License | Production readiness | Key weaknesses |
|---|---|---|---|---|---|---|
| TECE-OAM-RRA-1.0 | [unverified] | 6.6M OAM mix | 0.908 (1) | [unverified] | new entrant | unproven lineage |
| EquFlashV2 | Equiformer-lineage [unverified] | 6.6M OAM mix | 0.907 (2) | [unverified] | new entrant | unproven at scale |
| EquiformerV3+DeNS-OAM | SE(3) graph attention transformer + DeNS | 6.6M OAM mix | 0.902 (3), F1 0.931 | MIT code [20] | reference code public [19] | kappa 0.118 trails only TECE/EquFlash |
| GRACE-3L-OAM-L | Graph atomic cluster expansion | 6.6M OAM mix | 0.900 (4) | gracemaker open [63] | LAMMPS-native, fast [61] | descriptor expressivity ceiling |
| PET-OAM-XL | Parallel equivariant transformer | 6.6M OAM mix | 0.898 (5) | [unverified] | 730M params = heavy | capacity vs cost |
| eSEN-30M-OAM | scale-equivariant (FAIR) [unverified] | 6.6M OAM mix | 0.888 (7) | fairchem [64] | FAIR toolchain | details uncaptured |
| SevenNet-Omni-i12 | NequIP-based equivariant GNN, multitask | 243M COSMOS | 0.873 (11) | open repo [11] | multi-GPU MD [11] | kappa 0.192 mid |
| ORB v3 | graph transformer + denoising forces | 6.5M MPtrj+Alex+OMat24 | 0.860 (14) | repo, commercial-friendly [5] | best speed/memory engineering [6] | direct forces; kappa 0.210 |
| DPA-4.0.1-Pro | deep potential attention | 146k MPtrj | 0.840 (15) | DeePMD open [15] | LAMMPS production stack | data-bound (MPtrj-only) |
| MACE-MPA-0 | higher-order equivariant MP (ACE) | 3.4M MPtrj+sAlex | 0.795 (21) | weights permissive [76] | most-deployed family [3] | no long-range; kappa 0.412 |
| MatterSim v1 5M | GNN + attention | 17M generative T/P | 0.767 (24) | MIT [27] | MS-maintained [28] | underfits; PBE |
| MACE-MP-0 | as above | 146k MPtrj | 0.637 (34) | permissive [76] | ubiquitous legacy | obsolete accuracy |
| M3GNet | 3-body graph net | 63k MPF | 0.428 (40) | repo moved [75] | legacy via matgl | 2022 accuracy |
| CHGNet | charge-informed GNN | 146k MPtrj | 0.400 (41) | MIT [23] | ASE/LAMMPS + magmoms [21] | discovery-obsolete |
| NequIP-GNoME | E(3) equivariant MP | 6M GNoME | n/a; F1 0.829 | community fit | research artifact | uneven OOD errors |
| PET-MAD (official) | PET | MAD inorg+org mix | not on board | open [77] | lightweight + LoRA [9] | low-energy bias [9] |
| UMA-S/M | mixture of linear experts | ~500M multi-domain | not observed [1] | code MIT, ckpts vary [64] | fairchem | domain interference; licensing |
| AIMNet2 | atoms-in-molecules NQC | 20M molecular DFT | n/a (molecular) | HF weights [17] | tiny + cloud [44] | not periodic |

## 1.3 State-of-the-art frontiers in 2026

**Fine-tuning vs from-scratch.** Settled directionally: systematic 2026 work (Tompa et
al.) shows fine-tuning foundation models has clear data-efficiency advantages over
training from scratch in low-data regimes, with the advantage form varying by
benchmark.[25] A published tutorial line covers fine-tuning U-MLIPs as the standard
adaptation paradigm,[56] and LoRA-style adaptation is demonstrated even for
lightweight universals (PET-MAD's LoRA fine-tune reproducing bespoke-model dielectric
response for BaTiO3).[9] Practical guidance circulating in the community: small
learning rates, force-weighted losses, initial layer freezing [unverified — secondary
summary, not primary capture].

**Universal vs element-specific.** The 2026 literature is converging on: universals
as configuration-space generators/teachers for cheap data generation, then
material-specific fine-tuned models for production accuracy — directly evaluated in
the config-space-generator study comparing fine-tuned models trained from AIMD vs
universal-generated data.[26][72] Independent 2025-26 benchmark studies find universals
now usable for cheap pre-screening of thermodynamic stability on elemental
systems,[83] but still failing on equilibrium zeolite testbeds,[31] on
supported-nanoparticle structural exploration (decoupling energy accuracy from
structural exploration),[32] and on amorphous materials — flagged as *the* frontier
challenge for universal interatomic potentials.[71][30]

**Uncertainty quantification.** Ensemble conventions are now first-class on the
leaderboard (N= estimators shown in params column)[1]; training-time uncertainty and
robustness methods appear in the npj Computational Materials line (robust training of
MLIPs with uncertainty-driven data curation),[58] and calibrated-uncertainty active
learning is an active methods thread in 2025-26.[53] For error-geometry work this is
the connective tissue: per-structure error prediction and OOD detection are the
applied face of MLIP UQ.[58][1]

**Active learning loops.** DeepModeling's on-the-fly DeePMD learning remains the
production reference;[15] ORNL runs dedicated active-learning programs for
reliable/robust MLIP development (representative datasets with minimal ab initio
redundancy, e.g. actinide potentials);[78][79] the Shapeev group's
extrapolation-grade active learning (MLIP package, D-optimality/max-vol) is the
classical linear-cost lineage.[51] A 2026 single-shot workflow uses a big model
(e.g. MACE) to bootstrap small models, cutting active-learning cycles further.[53]
Inverse-design-of-potentials via active learning also appeared in 2026.[80]

**Benchmark geometry itself is a frontier.** Matbench Discovery's task set now spans
discovery, geometry optimization, phonons/kappa, MD, and diatomics;[1][2] community
benchmarks (zeolites, amorphous, nanoparticles, elemental systems) probe where
universals quietly fail.[31][32][71][83] The npj Computational Materials centennial
review (Dec 2025) frames MLIPs as the bridge between QM accuracy and FF
cost.[52] Phonon readiness specifically: 2025 analysis concluded universal MLIPs are
"ready for phonons" on well-behaved crystals,[73] while kappa_SRME spreads of
0.09-1.8 across the board show thermal-transport ranking remains the discriminating
task.[1]

---

# Part 2 — Institution and people map for TMS 2027

## 2.1 Section A — Groups and leaders (connection targets)

### US national labs

**Lawrence Berkeley National Lab / Materials Project (UC Berkeley).** Kristin Persson
— Materials Project director, UC Berkeley professor of materials science; elected to
the NAE (2025) for data-driven materials design via open materials databases, and to
the American Academy of Arts and Sciences (May 2026).[37][38] Why it matters: MP
curates MPtrj — the training substrate of CHGNet, MACE-MP, SevenNet, and the whole
OAM mix lineage;[23][1] any benchmark/error-geometry claim eventually touches MP data
governance. The CHGNet/charge-informed line is LBL-hosted.[21][23]

**Oak Ridge National Laboratory.** Active MLIP programs centered on active
learning for reliable/robust potentials (representative-dataset generation, actinide
applications).[78][79] Why it matters: the largest US-lab consumer-side practice of
MLIP validation methodology — natural audience for error-geometry and validation-gate
work.

**Los Alamos National Laboratory [unverified affiliation].** The GRACE production
potentials and gracemaker tooling.[61][62][63] Why it matters: ACE-lineage production
models for metals/alloys with LAMMPS-first deployment; the natural counterweight to
transformer-lineage benchmark results.

**NIST.** Interatomic Potentials Repository remains the classical-potential reference
infrastructure [unverified — appeared in search results but page not captured this
sweep].

**NREL.** Not captured this sweep [unverified — no reliable result retrieved].

### Universities

**University of Cambridge / Max Planck Institute for Polymer Research.** Gabor
Csanyi FRS — Professor of Engineering, Cambridge, and Director at MPI-P; the MACE
line (MACE-MP-0/-MPA, fine-tuning with "very little effort yields near-DFT accuracy")
and the newer MACE-POLAR-1 with electrostatics.[45][74][4] Why it matters: most-cited
universal-potential lineage; the fine-tuning paradigm most benchmark work assumes.

**Harvard.** Boris Kozinsky's MIR group — NequIP and Allegro; the equivariant
architecture wellspring with maintained open code and an extension
ecosystem.[47][48][49] Why it matters: architecture ablations and locality/long-range
tradeoffs live here.

**MIT.** Rafael Gomez-Bombarelli (DMSE) — ML for materials with simulation;
profiled by MIT News (Feb 2026) on AI+simulation at an inflection point.[50] Why it
matters: representation learning + design loops, MOF/porous-material ML potentials;
strong fine-tuning/benchmark collaboration partner.

**Carnegie Mellon University.** Olexandr Isayev — Carl and Amy Jones Professor in
Interdisciplinary Science (Chemistry + MSE); AIMNet2 (20M DFT calcs, 14 elements,
unified neutral/charged species) and AIMNetCentral with long-range electrostatics +
D3.[42][18][44][17] Why it matters: the molecular-side bookend to solid-state MLIPs;
charge-state handling is the live weakness frontier. CMU is also the academic partner
on Meta FAIR's UMA (FAIR + CMU authorship).[14]

**UC San Diego.** Shyue Ping Ong's Materials Virtual Lab — M3GNet (with Chi Chen),
the matgl ecosystem, Matterverse; recent review work on ML for materials
chemistry.[39][40][75] Why it matters: open tooling and the graph-potential lineage
that predated the foundation-model era; AlphaNet association [unverified this sweep].

**EPFL.** Michele Ceriotti's COSMO lab — PET-MAD (authors include Mazitov, Bigi,
Kellner, Pegolo, Tisi, Fraux, Pozdnyakov, Loche, Ceriotti), published in npj
Computational Materials 2025/26;[9][77] Nicola Marzari (THEOS chair; PSI) —
infrastructure and methodology for large-scale DFT reference data.[59] Why it
matters: EPFL owns the "lightweight + physically honest universal" counter-program
and the reference-data culture error-geometry work depends on.

**Skoltech.** Alexander Shapeev — moment tensor potentials, the MLIP package with
MPI + active learning, extrapolation-grade reliability theory.[51] Why it matters:
the deepest active-learning/UQ theory lineage; D-optimality error bounds are directly
adjacent to error-geometry claims.

**Seoul National University.** The MDIL lab (SevenNet; leader Yousung Jung
[unverified this sweep]) — SevenNet-0, SevenNet-Omni multi-task foundation model on
the COSMOS dataset, plus 2025 cross-domain-transfer methodology.[11][12][70][1] Why
it matters: the strongest Asia-Pacific universal-potential group with production MD
focus.

### Companies

**Meta FAIR (FAIR Chemistry).** The UMA/OMat24/OMol25 program (with CMU);[13][14][64]
UMA's mixture-of-linear-experts architecture and ~500M-configuration training
mix;[65][66] fairchem under MIT with per-domain checkpoint licensing.[64] Why it
matters: OMat24 is the single most load-bearing public dataset — most of the
leaderboard top-10 is trained on it;[1] FAIR's choices define the field's data
regime.

**Google DeepMind.** GNoME (2.2M discovered candidate crystals, ~381k stable —
figures widely reported [unverified this sweep]); materials discovery sits under
Pushmeet Kohli, VP Research / Chief Scientist Google Cloud.[55] Why it matters: the
OOD-heavy discovery-data regime and its error-geometry consequences; the
NequIP-GNoME leaderboard entry is the direct artifact.[1]

**Microsoft Research.** MatterSim team — generative finite-T/P training data
methodology, MIT-licensed code and docs.[8][27][28][29] Why it matters: the
temperature/pressure-realistic training-data philosophy, and a major cloud
distribution channel.

**Orbital Materials (London; now Orbital Industries).** Founded 2022; ~$66M raised
including a $50M Series B (May 2026); Orb v3 (Apr/Sep 2025) targets mesoscale
simulation; weights via orb-models with commercial engagement invited.[54][5][6][7]
Why it matters: the best inference-engineering shop in the field; speed-memory Pareto
leader.[6]

**DP Technology / AI for Science Institute, Beijing (DeepModeling).** DeePMD-kit,
DPA-2/DPA-3/DPA-4, OpenLAM ("Conquer the Periodic Table"), LAMBench
evaluation.[15][67][68][69] Why it matters: the largest production MD ecosystem and
the main non-Western universal-model program; individuals (Weihong Zhang, Linfeng
Zhang) [unverified this sweep].

**Citrine Informatics.** AI platform for materials/chemicals R&D; ~$81M raised;
2025 partnership activity (Econic, Sep 2025).[81][82] Why it matters: the
industrial-data-governance counterpart — where benchmark results meet corporate
adoption.

## 2.2 Section B — TMS 2027 verified logistics

All items in this section verified against tms.org / ProgramMaster on 2026-09-09
unless marked otherwise; corroborated in-repo in `tms2027_verified.json` (repo
root).[33][34][35]

- **Meeting:** 156th TMS Annual Meeting & Exhibition.
- **Dates:** Sunday March 14 – Thursday March 18, 2027.[34]
- **Venue:** Orlando World Center Marriott, Orlando, Florida, USA.[34]
- **Exhibition:** March 15–17, 2027.[34]
- **Housing deadline:** February 16, 2027.[34]
- **Abstracts:** opened May 11, 2026; the general deadline was July 15, 2026 and
  abstract submission for most TMS2027 symposia is now closed (as of Sept
  2026).[35] Late windows still open per the verified capture: Bladesmithing
  Symposium (Oct 31, 2026) and the Technical Division Student Poster Contest
  (Jan 22, 2027).
- **Program shape:** technical program runs Monday–Thursday, eight half-day sessions;
  TMS does not permit parallel sessions within a symposium; 100+ symposia
  overall.[33]

**Relevant symposia (approved list, Data-Driven / Computational track and
adjacent)** — the 13 most relevant from the verified capture:[33][35]

1. AI/ML/Data Informatics for Materials Discovery: Bridging Experiment, Theory, and
   Modeling — the flagship MLIP/ML-for-materials session.
2. Artificial Intelligence Applications in Integrated Computational Materials
   Engineering (AI-ICME) — co-organized with Wenwu Xu (SDSU M3 Lab) per the
   departmental call.[36]
3. Computational Discovery and Design of Materials.
4. Computational Thermodynamics and Kinetics — the phase-stability/Calphad bridge.
5. Hume-Rothery Symposium: Data-Driven Materials Discovery and Phase Stability —
   directly on the WBM/stability-prediction theme of Matbench Discovery.
6. Bridging Scale Gaps in Multiscale Materials Modeling in the Age of Artificial
   Intelligence.
7. Verification, Calibration, and Validation Approaches for Mechanical Modeling of
   Metals — the natural home for benchmark/validation/error-geometry methodology.
8. Algorithms Development in Materials Science and Engineering.
9. AI-Enabled Materials Processing: Integrating Accelerated Experimental Workflows
   and Processing-Aware Machine Learning.
10. Celebrating 50 Years of Building the Foundations of Materials Design (FMD/MPMD/
    SMD symposium honoring John Agren) — the materials-design elders will be present.
11. Chemistry and Physics of Interfaces.
12. Mechanistic and Experimental Thermodynamics & Kinetics of Alloys.
13. Avoiding Plot Holes: Telling Compelling Stories (with Data).

Adjacent approved symposia also worth scanning: Additive Manufacturing Modeling,
Simulation, and AI; Computational Modeling and Machine Learning for Bio-Related and
Sustainable Materials; Modeling, AI Applications, and Method Development in Nuclear
Materials; Energy Technology 2027 (theory/simulation track); Frontiers of Materials
Award Symposium on MOFs.[33]

**Which mapped groups attend TMS?** [unverified — TMS 2025/2026 program archives
were not captured in this sweep.] Symposia 1-9 above are the standing venues where
Materials Project/LBL, ORNL, LANL, SDSU (Xu), and the ICME community present; the
European FAIR-lab groups (Csanyi, Ceriotti) and company teams (Meta FAIR, DeepMind,
Orbital, DP Technology) historically favor ML-in-materials and NeurIPS-adjacent
venues instead — verify individual attendance against the final TMS2027 program when
ProgramMaster populates speaker lists, and target the symposium organizers (named on
each ProgramMaster symposium page) as the highest-value fixed points.

---

# Executive summary (10 lines)

1. TMS 2027 = March 14-18, 2027 at the Orlando World Center Marriott (exhibits Mar 15-17, housing deadline Feb 16, 2027); most abstract windows closed July 15, 2026 — Bladesmithing (Oct 31, 2026) and Student Posters (Jan 22, 2027) remain open.[33][34][35]
2. On Matbench Discovery (snapshot 2026-09-09), discovery F1 has saturated (best 0.931 vs DAF ceiling ~6.54) — the frontier moved to phonons, geometry robustness, and MD stability.[1]
3. Training data is the dominant lever: every top-10 model is trained on the ~6.6M-crystal OAM mix (MPtrj+OMat24+sAlex); identical architectures drop 6-16 CPS points in MPtrj-only variants.[1]
4. Current leaderboard leaders are 2025-26 entrants — TECE-OAM-RRA-1.0 (0.908), EquFlashV2 (0.907), EquiformerV3+DeNS-OAM (0.902, best F1), GRACE-3L-OAM-L (0.900) — not the household names of 2024.[1][19][61]
5. The classic universals are now mid-table or worse: MACE-MPA-0 ranks 21st, MatterSim v1 24th, MACE-MP-0 34th, M3GNet 40th, CHGNet 41st — still production-relevant, no longer accuracy-relevant without fine-tuning.[1]
6. Fine-tuning over from-scratch is settled for low-data regimes; the emerging pattern is universals as configuration-space generators feeding material-specific fine-tunes (incl. LoRA on PET-MAD).[25][26][9]
7. Documented 2026 failure frontiers for universal MLIPs: amorphous materials, zeolites, supported-nanoparticle structural exploration, and anything needing long-range electrostatics, magnetism, or charge transfer.[71][31][32][21]
8. Licensing splits the field: MIT/permissive (MatterSim, MACE-MP weights, fairchem code, EquiformerV3) vs per-checkpoint commercial caveats (FAIR checkpoints "vary by application area", orb-models, moved M3GNet) — verify per checkpoint before production.[27][76][64][5][75]
9. Highest-value TMS connection targets: Persson/LBL (MPtrj data governance), Csanyi/Cambridge-MPI-P (MACE), Kozinsky/Harvard (NequIP/Allegro), Isayev/CMU (AIMNet2, charge states), Ceriotti/EPFL (PET-MAD), Shapeev/Skoltech (active learning/UQ), Ong/UCSD (matgl), FAIR/DeepMind/Microsoft/Orbital/DP-Technology industrials.[37][45][47][42][9][51][39]
10. Target symposia: AI/ML/Data Informatics for Materials Discovery, AI-ICME, Hume-Rothery (data-driven phase stability), Verification/Calibration/Validation of Mechanical Modeling — the standing homes for MLIP benchmarking and error-geometry methodology; verify individual attendance against the final ProgramMaster speaker lists (archive not yet captured).[33][35]

## Sources

[1] https://matbench-discovery.materialsproject.org — Matbench Discovery leaderboard
[2] https://arxiv.org/abs/2308.14920 — Matbench Discovery paper
[3] https://github.com/ACEsuit/mace-foundations — MACE foundation models repo
[4] https://arxiv.org/abs/2401.00096 — MACE-MP-0 foundation model paper
[5] https://github.com/orbital-materials/orb-models — orb-models repo
[6] https://arxiv.org/abs/2504.06231 — Orb-v3 paper
[7] https://www.orbitalindustries.com/posts/orb-v3-atomistic-simulation-at-scale — Orb-v3 release post
[8] https://arxiv.org/abs/2405.04967 — MatterSim paper
[9] https://arxiv.org/abs/2503.14118 — PET-MAD paper
[11] https://github.com/MDIL-SNU/SevenNet — SevenNet repo
[12] https://sevennet.readthedocs.io/en/latest/user_guide/pretrained.html — SevenNet pretrained models docs
[13] https://arxiv.org/abs/2506.23971 — UMA paper
[14] https://ai.meta.com/research/publications/uma-a-family-of-universal-models-for-atoms — UMA Meta page
[15] https://github.com/deepmodeling/deepmd-kit — DeePMD-kit repo
[17] https://huggingface.co/isayevlab/aimnet2-2025/tree/main — AIMNet2-2025 weights
[18] https://olexandrisayev.com/aimnet2-a-neural-network-potential — AIMNet2 Isayev page
[19] https://arxiv.org/abs/2604.09130 — EquiformerV3 paper
[20] https://github.com/atomicarchitects/equiformer_v3 — equiformer_v3 repo
[21] https://chgnet.lbl.gov — CHGNet site
[22] https://arxiv.org/abs/2302.14231 — CHGNet paper
[23] https://github.com/CederGroupHub/chgnet — chgnet repo
[24] https://www.nature.com/articles/s42256-023-00716-3 — CHGNet Nature MI paper
[25] https://arxiv.org/abs/2606.12704 — Fine-tuning MLIP foundation models paper
[26] https://arxiv.org/html/2606.23214 — UIPs as configuration-space generators
[27] https://github.com/microsoft/mattersim — MatterSim repo
[28] https://microsoft.github.io/mattersim — MatterSim docs
[29] https://www.microsoft.com/en-us/research/publication/mattersim-a-deep-learning-atomistic-model-across-elements-temperatures-and-pressures — MatterSim MSR page
[30] https://arxiv.org/pdf/2607.11384 — Amorphous materials frontier challenge for UIPs
[31] https://kmu.github.io/publication/2026benchmark — Zeolite benchmark universal IPs
[32] https://collaborate.princeton.edu/en/publications/benchmarking-universal-machine-learning-interatomic-potentials-fo — Princeton supported-nanoparticle MLIP benchmark
[33] https://www.programmaster.org/PM/PM.nsf/Home?OpenForm&ParentUNID=A79798B673220E9885258B13005BB1F5 — TMS2027 ProgramMaster symposia list
[34] https://www.tms.org/TMS2027/TMS2027/Default.aspx — TMS2027 meeting site
[35] https://www.tms.org/TMS2027/TMS2027/Programming/TMS2027_Technical_Program.aspx — TMS2027 technical program page
[36] https://mmm.sdsu.edu/opportunities — SDSU M3 Lab TMS2027 AI-ICME call
[37] https://en.wikipedia.org/wiki/Kristin_Persson — Kristin Persson Wikipedia
[38] https://newscenter.lbl.gov/2026/05/08/berkeley-labs-kristin-persson-elected-to-the-american-academy-of-arts-and-sciences — Persson AAAS 2026
[39] https://profiles.ucsd.edu/shyueping.ong — Ong UCSD profile
[40] https://materialsvirtuallab.org/people — Materials Virtual Lab people
[42] https://www.cmu.edu/chemistry/people/faculty/isayev.html — Isayev CMU page
[44] https://github.com/isayevlab/aimnetcentral — aimnetcentral repo
[45] https://www.eng.cam.ac.uk/profiles/gc121 — Csanyi Cambridge profile
[47] https://mir.g.harvard.edu/research/software — MIR group Harvard software
[48] https://github.com/mir-group/nequip — nequip repo
[49] https://github.com/mir-group/allegro — allegro repo
[50] https://news.mit.edu/2026/accelerating-science-ai-and-simulations-rafael-gomez-bombarelli-0212 — MIT News RGB Feb 2026
[51] https://scholar.google.com/citations?user=NMyIbIwAAAAJ — Shapeev scholar
[52] https://www.nature.com/articles/s43588-025-00930-6 — MLIPs centennial review npj Comp Mater
[53] https://www.nature.com/articles/s41524-026-02023-y — single-shot MLIP workflow npj 2026
[54] https://indexed.vc/companies/orbital-materials — Orbital Materials funding profile
[55] https://research.google/people/105667 — Pushmeet Kohli research page
[56] https://www.researchgate.net/publication/393148877_Fine-Tuning_Universal_Machine-Learned_Interatomic_Potentials_A_Tutorial_on_Methods_and_Applications — Fine-tuning U-MLIPs tutorial
[58] https://www.nature.com/articles/s41524-024-01227-4 — Robust training of MLIPs w/ uncertainty npj 2024
[59] https://scholar.google.com/citations?user=YjHKNAUAAAAJ — Marzari scholar
[61] https://arxiv.org/abs/2508.17936 — GRACE graph atomic cluster expansion paper
[62] https://www.nature.com/articles/s41524-026-01979-1 — GRACE npj Comput Mater 2026
[63] https://gracemaker.readthedocs.io — gracemaker fitting tool docs
[64] https://github.com/facebookresearch/fairchem — fairchem repo (FAIR Chemistry)
[65] https://huggingface.co/papers/2506.23971 — UMA paper page HF
[66] https://aiwiki.ai/wiki/uma_meta — AI Wiki UMA overview
[67] https://arxiv.org/abs/2506.01686 — DPA-3 large atomistic model paper
[68] https://huggingface.co/deepmodelingcommunity/DPA-3.1-3M — DPA-3.1-3M HF model card
[69] https://github.com/deepmodeling/deepmd-kit/releases — DeePMD-kit releases (DPA-4)
[70] https://arxiv.org/abs/2510.11241 — SevenNet cross-domain transfer paper
[71] https://arxiv.org/abs/2607.11384 — amorphous materials frontier challenge UIPs
[72] https://arxiv.org/abs/2606.23214 — UIPs as configuration-space generators
[73] https://www.alphaxiv.org/abs/2502.12147 — smooth expressive potentials / phonon readiness
[74] https://www.h-its.org/event/joint-colloquium-gabor-csanyi — Csanyi H-ITS colloquium MACE-POLAR
[75] https://github.com/materialyzeai/m3gnet — m3gnet repo (materialyze)
[76] https://mace-docs.readthedocs.io/en/latest/guide/foundation_models.html — MACE foundation models docs
[77] https://springernature.figshare.com/articles/dataset/PET-MAD_A_Universal_Interatomic_Potential_for_Advanced_Materials_Modeling_-_Data_Record/28726703 — PET-MAD dataset record + authors
[78] https://impact.ornl.gov/en/publications/toward-machine-learning-interatomic-potentials-for-modeling-urani — ORNL uranium MLIP publication
[79] https://impact.ornl.gov/en/projects/accelerating-the-development-of-reliable-and-robust-machine-learn-5 — ORNL active-learning MLIP project
[80] https://link.springer.com/article/10.1186/s41313-026-00086-4 — inverse design of potentials via active learning
[81] https://citrine.io/media-type/press-releases — Citrine press releases
[82] https://www.azom.com/news.aspx?newsID=64896 — Citrine Econic partnership 2025
[83] https://www.researchgate.net/publication/410917392_Benchmarking_universal_machine_learning_interatomic_potentials_on_elemental_systems — elemental systems benchmark
