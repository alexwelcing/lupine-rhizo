# Company Profile — SOURCE OF TRUTH

> Every deck, email, brand asset, and one-pager draws from here. When a fact
> changes, change it HERE and propagate. Keep numbers identical everywhere.
> Derived from `docs/brand/narrative.md` (canonical public narrative) and
> `docs/plans/market-winning-strategy.md` (category strategy) — this file is the
> RAISE-FACING layer; public surfaces stay unpitched per the brand rule.

Last updated: 2026-07-01  ·  Stage: research program with operating system + first published benchmark (pre-revenue)

---

## 1. One-liner (positioning statement)

> **Lupine Science turns humanity's measured record into machine-checked rails
> that make atomistic AI simulation trustworthy.**

Long form: For materials labs and industrial R&D teams who cannot trust
machine-learned interatomic potentials outside the narrow conditions where they
looked accurate, Lupine Science is an **error-geometry evidence system** that
measures where models fail, proves the failure structure with machine-checked
evidence, and ships correction operators that make any simulation cheaper and
more accurate. Unlike benchmark leaderboards, every claim carries a provenance
chain, a decidable theorem, and a public retraction path.

## 2. Purpose / mission

Advance the research frontier by making model failure a first-class scientific
object: measured, proven, corrected, and preserved — so scientists can trust
simulation the way they trust the instruments in their lab.

## 3. The problem

- **Who has it:** computational materials leads at national labs, university
  PIs, MLIP builders, and industrial R&D teams (battery, alloy, semiconductor,
  nuclear).
- **What it costs:** validation by brute force — e.g. the "big-cell tax": 3×3×3
  supercell re-runs cost **3.86×** more core-hours and buy no accuracy on cubic
  metals (measured, `mlip-elastic-benchmark/mlip-elastic-benchmark-funder-brief-2026-06-27.md`).
  Industry teams either over-validate (slow, expensive) or under-validate
  (silent wrong answers in expensive materials decisions).
- **Status quo:** MAE/RMSE leaderboards, ad-hoc per-lab validation scripts,
  trust-by-reputation. No provenance, no retraction discipline, no failure
  geometry.

## 4. The solution / product

- **One sentence:** a live evidence system (benchmark → hypothesize → prove →
  publish) whose output is machine-checked failure maps and correction
  operators ("the turbo": capture the residual vs the measured record, feed the
  structure back as boost).
- **Core insight others miss:** potential errors are not random — they have
  low-dimensional, correctable geometry; and historical measured data (the only
  non-rotting substrate in the stack) can anchor live correction.
- **Demo:** LUPI (browser WebGPU evidence viewer, lupi.live), Lupine Library
  (public corpus), glim-think ledger (25,575 claims, 24/7 autonomous loop).

## 5. Why now

Foundation MLIPs (MACE, CHGNet, Orb, SevenNet, UMA…) exploded 2023–2026 with
universality claims nobody can independently verify; labs are adopting them
into production workflows *now*. The validation gap is open, the lab
partnership artifact is built (`hpc/` — Apptainer + SLURM one-command lane),
and the window is a multi-year lab-cycle decision that is being made this year.

## 6. Market

- **Beachhead:** MLIP builders + computational materials labs (audit/evidence
  packs) → **first revenue wedge: Potential Trust Reports for industrial R&D**
  (risk reduction before trusting a potential in battery/alloy/semiconductor/
  nuclear decisions).
- **Bottoms-up:** [GAP — founder to size: # industrial materials R&D groups ×
  trust-report ACV; # MLIP teams × audit ACV.]
- **Expansion:** product ladder per strategy doc — free corpus → shareable
  evidence → audits → trust reports → private ledger infrastructure.

## 7. Traction / signal (as of 2026-07-01)

- **Headline:** the entire operating record below was built on **< $10k**
  [GAP — founder must define the boundary of this number precisely: compute
  only? incl. hardware? It WILL be diligenced and quoted.]
- 25,575 ledger claims; autonomous research orchestrator running 24/7 (claims
  timestamped ahead of founder's local clock, nightly).
- ~264 machine-checked Lean declarations; evidence→theorem pipeline verified
  end-to-end (LAMMPS logs AND GPU calculator lane → decidable theorems).
- First published benchmark with an honest negative result (v0.1 operator
  failure published alongside the v0.2 win — the retraction discipline is the
  brand).
- One-command HPC reproduction artifact for labs: built, not yet distributed
  (**readiness, not traction — do not overclaim**).
- Three-plane operating system: Cloudflare control plane + ledger, GCP GPU
  burst, local GPU discovery lane.

## 8. Business model

- **First wedge:** Potential Trust Reports — industrial teams pay per material
  family / potential before production adoption. [GAP: pricing hypothesis.]
- Later: failure-geometry audits for MLIP builders; private ledger + evidence
  workspace as infrastructure.
- Round is **research capital in science mode**: revenue wedge must be *proven*,
  not maximized, during this round.

## 9. Competition & moat

- **Real competitors:** status quo (in-house validation scripts), Matbench-style
  leaderboards, MLIP vendors' own eval suites.
- **Why we win now:** only system whose claims are machine-checked with custody
  chains and public retractions; category ownership of "error geometry for
  interatomic potentials."
- **Compounding moat:** the ledger accretes (measured record never deprecates);
  every validated run becomes evidence that guides the next; retraction
  discipline compounds trust that competitors cannot retrofit culturally.

## 10. Go-to-market

- **Motion:** lab partnerships via the one-command artifact (visitation
  package → visiting-lab runs → co-published evidence → named references) →
  industrial trust-report buyers arrive via lab credibility.
- **Early proof:** [GAP — outreach not yet started; first 3 lab conversations
  are a near-term milestone, not an asset.]

## 11. Team

- **Model: small human core + agent fleet.** Founder (Alex Welcing) operating a
  multi-agent autonomous research system — position as "the first AI-operated
  research lab" (differentiator, not gap). Round funds 2–4 research
  engineers/scientists to harden the oath chain at scale.
- **Key gap:** senior computational-materials scientific credibility for lab
  doors — advisor or scientific co-founder search runs alongside the raise.

## 12. The ask

- **Amount:** $12M · Instrument: [open — founder: structure is secondary;
  "science mode"] · Cap/valuation: [open]
- **Runway:** ~4 years at $3M/yr steady-state burn.
- **Milestones it funds (the 5% → 30% conversion — use THIS, never bare
  percentages):**

| Axis | Today (< $10k) | Post-round (24 mo) |
|---|---|---|
| Property families (Y) | 1 (elastic) | 7 (vacancy, surfaces, SFE, EOS, intermetallics, finite-T) |
| Models (X) | 3 architectures | 6+ foundation MLIPs |
| Materials | 16 cubic metals | 30+ incl. alloys, semiconductors, oxides |
| Correction operator | 1 scalar win (elastic-only) | cross-property operator, gearing determined |
| Labs running the artifact | 0 (package built) | 3–5 named labs, co-published reproductions |
| Revenue | 0 | first Potential Trust Report customers |

- **Series A gate:** correction operator demonstrably cutting error at a
  fraction of ensemble cost across multiple property families, reproduced at
  partner labs on their hardware, with first trust-report revenue.

### The $3M/yr speed note (founder-requested)

What changes at $3M/yr burn vs today's <$10k-total pace — grounded in the
actual cost ledger:

- **Statics are cheap; the constraint is breadth and hands.** Elastic cells
  cost ~0.0134 core-hours each — Tier-1 statics on today's single RTX A4500
  are weeks, not dollars. $3M/yr does not buy faster elastic constants.
- **What it actually buys:** (1) the **finite-T lane** (melting, thermal
  expansion via MD) and **defects/interfaces at scale** (supercells explode) —
  genuinely GPU-heavy, orders of magnitude beyond the discovery lane;
  (2) **full-grid statistical rigor** — multi-seed uncertainty across the whole
  X×Y×materials lattice instead of 4-element spot checks; (3) **2–4 research
  engineers** keeping the oath chain rigorous while the matrix scales;
  (4) **lab partnership support** (travel, integration engineering, co-pub).
- **Net effect:** the road from 5% → 30% compresses from a ~4–6 year
  single-operator crawl to **~18–24 months** — roughly a **10–20× wall-clock
  compression** on the parts that are actually rate-limited (finite-T, alloys,
  lab reproduction cycles), not a marginal speedup on the parts that are
  already cheap.

## 13. Value pillars

1. **Machine-checked evidence** — proof: evidence→Lean pipeline live; failed
   claims encoded as theorems too (`exceeds_tol`), never hidden.
2. **Radical capital efficiency** — proof: the entire operating record on
   <$10k [pending precise definition].
3. **The measured record as moat** — proof: provenance-wrapped reference base
   (`data/y_matrix_targets/`) built under a no-fabrication rule; bedrock
   doesn't deprecate.

## 14. Brand voice (inherit `docs/brand/narrative.md`)

- **Calm, empirical, alive to self-correction** — Do: "supported, refuted,
  corrected, open" / Don't: leaderboard hype.
- **Evidence-forward** — Do: numbers with provenance / Don't: unsourced claims.
- **Public surfaces are never pitch surfaces** — Do: let investors watch the
  operating record / Don't: put the ask on the Library or LUPI.

## 15. Visual basics

[Inherit from existing brand system — `docs/brand/`; not re-derived here.]

## 16. Founder narrative

[GAP — founder to tell it in his own words. Raw material from this session:
"my main effort here is to help advance the research frontier and help the
scientists, and I am the one with the system that does this right now."]

## 17. Top 3 risks + mitigations

1. **Cross-property transfer fails** (the ribbon is a coupling artifact) →
   mitigation: pre-registered either-way design; per-family operators still
   ship the trust-report product; the evidence system has value independent of
   the operator ("the turbo gets built either way — the experiment determines
   its gearing").
2. **Solo-founder key-person risk** → mitigation: agent fleet + ledger make the
   research state durable and inspectable; senior hires funded by the round;
   everything reproducible from the corpus.
3. **Labs are slow to adopt** → mitigation: one-command artifact removes
   integration cost; readiness already built; co-publication (not procurement)
   is the initial ask, which matches lab incentives.
