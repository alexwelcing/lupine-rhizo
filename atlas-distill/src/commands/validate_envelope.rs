//! Emit a theorem-referenced certificate from the structural fixed-point gate.
//!
//! This command checks raw interval ordering and width. It does not attest
//! units, scope identity, outward rounding, or containment of a physical
//! residual; those belong to the composite runtime/scientific contracts.

use std::fs;
use std::path::PathBuf;

use anyhow::{Context, Result};
use clap::Args;

use crate::policy::{certify_fixed_envelope, FixedEnvelope};

#[derive(Debug, Clone, Args)]
pub struct ValidateEnvelopeArgs {
    /// Inclusive lower endpoint in fixed-point integer units.
    #[arg(long, allow_hyphen_values = true)]
    pub lower: i64,

    /// Inclusive upper endpoint in fixed-point integer units.
    #[arg(long, allow_hyphen_values = true)]
    pub upper: i64,

    /// Maximum admitted interval width in the same fixed-point units.
    #[arg(long)]
    pub tolerance: u64,

    /// Optional certificate path. Without it, JSON is written to stdout.
    #[arg(long)]
    pub output: Option<PathBuf>,
}

pub fn run(args: ValidateEnvelopeArgs) -> Result<()> {
    let certificate = certify_fixed_envelope(
        args.tolerance,
        FixedEnvelope {
            lower: args.lower,
            upper: args.upper,
        },
    );
    let json = serde_json::to_string_pretty(&certificate)
        .context("serialize fixed-envelope certificate")?;

    if let Some(path) = args.output {
        fs::write(&path, format!("{json}\n"))
            .with_context(|| format!("write certificate to {}", path.display()))?;
    } else {
        println!("{json}");
    }

    Ok(())
}
