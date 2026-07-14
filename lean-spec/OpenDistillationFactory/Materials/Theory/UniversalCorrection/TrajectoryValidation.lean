import Mathlib.Tactic.Linarith
import Mathlib.Tactic.NormNum
import Lean.Elab.Tactic.Omega
import Mathlib.Tactic.Ring
import OpenDistillationFactory.Materials.Theory.UniversalCorrection.Anchor
import OpenDistillationFactory.Materials.Theory.UniversalCorrection.Smoothness

/-!
# Sampled smoothness evidence and between-validation guarantees

A finite campaign can check a residual only at finitely many configurations.
That evidence is useful, but it is not the same proposition as a global
Lipschitz guarantee.  This module keeps the two levels separate:

* `SampledLipschitzEvidence` checks every pair in a finite sample list;
* `LipschitzResidual` is the global premise over every configuration;
* every global premise restricts to sampled evidence;
* a concrete singleton-sample counterexample proves that the converse is
  false; and
* only the global premise, combined with a per-timestep metric drift bound,
  yields sound residual bounds between validation checkpoints.

Thus a runtime certificate cannot promote a successful finite diagnostic into
a universal smoothness theorem.  A concrete campaign must obtain the global
premise from a separate theorem, validated model class, or explicitly trusted
assumption whose scope and provenance are recorded.
-/

namespace OpenDistillationFactory.Materials.Theory.UniversalCorrection

/-! ## Finite sampled evidence -/

/-- Pairwise `L`-Lipschitz evidence restricted to a finite list of sampled
configurations.  Duplicate samples are harmless and retain serialized order. -/
def SampledLipschitzEvidence {scope : Scope} {X : Type*}
    [PseudoMetricSpace X] (L : ℝ) (samples : List X)
    (field : ResidualField scope X ℝ) : Prop :=
  0 ≤ L ∧
    ∀ x ∈ samples, ∀ y ∈ samples,
      |field x - field y| ≤ L * dist x y

namespace SampledLipschitzEvidence

theorem nonneg {scope : Scope} {X : Type*} [PseudoMetricSpace X]
    {L : ℝ} {samples : List X} {field : ResidualField scope X ℝ}
    (h : SampledLipschitzEvidence L samples field) : 0 ≤ L :=
  h.1

/-- A sampled certificate controls exactly the pairs that occur in its list. -/
theorem bound {scope : Scope} {X : Type*} [PseudoMetricSpace X]
    {L : ℝ} {samples : List X} {field : ResidualField scope X ℝ}
    (h : SampledLipschitzEvidence L samples field)
    {x y : X} (hx : x ∈ samples) (hy : y ∈ samples) :
    |field x - field y| ≤ L * dist x y :=
  h.2 x hx y hy

/-- Removing sampled points cannot invalidate finite pairwise evidence. -/
theorem mono {scope : Scope} {X : Type*} [PseudoMetricSpace X]
    {L : ℝ} {small large : List X} {field : ResidualField scope X ℝ}
    (h : SampledLipschitzEvidence L large field)
    (hsubset : ∀ x, x ∈ small → x ∈ large) :
    SampledLipschitzEvidence L small field := by
  refine ⟨h.1, ?_⟩
  intro x hx y hy
  exact h.2 x (hsubset x hx) y (hsubset y hy)

end SampledLipschitzEvidence

/-- A global Lipschitz premise is sound evidence on every finite sample. -/
theorem LipschitzResidual.toSampled {scope : Scope} {X : Type*}
    [PseudoMetricSpace X] {L : ℝ} {field : ResidualField scope X ℝ}
    (h : LipschitzResidual L field) (samples : List X) :
    SampledLipschitzEvidence L samples field := by
  refine ⟨h.1, ?_⟩
  intro x _ y _
  exact h.2 x y

/-- **Finite evidence is not a global smoothness proof.**  The identity
residual passes the zero-Lipschitz check on the singleton sample `[0]`, while
it is not globally zero-Lipschitz on `ℝ`.  This theorem prevents downstream
code from treating finite diagnostics as a substitute for the global premise. -/
theorem singleton_sample_does_not_imply_global (scope : Scope) :
    let field : ResidualField scope ℝ ℝ := fun x => x
    SampledLipschitzEvidence 0 [0] field ∧
      ¬ LipschitzResidual 0 field := by
  dsimp
  constructor
  · refine ⟨by norm_num, ?_⟩
    intro x hx y hy
    simp only [List.mem_singleton] at hx hy
    subst x
    subst y
    norm_num
  · intro hglobal
    have h01 := hglobal.2 0 1
    norm_num at h01

/-! ## Per-timestep metric drift -/

/-- A trajectory moves by at most `stepBound` in the configured metric at
each timestep.  Nonnegativity is retained explicitly in the premise. -/
def PerStepDriftBound {X : Type*} [PseudoMetricSpace X]
    (trajectory : ℕ → X) (stepBound : ℝ) : Prop :=
  0 ≤ stepBound ∧
    ∀ step, dist (trajectory (step + 1)) (trajectory step) ≤ stepBound

namespace PerStepDriftBound

theorem nonneg {X : Type*} [PseudoMetricSpace X]
    {trajectory : ℕ → X} {stepBound : ℝ}
    (h : PerStepDriftBound trajectory stepBound) : 0 ≤ stepBound :=
  h.1

theorem one_step {X : Type*} [PseudoMetricSpace X]
    {trajectory : ℕ → X} {stepBound : ℝ}
    (h : PerStepDriftBound trajectory stepBound) (step : ℕ) :
    dist (trajectory (step + 1)) (trajectory step) ≤ stepBound :=
  h.2 step

/-- Repeated triangle inequalities convert a local per-step bound into a
distance bound from any validation checkpoint. -/
theorem distance_from_checkpoint_le {X : Type*} [PseudoMetricSpace X]
    {trajectory : ℕ → X} {stepBound : ℝ}
    (h : PerStepDriftBound trajectory stepBound)
    (checkpoint offset : ℕ) :
    dist (trajectory (checkpoint + offset)) (trajectory checkpoint) ≤
      (offset : ℝ) * stepBound := by
  induction offset with
  | zero => simp
  | succ offset ih =>
      calc
        dist (trajectory (checkpoint + Nat.succ offset))
            (trajectory checkpoint) ≤
            dist (trajectory (checkpoint + Nat.succ offset))
                (trajectory (checkpoint + offset)) +
              dist (trajectory (checkpoint + offset))
                (trajectory checkpoint) :=
          dist_triangle _ _ _
        _ ≤ stepBound + (offset : ℝ) * stepBound := by
          apply add_le_add
          · have hindex :
                checkpoint + Nat.succ offset = (checkpoint + offset) + 1 := by
              omega
            rw [hindex]
            exact h.2 (checkpoint + offset)
          · exact ih
        _ = (Nat.succ offset : ℝ) * stepBound := by
          push_cast
          ring

end PerStepDriftBound

/-! ## Between-validation residual guarantees -/

/-- Global residual smoothness and per-step metric drift control residual
change for every offset after a validation checkpoint. -/
theorem residual_drift_from_checkpoint_le
    {scope : Scope} {X : Type*} [PseudoMetricSpace X]
    {field : ResidualField scope X ℝ} {trajectory : ℕ → X}
    {L stepBound : ℝ} (hL : LipschitzResidual L field)
    (hstep : PerStepDriftBound trajectory stepBound)
    (checkpoint offset : ℕ) :
    |field (trajectory (checkpoint + offset)) - field (trajectory checkpoint)| ≤
      L * ((offset : ℝ) * stepBound) := by
  calc
    |field (trajectory (checkpoint + offset)) - field (trajectory checkpoint)| ≤
        L * dist (trajectory (checkpoint + offset))
          (trajectory checkpoint) := hL.2 _ _
    _ ≤ L * ((offset : ℝ) * stepBound) :=
      mul_le_mul_of_nonneg_left
        (hstep.distance_from_checkpoint_le checkpoint offset) hL.1

/-- A single period-wide budget is sound at every offset before the next
validation checkpoint. -/
theorem residual_drift_within_validation_period_le
    {scope : Scope} {X : Type*} [PseudoMetricSpace X]
    {field : ResidualField scope X ℝ} {trajectory : ℕ → X}
    {L stepBound : ℝ} (hL : LipschitzResidual L field)
    (hstep : PerStepDriftBound trajectory stepBound)
    (checkpoint offset period : ℕ) (hoffset : offset ≤ period) :
    |field (trajectory (checkpoint + offset)) - field (trajectory checkpoint)| ≤
      L * ((period : ℝ) * stepBound) := by
  have hoffsetReal : (offset : ℝ) ≤ (period : ℝ) := by
    exact_mod_cast hoffset
  have hmetric : (offset : ℝ) * stepBound ≤ (period : ℝ) * stepBound :=
    mul_le_mul_of_nonneg_right hoffsetReal hstep.1
  exact (residual_drift_from_checkpoint_le hL hstep checkpoint offset).trans
    (mul_le_mul_of_nonneg_left hmetric hL.1)

/-- An anchor checked at a validation checkpoint expands by at most the
Lipschitz drift budget at a later offset. -/
theorem residual_mem_expanded_checkpoint_anchor
    {scope : Scope} {X : Type*} [PseudoMetricSpace X]
    {field : ResidualField scope X ℝ} {trajectory : ℕ → X}
    {L stepBound : ℝ} (hL : LipschitzResidual L field)
    (hstep : PerStepDriftBound trajectory stepBound)
    (anchor : Anchor scope X) (hanchor : anchor.Contains field)
    (checkpoint offset : ℕ) (hpoint : anchor.point = trajectory checkpoint) :
    anchor.lower - L * ((offset : ℝ) * stepBound) ≤
        field (trajectory (checkpoint + offset)) ∧
      field (trajectory (checkpoint + offset)) ≤
        anchor.upper + L * ((offset : ℝ) * stepBound) := by
  have hcheckpoint :
      anchor.lower ≤ field (trajectory checkpoint) ∧
        field (trajectory checkpoint) ≤ anchor.upper := by
    unfold Anchor.Contains at hanchor
    rw [hpoint] at hanchor
    exact hanchor
  have hdrift := residual_drift_from_checkpoint_le hL hstep checkpoint offset
  rw [abs_le] at hdrift
  constructor <;> linarith [hcheckpoint.1, hcheckpoint.2, hdrift.1, hdrift.2]

/-- The checkpoint anchor midpoint remains a certified correction between
validations.  Its error budget is the anchor half-width plus the maximum
Lipschitz drift accumulated since the checkpoint. -/
theorem checkpoint_midpoint_error_le
    {scope : Scope} {X : Type*} [PseudoMetricSpace X]
    {field : ResidualField scope X ℝ} {trajectory : ℕ → X}
    {L stepBound : ℝ} (hL : LipschitzResidual L field)
    (hstep : PerStepDriftBound trajectory stepBound)
    (anchor : Anchor scope X) (hanchor : anchor.Contains field)
    (checkpoint offset : ℕ) (hpoint : anchor.point = trajectory checkpoint) :
    |field (trajectory (checkpoint + offset)) -
        (anchor.lower + anchor.upper) / 2| ≤
      L * ((offset : ℝ) * stepBound) + anchor.width / 2 := by
  have hdrift := residual_drift_from_checkpoint_le hL hstep checkpoint offset
  have hmidpoint := anchor.distance_to_midpoint_le_half_width field hanchor
  have hdecomposition :
      field (trajectory (checkpoint + offset)) -
          (anchor.lower + anchor.upper) / 2 =
        (field (trajectory (checkpoint + offset)) - field (trajectory checkpoint)) +
          (field anchor.point - (anchor.lower + anchor.upper) / 2) := by
    rw [hpoint]
    ring
  rw [hdecomposition]
  exact (abs_add_le _ _).trans (add_le_add hdrift hmidpoint)

/-- Period-wide midpoint certificate: one uniform error budget applies to
every offset before the next scheduled validation. -/
theorem checkpoint_midpoint_error_within_period_le
    {scope : Scope} {X : Type*} [PseudoMetricSpace X]
    {field : ResidualField scope X ℝ} {trajectory : ℕ → X}
    {L stepBound : ℝ} (hL : LipschitzResidual L field)
    (hstep : PerStepDriftBound trajectory stepBound)
    (anchor : Anchor scope X) (hanchor : anchor.Contains field)
    (checkpoint offset period : ℕ) (hoffset : offset ≤ period)
    (hpoint : anchor.point = trajectory checkpoint) :
    |field (trajectory (checkpoint + offset)) -
        (anchor.lower + anchor.upper) / 2| ≤
      L * ((period : ℝ) * stepBound) + anchor.width / 2 := by
  have hlocal := checkpoint_midpoint_error_le
    hL hstep anchor hanchor checkpoint offset hpoint
  have hoffsetReal : (offset : ℝ) ≤ (period : ℝ) := by
    exact_mod_cast hoffset
  have hmetric : (offset : ℝ) * stepBound ≤ (period : ℝ) * stepBound :=
    mul_le_mul_of_nonneg_right hoffsetReal hstep.1
  have hbudget :
      L * ((offset : ℝ) * stepBound) ≤
        L * ((period : ℝ) * stepBound) :=
    mul_le_mul_of_nonneg_left hmetric hL.1
  linarith

end OpenDistillationFactory.Materials.Theory.UniversalCorrection
