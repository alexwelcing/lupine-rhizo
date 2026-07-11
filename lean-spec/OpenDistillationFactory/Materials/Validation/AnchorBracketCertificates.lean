import OpenDistillationFactory.Materials.Theory.AnchorBracket
import OpenDistillationFactory.Materials.DistillAtlas.EnvFieldInstances

/-!
# Anchor-bracket certificates on the bound Y-matrix corpus

`Theory.AnchorBracket` proves what measured anchors determine *in general*;
this module instantiates those laws on the generated corpus
(`DistillAtlas.EnvFieldInstances`, corpus sha256 `c4393f3e3bcb`), producing
kernel-checked certificates about the actual (model, material) cells the
platform corrects with. Three kinds of certificate:

1. **Impossibility certificates** — the refusal upgrade. For the flagship
   refused cells (the stiffening `mace-mpa-0-medium/Ni` fcc cell and the
   `mace-mp-small/V` bcc cell locked in `Vision.lean`), we certify that
   **no softening field at all** passes through their measured anchors:
   the tier-2 refusal is forced by the physics axioms, not by the choice
   of the clamped step interpolation.

2. **Gap certificates** — for the flagship admitted cells (`chgnet/Ni` fcc,
   `chgnet/Fe` bcc), every field consistent with the measured anchors has
   its unanchored gap value pinned inside the measured anchor interval,
   and the cell's certified per-atom bracket width is a concrete rational
   (`537 × 10⁻⁴ eV/atom` for chgnet/Ni, `256 × 10⁻⁴ eV/atom` for
   chgnet/Fe).

3. **Identification-quality comparisons** — the certified per-atom bracket
   width is a *figure of merit for correction trustworthiness* that
   differs across models on the same material: on Ni, the
   `mace-mp-medium` cell's width (`81 × 10⁻⁴ eV/atom`) is provably more
   than six times tighter than the `chgnet` cell's (`537 × 10⁻⁴ eV/atom`).
   A promotion gate can prefer the better-identified cell *with a proof*.
   The diamond flagship (`chgnet/Si`) has width zero: its in-range
   corrections are certified **exact** under field-decomposability over
   any consistent measured field.

Empirical provenance: every numeral below is a generated corpus anchor
(×10⁻⁴ eV/atom, exact rationals) emitted by
`python/scripts/bind_env_field_instances.py`; nothing here is tuned to
make a theorem pass. House rules: zero `sorry`, zero new axioms.
-/

namespace OpenDistillationFactory.Materials.Validation.AnchorBracketCertificates

open OpenDistillationFactory.Materials.Theory.EnvironmentField
open OpenDistillationFactory.Materials.Theory.AnchoredField
open OpenDistillationFactory.Materials.Theory.AnchorBracket
open OpenDistillationFactory.Materials.DistillAtlas.EnvFieldInstances

/-! ## Impossibility certificates for the flagship refusals -/

/-- **No softening field exists for the mace-mpa-0-medium/Ni (fcc) cell.**
Its measured anchors (4190, 2296, 125)×10⁻⁴ eV/atom sit *above* bulk
accuracy — the stiffening/noise-floor regime. Proved by composing the
generated refusal `field_refused_mace_mpa_0_medium_Ni` with the
scaled-integer identification bridge, so this certificate breaks (rather
than silently desynchronizing) if corpus regeneration changes the cell's
anchors: the refusal is not merely "outside the step constructor's
precondition" but inconsistency with every `ErrorField 12`. -/
theorem no_interpolant_mace_mpa_0_medium_Ni :
    ¬ ∃ F : ErrorField 12,
      InterpolatesFcc F (4190 / 10000) (2296 / 10000) (125 / 10000) :=
  fun ⟨F, hF⟩ => field_refused_mace_mpa_0_medium_Ni
    ((scaledAnchorsValid_iff_exists_interpolant 4190 2296 125).mpr
      ⟨F, by push_cast; exact hF⟩)

/-- **No softening field exists for the mace-mp-small/V (bcc) cell.** Its
measured anchors (5401, 3072, 404)×10⁻⁴ eV/atom violate monotone
softening; composed with the generated refusal `field_refused_mace_mp_small_V`
through the bcc bridge, certifying that no `ErrorField 8` passes through
this cell's anchors. -/
theorem no_interpolant_mace_mp_small_V :
    ¬ ∃ F : ErrorField 8,
      InterpolatesBcc F (5401 / 10000) (3072 / 10000) (404 / 10000) :=
  fun ⟨F, hF⟩ => field_refused_mace_mp_small_V
    ((scaledAnchorsBccValid_iff_exists_interpolant 5401 3072 404).mpr
      ⟨F, by push_cast; exact hF⟩)

/-! ## Gap certificates for the flagship admitted cells -/

/-- **The chgnet/Ni gap certificate.** Every softening field consistent with
the chgnet/Ni measured anchors has its unanchored c = 10 value inside the
measured interval `[−673, −136]×10⁻⁴ eV/atom`: the corpus pins the
unmeasured coordination to within `537×10⁻⁴ eV/atom` of certainty. -/
theorem chgnet_Ni_gap_certificate :
    ∀ F : ErrorField 12,
      InterpolatesFcc F (-980 / 10000) (-673 / 10000) (-136 / 10000) →
        (-673 / 10000 : ℝ) ≤ F.P 10 ∧ F.P 10 ≤ (-136 / 10000 : ℝ) :=
  fun _ hF => interpolant_gap_mem hF

/-- The chgnet/Ni certified per-atom bracket width is exactly
`537 × 10⁻⁴ eV/atom` — the anchor gap `p11 − p9` that bounds the correction
overshoot of `corrected_bracket_fcc` per c = 10 atom. -/
theorem chgnet_Ni_bracket_width :
    (-136 / 10000 : ℝ) - (-673 / 10000) = 537 / 10000 := by
  norm_num

/-- **The chgnet/Fe (bcc) gap certificate.** Every softening field
consistent with the chgnet/Fe measured anchors has its unanchored c = 5
value inside `[−4852, −4596]×10⁻⁴ eV/atom`. -/
theorem chgnet_Fe_gap_certificate :
    ∀ F : ErrorField 8,
      InterpolatesBcc F (-4852 / 10000) (-4596 / 10000) (-1697 / 10000) →
        (-4852 / 10000 : ℝ) ≤ F.P 5 ∧ F.P 5 ≤ (-4596 / 10000 : ℝ) :=
  fun _ hF => interpolant_gap_mem_bcc hF

/-- The chgnet/Fe certified per-atom bracket width is exactly
`256 × 10⁻⁴ eV/atom` (the c = 5 gap budget `p6 − p4`). -/
theorem chgnet_Fe_bracket_width :
    (-4596 / 10000 : ℝ) - (-4852 / 10000) = 256 / 10000 := by
  norm_num

/-! ## Identification-quality comparison across models -/

/-- **On Ni, mace-mp-medium's corrections are certifiably better identified
than chgnet's.** Both cells pass tier 2, but the certified per-atom bracket
width — the correction uncertainty the anchors cannot remove — is
`81 × 10⁻⁴ eV/atom` for mace-mp-medium against `537 × 10⁻⁴ eV/atom` for
chgnet: more than six times tighter, and the factor-six bound is part of
the statement. A promotion gate ranking corrected Ni observables can prefer
the tighter cell with a kernel-checked justification. -/
theorem ni_bracket_width_comparison :
    6 * (((-229 : ℝ) / 10000) - ((-310) / 10000)) <
      ((-136 : ℝ) / 10000) - ((-673) / 10000) := by
  norm_num

/-! ## Exactness certificate for the diamond flagship -/

/-- **chgnet/Si corrections are exact in range.** The diamond layout has no
unanchored in-range coordination, so if the model's energy error decomposes
over *any* measured field `M` through the chgnet/Si anchor — not necessarily
the corpus step field — the corpus cell's correction still recovers the
reference energy exactly on in-range configurations: the single anchor fully
identifies the in-range field, so the corpus instance corrects with zero
width no matter which consistent field is true. -/
theorem chgnet_Si_inrange_exact {M : MeasuredField 4}
    (hM : M.P 3 = (-6906 / 10000 : ℝ)) {eModel eRef : ℝ} {cfg : Config}
    (hcfg : InRangeDiamond cfg)
    (h : eModel = eRef + M.fieldSum cfg) :
    mfield_chgnet_Si.corrected eModel cfg = eRef :=
  corrected_exact_diamond hM hcfg h

end OpenDistillationFactory.Materials.Validation.AnchorBracketCertificates
