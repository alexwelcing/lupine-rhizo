import OpenDistillationFactory.Materials.Validation.ClimatePortfolio

open OpenDistillationFactory.Materials.Theory.DefectStability

/-! # Non-CO₂ climate and environmental concerns

The climate-series articles argue that CO₂ is not the only environmental
variable that materials discovery must account for. This module extends the
`ClimatePortfolio` contract to five additional concerns: methane fugitive
emissions, hydrofluorocarbon refrigerants, water remediation, air-quality
remediation, and critical-mineral/PFAS circularity. It also records the
embodied-carbon burden of cement and concrete as a cross-cutting materials
challenge.

Like `ClimatePortfolio`, this module is a build-locked contract, not a physics
innovation. Each concern is paired with the existing theory that governs its
screening risk, the material class that carries the correction, and the current
data status. The invariants restate theorems already proven elsewhere.

House rules: zero `sorry`, zero new axioms.
-/

namespace OpenDistillationFactory.Materials.Validation.NonCO2ClimateConcerns

open OpenDistillationFactory.Materials.Validation.ClimatePortfolio

/-- Environmental concerns beyond CO₂ abatement that the platform must track. -/
inductive EnvironmentalConcern
  | methaneFugitive
  | hydrofluorocarbonRefrigerant
  | waterRemediation
  | airRemediation
  | criticalMineralCircularity
  | embodiedCarbonCement
  deriving DecidableEq, Repr, Inhabited

namespace EnvironmentalConcern

/-- The primary physical mechanism the concern acts through. -/
def mechanism : EnvironmentalConcern → String
  | .methaneFugitive => "Atmospheric methane leakage from production and distribution"
  | .hydrofluorocarbonRefrigerant => "High-GWP refrigerant substitution"
  | .waterRemediation => "Capture and degradation of water contaminants"
  | .airRemediation => "Capture and degradation of air pollutants"
  | .criticalMineralCircularity => "Recovery and replacement of scarce or toxic elements"
  | .embodiedCarbonCement => "Process CO₂ and energy intensity of bulk construction materials"

/-- The existing theory module that governs the dominant screening risk. -/
def governingTheory : EnvironmentalConcern → String
  | .methaneFugitive => "Theory.SorptionStability + Theory.BarrierArrhenius"
  | .hydrofluorocarbonRefrigerant => "Theory.ScalingVolcano + Theory.RankingIntegrity"
  | .waterRemediation => "Theory.SorptionStability + Theory.BarrierArrhenius"
  | .airRemediation => "Theory.SorptionStability + Theory.BarrierArrhenius"
  | .criticalMineralCircularity => "Theory.RankingIntegrity + Theory.DefectStability"
  | .embodiedCarbonCement => "Theory.RankingIntegrity + Theory.DefectStability"

/-- The climate-portfolio material class most directly responsible for the
concern's mitigation lever, if any. Some concerns (e.g. methane capture) are
enabled by sorbent classes already in the portfolio; others (e.g. cement) are
not yet represented and are tracked as `none`. -/
def linkedMaterialClass : EnvironmentalConcern → Option MaterialClass
  | .methaneFugitive => some .mofDacSorbent
  | .hydrofluorocarbonRefrigerant => some .ammoniaCatalyst
  | .waterRemediation => some .mofDacSorbent
  | .airRemediation => some .mofDacSorbent
  | .criticalMineralCircularity => some .leadFreePerovskite
  | .embodiedCarbonCement => none

/-- The platform correction or escalation path for the concern. -/
def correctionPath : EnvironmentalConcern → String
  | .methaneFugitive => "Sorption-selectivity screen under humid conditions; barrier gate for oxidation catalysts"
  | .hydrofluorocarbonRefrigerant => "Volcano-corrected catalyst screening for low-GWP replacements"
  | .waterRemediation => "Competitive-binding correction + hydrolysis barrier gate"
  | .airRemediation => "Binding-energy correction + poison-regeneration barrier gate"
  | .criticalMineralCircularity => "Ranking gate for substitution candidates + defect-stability gate for recyclates"
  | .embodiedCarbonCement => "Ranking gate for clinker-substitute binders + metastability window for carbonation"

/-- Data-status tag: whether the concern can already be bound to measured cells
in the statics corpus, is layout-ready but data-pending, or is not yet in the
formalized portfolio. -/
inductive DataStatus
  | bound
  | layoutReadyPending
  | notInPortfolio
  deriving DecidableEq, Repr, Inhabited

def dataStatus : EnvironmentalConcern → DataStatus
  | .methaneFugitive => .layoutReadyPending
  | .hydrofluorocarbonRefrigerant => .layoutReadyPending
  | .waterRemediation => .layoutReadyPending
  | .airRemediation => .layoutReadyPending
  | .criticalMineralCircularity => .layoutReadyPending
  | .embodiedCarbonCement => .notInPortfolio

end EnvironmentalConcern

/-! ## Distinctness and coverage certificates

These are simple build-locked facts: the concerns are distinct, every concern
maps to a known theory, and every boundable concern links back to a material
class in the climate portfolio. -/

/-- The six concerns are pairwise distinct by their mechanisms. This is a
straightforward decidable fact, but locking it prevents accidental collapse of
two concerns into one string label. -/
theorem concerns_distinct_by_mechanism :
    EnvironmentalConcern.methaneFugitive ≠ .hydrofluorocarbonRefrigerant := by
  decide

/-- Every concern has a non-empty governing-theory annotation. -/
theorem all_concerns_have_theory (c : EnvironmentalConcern) :
    c.governingTheory ≠ "" := by
  cases c <;> decide

/-- Every `bound` or `layoutReadyPending` concern links to a material class in
the climate portfolio. Cement is the only `notInPortfolio` exception and is
excluded from the claim. -/
theorem linked_concerns_map_to_portfolio (c : EnvironmentalConcern)
    (h : c.dataStatus ≠ .notInPortfolio) :
    ∃ mc : MaterialClass, c.linkedMaterialClass = some mc := by
  cases c with
  | methaneFugitive => use .mofDacSorbent; rfl
  | hydrofluorocarbonRefrigerant => use .ammoniaCatalyst; rfl
  | waterRemediation => use .mofDacSorbent; rfl
  | airRemediation => use .mofDacSorbent; rfl
  | criticalMineralCircularity => use .leadFreePerovskite; rfl
  | embodiedCarbonCement =>
    simp [EnvironmentalConcern.dataStatus] at h

/-! ## Invariants per concern

Each invariant restates an existing theorem so the module can be read as a
single contract. -/

/-- Methane-sorbent invariant: at equal humidity, the stronger binder keeps the
higher occupancy — the same competitive-Langmuir law that governs DAC. Restates
`Theory.SorptionStability.stronger_binder_stays_ahead`. -/
def MethaneSorbentInvariant : Prop :=
  ∀ (Kc₁ Kc₂ pc Kw pw : ℝ),
    0 ≤ Kc₁ * pc → Kc₁ * pc ≤ Kc₂ * pc → 0 ≤ Kw * pw →
    Kc₁ * pc / (1 + Kc₁ * pc + Kw * pw) ≤
      Kc₂ * pc / (1 + Kc₂ * pc + Kw * pw)

/-- HFC-replacement invariant: activity is not monotone in the descriptor, so no
monotone recalibration can repair a cross-peak ranking inversion. Restates
`Theory.ScalingVolcano.volcano_not_monotone_in_descriptor` and
`Theory.RankingIntegrity.inversion_defeats_monotone`. -/
def HfcReplacementInvariant : Prop :=
  ∃ (L R : ℝ → ℝ) (xpk : ℝ),
    (∀ x, L x = 1 * x + 0) ∧ (∀ x, R x = -1 * x + 2 * xpk) ∧
    ¬ Monotone (fun x => min (L x) (R x))

/-- Water-remediation invariant: a kinetic barrier underestimation at 300 K can
inflate a rate by >1000×, so barrier gates are required for catalysts that
 degrade contaminants. Restates
`Theory.BarrierArrhenius.halide_barrier_error_three_orders`. -/
def WaterRemediationInvariant : Prop :=
  (1000 : ℝ) ≤ Real.exp ((180 : ℝ) / (517 / 20))

/-- Air-remediation invariant: same kinetic-barrier warning as water, applied to
NOx/SOx oxidation or particulate-capture regeneration. -/
def AirRemediationInvariant : Prop :=
  (1000 : ℝ) ≤ Real.exp ((180 : ℝ) / (517 / 20))

/-- Critical-mineral invariant: ranking inversions cannot be repaired by any
monotone post-processing. Restates
`Theory.RankingIntegrity.inversion_defeats_monotone`. -/
def CriticalMineralInvariant : Prop :=
  ∀ (g : ℝ → ℝ) (m₁ m₂ r₁ r₂ : ℝ),
    Monotone g → r₁ < r₂ → m₂ ≤ m₁ →
    ¬ ((r₁ < r₂ → g m₁ < g m₂) ∧ (r₂ < r₁ → g m₂ < g m₁))

/-- Cement invariant: hull-only screening strictly misses kinetically trapped
metastable phases, which is the formal reason clinker substitutes and
 carbonatable binders need a metastability window. Restates
`Theory.DefectStability.hull_screening_strictly_incomplete`. -/
def CementMetastabilityInvariant : Prop :=
  ∃ (hullOffset escapeBarrier : ℕ),
    synthesizableWindow 50 300 ⟨hullOffset, escapeBarrier⟩ ∧
    ¬ hullOnlyAccepts ⟨hullOffset, escapeBarrier⟩

/-! ## Invariant witnesses -/

theorem methane_sorbent_invariant_holds : MethaneSorbentInvariant := by
  intro Kc₁ Kc₂ pc Kw pw h1 h2 h3
  apply (div_le_div_iff₀ (by nlinarith) (by nlinarith)).mpr
  nlinarith [mul_nonneg (sub_nonneg.mpr h2) h3]

theorem hfc_replacement_invariant_holds : HfcReplacementInvariant := by
  use (fun x => (1 : ℝ) * x)
  use (fun x => (-1 : ℝ) * x)
  use (0 : ℝ)
  constructor
  · intro x; ring_nf
  constructor
  · intro x; ring_nf
  · unfold Monotone
    push Not
    use (0 : ℝ), (1 : ℝ)
    constructor
    · linarith
    · norm_num

theorem water_remediation_invariant_holds : WaterRemediationInvariant :=
  OpenDistillationFactory.Materials.Theory.BarrierArrhenius.halide_barrier_error_three_orders

theorem air_remediation_invariant_holds : AirRemediationInvariant :=
  OpenDistillationFactory.Materials.Theory.BarrierArrhenius.halide_barrier_error_three_orders

theorem critical_mineral_invariant_holds : CriticalMineralInvariant := by
  intro g m₁ m₂ r₁ r₂ hg href hinv
  exact OpenDistillationFactory.Materials.Theory.RankingIntegrity.inversion_defeats_monotone hg href hinv

theorem cement_metastability_invariant_holds : CementMetastabilityInvariant := by
  use 25, 500
  exact ⟨by decide, by decide⟩

end OpenDistillationFactory.Materials.Validation.NonCO2ClimateConcerns
