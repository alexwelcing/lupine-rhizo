> **Provenance:** explore agent `agent-12` (director-commissioned deep research, backdrop research, 2026-07-21) — materialized verbatim. Quantitative claims are as reported by the research agent from sources it accessed; see citations inline. Citation-verification pass pending before any external publication.

# Compute Resourcing for Atomistic Simulation + ML: Program Digest

Compiled 2026-07-21. Prices are volatile and region-dependent; all figures come from the cited pages — treat them as pointers, not quotes. Items I could not verify against a primary source are marked **[uncertain]**.

## 1. Public allocation programs

### US — NSF

**ACCESS** (XSEDE successor; NSF awarded $52M over 5 years) — [access-ci.org](https://access-ci.org/)
- Free; no NSF award required to start. Four project types, awarded in ACCESS Credits (1 credit ≈ 1 core-hour or 1 GB storage, per the [exchange calculator](https://allocations.access-ci.org/exchange_calculator)):
  - **Explore**: 400,000 credits, anytime, overview-only application, approval in ~1–2 business days
  - **Discover**: 1,500,000 credits, 1-page proposal
  - **Accelerate**: 3,000,000 credits, 3-page proposal, panel review
  - **Maximize**: awarded in resource units, 10-page proposal + code performance doc, semi-annual windows (next: Jun 15–Jul 31, 2026, awards start Oct 1, 2026) — [project types](https://allocations.access-ci.org/project-types), [prepare requests](https://allocations.access-ci.org/prepare-requests)
- Graduate students can be PI with an advisor letter. Resources include GPU clusters (Delta, Expanse, Anvil, ACES) and the Jetstream2 research cloud — useful for a mixed DFT + ML workflow.

**NAIRR Pilot** — [nairrpilot.org](https://nairrpilot.org). US-based researchers/educators; 3-page application; distributes HPC time (Frontera, Expanse/Voyager, Anvil, DOE AI testbeds) and cloud credits from AWS/Google/Microsoft/NVIDIA partners. 375+ projects supported. ML-for-materials fits its focus areas.

### US — DOE (open to any researcher worldwide, no DOE funding required)

- **INCITE** — flagship; awards ~60% of ALCF/OLCF time (Aurora, Frontier). Typical awards ~0.5–2.5M node-hours, 1–3 years, renewable. Annual call Apr–Jun (2026 call: Apr 11–Jun 16, 2025); 10% reserved for an Early Career Track. [ALCF INCITE page](https://www.alcf.anl.gov/science/incite-allocation-program), [doeleadershipcomputing.org](https://doeleadershipcomputing.org/)
- **ALCC** — DOE-mission-aligned, high-risk/high-payoff; 2025–26 cycle: 38M node-hours across 56 projects; now 1–3 year requests, proposals due ~late January, no pre-proposal. [DOE FAQ](https://science.osti.gov/ascr/Facilities/Accessing-ASCR-Facilities/ALCC/FAQ-Detail), [award announcement](https://content.govdelivery.com/accounts/USDOEOS/bulletins/3e88768)
- **Director's Discretionary (ALCF/OLCF)** — small "get started" awards, anytime; the realistic entry point for a small team before INCITE/ALCC. [ALCF programs overview](https://www.alcf.anl.gov/sites/default/files/2025-12/ALCF_2025ScienceReport.pdf)
- **NERSC (ERCAP)** — annual call (AY2026: opened Aug 11, 2025, due Oct 2025; year runs ~Jan 21–Jan 19). Requires DOE Office of Science funding alignment; quarterly usage-based reductions. [ERCAP guidance](https://docs.nersc.gov/allocations/ercap_2026/)

### Europe

**EuroHPC JU** (the PRACE successor for allocation purposes) — [access policy](https://eurohpc-ju.europa.eu/access-our-supercomputers/access-policy-and-faq_en)
- Free of charge for EU/associated-country researchers (academia, industry, public sector). JU manages 35% (petascale) to 50% (pre-exascale) of system capacity on LUMI, Leonardo, MareNostrum5, Jupiter, etc.
- Modes: **Benchmark** (≤3 months, monthly cut-offs), **Development** (≤1 year, monthly cut-offs), **AI & Data-Intensive** (SME/industry/public sector), **Regular** (~2 cut-offs/year, 12-page proposal), **Extreme Scale** (~2 cut-offs/year, e.g. Oct 17, 2025; tracks for scientific/industry/SME). [Call summary](https://www.it4i.cz/en/about/infoservice/news/gain-access-to-european-supercomputers-including-karolina-eurohpc-ju-announced-calls-for-2025), [LUMI calls](https://lumi-supercomputer.eu/current-open-calls-for-lumi-resources/)
- **PRACE itself no longer allocates compute** — it transformed into an association of users and HPC centres ("PRACE 3.0"); EuroHPC runs its own peer-review platform. [ESFRI Landscape 2024](https://landscape2024.esfri.eu/media/yiplqqqc/esfri-la-2024_section1-digit.pdf), [EuroHPC peer-review tender](https://www.developmentaid.org/tenders/view/1342030/)

### UK — ARCHER2 — [access page](https://www.archer2.ac.uk/support-access/access.html)

- Routes: **Driving Test** (800 CU, new users, incl. GPU test), **Pump Priming** (≤4,000 CU / 6 months, always open, ~2-week decision), **Access to HPC** (EPSRC, semi-annual), **Pioneer Projects** (large, ≤2 years), **HEC Consortia** (e.g. materials/chemistry consortia with continuous allocations — a practical route for a materials team), plus ARCHER2-on-EPSRC-grant.
- 1 CU = 1 node-hour (128 cores). Notional cost £0.20/CU (EPSRC/NERC), £0.39 otherwise. [Edinburgh DRS page](https://digitalresearchservices.ed.ac.uk/resources/archer2)
- **Caution**: ARCHER2 service ends **21 November 2026**; successor provision is not guaranteed — flagged on the official access page.

### China **[partially uncertain — thin English-language primary sources]**

- NSFC does not itself allocate supercomputer time; access runs through the National Supercomputing Centers (Guangzhou, Tianjin, Wuxi, etc.) via institutional agreements, paid services, or project-tied allocations (e.g., National Key R&D projects). **[uncertain — verify per-center]**
- New: the **National Supercomputing Internet (国家超算互联网, scnet)**, launched April 2024 by the Ministry of Science and Technology — a marketplace aggregating 200+ providers, 25+ resource types, 6,000+ software listings, 100k+ users; a "core node" with 100k+ AI cards reported online in 2026. [PRC State Council announcement](https://english.www.gov.cn/news/202404/12/content_WS66187785c6d0868f4e8e5f5c.html), [China Daily](http://qiye.chinadaily.com.cn/a/202409/26/WS66f4ed0ea310b59111d9b490.html). Practical access for a foreign-affiliated team is **uncertain**; typically via Chinese institutional collaborators.

## 2. Cloud research credit programs

| Program | Offer | How a small team qualifies | Link |
|---|---|---|---|
| **AWS Cloud Credit for Research** | Credits for on-demand + spot EC2; students ≤$5,000; faculty/staff uncapped; 1-year term | Rolling application, 90–120 day review; academic affiliation | [aws.amazon.com](https://aws.amazon.com/government-education/research-and-technical-computing/cloud-credit-for-research/) |
| **Google Cloud research credits** | Credits expire 365 days after redemption; faculty, PhD students, postdocs at accredited institutions in approved countries; application requires a 250-word proposal + pricing-calculator estimate. Award size not published — historically ~$5,000 **[uncertain]** | Online form, rolling | [edu.google.com](https://edu.google.com/programs/credits/research/) |
| **Azure Research Credits** | "Azure for Academic Research"; contact-form intake. Third-party listings cite up to ~$60,000 **[uncertain; institutional deals vary — e.g., Stanford HAI offers up to $50k]** | Rolling | [microsoft.com](https://www.microsoft.com/en-us/azure-academic-research/) |
| **Oracle for Research** | 12-month OCI credits (IaaS+PaaS, incl. HPC/GPU); amounts vary by proposal — UCL cites ~£50k average; a Fellows track adds cash awards | Application form, reviewed on impact/feasibility | [program PDF](https://www.oracle.com/a/ocom/docs/corporate/research-application-example.pdf), [UCL page](https://www.ucl.ac.uk/health/academic-careers-office/training-portfolios/data-arcade/acooracle-cloud-computing-credits) |
| **CloudBank** | NSF-funded billing/brokerage so NSF awardees can spend grant funds on AWS/GCP/Azure with negotiated discounts | US institution + NSF award | [cloudbank.org](https://www.cloudbank.org/) |
| **NAIRR Pilot** | Distributes partner cloud credits (see §1) | US-based, 3-page app | [nairrpilot.org](https://nairrpilot.org) |

### GPU-specialty clouds (verified list prices)

- **CoreWeave** ([pricing](https://www.coreweave.com/pricing)): 8×H100 HGX $49.24/hr on-demand (~$6.16/GPU-hr), spot $19.71/hr; 8×H200 $50.44/hr; 8×A100 $21.60/hr; GB200 NVL72 $42/hr/GPU; CPU-only AMD Genoa 192 vCPU $7.78/hr (~$0.04/vCPU-hr); reserved up to 60% off; **free egress**.
- **RunPod** ([pricing](https://www.runpod.io/gpu-instance/pricing), secure cloud, per-GPU): H100 $4.55/hr, H200 $5.93, A100 $2.72, RTX 4090 $1.10, L4-class $0.69; B200 $8.64; community cloud is cheaper.
- **Lambda** ([pricing](https://lambda.ai/service/gpu-cloud)): page is JS-rendered; third-party trackers (Apr 2026) put 1×H100 PCIe at ~$3.29/hr, SXM ~$4.29/hr **[secondary source]**.
- **Vast.ai** ([pricing](https://vast.ai/pricing)): marketplace; live prices (page didn't render numbers) but interruptible tier is 50%+ below on-demand; reserved (1/3/6-mo) up to 50% off. Typically the cheapest GPU source **[typical rates uncertain — check live]**.
- Big-3 comparison anchor: AWS p4d.24xlarge (8×A100) ≈ $32.77/hr on-demand ([usage.ai](https://www.usage.ai/blogs/aws/ec2/instance-types/what-are-ec2-instances/)); p5 (8×H100) is substantially higher **[exact current price uncertain]**. GPU-specialty clouds undercut big-3 GPU on-demand by roughly 2–5×, but lack InfiniBand-class fabrics except CoreWeave (and big-3 ND/p5/A3 tiers).

## 3. Economics

**Purchase models.** Spot/preemptible: AWS Spot up to 90% off, GCP Spot VMs 60–91% off, Azure Spot up to 90% off ([ProsperOps comparison](https://www.prosperops.com/blog/spot-instances/)). Verified example: GCP h3-standard-88 $4.92–5.97/hr on-demand vs $2.45/hr spot ([devzero](https://www.devzero.io/instances/gcp/h3-standard-88)). Reserved/committed: ~37–57% off 1–3 yr (AWS RI), up to 60% off (CoreWeave), up to 50% off (Vast). Batch DFT/MD is checkpointable and embarrassingly parallel → spot-friendly; long MD trajectories need fault-tolerant restart logic.

**Cloud HPC instances, verified prices (on-demand, cheapest region):**
- AWS **hpc6a.48xlarge** (96 AMD cores): $2.88/hr → **$0.030/core-hr** ([cloudprice.net](https://cloudprice.net/aws/ec2/instances/hpc6a.48xlarge)); hpc7g (Graviton3E ARM) exists and is cheaper **[exact price unverified]**.
- GCP **h3-standard-88** (Sapphire Rapids, HPC-only, 2 regions): ~$4.92/hr → ~$0.056/vCPU-hr; **c3-standard-88** $4.44/hr us-central1 ([devzero](https://www.devzero.io/instances/gcp/c3-standard-88)).
- Azure **HB176rs_v4** (176 Zen4 cores): from $5,256/mo ≈ $7.20/hr → ~$0.041/vCPU-hr ([cloudprice.net](https://cloudprice.net/vm/Standard_HB176rs_v4)). **HBv5** (custom EPYC 9V64H, up to 352 cores, 6.7 TB/s HBM3) reached **GA in November 2025** ([Phoronix](https://www.phoronix.com/review/azure-hbv5-amd-epyc-9v64h)); pricing **[uncertain — portal only]**.

**When cloud beats an allocation.** Reference point: ARCHER2's notional £0.20/node-hour ≈ £0.0016/core-hour — allocations are ~10–20× cheaper per core-hour than any cloud; ACCESS/EuroHPC/DOE are free outright. Cloud wins when: (a) the workload is bursty or small (<~100k core-hours), (b) you can't wait 3–9 months of review cycles, (c) you have credits making marginal cost $0, (d) you need elasticity (thousands of short jobs now, not queued), or (e) GPU inference/fine-tuning where big-3 managed tooling matters. Steady, large MPI workloads belong on allocations.

## 4. Community / sharing models

- **OSG OSPool (PATh, NSF-funded)** — the strongest current federated option for a US-affiliated team: free, fair-share, no allocation review; account + short consultation; HTCondor high-throughput model ideal for DFT screening ensembles and ML dataset generation (jobs <~10 hrs, <8 cores each); OSG-wide delivers >2B core-hours/year; documented computational-chemistry use (70M-molecule dataset regeneration). [OSPool registration](https://osg-htc.org/services/ospool-registration.html), [chemistry spotlight](https://osg-htc.org/spotlights/ospool-computation.html)
- **Volunteer computing**: BOINC ecosystem still active ([project list/competition](https://arstechnica.com/civis/threads/formula-boinc-2025.1507290/)); **Folding@home** (volunteer GPU molecular dynamics — same method family as MD, but run by the project, not usable as your cluster) and **GPUGRID** (BOINC, MD). Running your own BOINC project is possible but only pays off with a large volunteer base — not realistic for a small team.
- **World Community Grid** — corporate-philanthropic volunteer grid; materials/chemistry projects have run on it historically (e.g., Harvard Clean Energy Project). Transferred from IBM to Krembil Research Institute in 2021 **[current submission process uncertain]**.
- **WLCG** — heritage grid (~1M+ cores) but restricted to LHC collaborations; not accessible for materials work. **EGI** remains Europe's general research grid/cloud federation **[current onboarding terms not verified this session]**.
- Materials-specific federated compute doesn't exist at scale today; nearest things are ACCESS science gateways ([SGX3](https://sciencegateways.org/)) and data-sharing infrastructures (Materials Cloud/NOMAD), which share data, not cycles.

## Suggested stack for a small atomistic-sim + ML team

1. **Today**: ACCESS Explore (400k credits, ~2 days) + AWS/Google/Oracle research credits for GPU work.
2. **Throughput**: OSPool for screening ensembles; institutional cluster if available.
3. **Scale-up**: ACCESS Discover→Accelerate; EuroHPC Development→Regular if EU-affiliated; DOE Director's Discretionary → ALCC for exascale ambitions.
4. **Burst/ML training**: spot GPUs on CoreWeave/RunPod/Vast with checkpointing; reserved only for sustained GPU needs.

**Uncertain items to verify before publishing**: Google/Azure credit award amounts, Lambda and Vast live prices, Azure HBv5 pricing, AWS hpc7g price, China scnet practical access, WCG submission process, EGI onboarding, AWS p5 current on-demand price.
