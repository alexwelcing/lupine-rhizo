import OpenDistillationFactory.HonestErrors.Acceptance

/-!
# Sealed endpoint contracts

The hashes in this module are opaque commitments supplied by an external data
pipeline.  Lean does not calculate SHA-256.  It does make a result incapable of
passing unless its endpoint identifier, specification commitment, dataset seal,
and deadline status match a valid registered contract.

The ledger theorem is deliberately narrow: the defined `appendFollowOn`
operation preserves every earlier entry.  An externally released ledger hash can
make rewriting detectable, but cryptographic hashing and storage integrity remain
outside the kernel boundary.
-/

namespace OpenDistillationFactory.HonestErrors

structure DatasetSeal where
  corpusSha256 : String
  splitSha256 : String
  denominator : Nat
  deriving DecidableEq, Repr

/-- Minimal well-formedness required before a dataset seal can be accepted. -/
def DatasetSeal.Valid (datasetSeal : DatasetSeal) : Prop :=
  datasetSeal.corpusSha256 ≠ "" ∧
  datasetSeal.splitSha256 ≠ "" ∧
  0 < datasetSeal.denominator

instance (datasetSeal : DatasetSeal) : Decidable datasetSeal.Valid := by
  unfold DatasetSeal.Valid
  infer_instance

structure EndpointSpec (metric : Metric) (scope : AcceptanceScope) where
  endpointId : String
  /-- Commitment to the external contract containing comparator, threshold, and deadline. -/
  specSha256 : String
  claim : String
  dataset : DatasetSeal
  comparator : String
  threshold : Threshold metric scope
  deadlineDescription : String
  deriving DecidableEq, Repr

/-- Syntactic validity only; it does not authenticate or recompute either hash. -/
def EndpointSpec.Valid {metric : Metric} {scope : AcceptanceScope}
    (spec : EndpointSpec metric scope) : Prop :=
  spec.endpointId ≠ "" ∧
  spec.specSha256 ≠ "" ∧
  spec.claim ≠ "" ∧
  spec.dataset.Valid ∧
  spec.comparator ≠ "" ∧
  spec.deadlineDescription ≠ ""

instance {metric : Metric} {scope : AcceptanceScope}
    (spec : EndpointSpec metric scope) : Decidable spec.Valid := by
  unfold EndpointSpec.Valid
  infer_instance

structure EndpointResult (metric : Metric) (scope : AcceptanceScope) where
  endpointId : String
  specSha256 : String
  dataset : DatasetSeal
  observed : ScopedObservation metric scope
  deadlineMet : Bool
  deriving DecidableEq, Repr

inductive EndpointOutcome where
  | passed
  | failed
  | invalidSpecification
  | invalidEndpointBinding
  | invalidDataset
  | missedDeadline
  deriving DecidableEq, Repr

def decisionOutcome : Decision → EndpointOutcome
  | .pass => .passed
  | .fail => .failed

/-- Every identity-bearing field that must agree before threshold evaluation. -/
def EndpointBindingMatches {metric : Metric} {scope : AcceptanceScope}
    (spec : EndpointSpec metric scope)
    (result : EndpointResult metric scope) : Prop :=
  result.endpointId = spec.endpointId ∧
  result.specSha256 = spec.specSha256 ∧
  result.dataset = spec.dataset

def evaluateEndpoint {metric : Metric} {scope : AcceptanceScope}
    (spec : EndpointSpec metric scope)
    (result : EndpointResult metric scope) :
    EndpointOutcome :=
  if ¬ spec.Valid then
    .invalidSpecification
  else if result.endpointId ≠ spec.endpointId ∨
      result.specSha256 ≠ spec.specSha256 then
    .invalidEndpointBinding
  else if result.dataset ≠ spec.dataset then
    .invalidDataset
  else if result.deadlineMet = false then
    .missedDeadline
  else
    decisionOutcome (evaluate spec.threshold result.observed)

theorem evaluateEndpoint_pass_iff {metric : Metric} {scope : AcceptanceScope}
    (spec : EndpointSpec metric scope)
    (result : EndpointResult metric scope) :
    evaluateEndpoint spec result = .passed ↔
      spec.Valid ∧
      EndpointBindingMatches spec result ∧
      result.deadlineMet = true ∧
      evaluate spec.threshold result.observed = .pass := by
  by_cases hvalid : spec.Valid <;>
  by_cases hid : result.endpointId = spec.endpointId <;>
  by_cases hhash : result.specSha256 = spec.specSha256 <;>
  by_cases hdataset : result.dataset = spec.dataset <;>
  cases hdeadline : result.deadlineMet <;>
  cases hevaluation : evaluate spec.threshold result.observed <;>
  simp_all [evaluateEndpoint, EndpointBindingMatches, decisionOutcome]

theorem invalid_specification_cannot_pass
    {metric : Metric} {scope : AcceptanceScope}
    (spec : EndpointSpec metric scope)
    (result : EndpointResult metric scope)
    (hinvalid : ¬ spec.Valid) :
    evaluateEndpoint spec result = .invalidSpecification := by
  simp [evaluateEndpoint, hinvalid]

theorem endpoint_binding_mismatch_cannot_pass
    {metric : Metric} {scope : AcceptanceScope}
    (spec : EndpointSpec metric scope)
    (result : EndpointResult metric scope)
    (hmismatch : result.endpointId ≠ spec.endpointId ∨
      result.specSha256 ≠ spec.specSha256) :
    evaluateEndpoint spec result ≠ .passed := by
  intro hpass
  have hconditions := (evaluateEndpoint_pass_iff spec result).mp hpass
  rcases hconditions.2.1 with ⟨hid, hhash, _⟩
  exact hmismatch.elim (fun h => h hid) (fun h => h hhash)

theorem dataset_mismatch_cannot_pass
    {metric : Metric} {scope : AcceptanceScope}
    (spec : EndpointSpec metric scope)
    (result : EndpointResult metric scope)
    (hmismatch : result.dataset ≠ spec.dataset) :
    evaluateEndpoint spec result ≠ .passed := by
  intro hpass
  have hconditions := (evaluateEndpoint_pass_iff spec result).mp hpass
  exact hmismatch hconditions.2.1.2.2

theorem missed_deadline_cannot_pass
    {metric : Metric} {scope : AcceptanceScope}
    (spec : EndpointSpec metric scope)
    (result : EndpointResult metric scope)
    (hmissed : result.deadlineMet = false) :
    evaluateEndpoint spec result ≠ .passed := by
  intro hpass
  have hdeadline := (evaluateEndpoint_pass_iff spec result).mp hpass |>.2.2.1
  simp [hmissed] at hdeadline

theorem endpoint_pass_implies_contract_match
    {metric : Metric} {scope : AcceptanceScope}
    (spec : EndpointSpec metric scope)
    (result : EndpointResult metric scope)
    (hpass : evaluateEndpoint spec result = .passed) :
    spec.Valid ∧ EndpointBindingMatches spec result ∧
      result.deadlineMet = true := by
  rcases (evaluateEndpoint_pass_iff spec result).mp hpass with
    ⟨hvalid, hbinding, hdeadline, _⟩
  exact ⟨hvalid, hbinding, hdeadline⟩

structure AuditEntry where
  endpointId : String
  endpointSpecSha256 : String
  dataset : DatasetSeal
  outcome : EndpointOutcome
  evaluatedAt : String
  artifactSha256 : String
  deriving DecidableEq, Repr

/-- The only append operation certified by this module. -/
def appendFollowOn (ledger : List AuditEntry) (followOn : AuditEntry) :
    List AuditEntry :=
  ledger ++ [followOn]

/-- Under `appendFollowOn`, a later record cannot remove an earlier record. -/
theorem prior_entry_survives_append
    {entry : AuditEntry} (ledger : List AuditEntry)
    (hentry : entry ∈ ledger) (followOn : AuditEntry) :
    entry ∈ appendFollowOn ledger followOn := by
  exact List.mem_append.mpr (Or.inl hentry)

theorem append_follow_on_preserves_prefix
    (ledger : List AuditEntry) (followOn : AuditEntry) :
    (appendFollowOn ledger followOn).take ledger.length = ledger := by
  simp [appendFollowOn]

end OpenDistillationFactory.HonestErrors
