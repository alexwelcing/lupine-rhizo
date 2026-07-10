import Mathlib.Data.Real.Basic
import Mathlib.Order.Monotone.Basic
import Mathlib.Tactic.Linarith
import Mathlib.Tactic.NormNum
import OpenDistillationFactory.Materials.Theory.EnvironmentField

/-!
# Ranking integrity: what correction can restore, and what it provably cannot

Screening campaigns act on *orderings* — rank candidates by migration barrier,
by vacancy formation energy, by hydrolysis energy — and send the top of the
list to a furnace. This module proves the three laws that govern whether a
correction layer can be trusted with an ordering:

1. `inversion_defeats_monotone` — **the impossibility law**: when a model's
   ordering of two candidates inverts the reference ordering, *no monotone
   recalibration of the model outputs* can reconcile them. The experimentalist
   receives a machine-checked "cannot be rescued within the method", not an
   uncertainty estimate. (The proof pack's "monotonicity impossibility
   lemma".)
2. `same_signature_corrected_iff` — **the transfer law**: candidates with the
   same coordination signature receive the same field correction, so the
   corrected comparison equals the raw comparison; chemically similar
   compositions are never spuriously re-ranked by the correction itself.
3. `corrected_recovers_reference_order` — **the soundness law**: for
   field-decomposable errors, ranking by corrected values *is* ranking by
   reference values. Post-correction voltage profiles, barrier orderings, and
   stability orderings are the reference orderings.

`cathode_inversion_witness` instantiates the impossibility law with concrete
barrier values in the softening regime, mirroring the LMR-cathode ranking
figure ("raw rankings discard the best candidates").

House rules: zero `sorry`, zero new axioms.
-/

namespace OpenDistillationFactory.Materials.Theory.RankingIntegrity

open EnvironmentField

/-- A recalibration `g` *reconciles* a pair of model values with a pair of
reference values when it maps strict reference order to strict corrected
order, in both directions. -/
def ReconcilesPair (g : ℝ → ℝ) (m₁ m₂ r₁ r₂ : ℝ) : Prop :=
  (r₁ < r₂ → g m₁ < g m₂) ∧ (r₂ < r₁ → g m₂ < g m₁)

/-- **The impossibility law.** If the reference strictly orders candidate 1
below candidate 2 but the model orders them the other way (`m₂ ≤ m₁`), then no
monotone recalibration `g` of the model outputs reconciles the pair. Ranking
inversions cannot be repaired downstream of the model; they must be repaired
*inside* it (by the environment field) or escalated. -/
theorem inversion_defeats_monotone {g : ℝ → ℝ} (hg : Monotone g)
    {m₁ m₂ r₁ r₂ : ℝ} (href : r₁ < r₂) (hinv : m₂ ≤ m₁) :
    ¬ ReconcilesPair g m₁ m₂ r₁ r₂ := by
  rintro ⟨h1, _⟩
  exact absurd (h1 href) (not_lt.mpr (hg hinv))

/-- Monotone recalibration can never *create* an inversion either: correct
model orderings survive any monotone post-processing. Together with
`inversion_defeats_monotone` this pins down monotone recalibration exactly:
it preserves whatever ordering the model already has. -/
theorem monotone_never_inverts {g : ℝ → ℝ} (hg : Monotone g)
    {m₁ m₂ : ℝ} (h : m₁ ≤ m₂) : ¬ (g m₂ < g m₁) :=
  not_lt.mpr (hg h)

/-- **The transfer law.** Two candidates whose configurations share one
coordination multiset receive identical field corrections, so their corrected
comparison is their raw comparison. The correction never re-ranks within an
iso-signature family — "chemically similar compositions receive similar
corrections". -/
theorem same_signature_corrected_iff {cBulk : ℕ} (F : ErrorField cBulk)
    (m₁ m₂ : ℝ) (cfg₁ cfg₂ : Config) (h : cfg₁.Perm cfg₂) :
    (F.corrected m₁ cfg₁ ≤ F.corrected m₂ cfg₂ ↔ m₁ ≤ m₂) := by
  unfold ErrorField.corrected
  rw [F.fieldSum_transfer cfg₁ cfg₂ h]
  constructor <;> intro h' <;> linarith

/-- **The soundness law.** For field-decomposable model errors, the corrected
ordering of two candidates is exactly their reference ordering: screening on
corrected values is screening on reference values. This is the theorem behind
"formal verification then checks that predicted voltage profiles remain
ordered after correction". -/
theorem corrected_recovers_reference_order {cBulk : ℕ} (F : ErrorField cBulk)
    (m₁ m₂ r₁ r₂ : ℝ) (cfg₁ cfg₂ : Config)
    (h₁ : m₁ = r₁ + F.fieldSum cfg₁) (h₂ : m₂ = r₂ + F.fieldSum cfg₂) :
    (F.corrected m₁ cfg₁ ≤ F.corrected m₂ cfg₂ ↔ r₁ ≤ r₂) := by
  rw [F.corrected_exact m₁ r₁ cfg₁ h₁, F.corrected_exact m₂ r₂ cfg₂ h₂]

/-- Strict version of the soundness law: strict reference order is recovered
strictly. The best candidate stays strictly first after correction. -/
theorem corrected_recovers_strict_order {cBulk : ℕ} (F : ErrorField cBulk)
    (m₁ m₂ r₁ r₂ : ℝ) (cfg₁ cfg₂ : Config)
    (h₁ : m₁ = r₁ + F.fieldSum cfg₁) (h₂ : m₂ = r₂ + F.fieldSum cfg₂) :
    (F.corrected m₁ cfg₁ < F.corrected m₂ cfg₂ ↔ r₁ < r₂) := by
  rw [F.corrected_exact m₁ r₁ cfg₁ h₁, F.corrected_exact m₂ r₂ cfg₂ h₂]

/-! ### The measured tier

Ranking soundness does not need the softening shape: the transfer and
recovery laws hold for any `MeasuredField` — every bound sweep cell,
including the non-monotone and stiffening ones the directional layer
refuses. -/

/-- The transfer law at the measured tier: iso-signature candidates keep
their raw comparison under any measured field's correction. -/
theorem measured_same_signature_corrected_iff {cBulk : ℕ}
    (F : MeasuredField cBulk) (m₁ m₂ : ℝ) (cfg₁ cfg₂ : Config)
    (h : cfg₁.Perm cfg₂) :
    (F.corrected m₁ cfg₁ ≤ F.corrected m₂ cfg₂ ↔ m₁ ≤ m₂) := by
  unfold MeasuredField.corrected
  rw [F.fieldSum_transfer cfg₁ cfg₂ h]
  constructor <;> intro h' <;> linarith

/-- The soundness law at the measured tier: for field-decomposable errors,
corrected ordering is reference ordering — with no shape assumption. -/
theorem measured_corrected_recovers_reference_order {cBulk : ℕ}
    (F : MeasuredField cBulk) (m₁ m₂ r₁ r₂ : ℝ) (cfg₁ cfg₂ : Config)
    (h₁ : m₁ = r₁ + F.fieldSum cfg₁) (h₂ : m₂ = r₂ + F.fieldSum cfg₂) :
    (F.corrected m₁ cfg₁ ≤ F.corrected m₂ cfg₂ ↔ r₁ ≤ r₂) := by
  rw [F.corrected_exact m₁ r₁ cfg₁ h₁, F.corrected_exact m₂ r₂ cfg₂ h₂]

/-- Strict measured-tier soundness. -/
theorem measured_corrected_recovers_strict_order {cBulk : ℕ}
    (F : MeasuredField cBulk) (m₁ m₂ r₁ r₂ : ℝ) (cfg₁ cfg₂ : Config)
    (h₁ : m₁ = r₁ + F.fieldSum cfg₁) (h₂ : m₂ = r₂ + F.fieldSum cfg₂) :
    (F.corrected m₁ cfg₁ < F.corrected m₂ cfg₂ ↔ r₁ < r₂) := by
  rw [F.corrected_exact m₁ r₁ cfg₁ h₁, F.corrected_exact m₂ r₂ cfg₂ h₂]

/-- **Concrete inversion witness (LMR-cathode regime).** Reference migration
barriers 0.30 eV < 0.45 eV rank candidate A ahead of candidate B for
voltage-fade resistance, but a softened model reporting 0.28 eV and 0.25 eV
ranks B ahead of A. By the impossibility law, no monotone recalibration of
those model outputs restores the reference ranking — the pair carries a
machine-checked escalation certificate. -/
theorem cathode_inversion_witness :
    ∃ rA rB mA mB : ℝ, rA < rB ∧ mB ≤ mA ∧
      ∀ g : ℝ → ℝ, Monotone g → ¬ ReconcilesPair g mA mB rA rB := by
  refine ⟨0.30, 0.45, 0.28, 0.25, by norm_num, by norm_num, ?_⟩
  intro g hg
  exact inversion_defeats_monotone hg (by norm_num) (by norm_num)

end OpenDistillationFactory.Materials.Theory.RankingIntegrity
