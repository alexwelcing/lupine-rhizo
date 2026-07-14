//! Composite runtime contract mirrored by Lean `UniversalCorrection.RuntimeContract`.
//!
//! Scope and numeric identities are checked before interval structure,
//! implementation support, and precision. That precedence is part of the
//! certificate semantics and must remain deterministic across deployments.

use serde::{Deserialize, Serialize};

use super::gate::{CertificateValidationError, FixedEnvelope};

pub const CURRENT_NUMERIC_SCHEMA_VERSION: u64 = 1;
pub const RUNTIME_CONTRACT_CERTIFICATE_SCHEMA: &str =
    "lupine.universal_correction.runtime_contract_certificate.v1";

const ADMIT_THEOREM: &str = "OpenDistillationFactory.Materials.Theory.\
UniversalCorrection.checkRuntimeContract_admit_iff";
const INCOMPATIBLE_THEOREM: &str = "OpenDistillationFactory.Materials.Theory.\
UniversalCorrection.checkRuntimeContract_incompatible_iff";
const INCONSISTENT_THEOREM: &str = "OpenDistillationFactory.Materials.Theory.\
UniversalCorrection.checkRuntimeContract_inconsistent_iff";
const UNSUPPORTED_SCHEMA_THEOREM: &str = "OpenDistillationFactory.Materials.Theory.\
UniversalCorrection.checkRuntimeContract_unsupportedSchema_iff";
const UNSUPPORTED_ROUNDING_THEOREM: &str = "OpenDistillationFactory.Materials.Theory.\
UniversalCorrection.checkRuntimeContract_unsupportedRounding_iff";
const WIDTH_TOO_LARGE_THEOREM: &str = "OpenDistillationFactory.Materials.Theory.\
UniversalCorrection.checkRuntimeContract_widthTooLarge_iff";
const FAIL_CLOSED_THEOREM: &str = "OpenDistillationFactory.Materials.Theory.\
UniversalCorrection.correctionAllowed_checkRuntimeContract_iff";

/// Versioned, content-addressed computational artifact.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ArtifactId {
    pub name: String,
    pub version: String,
    pub digest: String,
}

/// Molecular context that fixes the meaning of the observable.
///
/// Species ordering is retained exactly, matching Lean's `List String`.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct MolecularContext {
    pub species: Vec<String>,
    pub charge: i64,
    pub spin_convention: String,
    pub boundary_conditions: String,
}

/// Identity of the environment representation and metric convention.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct DescriptorId {
    pub artifact: ArtifactId,
    pub metric_convention: String,
}

/// Full structural mirror of Lean's strict scientific `Scope` identity.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ScopeIdentity {
    pub model: ArtifactId,
    pub reference: ArtifactId,
    pub observable: String,
    pub context: MolecularContext,
    pub descriptor: DescriptorId,
    pub units: String,
    pub numeric_semantics: String,
}

/// Declared rounding behavior of an encoded fixed-point payload.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum RoundingConvention {
    Outward,
    Nearest,
    TowardZero,
}

/// Exact interpretation of fixed-point integer payloads.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct NumericContract {
    pub schema_version: u64,
    pub scale: u64,
    pub units: String,
    pub semantics: String,
    pub rounding: RoundingConvention,
}

impl NumericContract {
    pub fn is_well_formed(&self) -> bool {
        self.scale > 0
    }

    pub fn is_supported(&self) -> bool {
        self.schema_version == CURRENT_NUMERIC_SCHEMA_VERSION
            && self.rounding == RoundingConvention::Outward
    }

    pub fn is_scope_compatible(&self, scope: &ScopeIdentity) -> bool {
        self.units == scope.units && self.semantics == scope.numeric_semantics
    }
}

/// Immutable expectations for one runtime correction decision.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct RuntimePolicy {
    pub scope: ScopeIdentity,
    pub numeric: NumericContract,
    pub tolerance: u64,
}

/// Complete exact payload presented at the runtime boundary.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct FixedMeasurement {
    pub scope: ScopeIdentity,
    pub numeric: NumericContract,
    pub envelope: FixedEnvelope,
}

impl RuntimePolicy {
    /// Strict compatibility predicate mirrored by Lean
    /// `RuntimePolicy.ContractCompatible`.
    pub fn is_contract_compatible(&self, evidence: &FixedMeasurement) -> bool {
        self.scope == evidence.scope
            && self.numeric == evidence.numeric
            && self.numeric.is_scope_compatible(&self.scope)
            && self.numeric.is_well_formed()
    }

    /// Complete admission predicate mirrored by Lean
    /// `RuntimePolicy.Admissible`.
    pub fn is_admissible(&self, evidence: &FixedMeasurement) -> bool {
        self.is_contract_compatible(evidence)
            && evidence.envelope.ordered_width().is_some()
            && self.numeric.is_supported()
            && evidence
                .envelope
                .ordered_width()
                .is_some_and(|width| width <= u128::from(self.tolerance))
    }
}

/// Definite contradictions that invalidate the serialized contract.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum RuntimeViolation {
    IncompatibleContract,
    InconsistentEnvelope,
}

/// Non-false inputs that the current checker cannot authorize.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum RuntimeReason {
    UnsupportedSchema,
    UnsupportedRounding,
    WidthTooLarge,
}

/// Three-valued result of the composite runtime reference monitor.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(tag = "decision", rename_all = "snake_case")]
pub enum RuntimeGateDecision {
    Admit,
    Refuse { violation: RuntimeViolation },
    Indeterminate { reason: RuntimeReason },
}

impl RuntimeGateDecision {
    pub const fn correction_allowed(self) -> bool {
        matches!(self, Self::Admit)
    }

    fn theorem_references(self) -> [&'static str; 2] {
        let outcome = match self {
            Self::Admit => ADMIT_THEOREM,
            Self::Refuse {
                violation: RuntimeViolation::IncompatibleContract,
            } => INCOMPATIBLE_THEOREM,
            Self::Refuse {
                violation: RuntimeViolation::InconsistentEnvelope,
            } => INCONSISTENT_THEOREM,
            Self::Indeterminate {
                reason: RuntimeReason::UnsupportedSchema,
            } => UNSUPPORTED_SCHEMA_THEOREM,
            Self::Indeterminate {
                reason: RuntimeReason::UnsupportedRounding,
            } => UNSUPPORTED_ROUNDING_THEOREM,
            Self::Indeterminate {
                reason: RuntimeReason::WidthTooLarge,
            } => WIDTH_TOO_LARGE_THEOREM,
        };
        [outcome, FAIL_CLOSED_THEOREM]
    }
}

/// Self-contained, serde-compatible certificate for one composite decision.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct RuntimeContractCertificate {
    pub schema: String,
    pub policy: RuntimePolicy,
    pub evidence: FixedMeasurement,
    #[serde(flatten)]
    pub result: RuntimeGateDecision,
    pub correction_allowed: bool,
    pub theorem_references: Vec<String>,
}

impl RuntimeContractCertificate {
    /// Re-run the composite checker and validate every derived field.
    pub fn validate(&self) -> Result<(), CertificateValidationError> {
        if self.schema != RUNTIME_CONTRACT_CERTIFICATE_SCHEMA {
            return Err(CertificateValidationError::Schema {
                expected: RUNTIME_CONTRACT_CERTIFICATE_SCHEMA.to_owned(),
                actual: self.schema.clone(),
            });
        }

        let expected_result = check_runtime_contract(&self.policy, &self.evidence);
        if self.result != expected_result {
            return Err(CertificateValidationError::Result);
        }

        let expected_allowed = expected_result.correction_allowed();
        if self.correction_allowed != expected_allowed {
            return Err(CertificateValidationError::CorrectionAllowed {
                expected: expected_allowed,
                actual: self.correction_allowed,
            });
        }

        let expected_references = expected_result
            .theorem_references()
            .into_iter()
            .map(str::to_owned)
            .collect::<Vec<_>>();
        if self.theorem_references != expected_references {
            return Err(CertificateValidationError::TheoremReferences {
                expected: expected_references,
                actual: self.theorem_references.clone(),
            });
        }

        Ok(())
    }

    /// Alias emphasizing that deserialized certificates are untrusted input.
    pub fn verify(&self) -> Result<(), CertificateValidationError> {
        self.validate()
    }
}

/// Exact composite checker with the same outcome precedence as Lean:
/// contract, interval ordering, schema, rounding, then width.
pub fn check_runtime_contract(
    policy: &RuntimePolicy,
    evidence: &FixedMeasurement,
) -> RuntimeGateDecision {
    if !policy.is_contract_compatible(evidence) {
        return RuntimeGateDecision::Refuse {
            violation: RuntimeViolation::IncompatibleContract,
        };
    }

    let Some(width) = evidence.envelope.ordered_width() else {
        return RuntimeGateDecision::Refuse {
            violation: RuntimeViolation::InconsistentEnvelope,
        };
    };

    if policy.numeric.schema_version != CURRENT_NUMERIC_SCHEMA_VERSION {
        return RuntimeGateDecision::Indeterminate {
            reason: RuntimeReason::UnsupportedSchema,
        };
    }

    if policy.numeric.rounding != RoundingConvention::Outward {
        return RuntimeGateDecision::Indeterminate {
            reason: RuntimeReason::UnsupportedRounding,
        };
    }

    if u128::from(policy.tolerance) < width {
        RuntimeGateDecision::Indeterminate {
            reason: RuntimeReason::WidthTooLarge,
        }
    } else {
        RuntimeGateDecision::Admit
    }
}

/// Evaluate the runtime contract and retain the exact policy and evidence.
pub fn certify_runtime_contract(
    policy: RuntimePolicy,
    evidence: FixedMeasurement,
) -> RuntimeContractCertificate {
    let result = check_runtime_contract(&policy, &evidence);
    RuntimeContractCertificate {
        schema: RUNTIME_CONTRACT_CERTIFICATE_SCHEMA.to_owned(),
        policy,
        evidence,
        correction_allowed: result.correction_allowed(),
        theorem_references: result
            .theorem_references()
            .into_iter()
            .map(str::to_owned)
            .collect(),
        result,
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    fn artifact(name: &str, digest: &str) -> ArtifactId {
        ArtifactId {
            name: name.to_owned(),
            version: "1".to_owned(),
            digest: digest.to_owned(),
        }
    }

    fn scope() -> ScopeIdentity {
        ScopeIdentity {
            model: artifact("fixture-model", "sha256:fixture-model"),
            reference: artifact("fixture-reference", "sha256:fixture-reference"),
            observable: "total-energy".to_owned(),
            context: MolecularContext {
                species: vec!["H".to_owned(), "H".to_owned()],
                charge: 0,
                spin_convention: "singlet".to_owned(),
                boundary_conditions: "isolated".to_owned(),
            },
            descriptor: DescriptorId {
                artifact: artifact("fixture-descriptor", "sha256:fixture-descriptor"),
                metric_convention: "discrete-v1".to_owned(),
            },
            units: "eV".to_owned(),
            numeric_semantics: "exact-fixed-point-v1".to_owned(),
        }
    }

    fn numeric() -> NumericContract {
        NumericContract {
            schema_version: CURRENT_NUMERIC_SCHEMA_VERSION,
            scale: 1000,
            units: "eV".to_owned(),
            semantics: "exact-fixed-point-v1".to_owned(),
            rounding: RoundingConvention::Outward,
        }
    }

    fn policy() -> RuntimePolicy {
        RuntimePolicy {
            scope: scope(),
            numeric: numeric(),
            tolerance: 5,
        }
    }

    fn evidence(lower: i64, upper: i64) -> FixedMeasurement {
        FixedMeasurement {
            scope: scope(),
            numeric: numeric(),
            envelope: FixedEnvelope { lower, upper },
        }
    }

    #[test]
    fn matches_every_lean_runtime_outcome() {
        let policy = policy();

        assert_eq!(
            check_runtime_contract(&policy, &evidence(100, 104)),
            RuntimeGateDecision::Admit
        );

        let mut incompatible = evidence(100, 104);
        incompatible.scope.model.digest = "sha256:different-model".to_owned();
        assert_eq!(
            check_runtime_contract(&policy, &incompatible),
            RuntimeGateDecision::Refuse {
                violation: RuntimeViolation::IncompatibleContract,
            }
        );

        assert_eq!(
            check_runtime_contract(&policy, &evidence(105, 104)),
            RuntimeGateDecision::Refuse {
                violation: RuntimeViolation::InconsistentEnvelope,
            }
        );

        let mut unsupported_schema_policy = policy.clone();
        unsupported_schema_policy.numeric.schema_version = 2;
        let mut unsupported_schema_evidence = evidence(100, 104);
        unsupported_schema_evidence.numeric.schema_version = 2;
        assert_eq!(
            check_runtime_contract(&unsupported_schema_policy, &unsupported_schema_evidence),
            RuntimeGateDecision::Indeterminate {
                reason: RuntimeReason::UnsupportedSchema,
            }
        );

        let mut unsupported_rounding_policy = policy.clone();
        unsupported_rounding_policy.numeric.rounding = RoundingConvention::Nearest;
        let mut unsupported_rounding_evidence = evidence(100, 104);
        unsupported_rounding_evidence.numeric.rounding = RoundingConvention::Nearest;
        assert_eq!(
            check_runtime_contract(&unsupported_rounding_policy, &unsupported_rounding_evidence),
            RuntimeGateDecision::Indeterminate {
                reason: RuntimeReason::UnsupportedRounding,
            }
        );

        assert_eq!(
            check_runtime_contract(&policy, &evidence(100, 110)),
            RuntimeGateDecision::Indeterminate {
                reason: RuntimeReason::WidthTooLarge,
            }
        );
    }

    #[test]
    fn contract_compatibility_checks_every_identity_field() {
        let policy = policy();

        let mut numeric_mismatch = evidence(100, 104);
        numeric_mismatch.numeric.scale = 2000;
        assert!(!policy.is_contract_compatible(&numeric_mismatch));

        let mut unit_mismatch_policy = policy.clone();
        unit_mismatch_policy.scope.units = "hartree".to_owned();
        let unit_mismatch_evidence = FixedMeasurement {
            scope: unit_mismatch_policy.scope.clone(),
            numeric: unit_mismatch_policy.numeric.clone(),
            envelope: FixedEnvelope {
                lower: 100,
                upper: 104,
            },
        };
        assert!(!unit_mismatch_policy.is_contract_compatible(&unit_mismatch_evidence));

        let mut zero_scale_policy = policy.clone();
        zero_scale_policy.numeric.scale = 0;
        let mut zero_scale_evidence = evidence(100, 104);
        zero_scale_evidence.numeric.scale = 0;
        assert!(!zero_scale_policy.is_contract_compatible(&zero_scale_evidence));

        let mut semantics_mismatch_policy = policy.clone();
        semantics_mismatch_policy.scope.numeric_semantics = "different-semantics".to_owned();
        let semantics_mismatch_evidence = FixedMeasurement {
            scope: semantics_mismatch_policy.scope.clone(),
            numeric: semantics_mismatch_policy.numeric.clone(),
            envelope: FixedEnvelope {
                lower: 100,
                upper: 104,
            },
        };
        assert!(!semantics_mismatch_policy.is_contract_compatible(&semantics_mismatch_evidence));
    }

    #[test]
    fn structural_scope_equality_is_strict() {
        let base_policy = policy();
        let mut mutations = Vec::new();

        let mut changed = evidence(100, 104);
        changed.scope.model.digest = "sha256:other-model".to_owned();
        mutations.push(changed);

        let mut changed = evidence(100, 104);
        changed.scope.reference.version = "2".to_owned();
        mutations.push(changed);

        let mut changed = evidence(100, 104);
        changed.scope.observable = "forces".to_owned();
        mutations.push(changed);

        let mut changed = evidence(100, 104);
        changed.scope.context.species = vec!["He".to_owned(), "H".to_owned()];
        mutations.push(changed);

        let mut changed = evidence(100, 104);
        changed.scope.context.charge = 1;
        mutations.push(changed);

        let mut changed = evidence(100, 104);
        changed.scope.context.spin_convention = "triplet".to_owned();
        mutations.push(changed);

        let mut changed = evidence(100, 104);
        changed.scope.context.boundary_conditions = "periodic".to_owned();
        mutations.push(changed);

        let mut changed = evidence(100, 104);
        changed.scope.descriptor.artifact.digest = "sha256:other-descriptor".to_owned();
        mutations.push(changed);

        let mut changed = evidence(100, 104);
        changed.scope.descriptor.metric_convention = "other-metric".to_owned();
        mutations.push(changed);

        let mut changed = evidence(100, 104);
        changed.scope.units = "hartree".to_owned();
        mutations.push(changed);

        let mut changed = evidence(100, 104);
        changed.scope.numeric_semantics = "other-semantics".to_owned();
        mutations.push(changed);

        assert!(mutations
            .iter()
            .all(|measurement| !base_policy.is_contract_compatible(measurement)));

        let mut ordered_policy = policy();
        ordered_policy.scope.context.species = vec!["H".to_owned(), "He".to_owned()];
        let mut reordered = evidence(100, 104);
        reordered.scope = ordered_policy.scope.clone();
        reordered.scope.context.species.reverse();
        assert!(!ordered_policy.is_contract_compatible(&reordered));
    }

    #[test]
    fn outcome_precedence_matches_lean() {
        let mut incompatible = evidence(105, 104);
        incompatible.scope.model.digest = "sha256:different-model".to_owned();
        assert_eq!(
            check_runtime_contract(&policy(), &incompatible),
            RuntimeGateDecision::Refuse {
                violation: RuntimeViolation::IncompatibleContract,
            }
        );

        let mut unsupported_policy = policy();
        unsupported_policy.numeric.schema_version = 2;
        unsupported_policy.numeric.rounding = RoundingConvention::Nearest;
        let mut inverted = evidence(105, 104);
        inverted.numeric = unsupported_policy.numeric.clone();
        assert_eq!(
            check_runtime_contract(&unsupported_policy, &inverted),
            RuntimeGateDecision::Refuse {
                violation: RuntimeViolation::InconsistentEnvelope,
            }
        );

        let mut unsupported_evidence = evidence(100, 110);
        unsupported_evidence.numeric = unsupported_policy.numeric.clone();
        assert_eq!(
            check_runtime_contract(&unsupported_policy, &unsupported_evidence),
            RuntimeGateDecision::Indeterminate {
                reason: RuntimeReason::UnsupportedSchema,
            }
        );

        unsupported_policy.numeric.schema_version = CURRENT_NUMERIC_SCHEMA_VERSION;
        unsupported_evidence.numeric.schema_version = CURRENT_NUMERIC_SCHEMA_VERSION;
        assert_eq!(
            check_runtime_contract(&unsupported_policy, &unsupported_evidence),
            RuntimeGateDecision::Indeterminate {
                reason: RuntimeReason::UnsupportedRounding,
            }
        );
    }

    #[test]
    fn correction_authorization_is_fail_closed_for_every_non_admit_outcome() {
        let policy = policy();
        let mut outcomes = vec![
            check_runtime_contract(&policy, &evidence(105, 104)),
            check_runtime_contract(&policy, &evidence(100, 110)),
        ];

        let mut incompatible = evidence(100, 104);
        incompatible.scope.observable = "forces".to_owned();
        outcomes.push(check_runtime_contract(&policy, &incompatible));

        let mut unsupported_policy = policy.clone();
        unsupported_policy.numeric.schema_version = 2;
        let mut unsupported_evidence = evidence(100, 104);
        unsupported_evidence.numeric.schema_version = 2;
        outcomes.push(check_runtime_contract(
            &unsupported_policy,
            &unsupported_evidence,
        ));

        unsupported_policy.numeric.schema_version = CURRENT_NUMERIC_SCHEMA_VERSION;
        unsupported_policy.numeric.rounding = RoundingConvention::TowardZero;
        unsupported_evidence.numeric.schema_version = CURRENT_NUMERIC_SCHEMA_VERSION;
        unsupported_evidence.numeric.rounding = RoundingConvention::TowardZero;
        outcomes.push(check_runtime_contract(
            &unsupported_policy,
            &unsupported_evidence,
        ));

        assert!(outcomes
            .into_iter()
            .all(|outcome| !outcome.correction_allowed()));
    }

    #[test]
    fn certificate_schema_is_stable_and_round_trips() {
        let mut policy = policy();
        policy.numeric.rounding = RoundingConvention::Nearest;
        let mut evidence = evidence(100, 104);
        evidence.numeric.rounding = RoundingConvention::Nearest;

        let certificate = certify_runtime_contract(policy, evidence);
        let encoded = serde_json::to_value(&certificate).expect("serialize certificate");
        assert_eq!(
            encoded["schema"],
            json!(RUNTIME_CONTRACT_CERTIFICATE_SCHEMA)
        );
        assert_eq!(
            encoded["policy"]["scope"]["model"]["digest"],
            "sha256:fixture-model"
        );
        assert_eq!(
            encoded["policy"]["scope"]["context"]["species"],
            json!(["H", "H"])
        );
        assert_eq!(encoded["policy"]["scope"]["context"]["charge"], 0);
        assert_eq!(
            encoded["policy"]["scope"]["descriptor"]["metric_convention"],
            "discrete-v1"
        );
        assert_eq!(encoded["policy"]["numeric"]["schema_version"], 1);
        assert_eq!(encoded["policy"]["numeric"]["scale"], 1000);
        assert_eq!(encoded["policy"]["numeric"]["units"], "eV");
        assert_eq!(
            encoded["policy"]["numeric"]["semantics"],
            "exact-fixed-point-v1"
        );
        assert_eq!(encoded["policy"]["numeric"]["rounding"], "nearest");
        assert_eq!(encoded["decision"], "indeterminate");
        assert_eq!(encoded["reason"], "unsupported_rounding");
        assert_eq!(encoded["correction_allowed"], false);
        assert_eq!(
            encoded["theorem_references"],
            json!([UNSUPPORTED_ROUNDING_THEOREM, FAIL_CLOSED_THEOREM])
        );

        let decoded: RuntimeContractCertificate =
            serde_json::from_value(encoded).expect("deserialize certificate");
        assert_eq!(decoded, certificate);
        assert_eq!(decoded.verify(), Ok(()));
    }

    #[test]
    fn forged_runtime_certificates_are_rejected() {
        let certificate = certify_runtime_contract(policy(), evidence(100, 104));
        assert_eq!(certificate.validate(), Ok(()));

        let mut forged_schema = certificate.clone();
        forged_schema.schema = "lupine.forged.v1".to_owned();
        assert!(matches!(
            forged_schema.verify(),
            Err(CertificateValidationError::Schema { .. })
        ));

        let mut forged_input = certificate.clone();
        forged_input.evidence.scope.model.digest = "sha256:forged-model".to_owned();
        assert_eq!(
            forged_input.verify(),
            Err(CertificateValidationError::Result)
        );

        let mut forged_result = certificate.clone();
        forged_result.result = RuntimeGateDecision::Indeterminate {
            reason: RuntimeReason::WidthTooLarge,
        };
        assert_eq!(
            forged_result.verify(),
            Err(CertificateValidationError::Result)
        );

        let mut forged_authorization = certificate.clone();
        forged_authorization.correction_allowed = false;
        assert_eq!(
            forged_authorization.verify(),
            Err(CertificateValidationError::CorrectionAllowed {
                expected: true,
                actual: false,
            })
        );

        let mut forged_reference = certificate;
        forged_reference.theorem_references[0] = "Forged.theorem".to_owned();
        assert!(matches!(
            forged_reference.verify(),
            Err(CertificateValidationError::TheoremReferences { .. })
        ));
    }

    #[test]
    fn certificates_cover_every_lean_runtime_outcome() {
        let base_policy = policy();
        let mut incompatible = evidence(100, 104);
        incompatible.scope.model.digest = "sha256:different-model".to_owned();

        let mut schema_policy = base_policy.clone();
        schema_policy.numeric.schema_version = 2;
        let mut schema_evidence = evidence(100, 104);
        schema_evidence.numeric.schema_version = 2;

        let mut rounding_policy = base_policy.clone();
        rounding_policy.numeric.rounding = RoundingConvention::Nearest;
        let mut rounding_evidence = evidence(100, 104);
        rounding_evidence.numeric.rounding = RoundingConvention::Nearest;

        let cases = [
            (
                base_policy.clone(),
                evidence(100, 104),
                RuntimeGateDecision::Admit,
                ADMIT_THEOREM,
            ),
            (
                base_policy.clone(),
                incompatible,
                RuntimeGateDecision::Refuse {
                    violation: RuntimeViolation::IncompatibleContract,
                },
                INCOMPATIBLE_THEOREM,
            ),
            (
                base_policy.clone(),
                evidence(105, 104),
                RuntimeGateDecision::Refuse {
                    violation: RuntimeViolation::InconsistentEnvelope,
                },
                INCONSISTENT_THEOREM,
            ),
            (
                schema_policy,
                schema_evidence,
                RuntimeGateDecision::Indeterminate {
                    reason: RuntimeReason::UnsupportedSchema,
                },
                UNSUPPORTED_SCHEMA_THEOREM,
            ),
            (
                rounding_policy,
                rounding_evidence,
                RuntimeGateDecision::Indeterminate {
                    reason: RuntimeReason::UnsupportedRounding,
                },
                UNSUPPORTED_ROUNDING_THEOREM,
            ),
            (
                base_policy,
                evidence(100, 110),
                RuntimeGateDecision::Indeterminate {
                    reason: RuntimeReason::WidthTooLarge,
                },
                WIDTH_TOO_LARGE_THEOREM,
            ),
        ];

        for (policy, evidence, expected, theorem) in cases {
            let certificate = certify_runtime_contract(policy, evidence);
            assert_eq!(certificate.result, expected);
            assert_eq!(
                certificate.correction_allowed,
                expected.correction_allowed()
            );
            assert_eq!(
                certificate.theorem_references,
                vec![theorem.to_owned(), FAIL_CLOSED_THEOREM.to_owned()]
            );
        }
    }

    #[test]
    fn declarative_admissibility_matches_checker() {
        let policy = policy();
        for evidence in [evidence(100, 104), evidence(105, 104), evidence(100, 110)] {
            assert_eq!(
                policy.is_admissible(&evidence),
                check_runtime_contract(&policy, &evidence) == RuntimeGateDecision::Admit
            );
        }
    }
}
