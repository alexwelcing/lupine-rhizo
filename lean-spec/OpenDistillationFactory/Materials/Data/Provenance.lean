namespace OpenDistillationFactory.Materials.Data

/-- Source of a benchmark data point.
    Distinguishes synthetic/hardcoded data from empirically derived data. -/
inductive DataSource
  | synthetic (rationale : String)
  | nistIpr (id : String) (doi : String)
  | lammps (inputHash : String) (command : String)
  | literature (citation : String) (page : Nat)
  deriving Repr, BEq

/-- Trust level assigned to a data source. -/
inductive TrustLevel
  | unverified
  | reproducible
  | peerReviewed
  | formallyVerified
  deriving Repr, BEq, Ord

/-- Provenance record for a single numeric value. -/
structure ValueProvenance where
  source : DataSource
  trust  : TrustLevel
  date   : String  -- ISO date, e.g. "2026-04-22"
  notes  : String
  deriving Repr, BEq

def syntheticProvenance (rationale : String) : ValueProvenance :=
  { source := DataSource.synthetic rationale
    trust  := TrustLevel.unverified
    date   := "unknown"
    notes  := "Hand-typed synthetic value with no empirical provenance" }

def nistProvenance (id : String) (doi : String) : ValueProvenance :=
  { source := DataSource.nistIpr id doi
    trust  := TrustLevel.reproducible
    date   := "unknown"
    notes  := "NIST Interatomic Potentials Repository entry" }

/-- Provenance for a value derived from an actual LAMMPS execution. -/
def experimentProvenance (inputHash command : String) : ValueProvenance :=
  { source := DataSource.lammps inputHash command
    trust  := TrustLevel.reproducible
    date   := "unknown"
    notes  := "Computed via LAMMPS with traceable input script and output log" }

/-- Check whether a dataset is NIST-backed (i.e., every point has NIST IPR provenance). -/
def isNistBacked (provenances : List ValueProvenance) : Bool :=
  provenances.all (λ p => match p.source with
    | DataSource.nistIpr _ _ => true
    | _ => false)

/-- Check whether a dataset is purely synthetic. -/
def isSynthetic (provenances : List ValueProvenance) : Bool :=
  provenances.all (λ p => match p.source with
    | DataSource.synthetic _ => true
    | _ => false)

/-- Check whether a dataset is experiment-backed (i.e., every point has LAMMPS provenance). -/
def isExperimentBacked (provenances : List ValueProvenance) : Bool :=
  provenances.all (λ p => match p.source with
    | DataSource.lammps _ _ => true
    | _ => false)

/-- Check whether a dataset is empirically grounded (NIST-backed OR experiment-backed).
    This is the predicate required for empirical claims. -/
def isEmpiricallyGrounded (provenances : List ValueProvenance) : Bool :=
  provenances.all (λ p => match p.source with
    | DataSource.nistIpr _ _ => true
    | DataSource.lammps _ _  => true
    | _ => false)

end OpenDistillationFactory.Materials.Data
