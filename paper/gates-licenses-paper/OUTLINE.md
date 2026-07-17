# Calibrated Trust for Foundation MLIPs: Per-Property Gates, Class-Native Licenses, and Theorem-Gated Corrections

**Methods-paper skeleton — 2026-07-13. Drafting authority: the errata-corrected record.**

> **Grounding rule (binding).** Every claim in this outline cites an artifact in this
> repository. The controlling document is
> `docs/plans/2026-07-13-errata-and-red-team-dispositions.md` (the errata): any number or
> framing it withdrew MUST NOT appear in any draft built from this outline. Corrections that
> require new computation are REGISTERED in
> `docs/plans/2026-07-13-round3-preregistration.md`, never silently patched (house rule,
> errata header). Registration-obligation tags used below:
> - `[WITHDRAWN — errata #N]` — must not appear in the paper.
> - `[REGISTERED — R3]` — claim/fix is frozen in the Round-3 prereg; cite the prereg, not an outcome.
> - `[OPEN — pending R3 verdict]` — section slot exists, text must not be drafted until the verdict artifact lands.

## 0. Claim hygiene — the do-not-say list

Withdrawn or demoted claims that reviewers of any draft should grep for and reject:

1. Pooled "gate efficacy 1.8x" — Simpson's artifact of class composition. Risk–coverage is
   reported **within class only**, with control false-refusals tabulated. `[WITHDRAWN — errata #3]`
2. "60–346x defect-vs-bulk dispersion ratio" — normalization artifact (energy vs length
   dispersions non-commensurable). Only absolute spreads (0.5–1.8 eV) and the vs-B0 / vs-C11
   ratios (2–34x / 0.8–8.5x) may be stated; negative-E_vac cells flagged invalid, never
   pooled; Sn rows labeled n=3 MACE-family-only. `[WITHDRAWN — errata #10]`
3. "Round 2 confirmed the correction layer" — Round 2 is **exploratory rule selection**
   (rule chosen after seeing Round-1 fail, evaluated on the same 9 candidates). `[errata #1]`
4. "The sign gate is theorem-based" — the implemented gate is NOT licensed by
   `wrong_direction_*_worsens` (the theorem requires the *target's* error side as
   hypothesis; the code checks only classmate consensus). Correct statement: "the gate
   excludes one failure mode on calibration members." The FeNi B0 / mace-mp-small
   counterexample (pred 143.1 < ref 176.7, deflated anyway) must be reported. `[errata #2]`
5. "Perovskite c12 median improved 36.04% → 18.91%" — withdrawn until Round-1/2 arm tables
   are regenerated with the preregistered exclusions (CsSnI3 Cij, CsGeI3 a0) applied and
   absolute-GPa deltas alongside. `[WITHDRAWN pending regeneration — errata #5]`
6. "B0 concordance is an uncertainty statement" — demoted to descriptive program-wide
   (fcc rho = −0.63). Only Born (exact physics) and bcc a0 (rho 0.89, n=7) currently carry
   an empirical dispersion→error license. `[errata #4]`
7. thresholds.v3 perovskite class as an out-of-sample license — it is circular
   (calibration corpus = the gated candidates, rho = 1.0 on the same 5 compounds); marked
   provisional/in-sample until Round-3 creates an out-of-sample perovskite corpus. `[errata #6]`
8. "asym = 0.0000 shows NEB convergence" — it is a builder symmetry identity; the
   endpoint-vs-band-minimum check replaces it. `[errata #12; REGISTERED — R3 fix 4]`

---

## 1. Motivation: five targets, five failure modes

Thesis: foundation MLIPs do not fail with one error bar. On the five preregistered target
properties (a0, B0, C11, C12, C44) the Round-1 record exhibits five *structurally different*
failure modes, and each one defeats a different naive trust strategy. This is why trust must
be per-property, per-class, and refusal-first.

- **1.1 a0 — bias sign flips by class.** HEA fcc candidates are *under*-predicted
  (all 16 cells; e.g. CoCrNi 3.521–3.534 vs 3.560 Å) while cubic halide perovskites are
  *over*-predicted (e.g. CsSnCl3 5.613–5.661 vs 5.579 Å), so any cross-class de-bias is
  provably wrong-direction for one class: the Round-1 cross-class correction worsened HEA a0
  in 16/16 cells (p = 3.1e-5). Source: `data/candidates/round1/REPORT.md`,
  `data/candidates/round1/criteria_evaluation.json`.
- **1.2 B0 — the ensemble can be confidently wrong.** On elemental fcc metals, cross-model
  dispersion is *anti-correlated* with true error (Spearman rho = −0.63, n = 9): e.g. Au B0
  dispersion 0.088 with 26% median error. Agreement is not accuracy. Source:
  `data/discovery_gates/dispersion_vs_error_by_class.json`.
- **1.3 C11/C12 — reference weakness dominates the error budget.** CsSnI3's C12 reference
  (1.22 GPa, DFT, flagged WEAK pre-freeze) turns ordinary prediction scatter into 260–435%
  cell errors; without pre-registered exclusions this one cell dominates the class median.
  Source: `docs/plans/2026-07-13-unbiased-accuracy-campaign.md` (targets, S4 exclusions);
  errata #5.
- **1.4 C44 — shear softening down to unphysicality.** CHGNet collapses perovskite C44
  (CsSnI3: 0.15 vs 5.74 GPa reference) and drives the known-good control CsPbI3 to a
  *negative* C44 (−1.54 GPa), i.e. a Born-unstable prediction for a synthesized compound.
  Separately, the relative-dispersion metric itself is undefined at sign-crossing medians
  (elemental V C44), a metric pathology now fixed by a registered denominator floor.
  Sources: `data/candidates/round1/REPORT.md`; errata #7; floored metric in
  `data/discovery_gates/thresholds.v3.json` `[REGISTERED — R3 fix 1]`.
- **1.5 Beyond elastics — energetics soften, and dispersion cannot see finite-size error.**
  All four models underestimate Schottky pair formation 40–105% vs conductivity-derived
  anchors (§3.2); one cell is unphysically negative (CHGNet LiI −0.083 eV, flagged invalid).
  Barrier panels are single-supercell, so finite-size error is common-mode and invisible to
  cross-model dispersion *by construction*. Sources:
  `data/defects/schottky_panel/panel_summary.json`; `data/kinetics/barrier_panel/REPORT.md`;
  errata #10, #11.

Framing paragraph: the cheapest true statement in materials AI is a fast, justified no
(`docs/discovery-formalization-protocol.md`); the paper's contribution is making the "no"
carry a machine-checkable certificate and making every "yes" carry a license with provenance.

## 2. The instrument: same-probe calibration, determinism, refusal-first gates

- **2.1 Same-probe calibration.** Concordance thresholds are p75/p95 percentiles of
  cross-model relative dispersion measured by the *same* relax → EOS → strain pipeline on a
  21-material reference-bound baseline — no invented thresholds; the derivation is in the
  artifact. v2: per-property thresholds (a0/B0/C11/C12/C44 each gated by its own baseline).
  v3: class-native thresholds from per-class corpora. Sources:
  `data/discovery_gates/REPORT.md`; `data/discovery_gates/thresholds.v2.json`, `thresholds.v3.json`;
  protocol `docs/plans/mlip-elastic-benchmark-protocol-2026-06-27.md`.
- **2.2 Dispersion metric (floored-v1).** (max−min)/max(|median|, 0.1 × class-median |value|),
  registered fix for the sign-crossing C44 pathology; v2/v3 regenerated under the fixed
  metric; unfloored variants retained for audit (`thresholds.v3.unfloored.json`).
  `[REGISTERED — R3 fix 1]`
- **2.3 Determinism and provenance.** Fixed RNG seed (20260713) and a single recorded RSS
  configuration per HEA candidate; recorded calculator versions (chgnet 0.4.2,
  mace-torch 0.3.16); schema-versioned evidence JSONs per cell; wall-times per gate;
  seed-variance subset shows ~0 GPa MAE std dev
  (`mlip-elastic-benchmark/operator-failure-diagnosis-2026-06-27.md`, variance subset).
- **2.4 Gate ladder with early-stop and finality.** Born (exact physics) → per-property
  concordance → dynamic-return probe, early-stop ordered; a refusal is final, so skipped
  probes change no verdict (Theorem §4.1); wall-time result: verdicts identical by
  construction, expensive probes paid only by survivors (Li2S 29.9 s vs refused LiS 15.7 s).
  Source: `data/discovery_gates/REPORT.md`.
- **2.5 Scoring discipline.** Gates are scored as selective prediction (within-class
  risk–coverage, control false-refusals tabulated); corrections are scored by preregistered
  per-property medians + exact binomial sign tests, ties dropped.

## 3. Results, in the honest hierarchy

Ordering principle (this is the paper's spine): **exact physics > preregistered kill >
referenced absolute findings > class-licensed dispersion > exploratory selection >
[open confirmatory slot]**. Each subsection states its rung.

### 3.1 Round 1: the preregistered kill (strongest artifact — lead with it)

- Design frozen before any prediction ran (`docs/plans/2026-07-13-unbiased-accuracy-campaign.md`);
  9 candidates (4 HEA fcc, 5 cubic halide perovskites incl. known-good control CsPbI3),
  4 models, 5 properties, null-discipline on unverifiable references.
- Preregistered criterion (de-bias improves ≥ 2 of 3 property legs per group, sign-test
  p < 0.1) — **FAILED in both groups**, computed post hoc as a registered fix because the
  primary statistic was never computed at the time `[errata #8]`:
  - HEA: 0/3 legs. a0 worsened 16/16 (p = 3.1e-5), B0 worsened 13/16 (p = 0.021, median
    9.06% → 16.89%), Cij leg had zero corrected cells (silent bias-load failure; the 3-leg
    denominator is kept, not degraded to 2-of-2).
  - Perovskite: 1/3 legs (a0 improved 16/16, p = 3.1e-5; B0 p = 0.82; Cij zero cells).
  - Source: `data/candidates/round1/criteria_evaluation.json` (verdicts verbatim: FAIL, FAIL).
- The kill is the credibility anchor of the whole paper: preregistered, failed, reported as
  failed (errata: "What survives untouched").
- Correction-direction laws (§4.4) make the Round-1 harm mechanism a theorem: calibration
  bias sign (elemental fcc under-predicts B0) opposite to the target class's error sign
  (HEA already over/near reference) ⇒ inflation provably worsens.

### 3.2 The softening dichotomy (referenced absolute numbers only)

Claim shape: *foundation MLIPs systematically soften defect formation energetics while
placing migration-barrier scales inside the ab-initio envelope — thermodynamics soft,
kinetics roughly right — and both statements are made in absolute eV with stated
conventions.*

- **Schottky (thermodynamics, softened).** All models underestimate Schottky pair formation
  by 40–105% vs conductivity-derived experimental anchors while preserving the halide-series
  ordering (LiF > LiCl > LiBr > LiI). CHGNet LiI is negative (−0.083 eV) — flagged invalid,
  never pooled. Cross-model absolute spreads 0.5–1.8 eV. Conventions stated: neutral cells,
  2×2×2 rocksalt, anchors are conductivity-derived. Sources:
  `data/defects/schottky_panel/panel_summary.json`; errata "survives" list + #10.
- **Barriers (kinetics, in-envelope).** Cation-vacancy <110> CI-NEB, 5 interior images,
  fmax 0.05 eV/Å: LiF MACE-family barriers 0.59–0.68 eV vs neutral PBE-NEB comparators
  0.66–0.73 eV (the only convention-consistent absolute anchor); cross-model spreads
  0.13–0.20 eV reported as ABSOLUTE numbers; experimental dH_m used for trend/ordering only.
  Sources: `data/kinetics/barrier_panel/REPORT.md`; errata #11.
- Honesty boundary carried into the text: single 2×2×2 supercell ⇒ finite-size error is
  common-mode and invisible to dispersion by construction; one 3×3×3 scaling point per
  compound is registered *before* any kinetics threshold derivation `[REGISTERED — R3 fix 4]`;
  endpoint-vs-band-minimum convergence check replaces the symmetric-asymmetry identity
  `[errata #12]`.

### 3.3 The license table: when is cross-model agreement evidence?

Core methodological result: a dispersion gate earns a *license* per (class, property) by
measured rank correlation between dispersion and true error — and the paper prints the
licenses it does NOT have with the same prominence as the ones it does.

| class | property | Spearman rho (dispersion vs median rel. err) | n | license verdict |
|---|---|---|---|---|
| metals-fcc | a0 | 0.07 | 9 | none — dispersion uninformative |
| metals-fcc | B0 | **−0.63** | 9 | **refused — anti-correlated ("confidently wrong")** |
| metals-bcc | a0 | 0.89 | 7 | licensed (small n) |
| metals-bcc | B0 | 0.32 | 7 | none |
| perovskites | a0 | −0.80 | 4 | refused + circular corpus `[errata #6]` |
| perovskites | B0 | 1.00 | 5 | provisional/in-sample only `[errata #6; REGISTERED — R3 fix 2]` |
| any class | Born stability | exact physics | — | always licensed (necessary conditions) |

- Pooled (unstratified) correlations for contrast: B0 rho 0.16, a0 rho 0.57 — pooling both
  hides the fcc anti-correlation and understates the bcc license (Simpson-flavored, ties to
  errata #3). Source: `data/discovery_gates/dispersion_vs_error.json`,
  `dispersion_vs_error_by_class.json` (caveats field is quotable verbatim).
- B0 concordance demoted to descriptive program-wide; LiS's REFUSED verdict survives
  independently on Born (all four models C44 < 0) — the load-bearing refusal is exact
  physics, not calibration `[errata #4]`. Source: `data/discovery_gates/REPORT.md`.
- Within-class risk–coverage, with the control refusal reported as a false positive:
  the gate refused the most accurate HEA and the known-good CsPbI3 control (Born FAIL from
  CHGNet's C44 = −1.54 GPa): HEA issued 4.31% vs refused 1.81%; perovskites 10.08% vs
  11.28% `[errata #3 numbers; descriptive split also in criteria_evaluation.json
  gates_descriptive]`. No pooled cross-class ratio anywhere.

### 3.4 Round 2: exploratory rule selection (labeled as such, no confirmatory language)

- Relabeled per errata #1: sign-gate rule, LOO-median estimator, min-members = 2 were chosen
  AFTER Round-1 failure and evaluated on the same 9 candidates. Report as hypothesis
  generation with in-sample deltas only; 69 corrections applied / 71 abstained.
  Source: `data/candidates/round2/REPORT.md`.
- Reportable exploratory observations (with the withdrawn-pending flag): in-class LOO
  medians improved perovskite a0 1.41% → 0.48% and HEA a0 0.84% → 0.17%; Cij deltas are
  `[WITHDRAWN pending exclusion-applied regeneration — errata #5]`.
- The gate's known failure inside its own calibration data: FeNi B0 / mace-mp-small received
  a theorem-forbidden deflation (classmate consensus ≠ target side) — motivates the
  registered magnitude cap (abstain unless |b−1| > ratio spread). `[errata #2; REGISTERED — R3]`

### 3.5 Round 3: out-of-sample confirmatory trial — scope narrowed

- Report the frozen registration and executed disposition:
  `docs/plans/2026-07-13-round3-preregistration.md` — frozen rule (direction gate + magnitude
  cap + abstention), evaluation set (perovskites CsPbBr3/CsPbCl3/RbSnBr3/KSnCl3 with
  fluoroperovskite fallbacks; rocksalts KCl/KBr/RbCl/NaF), primary statistic (per group ×
  property median |rel err| raw vs corrected + exact sign test), SUCCESS/FAILURE criteria,
  and the KILL condition. Round-3 supports only same-class a0 in the preregistered rocksalt
  and perovskite groups. B0 improvement was contradicted, so its runtime gate returns
  `deny` / `contradicting_evidence`; cross-class and universal correction remain unsupported.

## 4. Theorems: what the formal layer actually licenses

All in `lean-spec/LupineEvidence/Shapes/Certificates.lean` (0 sorry, decidable predicates,
kernel-checked via `decide`) unless noted. Frame honestly: these certify the *logic and
arithmetic of the trust layer*, not the physics of any prediction — and say so (errata:
migration certificates "certify arithmetic, and say so").

- **4.1 Refusal finality.** `no_monotone_fix` + `orderJustified_uncorrectable`: an
  order-justified refusal (prediction order inverts reference order) cannot be repaired by
  ANY monotone correction — refusals are final, which is what licenses the early-stop gate
  order. Live instance: SFE Ni/Al inversion under mace-mp-small (witnesses in-file).
- **4.2 Threshold-migration laws.** `refused_stable_under_tightening`,
  `unrefusal_needs_looser_threshold`, `deconcordance_needs_tighter_threshold`: v1→v2→v3
  recalibration verdict flips are kernel-checked consequences of the threshold delta, never
  fresh claims — every un-refusal must exhibit a looser-threshold witness.
- **4.3 Ensemble-hull Born refusal.** `hull_born_refusal_c44` / `_shear` / `_volumetric`:
  if the axis-aligned hull of ensemble predictions violates a Born inequality at its
  favourable endpoint, EVERY tensor in the hull is unstable — the refusal covers the whole
  ensemble range, not just sampled models. Live instance: rocksalt LiS (all four models
  C44 < 0 ⇒ c44max ≤ 0).
- **4.4 Correction-direction laws.** `wrong_direction_inflation_worsens` /
  `_deflation_worsens` + `directionVerified` (calibration-sign × in-class-anchor-sign > 0):
  the Round-1 harm as arithmetic, with the recorded HEA B0 witness (raw 194.0 vs ref 163.0
  inflated to 226.5 — strictly worse, by law).
- **4.5 Scope-honesty subsection (required by errata #2).** State explicitly: the
  *implemented* Round-2/3 gate checks classmate consensus, which is strictly weaker than the
  theorems' hypothesis (the target's own error side). The theorems license abstention
  semantics and the failure-mode taxonomy; they do NOT certify the gate's decisions. Round 3
  registers either (a) a Lean theorem matching the implemented gate + magnitude cap, or
  (b) removal of all theorem language from correction claims. `[REGISTERED — R3]`
- Adjacent formal scope boundary: hull-level thermodynamic screening is proven *strictly
  incomplete* (`hull_screening_strictly_incomplete`,
  `OpenDistillationFactory/Materials/Theory/DefectStability.lean`) — mechanical stability
  gates never claim thermodynamic stability (matches
  `data/discovery_gates/REPORT.md` scope notes).

## 5. Related work (DRAFTED — citations verified 2026-07-13, incl. web check of PCM)

- **5.1 PROBE — engaged head-on.** Mehdi, Cho, Isayev, *Knowing when to trust
  machine-learned interatomic potentials*, arXiv:2605.00640. PROBE's critique: ensemble
  member-disagreement correlates weakly with per-prediction error, so dispersion gating
  risks being a normality test, not an uncertainty statement. Our response is structural,
  not defensive: (i) we *measured* the critique on our reference-bound corpus
  (`data/discovery_gates/dispersion_vs_error.json`, run explicitly as the PROBE answer —
  pooled B0 rho 0.16 CONFIRMS the critique at the pooled level); (ii) the license table
  (§3.3) is the consequence — dispersion is admitted as evidence only per (class, property)
  where the correlation is measured and positive, refused where it is ~0 or negative
  (fcc B0 −0.63), and bypassed entirely where exact physics gates exist (Born);
  (iii) PROBE's learned per-atom reliability classifier is complementary — it produces a
  score, our gates produce decidable certificates with provenance; a PROBE-style classifier
  could serve as a Gate-0 coverage proxy in our ladder.
- **5.2 Conformal calibration.** Ho, Ortner, Wang, *Flexible Uncertainty Calibration for
  Machine-Learned Interatomic Potentials*, arXiv:2510.00721. Environment-dependent quantile
  functions inspired by conformal prediction, on MACE-MP-0. Relation: their
  environment-dependence concedes exactly our premise — one global calibration does not
  hold; class-native licenses are the discrete, provenance-first analog. Contrast: conformal
  gives marginal coverage over an exchangeable calibration set; our record shows class
  structure breaks exchangeability across classes (a0 bias sign flip, §1.1), so we calibrate
  within class and refuse across.
- **5.3 Committee/ensemble UQ at reduced cost.** Kellner, Ceriotti, *Uncertainty
  quantification by direct propagation of shallow ensembles*, arXiv:2402.16621; Beck,
  Simko, Schaaf, Marsalek, Schran, *Multi-head committees enable direct uncertainty
  prediction for atomistic foundation models*, arXiv:2508.09907. Both attack the COST of
  committee UQ (shallow ensembles; frozen-base multi-head committees). Orthogonal to us:
  cheaper committee variance inherits the license problem unchanged — variance is only
  evidence where dispersion tracks error, which is class- and property-local in our record;
  also note our N_eff caveat cuts against naive committees (MACE variants share training
  data — dispersion is ensemble spread, not independent error, §6).
- **5.4 Survey-scale elastic benchmarking.** Gao, Wang, *Benchmarking Universal Machine
  Learning Interatomic Potentials for Elastic Property Prediction*, arXiv:2510.22999
  (~11,000 elastically stable materials; MatterSim/MACE/SevenNet/CHGNet). Relation: they
  establish pooled accuracy hierarchies at scale; we make per-candidate trust decisions at
  n=1 with provenance. Their corpus is a natural source for the out-of-sample class corpora
  our licenses require (esp. the missing perovskite corpus, `[REGISTERED — R3 fix 2]`).
- **5.5 Proof-Carrying Materials.** Basu, Chakraborty, *Proof-Carrying Materials:
  Falsifiable Safety Certificates for Machine-Learned Interatomic Potentials*,
  arXiv:2603.12183. **Verified by web read 2026-07-13** (was previously cited-unread; now
  read): adversarial falsification across composition space + bootstrap envelope refinement
  + Lean 4 certification; headline motivation: a single MLIP used as a stability filter
  attains recall 0.07 on a 25k-material DFT-stable benchmark; risk model AUC 0.938,
  cross-architecture transfer, +25% discovery yield in thermoelectric screening. Closest
  prior art for machine-checked MLIP trust; differences to state precisely: (i) PCM
  certifies statistical envelopes of a learned risk model; our certificates are per-claim
  decidable propositions (Born instances, concordance zones, refusal finality) checked by
  the Lean kernel on the candidate's own numbers; (ii) PCM's blind-spot finding (minimal
  cross-architecture error correlation) is consistent with our class-local error geometry;
  (iii) their recall-0.07 result is independent motivation for refusal-first screening. Cite
  their falsification stage as the template for adversarially stress-testing our gates
  (future work).
- Supporting/background (already in-house): Deng et al. systematic softening
  (arXiv:2405.07105) for §3.2 framing — see `paper/references-envfield.md` [deng2024softening]
  and `paper/prior-art-positioning.md` for the verified wording caveat.

## 6. Limitations (each stated with its number, none hidden)

1. **Small n everywhere.** 4+5 Round-1 candidates; class licenses on n = 4–9 materials;
   Round-3 groups n = 4–6. This is a methodology demonstration, not a survey benchmark
   (prereg language, quote it).
2. **N_eff < N models.** 4 models include two MACE siblings (shared architecture + training
   data) plus a shared-lineage MPA variant; cross-model dispersion is ensemble spread, not
   independent-error spread (caveat fields in `dispersion_vs_error*.json` and
   `barrier_panel/REPORT.md`, quotable verbatim).
3. **Reference conventions.** High-T experimental lattice references vs athermal 0 K
   predictions (perovskite cubic phases at 379–634 K); a0 gains partly absorb thermal
   expansion — decomposition into published expansion offset + residual model bias is
   registered `[errata #9; REGISTERED — R3]`; HEA B0 references derived from polycrystal
   G, nu; Vegard-estimate and tetrataenite-caveated entries recorded per value; per-material
   n reported instead of per-cell n.
4. **Defect/kinetics conventions.** Neutral cells only, no charge corrections; single
   2×2×2 supercells, finite-size common-mode (§3.2); T=0 E_m, not diffusivity.
5. **Perovskite license circularity** until the Round-3 out-of-sample corpus exists
   `[errata #6]`.
6. **Metric edge cases.** Floored dispersion metric is registered and regenerated, but
   V/Cr calibration cells remain under audit `[errata #7; REGISTERED — R3 fix 1]`.
7. **Gates are necessary-condition filters.** Born catches self-inconsistency, not
   hull instability; dynamic-return is a rattle probe, not phonons; cubic symmetry assumed
   by construction (scope notes in `data/discovery_gates/REPORT.md`, keep verbatim).

## 7. Registration-obligation ledger (paper-blocking items, house rules)

| # | Obligation | Status gate for the paper |
|---|---|---|
| 1 | Round-3 verdict (frozen rule, OOS set) | §3.5 stays empty until artifact lands `[OPEN]` |
| 2 | Round-1/2 arm tables regenerated with S4 exclusions + absolute-GPa deltas | until then, no perovskite Cij improvement numbers `[errata #5]` |
| 3 | Lean theorem matching the implemented gate (or drop theorem language) | §4.5 wording depends on which lands `[errata #2]` |
| 4 | NEB 3×3×3 scaling point + endpoint-vs-band-minimum check | blocks any kinetics threshold claim `[errata #11, #12]` |
| 5 | a0 thermal-expansion decomposition | blocks "a0 correction" being read as model bias alone `[errata #9]` |
| 6 | Out-of-sample perovskite corpus for thresholds.v3 | blocks perovskite license upgrade from provisional `[errata #6]` |
| 7 | V/Cr calibration-cell audit under floored metric | blocks bcc C44 gate claims `[errata #7]` |

## 8. Figures and tables (planned, all from committed artifacts)

- F1: five-failure-modes panel (one exemplar cell per target property, §1).
- F2: license matrix heat/table (rho per class × property, refused cells marked, §3.3).
- F3: Round-1 preregistered criteria scorecard (verdict FAIL/FAIL rendered verbatim, §3.1).
- F4: softening dichotomy — Schottky underestimate (absolute eV, anchors) beside barrier
  panel vs PBE-NEB envelope (§3.2).
- F5: gate-ladder wall-time / early-stop diagram with the LiS hull-refusal instance (§2.4, §4.3).
- T1: within-class risk–coverage incl. control false-refusal row (§3.3).
- T2: theorem inventory with what each does and does NOT license (§4).
- (R3 results figure slot reserved — `[OPEN]`.)

## 9. Artifact map (single source of truth per section)

| Section | Artifacts |
|---|---|
| §1 | `data/candidates/round1/REPORT.md`, `round1_targets.json`, errata |
| §2 | `data/discovery_gates/REPORT.md`, `thresholds.v2/v3(.unfloored).json`, protocol docs |
| §3.1 | `data/candidates/round1/criteria_evaluation.json`, unbiased-accuracy-campaign prereg |
| §3.2 | `data/defects/schottky_panel/panel_summary.json`, `data/kinetics/barrier_panel/REPORT.md` |
| §3.3 | `data/discovery_gates/dispersion_vs_error(.by_class).json` |
| §3.4 | `data/candidates/round2/REPORT.md`, `round2-verify/REPORT.md` |
| §3.5 | `docs/plans/2026-07-13-round3-preregistration.md` (only) |
| §4 | `lean-spec/LupineEvidence/Shapes/Certificates.lean`, `.../Theory/DefectStability.lean` |
| §5 | arXiv:2605.00640, 2510.00721, 2402.16621, 2508.09907, 2510.22999, 2603.12183 (all verified) |
| §6 | caveat fields quoted verbatim from the JSON artifacts + prereg honesty notes |
