> **Provenance:** explore agent `agent-11` (director-commissioned deep research, backdrop research, 2026-07-21) — materialized verbatim. Quantitative claims are as reported by the research agent from sources it accessed; see citations inline. Citation-verification pass pending before any external publication.

# Atomic-Scale Simulation on Supercomputers: Expert Digest

All figures below are sourced; derived numbers are labeled **[derived]**, and anything not cleanly verifiable is flagged **[uncertain]**. Machine performance numbers are TOP500 HPL (Rmax) unless noted.

---

## 1. Machine table

| Machine | Site / debut | Peak / HPL (FP64) | Architecture | Cost | Power | Notes for atomistic sim |
|---|---|---|---|---|---|---|
| **Tianhe-2** | NSCC Guangzhou; #1 June 2013 – Nov 2015 | 54.9 PF peak / 33.86 PF HPL | 16,000 nodes × (2× Intel Xeon E5-2692 + 3× Xeon Phi 31S1P), 3.12M cores | ¥2.4B ≈ **$390M** ([Wikipedia/Dongarra report](https://en.wikipedia.org/wiki/Tianhe-2)) | 17.6 MW; 24 MW with cooling | 2015 US export ban blocked its upgrade → rebuilt as Tianhe-2A with domestic Matrix-2000 (61.4 PF HPL) |
| **Sunway TaihuLight** | NSCC Wuxi; #1 June 2016 – June 2018 | 125.4 PF peak / 93.01 PF HPL | 40,960× SW26010 (260 cores @1.45 GHz), 10.65M cores, **no accelerators** ([Dongarra report](https://www.netlib.org/utk/people/JackDongarra/PAPERS/sunway-report-2016.pdf), [Klockwood notes](https://www.glennklockwood.com/garden/systems/Sunway-TaihuLight)) | ¥1.8B ≈ **$270–273M** incl. R&D ([DCD](https://www.datacenterdynamics.com/en/analysis/chinas-sunway-taihulight-named-worlds-most-powerful-computer-uses-homegrown-tech/), [SCIO](http://www.scio.gov.cn/news_0/202209/t20220921_415792.html)) | 15.37 MW (HPL) | First all-domestic Chinese #1; later a proving ground for ML-potential MD (see §2) |
| **Summit** | ORNL OLCF; #1 June 2018 – June 2020 | 200.8 PF peak / 148.6 PF HPL | 4,608 nodes × (2× IBM POWER9 22c + 6× NVIDIA V100) | **~$200M** ([Oak Ridge Today](http://oakridgetoday.com/2019/06/17/ornls-summit-remains-worlds-most-powerful-supercomputer/)) | ~13 MW full system ([Next Platform](https://www.nextplatform.com/2017/09/19/power9-rollout-begins-summit-sierra/)); HPL power ~10 MW **[uncertain]** | Machine that launched MLIP-at-scale: 2020 Gordon Bell DPMD run; 3.3 mixed-precision "exaops" advertised |
| **Sierra** | LLNL (NNSA); online Oct 2018, #2 Nov 2018 | 125.7 PF peak / 94.6 PF HPL | 4,320 nodes × (2× POWER9 + 4× V100), 17,280 GPUs ([LLNL](https://hpc.llnl.gov/hardware/compute-platforms/sierra), [ACM ICS'25](https://dl.acm.org/doi/10.1145/3721145.3734532)) | Not separately disclosed **[uncertain]** (CORAL program total ~$525M, [FedScoop](https://fedscoop.com/energy-dept-aurora-supercomputer-intel-cray/)) | ~11–13 MW **[uncertain]** | Classified stockpile stewardship; decommissioned ([LLNL page](https://hpc.llnl.gov/hardware/compute-platforms/sierra)) |
| **Fugaku** | RIKEN R-CCS Kobe; #1 June 2020 – June 2022 | 537 PF peak / 442 PF HPL | 158,976× Fujitsu A64FX (48-core Arm SVE + HBM2), 7.63M cores, **no GPUs** ([DCD](https://www.datacenterdynamics.com/en/news/fugaku-remains-worlds-fastest-supercomputer-in-latest-top500/)) | Reported **~$1B** total program ([CACM](https://cacm.acm.org/news/fugaku-takes-the-lead/)) **[reported, not official]** | ~30 MW (Fujitsu spec: 30–40 MW, [Fujitsu](https://global.fujitsu/en-global/technology/research/fugaku)) | First machine to break 2 EF on HPL-AI (mixed precision); shared use from 9 Mar 2021 |
| **LUMI** | CSC Kajaani, Finland; full system Nov 2022 | ~530–552 PF peak **[uncertain, sources differ]** / 379.7 PF HPL | LUMI-G: 2,560 nodes × (1× AMD "Trento" 64c + 4× MI250X); HPE Cray EX ([CSC/ScienceBusiness](https://sciencebusiness.net/network-updates/csc-supercomputer-ranked-among-worlds-fastest), [RankRed](https://www.rankred.com/fastest-supercomputers-in-the-world/)) | **€200M** lifecycle ([EuroHPC](https://www.eurohpc-ju.europa.eu/lumi-new-eurohpc-world-class-supercomputer-finland-2020-10-21_en); total ecosystem budget >€600M per [CSC](https://indico.cern.ch/event/1466360/contributions/6325288/attachments/3007776/5302233/CSC-update-300125.pdf)) | 7.1 MW, hydro-powered with waste-heat reuse ([DCD](https://www.datacenterdynamics.com/en/analysis/lumi-europes-fastest-ai-supercomputer-finland/)) | Europe's flagship GPU machine; major MLIP/materials user community |
| **Frontier** | ORNL OLCF; **first exascale**, #1 June 2022 – Nov 2024 | 1.685 EF peak / 1.102 EF HPL (June 2022); 1.353 EF (Nov 2024) | 9,408 nodes × (1× AMD EPYC "Trento" 64c + 4× MI250X), HPE Cray EX235a ([arXiv survey](https://www.arxiv.org/pdf/2506.19019)) | **$600M** ([widely reported](https://tipsmake.com/10-fastest-supercomputers-iocqo)) | 21.1 MW during HPL run ([OSTI/IEEE paper](https://www.osti.gov/servlets/purl/2429796)); 52.2 GF/W | Host of 2023 and 2024 Gordon Bell atomistic prizes (§2) |
| **Aurora** | ANL ALCF; exascale verified May 2024 | 1.98 EF peak / 1.012 EF HPL (on 87% of system) | HPE Cray EX; Intel Xeon Max 9470 + Intel Data Center GPU Max ("Ponte Vecchio"), 6 GPUs/node ([HPE](https://www.hpe.com/us/en/newsroom/press-release/2024/05/hewlett-packard-enterprise-delivers-second-exascale-supercomputer-aurora-to-us-department-of-energys-argonne-national-laboratory.html)) | **$500M+** contract ([DOE, 2019](https://www.energy.gov/articles/us-department-energy-and-intel-build-first-exascale-supercomputer)) | 38.7 MW ([Wikipedia](https://en.wikipedia.org/wiki/Aurora_(supercomputer))) | 10.6 EF on HPL-MxP (mixed precision) — largest AI-capable system at delivery |
| **El Capitan** | LLNL (NNSA); **#1 since Nov 2024**; dedicated 9 Jan 2025 | 2.746 EF peak / 1.742 EF HPL | 11,136 nodes × 4× AMD MI300A APU (44,544 APUs; 24 Zen4 cores + 228 CDNA3 CUs each), 5.4 PB HBM3 ([LLNL](https://www.llnl.gov/article/51231/llnls-el-capitan-debuted-new-top500-list-worlds-most-powerful-supercomputers), [chinaaet/Top500 report](https://chinaaet.com/article/3000168703)) | **$600M** ([Caliber.Az/AP](https://caliber.az/en/post/el-capitan-us-breaks-supercomputing-barriers-with-new-600-million-machine)) | ~30 MW; 58.89 GF/W Green500 ([IT Pro](https://www.itpro.com/technology/what-is-exascale-computing-exploring-the-next-step-in-supercomputers)) | Classified NNSA stockpile work; unclassified sibling Tuolumne exists |

---

## 2. Workload evolution (with citations)

**Phase A — plane-wave/pseudopotential DFT era (–2015).** Community codes VASP and Quantum ESPRESSO (Giannozzi et al., *JPCM* 21, 395502, 2009; [cited in QE exascale papers](https://arxiv.org/html/2510.01875)) dominated leadership allocations; routine DFT topped out at ~10³ atoms. Linear-scaling efforts (PEXSI, ~10–20k atoms; [Lin Lin slides](https://www.bnl.gov/nysds20/files/talks/lin_lin.pdf)) were the scale frontier. This era maps to Tianhe-2's Xeon+Phi architecture.

**Phase B — GPU adoption + classical MD at scale (2016–2020).** QE's exascale rewrite is documented in "Quantum ESPRESSO toward the exascale" (Giannozzi et al., *JCP* 152, 154105, 2020) and the follow-up JCTC 19, 6992 (2023). LAMMPS + Kokkos became the portability vehicle; DOE's Exascale Computing Project funded the **EXAALT** (Exascale Atomistics for Accuracy, Length, and Time) project, whose SNAP kernel re-engineering gave a 5× speedup on Summit ([DOE FY2021 budget justification](https://www.energy.gov/science/articles/fy-2021-advanced-scientific-computing-research-budget-request)).

**Phase C — MLIP era (2018–2022).**
- Deep Potential MD method: Zhang et al., *PRL* 120, 143001 (2018).
- **2020 ACM Gordon Bell Prize**: Jia, Wang, Chen, Lu, Lin, Car, E, Zhang, "Pushing the limit of molecular dynamics with ab initio accuracy to 100 million atoms with machine learning," SC'20 — 100M atoms at 91 PF (FP64) / 275 PF (mixed half precision), run on **Summit** ([ACM](https://mags.acm.org/communications/february_2021/MobilePagedArticle.action?articleId=1654975); journal version: Lu et al., "86 PFLOPS DPMD…," *Comput. Phys. Commun.* 259, 107624, 2021). Note: this prize run was on Summit, not Sunway — the Sunway association comes from the follow-up below.
- **10 billion atoms**: Guo et al., "Extending the limit of molecular dynamics with ab initio accuracy to 10 billion atoms," PPoPP 2022, on the new-generation Sunway system ([arXiv:2201.01446](https://arxiv.org/abs/2201.01446)) — the Sunway hardware generation is described in the paper; treat "OceanLight-class prototype" phrasing as **[lightly uncertain]**.
- Billion-atom classical-precision-scale MD: Nguyen-Cong et al., SC21 — 20B-atom SNAP/LAMMPS carbon run on all 27,900 Summit GPUs, 50 PF peak, 97% strong-scaling efficiency ([Consensus/SC21](https://www.consensus.app/papers/billion-atom-molecular-dynamics-simulations-of-carbon-at-nguyen-cong-belonoshko/0c366bdff8f656088bbc0269f4be1c57)).
- Universal MLIPs begin: **M3GNet** (Chen & Ong, *Nat. Comput. Sci.* 2, 718–728, 2022), CHGNet (Deng et al., 2023).

**Phase D — exascale + foundation models (2022–now).**
- Frontier exascale HPL: June 2022 ([Next Platform](https://www.nextplatform.com/hpc/2022/05/30/at-long-last-hpc-officially-breaks-the-exascale-barrier/1646968)).
- **2023 Gordon Bell Prize**: DFT-FE team (incl. Motamarri, Gavini) — real-space DFT at 659.7 PF on Frontier, quasicrystals and alloy defects ([ACM, 16 Nov 2023](https://www.acm.org/media-center/2023/november/gordon-bell-prize-2023), [IISc](https://cds.iisc.in/dr-phani-motamarri-and-his-research-group-part-of-the-team-that-won-the-2023-acm-gordon-bell-prize/)).
- **2024 Gordon Bell Prize**: Barca et al. — "Breaking the Million-Electron and 1 EFLOP/s Barriers: Biomolecular-Scale Ab Initio MD Using MP2 Potentials," >1M electrons, >1 EF/s sustained on Frontier ([ACM, 21 Nov 2024](https://www.acm.org/media-center/2024/november/gordon-bell-prize-2024), [Univ. Melbourne](https://www.unimelb.edu.au/newsroom/news/2024/november/melbourne-researchers-win-the-nobel-of-high-performance-computing)).
- Foundation-model MLIPs: **MACE-MP-0** (Batatia et al., [arXiv:2401.00096](https://arxiv.org/pdf/2401.00096.pdf), Dec 2023; published *JCP* 163, 184110, 2025, already >1000 citations per [AIP](https://pubs.aip.org/aip/jcp/article/163/18/184110/3372267/A-foundation-model-for-atomistic-materials)).
- Frontier ParSplice+SNAP: 13,856 concurrent LAMMPS instances on ~75% of Frontier, 3.57×10⁹ atom-steps/s sustained for 1 h ([ACM SC paper](https://dl.acm.org/doi/pdf/10.1145/3581784.3607089)).
- Latest scale record: 1.62-trillion-atom MD with Neuroevolution Potential (NEP), "ab initio accuracy," on China's new-generation intelligent supercomputer — 2026 **preprint** ([arXiv:2604.24816](https://arxiv.org/pdf/2604.24816)) **[preprint, unrefereed]**.
- Cross-machine portability proven: LAMMPS-Kokkos strong scaling on Frontier, Aurora, El Capitan, and Alps ([arXiv:2508.13523](https://arxiv.org/abs/2508.13523)).

**AI-for-science programs.** DOE's "AI for Science, Energy and Security" report (May 2023, [ANL/ASCR overview](https://science.osti.gov/-/media/ascr/pdf/Office-Hours/2024/ASCR-Overview---2024-03.pdf)); the **FASST** (Frontiers in AI for Science, Security and Technology) initiative ([ANL/HPC User Forum deck](https://www.hpcuserforum.com/wp-content/uploads/2024/09/Rick-Stevens_ANL_FASST-Initiative_HPC-AI-User-Forum-Sept-2024.pdf)). Atomistic-specific allocations: 2025 INCITE project "exascale ab initio reactive MD (AIRMD)" awarded 380,000 Frontier node-hours ([2025 INCITE fact sheets](https://doeleadershipcomputing.org/wp-content/uploads/sites/123/2024/11/2025INCITEFactSheets.pdf)); 2026 INCITE includes an "Ab Initio Foundation Model" MLIP project ([2026 fact sheets](https://doeleadershipcomputing.org/wp-content/uploads/sites/123/2026/05/2026INCITEFactSheets.pdf)).

---

## 3. Timeline (compressed)

- 2013–2015: Tianhe-2 #1 — end of the CPU/coprocessor DFT era; US export ban (2015) pushes China to domestic silicon.
- June 2016: Sunway TaihuLight #1, 93 PF, all-domestic SW26010.
- 2018: Summit (#1) and Sierra (#2) — V100 GPU era; Deep Potential PRL published.
- 2020: Fugaku #1 (442 PF, Arm, no GPU); SC20 Gordon Bell: 100M-atom DPMD on Summit.
- 2022: Frontier breaks exascale (1.102 EF); PPoPP 10B-atom DPMD on new Sunway; M3GNet.
- 2023: DFT-FE Gordon Bell on Frontier (659.7 PF); MACE-MP-0 preprint; DOE AI4S report.
- 2024: Aurora verified exascale (May); El Capitan #1 at 1.742 EF (Nov); MP2 1M-electron Gordon Bell on Frontier.
- 2025–2026: El Capitan dedicated; MACE-MP-0 published; 1.62T-atom MD preprint; FASST / AI4S INCITE projects.

---

## 4. Cost & access notes

**Capex per peak PFLOP [derived — capex ÷ Rpeak]:**
- Tianhe-2 ≈ $7.1M/PF; Sunway ≈ $2.2M/PF; Summit ≈ $1.0M/PF; Fugaku ≈ $1.9M/PF (includes national R&D); LUMI ≈ €0.4M/PF (lifecycle); Frontier ≈ $0.36M/PF; Aurora ≈ $0.25M/PF; El Capitan ≈ $0.22M/PF. Trend: ~30× cheaper per FLOP in a decade, driven by GPU/AI silicon.

**Effective $/FLOP-hour [derived estimate, electricity only]:** at $0.05–0.10/kWh, Frontier's 21.1 MW costs ~$1,050–2,100 per machine-hour; dividing by its 1.353 EF HPL rate gives roughly **$800–1,600 per exaflop-hour** of delivered Linpack work. Real applications sustain far below HPL, so effective cost per useful FLOP is typically 3–10× higher **[rough estimate — electricity price and duty cycle assumptions, not an official figure]**. Amortizing Frontier's $600M capex over a 5-year life adds ~$14k/machine-hour (~$10k per HPL-exaflop-hour) **[derived]**.

**Access models:**
- **Open science (Frontier, Aurora, LUMI, Fugaku, Sunway-era OLCF):** DOE splits LCF time ~**60% INCITE / 30% ALCC / 10% Director's Discretionary** ([INCITE Overview & Policies](https://doeleadershipcomputing.org/wp-content/uploads/sites/123/2025/04/INCITE-Overview-and-Policies_2026.pdf)). INCITE is peer-reviewed and open to any affiliation; awards run to millions of node-hours. For 2026–27, ALCC pools: Frontier 20M node-hours (max request 2M), Aurora 16M ([ASCR ALCC cap page](https://science.osti.gov/ascr/Facilities/Accessing-ASCR-Facilities/ALCC/Allocation-Request-Cap)).
- **LUMI:** EuroHPC JU model — half the capacity for EU-wide calls, half for the hosting consortium countries (standard EuroHPC arrangement; [LUMI/EuroHPC](https://lumi-supercomputer.eu/lumi-one-of-the-worlds-mightiest-supercomputers/)) **[standard model; not re-verified per-call]**.
- **Fugaku:** shared-use via RIKEN/HPCI since 9 Mar 2021 ([Fujitsu](https://global.fujitsu/en-global/technology/research/fugaku)).
- **Sierra, El Capitan:** classified NNSA machines — no INCITE; tri-lab allocation via the ATCC process ([ASC implementation plan](https://www.osti.gov/servlets/purl/2475271)). El Capitan's unclassified sibling Tuolumne serves open science.

---

## Items flagged as uncertain or unverifiable

- Sierra's standalone cost — never officially broken out of CORAL; the $525M figure covers the program.
- Fugaku's $1B is a "reported" figure (CACM); official MEXT budgets were spread over the ¥100B+ Flagship 2020 project.
- LUMI Rpeak appears as 531–552 PF depending on source; HPL 379.7 PF is solid.
- Summit's HPL power (~10 MW) vs full-system power (~13 MW) — sources conflate.
- The PPoPP 2022 "10 billion atoms" run's exact machine designation (described as the new-generation Sunway system; "OceanLight" naming is press usage).
- The 1.62-trillion-atom NEP result is a 2026 arXiv preprint, not yet peer-reviewed.
- All $/exaflop-hour numbers are my arithmetic on reported capex/power, not published values.
