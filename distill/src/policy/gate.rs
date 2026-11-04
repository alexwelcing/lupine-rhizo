//! Exact fixed-point reference gate mirrored by Lean `UniversalCorrection.Gate`.
//!
//! Floating-point parsing, unit conversion, and outward rounding must happen
//! before this boundary. The gate itself consumes only exact fixed-point
//! integers and produces a three-valued, fail-closed decision.

use serde::{Deserialize, Serialize};
use std::fmt;

pub const FIXED_ENVELOPE_CERTIFICATE_SCHEMA: &str =
    "lupine.universal_correction.fixed_envelope_certificate.v1";

const ADMIT_THEOREM: &str = "OpenDistillationFactory.Materials.Theory.\
UniversalCorrection.checkFixedEnvelope_admit_iff";
const REFUSE_THEOREM: &str = "OpenDistillationFactory.Materials.Theory.\
UniversalCorrection.checkFixedEnvelope_refuse_iff";
const INDETERMINATE_THEOREM: &str = "OpenDistillationFactory.Materials.Theory.\
UniversalCorrection.checkFixedEnvelope_indeterminate_iff";
const ALLOW_ADMIT_THEOREM: &str = "OpenDistillationFactory.Materials.Theory.\
UniversalCorrection.correctionAllowed_admit";
const BLOCK_REFUSE_THEOREM: &str = "OpenDistillationFactory.Materials.Theory.\
UniversalCorrection.correctionAllowed_refuse";
const BLOCK_INDETERMINATE_THEOREM: &str = "OpenDistillationFactory.Materials.Theory.\
UniversalCorrection.correctionAllowed_indeterminate";

/// A deserialized certificate failed semantic revalidation.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum CertificateValidationError {
    Schema {
        expected: String,
        actual: String,
    },
    Result,
    CorrectionAllowed {
        expected: bool,
        actual: bool,
    },
    TheoremReferences {
        expected: Vec<String>,
        actual: Vec<String>,
    },
}

impl fmt::Display for CertificateValidationError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Schema { expected, actual } => {
                write!(
                    formatter,
                    "certificate schema mismatch: expected {expected}, got {actual}"
                )
            }
            Self::Result => write!(formatter, "certificate result does not match checker"),
            Self::CorrectionAllowed { expected, actual } => write!(
                formatter,
                "certificate correction_allowed mismatch: expected {expected}, got {actual}"
            ),
            Self::TheoremReferences { .. } => {
                write!(
                    formatter,
                    "certificate theorem references do not match checker"
                )
            }
        }
    }
}

impl std::error::Error for CertificateValidationError {}

/// Exact fixed-point enclosure produced by the numeric ingestion boundary.
///
/// `i64` is the wire representation. Width comparisons are evaluated in
/// `i128`, so even the full interval `i64::MIN..=i64::MAX` cannot overflow.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub struct FixedEnvelope {
    pub lower: i64,
    pub upper: i64,
}

impl FixedEnvelope {
    pub(crate) fn ordered_width(self) -> Option<u128> {
        (self.lower <= self.upper)
            .then(|| (i128::from(self.upper) - i128::from(self.lower)) as u128)
    }

    /// Declarative admissibility predicate mirrored by Lean
    /// `FixedEnvelope.Admissible`.
    pub fn is_admissible(self, tolerance: u64) -> bool {
        self.ordered_width()
            .is_some_and(|width| width <= u128::from(tolerance))
    }
}

/// Definite contradiction carried by a refusal.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum EnvelopeViolation {
    Inconsistent,
}

/// Insufficient numeric resolution carried by an indeterminate decision.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum EnvelopeReason {
    WidthTooLarge,
}

/// Three-valued structural numeric decision.
///
/// `Admit` authorizes the runtime gate only. A scientific correction claim
/// additionally needs the residual-enclosure attestation formalized by Lean
/// `UniversalCorrection.ScientificAdmission`.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(tag = "decision", rename_all = "snake_case")]
pub enum GateDecision {
    Admit,
    Refuse { violation: EnvelopeViolation },
    Indeterminate { reason: EnvelopeReason },
}

impl GateDecision {
    /// Fail-closed authorization mirrored by Lean `correctionAllowed`.
    pub const fn correction_allowed(self) -> bool {
        matches!(self, Self::Admit)
    }

    fn theorem_references(self) -> [&'static str; 2] {
        match self {
            Self::Admit => [ADMIT_THEOREM, ALLOW_ADMIT_THEOREM],
            Self::Refuse { .. } => [REFUSE_THEOREM, BLOCK_REFUSE_THEOREM],
            Self::Indeterminate { .. } => [INDETERMINATE_THEOREM, BLOCK_INDETERMINATE_THEOREM],
        }
    }
}

/// Machine-readable certificate for one exact gate evaluation.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct FixedEnvelopeCertificate {
    pub schema: String,
    pub tolerance: u64,
    pub envelope: FixedEnvelope,
    #[serde(flatten)]
    pub result: GateDecision,
    pub correction_allowed: bool,
    pub theorem_references: Vec<String>,
}

impl FixedEnvelopeCertificate {
    /// Re-run the exact checker and validate every derived certificate field.
    pub fn validate(&self) -> Result<(), CertificateValidationError> {
        if self.schema != FIXED_ENVELOPE_CERTIFICATE_SCHEMA {
            return Err(CertificateValidationError::Schema {
                expected: FIXED_ENVELOPE_CERTIFICATE_SCHEMA.to_owned(),
                actual: self.schema.clone(),
            });
        }

        let expected_result = check_fixed_envelope(self.tolerance, self.envelope);
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

/// Exact, deterministic reference checker for one fixed-point enclosure.
pub fn check_fixed_envelope(tolerance: u64, envelope: FixedEnvelope) -> GateDecision {
    let Some(width) = envelope.ordered_width() else {
        return GateDecision::Refuse {
            violation: EnvelopeViolation::Inconsistent,
        };
    };

    if u128::from(tolerance) < width {
        GateDecision::Indeterminate {
            reason: EnvelopeReason::WidthTooLarge,
        }
    } else {
        GateDecision::Admit
    }
}

/// Evaluate the reference gate and retain its exact inputs and theorem hooks.
pub fn certify_fixed_envelope(tolerance: u64, envelope: FixedEnvelope) -> FixedEnvelopeCertificate {
    let result = check_fixed_envelope(tolerance, envelope);
    FixedEnvelopeCertificate {
        schema: FIXED_ENVELOPE_CERTIFICATE_SCHEMA.to_owned(),
        tolerance,
        envelope,
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

    const ADMITTED: FixedEnvelope = FixedEnvelope {
        lower: 100,
        upper: 104,
    };
    const REFUSED: FixedEnvelope = FixedEnvelope {
        lower: 105,
        upper: 104,
    };
    const INDETERMINATE: FixedEnvelope = FixedEnvelope {
        lower: 100,
        upper: 110,
    };

    #[test]
    fn matches_lean_admit_fixture() {
        assert!(ADMITTED.is_admissible(5));
        assert_eq!(check_fixed_envelope(5, ADMITTED), GateDecision::Admit);
        assert!(check_fixed_envelope(5, ADMITTED).correction_allowed());
    }

    #[test]
    fn matches_lean_refuse_fixture() {
        assert!(!REFUSED.is_admissible(5));
        assert_eq!(
            check_fixed_envelope(5, REFUSED),
            GateDecision::Refuse {
                violation: EnvelopeViolation::Inconsistent,
            }
        );
    }

    #[test]
    fn matches_lean_indeterminate_fixture() {
        assert!(!INDETERMINATE.is_admissible(5));
        assert_eq!(
            check_fixed_envelope(5, INDETERMINATE),
            GateDecision::Indeterminate {
                reason: EnvelopeReason::WidthTooLarge,
            }
        );
    }

    #[test]
    fn correction_authorization_is_fail_closed() {
        assert!(!check_fixed_envelope(5, REFUSED).correction_allowed());
        assert!(!check_fixed_envelope(5, INDETERMINATE).correction_allowed());
    }

    #[test]
    fn certificate_schema_is_stable_and_round_trips() {
        let certificate = certify_fixed_envelope(5, INDETERMINATE);
        let encoded = serde_json::to_value(&certificate).expect("serialize certificate");
        assert_eq!(
            encoded,
            json!({
                "schema": FIXED_ENVELOPE_CERTIFICATE_SCHEMA,
                "tolerance": 5,
                "envelope": {"lower": 100, "upper": 110},
                "decision": "indeterminate",
                "reason": "width_too_large",
                "correction_allowed": false,
                "theorem_references": [
                    INDETERMINATE_THEOREM,
                    BLOCK_INDETERMINATE_THEOREM
                ]
            })
        );

        let decoded: FixedEnvelopeCertificate =
            serde_json::from_value(encoded).expect("deserialize certificate");
        assert_eq!(decoded, certificate);
        assert_eq!(decoded.verify(), Ok(()));
    }

    #[test]
    fn forged_fixed_envelope_certificates_are_rejected() {
        let certificate = certify_fixed_envelope(5, INDETERMINATE);

        let mut forged_schema = certificate.clone();
        forged_schema.schema = "lupine.forged.v1".to_owned();
        assert!(matches!(
            forged_schema.verify(),
            Err(CertificateValidationError::Schema { .. })
        ));

        let mut forged_result = certificate.clone();
        forged_result.result = GateDecision::Admit;
        assert_eq!(
            forged_result.verify(),
            Err(CertificateValidationError::Result)
        );

        let mut forged_authorization = certificate.clone();
        forged_authorization.correction_allowed = true;
        assert_eq!(
            forged_authorization.verify(),
            Err(CertificateValidationError::CorrectionAllowed {
                expected: false,
                actual: true,
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
    fn full_i64_width_is_compared_without_overflow() {
        let full = FixedEnvelope {
            lower: i64::MIN,
            upper: i64::MAX,
        };
        assert_eq!(check_fixed_envelope(u64::MAX, full), GateDecision::Admit);
        assert_eq!(
            check_fixed_envelope(u64::MAX - 1, full),
            GateDecision::Indeterminate {
                reason: EnvelopeReason::WidthTooLarge,
            }
        );
    }
}
