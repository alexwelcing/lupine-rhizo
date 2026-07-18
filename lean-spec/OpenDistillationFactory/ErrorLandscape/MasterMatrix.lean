import OpenDistillationFactory.ErrorLandscape.Emblems

namespace OpenDistillationFactory.ErrorLandscape

/-- One row of Chapter 13's partitioned master error map. Empty cells are
represented by `none`, so closure and validation gaps cannot be laundered into
prediction errors. -/
structure MasterMatrixRow where
  className : String
  classChapters : List Nat
  discoveryChains : List Nat
  classification : ErrorClassification
  predictionError : Option QuantifiedMagnitude
  closureGap : Option QuantifiedMagnitude
  validationOrObservabilityGap : Option QuantifiedMagnitude
  source : SourceCitation
  readiness : Readiness
  correction : CorrectionLever
  deriving Repr, DecidableEq, BEq

namespace MasterMatrixRow

/-- Executable witness that the row's typed tag list is nonempty. The list is
constructed with the binding type at its head by `ErrorClassification.tags`. -/
def hasTypedClassification (row : MasterMatrixRow) : Bool :=
  !row.classification.tags.isEmpty

@[simp] theorem hasTypedClassification_eq_true (row : MasterMatrixRow) :
    row.hasTypedClassification = true := by
  simp [hasTypedClassification, ErrorClassification.tags]

end MasterMatrixRow

private def q (headline : String) (quantities : List Quantity) : QuantifiedMagnitude :=
  { headline := headline, quantities := quantities }

private def chapter13Source (location : String) (markers : List Nat) : SourceCitation :=
  { chapter := 13, location := location, markers := markers,
    verifiedAsOf := some "2026-07-17" }

/-- Table 13.1 batteries row. -/
def batteriesRow : MasterMatrixRow :=
  { className := "Batteries"
    classChapters := [7]
    discoveryChains := [1]
    classification := { primary := .T2, secondary := [.T3] }
    predictionError := some <| q "Barrier MAE 0.310–0.349 eV across 574 DFT-NEB paths" [
      { label := "barrier MAE", value := "0.310–0.349", unit := "eV" },
      { label := "reference floor", value := "~60", unit := "meV" },
      { label := "CHGNet underestimation", value := "73.1", unit := "%" },
      { label := "M3GNet underestimation", value := "78.2", unit := "%" }]
    closureGap := none
    validationOrObservabilityGap := some <| q "Seventeen shared >1 eV outliers inflate every model's MAE" [
      { label := "shared outliers", value := "17", unit := "paths" },
      { label := "outlier-removed MAE", value := "0.239–0.290", unit := "eV" }]
    source := chapter13Source "Table 13.1, batteries" [5, 6]
    readiness := .medium
    correction := barriers.correction }

/-- Table 13.1 magnets row. -/
def magnetsRow : MasterMatrixRow :=
  { className := "Magnets"
    classChapters := [9]
    discoveryChains := [2]
    classification := { primary := .T1, secondary := [.T2, .T5] }
    predictionError := some <| q "Curie-temperature errors have 15–35% non-systematic sign" [
      { label := "Tc error band", value := "15–35", unit := "%" },
      { label := "Fe2B bias", value := "+35", unit := "%" },
      { label := "Co2B underestimate", value := "1.5", unit := "×" }]
    closureGap := some <| q "Continuum micromagnetics overestimates coercivity without grain-boundary chemistry" [
      { label := "coercivity overestimate", value := "~5", unit := "×" }]
    validationOrObservabilityGap := none
    source := chapter13Source "Table 13.1, magnets" [1, 16, 17]
    readiness := .medium
    correction := magnetism.correction }

/-- Table 13.1 catalysts row. -/
def catalystsRow : MasterMatrixRow :=
  { className := "Catalysts"
    classChapters := [8]
    discoveryChains := [3]
    classification := { primary := .T1, secondary := [.T7] }
    predictionError := some <| q "GGA adsorption errors are 0.2–0.4 eV against 39 experiments" [
      { label := "GGA adsorption error", value := "0.2–0.4", unit := "eV" },
      { label := "experimental energies", value := "39", unit := "energies" },
      { label := "RPA deviation", value := "~0.2", unit := "eV" }]
    closureGap := none
    validationOrObservabilityGap := some <| q "OC20 reconstructions create a dataset/reference-consistency gap" [
      { label := "reconstructed relaxations", value := "22", unit := "%" },
      { label := "MAE reduction after exclusion", value := "~35–39", unit := "%" },
      { label := "GemNet-OC MAE", value := "0.248→0.160", unit := "eV" }]
    source := chapter13Source "Table 13.1, catalysts" [1, 2, 75]
    readiness := .medium
    correction :=
      { name := "Multi-fidelity reference and consistency filtering"
        intervention := "Use Δ-learning for higher-fidelity labels and exclude reconstructed anomalies under a declared protocol"
        evidence := "Mechanism demonstrated on Si/water; OC20 filtering reduces MAE without retraining" } }

/-- Table 13.1 HEAs and disorder row. -/
def heasRow : MasterMatrixRow :=
  { className := "HEAs and disorder"
    classChapters := [6]
    discoveryChains := [4]
    classification := { primary := .T3, secondary := [.T2] }
    predictionError := some <| q "MS25 architectures miss the usability threshold by four to five times" [
      { label := "threshold miss", value := "4–5", unit := "×" },
      { label := "threshold", value := "2.5", unit := "meV/atom" },
      { label := "MTP force error", value := "189", unit := "meV/Å" },
      { label := "HEA25S zero-shot energy error", value := "617.9", unit := "meV/atom" },
      { label := "fine-tuned energy error", value := "3.5", unit := "meV/atom" }]
    closureGap := none
    validationOrObservabilityGap := none
    source := chapter13Source "Table 13.1, HEAs and disorder" [7, 8]
    readiness := .medium
    correction := coverage.correction }

/-- Table 13.1 frameworks and two-dimensional materials row. -/
def frameworksRow : MasterMatrixRow :=
  { className := "Frameworks and 2D"
    classChapters := [11]
    discoveryChains := [5]
    classification := { primary := .T1, secondary := [.T2, .T3, .T6] }
    predictionError := some <| q "Dispersion corrections scatter and framework transfer fails" [
      { label := "dispersion / RPA", value := "0.77–3.04", unit := "×" },
      { label := "CHA-to-MFI error inflation", value := "≥10", unit := "×" }]
    closureGap := none
    validationOrObservabilityGap := some <| q "No class-scale water-stability labels" [
      { label := "hydrolysis driving-force family split", value := "200–250", unit := "kJ/mol per metal" }]
    source := chapter13Source "Table 13.1, frameworks and 2D" [7, 19, 47]
    readiness := .medium
    correction := dispersion.correction }

/-- Table 13.1 semiconductors, perovskites, and thermoelectrics row. -/
def semiconductorsRow : MasterMatrixRow :=
  { className := "Semiconductors, perovskites, and thermoelectrics"
    classChapters := [12]
    discoveryChains := [6, 11]
    classification := { primary := .T1, secondary := [.T2] }
    predictionError := some <| q "Band-gap reference bias and missing thermal-transport physics" [
      { label := "LDA gap bias", value := "~50", unit := "% low" },
      { label := "Materials Project label bias", value := "~1.6", unit := "× low" },
      { label := "Pb-halide spin-orbit cancellation", value := "~1", unit := "eV" },
      { label := "BAs four-phonon theory", value := "~1400", unit := "W/m·K" },
      { label := "BAs measurement", value := "~2100–2200", unit := "W/m·K" }]
    closureGap := none
    validationOrObservabilityGap := none
    source := chapter13Source "Table 13.1, semiconductors/perovskites/thermoelectrics" [20, 21, 386, 392, 395]
    readiness := .medium
    correction := excitedStates.correction }

/-- Table 13.1 fusion-materials row. Its prediction cell is deliberately empty. -/
def fusionRow : MasterMatrixRow :=
  { className := "Fusion materials"
    classChapters := [10]
    discoveryChains := [7]
    classification := { primary := .T5, secondary := [.T6] }
    predictionError := none
    closureGap := some multiscaleClosure.magnitude
    validationOrObservabilityGap := some validationScarcity.magnitude
    source := chapter13Source "Table 13.1, fusion materials" [18, 335]
    readiness := .low
    correction := multiscaleClosure.correction }

/-- Table 13.1 superconductors row. -/
def superconductorsRow : MasterMatrixRow :=
  { className := "Superconductors"
    classChapters := [4]
    discoveryChains := [8]
    classification := { primary := .T1 }
    predictionError := some <| q "Harmonic treatment overstates coupling and hydride Tc" [
      { label := "harmonic lambda", value := "2.64", unit := "dimensionless" },
      { label := "anharmonic lambda", value := "1.84", unit := "dimensionless" },
      { label := "harmonic lambda bias", value := "~43", unit := "% high" },
      { label := "hydride Tc overshoot", value := "+10–15", unit := "%" }]
    closureGap := none
    validationOrObservabilityGap := none
    source := chapter13Source "Table 13.1, superconductors" [11, 12, 13, 132, 135]
    readiness := .low
    correction := strongCorrelation.correction }

/-- Table 13.1 correlated-oxides row. -/
def correlatedOxidesRow : MasterMatrixRow :=
  { className := "Correlated oxides"
    classChapters := [5]
    discoveryChains := [9]
    classification := { primary := .T1, secondary := [.T4] }
    predictionError := some <| q "Semilocal DFT metallizes Mott insulators and defect energies split across methods" [
      { label := "ZnO oxygen-vacancy HSE/DMC split", value := "~1", unit := "eV" },
      { label := "best-case NiO exchange RMS", value := "13", unit := "%" }]
    closureGap := none
    validationOrObservabilityGap := none
    source := chapter13Source "Table 13.1, correlated oxides" [15, 160, 166]
    readiness := .low
    correction := strongCorrelation.correction }

/-- Chapter 13, Table 13.1, in report order. -/
def masterMatrix : List MasterMatrixRow :=
  [batteriesRow, magnetsRow, catalystsRow, heasRow, frameworksRow,
   semiconductorsRow, fusionRow, superconductorsRow, correlatedOxidesRow]

@[simp] theorem masterMatrix_length : masterMatrix.length = 9 := by native_decide

theorem everyMasterRow_hasTypedClassification :
    masterMatrix.all MasterMatrixRow.hasTypedClassification = true := by native_decide

/-- Row-level lookup theorems make table position part of the checked interface. -/
theorem batteries_row : masterMatrix[0]? = some batteriesRow := by native_decide
theorem magnets_row : masterMatrix[1]? = some magnetsRow := by native_decide
theorem catalysts_row : masterMatrix[2]? = some catalystsRow := by native_decide
theorem heas_row : masterMatrix[3]? = some heasRow := by native_decide
theorem frameworks_row : masterMatrix[4]? = some frameworksRow := by native_decide
theorem semiconductors_row : masterMatrix[5]? = some semiconductorsRow := by native_decide
theorem fusion_row : masterMatrix[6]? = some fusionRow := by native_decide
theorem superconductors_row : masterMatrix[7]? = some superconductorsRow := by native_decide
theorem correlatedOxides_row : masterMatrix[8]? = some correlatedOxidesRow := by native_decide

/-- Chapter 13's honesty constraint: fusion has closure and validation entries,
but no prediction error that could be compared to an MAE. -/
theorem fusion_prediction_cell_is_empty : fusionRow.predictionError = none := rfl

end OpenDistillationFactory.ErrorLandscape
