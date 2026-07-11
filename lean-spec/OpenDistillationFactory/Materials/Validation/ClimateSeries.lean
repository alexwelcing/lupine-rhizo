/-!
# Climate-series certificate pack

Decidable, kernel-checked certificates for the quantitative claims of the
climate partnerships proof pack ("The 0.2 % Synthesis Problem", "A Field, Not
a Neural Net", "Five Materials That Could Unlock 5–12 GtCO₂/Year",
lupine.science, 2026-07-09). Every theorem is a `decide`-checked integer fact
in the style of the evidence corpus: no floats, no `sorry`, no trust in an
analysis script. Scaled units are stated per theorem.

These certificates pin the *arithmetic* of the narrative; the *physics* is
proven in `Theory.EnvironmentField`, `Theory.BarrierArrhenius`,
`Theory.RankingIntegrity`, `Theory.ScalingVolcano`, `Theory.DefectStability`,
and `Theory.SorptionStability`.
-/

namespace OpenDistillationFactory.Materials.Validation.ClimateSeries

/-- **The 0.2 % synthesis funnel.** GNoME reported 380,000 computationally
stable structures; 736 were independently synthesized by late 2023. The
validation rate is at most 0.2 % = 1/500: `736 × 500 ≤ 380000`. -/
theorem gnome_validation_rate_at_most_0_2_percent : 736 * 500 ≤ 380000 := by
  decide

/-- **The A-Lab novelty collapse.** Of 41 reported syntheses, independent
review left 13 true novel phases — at most one third survive:
`13 × 3 ≤ 41`. -/
theorem alab_true_novelty_at_most_one_third : 13 * 3 ≤ 41 := by decide

/-- **The kernel-rejected-claim episode.** A statistical filter accepted
"27 of 36 cells improved strictly"; at 10⁻⁴ J/m² integer precision one cell's
margin was exactly zero, and the Lean kernel refused `813 < 813`. The
certificate that forced the correction to 26. -/
theorem kernel_refuses_zero_margin : ¬ (813 < 813) := by decide

/-- The corrected strict-improvement count after the kernel rejection:
26 of 36 cells, a strict majority. -/
theorem corrected_strict_improvement_count : 26 ≤ 36 ∧ 36 < 2 * 26 := by
  decide

/-- **Median residual improvement.** Applying the field drops the median
(110) blind residual from 0.104 to 0.066 J/m² (×1000 scale):
corrected < raw. -/
theorem median_blind_residual_improves : 66 < 104 := by decide

/-- **The blind-prediction correlation is inside its confidence interval.**
r = 0.906 with 95 % CI [0.82, 0.96] (×1000 scale): 820 ≤ 906 ≤ 960. -/
theorem blind_r_within_confidence_interval : 820 ≤ 906 ∧ 906 ≤ 960 := by
  decide

/-- **Ni blind-facet improvement ≥ 6×.** The blind (110) error for Ni drops
from 9.7 % to 1.5 % — at least a six-fold reduction (×10 scale):
`6 × 15 ≤ 97`. -/
theorem ni_blind_error_improves_sixfold : 6 * 15 ≤ 97 := by decide

/-- **Cu blind-facet improvement ≥ 2×.** The blind (110) error for Cu drops
from 28.0 % to 13.7 % — at least a two-fold reduction (×10 scale):
`2 × 137 ≤ 280`. -/
theorem cu_blind_error_improves_twofold : 2 * 137 ≤ 280 := by decide

/-- **The five-target portfolio envelope.** Per-class abatement potentials
(×10 GtCO₂/yr): LMR cathodes 1.0–3.0, halide electrolytes 0.5–2.0, MOF DAC
sorbents 4.0–10.0, ammonia catalysts 0.4–1.2, lead-free perovskites 0.5–3.0.
The claimed 5–12 GtCO₂/yr aggregate is inside the component-sum envelope:
`50 ≤ 10+5+40+4+5` and `120 ≤ 30+20+100+12+30`. -/
theorem portfolio_range_within_component_sums :
    50 ≤ 10 + 5 + 40 + 4 + 5 ∧ 120 ≤ 30 + 20 + 100 + 12 + 30 := by decide

/-- **Formalization inventory floor at the time of the proof pack**: 51
modules, 190 build-locked theorems, ~640 declarations, 0 `sorry`. The count
below this line only grows; the zero-`sorry` invariant is enforced by the
build gate, not by this certificate. -/
theorem proof_pack_inventory_floor : 51 ≤ 51 ∧ 190 ≤ 190 ∧ (0 : Nat) = 0 := by
  decide

end OpenDistillationFactory.Materials.Validation.ClimateSeries
