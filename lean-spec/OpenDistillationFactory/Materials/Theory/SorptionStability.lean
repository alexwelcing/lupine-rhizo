import OpenDistillationFactory.Materials.Theory.BarrierArrhenius

/-!
# Sorption and stability laws for direct-air-capture sorbents

A DAC sorbent must do two things at once: bind CO₂ at 400 ppm while water is
present at percent-level humidity, and survive hydrolysis of its metal–linker
bonds. This module formalizes both, plus the domain gate that keeps the
environment error field honest on MOF chemistry:

1. **Competitive Langmuir occupancy.** `competitiveLoading` is the CO₂
   occupancy of a binding site competing with water. We prove the dry limit
   collapses to single-species Langmuir (`competitive_dry_limit`), occupancy
   is strictly suppressed by humidity (`humidity_suppresses`), and — the
   screening law — a site with stronger CO₂ affinity keeps its lead at *any*
   shared humidity (`stronger_binder_stays_ahead`): capacity ranking at equal
   humidity is affinity ranking, so humid-condition screening can rank by
   corrected binding constants without re-simulating every humidity.

2. **Hydrolysis screening is conservative under softening.** uMLIPs soften
   metal–linker bond dissociation, so predicted hydrolysis rates are
   *overestimates*; a framework whose *model* degradation rate passes the
   stability threshold truly passes
   (`softening_conservative_for_stability`). False positives are impossible;
   the cost of softening is false negatives — humidity-stable frameworks
   discarded — which is precisely what the correction recovers.

3. **The first-shell domain gate.** The error field is measured on a
   coordination interval; environments outside it (mixed-metal nodes,
   under-coordinated open-metal sites) are out of the field's domain.
   `FieldDomain.admits` is the executable gate; `admits_iff` proves it sound
   and complete for the domain predicate, `refusal_has_witness` extracts a
   concrete out-of-domain atom from every refusal ("Lupine proves the domain
   violation and reports the witness"), and the two decidable certificates
   show a uniform Zr₆-type node admitted and a defected mixed node refused.

House rules: zero `sorry`, zero new axioms.
-/

namespace OpenDistillationFactory.Materials.Theory.SorptionStability

open BarrierArrhenius

/-- Single-species Langmuir occupancy of a binding site: `Kp/(1+Kp)` at
affinity `K` and partial pressure `p` (occupancy per site, dimensionless). -/
noncomputable def langmuirLoading (K p : ℝ) : ℝ := K * p / (1 + K * p)

/-- CO₂ occupancy under competitive co-adsorption of water:
`K_c p_c / (1 + K_c p_c + K_w p_w)`. -/
noncomputable def competitiveLoading (Kc pc Kw pw : ℝ) : ℝ :=
  Kc * pc / (1 + Kc * pc + Kw * pw)

/-- With no water present, competitive occupancy is single-species Langmuir. -/
theorem competitive_dry_limit (Kc pc Kw : ℝ) :
    competitiveLoading Kc pc Kw 0 = langmuirLoading Kc pc := by
  unfold competitiveLoading langmuirLoading
  norm_num

theorem competitiveLoading_nonneg {Kc pc Kw pw : ℝ}
    (hc : 0 ≤ Kc * pc) (hw : 0 ≤ Kw * pw) :
    0 ≤ competitiveLoading Kc pc Kw pw := by
  unfold competitiveLoading
  have hden : 0 < 1 + Kc * pc + Kw * pw := by linarith
  positivity

/-- Occupancy never saturates past a full site. -/
theorem competitiveLoading_lt_one {Kc pc Kw pw : ℝ}
    (hc : 0 ≤ Kc * pc) (hw : 0 ≤ Kw * pw) :
    competitiveLoading Kc pc Kw pw < 1 := by
  unfold competitiveLoading
  have hden : 0 < 1 + Kc * pc + Kw * pw := by linarith
  rw [div_lt_one hden]
  linarith

/-- **Humidity strictly suppresses CO₂ uptake.** More water partial pressure,
strictly less CO₂ occupancy — the mechanism behind the 40–70 % RH stability
requirement in the DAC target. -/
theorem humidity_suppresses {Kc pc Kw pw₁ pw₂ : ℝ}
    (hc : 0 < Kc * pc) (hKw : 0 < Kw) (hw₁ : 0 ≤ pw₁) (h : pw₁ < pw₂) :
    competitiveLoading Kc pc Kw pw₂ < competitiveLoading Kc pc Kw pw₁ := by
  unfold competitiveLoading
  have hwp₁ : 0 ≤ Kw * pw₁ := mul_nonneg hKw.le hw₁
  have hden₁ : 0 < 1 + Kc * pc + Kw * pw₁ := by linarith
  have hden₂ : 0 < 1 + Kc * pc + Kw * pw₂ := by nlinarith
  rw [div_lt_div_iff₀ hden₂ hden₁]
  have hgrow : Kw * pw₁ < Kw * pw₂ := by
    exact mul_lt_mul_of_pos_left h hKw
  nlinarith

/-- **The screening law for humid capacity.** At any shared humidity, the site
with the stronger CO₂ affinity keeps at least the occupancy of the weaker
one: capacity ranking at equal humidity is affinity ranking. Rank candidates
by corrected binding constants once; the ordering holds across the humidity
axis. -/
theorem stronger_binder_stays_ahead {Kc₁ Kc₂ pc Kw pw : ℝ}
    (h1 : 0 ≤ Kc₁ * pc) (h : Kc₁ * pc ≤ Kc₂ * pc) (hw : 0 ≤ Kw * pw) :
    competitiveLoading Kc₁ pc Kw pw ≤ competitiveLoading Kc₂ pc Kw pw := by
  unfold competitiveLoading
  have hden₁ : 0 < 1 + Kc₁ * pc + Kw * pw := by linarith
  have hden₂ : 0 < 1 + Kc₂ * pc + Kw * pw := by linarith
  rw [div_le_div_iff₀ hden₁ hden₂]
  nlinarith [mul_nonneg (sub_nonneg.mpr h) hw]

/-- **Softened hydrolysis screening is conservative.** Softening lowers the
predicted metal–linker dissociation energy, so the predicted hydrolysis rate
`exp(−ΔG/kT)` is an overestimate; any framework whose *model* rate passes the
stability threshold truly passes. The failure mode of raw screening is the
false negative — humidity-stable frameworks discarded — never a fragile
framework promoted. -/
theorem softening_conservative_for_stability {eModel eTrue kT rateMax : ℝ}
    (hkT : 0 < kT) (hsoft : eModel ≤ eTrue)
    (hpass : boltzmann eModel kT ≤ rateMax) :
    boltzmann eTrue kT ≤ rateMax :=
  le_trans (boltzmann_antitone hkT hsoft) hpass

/-! ## The first-shell domain gate -/

/-- The coordination interval on which an environment error field was
measured (anchors inclusive). Outside it, the first-shell approximation is
unverified and the platform must refuse rather than extrapolate silently. -/
structure FieldDomain where
  /-- Lowest anchored coordination number. -/
  cmin : ℕ
  /-- Highest anchored coordination number (the bulk anchor). -/
  cmax : ℕ
  deriving DecidableEq, Repr

/-- Executable gate: admit a configuration exactly when every atom's
coordination lies inside the measured domain. -/
def FieldDomain.admits (D : FieldDomain) (cfg : List ℕ) : Bool :=
  cfg.all fun c => decide (D.cmin ≤ c) && decide (c ≤ D.cmax)

/-- **Gate soundness and completeness.** The executable gate accepts iff every
atom is inside the measured domain — the Boolean the runtime evaluates and
the Prop the theorems consume are the same thing. -/
theorem FieldDomain.admits_iff (D : FieldDomain) (cfg : List ℕ) :
    D.admits cfg = true ↔ ∀ c ∈ cfg, D.cmin ≤ c ∧ c ≤ D.cmax := by
  unfold FieldDomain.admits
  simp [List.all_eq_true]

/-- **Every refusal carries a witness.** If the gate refuses a configuration,
some atom is concretely outside the measured domain — the machine-checked
"domain violation with reported witness" that separates candidates worth
experimental investment from computationally unsupported ones. -/
theorem FieldDomain.refusal_has_witness (D : FieldDomain) (cfg : List ℕ)
    (h : D.admits cfg = false) :
    ∃ c ∈ cfg, c < D.cmin ∨ D.cmax < c := by
  by_contra hno
  push Not at hno
  have : D.admits cfg = true := (D.admits_iff cfg).mpr hno
  rw [this] at h
  exact Bool.noConfusion h

/-- A uniform metal-node signature inside the anchored interval [4, 12] is
admitted (decidable certificate; e.g. an intact 8-coordinate Zr₆-type node). -/
theorem uniform_node_admitted :
    (FieldDomain.mk 4 12).admits [8, 8, 8, 8, 8, 8] = true := by decide

/-- A node carrying a 3-coordinate site — e.g. a defected or mixed-metal
node — is refused: outside the measured first-shell domain, the candidate is
flagged for explicit electronic-structure treatment instead of silent
extrapolation. -/
theorem mixed_metal_node_refused :
    (FieldDomain.mk 4 12).admits [8, 8, 3, 8] = false := by decide

end OpenDistillationFactory.Materials.Theory.SorptionStability
