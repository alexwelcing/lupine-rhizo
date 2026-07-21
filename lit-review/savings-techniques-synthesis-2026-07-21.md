> **Provenance:** director synthesis, 2026-07-21. Draws on nine deep-research digests initially materialized verbatim in this directory (`savings-surrogate-neb.md`, `savings-active-learning.md`, `savings-delta-multifidelity.md`, `savings-abstention-economics.md`, `savings-dft-systems.md`, `savings-electronic-surrogates.md`, `savings-path-sampling-algorithms.md`, `supercomputing-atomistic-history.md`, `research-compute-resourcing.md`); six digests subsequently received narrowly scoped editorial corrections replacing the retracted 624/132 union-anchor figures. It also draws on two primary records: `data/candidates/z1-union-anchor-economics.json` (+ `docs/analysis/z1-union-anchor-economics.md`) and `docs/plans/2026-07-20-sparse-dft-pilot-preregistration.md`. The identifier-level citation audit in `citation-verification-2026-07-21.md` verified every extracted arXiv ID and DOI; literature numbers remain qualified by each digest's stated access level and [UNVERIFIED] claim flags. Every number marked **[derived]** is our arithmetic on stated inputs, not a published value.

# The savings stack and the theorem commons

**Scope:** compute-savings techniques in atomistic and molecular simulation, 2015–2026, organized as one argument: the field has independently discovered seven layers of savings, each layer has a known hole, and the holes are all the same shape — the absence of a *correctness certificate*. That shape is where Lupine lives, and it is why a shared, formally verified theorem library is not a philosophy but the next savings technology.

## 1. The argument in one paragraph

Atomistic simulation spent forty years making FLOPs cheaper (capex per peak PFLOP fell ~30× in a decade: Tianhe-2 ≈ \$7.1M/PF to El Capitan ≈ \$0.22M/PF — see `supercomputing-atomistic-history.md`) and the last ten years discovering that the real enemy is not the FLOP price but the *evaluation count*: how many times you must call the expensive oracle at all. Every successful savings technology of the ML era — active learning, surrogate NEB, Δ-learning, abstention gates — is an evaluation-count reduction with an unpriced correctness risk attached. Our measured contribution is that correctness-gated evaluation, shared across models, is itself a savings technology with a remarkable property: **four independent models of guidance cost only ~10% more DFT than one** (measured, §4). If that property generalizes — and the scaling curve says it should — then a commons in which teams contribute theorems and anchors back is a machine where *we all get faster together*, at no marginal cost to anyone.

## 2. The cost wall, briefly

The backdrop (full version in `supercomputing-atomistic-history.md`, `research-compute-resourcing.md`):

- Delivered supercomputing is cheap and getting cheaper: Frontier's electricity alone is roughly \$800–1,600 per HPL-exaflop-hour **[derived]**; real applications sustain 3–10× less than HPL, so useful-FLOP costs are correspondingly higher.
- Access is not the bottleneck for a small team: ACCESS Explore grants (~400k credits) land in days; INCITE/ALCC, EuroHPC, and Director's Discretionary pools exist above that; spot GPU clouds cover bursts.
- The bottleneck is that serious atomistic campaigns still price out in the thousands-to-millions of oracle evaluations. A dense CI-NEB band is ~50–100 energy/force evaluations per image-set convergence accounting (our preregistration's accounting basis); a reaction network or screening panel multiplies that by hundreds of paths; an honest multi-model uncertainty check multiplies again by the model count. FLOP prices falling 30× per decade does not rescue a workload whose evaluation count grows with ambition.

So the interesting question is never "what does a FLOP cost" but "who lets you make fewer oracle calls, and when are they wrong."

## 3. The seven savings layers, and the hole in each

Each layer below is covered in depth by its own digest; one strongest measured number is quoted per layer, with its hole.

1. **Surrogate-accelerated saddle search** (`savings-surrogate-neb.md`). Local GP surrogates cut true evaluations by ~an order of magnitude, replicated for a decade: Koistinen/Jónsson 2017 (JCP 147, 152720); Garrido Torres 2019 (PRL 122, 156001), 5–25× fewer calls, cost *decoupled from image count*; Goswami 2025 (JCTC 21, 7935), ~10× on 500 molecular reactions. **Hole:** GP variance is a sampling-density signal, not an accuracy bound (stated plainly in the 2026 tutorial review); each search re-trains and then *discards* its surrogate.
2. **Active learning** (`savings-active-learning.md`). Uncertainty/committee-triggered labeling removes 2–4 orders of magnitude of DFT: VASP on-the-fly MLFF skips >99% of first-principles steps (Jinnouchi/Kresse 2019); DP-GEN labeled 0.0044% of ~650M explored configurations (Zhang et al., PRM 3, 023804); FLARE trains reactive force fields in ~100–250 calls. **Hole:** every mainstream trigger is sufficient-but-not-necessary — DP-GEN's own authors concede the committee can agree and be wrong; FLARE's GP variance *underestimates* error under strong extrapolation; rare events are the documented miss.
3. **Δ-learning, multi-fidelity, transfer** (`savings-delta-multifidelity.md`). MatterSim fine-tuned to revPBE0-D3 water with **30 high-fidelity configurations vs 900 from scratch** (30×; arXiv:2405.04967); DPA-2 reports 1–2 orders less downstream data; classic Δ-ML reaches DFT enthalpies from 1–10% of the labels (Ramakrishnan 2015). **Hole:** fine-tuning reintroduces PES softening (OMat24 analysis), fails out-of-distribution, and costs a training run *per model per chemistry* — the wrong shape for breadth.
4. **Abstention economics** (`savings-abstention-economics.md`). The cleanest production measurement: AdsorbML finds the DFT-level adsorption minimum in 87.4% of ~1000 systems while paying full DFT only on the ~13% tail (Lan et al., npj Comput. Mater. 2023). **Hole:** no published budget prices abstention *across models* — every number is per-model/per-potential. The cross-model sharing economy is unmeasured territory.
5. **Systems-level DFT acceleration** (`savings-dft-systems.md`). GPU ports give 3–20× per node above a size threshold; reduced-rank exact exchange (ACE/ACE-ISDF) cuts hybrid-DFT cost ~2 orders (1,000-atom Si HSE in 10 min on 2,000 cores); Periodic Pulay gives 3× fewer SCF iterations on hard metals; ML density guesses cut ~20–33% of SCF iterations (ELECTRAFI: −20% *total* cost). **Hole:** these cut the cost *per evaluation*, not the count — and the aggressive settings (mixed precision, loose mixing) carry exactly the silent-failure risk that gates exist to catch.
6. **Electronic-structure surrogates** (`savings-electronic-surrogates.md`). ML Hamiltonians eliminate 100% of SCF at inference (DeepH: 10³× on a MoS₂ supercell; HamGNN: 4,284-atom Si Hamiltonian in 36 s); M-OFDFT reaches chemical accuracy at 27.4× on a 738-atom protein. **Hole:** predicted Hamiltonians do not give variationally reliable energies/forces for MD or NEB — and ML functionals fail silently (DM21's transition-metal convergence failures).
7. **Path and sampling algorithms** (`savings-path-sampling-algorithms.md`). Freezing/growing-string: a TS guess in ~20–90 gradient calls (Marks et al.); ART nouveau converges a DFT saddle in 50 force evaluations vs 463 unbiased; REST2 folds trpcage with 10 replicas where T-REMD needs 48; OPES explores ~10× faster than WTMetaD. **Hole:** cheap exploration distorts or skips the TS region (OneOPES says so explicitly), and string methods converge to second-order saddles at measured rates (2/16, 7/24 in Marks et al.) — a *wrong-curvature* failure that is, note, a violated-theorem condition.

Seven layers, one repeated hole: **no certificate.** The field's triggers, variances, and committees all estimate *where the model is probably wrong*. None can say *where physics is definitely violated*.

## 4. What we have measured ourselves

All numbers in this section trace to committed records; nothing here is from chat memory.

**Sparse anchors work on real metal.** Path mp-760344, sparse barrier 0.5567 eV vs reference 0.5244 eV → **32.2 meV error, WIN** against the frozen ≤40 meV gate. Anchor cost on a 4-vCPU local box: 2,483–3,668 s each (~48 min mean, ~3.2 vCPU-hours, ~\$0.19 at \$0.06/vCPU-h **[derived]**). Known line item: the GPAW-vs-VASP convention offset drifts ~122 meV along the profile (tracked as theorem-line T1).

**The sparse protocol was validated before any DFT ran.** On recorded campaign artifacts, the preregistration's simulation showed sparse-protocol barrier MAE of 1.2–9.4 meV at ~7 anchors/path versus ~50–100 dense evaluations, with the saddle image located exactly on 82–86% of paths and within ±1 on 89–93% (`docs/plans/2026-07-20-sparse-dft-pilot-preregistration.md`).

**Union anchors: the measured sharing economy** (`data/candidates/z1-union-anchor-economics.json`, recomputed 2026-07-21; supersedes earlier informal figures of 624/132/79%, which were arithmetic drift and are retracted):

- **558 naive per-model anchors vs 154 union anchors across 29 analyzable paths → 72.4% fewer DFT evaluations (3.62×).** On the 26 fully-covered paths: 520 vs 136, 73.8% (3.82×).
- One path (index 14, `mp-756912_1_1_1_0_0`) is unanalyzable — it failed CI-NEB convergence in all four model artifacts. The panel denominator is 29 of 30, on record.
- Cross-model agreement: identical predicted saddle image on 20/29 paths (all-four basis; 26/29 within ±1); both extrema within ±1 on 12/29.
- **The scaling law is the headline.** Mean over model subsets as model count k goes 1→4: naive grows 139.5 → 279 → 418.5 → 558, while union grows 139.5 → 147.8 → 152 → **154**. Four models of guidance cost ~10% more DFT than one. Cross-model validation — the thing everyone agrees multiplies cost — is nearly free at the oracle.

**The multiplicative stack [derived estimate, undemonstrated as a product].** Union-sparse evaluation (154 anchors vs a 4-model dense accounting of 4 × 50–100 = 200–400 per path) is a ~38–76× reduction in evaluation count; per-anchor cost levers from layer 5 (mixed precision ~2×, ML density guess ~1.25×) compose orthogonally to ~95–190×. Each factor is individually cited; the product is ours to demonstrate — that demonstration is the pilot program now running.

## 5. The theorem commons

Here is the network effect, stated as an engineering property rather than a hope.

**Theorems are non-rival goods with zero marginal sharing cost.** A Lean-checked physical-law theorem — curvature signature at a first-order saddle, energy–force consistency, symmetry constraints, boundary conditions — is contributed once and then gates every simulation for everyone, forever. Unlike training data, a theorem leaks nothing about the contributor's chemistry or commercial targets. It is the shareable residue of work a serious team does anyway: every failed simulation is a candidate theorem, and *formalizing your own failure* converts your most expensive knowledge into a permanent asset for the commons that pays you back in everyone else's theorems.

**The demand side already exists — the literature is asking for it.** Seven digests, working independently, came back with the same hole: learned triggers are sufficient-not-necessary (DP-GEN), GP variance saturates (FLARE), ensemble σ decorrelates from true error (Annevelink–Viswanathan line), fast exploration skips the TS region (OneOPES), string methods land on second-order saddles (Marks), ML functionals fail silently (DM21). Every one of those failure modes is a *physical-law violation detectable without learning anything*. A commons of formal theorems is precisely the supply for a demand the field has been circling for five years.

**Union anchors are the evaluation-side commons, and we have already measured its economics.** Within one lab, four models share anchors at 72–74% savings, sub-linearly with model count (§4). Across labs the same arithmetic applies to anchor *libraries*: a content-addressed store mapping structure-hash → DFT energy/forces lets one team's anchor validate every other team's model on the same path. Where theorems are zero-leak by construction, anchor sharing is opt-in per project — the commons has two tiers and members choose their exposure.

**The contribution loop.** Run your campaign on the commons → your model's failures are caught by existing theorems (you save evaluations immediately) → your *novel* failures get formalized as new theorems (you contribute) → every member's gates get sharper (false-accept and false-reject rates both fall) → evaluations saved compound across the network. The gate quality is a monotone function of membership. That is what "we all get faster together" means mechanically: **the commons converts each team's worst day into everyone's permanent speedup.**

## 6. What we do not claim

- For a single isolated saddle search with a cheap oracle, local GP surrogates win outright — the honest literature says so, and so do we. Our wedge is amortized, multi-path, multi-model workloads: panels, networks, screening campaigns.
- For one stable, high-volume chemistry, fine-tuning is the right tool. Runtime correction is for breadth, for barriers, and for not paying a training run per model per chemistry — and it avoids fine-tuning's documented PES-softening and OOD failures by construction.
- Our measured basis is one 30-path barrier panel, four uMLIPs, one DFT engine (GPAW, frozen PBE/fd settings), one chemistry family. The stacking figure in §4 is a derived estimate, not a measurement. The union scaling curve is four points deep.
- The nine digests retain their own [UNVERIFIED] claim flags. The identifier audit verified 115 unique arXiv IDs and 48 unique DOIs and reconciled the VASP MLFF venue ambiguity: PRB 100, 014105 / arXiv:1904.12961 is the melting-point paper; PRL 122, 225701 is the distinct earlier hybrid-perovskite demonstration. Identifier verification does not upgrade abstract-only evidence or validate every quantitative claim.

## 7. Next measurements

1. **Chgnet × 23 active paths** (local pilot, running): verdict against the ≤40 meV gate plus measured wall-hours — replaces the derived unit-cost figures with measured ones. Seven ≥159-atom paths deferred (`data/candidates/z1-sparse-dft-deferred.json`), verdicts PENDING, not excluded.
2. **Union-anchor driver variant:** evaluate the 154 unique anchors once and assemble per-model barriers from the shared pool — the direct experimental test that shared evaluation loses nothing vs per-model evaluation.
3. **Gate-versus-gate pricing:** theorem-gate false-accept/false-reject rates against a GP-variance gate on the same panel, in units of barrier error per DFT call — the abstention-economics baseline the literature lacks.
4. **Convergence-loosening revalidation:** Gamma-point vs (2,2,2) and h=0.20 vs 0.18, one path each, adopt-if-≤5 meV — a further 4–8× and ~40% per-anchor lever pending a preregistration amendment.

## References

Primary records: `data/candidates/z1-union-anchor-economics.json`; `docs/analysis/z1-union-anchor-economics.md`; `tools/analysis/union_anchor_economics.py`; `docs/plans/2026-07-20-sparse-dft-pilot-preregistration.md`; `data/candidates/z1-sparse-dft-deferred.json`.
Digests (this directory): the nine files listed in the provenance header. Literature citations live inside the digests with per-item access level (full text vs abstract) and [UNVERIFIED] flags.
