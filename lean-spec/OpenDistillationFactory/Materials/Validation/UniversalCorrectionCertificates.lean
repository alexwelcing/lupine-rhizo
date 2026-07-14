import Mathlib.Tactic.NormNum
import OpenDistillationFactory.Materials.Theory.UniversalCorrection.Aggregation
import OpenDistillationFactory.Materials.Theory.UniversalCorrection.Descriptor
import OpenDistillationFactory.Materials.Theory.UniversalCorrection.RobustRanking
import OpenDistillationFactory.Materials.Theory.UniversalCorrection.ScalarEnvelope

/-!
# Synthetic certificates for the universal correction core

This module instantiates the representation-agnostic theory on small, exact
examples.  The fixtures contain no empirical claims; they are executable
regression certificates for the semantics that production evidence must use:

* the fixed-point gate reaches each of its three outcomes exactly;
* correction authorization is fail-closed;
* separated score intervals certify a true minimization ranking;
* a descriptor collision with unequal residuals blocks factorization;
* distributed severity reduction is order independent and fail-closed; and
* a one-anchor Lipschitz corpus supplies an exact midpoint envelope.

All numerals are exact Lean integers or rationals.  There is no floating-point
evaluation and no unproved scientific assumption in this file.
-/

namespace OpenDistillationFactory.Materials.Validation.UniversalCorrectionCertificates

open OpenDistillationFactory.Materials.Theory.UniversalCorrection

/-! ## One fully specified semantic scope -/

/-- Synthetic content-addressed model identity used only by these fixtures. -/
def fixtureModel : ArtifactId where
  name := "fixture-model"
  version := "1"
  digest := "sha256:model-fixture"

/-- Synthetic reference-method identity used only by these fixtures. -/
def fixtureReference : ArtifactId where
  name := "fixture-reference"
  version := "1"
  digest := "sha256:reference-fixture"

/-- A complete scope demonstrates that every downstream value is indexed by
model, reference, observable, molecular context, descriptor, units, and
numeric interpretation. -/
def fixtureScope : Scope where
  model := fixtureModel
  reference := fixtureReference
  observable := "total-energy"
  context := {
    species := ["H", "H"]
    charge := 0
    spinConvention := "singlet"
    boundaryConditions := "isolated"
  }
  descriptor := {
    artifact := {
      name := "fixture-descriptor"
      version := "1"
      digest := "sha256:descriptor-fixture"
    }
    metricConvention := "discrete-v1"
  }
  units := "eV"
  numericSemantics := "exact-fixed-point-v1"

/-! ## Exact tri-state gate and fail-closed authorization -/

def admittedEnvelope : FixedEnvelope where
  lower := 100
  upper := 104

def refusedEnvelope : FixedEnvelope where
  lower := 105
  upper := 104

def indeterminateEnvelope : FixedEnvelope where
  lower := 100
  upper := 110

/-- A consistent interval of width four is admitted at tolerance five. -/
theorem exact_gate_admits :
    checkFixedEnvelope 5 admittedEnvelope = .admit := by
  decide

/-- An inverted interval produces a definite refusal witness. -/
theorem exact_gate_refuses :
    checkFixedEnvelope 5 refusedEnvelope = .refuse .inconsistent := by
  decide

/-- A consistent interval wider than policy tolerance is indeterminate, not a
scientific refusal and not an admission. -/
theorem exact_gate_is_indeterminate :
    checkFixedEnvelope 5 indeterminateEnvelope =
      .indeterminate .widthTooLarge := by
  decide

/-- The admitted fixture authorizes correction. -/
theorem admitted_correction_is_allowed :
    correctionAllowed (checkFixedEnvelope 5 admittedEnvelope) = true := by
  rw [exact_gate_admits]
  rfl

/-- A definite refusal cannot authorize correction. -/
theorem refused_correction_is_blocked :
    correctionAllowed (checkFixedEnvelope 5 refusedEnvelope) = false := by
  rw [exact_gate_refuses]
  rfl

/-- Insufficient resolution is also blocked: the operational policy is
strictly fail-closed. -/
theorem indeterminate_correction_is_blocked :
    correctionAllowed (checkFixedEnvelope 5 indeterminateEnvelope) = false := by
  rw [exact_gate_is_indeterminate]
  rfl

/-! ## Deterministic robust ranking -/

def lowerScore : ScoreInterval where
  lower := 1
  upper := 2
  valid := by norm_num

def higherScore : ScoreInterval where
  lower := 3
  upper := 5
  valid := by norm_num

/-- The complete lower-score interval lies below the higher-score interval. -/
theorem robust_ranking_certificate :
    lowerScore.RobustlyPrecedes higherScore := by
  norm_num [ScoreInterval.RobustlyPrecedes, lowerScore, higherScore]

/-- Instantiating interval soundness certifies the true order `3/2 < 7/2`. -/
theorem robust_ranking_true_scores :
    (3 / 2 : ℝ) < 7 / 2 := by
  apply ScoreInterval.robustlyPrecedes_sound robust_ranking_certificate
  · norm_num [ScoreInterval.Contains, lowerScore]
  · norm_num [ScoreInterval.Contains, higherScore]

/-! ## Descriptor collision and factorization obstruction -/

/-- A deliberately lossy descriptor that maps both configurations to the same
feature value. -/
def collidingDescriptor : Descriptor fixtureScope Bool Unit where
  encode := fun _ => ()

/-- A residual that distinguishes the two configurations hidden by the
descriptor. -/
def separatedResidual : ResidualField fixtureScope Bool Nat
  | false => 0
  | true => 1

theorem fixture_descriptor_collision :
    collidingDescriptor.Collision false true := rfl

theorem fixture_residuals_separated :
    separatedResidual false ≠ separatedResidual true := by
  decide

/-- The unequal residuals cannot be represented as any readout of the lossy
descriptor.  A runtime gate must therefore refuse this descriptor scope. -/
theorem collision_blocks_factorization :
    ¬ Descriptor.FactorsThrough collidingDescriptor separatedResidual :=
  Descriptor.collision_obstructs_factorization
    fixture_descriptor_collision fixture_residuals_separated

/-- In contrast, retaining the configuration itself gives a valid exact
factorization.  This positive fixture checks the meaning of `FactorsThrough`. -/
def injectiveDescriptor : Descriptor fixtureScope Bool Bool where
  encode := id

theorem injective_descriptor_factors :
    Descriptor.FactorsThrough injectiveDescriptor separatedResidual := by
  refine ⟨separatedResidual, ?_⟩
  intro configuration
  rfl

/-! ## Deterministic distributed aggregation -/

/-- Any definite refusal dominates admission and indeterminacy. -/
theorem distributed_refusal_dominates :
    Severity.aggregate [.admit, .indeterminate, .refuse, .admit] = .refuse := by
  rfl

/-- Reordering workers does not change the global severity. -/
theorem distributed_reordering_stable :
    Severity.aggregate [.admit, .indeterminate, .refuse] =
      Severity.aggregate [.refuse, .admit, .indeterminate] := by
  apply Severity.aggregate_eq_of_perm
  decide

/-- A globally admitted reduction certifies that every local worker admitted. -/
theorem distributed_all_admit :
    Severity.aggregate [.admit, .admit, .admit] = .admit := by
  rfl

/-- Gate results may discard their payloads only after conversion to the
decision-severity algebra; the refusal still dominates globally. -/
theorem distributed_gate_results_fail_closed :
    Severity.aggregate
      [ (checkFixedEnvelope 5 admittedEnvelope).severity,
        (checkFixedEnvelope 5 indeterminateEnvelope).severity,
        (checkFixedEnvelope 5 refusedEnvelope).severity ] = .refuse := by
  rw [exact_gate_admits, exact_gate_is_indeterminate, exact_gate_refuses]
  rfl

/-! ## A scalar-envelope certificate -/

/-- A constant synthetic residual on the real configuration line. -/
def scalarResidual : ResidualField fixtureScope ℝ ℝ := fun _ => 3

def scalarAnchor : Anchor fixtureScope ℝ :=
  Anchor.exact 0 3

def scalarCorpus : AnchorCorpus fixtureScope ℝ where
  head := scalarAnchor
  tail := []

theorem scalar_corpus_contains : scalarCorpus.Contains scalarResidual := by
  simp [scalarCorpus, scalarAnchor, scalarResidual, AnchorCorpus.Contains,
    AnchorCorpus.toList]

theorem scalar_residual_lipschitz : LipschitzResidual 0 scalarResidual := by
  constructor
  · norm_num
  · intro x y
    simp [scalarResidual]

/-- The finite-envelope theorem certifies the chosen midpoint directly. -/
theorem scalar_midpoint_error_certificate :
    |scalarResidual 7 - scalarCorpus.midpoint 0 7| ≤
      scalarCorpus.radius 0 7 :=
  midpoint_error_le_radius (x := 7) scalar_corpus_contains scalar_residual_lipschitz

/-- In this exact one-anchor fixture the enclosure collapses to the measured
residual, so its midpoint is 3 and its radius is zero. -/
theorem scalar_envelope_collapses :
    scalarCorpus.lowerBound 0 7 = 3 ∧
      scalarCorpus.upperBound 0 7 = 3 ∧
      scalarCorpus.midpoint 0 7 = 3 ∧
      scalarCorpus.radius 0 7 = 0 := by
  norm_num [scalarCorpus, scalarAnchor, Anchor.exact, AnchorCorpus.lowerBound,
    AnchorCorpus.upperBound, AnchorCorpus.midpoint, AnchorCorpus.radius,
    lowerTerm, upperTerm]

end OpenDistillationFactory.Materials.Validation.UniversalCorrectionCertificates
