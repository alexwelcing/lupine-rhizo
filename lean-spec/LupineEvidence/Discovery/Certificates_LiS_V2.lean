/- AUTHORED from the Li-S discovery-gates re-verdict under per-property
   thresholds.v2 (report sha256 fb824484c2c1, panel li-s, gate order
   early-stop, 2026-07-13). The v1 -> v2 migration replaced the B0-proxy
   transfer with per-property p75/p95 thresholds measured on the 21-material
   x 4-model elastic baseline (thresholds.v2.json). Every verdict change is
   certified below as THRESHOLD-DRIVEN via the Shapes migration laws — the
   measured dispersions are identical between runs (deterministic probe) —
   and the LiS Born refusal is upgraded from four per-model failures to a
   single ensemble-hull impossibility. Dispersions and thresholds x10000. -/
import LupineEvidence.Shapes.Certificates
import LupineEvidence.Discovery.Certificates_LiS_Demo

namespace Lupine.Discovery.LiSV2
open Lupine.Shapes
open Lupine.Discovery.LiSDemo

/-! ## Li2S antifluorite (known-good): the v1 false refusal, un-refused

    v1 refused the known-good calibration subject on C11 (disp 0.5885) and
    C44 (disp 0.6685) because the 0.3848 refuse threshold was measured on B0
    dispersions. Under C11/C44's OWN baselines the same dispersions are
    flag/pass. The kernel certifies each un-refusal is exactly a
    threshold-loosening, never a data change. -/

/-- Li2S C11 under the v1 B0-proxy window: refused. -/
def c11_li2s_v1 : ConcordanceWindow := ⟨5885, 2490, 3848⟩
/-- Li2S C11 under its own v2 per-property window: flagged, NOT refused. -/
def c11_li2s_v2 : ConcordanceWindow := ⟨5885, 4884, 12106⟩

theorem c11_li2s_v1_refused : refused c11_li2s_v1 := by decide
theorem c11_li2s_v2_flagged : flagged c11_li2s_v2 := by decide
theorem c11_li2s_v2_not_refused : ¬ refused c11_li2s_v2 := by decide

/-- The C11 un-refusal is threshold-driven: same dispersion, and the kernel
    derives that the v2 refuse threshold must be strictly looser. -/
theorem c11_li2s_unrefusal_threshold_driven :
    c11_li2s_v1.refuseThreshold < c11_li2s_v2.refuseThreshold :=
  unrefusal_needs_looser_threshold c11_li2s_v1 c11_li2s_v2
    (by decide) c11_li2s_v1_refused c11_li2s_v2_not_refused

/-- Li2S C44 under the v1 B0-proxy window: refused (this is the window the
    demo module certified). -/
def c44_li2s_v1 : ConcordanceWindow := c44_window_li2s
/-- Li2S C44 under its own v2 per-property window: fully concordant. -/
def c44_li2s_v2 : ConcordanceWindow := ⟨6685, 12220, 37891⟩

theorem c44_li2s_v2_concordant : concordant c44_li2s_v2 := by decide
theorem c44_li2s_v2_not_refused : ¬ refused c44_li2s_v2 := by decide

/-- The C44 un-refusal is threshold-driven. -/
theorem c44_li2s_unrefusal_threshold_driven :
    c44_li2s_v1.refuseThreshold < c44_li2s_v2.refuseThreshold :=
  unrefusal_needs_looser_threshold c44_li2s_v1 c44_li2s_v2
    (by decide) c44_refused_li2s c44_li2s_v2_not_refused

/-- Li2S B0 keeps its verdict across the migration: the v2 B0 thresholds
    reproduce v1's exactly (same property, same baseline percentiles), and
    the cell stays flagged — the migration only moved verdicts where the
    proxy was wrong. -/
def b0_li2s_v2 : ConcordanceWindow := ⟨2580, 2490, 3848⟩
theorem b0_li2s_v2_flagged : flagged b0_li2s_v2 := by decide

/-! ## LiS rocksalt (speculative): still refused, on better evidence

    The negative control survives recalibration. Under v2 the tightened a0
    window (refuse at 0.0086, measured on a0's own near-zero dispersion
    baseline) becomes a DISCRIMINATIVE gate: LiS a0 dispersion 0.0199 is
    2.3x past refuse while known-good Li2S passes at 0.0050. C12 also
    refuses on its own baseline. -/

/-- LiS a0 under v2: refused — a gate that was vacuously lenient under the
    v1 proxy (0.0199 << 0.3848) now catches the lattice disagreement. -/
def a0_lis_v2 : ConcordanceWindow := ⟨199, 60, 86⟩
theorem a0_lis_v2_refused : refused a0_lis_v2 := by decide

/-- Li2S a0 under the same v2 window: concordant — the tightened gate still
    separates known-good from speculative. -/
def a0_li2s_v2 : ConcordanceWindow := ⟨50, 60, 86⟩
theorem a0_li2s_v2_concordant : concordant a0_li2s_v2 := by decide

/-- LiS C12 under v2: refused on C12's own baseline. -/
def c12_lis_v2 : ConcordanceWindow := ⟨12400, 5703, 10589⟩
theorem c12_lis_v2_refused : refused c12_lis_v2 := by decide

/-- Ensemble hull of the four models' LiS elastic predictions (GPa x10000):
    component-wise min/max over chgnet, mace-mp-small, mace-mp-medium,
    mace-mpa-0-medium (values from Certificates_LiS_Demo). -/
def lisHull : ElasticHull :=
  { c11min := 599094, c11max := 1200015
  , c12min := 158064, c12max := 646638
  , c44min := -384317, c44max := -70627 }

/-- Every model's LiS prediction lies in the hull (spot-checked here for the
    extreme members; the hull is their component-wise envelope). -/
theorem lis_chgnet_in_hull : memHull elastic_lis_chgnet lisHull := by decide
theorem lis_mace_mpa_0_in_hull : memHull elastic_lis_mace_mpa_0_medium lisHull := by decide

/-- Ensemble-hull Born refusal: even the LARGEST C44 any model predicts for
    rocksalt LiS is negative (-7.1 GPa), so EVERY elastic tensor in the
    ensemble hull is Born-unstable — the refusal covers the whole ensemble
    range, not just the four sampled models. Four per-model refusals become
    one impossibility certificate. -/
theorem lis_hull_born_refused :
    ∀ e : CubicElastic, memHull e lisHull → ¬ bornStable e :=
  hull_born_refusal_c44 lisHull (by decide)

/-! ## Early-stop justification

    The runner skipped LiS's dynamic-return probe (the most expensive gate)
    under gate order early-stop. That skip is sound because refusal is
    final: the concordance refusals above are kernel-checked facts about
    the measured dispersions, and `orderJustified`-style finality means no
    later gate can overturn them. Wall time on the li-s panel: 94.9 s
    (legacy) -> 55.0 s (early-stop), a 42% cut with identical verdicts. -/

end Lupine.Discovery.LiSV2
