//! Reusable, theorem-mirrored runtime policy kernels.
//!
//! Command modules own transport and CLI concerns. This module owns the small,
//! deterministic decision procedures whose semantics are mirrored in Lean.

pub mod gate;
pub mod runtime;

#[allow(unused_imports)]
pub use gate::{
    certify_fixed_envelope, check_fixed_envelope, CertificateValidationError, EnvelopeReason,
    EnvelopeViolation, FixedEnvelope, FixedEnvelopeCertificate, GateDecision,
};
#[allow(unused_imports)]
pub use runtime::{
    certify_runtime_contract, check_runtime_contract, ArtifactId, DescriptorId, FixedMeasurement,
    MolecularContext, NumericContract, RoundingConvention, RuntimeContractCertificate,
    RuntimeGateDecision, RuntimePolicy, RuntimeReason, RuntimeViolation, ScopeIdentity,
    CURRENT_NUMERIC_SCHEMA_VERSION, RUNTIME_CONTRACT_CERTIFICATE_SCHEMA,
};
