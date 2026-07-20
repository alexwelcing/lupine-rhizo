import Mathlib.Data.Finset.BooleanAlgebra
import Mathlib.Data.Finset.Lattice.Fold
import Mathlib.Data.Fin.VecNotation
import Mathlib.Data.Fintype.EquivFin
import Mathlib.Data.Real.Basic
import Mathlib.Tactic.FinCases
import Mathlib.Tactic.Linarith
import Mathlib.Tactic.NormNum
import Mathlib.Tactic.Ring

/-!
# Correction boundary theorems — EXPLORATORY / IDEATION LAYER

**Status (2026-07-20):** exploratory / ideation. This module maps the
correction boundary for runtime path-profile correction; it is NOT a frozen
gate. No consumer may treat any theorem here as a preregistered acceptance
gate. The module is deliberately excluded from the frozen theorem counts
(`Materials/Vision.lean`'s `honestErrorsProvenCount` tracks the frozen
Honest Errors contract layer) and from the empirical correction-surface
inventory in `UniversalCorrection/Empirical/Registry.lean`, which is scoped
to the 17-module `Materials.Theory` correction theory surface.

**Motivation (measured):** along-path profile wobble of foundation MLIPs on
the Z1 panel is ~100–130 meV RMS; every low-dimensional correction gate
abstains correctly; even a perfect model-routing oracle only reaches 70 meV.
The theorems below make the correction boundary precise instead of folklore:

1. `barrier_shift_invariant` — global additive shifts cannot move any barrier.
2. `barrier_error_le_wobble` — a model's barrier error never exceeds its
   profile wobble, and the bound is tight (`barrier_error_le_wobble_tight`).
3. T-slope stability — a single-ratio slope correction is certified by the
   slope residuals (`slope_correction_error_le`), the midrange ratio halves
   the residual factor (`slope_correction_error_le_midrange`), and one-signed
   ratios make the corrected certificate beat the raw one
   (`slope_correction_stable_of_one_sign`); mixed-sign ratios admit an
   abstention witness where no ratio helps at all
   (`slope_instability_witness`).
4. `anchor_impossibility_bound` — a single-anchor correction buys at most the
   deviation it removes, while two anchors (saddle + endpoint) reconstruct
   the reference barrier exactly (`two_point_anchor_exact`).

**Design adjustment (documented, not hidden):** the design sketch's "precise"
anchor lower bound `residual ≥ wobble d − |d k|` is FALSE as stated —
`anchor_wobble_lower_bound_refuted` exhibits a deviation of wobble 100 whose
anchored residual barrier error is 0 (a barrier-preserving rotation of the
profile). The proved form lower-bounds the residual by the RAW barrier error
minus the anchored deviation, which is the content of "anchoring removes at
most the deviation at `k`".
-/

namespace OpenDistillationFactory.HonestErrors.CorrectionBoundary

variable {n : ℕ} [Nonempty (Fin n)]

/-- Energy profile along a reaction path (model or reference), sampled at
`n` path points. -/
abbrev Profile (n : ℕ) := Fin n → ℝ

/-- Sampled maximum of a profile. -/
noncomputable def profileMax (p : Profile n) : ℝ :=
  Finset.univ.sup' Finset.univ_nonempty p

/-- Sampled minimum of a profile. -/
noncomputable def profileMin (p : Profile n) : ℝ :=
  Finset.univ.inf' Finset.univ_nonempty p

/-- Path barrier: sampled max minus sampled min, matching the frozen campaign
convention. -/
noncomputable def barrier (p : Profile n) : ℝ :=
  profileMax p - profileMin p

/-- Pointwise deviation of a model profile against its reference. -/
def deviation (m r : Profile n) : Profile n :=
  fun i => m i - r i

/-- Along-path profile wobble: the barrier of the deviation profile. -/
noncomputable def wobble (d : Profile n) : ℝ :=
  barrier d

/-! ## 1. The shift family is dead -/

theorem profileMax_add_const (p : Profile n) (c : ℝ) :
    profileMax (fun i => p i + c) = profileMax p + c := by
  apply le_antisymm
  · simp only [profileMax, Finset.sup'_le_iff]
    intro i _
    exact (add_le_add_iff_right c).mpr (Finset.le_sup' (f := p) (Finset.mem_univ i))
  · obtain ⟨j, -, hj⟩ := Finset.exists_mem_eq_sup' Finset.univ_nonempty p
    simp only [profileMax]
    rw [hj]
    exact Finset.le_sup' (f := fun i => p i + c) (Finset.mem_univ j)

theorem profileMin_add_const (p : Profile n) (c : ℝ) :
    profileMin (fun i => p i + c) = profileMin p + c := by
  apply le_antisymm
  · obtain ⟨j, -, hj⟩ := Finset.exists_mem_eq_inf' Finset.univ_nonempty p
    simp only [profileMin]
    rw [hj]
    exact Finset.inf'_le (f := fun i => p i + c) (Finset.mem_univ j)
  · simp only [profileMin]
    apply Finset.le_inf'
    intro i _
    exact (add_le_add_iff_right c).mpr (Finset.inf'_le (f := p) (Finset.mem_univ i))

/-- **Theorem 1 (shift invariance).** A global additive shift cannot change
any barrier: the sampled max and min absorb the same constant. This is why
the shift correction family was dead on arrival — now a theorem, not a mood. -/
theorem barrier_shift_invariant (p : Profile n) (c : ℝ) :
    barrier (fun i => p i + c) = barrier p := by
  simp only [barrier]
  rw [profileMax_add_const, profileMin_add_const]
  ring

/-! ## 2. Barrier error is bounded by wobble, and the bound is tight -/

/-- One direction of the wobble bound: the barrier difference is dominated by
the deviation's own extrema. -/
theorem barrier_sub_le_wobble (m r : Profile n) :
    barrier m - barrier r ≤ wobble (deviation m r) := by
  have hpt : ∀ i, m i = r i + deviation m r i := by
    intro i; show m i = r i + (m i - r i); ring
  have hsup : profileMax m ≤ profileMax r + profileMax (deviation m r) := by
    simp only [profileMax, Finset.sup'_le_iff]
    intro i _
    have h1 := Finset.le_sup' (f := r) (Finset.mem_univ i)
    have h2 := Finset.le_sup' (f := deviation m r) (Finset.mem_univ i)
    linarith [hpt i]
  have hinf : profileMin r + profileMin (deviation m r) ≤ profileMin m := by
    simp only [profileMin]
    apply Finset.le_inf'
    intro i _
    have h1 := Finset.inf'_le (f := r) (Finset.mem_univ i)
    have h2 := Finset.inf'_le (f := deviation m r) (Finset.mem_univ i)
    linarith [hpt i]
  simp only [barrier, wobble]
  linarith

theorem profileMax_neg (d : Profile n) :
    profileMax (fun i => -d i) = -profileMin d := by
  apply le_antisymm
  · rw [profileMax, Finset.sup'_le_iff]
    intro i _
    exact neg_le_neg (Finset.inf'_le (f := d) (Finset.mem_univ i))
  · obtain ⟨j, -, hj⟩ := Finset.exists_mem_eq_inf' Finset.univ_nonempty d
    rw [profileMin, hj]
    exact Finset.le_sup' (f := fun i => -d i) (Finset.mem_univ j)

theorem profileMin_neg (d : Profile n) :
    profileMin (fun i => -d i) = -profileMax d := by
  apply le_antisymm
  · obtain ⟨j, -, hj⟩ := Finset.exists_mem_eq_sup' Finset.univ_nonempty d
    rw [profileMax, hj]
    exact Finset.inf'_le (f := fun i => -d i) (Finset.mem_univ j)
  · rw [profileMin]
    apply Finset.le_inf'
    intro i _
    exact neg_le_neg (Finset.le_sup' (f := d) (Finset.mem_univ i))

theorem wobble_neg (d : Profile n) : wobble (fun i => -d i) = wobble d := by
  simp only [wobble, barrier]
  rw [profileMax_neg, profileMin_neg]
  ring

/-- **Theorem 2 (the measurable upper bound).** A model's barrier error never
exceeds its along-path profile wobble. -/
theorem barrier_error_le_wobble (m r : Profile n) :
    |barrier m - barrier r| ≤ wobble (deviation m r) := by
  rw [abs_le]
  constructor
  · have h := barrier_sub_le_wobble r m
    have hdev : deviation r m = fun i => -deviation m r i := by
      funext i; simp only [deviation]; ring
    rw [hdev, wobble_neg] at h
    linarith
  · exact barrier_sub_le_wobble m r

/-! ## Concrete computation on two- and three-point profiles -/

@[simp] theorem profileMax_pair (a b : ℝ) :
    profileMax (![a, b] : Profile 2) = max a b := by
  apply le_antisymm
  · rw [profileMax, Finset.sup'_le_iff]
    intro i _
    fin_cases i
    · exact le_max_left a b
    · exact le_max_right a b
  · apply max_le
    · exact Finset.le_sup' (f := ![a, b]) (Finset.mem_univ (0 : Fin 2))
    · exact Finset.le_sup' (f := ![a, b]) (Finset.mem_univ (1 : Fin 2))

@[simp] theorem profileMin_pair (a b : ℝ) :
    profileMin (![a, b] : Profile 2) = min a b := by
  apply le_antisymm
  · rcases le_total a b with h | h
    · rw [min_eq_left h]
      exact Finset.inf'_le (f := ![a, b]) (Finset.mem_univ 0)
    · rw [min_eq_right h]
      exact Finset.inf'_le (f := ![a, b]) (Finset.mem_univ 1)
  · rw [profileMin]
    apply Finset.le_inf'
    intro i _
    fin_cases i
    · exact min_le_left a b
    · exact min_le_right a b

theorem barrier_pair (a b : ℝ) :
    barrier (![a, b] : Profile 2) = max a b - min a b := by
  rw [barrier, profileMax_pair, profileMin_pair]

@[simp] theorem profileMax_triple (a b c : ℝ) :
    profileMax (![a, b, c] : Profile 3) = max (max a b) c := by
  apply le_antisymm
  · rw [profileMax, Finset.sup'_le_iff]
    intro i _
    fin_cases i
    · exact le_max_of_le_left (le_max_left a b)
    · exact le_max_of_le_left (le_max_right a b)
    · exact le_max_right (max a b) c
  · apply max_le
    · apply max_le
      · exact Finset.le_sup' (f := ![a, b, c]) (Finset.mem_univ (0 : Fin 3))
      · exact Finset.le_sup' (f := ![a, b, c]) (Finset.mem_univ (1 : Fin 3))
    · exact Finset.le_sup' (f := ![a, b, c]) (Finset.mem_univ (2 : Fin 3))

@[simp] theorem profileMin_triple (a b c : ℝ) :
    profileMin (![a, b, c] : Profile 3) = min (min a b) c := by
  apply le_antisymm
  · rcases le_total (min a b) c with h | h
    · rw [min_eq_left h]
      rcases le_total a b with hab | hab
      · rw [min_eq_left hab]
        exact Finset.inf'_le (f := ![a, b, c]) (Finset.mem_univ 0)
      · rw [min_eq_right hab]
        exact Finset.inf'_le (f := ![a, b, c]) (Finset.mem_univ 1)
    · rw [min_eq_right h]
      exact Finset.inf'_le (f := ![a, b, c]) (Finset.mem_univ 2)
  · rw [profileMin]
    apply Finset.le_inf'
    intro i _
    fin_cases i
    · exact min_le_of_left_le (min_le_left a b)
    · exact min_le_of_left_le (min_le_right a b)
    · exact min_le_right (min a b) c

theorem barrier_triple (a b c : ℝ) :
    barrier (![a, b, c] : Profile 3) = max (max a b) c - min (min a b) c := by
  rw [barrier, profileMax_triple, profileMin_triple]

/-- **Tightness witness for Theorem 2.** The model `m = (1, 0)` overshoots
the saddle of the flat reference `r = (0, 0)` and nails the minimum: its
barrier error equals its full profile wobble, so no information-free
correction can beat the wobble bound. -/
theorem barrier_error_le_wobble_tight :
    |barrier (![1, 0] : Profile 2) - barrier (![0, 0] : Profile 2)| =
      wobble (deviation (![1, 0] : Profile 2) (![0, 0] : Profile 2)) := by
  have hb1 : barrier (![1, 0] : Profile 2) = 1 := by
    rw [barrier_pair, max_eq_left (by norm_num : (0:ℝ) ≤ 1),
      min_eq_right (by norm_num : (0:ℝ) ≤ 1)]
    norm_num
  have hb0 : barrier (![0, 0] : Profile 2) = 0 := by
    rw [barrier_pair, max_eq_left (le_refl (0:ℝ)), min_eq_left (le_refl (0:ℝ))]
    norm_num
  have hdev : deviation (![1, 0] : Profile 2) (![0, 0] : Profile 2) =
      (![1, 0] : Profile 2) := by
    funext i; fin_cases i <;> simp [deviation]
  rw [hdev, wobble, hb1, hb0]
  norm_num

/-! ## 3. T-slope stability -/

/-- A single-ratio slope correction: rescale the deviation direction by the
ratio `σ` along the reference profile. -/
def slopeCorrected (m r : Profile n) (σ : ℝ) : Profile n :=
  fun i => m i - σ * r i

/-- Per-point slope ratios `(m i − r i) / r i`; meaningful where `r i ≠ 0`.
Proofs take the representation hypothesis `m i − r i = s i * r i` instead,
which is exactly this ratio when the reference never vanishes. -/
noncomputable def slopeRatio (m r : Profile n) : Profile n :=
  fun i => (m i - r i) / r i

/-- Reference scale: the largest sampled magnitude of the reference profile. -/
noncomputable def refScale (r : Profile n) : ℝ :=
  Finset.univ.sup' Finset.univ_nonempty fun i => |r i|

/-- Midrange of a profile: the midpoint of its sampled extremes. -/
noncomputable def midrange (s : Profile n) : ℝ :=
  (profileMax s + profileMin s) / 2

theorem refScale_nonneg (r : Profile n) : 0 ≤ refScale r := by
  obtain ⟨j, -, hj⟩ :=
    Finset.exists_mem_eq_sup' Finset.univ_nonempty fun i => |r i|
  rw [refScale, hj]
  exact abs_nonneg _

/-- **Theorem 3a (slope-residual bound).** For any single ratio `σ`, the
corrected barrier error is bounded by twice the largest slope residual
`s i − σ` times the reference scale. No sign hypothesis is needed for the
bound itself; the sign decides whether the bound beats the raw certificate. -/
theorem slope_correction_error_le (m r s : Profile n) (σ : ℝ)
    (hrep : ∀ i, m i - r i = s i * r i) :
    |barrier (slopeCorrected m r σ) - barrier r| ≤
      2 * (Finset.univ.sup' Finset.univ_nonempty fun i => |s i - σ|) *
        refScale r := by
  have hM : 0 ≤ Finset.univ.sup' Finset.univ_nonempty fun i => |s i - σ| := by
    obtain ⟨j, -, hj⟩ :=
      Finset.exists_mem_eq_sup' Finset.univ_nonempty fun i => |s i - σ|
    rw [hj]
    exact abs_nonneg _
  have hR : 0 ≤ refScale r := refScale_nonneg r
  have hdev : ∀ i, deviation (slopeCorrected m r σ) r i = (s i - σ) * r i := by
    intro i
    show m i - σ * r i - r i = (s i - σ) * r i
    calc m i - σ * r i - r i = (m i - r i) - σ * r i := by ring
      _ = (s i - σ) * r i := by rw [hrep i]; ring
  have hbound : ∀ i, |(s i - σ) * r i| ≤
      (Finset.univ.sup' Finset.univ_nonempty fun i => |s i - σ|) *
        refScale r := by
    intro i
    rw [abs_mul]
    exact mul_le_mul
      (Finset.le_sup' (f := fun i => |s i - σ|) (Finset.mem_univ i))
      (Finset.le_sup' (f := fun i => |r i|) (Finset.mem_univ i))
      (abs_nonneg _) hM
  apply le_trans (barrier_error_le_wobble (slopeCorrected m r σ) r)
  have hsup : profileMax (deviation (slopeCorrected m r σ) r) ≤
      (Finset.univ.sup' Finset.univ_nonempty fun i => |s i - σ|) *
        refScale r := by
    rw [profileMax, Finset.sup'_le_iff]
    intro i _
    calc deviation (slopeCorrected m r σ) r i = (s i - σ) * r i := hdev i
      _ ≤ |(s i - σ) * r i| := le_abs_self _
      _ ≤ _ := hbound i
  have hinf : -((Finset.univ.sup' Finset.univ_nonempty fun i => |s i - σ|) *
        refScale r) ≤ profileMin (deviation (slopeCorrected m r σ) r) := by
    rw [profileMin]
    apply Finset.le_inf'
    intro i _
    calc -((Finset.univ.sup' Finset.univ_nonempty fun i => |s i - σ|) *
          refScale r) ≤ -|(s i - σ) * r i| := neg_le_neg (hbound i)
      _ ≤ (s i - σ) * r i := neg_abs_le _
      _ = deviation (slopeCorrected m r σ) r i := (hdev i).symm
  rw [wobble, barrier]
  linarith

theorem abs_sub_midrange_le (s : Profile n) (i : Fin n) :
    |s i - midrange s| ≤ (profileMax s - profileMin s) / 2 := by
  have hlo : profileMin s ≤ s i := Finset.inf'_le (f := s) (Finset.mem_univ i)
  have hhi : s i ≤ profileMax s := Finset.le_sup' (f := s) (Finset.mem_univ i)
  rw [abs_le]
  constructor <;> rw [midrange] <;> linarith

/-- **Theorem 3b (midrange certificate).** Scaling by the midrange ratio
halves the residual factor: the corrected barrier error is bounded by the
slope spread times the reference scale. -/
theorem slope_correction_error_le_midrange (m r s : Profile n)
    (hrep : ∀ i, m i - r i = s i * r i) :
    |barrier (slopeCorrected m r (midrange s)) - barrier r| ≤
      (profileMax s - profileMin s) * refScale r := by
  have hR : 0 ≤ refScale r := refScale_nonneg r
  have hbound := slope_correction_error_le m r s (midrange s) hrep
  have hspread : Finset.univ.sup' Finset.univ_nonempty
        (fun i => |s i - midrange s|) ≤ (profileMax s - profileMin s) / 2 := by
    rw [Finset.sup'_le_iff]
    intro i _
    exact abs_sub_midrange_le s i
  have h2 := mul_le_mul_of_nonneg_right
    (mul_le_mul_of_nonneg_left hspread (by norm_num : (0:ℝ) ≤ 2)) hR
  linarith

theorem slopeSpread_le_maxAbs_of_nonneg (s : Profile n) (hs : ∀ i, 0 ≤ s i) :
    profileMax s - profileMin s ≤
      Finset.univ.sup' Finset.univ_nonempty fun i => |s i| := by
  have hmin : 0 ≤ profileMin s := by
    rw [profileMin]
    apply Finset.le_inf'
    intro i _
    exact hs i
  have hmax : profileMax s ≤
      Finset.univ.sup' Finset.univ_nonempty fun i => |s i| := by
    rw [profileMax, Finset.sup'_le_iff]
    intro i _
    rw [← abs_of_nonneg (hs i)]
    exact Finset.le_sup' (f := fun i => |s i|) (Finset.mem_univ i)
  linarith

theorem slopeSpread_le_maxAbs_of_nonpos (s : Profile n) (hs : ∀ i, s i ≤ 0) :
    profileMax s - profileMin s ≤
      Finset.univ.sup' Finset.univ_nonempty fun i => |s i| := by
  have hmax : profileMax s ≤ 0 := by
    rw [profileMax, Finset.sup'_le_iff]
    intro i _
    exact hs i
  have hnegmin : -profileMin s ≤
      Finset.univ.sup' Finset.univ_nonempty fun i => |s i| := by
    obtain ⟨j, -, hj⟩ := Finset.exists_mem_eq_inf' Finset.univ_nonempty s
    rw [profileMin, hj, ← abs_of_nonpos (hs j)]
    exact Finset.le_sup' (f := fun i => |s i|) (Finset.mem_univ j)
  linarith

/-- **Theorem 3c (T-slope stability).** When every slope ratio shares one
sign, the midrange-corrected barrier error is bounded by the largest slope
magnitude times the reference scale — at least a factor two tighter than the
raw certificate of `barrier_error_le_raw_slope_certificate`. -/
theorem slope_correction_stable_of_one_sign (m r s : Profile n)
    (hrep : ∀ i, m i - r i = s i * r i)
    (hs : (∀ i, 0 ≤ s i) ∨ (∀ i, s i ≤ 0)) :
    |barrier (slopeCorrected m r (midrange s)) - barrier r| ≤
      (Finset.univ.sup' Finset.univ_nonempty fun i => |s i|) * refScale r := by
  have h := slope_correction_error_le_midrange m r s hrep
  have hR : 0 ≤ refScale r := refScale_nonneg r
  have hspread := hs.elim
    (slopeSpread_le_maxAbs_of_nonneg s) (slopeSpread_le_maxAbs_of_nonpos s)
  have h2 := mul_le_mul_of_nonneg_right hspread hR
  linarith

/-- The raw (uncorrected) slope certificate: the `σ = 0` case of Theorem 3a.
Under one-signed ratios the midrange certificate of Theorem 3c is at least
twice as tight. -/
theorem barrier_error_le_raw_slope_certificate (m r s : Profile n)
    (hrep : ∀ i, m i - r i = s i * r i) :
    |barrier m - barrier r| ≤
      2 * (Finset.univ.sup' Finset.univ_nonempty fun i => |s i|) *
        refScale r := by
  have h := slope_correction_error_le m r s 0 hrep
  have hm : slopeCorrected m r 0 = m := by
    funext i; simp [slopeCorrected]
  rw [hm] at h
  simpa using h

/-- **Theorem 3d (slope instability witness — the abstention certificate).**
On the flat reference `r = (1, 1)` the model `m = (2, 0)` overshoots one
endpoint and undershoots the other: slope ratios `+1` and `−1`, signs differ.
Every single-ratio correction then degenerates to a pure shift, so by Theorem
1 it cannot move the barrier error at all — no ratio strictly improves on the
raw profile, and a slope gate must abstain. -/
theorem slope_instability_witness :
    slopeRatio (![2, 0] : Profile 2) (![1, 1] : Profile 2) 0 *
        slopeRatio (![2, 0] : Profile 2) (![1, 1] : Profile 2) 1 < 0 ∧
      ∀ σ : ℝ,
        |barrier (slopeCorrected (![2, 0] : Profile 2) (![1, 1] : Profile 2) σ) -
            barrier (![1, 1] : Profile 2)| =
          |barrier (![2, 0] : Profile 2) - barrier (![1, 1] : Profile 2)| := by
  constructor
  · norm_num [slopeRatio]
  · intro σ
    have hshift :
        slopeCorrected (![2, 0] : Profile 2) (![1, 1] : Profile 2) σ =
          fun i => (![2, 0] : Profile 2) i + (-σ) := by
      funext i
      fin_cases i <;> simp [slopeCorrected, sub_eq_add_neg]
    rw [hshift, barrier_shift_invariant]

/-! ## 4. Anchor corrections: impossibility bound and two-point exactness -/

/-- A single-anchor correction: force point `k` to its reference value and
leave the rest of the model profile untouched. -/
def anchored (m r : Profile n) (k : Fin n) : Profile n :=
  fun i => if i = k then r i else m i

/-- A two-anchor correction (typically saddle + endpoint). -/
def anchored2 (m r : Profile n) (k₁ k₂ : Fin n) : Profile n :=
  fun i => if i = k₁ ∨ i = k₂ then r i else m i

/-- The deviation between a profile and its single-anchor correction is the
removed deviation at `k` and zero elsewhere; with at least two sampled
points its wobble is exactly `|m k − r k|`. -/
theorem wobble_anchor_deviation (hn : 1 < n) (m r : Profile n) (k : Fin n) :
    wobble (deviation (anchored m r k) m) = |m k - r k| := by
  obtain ⟨j, hjk⟩ := Fintype.exists_ne_of_one_lt_card (α := Fin n)
    (by rw [Fintype.card_fin]; exact hn) k
  set c := r k - m k with hc
  have hval : ∀ i, deviation (anchored m r k) m i = if i = k then c else 0 := by
    intro i
    show (if i = k then r i else m i) - m i = if i = k then c else 0
    by_cases hi : i = k <;> simp [hi, hc]
  have hck : deviation (anchored m r k) m k = c := by rw [hval k, if_pos rfl]
  have h0 : deviation (anchored m r k) m j = 0 := by rw [hval j, if_neg hjk]
  have hsup : profileMax (deviation (anchored m r k) m) = max c 0 := by
    apply le_antisymm
    · rw [profileMax, Finset.sup'_le_iff]
      intro i _
      rw [hval i]
      by_cases hi : i = k <;> simp [hi]
    · apply max_le
      · rw [← hck]
        exact Finset.le_sup' (f := deviation (anchored m r k) m)
          (Finset.mem_univ k)
      · rw [← h0]
        exact Finset.le_sup' (f := deviation (anchored m r k) m)
          (Finset.mem_univ j)
  have hinf : profileMin (deviation (anchored m r k) m) = min c 0 := by
    apply le_antisymm
    · apply le_min
      · rw [← hck]
        exact Finset.inf'_le (f := deviation (anchored m r k) m)
          (Finset.mem_univ k)
      · rw [← h0]
        exact Finset.inf'_le (f := deviation (anchored m r k) m)
          (Finset.mem_univ j)
    · simp only [profileMin]
      apply Finset.le_inf'
      intro i _
      rw [hval i]
      by_cases hi : i = k <;> simp [hi]
  rw [wobble, barrier, hsup, hinf, abs_sub_comm (m k) (r k), ← hc]
  rcases le_total c 0 with h | h
  · rw [max_eq_right h, min_eq_left h, abs_of_nonpos h]
    ring
  · rw [max_eq_left h, min_eq_right h, abs_of_nonneg h]
    ring

/-- **Theorem 4a (one anchor moves at most its own deviation).** Anchoring a
single point changes the sampled barrier by at most the removed deviation. -/
theorem anchor_barrier_change_le (hn : 1 < n) (m r : Profile n) (k : Fin n) :
    |barrier (anchored m r k) - barrier m| ≤ |m k - r k| := by
  rw [← wobble_anchor_deviation hn m r k]
  exact barrier_error_le_wobble (anchored m r k) m

/-- **Theorem 4 (anchor impossibility bound).** The residual barrier error
after a single-anchor correction is at least the raw barrier error minus the
anchored deviation: one anchor can buy no more accuracy than the deviation it
removes. -/
theorem anchor_impossibility_bound (hn : 1 < n) (m r : Profile n) (k : Fin n) :
    |barrier m - barrier r| - |m k - r k| ≤
      |barrier (anchored m r k) - barrier r| := by
  have h4a := anchor_barrier_change_le hn m r k
  have htri : |barrier m - barrier r| ≤
      |barrier m - barrier (anchored m r k)| +
        |barrier (anchored m r k) - barrier r| :=
    abs_sub_le (barrier m) (barrier (anchored m r k)) (barrier r)
  rw [abs_sub_comm (barrier m) (barrier (anchored m r k))] at htri
  linarith

/-- The design sketch's naive wobble lower bound `residual ≥ wobble d − |d k|`
is FALSE: the deviation `(0, 100, 1)` wobbles by 100 while the anchored
residual barrier error is exactly 0 — the deviation rotates the profile,
preserving its barrier. The proved form (`anchor_impossibility_bound`)
lower-bounds the residual by the raw barrier error minus the anchored
deviation, not by the wobble. -/
theorem anchor_wobble_lower_bound_refuted :
    |barrier (anchored (![50, 100, 51] : Profile 3) (![50, 0, 50] : Profile 3) 0) -
        barrier (![50, 0, 50] : Profile 3)| <
      wobble (deviation (![50, 100, 51] : Profile 3) (![50, 0, 50] : Profile 3)) -
        |deviation (![50, 100, 51] : Profile 3) (![50, 0, 50] : Profile 3) 0| := by
  have hanch : anchored (![50, 100, 51] : Profile 3) (![50, 0, 50] : Profile 3) 0 =
      (![50, 100, 51] : Profile 3) := by
    funext i
    by_cases hi : i = 0 <;> simp [anchored, hi]
  have hdev : deviation (![50, 100, 51] : Profile 3) (![50, 0, 50] : Profile 3) =
      (![0, 100, 1] : Profile 3) := by
    funext i
    fin_cases i <;> norm_num [deviation]
  have hb1 : barrier (![50, 100, 51] : Profile 3) = 50 := by
    rw [barrier_triple,
      max_eq_right (by norm_num : (50:ℝ) ≤ 100),
      max_eq_left (by norm_num : (51:ℝ) ≤ 100),
      min_eq_left (by norm_num : (50:ℝ) ≤ 100),
      min_eq_left (by norm_num : (50:ℝ) ≤ 51)]
    norm_num
  have hb2 : barrier (![50, 0, 50] : Profile 3) = 50 := by
    rw [barrier_triple,
      max_eq_left (by norm_num : (0:ℝ) ≤ 50),
      max_eq_left (le_refl (50:ℝ)),
      min_eq_right (by norm_num : (0:ℝ) ≤ 50),
      min_eq_left (by norm_num : (0:ℝ) ≤ 50)]
    norm_num
  have hb3 : barrier (![0, 100, 1] : Profile 3) = 100 := by
    rw [barrier_triple,
      max_eq_right (by norm_num : (0:ℝ) ≤ 100),
      max_eq_left (by norm_num : (1:ℝ) ≤ 100),
      min_eq_left (by norm_num : (0:ℝ) ≤ 100),
      min_eq_left (by norm_num : (0:ℝ) ≤ 1)]
    norm_num
  rw [hanch, hdev, wobble, hb1, hb2, hb3]
  simp only [Matrix.cons_val_zero]
  norm_num

/-- **Theorem 4c (two-point exactness).** Anchoring at a sampled maximum and
a sampled minimum of the reference reconstructs the reference barrier
exactly, as long as every remaining model value stays inside the reference
range: the interior of the model profile is irrelevant beyond range
compliance. Sparse anchors pay for accuracy with model irrelevance. -/
theorem two_point_anchor_exact (m r : Profile n) (k₁ k₂ : Fin n)
    (hmax : r k₁ = profileMax r) (hmin : r k₂ = profileMin r)
    (hinterior : ∀ i, i ≠ k₁ → i ≠ k₂ → profileMin r ≤ m i ∧ m i ≤ profileMax r) :
    barrier (anchored2 m r k₁ k₂) = barrier r := by
  have hsup : profileMax (anchored2 m r k₁ k₂) = profileMax r := by
    apply le_antisymm
    · rw [profileMax, Finset.sup'_le_iff]
      intro i _
      by_cases hi : i = k₁ ∨ i = k₂
      · simp only [anchored2, hi, if_true]
        exact Finset.le_sup' (f := r) (Finset.mem_univ i)
      · simp only [anchored2, hi, if_false]
        exact (hinterior i (fun h => hi (Or.inl h)) (fun h => hi (Or.inr h))).2
    · rw [← hmax,
        show r k₁ = anchored2 m r k₁ k₂ k₁ from (if_pos (Or.inl rfl)).symm]
      exact Finset.le_sup' (f := anchored2 m r k₁ k₂) (Finset.mem_univ k₁)
  have hinf : profileMin (anchored2 m r k₁ k₂) = profileMin r := by
    apply le_antisymm
    · rw [← hmin,
        show r k₂ = anchored2 m r k₁ k₂ k₂ from (if_pos (Or.inr rfl)).symm]
      exact Finset.inf'_le (f := anchored2 m r k₁ k₂) (Finset.mem_univ k₂)
    · rw [profileMin]
      apply Finset.le_inf'
      intro i _
      by_cases hi : i = k₁ ∨ i = k₂
      · simp only [anchored2, hi, if_true]
        exact Finset.inf'_le (f := r) (Finset.mem_univ i)
      · simp only [anchored2, hi, if_false]
        exact (hinterior i (fun h => hi (Or.inl h)) (fun h => hi (Or.inr h))).1
  rw [barrier, barrier, hsup, hinf]

/-- Two-point exactness, computed: anchoring the endpoint (index 0) and the
saddle (index 2) reconstructs the 10-unit reference barrier of
`r = (0, 5, 10)` even though the raw model `m = (3, 4, 12)` misses it
(raw barrier 9, error 1) — the interior model value 4 matters only through
staying inside the reference range. -/
theorem two_point_anchor_exact_witness :
    barrier (anchored2 (![3, 4, 12] : Profile 3) (![0, 5, 10] : Profile 3) 2 0) =
      barrier (![0, 5, 10] : Profile 3) := by
  apply two_point_anchor_exact
  · rw [profileMax_triple, max_eq_right (by norm_num : (0:ℝ) ≤ 5),
      max_eq_right (by norm_num : (5:ℝ) ≤ 10)]
    simp
  · rw [profileMin_triple, min_eq_left (by norm_num : (0:ℝ) ≤ 5),
      min_eq_left (by norm_num : (0:ℝ) ≤ 10)]
    simp
  · intro i hi1 hi2
    fin_cases i
    · exact absurd rfl hi2
    · rw [profileMin_triple, profileMax_triple,
        min_eq_left (by norm_num : (0:ℝ) ≤ 5),
        min_eq_left (by norm_num : (0:ℝ) ≤ 10),
        max_eq_right (by norm_num : (0:ℝ) ≤ 5),
        max_eq_right (by norm_num : (5:ℝ) ≤ 10)]
      constructor <;> norm_num
    · exact absurd rfl hi1

end OpenDistillationFactory.HonestErrors.CorrectionBoundary
