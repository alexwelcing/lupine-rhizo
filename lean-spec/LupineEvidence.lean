/- LupineEvidence — MANIFEST of the generated evidence corpus (ladder rung L1).

   This file is the reviewed admission list: every generated evidence/verdict
   module under `LupineEvidence/` MUST be imported here, and every import here
   MUST exist on disk. `scripts/check_evidence_manifest.sh` enforces the
   bijection; the `LupineEvidence.+` glob in lakefile.toml builds every file
   in the tree regardless, so an orphan still compiles but fails the manifest
   gate instead of rotting silently.

   Generated-file convention: each module is written by a generator and starts
   with an `/- AUTHORED by/from ... -/` header naming the emitter and the
   sha256 of its inputs. Do NOT edit the generated modules by hand — re-run
   the generator (binder CLI `--emit-lean`, or the Round emitters) and re-sync.
   Regenerated 2026-07-02: module names now carry structure
   (Material_structure_model); 84 evidence modules incl. MPA-0 + 9 Round
   verdict modules + demo.
   2026-07-02 (ladder L3 groundwork): Shapes.Certificates admitted — the
   first HAND-WRITTEN module (typed claim-shapes the discovery workflow
   instantiates; see LupineEvidence/Shapes/README.md). Generated instances
   of these shapes land in LupineEvidence/Discovery/. -/

import LupineEvidence.Demo.Ni_EAM
import LupineEvidence.Shapes.Certificates
import LupineEvidence.Discovery.Certificates_LiS_Demo
import LupineEvidence.YMatrix.Ag_chgnet
import LupineEvidence.YMatrix.Ag_fcc_chgnet
import LupineEvidence.YMatrix.Ag_fcc_mace_mp_medium
import LupineEvidence.YMatrix.Ag_fcc_mace_mp_small
import LupineEvidence.YMatrix.Ag_fcc_mace_mpa_0_medium
import LupineEvidence.YMatrix.Ag_mace_mp_medium
import LupineEvidence.YMatrix.Ag_mace_mp_small
import LupineEvidence.YMatrix.Al_chgnet
import LupineEvidence.YMatrix.Al_fcc_chgnet
import LupineEvidence.YMatrix.Al_fcc_mace_mp_medium
import LupineEvidence.YMatrix.Al_fcc_mace_mp_small
import LupineEvidence.YMatrix.Al_fcc_mace_mpa_0_medium
import LupineEvidence.YMatrix.Al_mace_mp_medium
import LupineEvidence.YMatrix.Al_mace_mp_small
import LupineEvidence.YMatrix.Au_chgnet
import LupineEvidence.YMatrix.Au_fcc_chgnet
import LupineEvidence.YMatrix.Au_fcc_mace_mp_medium
import LupineEvidence.YMatrix.Au_fcc_mace_mp_small
import LupineEvidence.YMatrix.Au_fcc_mace_mpa_0_medium
import LupineEvidence.YMatrix.Au_mace_mp_medium
import LupineEvidence.YMatrix.Au_mace_mp_small
import LupineEvidence.YMatrix.Ca_chgnet
import LupineEvidence.YMatrix.Ca_fcc_chgnet
import LupineEvidence.YMatrix.Ca_fcc_mace_mp_medium
import LupineEvidence.YMatrix.Ca_fcc_mace_mp_small
import LupineEvidence.YMatrix.Ca_fcc_mace_mpa_0_medium
import LupineEvidence.YMatrix.Ca_mace_mp_medium
import LupineEvidence.YMatrix.Ca_mace_mp_small
import LupineEvidence.YMatrix.Cr_bcc_chgnet
import LupineEvidence.YMatrix.Cr_bcc_mace_mp_medium
import LupineEvidence.YMatrix.Cr_bcc_mace_mp_small
import LupineEvidence.YMatrix.Cr_bcc_mace_mpa_0_medium
import LupineEvidence.YMatrix.Cr_chgnet
import LupineEvidence.YMatrix.Cr_mace_mp_medium
import LupineEvidence.YMatrix.Cr_mace_mp_small
import LupineEvidence.YMatrix.Cu_chgnet
import LupineEvidence.YMatrix.Cu_fcc_chgnet
import LupineEvidence.YMatrix.Cu_fcc_mace_mp_medium
import LupineEvidence.YMatrix.Cu_fcc_mace_mp_small
import LupineEvidence.YMatrix.Cu_fcc_mace_mpa_0_medium
import LupineEvidence.YMatrix.Cu_mace_mp_medium
import LupineEvidence.YMatrix.Cu_mace_mp_small
import LupineEvidence.YMatrix.Fe_bcc_chgnet
import LupineEvidence.YMatrix.Fe_bcc_mace_mp_medium
import LupineEvidence.YMatrix.Fe_bcc_mace_mp_small
import LupineEvidence.YMatrix.Fe_bcc_mace_mpa_0_medium
import LupineEvidence.YMatrix.Fe_chgnet
import LupineEvidence.YMatrix.Fe_mace_mp_medium
import LupineEvidence.YMatrix.Fe_mace_mp_small
import LupineEvidence.YMatrix.MgO_rocksalt_chgnet
import LupineEvidence.YMatrix.MgO_rocksalt_mace_mp_medium
import LupineEvidence.YMatrix.MgO_rocksalt_mace_mp_small
import LupineEvidence.YMatrix.MgO_rocksalt_mace_mpa_0_medium
import LupineEvidence.YMatrix.Mo_bcc_chgnet
import LupineEvidence.YMatrix.Mo_bcc_mace_mp_medium
import LupineEvidence.YMatrix.Mo_bcc_mace_mp_small
import LupineEvidence.YMatrix.Mo_bcc_mace_mpa_0_medium
import LupineEvidence.YMatrix.Mo_chgnet
import LupineEvidence.YMatrix.Mo_mace_mp_medium
import LupineEvidence.YMatrix.Mo_mace_mp_small
import LupineEvidence.YMatrix.NaCl_rocksalt_chgnet
import LupineEvidence.YMatrix.NaCl_rocksalt_mace_mp_medium
import LupineEvidence.YMatrix.NaCl_rocksalt_mace_mp_small
import LupineEvidence.YMatrix.NaCl_rocksalt_mace_mpa_0_medium
import LupineEvidence.YMatrix.Nb_bcc_chgnet
import LupineEvidence.YMatrix.Nb_bcc_mace_mp_medium
import LupineEvidence.YMatrix.Nb_bcc_mace_mp_small
import LupineEvidence.YMatrix.Nb_bcc_mace_mpa_0_medium
import LupineEvidence.YMatrix.Nb_chgnet
import LupineEvidence.YMatrix.Nb_mace_mp_medium
import LupineEvidence.YMatrix.Nb_mace_mp_small
import LupineEvidence.YMatrix.Ni3Al_chgnet
import LupineEvidence.YMatrix.Ni3Al_l12_chgnet
import LupineEvidence.YMatrix.Ni3Al_l12_mace_mp_medium
import LupineEvidence.YMatrix.Ni3Al_l12_mace_mp_small
import LupineEvidence.YMatrix.Ni3Al_l12_mace_mpa_0_medium
import LupineEvidence.YMatrix.Ni3Al_mace_mp_medium
import LupineEvidence.YMatrix.Ni3Al_mace_mp_small
import LupineEvidence.YMatrix.NiAl_b2_chgnet
import LupineEvidence.YMatrix.NiAl_b2_mace_mp_medium
import LupineEvidence.YMatrix.NiAl_b2_mace_mp_small
import LupineEvidence.YMatrix.NiAl_b2_mace_mpa_0_medium
import LupineEvidence.YMatrix.NiAl_chgnet
import LupineEvidence.YMatrix.NiAl_mace_mp_medium
import LupineEvidence.YMatrix.NiAl_mace_mp_small
import LupineEvidence.YMatrix.Ni_chgnet
import LupineEvidence.YMatrix.Ni_fcc_chgnet
import LupineEvidence.YMatrix.Ni_fcc_mace_mp_medium
import LupineEvidence.YMatrix.Ni_fcc_mace_mp_small
import LupineEvidence.YMatrix.Ni_fcc_mace_mpa_0_medium
import LupineEvidence.YMatrix.Ni_mace_mp_medium
import LupineEvidence.YMatrix.Ni_mace_mp_small
import LupineEvidence.YMatrix.Pd_chgnet
import LupineEvidence.YMatrix.Pd_fcc_chgnet
import LupineEvidence.YMatrix.Pd_fcc_mace_mp_medium
import LupineEvidence.YMatrix.Pd_fcc_mace_mp_small
import LupineEvidence.YMatrix.Pd_fcc_mace_mpa_0_medium
import LupineEvidence.YMatrix.Pd_mace_mp_medium
import LupineEvidence.YMatrix.Pd_mace_mp_small
import LupineEvidence.YMatrix.Pt_chgnet
import LupineEvidence.YMatrix.Pt_fcc_chgnet
import LupineEvidence.YMatrix.Pt_fcc_mace_mp_medium
import LupineEvidence.YMatrix.Pt_fcc_mace_mp_small
import LupineEvidence.YMatrix.Pt_fcc_mace_mpa_0_medium
import LupineEvidence.YMatrix.Pt_mace_mp_medium
import LupineEvidence.YMatrix.Pt_mace_mp_small
import LupineEvidence.YMatrix.Round1_H4
import LupineEvidence.YMatrix.Round1_Verdicts
import LupineEvidence.YMatrix.Round2_Verdicts
import LupineEvidence.YMatrix.Round3_Ordinal
import LupineEvidence.YMatrix.Round4_Isotonic
import LupineEvidence.YMatrix.Round5_LammpsValue
import LupineEvidence.YMatrix.Round6_MRH
import LupineEvidence.YMatrix.Round7_FamilyExponent
import LupineEvidence.YMatrix.Round8_EnvField
import LupineEvidence.YMatrix.Si_chgnet
import LupineEvidence.YMatrix.Si_diamond_chgnet
import LupineEvidence.YMatrix.Si_diamond_mace_mp_medium
import LupineEvidence.YMatrix.Si_diamond_mace_mp_small
import LupineEvidence.YMatrix.Si_diamond_mace_mpa_0_medium
import LupineEvidence.YMatrix.Si_mace_mp_medium
import LupineEvidence.YMatrix.Si_mace_mp_small
import LupineEvidence.YMatrix.Sr_chgnet
import LupineEvidence.YMatrix.Sr_fcc_chgnet
import LupineEvidence.YMatrix.Sr_fcc_mace_mp_medium
import LupineEvidence.YMatrix.Sr_fcc_mace_mp_small
import LupineEvidence.YMatrix.Sr_fcc_mace_mpa_0_medium
import LupineEvidence.YMatrix.Sr_mace_mp_medium
import LupineEvidence.YMatrix.Sr_mace_mp_small
import LupineEvidence.YMatrix.Ta_bcc_chgnet
import LupineEvidence.YMatrix.Ta_bcc_mace_mp_medium
import LupineEvidence.YMatrix.Ta_bcc_mace_mp_small
import LupineEvidence.YMatrix.Ta_bcc_mace_mpa_0_medium
import LupineEvidence.YMatrix.Ta_chgnet
import LupineEvidence.YMatrix.Ta_mace_mp_medium
import LupineEvidence.YMatrix.Ta_mace_mp_small
import LupineEvidence.YMatrix.V_bcc_chgnet
import LupineEvidence.YMatrix.V_bcc_mace_mp_medium
import LupineEvidence.YMatrix.V_bcc_mace_mp_small
import LupineEvidence.YMatrix.V_bcc_mace_mpa_0_medium
import LupineEvidence.YMatrix.V_chgnet
import LupineEvidence.YMatrix.V_mace_mp_medium
import LupineEvidence.YMatrix.V_mace_mp_small
import LupineEvidence.YMatrix.W_bcc_chgnet
import LupineEvidence.YMatrix.W_bcc_mace_mp_medium
import LupineEvidence.YMatrix.W_bcc_mace_mp_small
import LupineEvidence.YMatrix.W_bcc_mace_mpa_0_medium
import LupineEvidence.YMatrix.W_chgnet
import LupineEvidence.YMatrix.W_mace_mp_medium
import LupineEvidence.YMatrix.W_mace_mp_small
