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
