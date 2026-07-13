/- AUTHORED from the Li-S discovery-gates demo (report sha256 358e94629954).
   First instantiation of the Shapes.Certificates claim-shapes on real
   discovery subjects: Li2S antifluorite (known-good) and rocksalt LiS
   (unproven composition). GPa x10000. Every verdict below is the kernel
   re-checking the gate arithmetic, including the honest ones. -/
import LupineEvidence.Shapes.Certificates

namespace Lupine.Discovery.LiSDemo
open Lupine.Shapes

/-- Li2S_antifluorite/chgnet: measured cubic elastic constants (GPa x10000). -/
def elastic_li2s_chgnet : CubicElastic := ⟨389617, 153901, 168446⟩

/-- Born mechanical stability holds for Li2S_antifluorite/chgnet. -/
theorem born_li2s_chgnet : bornStable elastic_li2s_chgnet := by decide

/-- Li2S_antifluorite/mace-mp-small: measured cubic elastic constants (GPa x10000). -/
def elastic_li2s_mace_mp_small : CubicElastic := ⟨649127, 188993, 298105⟩

/-- Born mechanical stability holds for Li2S_antifluorite/mace-mp-small. -/
theorem born_li2s_mace_mp_small : bornStable elastic_li2s_mace_mp_small := by decide

/-- Li2S_antifluorite/mace-mp-medium: measured cubic elastic constants (GPa x10000). -/
def elastic_li2s_mace_mp_medium : CubicElastic := ⟨679666, 177008, 239122⟩

/-- Born mechanical stability holds for Li2S_antifluorite/mace-mp-medium. -/
theorem born_li2s_mace_mp_medium : bornStable elastic_li2s_mace_mp_medium := by decide

/-- Li2S_antifluorite/mace-mpa-0-medium: measured cubic elastic constants (GPa x10000). -/
def elastic_li2s_mace_mpa_0_medium : CubicElastic := ⟨780630, 184600, 348027⟩

/-- Born mechanical stability holds for Li2S_antifluorite/mace-mpa-0-medium. -/
theorem born_li2s_mace_mpa_0_medium : bornStable elastic_li2s_mace_mpa_0_medium := by decide

/-- LiS_rocksalt/chgnet: measured cubic elastic constants (GPa x10000). -/
def elastic_lis_chgnet : CubicElastic := ⟨1200015, 646638, -70627⟩

/-- Born stability FAILS for LiS_rocksalt/chgnet (C44 = -7.1 GPa < 0): the candidate's own predicted physics refuses it. -/
theorem not_born_lis_chgnet : ¬ bornStable elastic_lis_chgnet := by decide

/-- LiS_rocksalt/mace-mp-small: measured cubic elastic constants (GPa x10000). -/
def elastic_lis_mace_mp_small : CubicElastic := ⟨599094, 442090, -182497⟩

/-- Born stability FAILS for LiS_rocksalt/mace-mp-small (C44 = -18.2 GPa < 0): the candidate's own predicted physics refuses it. -/
theorem not_born_lis_mace_mp_small : ¬ bornStable elastic_lis_mace_mp_small := by decide

/-- LiS_rocksalt/mace-mp-medium: measured cubic elastic constants (GPa x10000). -/
def elastic_lis_mace_mp_medium : CubicElastic := ⟨915372, 344667, -143424⟩

/-- Born stability FAILS for LiS_rocksalt/mace-mp-medium (C44 = -14.3 GPa < 0): the candidate's own predicted physics refuses it. -/
theorem not_born_lis_mace_mp_medium : ¬ bornStable elastic_lis_mace_mp_medium := by decide

/-- LiS_rocksalt/mace-mpa-0-medium: measured cubic elastic constants (GPa x10000). -/
def elastic_lis_mace_mpa_0_medium : CubicElastic := ⟨894416, 158064, -384317⟩

/-- Born stability FAILS for LiS_rocksalt/mace-mpa-0-medium (C44 = -38.4 GPa < 0): the candidate's own predicted physics refuses it. -/
theorem not_born_lis_mace_mpa_0_medium : ¬ bornStable elastic_lis_mace_mpa_0_medium := by decide

/-- Li2S_antifluorite: C44 cross-model dispersion window (thresholds derived from the 84-cell baseline, p75/p95). -/
def c44_window_li2s : ConcordanceWindow := ⟨6685, 2490, 3848⟩
theorem c44_refused_li2s : refused c44_window_li2s := by decide

/-- LiS_rocksalt: C44 cross-model dispersion window (thresholds derived from the 84-cell baseline, p75/p95). -/
def c44_window_lis : ConcordanceWindow := ⟨19249, 2490, 3848⟩
theorem c44_refused_lis : refused c44_window_lis := by decide

end Lupine.Discovery.LiSDemo