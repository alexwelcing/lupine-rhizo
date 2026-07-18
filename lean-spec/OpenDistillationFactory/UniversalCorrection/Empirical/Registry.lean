/- Materialized empirical registry for the UniversalCorrection theorem surface.
Keep its contracts and gate policies synchronized with the JSON claim registry. -/

import OpenDistillationFactory.Materials.Theory.AccuracyCommitment
import OpenDistillationFactory.Materials.Theory.ActiveSampling
import OpenDistillationFactory.Materials.Theory.AffineDecomposition
-- import OpenDistillationFactory.Materials.Theory.AlloyResidualTransfer  -- quarantined 2026-07-02
import OpenDistillationFactory.Materials.Theory.ContextSpecificProof
import OpenDistillationFactory.Materials.Theory.ConvexProjection
import OpenDistillationFactory.Materials.Theory.ErrorGeometry
import OpenDistillationFactory.Materials.Theory.ExactTubularUniversality
import OpenDistillationFactory.Materials.Theory.FiniteSampleConcentration
import OpenDistillationFactory.Materials.Theory.HyperRibbon
import OpenDistillationFactory.Materials.Theory.HyperRibbonEmpirical
import OpenDistillationFactory.Materials.Theory.ParameterBound
import OpenDistillationFactory.Materials.Theory.ProjectedRibbon
import OpenDistillationFactory.Materials.Theory.ProjectionLaw
import OpenDistillationFactory.Materials.Theory.SmoothProjection
import OpenDistillationFactory.Materials.Theory.SpectrumBridge
import OpenDistillationFactory.Materials.Theory.UniversalityBridge
import OpenDistillationFactory.Materials.Theory.WeakAcceleration

namespace OpenDistillationFactory.UniversalCorrection.Empirical

/-- Epistemic classification for theorem declarations on the correction surface. -/
inductive EpistemicGrade where
  | pureMathematical
  | empiricallyConditional
  | assuranceExported
  | unsupportedOverScoped
  deriving BEq, DecidableEq, Repr

inductive DeclarationKind where
  | theorem
  | lemma
  deriving BEq, DecidableEq, Repr

inductive ContractStatus where
  | active
  | withdrawn
  | unsupported
  deriving BEq, DecidableEq, Repr

/-- Machine-readable predicate describing the empirical scope of a contract. -/
structure ScopePredicate where
  structures : List String
  properties : List String
  conditions : List String
  deriving BEq, DecidableEq, Repr

structure ClaimContractEntry where
  contractId : String
  status : ContractStatus
  epistemicGrade : EpistemicGrade
  scope : ScopePredicate
  /-- False when the authored ClaimContract explicitly says no Lean theorem proves it. -/
  leanBindingSupported : Bool
  deriving BEq, DecidableEq, Repr

structure TheoremInventoryEntry where
  moduleName : String
  declarationName : String
  declarationKind : DeclarationKind
  epistemicGrade : EpistemicGrade
  contractId : Option String
  deriving BEq, DecidableEq, Repr

inductive CorrectionGateDecision where
  | allow
  | deny
  deriving BEq, DecidableEq, Repr

/-- Runtime policy forced by the Round-3 disposition. A property-agnostic or
universally quantified theorem cannot override this empirical gate. -/
structure CorrectionGatePolicy where
  property : String
  decision : CorrectionGateDecision
  reason : String
  deriving BEq, DecidableEq, Repr

/-- Materialized scope/status view of the empirical ClaimContracts. -/
def claimContracts : List ClaimContractEntry := [
  { contractId := "barrier.accuracy.z1.v1", status := .withdrawn, epistemicGrade := .unsupportedOverScoped, scope := { structures := ["rocksalt"], properties := ["migration_barrier"], conditions := ["Hard Materials Z1", "barrier MAE ≤ 40 meV", "five-compound 3x3x3 MACE panel", "charged-reference versus neutral-CI-NEB convention caveat"] }, leanBindingSupported := false },
  { contractId := "correction.same_class.a0.v1", status := .active, epistemicGrade := .assuranceExported, scope := { structures := ["rocksalt", "perovskite"], properties := ["a0"], conditions := ["Round-3 out-of-sample", "leave-one-out within structure class"] }, leanBindingSupported := false },
  { contractId := "correction.b0.v1", status := .withdrawn, epistemicGrade := .unsupportedOverScoped, scope := { structures := ["rocksalt", "perovskite"], properties := ["B0"], conditions := ["Round-3 contradicting evidence", "correction gate deny for every class"] }, leanBindingSupported := false },
  { contractId := "fcc.b0.anticorrelation.v1", status := .withdrawn, epistemicGrade := .unsupportedOverScoped, scope := { structures := ["fcc"], properties := ["B0"], conditions := ["elemental metals", "negative Spearman association"] }, leanBindingSupported := false }
]

/-- The only active correction scope is same-class a0. B0 is denied
fail-closed because its Round-3 evidence contradicts improvement. -/
def correctionGatePolicies : List CorrectionGatePolicy := [
  { property := "a0", decision := .allow, reason := "scope_matched_same_class_a0" },
  { property := "B0", decision := .deny, reason := "contradicting_evidence" }
]

/-- Inventory of every theorem and lemma in the 17-module active correction theory surface
(AlloyResidualTransfer is quarantined and excluded). -/
def theoremInventory : List TheoremInventoryEntry := [
  { moduleName := "OpenDistillationFactory.Materials.Theory.AccuracyCommitment", declarationName := "accuracyGain_is_operative_value", declarationKind := .theorem, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.AccuracyCommitment", declarationName := "distill_win_has_positive_operative_value", declarationKind := .theorem, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.AccuracyCommitment", declarationName := "accuracyGain_pos_iff_improves", declarationKind := .theorem, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.AccuracyCommitment", declarationName := "mace_energy_beats_baseline", declarationKind := .theorem, epistemicGrade := .empiricallyConditional, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.AccuracyCommitment", declarationName := "sevennet_energy_beats_baseline", declarationKind := .theorem, epistemicGrade := .empiricallyConditional, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.AccuracyCommitment", declarationName := "sevennet_accelerate_beats_baseline", declarationKind := .theorem, epistemicGrade := .empiricallyConditional, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.AccuracyCommitment", declarationName := "mace_energy_reduction_is_material", declarationKind := .theorem, epistemicGrade := .empiricallyConditional, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.AccuracyCommitment", declarationName := "mace_stress_correctly_blocked", declarationKind := .theorem, epistemicGrade := .empiricallyConditional, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.AccuracyCommitment", declarationName := "mace_mp0_ni_energy_beats_baseline", declarationKind := .theorem, epistemicGrade := .empiricallyConditional, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.AccuracyCommitment", declarationName := "mace_mp0_ni_energy_reduction_is_material", declarationKind := .theorem, epistemicGrade := .empiricallyConditional, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.AccuracyCommitment", declarationName := "bridge_identity_is_proved", declarationKind := .theorem, epistemicGrade := .unsupportedOverScoped, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.AccuracyCommitment", declarationName := "broad_commitment_is_open", declarationKind := .theorem, epistemicGrade := .unsupportedOverScoped, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.ActiveSampling", declarationName := "exists_greedyChoice", declarationKind := .theorem, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.ActiveSampling", declarationName := "greedy_minimizes_max_remaining", declarationKind := .theorem, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.ActiveSampling", declarationName := "projection_norm_nonincreasing", declarationKind := .theorem, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.ActiveSampling", declarationName := "active_sampling_rank_bound", declarationKind := .theorem, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.AffineDecomposition", declarationName := "affineSubspace_convex", declarationKind := .theorem, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.AffineDecomposition", declarationName := "bestApprox_exists", declarationKind := .lemma, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.AffineDecomposition", declarationName := "bestApprox_mem", declarationKind := .theorem, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.AffineDecomposition", declarationName := "bestApprox_isBestApprox", declarationKind := .theorem, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.AffineDecomposition", declarationName := "residual_inner_le_zero", declarationKind := .theorem, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.AffineDecomposition", declarationName := "bias_orthogonal_direction", declarationKind := .theorem, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.AffineDecomposition", declarationName := "bias_in_orthogonal", declarationKind := .theorem, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.AffineDecomposition", declarationName := "withinFamily_in_direction", declarationKind := .theorem, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.AffineDecomposition", declarationName := "bias_orthogonal_withinFamily", declarationKind := .theorem, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.AffineDecomposition", declarationName := "decomposition", declarationKind := .theorem, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.ContextSpecificProof", declarationName := "ribbon_residual_is_deficit_sq", declarationKind := .theorem, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.ContextSpecificProof", declarationName := "context_correction_closes_exactly", declarationKind := .theorem, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.ContextSpecificProof", declarationName := "context_correction_necessary", declarationKind := .theorem, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.ContextSpecificProof", declarationName := "operativeValue_closed_form", declarationKind := .theorem, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.ContextSpecificProof", declarationName := "context_correction_strictly_valuable", declarationKind := .theorem, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.ContextSpecificProof", declarationName := "context_correction_optimal", declarationKind := .theorem, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.ContextSpecificProof", declarationName := "context_correction_does_not_transfer", declarationKind := .theorem, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.ContextSpecificProof", declarationName := "correction_decoupled_from_spectrum", declarationKind := .theorem, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.ContextSpecificProof", declarationName := "hyper_ribbon_survives_context_correction", declarationKind := .theorem, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.ContextSpecificProof", declarationName := "context_specific_operative_value", declarationKind := .theorem, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.ContextSpecificProof", declarationName := "cr_context_correction_is_valuable", declarationKind := .theorem, epistemicGrade := .empiricallyConditional, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.ContextSpecificProof", declarationName := "record_is_proved", declarationKind := .theorem, epistemicGrade := .unsupportedOverScoped, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.ConvexProjection", declarationName := "residual_mem_normalCone", declarationKind := .theorem, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.ConvexProjection", declarationName := "unique", declarationKind := .theorem, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.ConvexProjection", declarationName := "residual_eq", declarationKind := .theorem, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.ConvexProjection", declarationName := "consensus_needs_convexity", declarationKind := .theorem, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.ErrorGeometry", declarationName := "prBiasNoise_denom_pos", declarationKind := .theorem, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.ErrorGeometry", declarationName := "prBiasNoise_zero", declarationKind := .theorem, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.ErrorGeometry", declarationName := "prBiasNoise_le_dim", declarationKind := .theorem, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.ErrorGeometry", declarationName := "one_le_prBiasNoise", declarationKind := .theorem, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.ErrorGeometry", declarationName := "prBiasNoise_strictAnti", declarationKind := .theorem, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.ErrorGeometry", declarationName := "systematicFraction_nonneg", declarationKind := .theorem, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.ErrorGeometry", declarationName := "systematicFraction_lt_one", declarationKind := .theorem, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.ErrorGeometry", declarationName := "prSpectrum_rank_one", declarationKind := .theorem, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.ErrorGeometry", declarationName := "axisSecondMoment_sign_blind", declarationKind := .theorem, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.ErrorGeometry", declarationName := "axis_pr_one", declarationKind := .theorem, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.ErrorGeometry", declarationName := "pairAlignment_same_sign", declarationKind := .theorem, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.ErrorGeometry", declarationName := "pairAlignment_opposite_sign", declarationKind := .theorem, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.ErrorGeometry", declarationName := "ribbon_consensus_decoupled", declarationKind := .theorem, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.ErrorGeometry", declarationName := "systematicFraction_zero", declarationKind := .theorem, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.ErrorGeometry", declarationName := "systematicFraction_limit_one", declarationKind := .theorem, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.ErrorGeometry", declarationName := "prBiasNoise_one", declarationKind := .theorem, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.ErrorGeometry", declarationName := "prSpectrum_scale_invariant", declarationKind := .theorem, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.ErrorGeometry", declarationName := "axisSecondMoment_nonneg", declarationKind := .theorem, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.ErrorGeometry", declarationName := "pairAlignment_self", declarationKind := .theorem, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.ExactTubularUniversality", declarationName := "distToSet_nonneg", declarationKind := .lemma, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.ExactTubularUniversality", declarationName := "tangentProjection_C1", declarationKind := .lemma, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.ExactTubularUniversality", declarationName := "normalProjection_C1", declarationKind := .lemma, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.ExactTubularUniversality", declarationName := "tubularMap_contDiff", declarationKind := .lemma, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.ExactTubularUniversality", declarationName := "normalBundle_fiber_orthogonal", declarationKind := .lemma, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.ExactTubularUniversality", declarationName := "unitNormalBundle_subset_normalBundle", declarationKind := .lemma, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.ExactTubularUniversality", declarationName := "coreParam_spec", declarationKind := .lemma, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.ExactTubularUniversality", declarationName := "distToSet_le_mem", declarationKind := .lemma, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.ExactTubularUniversality", declarationName := "distToSet_eq_sInf", declarationKind := .lemma, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.ExactTubularUniversality", declarationName := "exists_nearestPoint", declarationKind := .lemma, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.ExactTubularUniversality", declarationName := "nearestPoint_mem_normalSpace", declarationKind := .lemma, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.ExactTubularUniversality", declarationName := "tubularMap_zero", declarationKind := .lemma, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.ExactTubularUniversality", declarationName := "IsC1Diffeomorphic.refl", declarationKind := .lemma, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.ExactTubularUniversality", declarationName := "IsC1Diffeomorphic.symm", declarationKind := .lemma, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.ExactTubularUniversality", declarationName := "IsC1Diffeomorphic.trans", declarationKind := .lemma, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.ExactTubularUniversality", declarationName := "smul_right_injective_real", declarationKind := .lemma, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.ExactTubularUniversality", declarationName := "boundary_subset_tube", declarationKind := .lemma, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.ExactTubularUniversality", declarationName := "boundaryDim_eq", declarationKind := .lemma, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.ExactTubularUniversality", declarationName := "psi_le_iff", declarationKind := .lemma, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.ExactTubularUniversality", declarationName := "distToSet_nonneg", declarationKind := .lemma, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.ExactTubularUniversality", declarationName := "highErrorSublevel_eq_highErrorTube_of_eta_zero", declarationKind := .lemma, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.ExactTubularUniversality", declarationName := "distToSet_singleton_zero", declarationKind := .lemma, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.ExactTubularUniversality", declarationName := "highErrorBoundary_pointCore", declarationKind := .lemma, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.ExactTubularUniversality", declarationName := "unitNormalBundle_pointCore", declarationKind := .lemma, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.ExactTubularUniversality", declarationName := "scale_sphere_mem", declarationKind := .lemma, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.ExactTubularUniversality", declarationName := "pointCore_boundary_diffeo", declarationKind := .lemma, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.ExactTubularUniversality", declarationName := "pointCore_boundary_pairwise_diffeo", declarationKind := .lemma, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.ExactTubularUniversality", declarationName := "radialThreshold_pos", declarationKind := .lemma, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.ExactTubularUniversality", declarationName := "exact_tubular_universality_pointCore", declarationKind := .theorem, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.ExactTubularUniversality", declarationName := "sublevel_eq_tube_general", declarationKind := .lemma, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.ExactTubularUniversality", declarationName := "boundary_diffeomorphic_unitNormalBundle", declarationKind := .lemma, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.ExactTubularUniversality", declarationName := "boundary_pairwise_diffeomorphic_general", declarationKind := .lemma, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.ExactTubularUniversality", declarationName := "exact_tubular_universality_of_A0ToA5", declarationKind := .theorem, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.FiniteSampleConcentration", declarationName := "ae_mem_of_identDistrib", declarationKind := .lemma, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.FiniteSampleConcentration", declarationName := "empiricalSecondMoment_unbiased", declarationKind := .theorem, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.FiniteSampleConcentration", declarationName := "product_bound", declarationKind := .lemma, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.FiniteSampleConcentration", declarationName := "secondMoment_bound", declarationKind := .lemma, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.FiniteSampleConcentration", declarationName := "empiricalSecondMoment_entrywise_concentration", declarationKind := .theorem, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.FiniteSampleConcentration", declarationName := "participationRatioMatrix_continuous", declarationKind := .theorem, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.HyperRibbon", declarationName := "hyper_ribbon_bound_3d", declarationKind := .theorem, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.HyperRibbon", declarationName := "PRfin_scale_invariant", declarationKind := .theorem, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.HyperRibbon", declarationName := "hyper_ribbon_bound_4d", declarationKind := .theorem, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.HyperRibbonEmpirical", declarationName := "empirical_hyper_ribbon_holds", declarationKind := .theorem, epistemicGrade := .empiricallyConditional, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.ParameterBound", declarationName := "syntheticEamSatisfiesBound", declarationKind := .theorem, epistemicGrade := .empiricallyConditional, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.ParameterBound", declarationName := "jacobianRank_le_params", declarationKind := .theorem, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.ParameterBound", declarationName := "jacobianRank_le_observables", declarationKind := .theorem, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.ParameterBound", declarationName := "jacobianRank_le_min", declarationKind := .theorem, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.ParameterBound", declarationName := "jacobianRank_zero_params", declarationKind := .theorem, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.ParameterBound", declarationName := "jacobianRank_zero_observables", declarationKind := .theorem, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.ParameterBound", declarationName := "eamFcc_effective_parameter_bound", declarationKind := .theorem, epistemicGrade := .empiricallyConditional, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.ParameterBound", declarationName := "observedEamFccPR_well_below_bound", declarationKind := .theorem, epistemicGrade := .empiricallyConditional, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.ParameterBound", declarationName := "lj_parameter_bound", declarationKind := .theorem, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.ParameterBound", declarationName := "sw_parameter_bound", declarationKind := .theorem, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.ParameterBound", declarationName := "jacobianRank_monotone_params", declarationKind := .theorem, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.ParameterBound", declarationName := "participationRatio_nonneg", declarationKind := .theorem, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.ParameterBound", declarationName := "participationRatio_le_N", declarationKind := .theorem, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.ParameterBound", declarationName := "participationRatio_le_rank_bound", declarationKind := .theorem, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.ParameterBound", declarationName := "parameterBound_conditional", declarationKind := .theorem, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.ProjectedRibbon", declarationName := "complement_dominance_bounds_stiff", declarationKind := .theorem, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.ProjectedRibbon", declarationName := "accepted_projection_distance_bounded", declarationKind := .theorem, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.ProjectedRibbon", declarationName := "accepted_stiff_drift_bounded", declarationKind := .theorem, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.ProjectedRibbon", declarationName := "accepted_support_lift_ok", declarationKind := .theorem, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.ProjectedRibbon", declarationName := "accepted_support_floor_satisfied", declarationKind := .theorem, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.ProjectedRibbon", declarationName := "projection_tube_refuses_outside_distance", declarationKind := .theorem, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.ProjectedRibbon", declarationName := "projection_tube_refuses_stiff_drift", declarationKind := .theorem, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.ProjectedRibbon", declarationName := "accepted_projected_win_has_positive_accuracy_gain", declarationKind := .theorem, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.ProjectedRibbon", declarationName := "accepted_projected_win_has_positive_operative_value", declarationKind := .theorem, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.ProjectionLaw", declarationName := "residual_inner_eq_zero", declarationKind := .theorem, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.ProjectionLaw", declarationName := "unique", declarationKind := .theorem, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.ProjectionLaw", declarationName := "residual_eq", declarationKind := .theorem, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.ProjectionLaw", declarationName := "residual_eq_zero_iff", declarationKind := .theorem, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.SmoothProjection", declarationName := "toFun_differentiableAt", declarationKind := .lemma, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.SmoothProjection", declarationName := "sqDist_differentiableAt", declarationKind := .lemma, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.SmoothProjection", declarationName := "sqDist_fderiv_apply", declarationKind := .lemma, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.SmoothProjection", declarationName := "residual_orthogonal_to_tangent", declarationKind := .theorem, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.SmoothProjection", declarationName := "residual_mem_normalSpace", declarationKind := .theorem, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.SmoothProjection", declarationName := "local_consensus_weak", declarationKind := .theorem, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.SpectrumBridge", declarationName := "biasNoiseOp_eigen_bias", declarationKind := .theorem, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.SpectrumBridge", declarationName := "biasNoiseOp_eigen_orth", declarationKind := .theorem, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.SpectrumBridge", declarationName := "prSpectrumFin_smul", declarationKind := .theorem, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.SpectrumBridge", declarationName := "sum_biasNoiseSpectrum", declarationKind := .theorem, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.SpectrumBridge", declarationName := "sumsq_biasNoiseSpectrum", declarationKind := .theorem, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.SpectrumBridge", declarationName := "prSpectrumFin_biasNoise", declarationKind := .theorem, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.SpectrumBridge", declarationName := "prBiasNoise_sub_one_le", declarationKind := .theorem, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.UniversalityBridge", declarationName := "refuse_prob_nonneg", declarationKind := .theorem, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.UniversalityBridge", declarationName := "pRefuse_nonneg", declarationKind := .theorem, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.UniversalityBridge", declarationName := "speedup_ge_one", declarationKind := .theorem, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.UniversalityBridge", declarationName := "speedup_tightness", declarationKind := .theorem, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.UniversalityBridge", declarationName := "accuracy_axis_is_operative_value", declarationKind := .theorem, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.UniversalityBridge", declarationName := "cellValue_baseline", declarationKind := .theorem, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.UniversalityBridge", declarationName := "cellValue_mono_speed", declarationKind := .theorem, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.UniversalityBridge", declarationName := "cellValue_mono_accuracy", declarationKind := .theorem, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.UniversalityBridge", declarationName := "complementary_improvement", declarationKind := .theorem, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.UniversalityBridge", declarationName := "complementary_strict", declarationKind := .theorem, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.UniversalityBridge", declarationName := "complementary_intervention_passes_gate", declarationKind := .theorem, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.UniversalityBridge", declarationName := "shared_ribbon_premise", declarationKind := .theorem, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.UniversalityBridge", declarationName := "pRefuse_lt_one", declarationKind := .theorem, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.UniversalityBridge", declarationName := "speedup_strict", declarationKind := .theorem, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.UniversalityBridge", declarationName := "cellValue_nonneg", declarationKind := .theorem, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.UniversalityBridge", declarationName := "composition_is_verified", declarationKind := .theorem, epistemicGrade := .unsupportedOverScoped, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.WeakAcceleration", declarationName := "savedLayerFraction_nonneg", declarationKind := .theorem, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.WeakAcceleration", declarationName := "uncoveredMass_nonneg", declarationKind := .theorem, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.WeakAcceleration", declarationName := "catchProbability_nonneg", declarationKind := .theorem, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.WeakAcceleration", declarationName := "weakSpeedup_ge_one", declarationKind := .theorem, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.WeakAcceleration", declarationName := "weakSpeedup_ge_one_despite_spectral_failure", declarationKind := .theorem, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.WeakAcceleration", declarationName := "weakConditions_independent_of_rho", declarationKind := .theorem, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.WeakAcceleration", declarationName := "weakSpeedup_lift_nonneg", declarationKind := .theorem, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.WeakAcceleration", declarationName := "savedLayerFraction_le_one", declarationKind := .theorem, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.WeakAcceleration", declarationName := "uncoveredMass_le_one", declarationKind := .theorem, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.WeakAcceleration", declarationName := "catchProbability_lt_one", declarationKind := .theorem, epistemicGrade := .pureMathematical, contractId := none },
  { moduleName := "OpenDistillationFactory.Materials.Theory.WeakAcceleration", declarationName := "weakSpeedup_strict", declarationKind := .theorem, epistemicGrade := .pureMathematical, contractId := none }
]

private def eligibleContract (contractId : String) : Bool :=
  claimContracts.any (fun contract =>
    contract.contractId == contractId && contract.leanBindingSupported)

private def assuranceBindingValid (entry : TheoremInventoryEntry) : Bool :=
  if entry.epistemicGrade == .assuranceExported then
    entry.contractId.any eligibleContract
  else
    entry.contractId.isNone

/-- An assurance export is impossible without a known ClaimContract identifier. -/
def allAssuranceExportsBound : Bool := theoremInventory.all assuranceBindingValid

/-- Current contracts deliberately have no Lean binding: their authored contracts say
that the empirical Round-3 outcomes are not proved by an existing Lean theorem. -/
def activeLeanBindings : List TheoremInventoryEntry :=
  theoremInventory.filter (fun entry => entry.epistemicGrade == .assuranceExported)

/-- Property-agnostic mathematical theorems do not constitute empirical B0 assurance. -/
def b0AssuranceBindings : List TheoremInventoryEntry :=
  theoremInventory.filter (fun entry => entry.contractId == some "correction.b0.v1")

#guard theoremInventory.length == 172
#guard (theoremInventory.map (·.moduleName) |>.eraseDups |>.length) == 17
#guard allAssuranceExportsBound
#guard activeLeanBindings.isEmpty
#guard claimContracts.any (fun contract =>
  contract.contractId == "barrier.accuracy.z1.v1" && contract.status == .withdrawn)
#guard correctionGatePolicies.any (fun policy =>
  policy.property == "B0" && policy.decision == .deny &&
    policy.reason == "contradicting_evidence")
#guard b0AssuranceBindings.isEmpty

end OpenDistillationFactory.UniversalCorrection.Empirical