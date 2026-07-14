import OpenDistillationFactory.Materials.Theory.UniversalCorrection.Gate

/-!
# Deterministic distributed decision aggregation

MPI ranks and accelerator workers may reduce local observations in different
orders.  The scientific severity reduction is therefore an explicit
commutative idempotent semigroup: refusal dominates indeterminacy, which
dominates admission.  Witness serialization can be layered on top using a
canonical atom ordering without changing this decision algebra.
-/

namespace OpenDistillationFactory.Materials.Theory.UniversalCorrection

/-- Scientific severity, ordered from safe to fail-closed. -/
inductive Severity where
  | admit
  | indeterminate
  | refuse
  deriving DecidableEq, Repr

namespace Severity

/-- Dominating severity used by distributed reductions. -/
def join : Severity → Severity → Severity
  | .refuse, _ => .refuse
  | _, .refuse => .refuse
  | .indeterminate, _ => .indeterminate
  | _, .indeterminate => .indeterminate
  | .admit, .admit => .admit

@[simp] theorem join_admit_left (severity : Severity) :
    join .admit severity = severity := by
  cases severity <;> rfl

@[simp] theorem join_admit_right (severity : Severity) :
    join severity .admit = severity := by
  cases severity <;> rfl

theorem join_comm (left right : Severity) :
    join left right = join right left := by
  cases left <;> cases right <;> rfl

theorem join_assoc (first second third : Severity) :
    join (join first second) third = join first (join second third) := by
  cases first <;> cases second <;> cases third <;> rfl

theorem join_idem (severity : Severity) :
    join severity severity = severity := by
  cases severity <;> rfl

@[simp] theorem join_eq_admit_iff (left right : Severity) :
    join left right = .admit ↔ left = .admit ∧ right = .admit := by
  cases left <;> cases right <;> simp [join]

/-- Order-independent reduction of a finite set of local severities. -/
def aggregate : List Severity → Severity :=
  List.foldr join .admit

@[simp] theorem aggregate_nil : aggregate [] = .admit := rfl

@[simp] theorem aggregate_cons (head : Severity) (tail : List Severity) :
    aggregate (head :: tail) = join head (aggregate tail) := rfl

/-- Global admission holds exactly when every local result admits. -/
theorem aggregate_eq_admit_iff (severities : List Severity) :
    aggregate severities = .admit ↔ ∀ severity ∈ severities, severity = .admit := by
  induction severities with
  | nil => simp [aggregate]
  | cons head tail ih =>
      rw [aggregate_cons, join_eq_admit_iff, ih]
      constructor
      · rintro ⟨hhead, htail⟩ severity hmem
        rcases List.mem_cons.mp hmem with rfl | hmem
        · exact hhead
        · exact htail severity hmem
      · intro hall
        exact ⟨hall head (List.mem_cons_self), fun severity hmem =>
          hall severity (List.mem_cons_of_mem head hmem)⟩

/-- Reordering local results cannot change the global scientific decision. -/
theorem aggregate_eq_of_perm {left right : List Severity}
    (hperm : left.Perm right) : aggregate left = aggregate right := by
  induction hperm with
  | nil => rfl
  | cons head _ ih =>
      rw [aggregate_cons, aggregate_cons, ih]
  | swap first second tail =>
      simp only [aggregate_cons]
      calc
        join second (join first (aggregate tail)) =
            join (join second first) (aggregate tail) :=
          (join_assoc second first (aggregate tail)).symm
        _ = join (join first second) (aggregate tail) := by
          rw [join_comm second first]
        _ = join first (join second (aggregate tail)) :=
          join_assoc first second (aggregate tail)
  | trans _ _ ih₁ ih₂ => exact ih₁.trans ih₂

end Severity

/-- Forget witnesses only for the purpose of the distributed severity join. -/
def GateDecision.severity : GateDecision Violation Reason → Severity
  | .admit => .admit
  | .refuse _ => .refuse
  | .indeterminate _ => .indeterminate

@[simp] theorem GateDecision.severity_admit :
    (GateDecision.admit : GateDecision Violation Reason).severity = .admit := rfl

@[simp] theorem GateDecision.severity_refuse (witness : Violation) :
    (GateDecision.refuse witness : GateDecision Violation Reason).severity = .refuse := rfl

@[simp] theorem GateDecision.severity_indeterminate (reason : Reason) :
    (GateDecision.indeterminate reason : GateDecision Violation Reason).severity =
      .indeterminate := rfl

end OpenDistillationFactory.Materials.Theory.UniversalCorrection
