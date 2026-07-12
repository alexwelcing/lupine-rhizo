import OpenDistillationFactory.Materials.Theory.ClimateForcers

/-! # Climate-forcer certificates (non-CO₂ expansion)

Kernel-checked quantitative certificates for the non-CO₂ environmental
concerns raised in the expansion series: methane, refrigerants, and nitrous
oxide. Each theorem is either `decide`-checked integer arithmetic or a short
`norm_num` calculation over the rational-scaled definitions in
`Theory.ClimateForcers`.

Sources (stated in comments, not axioms):
- IPCC AR6 WGI Table 7.15 for 100-year and 20-year GWPs.
- NOAA/AGAGE lifetimes for HFCs and SF₆.
- IEA Global Energy Review / EPA for refrigerant-bank leakage rates.

House rules: zero `sorry`, zero new axioms.
-/

namespace OpenDistillationFactory.Materials.Validation.ClimateForcers

open OpenDistillationFactory.Materials.Theory.ClimateForcers
open OpenDistillationFactory.Materials.Theory.ClimateForcers.ClimateForcer

/-- **Methane dominates near-term warming.** On the 20-year horizon, 1 kg of CH₄
is at least 80× the CO₂e of 1 kg of CO₂. -/
theorem methane_20yr_potency :
    80 ≤ co2e20 1 .methane := by
  simp [co2e20, ClimateForcer.gwp20]
  norm_num

/-- **Refrigerant leaks are massive on a mass basis.** The average residential
heat-pump charge is ~2 kg; a full leak of HFC-410A is >4 t CO₂e, comparable to
the annual operating emissions of a fossil furnace. -/
theorem heat_pump_full_leak_co2e :
    4000 < co2e 2 .hfc410a := by
  simp [co2e, ClimateForcer.gwp100]
  norm_num

/-- **Low-GWP replacement is high leverage.** Replacing the standard 2 kg
HFC-410A charge with a CO₂-based working fluid saves more than 4 tonnes of
CO₂e per unit. -/
theorem low_gwp_replacement_savings :
    co2e 2 .hfc410a - co2e 2 .co2 > 4000 := by
  simp [co2e, ClimateForcer.gwp100]
  norm_num

/-- **SF₆ switchgear leak.** A single 1 kg SF₆ leak from medium-voltage
electrical gear exceeds the lifetime embodied emissions of many material lots.
Certificate: >25 t CO₂e. -/
theorem sf6_switchgear_leak :
    25000 < co2e 1 .sf6 := by
  simp [co2e, ClimateForcer.gwp100]
  norm_num

/-- **Agricultural nitrous oxide is not negligible.** 1 kg N₂O is ~273 kg CO₂e,
so a modest 10 kg N₂O process stream is >2.5 t CO₂e. -/
theorem nitrous_oxide_process_stream :
    2500 < co2e 10 .nitrousOxide := by
  simp [co2e, ClimateForcer.gwp100]
  norm_num

/-- **Total footprint of a representative mixed stream** (1 kg CH₄, 1 kg N₂O,
1 kg HFC-410A) exceeds 2 tonnes CO₂e. This is the kind of boundary condition
a materials platform must get right for chemical-process climate claims. -/
theorem mixed_stream_exceeds_2tonne :
    2000 < totalCo2e [(1, .methane), (1, .nitrousOxide), (1, .hfc410a)] := by
  simp [totalCo2e, co2e, ClimateForcer.gwp100]
  norm_num

/-- The methane 20-year CO₂e is strictly larger than its 100-year CO₂e. This
justifies separate near-term and long-term reporting buckets. -/
theorem methane_near_term_stronger_than_long_term :
    co2e 1 .methane < co2e20 1 .methane := by
  simp [co2e, co2e20, ClimateForcer.gwp100, ClimateForcer.gwp20]
  norm_num

/-- HFC-410A's 20-year CO₂e is larger than its 100-year CO₂e. -/
theorem hfc410a_near_term_stronger_than_long_term :
    co2e 1 .hfc410a < co2e20 1 .hfc410a := by
  simp [co2e, co2e20, ClimateForcer.gwp100, ClimateForcer.gwp20]
  norm_num

/-- Non-CO₂ forcers in this module are all more potent than CO₂ on the 100-year
horizon. -/
theorem all_expansion_forcers_exceed_co2 :
    gwp100 .methane > gwp100 .co2 ∧
    gwp100 .nitrousOxide > gwp100 .co2 ∧
    gwp100 .hfc134a > gwp100 .co2 ∧
    gwp100 .hfc410a > gwp100 .co2 ∧
    gwp100 .sf6 > gwp100 .co2 := by decide

end OpenDistillationFactory.Materials.Validation.ClimateForcers
