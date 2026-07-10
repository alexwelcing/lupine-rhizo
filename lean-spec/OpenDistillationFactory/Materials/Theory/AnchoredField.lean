import Mathlib.Tactic.Linarith
import Mathlib.Tactic.NormNum
import OpenDistillationFactory.Materials.Theory.EnvironmentField

/-!
# Anchored fields: measured `ErrorField` instances from three anchors

`Theory.EnvironmentField` proves the laws of *any* softening field. This
module is the bridge from measurement to those laws: it packages the three
standard fcc anchors — the (100) surface probing c = 8, the (111) surface
probing c = 9, and the vacancy probing c = 11, with the bulk pinned to zero
at c = 12 — into a concrete `ErrorField 12`, discharging the structure's
proof obligations (`bulk_anchor`, `softening`, `mono`) once and for all.

The interpolation is the *clamped step field*: piecewise-constant between
anchors and frozen at `p8` below the lowest anchor. This is the conservative
envelope of the measured data — monotone by construction whenever the anchors
themselves are monotone, with no extrapolation freedom. (The *linear* blind
continuation below c = 8 used for the (110) prediction is governed abstractly
by `EnvironmentField.affine_continuation_unique`; the step field is the
correction-side object, the linear continuation the prediction-side one.)

The measured anchors of a (model, material) cell are admissible exactly when

    p8 ≤ p9 ≤ p11 ≤ 0,

i.e. the cell actually exhibits monotone softening. `mkAnchoredField` turns
an admissible triple into an `ErrorField 12` (its per-cell side conditions
are `norm_num`-checkable numeric facts); `scaledAnchorsValid` is the
decidable integer-scaled form of the same admissibility test, so a cell that
*violates* monotone softening gets a kernel-checked refusal certificate
(`¬ scaledAnchorsValid …`) instead of a silently wrong field — the noise-floor
and out-of-domain cells the platform must refuse to correct.

Generated per-cell instances live in
`DistillAtlas.EnvFieldInstances` (emitter:
`python/scripts/bind_env_field_instances.py`).

House rules: zero `sorry`, zero new axioms.
-/

namespace OpenDistillationFactory.Materials.Theory.AnchoredField

open EnvironmentField

/-- Clamped step interpolation of the three fcc anchors: `p8` up to c = 8
(and below, as a conservative floor), `p9` on c = 9, 10, `p11` on c = 11,
zero at bulk (c ≥ 12). -/
def stepField (p8 p9 p11 : ℝ) : ℕ → ℝ := fun c =>
  if c ≤ 8 then p8
  else if c ≤ 10 then p9
  else if c ≤ 11 then p11
  else 0

theorem stepField_bulk_anchor (p8 p9 p11 : ℝ) :
    ∀ c, 12 ≤ c → stepField p8 p9 p11 c = 0 := by
  intro c hc
  unfold stepField
  split_ifs <;> first | rfl | omega

theorem stepField_softening {p8 p9 p11 : ℝ}
    (h89 : p8 ≤ p9) (h911 : p9 ≤ p11) (h110 : p11 ≤ 0) :
    ∀ c, stepField p8 p9 p11 c ≤ 0 := by
  intro c
  unfold stepField
  split_ifs <;> linarith

theorem stepField_monotone {p8 p9 p11 : ℝ}
    (h89 : p8 ≤ p9) (h911 : p9 ≤ p11) (h110 : p11 ≤ 0) :
    Monotone (stepField p8 p9 p11) := by
  intro a b hab
  unfold stepField
  split_ifs <;> linarith

/-- **The measurement bridge.** Three admissible measured anchors
(`p8 ≤ p9 ≤ p11 ≤ 0`) yield a genuine `ErrorField 12`: every law proven in
`Theory.EnvironmentField`, `Theory.BarrierArrhenius`, and
`Theory.RankingIntegrity` now applies to this cell's measured field. The
per-cell hypotheses are numeric facts dischargeable by `norm_num`. -/
def mkAnchoredField (p8 p9 p11 : ℝ)
    (h89 : p8 ≤ p9) (h911 : p9 ≤ p11) (h110 : p11 ≤ 0) :
    ErrorField 12 where
  P := stepField p8 p9 p11
  bulk_anchor := stepField_bulk_anchor p8 p9 p11
  softening := stepField_softening h89 h911 h110
  mono := stepField_monotone h89 h911 h110

section Eval

variable (p8 p9 p11 : ℝ) (h89 : p8 ≤ p9) (h911 : p9 ≤ p11) (h110 : p11 ≤ 0)

/-- The anchored field reproduces its (100) anchor. -/
theorem mkAnchoredField_at_100 :
    (mkAnchoredField p8 p9 p11 h89 h911 h110).P 8 = p8 := rfl

/-- The anchored field reproduces its (111) anchor. -/
theorem mkAnchoredField_at_111 :
    (mkAnchoredField p8 p9 p11 h89 h911 h110).P 9 = p9 := rfl

/-- The anchored field reproduces its vacancy anchor. -/
theorem mkAnchoredField_at_vacancy :
    (mkAnchoredField p8 p9 p11 h89 h911 h110).P 11 = p11 := rfl

/-- The anchored field vanishes at bulk — the pinned boundary condition
`P(12) = 0`. -/
theorem mkAnchoredField_at_bulk :
    (mkAnchoredField p8 p9 p11 h89 h911 h110).P 12 = 0 := rfl

/-- Below the lowest anchor the step field continues at the (100) value —
the conservative clamp for under-coordinated environments such as the c = 7
sites of a (110) facet. -/
theorem mkAnchoredField_clamped_below :
    (mkAnchoredField p8 p9 p11 h89 h911 h110).P 7 = p8 := rfl

end Eval

/-- **The measured-tier constructor.** Any three measured anchors — monotone
or not, softening or stiffening — yield a `MeasuredField 12`: the closure,
bulk-invariance, family-transfer, and ranking-recovery laws apply to every
bound sweep cell unconditionally. Only the *directional* softening laws
require the admissibility hypotheses of `mkAnchoredField`. -/
def mkMeasuredField (p8 p9 p11 : ℝ) : MeasuredField 12 where
  P := stepField p8 p9 p11
  bulk_anchor := stepField_bulk_anchor p8 p9 p11

/-- The measured tier is pinned at bulk: `P(12) = 0`. -/
theorem mkMeasuredField_at_bulk (p8 p9 p11 : ℝ) :
    (mkMeasuredField p8 p9 p11).P 12 = 0 := rfl

/-- The two constructors agree: an admissible cell's strong field forgets to
exactly its measured field, so both tiers' laws compose on the same object. -/
@[simp] theorem mkAnchoredField_toMeasuredField (p8 p9 p11 : ℝ)
    (h89 : p8 ≤ p9) (h911 : p9 ≤ p11) (h110 : p11 ≤ 0) :
    (mkAnchoredField p8 p9 p11 h89 h911 h110).toMeasuredField =
      mkMeasuredField p8 p9 p11 := rfl

/-- Decidable admissibility of integer-scaled anchors (×10⁻⁴ eV/atom):
monotone softening `p8 ≤ p9 ≤ p11 ≤ 0`. A cell violating this predicate is
outside the anchored field's domain — the generator emits a kernel-checked
refusal certificate `¬ scaledAnchorsValid …` for it instead of an instance. -/
def scaledAnchorsValid (p8 p9 p11 : Int) : Prop :=
  p8 ≤ p9 ∧ p9 ≤ p11 ∧ p11 ≤ 0

instance (p8 p9 p11 : Int) : Decidable (scaledAnchorsValid p8 p9 p11) := by
  unfold scaledAnchorsValid
  infer_instance

/-- Sanity lock: an admissible scaled triple, and an inadmissible one (the
(111) anchor deeper than the (100) anchor — a ranking of the anchors that
contradicts monotone softening) is refused. -/
theorem scaledAnchorsValid_example :
    scaledAnchorsValid (-980) (-673) (-136) ∧
      ¬ scaledAnchorsValid (-673) (-980) (-136) := by
  constructor <;> decide

end OpenDistillationFactory.Materials.Theory.AnchoredField
