//! Validate the complete structural runtime contract from a file-based input.
//!
//! The request mirrors Lean's full `Scope`, numeric contract, policy, and
//! fixed measurement. Scientific residual containment remains a separate
//! attestation; this command deliberately does not manufacture one.

use std::fs;
use std::path::PathBuf;

use anyhow::{Context, Result};
use clap::Args;
use serde::{Deserialize, Serialize};

use crate::policy::{certify_runtime_contract, FixedMeasurement, RuntimePolicy};

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct RuntimeContractRequest {
    pub policy: RuntimePolicy,
    pub evidence: FixedMeasurement,
}

#[derive(Debug, Clone, Args)]
pub struct ValidateRuntimeContractArgs {
    /// JSON file containing `policy` and `evidence` objects.
    #[arg(long)]
    pub input: PathBuf,

    /// Optional certificate path. Without it, JSON is written to stdout.
    #[arg(long)]
    pub output: Option<PathBuf>,
}

pub fn run(args: ValidateRuntimeContractArgs) -> Result<()> {
    let input = fs::read_to_string(&args.input)
        .with_context(|| format!("read runtime contract from {}", args.input.display()))?;
    let request: RuntimeContractRequest = serde_json::from_str(&input)
        .with_context(|| format!("parse runtime contract from {}", args.input.display()))?;
    let certificate = certify_runtime_contract(request.policy, request.evidence);
    certificate
        .verify()
        .context("internally verify generated runtime certificate")?;
    let json = serde_json::to_string_pretty(&certificate)
        .context("serialize runtime-contract certificate")?;

    if let Some(path) = args.output {
        fs::write(&path, format!("{json}\n"))
            .with_context(|| format!("write certificate to {}", path.display()))?;
    } else {
        println!("{json}");
    }

    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::policy::{check_runtime_contract, RuntimeGateDecision};

    #[test]
    fn lean_mirrored_fixture_admits() {
        let request: RuntimeContractRequest =
            serde_json::from_str(include_str!("../../fixtures/runtime_contract_admit.json"))
                .expect("parse fixture mirrored from the Lean certificate");
        assert_eq!(
            check_runtime_contract(&request.policy, &request.evidence),
            RuntimeGateDecision::Admit
        );
        assert!(certify_runtime_contract(request.policy, request.evidence)
            .verify()
            .is_ok());
    }
}
