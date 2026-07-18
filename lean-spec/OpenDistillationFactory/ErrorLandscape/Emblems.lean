import OpenDistillationFactory.ErrorLandscape.Types

namespace OpenDistillationFactory.ErrorLandscape

/-- One of the nine quantitative emblems in §3.2.2. -/
structure Emblem where
  number : Nat
  name : String
  classification : ErrorClassification
  magnitude : QuantifiedMagnitude
  source : SourceCitation
  correction : CorrectionLever
  deriving Repr, DecidableEq, BEq

namespace Emblem

/-- Executable witness that the emblem's typed tag list is nonempty. The list
is constructed with the binding type at its head by `ErrorClassification.tags`. -/
def hasTypedClassification (emblem : Emblem) : Bool :=
  !emblem.classification.tags.isEmpty

@[simp] theorem hasTypedClassification_eq_true (emblem : Emblem) :
    emblem.hasTypedClassification = true := by
  simp [hasTypedClassification, ErrorClassification.tags]

end Emblem

private def chapter3Source (location : String) (markers : List Nat) : SourceCitation :=
  { chapter := 3, location := location, markers := markers,
    verifiedAsOf := some "2026-07-17" }

/-- E1: strong correlation and self-interaction. -/
def strongCorrelation : Emblem :=
  { number := 1
    name := "Strong correlation and self-interaction"
    classification := { primary := .T1, secondary := [.T2] }
    magnitude :=
      { headline := "Plain DFT predicts metallic La2CuO4 instead of the observed ~2 eV-gap insulator"
        quantities := [{ label := "experimental charge-transfer gap", value := "~2", unit := "eV" }] }
    source := chapter3Source "§3.2.2, Emblem 1" [12, 13, 14, 81, 82]
    correction :=
      { name := "Correlation-aware fidelity escalation"
        intervention := "Tune an experiment-anchored Hubbard U or escalate to cluster DMFT"
        evidence := "Cluster-DMFT was demonstrated for cuprates in 2025; no family-general unconventional-Tc method exists" } }

/-- E2: excited states and band gaps. -/
def excitedStates : Emblem :=
  { number := 2
    name := "Excited states and band gaps"
    classification := { primary := .T1 }
    magnitude :=
      { headline := "Spin-orbit coupling shifts Pb-halide gaps by ~1 eV while QSGW overestimates by 15%"
        quantities :=
          [{ label := "spin-orbit gap reduction", value := "~1", unit := "eV" },
           { label := "QSGW overestimate", value := "+15", unit := "%" }] }
    source := chapter3Source "§3.2.2, Emblem 2" [20, 21]
    correction :=
      { name := "Cancellation-free excited-state reference"
        intervention := "Escalate to a GW-level stack with spin-orbit terms explicit and anchor it to experiment"
        evidence := "The report treats apparent agreement from cancellation as non-transferable" } }

/-- E3: magnetic ordering and Curie-temperature prediction. -/
def magnetism : Emblem :=
  { number := 3
    name := "Magnetism"
    classification := { primary := .T1, secondary := [.T2] }
    magnitude :=
      { headline := "Mean-field Curie-temperature errors span 15–35% with non-systematic sign"
        quantities :=
          [{ label := "Fe2B overestimate", value := "~35", unit := "%" },
           { label := "Fe2B predicted / observed", value := "1570 / 1013", unit := "K" },
           { label := "Co2B underestimate factor", value := "1.5", unit := "×" }] }
    source := chapter3Source "§3.2.2, Emblem 3" [16, 83, 84]
    correction :=
      { name := "Spin-aware multi-fidelity modelling"
        intervention := "Use spin-aware MLIPs and experiment-anchored magnetic reference calculations"
        evidence := "Mechanism-level spin-aware potentials exist; screening-scale coercivity closure remains incomplete" } }

/-- E4: migration barriers and transition states. -/
def barriers : Emblem :=
  { number := 4
    name := "Barrier and transition-state error"
    classification := { primary := .T2, secondary := [.T3] }
    magnitude :=
      { headline := "Foundation-MLIP barrier MAE is 0.310–0.349 eV on 574 paths, five to six times the DFT-NEB floor"
        quantities :=
          [{ label := "paths", value := "574", unit := "paths" },
           { label := "barrier MAE", value := "0.310–0.349", unit := "eV" },
           { label := "DFT-NEB reference floor", value := "~60", unit := "meV" },
           { label := "CHGNet barriers underestimated", value := "73.1", unit := "%" },
           { label := "M3GNet barriers underestimated", value := "78.2", unit := "%" }] }
    source := chapter3Source "§3.2.2, Emblem 4" [5, 6, 7]
    correction :=
      { name := "Transition-state targeted fine-tuning and escalation"
        intervention := "Fine-tune on transition-state data, then send screened paths to DFT-NEB"
        evidence := "One Li chemistry improves test MAE from 0.23 to 0.09 eV; matched-budget cross-chemistry evidence is lacking" } }

/-- E5: softened potential-energy surfaces. -/
def pesSoftening : Emblem :=
  { number := 5
    name := "PES softening and finite-temperature error"
    classification := { primary := .T2 }
    magnitude :=
      { headline := "More than 90% of 229 PhononDB materials are softened; frequency MAE is 17–61 K"
        quantities :=
          [{ label := "softened materials", value := ">90", unit := "% of 229" },
           { label := "maximum-frequency MAE", value := "17–61", unit := "K" }] }
    source := chapter3Source "§3.2.2, Emblem 5" [23, 85, 86]
    correction :=
      { name := "Non-equilibrium data and micro-dose fine-tuning"
        intervention := "Add off-equilibrium structures, then apply scalar or full fine-tuning"
        evidence := "Reported force-MAE reductions are 11.9–16.4% for scalar and ~34% for ten-structure full fine-tuning" } }

/-- E6: dispersion and interlayer interactions. -/
def dispersion : Emblem :=
  { number := 6
    name := "Dispersion"
    classification := { primary := .T1, secondary := [.T3] }
    magnitude :=
      { headline := "vdW corrections span 0.77–3.04 times RPA interlayer energies"
        quantities :=
          [{ label := "vdW / RPA interlayer energy", value := "0.77–3.04", unit := "×" },
           { label := "MoS2 surface-energy span", value := "0.07–0.32", unit := "N/m" },
           { label := "WS2 convergence set", value := "~2000", unit := "frames" }] }
    source := chapter3Source "§3.2.2, Emblem 6" [19, 24, 87]
    correction :=
      { name := "Dispersion-fidelity escalation plus coverage"
        intervention := "Use RPA-quality anchors and train on explicit vdW configurations"
        evidence := "CHGNet requires about 2,000 frames to converge the WS2 interlayer gap" } }

/-- E7: composition and framework coverage. -/
def coverage : Emblem :=
  { number := 7
    name := "Composition- and framework-space coverage"
    classification := { primary := .T3 }
    magnitude :=
      { headline := "Five architectures miss a 2.5 meV/atom EAM target by four to five times"
        quantities :=
          [{ label := "energy error / usability threshold", value := "4–5", unit := "×" },
           { label := "usability threshold", value := "2.5", unit := "meV/atom" },
           { label := "MTP force error", value := "189", unit := "meV/Å" },
           { label := "CHA-to-MFI transfer inflation", value := "≥10", unit := "×" }] }
    source := chapter3Source "§3.2.2, Emblem 7" [7, 8]
    correction :=
      { name := "Composition- and framework-aware data"
        intervention := "Build per-family coverage sets and fine-tune within each target family"
        evidence := "HEA25S fine-tuning reaches 3.5 meV/atom and 85 meV/Å but loses held-out generality" } }

/-- E8: atomistic-to-service-life closure. -/
def multiscaleClosure : Emblem :=
  { number := 8
    name := "Multiscale closure"
    classification := { primary := .T5 }
    magnitude :=
      { headline := "An 8.1-million-atom, 240 ps cascade remains over 15 orders short of five-year service"
        quantities :=
          [{ label := "cascade size", value := "8.1 million", unit := "atoms" },
           { label := "cascade duration", value := "240", unit := "ps" },
           { label := "service life", value := "5", unit := "years" },
           { label := "timescale gap", value := ">15", unit := "orders of magnitude" }] }
    source := chapter3Source "§3.2.2, Emblem 8" [18, 88]
    correction :=
      { name := "Uncertainty-carrying scale hand-off"
        intervention := "Validate cascade-to-OKMC-to-rate-theory closure with uncertainty on every inherited source term"
        evidence := "The report identifies this as a missing capability rather than a demonstrated fix" } }

/-- E9: fusion-spectrum validation data. -/
def validationScarcity : Emblem :=
  { number := 9
    name := "Validation-data scarcity"
    classification := { primary := .T6 }
    magnitude :=
      { headline := "Qualified RAFM data end near 20 dpa while DEMO's second blanket requires 50 dpa"
        quantities :=
          [{ label := "qualified dose", value := "~20", unit := "dpa" },
           { label := "second-blanket requirement", value := "50", unit := "dpa" },
           { label := "fusion helium production", value := "11–14", unit := "appm He/dpa" }] }
    source := chapter3Source "§3.2.2, Emblem 9" [10, 89]
    correction :=
      { name := "Qualified fusion-spectrum validation"
        intervention := "Create new irradiation facilities and operando measurements at the required dose and He/dpa"
        evidence := "No model improvement can replace the absent application-relevant validation record" } }

/-- Chapter 3's nine emblems, in report order. -/
def allEmblems : List Emblem :=
  [strongCorrelation, excitedStates, magnetism, barriers, pesSoftening,
   dispersion, coverage, multiscaleClosure, validationScarcity]

@[simp] theorem allEmblems_length : allEmblems.length = 9 := by native_decide

theorem everyEmblem_hasTypedClassification :
    allEmblems.all Emblem.hasTypedClassification = true := by native_decide

end OpenDistillationFactory.ErrorLandscape
