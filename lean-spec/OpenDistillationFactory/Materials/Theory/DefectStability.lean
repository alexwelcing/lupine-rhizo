import OpenDistillationFactory.Materials.Theory.BarrierArrhenius

/-!
# Defect stability: vacancy thermodynamics and the metastability window

Lead-free tin perovskites die by a defect mechanism: Sn²⁺ oxidizes to Sn⁴⁺
through oxygen insertion at tin vacancies, so the vacancy formation energy
`Ef` sets the stability ceiling. uMLIPs systematically underestimate `Ef`
because a vacancy's neighbours are under-coordinated — exactly the softening
regime of the environment error field. This module proves the resulting laws:

1. `vacancyFraction_*` — equilibrium vacancy site-fraction obeys the
   Boltzmann law `exp(−Ef/kT)`: softened `Ef` *overestimates* the vacancy
   population (`softened_Ef_overestimates_vacancies`) by exactly
   `exp(δ/kT)` (`vacancy_overestimation_factor`), ≥ 32× for a 100 meV error
   at room temperature (`sn_vacancy_100meV_overestimates_32x`). Raw screening
   therefore *understates* every tin perovskite's oxidation resistance —
   and correction restores the reference ordering of compositions
   (`RankingIntegrity.corrected_recovers_reference_order`).

2. The **metastability window**: many high-efficiency perovskites are
   kinetically trapped phases sitting slightly above the convex hull, held by
   a decomposition barrier. `synthesizableWindow` makes the accept region
   explicit (on-hull, or within hull tolerance *and* above a barrier floor);
   `hull_accept_subset_window` shows hull-only screening is a special case,
   `hull_screening_strictly_incomplete` exhibits a decidable witness the hull
   screen wrongly discards, and the monotonicity laws
   (`window_widens_with_tolerance`, `window_narrows_with_barrier_floor`)
   make the screening policy order-sensible so gates can be tuned without
   re-proof. This is the formal content of "impossibility proofs establish
   boundaries between candidates where predictions are reliable and
   candidates requiring synthesis-route engineering".

House rules: zero `sorry`, zero new axioms; window facts are decidable
integer-scaled statements in the style of the evidence corpus.
-/

namespace OpenDistillationFactory.Materials.Theory.DefectStability

open BarrierArrhenius

/-- Equilibrium vacancy site fraction in the dilute limit: `exp(−Ef/kT)`. -/
noncomputable def vacancyFraction (Ef kT : ℝ) : ℝ := boltzmann Ef kT

theorem vacancyFraction_pos (Ef kT : ℝ) : 0 < vacancyFraction Ef kT :=
  boltzmann_pos Ef kT

/-- **Softening overestimates vacancies.** A model that underestimates the
vacancy formation energy predicts at least the reference vacancy population:
raw uMLIP screening paints every tin perovskite as more oxidation-prone than
it is, burying the resistant compositions. -/
theorem softened_Ef_overestimates_vacancies {eModel eTrue kT : ℝ}
    (hkT : 0 < kT) (h : eModel ≤ eTrue) :
    vacancyFraction eTrue kT ≤ vacancyFraction eModel kT :=
  boltzmann_antitone hkT h

/-- **The vacancy amplification identity.** An `Ef` error of δ multiplies the
predicted vacancy fraction by exactly `exp(δ/kT)` — the same law that
amplifies barrier errors into rate errors. -/
theorem vacancy_overestimation_factor (Ef δ kT : ℝ) :
    vacancyFraction (Ef - δ) kT = Real.exp (δ / kT) * vacancyFraction Ef kT :=
  boltzmann_error_factor Ef δ kT

/-- **The Sn-vacancy lock.** A 100 meV underestimation of a tin vacancy
formation energy overstates the equilibrium vacancy density — hence the
oxygen-insertion attack surface — by at least 32× at room temperature
(kT = 25.85 meV). Numeric content shared with the barrier lock; restated here
because it is the perovskite failure mode. -/
theorem sn_vacancy_100meV_overestimates_32x :
    (32 : ℝ) ≤ Real.exp ((100 : ℝ) / (517 / 20)) :=
  barrier_error_100meV_amplifies_32x

/-! ## The metastability window (integer-scaled, decidable) -/

/-- Screening data for one candidate phase, integer-scaled in meV so window
membership is decidable: energy above the convex hull, and the kinetic
barrier holding the phase against decomposition. -/
structure PhaseScreen where
  /-- Energy above the convex hull, meV/atom. -/
  hullOffset_meV : ℕ
  /-- Kinetic barrier against transformation to the ground state, meV. -/
  escapeBarrier_meV : ℕ
  deriving DecidableEq, Repr

/-- The synthesizability window at hull tolerance `tol` and barrier floor
`bar`: a phase is admitted when it is the ground state, or when it is within
`tol` of the hull *and* kinetically protected by at least `bar`. -/
def synthesizableWindow (tol bar : ℕ) (p : PhaseScreen) : Prop :=
  p.hullOffset_meV = 0 ∨ (p.hullOffset_meV ≤ tol ∧ bar ≤ p.escapeBarrier_meV)

/-- Hull-only screening: accept exactly the phases on the convex hull. -/
def hullOnlyAccepts (p : PhaseScreen) : Prop := p.hullOffset_meV = 0

instance (tol bar : ℕ) (p : PhaseScreen) :
    Decidable (synthesizableWindow tol bar p) := by
  unfold synthesizableWindow; infer_instance

instance (p : PhaseScreen) : Decidable (hullOnlyAccepts p) := by
  unfold hullOnlyAccepts; infer_instance

/-- Everything the hull screen accepts, the window accepts: the window is a
relaxation, never a contradiction, of convex-hull screening. -/
theorem hull_accept_subset_window (tol bar : ℕ) (p : PhaseScreen)
    (h : hullOnlyAccepts p) : synthesizableWindow tol bar p :=
  Or.inl h

/-- **Hull-only screening is strictly incomplete.** A kinetically trapped
phase 25 meV above the hull behind a 500 meV decomposition barrier is inside
the (50 meV, 300 meV) synthesizability window yet rejected by the hull
screen — the class of solution-processed metastable perovskites that standard
convex-hull screening discards. Decidable witness. -/
theorem hull_screening_strictly_incomplete :
    ∃ p : PhaseScreen, synthesizableWindow 50 300 p ∧ ¬ hullOnlyAccepts p :=
  ⟨⟨25, 500⟩, by decide, by decide⟩

/-- Raising the hull tolerance only admits more phases (never re-rejects):
screening policy is monotone in the tolerance. -/
theorem window_widens_with_tolerance {tol₁ tol₂ bar : ℕ} (h : tol₁ ≤ tol₂)
    (p : PhaseScreen) :
    synthesizableWindow tol₁ bar p → synthesizableWindow tol₂ bar p := by
  rintro (h0 | ⟨h1, h2⟩)
  · exact Or.inl h0
  · exact Or.inr ⟨le_trans h1 h, h2⟩

/-- Raising the barrier floor only rejects more phases: the kinetic
requirement is antitone, so gates can be tightened without re-examining
accepted ground states. -/
theorem window_narrows_with_barrier_floor {tol bar₁ bar₂ : ℕ} (h : bar₁ ≤ bar₂)
    (p : PhaseScreen) :
    synthesizableWindow tol bar₂ p → synthesizableWindow tol bar₁ p := by
  rintro (h0 | ⟨h1, h2⟩)
  · exact Or.inl h0
  · exact Or.inr ⟨h1, le_trans h h2⟩

end OpenDistillationFactory.Materials.Theory.DefectStability
