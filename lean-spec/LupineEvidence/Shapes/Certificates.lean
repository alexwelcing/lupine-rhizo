/- HAND-WRITTEN claim-shape library — formalization ladder L3 groundwork.
   NOT generated. This module defines the TYPES of facts a discovery run can
   establish: certificates that a lab run instantiates, reusable across runs.
   Generators emit *instances* of these shapes into LupineEvidence/Discovery/
   (see README.md in this directory); they never edit this file.
   Conventions: dependency-free (core Lean only — no Mathlib/Atlas); physical
   quantities integer-scaled x10000, matching the evidence corpus; 0 sorry.
   Every predicate is Decidable so a concrete instance is checked by `decide`
   and the kernel — a run either produces a witness or it does not. -/

namespace Lupine.Shapes

/-! ## Cubic elasticity -/

/-- Cubic elastic stiffness triple (c11, c12, c44), GPa x10000.
    Scientific meaning: the three independent elastic constants of a cubic
    crystal, fully determining its linear elastic response.
    Instantiated by: a statics elastic-constants cell (energy-strain or
    stress-strain fit) for one material/model, e.g. the
    `lupine_distill.statics` lane. -/
structure CubicElastic where
  c11 : Int
  c12 : Int
  c44 : Int
deriving Repr, DecidableEq

/-- Born mechanical-stability criterion for a cubic crystal:
    c11 - c12 > 0 (tetragonal shear stability), c11 + 2*c12 > 0 (volumetric
    stability), c44 > 0 (trigonal shear stability). A model whose predicted
    constants fail this describes a mechanically unstable phase — grounds for
    refusal regardless of accuracy elsewhere. -/
def bornStable (e : CubicElastic) : Prop :=
  e.c11 - e.c12 > 0 ∧ e.c11 + 2 * e.c12 > 0 ∧ e.c44 > 0

instance (e : CubicElastic) : Decidable (bornStable e) :=
  inferInstanceAs (Decidable (_ ∧ _ ∧ _))

/-! ## Cross-model concordance -/

/-- Cross-model concordance measurement for one property on an unknown
    structure, all values x10000. `dispersionScaled` is the observed
    cross-model dispersion of the ensemble's predictions (e.g. relative IQR);
    the two thresholds are fixed BEFORE the run and cut the dispersion axis
    into three ordered zones: concordant (report), flagged (report only with
    anchor-calibrated correction attached), refused (no claim issued).
    Instantiated by: an ensemble prediction cell (>= 2 models, one property)
    in the unknown-structure discovery workflow. -/
structure ConcordanceWindow where
  dispersionScaled : Int
  flagThreshold : Int
  refuseThreshold : Int
deriving Repr, DecidableEq

/-- Window well-formedness: the flag threshold does not exceed the refuse
    threshold. Fixed at registration time, before any data is seen. -/
def wellFormed (w : ConcordanceWindow) : Prop :=
  w.flagThreshold ≤ w.refuseThreshold

/-- Concordant: dispersion strictly below the flag threshold — the models
    agree and the ensemble value may be reported as-is. Boundary convention
    matches the runtime (`lupine_distill.statics.gates.concordance`):
    a dispersion AT a threshold takes the more cautious zone. -/
def concordant (w : ConcordanceWindow) : Prop :=
  w.dispersionScaled < w.flagThreshold

/-- Flagged: dispersion at-or-above flag but strictly below refuse —
    reportable only with an `AnchorCalibration`-backed correction attached.
    (Runtime convention: `dispersion >= flag` flags, `>= refuse` refuses.) -/
def flagged (w : ConcordanceWindow) : Prop :=
  w.flagThreshold ≤ w.dispersionScaled ∧ w.dispersionScaled < w.refuseThreshold

/-- Refused: dispersion at-or-beyond the refuse threshold — no claim is
    issued for this cell; a `Refusal` certificate is emitted instead. -/
def refused (w : ConcordanceWindow) : Prop :=
  w.refuseThreshold ≤ w.dispersionScaled

instance (w : ConcordanceWindow) : Decidable (wellFormed w) :=
  inferInstanceAs (Decidable (_ ≤ _))
instance (w : ConcordanceWindow) : Decidable (concordant w) :=
  inferInstanceAs (Decidable (_ < _))
instance (w : ConcordanceWindow) : Decidable (flagged w) :=
  inferInstanceAs (Decidable (_ ∧ _))
instance (w : ConcordanceWindow) : Decidable (refused w) :=
  inferInstanceAs (Decidable (_ ≤ _))

/-- The three outcomes are mutually exclusive and exhaustive: every
    well-formed window lands in EXACTLY one zone. The zones are totally
    ordered along the dispersion axis (concordant < flagged < refused). -/
theorem outcome_trichotomy (w : ConcordanceWindow) (hw : wellFormed w) :
    (concordant w ∧ ¬ flagged w ∧ ¬ refused w)
    ∨ (¬ concordant w ∧ flagged w ∧ ¬ refused w)
    ∨ (¬ concordant w ∧ ¬ flagged w ∧ refused w) := by
  unfold wellFormed at hw
  unfold concordant flagged refused
  omega

/-! ## Threshold migration (v1 proxy -> v2 per-property calibration)

    When thresholds are recalibrated on the SAME measured dispersion (the
    subject's data does not change; only the baseline the percentiles are
    taken from does), verdict changes are fully characterized by the
    threshold delta. These laws make a re-verdict a kernel-checked
    consequence of the calibration change rather than a fresh claim. -/

/-- Two windows measure the same dispersion (the recalibration setting). -/
def sameDispersion (w w' : ConcordanceWindow) : Prop :=
  w.dispersionScaled = w'.dispersionScaled

instance (w w' : ConcordanceWindow) : Decidable (sameDispersion w w') :=
  inferInstanceAs (Decidable (_ = _))

/-- Tightening can only add refusals: under an equal-or-lower refuse
    threshold, a refused cell stays refused. Migrating to stricter
    per-property thresholds can never un-refuse a subject. -/
theorem refused_stable_under_tightening (w w' : ConcordanceWindow)
    (hd : sameDispersion w w') (ht : w'.refuseThreshold ≤ w.refuseThreshold)
    (hr : refused w) : refused w' := by
  unfold sameDispersion at hd
  unfold refused at *
  omega

/-- An un-refusal is threshold-driven, never data-driven: if the same
    measured dispersion is refused under the old window but not under the
    new one, the new refuse threshold is strictly looser. Every Run-2
    verdict flip must exhibit this witness. -/
theorem unrefusal_needs_looser_threshold (w w' : ConcordanceWindow)
    (hd : sameDispersion w w') (hr : refused w) (hn : ¬ refused w') :
    w.refuseThreshold < w'.refuseThreshold := by
  unfold sameDispersion at hd
  unfold refused at *
  omega

/-- Dually, a cell concordant under the old window that stops being
    concordant under the new one certifies a strictly tighter flag
    threshold. -/
theorem deconcordance_needs_tighter_threshold (w w' : ConcordanceWindow)
    (hd : sameDispersion w w') (hc : concordant w) (hn : ¬ concordant w') :
    w'.flagThreshold < w.flagThreshold := by
  unfold sameDispersion at hd
  unfold concordant at *
  omega

/-! ## Ensemble-hull Born refusal

    Per-model Born failures compose into a single impossibility statement:
    if the axis-aligned hull of the ensemble's predicted elastic constants
    already violates one Born inequality at its favourable endpoint, then
    EVERY tensor inside the hull is Born-unstable — the refusal holds for
    the whole ensemble range, not just the sampled models. This is the
    statics analog of the anchor-bracket "refusal for ALL fields" pattern. -/

/-- Axis-aligned interval hull of an ensemble's cubic elastic predictions,
    GPa x10000 (component-wise min/max over the models). -/
structure ElasticHull where
  c11min : Int
  c11max : Int
  c12min : Int
  c12max : Int
  c44min : Int
  c44max : Int
deriving Repr, DecidableEq

/-- Membership: each constant lies inside its interval. -/
def memHull (e : CubicElastic) (h : ElasticHull) : Prop :=
  h.c11min ≤ e.c11 ∧ e.c11 ≤ h.c11max
  ∧ h.c12min ≤ e.c12 ∧ e.c12 ≤ h.c12max
  ∧ h.c44min ≤ e.c44 ∧ e.c44 ≤ h.c44max

instance (e : CubicElastic) (h : ElasticHull) : Decidable (memHull e h) :=
  inferInstanceAs (Decidable (_ ∧ _ ∧ _ ∧ _ ∧ _ ∧ _))

/-- Trigonal-shear hull refusal: if even the LARGEST ensemble c44 is
    nonpositive, every tensor in the hull fails Born. -/
theorem hull_born_refusal_c44 (h : ElasticHull) (hc : h.c44max ≤ 0) :
    ∀ e : CubicElastic, memHull e h → ¬ bornStable e := by
  intro e hm hb
  unfold memHull at hm
  unfold bornStable at hb
  omega

/-- Tetragonal-shear hull refusal: if the most favourable spread
    (c11max - c12min) is nonpositive, every tensor in the hull fails Born. -/
theorem hull_born_refusal_shear (h : ElasticHull)
    (hc : h.c11max - h.c12min ≤ 0) :
    ∀ e : CubicElastic, memHull e h → ¬ bornStable e := by
  intro e hm hb
  unfold memHull at hm
  unfold bornStable at hb
  omega

/-- Volumetric hull refusal: if even c11max + 2*c12max is nonpositive,
    every tensor in the hull fails Born. -/
theorem hull_born_refusal_volumetric (h : ElasticHull)
    (hc : h.c11max + 2 * h.c12max ≤ 0) :
    ∀ e : CubicElastic, memHull e h → ¬ bornStable e := by
  intro e hm hb
  unfold memHull at hm
  unfold bornStable at hb
  omega

/-! ## Correction-direction laws (campaign Round-1 -> Round-2 iteration)

    Round 1 of the unbiased accuracy campaign (2026-07-13) showed a
    cross-class multiplicative de-bias HARMING accuracy: a bias calibrated
    on elemental fcc metals (models underpredict B0 there) inflated HEA
    predictions that were already above their references. These laws make
    the failure mode a theorem and license the Round-2 gate: a correction
    whose direction is not verified in-class must ABSTAIN. -/

/-- Inflating a prediction that is already at-or-above its reference
    strictly increases the error. -/
theorem wrong_direction_inflation_worsens (pred ref corrected : Int)
    (hover : ref ≤ pred) (hinc : pred < corrected) :
    (pred - ref).natAbs < (corrected - ref).natAbs := by omega

/-- Deflating a prediction that is already at-or-below its reference
    strictly increases the error. -/
theorem wrong_direction_deflation_worsens (pred ref corrected : Int)
    (hunder : pred ≤ ref) (hdec : corrected < pred) :
    (pred - ref).natAbs < (corrected - ref).natAbs := by omega

/-- Direction evidence for one (model, property, class) correction:
    `calibrationDirection` = sign witness of (median bias - 1) on the
    calibration class (x10000, nonzero); `anchorDirection` = sign witness of
    (pred - ref) on an in-class anchor of the TARGET class. The correction
    divides by the bias, so it moves predictions opposite to the calibration
    direction; it is licensed only when the target class errs the same way. -/
structure CorrectionAnchor where
  calibrationDirection : Int
  anchorDirection : Int
deriving Repr, DecidableEq

/-- Verified direction: calibration and in-class anchor agree in sign.
    Without an in-class anchor there is no witness and the correction
    must abstain (corrected := pred), which never changes the error. -/
def directionVerified (c : CorrectionAnchor) : Prop :=
  0 < c.calibrationDirection * c.anchorDirection

instance (c : CorrectionAnchor) : Decidable (directionVerified c) :=
  inferInstanceAs (Decidable (_ < _))

/-- Round-1 witness (HEA B0, x10000): calibration bias 0.8565 - 1 < 0
    (elemental fcc metals underpredicted) but the alloy anchor overpredicts
    (+1900 vs its reference): direction NOT verified — the Round-1 harm was
    licensed by nothing, and the Round-2 gate abstains here. -/
example : ¬ directionVerified { calibrationDirection := -1435, anchorDirection := 1900 } := by
  decide

/-- The Round-1 harm as arithmetic (HEA-like B0, GPa x10): raw 1940 vs
    reference 1630, de-bias inflates to 2265 — strictly worse, by law. -/
example : (1940 - 1630 : Int).natAbs < (2265 - 1630 : Int).natAbs :=
  wrong_direction_inflation_worsens 1940 1630 2265 (by omega) (by omega)

/-! ## Capped in-hull correction laws (the theorem the review demanded)

    Errata finding 2 (2026-07-13): `wrong_direction_*_worsens` takes the
    TARGET's error side as a hypothesis, but the runtime sign-gate checks
    only that CLASSMATES share a side — FeNi B0 / mace-mp-small received a
    licensed deflation those theorems forbid. These laws state what the
    implemented gate can honestly claim: every hypothesis below is checkable
    from calibration data EXCEPT the in-hull hypothesis `lo ≤ r ≤ hi`, which
    is the formal content of the informal word "in-class" — the target's
    true ratio behaves like its classmates'. A run that cannot witness
    in-hull membership gets NO license from these theorems.

    Quantities are ratios x10000 (10000 = ratio 1): calibration ratio hull
    [lo, hi] over classmates' pred/ref ratios, bias b = median ratio, spread
    s = hi - lo, target ratio r = pred/ref. The correction divides the
    prediction by b, so the corrected ratio is r/b, and the claim
    |r/b - 1| < |r - 1| is stated division-free: for b > 0 it is equivalent
    (multiply both sides by b * 10000 > 0) to

        |r - b| * 10000 < |r - 10000| * b.

    RELATION TO THE FROZEN ROUND-3 RUNTIME CAP. The Round-3 preregistration
    (docs/plans/2026-07-13-round3-preregistration.md, rule 4) froze the cap
    |b - 1| > s — ONE spread. That is strictly WEAKER than what these
    theorems require (2s on the inflation side; 3s plus a 0.5 floor on the
    deflation side), and the counterexamples below exhibit in-hull cells the
    1s cap licenses where the correction strictly HARMS. These theorems
    therefore do NOT retroactively license the Round-3 rule: Round-3 results
    are read under Round-3's own frozen registration, and the caps proved
    here inform a REGISTERED Round-4 cap change only.

    ASYMMETRY (derived, not assumed). The corrected error is measured
    relative to b. Inflation (b > 1) divides by a larger denominator and
    gains margin: b - 1 > 2s suffices, with no ceiling on b. Deflation
    (b < 1) divides by a smaller denominator, amplifying the same |r - b|:
    the spread multiple rises to THREE and a floor b ≥ 0.5 is needed. The
    exact deflation boundary is quadratic in b (10000 * s < (|b - 10000| -
    s) * b); 3s + floor is the clean linear sufficient cap, and the
    deflation counterexample shows the mirrored 2s cap admitting a strict
    harm even with the floor in place. -/

/-- CAPPED IN-HULL CORRECTION, inflation side (all calibration ratios > 1).
    Hull strictly above 1 (10000 < lo ≤ hi), bias b in-hull, TARGET ratio r
    in-hull (the "in-class" hypothesis), cap b - 1 > 2s: dividing by the
    bias strictly shrinks the target's error, |r/b - 1| < |r - 1|, stated
    division-free as |r - b| * 10000 < |r - 10000| * b.
    (Underscored hypotheses pin the regime for the reader; they are
    derivable from the cap and the memberships, so the proof never uses
    them.) -/
theorem capped_inhull_correction_helps_inflation
    (lo hi s b r : Int) (hs : s = hi - lo)
    (_hlo : 10000 < lo) (hle : lo ≤ hi)
    (hb1 : lo ≤ b) (hb2 : b ≤ hi)
    (hr1 : lo ≤ r) (hr2 : r ≤ hi)
    (hcap : 2 * s < b - 10000) :
    ((r - b).natAbs : Int) * 10000 < ((r - 10000).natAbs : Int) * b := by
  have hcast : ((r - 10000).natAbs : Int) = r - 10000 := by omega
  rw [hcast]
  calc ((r - b).natAbs : Int) * 10000
      ≤ s * 10000 := by omega
    _ < (r - 10000) * 10000 := by omega
    _ ≤ (r - 10000) * b :=
        Int.mul_le_mul_of_nonneg_left (by omega) (by omega)

/-- CAPPED IN-HULL CORRECTION, deflation side (all calibration ratios < 1).
    NOT the mirror image: needs the bias magnitude above THREE spreads
    (1 - b > 3s) AND the floor b ≥ 0.5 (5000 x10000), because the corrected
    error is measured relative to b < 1 — see the asymmetry note above and
    the 2s counterexample below. (Underscored hypotheses pin the regime
    for the reader; they are derivable from the cap, the floor, and the
    memberships, so the proof never uses them.) -/
theorem capped_inhull_correction_helps_deflation
    (lo hi s b r : Int) (hs : s = hi - lo)
    (_hlo : 0 < lo) (_hle : lo ≤ hi) (_hhi : hi < 10000)
    (hb1 : lo ≤ b) (hb2 : b ≤ hi)
    (hr1 : lo ≤ r) (hr2 : r ≤ hi)
    (hfloor : 5000 ≤ b)
    (hcap : 3 * s < 10000 - b) :
    ((r - b).natAbs : Int) * 10000 < ((r - 10000).natAbs : Int) * b := by
  have hcast : ((r - 10000).natAbs : Int) = 10000 - r := by omega
  rw [hcast]
  calc ((r - b).natAbs : Int) * 10000
      ≤ s * 10000 := by omega
    _ < (10000 - r) * 5000 := by omega
    _ ≤ (10000 - r) * b :=
        Int.mul_le_mul_of_nonneg_left (by omega) (by omega)

/-- Non-vacuity, inflation: hull [1.05, 1.07] (s = 200), b = 1.06 (cap:
    600 > 400), r = 1.07 — corrected error ~0.94e-2 beats raw 7e-2. -/
example : ((10700 - 10600 : Int).natAbs : Int) * 10000
    < ((10700 - 10000 : Int).natAbs : Int) * 10600 :=
  capped_inhull_correction_helps_inflation 10500 10700 200 10600 10700
    (by decide) (by decide) (by decide) (by decide) (by decide)
    (by decide) (by decide) (by decide)

/-- Non-vacuity, deflation: hull [0.80, 0.84] (s = 400), b = 0.82 (floor
    holds; cap: 1200 < 1800), r = 0.84 — corrected error ~2.4e-2 beats raw
    16e-2. -/
example : ((8400 - 8200 : Int).natAbs : Int) * 10000
    < ((8400 - 10000 : Int).natAbs : Int) * 8200 :=
  capped_inhull_correction_helps_deflation 8000 8400 400 8200 8400
    (by decide) (by decide) (by decide) (by decide) (by decide)
    (by decide) (by decide) (by decide) (by decide) (by decide)

/-- Round-2 FeNi B0 (errata finding 2) — the case that demanded this
    section. mace-mp-small predicted 143.1 GPa vs reference 176.7 GPa:
    target ratio r = 0.810 (8100 x10000), while the elemental-fcc
    calibration classmates' ratios spanned [1.02, 1.175] ([10200, 11750]).
    The IN-HULL hypothesis FAILS — 8100 lies outside [10200, 11750] — so
    neither theorem licenses the deflation Round 2 applied there (which
    pushed the already-low prediction further from its reference). The
    refusal is the theorem working as intended. -/
example : ¬ (10200 ≤ (8100 : Int) ∧ (8100 : Int) ≤ 11750) := by decide

/-- Independently of the target: that calibration hull cannot clear the
    inflation cap for ANY in-hull bias — s = 1550 demands b > 1.31 (13100)
    but the hull tops out at 11750. The FeNi-era correction fails BOTH
    license hypotheses. -/
example : ∀ b : Int, 10200 ≤ b → b ≤ 11750 →
    ¬ (2 * (11750 - 10200) < b - 10000) := by
  intro b hb1 hb2
  omega

/-- The frozen Round-3 runtime cap (|b - 1| > s, ONE spread) is strictly
    weaker than the theorem's: an in-hull inflation cell it licenses where
    the correction HARMS. Hull [1.0001, 1.0003] (s = 2), b = 10003 (1s cap:
    3 > 2 passes; theorem cap: 3 > 4 fails), r = 10001: corrected error
    ~2.0 x10000-units vs raw 1 — strictly worse. Round 3 stays governed by
    its own registration; this witness motivates the registered Round-4 cap
    change. -/
example : ¬ (((10001 - 10003 : Int).natAbs : Int) * 10000
    < ((10001 - 10000 : Int).natAbs : Int) * 10003) := by decide

/-- Deflation asymmetry witness: the MIRRORED inflation cap (2s) is NOT
    sufficient below 1, even with the b ≥ 0.5 floor. Hull [0.50, 0.74]
    (s = 2400), b = 0.5 (floor holds; 2s cap: 5000 > 4800 passes; the
    Round-3 1s cap passes too), r = 0.74: corrected error 0.48 vs raw 0.26
    — strictly worse. Hence the deflation side's THREE spreads. -/
example : ¬ (((7400 - 5000 : Int).natAbs : Int) * 10000
    < ((7400 - 10000 : Int).natAbs : Int) * 5000) := by decide

/-! ## Anchor calibration -/

/-- Power-law calibration for one property family: pred ~ c * T^alpha, with
    the exponent owned by the property FAMILY (shared across models) and the
    prefactor owned by the MODEL — the Round 7 family-exponent law.
    `familyExponentScaled` = alpha x10000, `prefactorScaled` = c x10000,
    `anchorCount` = number of known-reference materials the fit used.
    Instantiated by: an anchor-calibration fit over the bound reference set
    for one (family, model) pair, before correcting an unknown structure. -/
structure AnchorCalibration where
  familyExponentScaled : Int
  prefactorScaled : Int
  anchorCount : Nat
deriving Repr, DecidableEq

/-- Well-anchored: at least 3 anchors — the minimum for a monotone
    interpolation with an interior knot. Below this, "calibration" is a line
    through two points and clamping dominates (Round 4's extrapolation
    boundary applies everywhere). -/
def wellAnchored (a : AnchorCalibration) : Prop :=
  3 ≤ a.anchorCount

/-- Physically admissible calibration: positive prefactor and positive family
    exponent. The corpus's observed family exponents are all positive; a
    nonpositive fit signals a degenerate regression, not physics. -/
def admissibleCalibration (a : AnchorCalibration) : Prop :=
  0 < a.prefactorScaled ∧ 0 < a.familyExponentScaled

instance (a : AnchorCalibration) : Decidable (wellAnchored a) :=
  inferInstanceAs (Decidable (_ ≤ _))
instance (a : AnchorCalibration) : Decidable (admissibleCalibration a) :=
  inferInstanceAs (Decidable (_ ∧ _))

/-! ## Refusal -/

/-- A refusal certificate: the run declines to issue a claim and records WHY,
    with two integer witnesses (x10000-scaled predictions) carrying the
    obstruction — typically an ordinal inversion against the references.
    Instantiated by: any cell the discovery workflow refuses (dispersion past
    the refuse threshold, Born instability, or an uncorrectable inversion). -/
structure Refusal where
  reason : String
  witnessA : Int
  witnessB : Int
deriving Repr, DecidableEq

/-- A refusal is ORDER-JUSTIFIED against references (refA, refB) when the
    witness order inverts the reference order: witnessA ≤ witnessB but
    refB < refA. By `no_monotone_fix`, no monotone correction repairs it. -/
def orderJustified (r : Refusal) (refA refB : Int) : Prop :=
  r.witnessA ≤ r.witnessB ∧ refB < refA

instance (r : Refusal) (refA refB : Int) : Decidable (orderJustified r refA refB) :=
  inferInstanceAs (Decidable (_ ∧ _))

/-- General impossibility lemma: a monotone map cannot swap an order.
    Self-contained restatement of the lemma proved in
    LupineEvidence.YMatrix.Round4_Isotonic (emitted from
    data/y_matrix_runs/lean/Round4_Isotonic.lean), copied here so Shapes has
    no imports. -/
theorem no_monotone_fix {f : Int → Int} (hf : ∀ a b : Int, a ≤ b → f a ≤ f b)
    {pa pb : Int} (hp : pa ≤ pb) : ¬ (f pb < f pa) := by
  intro hlt
  have := hf pa pb hp
  omega

/-- An order-justified refusal is final: no monotone correction g can map
    both witnesses onto their references. -/
theorem orderJustified_uncorrectable (r : Refusal) (refA refB : Int)
    (h : orderJustified r refA refB) {g : Int → Int}
    (hg : ∀ a b : Int, a ≤ b → g a ≤ g b)
    (hA : g r.witnessA = refA) (hB : g r.witnessB = refB) : False := by
  have hmono := hg r.witnessA r.witnessB h.1
  have hinv := h.2
  omega

/-! ## Worked examples — every shape is decidable on concrete data.
    These are the instantiation pattern generators must follow: build the
    structure literal, state the predicate, close with `decide`. -/

/-- Born-stable cell with plausible fcc-metal constants
    (c11 = 245 GPa, c12 = 147 GPa, c44 = 125 GPa, x10000): one `decide`,
    the kernel checks all three Born inequalities. -/
example : bornStable { c11 := 2450000, c12 := 1470000, c44 := 1250000 } := by
  decide

/-- Born-UNSTABLE counterexample: c11 - c12 ≤ 0 (shear-soft phase) is
    rejected by the same decision procedure. -/
example : ¬ bornStable { c11 := 1470000, c12 := 2450000, c44 := 1250000 } := by
  decide

/-- A refused concordance cell: observed dispersion 0.62 (x10000 = 6200)
    against a window registered at flag 0.15 / refuse 0.50 — and it is in
    exactly the refused zone. -/
example :
    refused { dispersionScaled := 6200, flagThreshold := 1500, refuseThreshold := 5000 }
    ∧ ¬ concordant { dispersionScaled := 6200, flagThreshold := 1500, refuseThreshold := 5000 }
    ∧ ¬ flagged { dispersionScaled := 6200, flagThreshold := 1500, refuseThreshold := 5000 } := by
  decide

/-- Well-anchored, admissible calibration with the corpus's surface-family
    shape (alpha = 1.1065 x10000, 8 anchors as in the Round 4 LOO fit). -/
example :
    wellAnchored { familyExponentScaled := 11065, prefactorScaled := 21500, anchorCount := 8 }
    ∧ admissibleCalibration { familyExponentScaled := 11065, prefactorScaled := 21500, anchorCount := 8 } := by
  decide

/-- The MPtrj SFE boundary as an order-justified refusal (numbers from
    Round4_Isotonic): mace-mp-small predicts SFE(Ni) = -77759 ≤
    SFE(Al) = -76202 (x10000 mJ/m^2) while the references order the other
    way (Al 1175400 < Ni 1535600). -/
def sfeMptrjRefusal : Refusal :=
  { reason := "SFE ordinal inversion Ni/Al under mace-mp-small (MPtrj boundary)"
  , witnessA := -77759
  , witnessB := -76202 }

example : orderJustified sfeMptrjRefusal 1535600 1175400 := by decide

/-- `no_monotone_fix` applied through the certificate: no monotone g maps
    both SFE witnesses onto their references — the refusal is final. -/
example (g : Int → Int) (hg : ∀ a b : Int, a ≤ b → g a ≤ g b)
    (hNi : g (-77759) = 1535600) (hAl : g (-76202) = 1175400) : False :=
  orderJustified_uncorrectable sfeMptrjRefusal 1535600 1175400 (by decide) hg hNi hAl

end Lupine.Shapes
