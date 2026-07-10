import Mathlib.Tactic.Linarith
import Mathlib.Tactic.NormNum
import OpenDistillationFactory.Materials.Theory.EnvironmentField

/-!
# Anchored fields: measured `ErrorField` instances from three anchors

`Theory.EnvironmentField` proves the laws of *any* softening field. This
module is the bridge from measurement to those laws: it packages the three
standard anchors of a crystal-structure family into a concrete `ErrorField`,
discharging the structure's proof obligations (`bulk_anchor`, `softening`,
`mono`) once and for all. Two layouts are provided:

* **fcc** — the (100) surface probing c = 8, the (111) surface probing
  c = 9, and the vacancy probing c = 11, with the bulk pinned to zero at
  c = 12 (`stepField` / `mkAnchoredField` / `scaledAnchorsValid`);
* **bcc** — the (100) surface probing c = 4, the (110) surface probing
  c = 6, and the vacancy probing c = 7, with the bulk pinned to zero at
  c = 8 (`stepFieldBcc` / `mkAnchoredFieldBcc` / `scaledAnchorsBccValid`).

The interpolation is the *clamped step field*: piecewise-constant between
anchors — each anchor's value held across the gap up to the next anchor, the
deeper (more negative) side of every gap — and frozen at the lowest anchor's
value below it. This is the conservative envelope of the measured data —
monotone by construction whenever the anchors themselves are monotone, with
no extrapolation freedom. (The *linear* blind continuation below the lowest
anchor used for blind facet predictions is governed abstractly by
`EnvironmentField.affine_continuation_unique`; the step field is the
correction-side object, the linear continuation the prediction-side one.)

The measured anchors of a (model, material) cell are admissible exactly when

    p_lo ≤ p_mid ≤ p_hi ≤ 0,

i.e. the cell actually exhibits monotone softening (fcc: `p8 ≤ p9 ≤ p11 ≤ 0`;
bcc: `p4 ≤ p6 ≤ p7 ≤ 0`). `mkAnchoredField` / `mkAnchoredFieldBcc` turn an
admissible triple into an `ErrorField` (their per-cell side conditions are
`norm_num`-checkable numeric facts); `scaledAnchorsValid` /
`scaledAnchorsBccValid` are the decidable integer-scaled forms of the same
admissibility tests, so a cell that *violates* monotone softening gets a
kernel-checked refusal certificate (`¬ scaledAnchorsValid …`) instead of a
silently wrong field — the noise-floor and out-of-domain cells the platform
must refuse to correct.

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

/-! ## The bcc layout

Same measurement bridge for the bcc refractory metals (Cr, Fe, Mo, Nb, Ta,
V, W): the (100) surface probes c = 4, the (110) surface probes c = 6, the
vacancy's 8 first-shell atoms sit at c = 7, and the bulk pin is the bcc
first-shell coordination c = 8. The clamped step field holds each anchor's
value across the gap up to the next anchor (so the unanchored c = 5 takes
the deeper (100) value `p4` — the conservative envelope, exactly as the fcc
field holds `p9` across the unanchored c = 10). -/

/-- Clamped step interpolation of the three bcc anchors: `p4` up to c = 5
(covering the c = 4 anchor, the unanchored c = 5 gap, and everything below
as a conservative floor), `p6` on c = 6, `p7` on c = 7, zero at bulk
(c ≥ 8). -/
def stepFieldBcc (p4 p6 p7 : ℝ) : ℕ → ℝ := fun c =>
  if c ≤ 5 then p4
  else if c ≤ 6 then p6
  else if c ≤ 7 then p7
  else 0

theorem stepFieldBcc_bulk_anchor (p4 p6 p7 : ℝ) :
    ∀ c, 8 ≤ c → stepFieldBcc p4 p6 p7 c = 0 := by
  intro c hc
  unfold stepFieldBcc
  split_ifs <;> first | rfl | omega

theorem stepFieldBcc_softening {p4 p6 p7 : ℝ}
    (h46 : p4 ≤ p6) (h67 : p6 ≤ p7) (h70 : p7 ≤ 0) :
    ∀ c, stepFieldBcc p4 p6 p7 c ≤ 0 := by
  intro c
  unfold stepFieldBcc
  split_ifs <;> linarith

theorem stepFieldBcc_monotone {p4 p6 p7 : ℝ}
    (h46 : p4 ≤ p6) (h67 : p6 ≤ p7) (h70 : p7 ≤ 0) :
    Monotone (stepFieldBcc p4 p6 p7) := by
  intro a b hab
  unfold stepFieldBcc
  split_ifs <;> linarith

/-- **The bcc measurement bridge.** Three admissible measured bcc anchors
(`p4 ≤ p6 ≤ p7 ≤ 0`) yield a genuine `ErrorField 8`: every law proven in
`Theory.EnvironmentField`, `Theory.BarrierArrhenius`, and
`Theory.RankingIntegrity` now applies to this cell's measured field. The
per-cell hypotheses are numeric facts dischargeable by `norm_num`. -/
def mkAnchoredFieldBcc (p4 p6 p7 : ℝ)
    (h46 : p4 ≤ p6) (h67 : p6 ≤ p7) (h70 : p7 ≤ 0) :
    ErrorField 8 where
  P := stepFieldBcc p4 p6 p7
  bulk_anchor := stepFieldBcc_bulk_anchor p4 p6 p7
  softening := stepFieldBcc_softening h46 h67 h70
  mono := stepFieldBcc_monotone h46 h67 h70

section EvalBcc

variable (p4 p6 p7 : ℝ) (h46 : p4 ≤ p6) (h67 : p6 ≤ p7) (h70 : p7 ≤ 0)

/-- The bcc anchored field reproduces its (100) anchor. -/
theorem mkAnchoredFieldBcc_at_100 :
    (mkAnchoredFieldBcc p4 p6 p7 h46 h67 h70).P 4 = p4 := rfl

/-- The bcc anchored field reproduces its (110) anchor. -/
theorem mkAnchoredFieldBcc_at_110 :
    (mkAnchoredFieldBcc p4 p6 p7 h46 h67 h70).P 6 = p6 := rfl

/-- The bcc anchored field reproduces its vacancy anchor. -/
theorem mkAnchoredFieldBcc_at_vacancy :
    (mkAnchoredFieldBcc p4 p6 p7 h46 h67 h70).P 7 = p7 := rfl

/-- The bcc anchored field vanishes at bulk — the pinned boundary condition
`P(8) = 0` at the bcc first-shell coordination. -/
theorem mkAnchoredFieldBcc_at_bulk :
    (mkAnchoredFieldBcc p4 p6 p7 h46 h67 h70).P 8 = 0 := rfl

/-- Below the lowest anchor the bcc step field continues at the (100) value —
the conservative clamp for under-coordinated environments such as c = 3
kink and step-edge sites. -/
theorem mkAnchoredFieldBcc_clamped_below :
    (mkAnchoredFieldBcc p4 p6 p7 h46 h67 h70).P 3 = p4 := rfl

end EvalBcc

/-- **The bcc measured-tier constructor.** Any three measured bcc anchors —
monotone or not, softening or stiffening — yield a `MeasuredField 8`: the
closure, bulk-invariance, family-transfer, and ranking-recovery laws apply
to every bound bcc sweep cell unconditionally. Only the *directional*
softening laws require the admissibility hypotheses of
`mkAnchoredFieldBcc`. -/
def mkMeasuredFieldBcc (p4 p6 p7 : ℝ) : MeasuredField 8 where
  P := stepFieldBcc p4 p6 p7
  bulk_anchor := stepFieldBcc_bulk_anchor p4 p6 p7

/-- The bcc measured tier is pinned at bulk: `P(8) = 0`. -/
theorem mkMeasuredFieldBcc_at_bulk (p4 p6 p7 : ℝ) :
    (mkMeasuredFieldBcc p4 p6 p7).P 8 = 0 := rfl

/-- The two bcc constructors agree: an admissible cell's strong field forgets
to exactly its measured field, so both tiers' laws compose on the same
object. -/
@[simp] theorem mkAnchoredFieldBcc_toMeasuredField (p4 p6 p7 : ℝ)
    (h46 : p4 ≤ p6) (h67 : p6 ≤ p7) (h70 : p7 ≤ 0) :
    (mkAnchoredFieldBcc p4 p6 p7 h46 h67 h70).toMeasuredField =
      mkMeasuredFieldBcc p4 p6 p7 := rfl

/-- Decidable admissibility of integer-scaled bcc anchors (×10⁻⁴ eV/atom):
monotone softening `p4 ≤ p6 ≤ p7 ≤ 0`. A cell violating this predicate is
outside the bcc anchored field's domain — the generator emits a
kernel-checked refusal certificate `¬ scaledAnchorsBccValid …` for it
instead of an instance. -/
def scaledAnchorsBccValid (p4 p6 p7 : Int) : Prop :=
  p4 ≤ p6 ∧ p6 ≤ p7 ∧ p7 ≤ 0

instance (p4 p6 p7 : Int) : Decidable (scaledAnchorsBccValid p4 p6 p7) := by
  unfold scaledAnchorsBccValid
  infer_instance

/-- Sanity lock: an admissible scaled bcc triple, and an inadmissible one
(the (110) anchor deeper than the (100) anchor — a ranking of the anchors
that contradicts monotone softening) is refused. -/
theorem scaledAnchorsBccValid_example :
    scaledAnchorsBccValid (-4852) (-4596) (-1697) ∧
      ¬ scaledAnchorsBccValid (-4596) (-4852) (-1697) := by
  constructor <;> decide

end OpenDistillationFactory.Materials.Theory.AnchoredField
