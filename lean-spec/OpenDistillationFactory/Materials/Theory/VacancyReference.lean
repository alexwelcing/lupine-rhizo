import Mathlib.Analysis.InnerProductSpace.Basic
import Mathlib.Tactic.FieldSimp
import Mathlib.Tactic.Ring
import Mathlib.Tactic.Linarith

/-!
# Vacancy-label loss under species centering

Finite real-valued labels, partitioned into nonempty species groups. Every
site has equal weight; a species is weighted by its number of supplied sites.
The definitions use the same fixed cohort throughout.

This proves the three-part loss identity used by the vacancy-reference
checker and the uniform-bias obstruction to a centered-only accuracy claim.
It does not prove source applicability, the Rust/TypeScript implementation,
floating-point behavior, the reference projector's rank, or physical accuracy.
-/

noncomputable section

namespace OpenDistillationFactory.Materials.Theory.VacancyReference

open scoped BigOperators

/-- Weighted centering identity. The mean equation is the only algebraic premise. -/
theorem weighted_square_decomposition {G : Type*} [Fintype G]
    (w x : G → ℝ) (m : ℝ)
    (hmean : (∑ g, w g * x g) = (∑ g, w g) * m) :
    (∑ g, w g * x g ^ 2) =
      (∑ g, w g * (x g - m) ^ 2) + (∑ g, w g) * m ^ 2 := by
  calc
    (∑ g, w g * x g ^ 2) =
        ∑ g, (w g * (x g - m) ^ 2 + 2 * m * (w g * x g) - m ^ 2 * w g) := by
      apply Finset.sum_congr rfl
      intro g _
      ring
    _ = (∑ g, w g * (x g - m) ^ 2) +
        2 * m * (∑ g, w g * x g) - m ^ 2 * (∑ g, w g) := by
      simp only [Finset.sum_sub_distrib, Finset.sum_add_distrib, ← Finset.mul_sum]
    _ = _ := by rw [hmean]; ring

variable {G : Type*} [Fintype G] [Nonempty G]
variable (I : G → Type*) [∀ g, Fintype (I g)] [∀ g, Nonempty (I g)]

/-- Number of sites in one species group. -/
def groupCount (g : G) : ℝ := Fintype.card (I g)

/-- Number of all supplied sites, including unequal species counts. -/
def totalCount : ℝ := ∑ g, groupCount I g

def speciesMean (x : (g : G) → I g → ℝ) (g : G) : ℝ :=
  (∑ i, x g i) / groupCount I g

def grandMean (x : (g : G) → I g → ℝ) : ℝ :=
  (∑ g, ∑ i, x g i) / totalCount I

def fullMSE (x : (g : G) → I g → ℝ) : ℝ :=
  (∑ g, ∑ i, x g i ^ 2) / totalCount I

def withinMSE (x : (g : G) → I g → ℝ) : ℝ :=
  (∑ g, ∑ i, (x g i - speciesMean I x g) ^ 2) / totalCount I

def imbalanceMSE (x : (g : G) → I g → ℝ) : ℝ :=
  (∑ g, groupCount I g * (speciesMean I x g - grandMean I x) ^ 2) / totalCount I

theorem groupCount_pos (g : G) : 0 < groupCount I g := by
  unfold groupCount
  exact Nat.cast_pos.mpr Fintype.card_pos

theorem totalCount_pos : 0 < totalCount I := by
  unfold totalCount
  exact Finset.sum_pos (fun g _ => groupCount_pos I g) Finset.univ_nonempty

theorem count_mul_speciesMean (x : (g : G) → I g → ℝ) (g : G) :
    groupCount I g * speciesMean I x g = ∑ i, x g i := by
  unfold speciesMean
  field_simp [ne_of_gt (groupCount_pos I g)] <;> ring

theorem count_mul_grandMean (x : (g : G) → I g → ℝ) :
    totalCount I * grandMean I x = ∑ g, ∑ i, x g i := by
  unfold grandMean
  field_simp [ne_of_gt (totalCount_pos I)] <;> ring

/-- The group weights recover the actual overall site mean. -/
theorem weighted_species_means (x : (g : G) → I g → ℝ) :
    (∑ g, groupCount I g * speciesMean I x g) = totalCount I * grandMean I x := by
  simp_rw [count_mul_speciesMean]
  exact (count_mul_grandMean I x).symm

theorem group_square_decomposition (x : (g : G) → I g → ℝ) (g : G) :
    (∑ i, x g i ^ 2) =
      (∑ i, (x g i - speciesMean I x g) ^ 2) + groupCount I g * speciesMean I x g ^ 2 := by
  have hmean : (∑ i : I g, (1 : ℝ) * x g i) =
      (∑ _i : I g, (1 : ℝ)) * speciesMean I x g := by
    simpa [groupCount] using (count_mul_speciesMean I x g).symm
  simpa [groupCount] using
    weighted_square_decomposition (fun _i : I g => (1 : ℝ)) (x g) (speciesMean I x g) hmean

/-- Complete equal-site-weight loss, with no equal-species-size assumption. -/
theorem loss_decomposition (x : (g : G) → I g → ℝ) :
    fullMSE I x = withinMSE I x + grandMean I x ^ 2 + imbalanceMSE I x := by
  have hgroups : (∑ g, ∑ i, x g i ^ 2) =
      (∑ g, ∑ i, (x g i - speciesMean I x g) ^ 2) +
        ∑ g, groupCount I g * speciesMean I x g ^ 2 := by
    calc
      _ = ∑ g, ((∑ i, (x g i - speciesMean I x g) ^ 2) +
          groupCount I g * speciesMean I x g ^ 2) := by
        apply Finset.sum_congr rfl
        intro g _
        exact group_square_decomposition I x g
      _ = _ := Finset.sum_add_distrib
  have hbetween := weighted_square_decomposition
    (groupCount I) (speciesMean I x) (grandMean I x) (weighted_species_means I x)
  unfold fullMSE withinMSE imbalanceMSE
  rw [hgroups, hbetween]
  change
    ((∑ g, ∑ i, (x g i - speciesMean I x g) ^ 2) +
      ((∑ g, groupCount I g * (speciesMean I x g - grandMean I x) ^ 2) +
        totalCount I * grandMean I x ^ 2)) / totalCount I = _
  field_simp [ne_of_gt (totalCount_pos I)] <;> ring

/-- Dropping mean terms can only decrease the reported error. -/
theorem within_le_full (x : (g : G) → I g → ℝ) :
    withinMSE I x ≤ fullMSE I x := by
  have hbetween : 0 ≤ imbalanceMSE I x := by
    unfold imbalanceMSE
    apply div_nonneg
    · exact Finset.sum_nonneg (fun g _ =>
        mul_nonneg (le_of_lt (groupCount_pos I g)) (sq_nonneg _))
    · exact le_of_lt (totalCount_pos I)
  rw [loss_decomposition]
  linarith [sq_nonneg (grandMean I x)]

theorem speciesMean_constant (c : ℝ) (g : G) :
    speciesMean I (fun _ _ => c) g = c := by
  have hsum : (∑ _i : I g, c) = groupCount I g * c := by
    simp [groupCount]
  unfold speciesMean
  rw [hsum]
  field_simp [ne_of_gt (groupCount_pos I g)] <;> ring

theorem grandMean_constant (c : ℝ) :
    grandMean I (fun _ _ => c) = c := by
  have hsum : (∑ g, ∑ _i : I g, c) = totalCount I * c := by
    simp [totalCount, groupCount, Finset.sum_mul]
  unfold grandMean
  rw [hsum]
  field_simp [ne_of_gt (totalCount_pos I)] <;> ring

theorem withinMSE_constant (c : ℝ) :
    withinMSE I (fun _ _ => c) = 0 := by
  simp [withinMSE, speciesMean_constant]

theorem imbalanceMSE_constant (c : ℝ) :
    imbalanceMSE I (fun _ _ => c) = 0 := by
  simp [imbalanceMSE, speciesMean_constant, grandMean_constant]

theorem fullMSE_constant (c : ℝ) :
    fullMSE I (fun _ _ => c) = c ^ 2 := by
  rw [loss_decomposition, withinMSE_constant, grandMean_constant, imbalanceMSE_constant]
  ring

/-- A nonzero uniform formation-label bias defeats every multiplicative bound
    based only on the within-species centered error, for every finite cohort. -/
theorem centered_does_not_bound_full (C c : ℝ) (hc : c ≠ 0) :
    ¬ fullMSE I (fun _ _ => c) ≤ C * withinMSE I (fun _ _ => c) := by
  rw [fullMSE_constant, withinMSE_constant, mul_zero]
  exact not_le_of_gt (sq_pos_of_ne_zero hc)

#print axioms loss_decomposition
#print axioms centered_does_not_bound_full

end OpenDistillationFactory.Materials.Theory.VacancyReference
