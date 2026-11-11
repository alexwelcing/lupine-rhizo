# Reproduce Our Results

Every claim in the [conjecture ledger](conjectures/ledger.md) is regenerable from the
open-source `distill` engine against the corpus described in
[Data & Provenance](data-provenance.md). Nothing here requires private data.

## Build the engine

```bash
cd distill
cargo build --release
```

A single static Rust binary — deterministic build, no service dependencies,
air-gap-compatible.

## Reproduce the core results

```bash
# Hyper-ribbon manifold + full FCC validation
cargo run --bin distill -- validate --full

# BCC benchmark (the crystal-structure dichotomy regime)
cargo run --bin distill -- validate --full --bcc

# Manifold analysis only (participation-ratio dimensionality)
cargo run --bin distill -- manifold

# Simpson's-paradox detection demo — on the recorded BCC data it finds no reversal (claim withdrawn)
cargo run --bin distill -- detect-paradox --bcc

# Random-effects meta-analysis across elements
cargo run --bin distill -- meta-analysis
```

Outputs are written as JSON next to the binary
(`benchmark_manifold.json`, `bcc_manifold_analysis.json`, …) — the same artifacts the
figures and the [formal proof ledger](formal-proof-ledger.md) consume.

## Reproduce the formal verdicts

The Lean 4 specification is the adversary of the prose. The
[Formal Audit Report](formal-audit.md) is generated *by* the spec:

```bash
cd lean-spec
lake build          # checks every theorem, including simpsonsDetectedEmpirical
```

A green `lake build` *is* the audit: if a verdict changed, the build would fail.

## What "reproduce" means here

- **Statistical claims** (ribbon dimensionality, refutations) → re-run `distill`
  on the public corpus; numbers should match the ledger within bootstrap variance.
- **Structural claims** (Simpson's-paradox impossibility, parameter bounds) → re-run
  `lake build`; the theorem either checks or it does not.
- **Self-corrections** (BCC/FCC) → the ingest gate is in the engine; running on the
  pre-purge data and the post-purge data reproduces *both* the artifact and its
  removal — the self-correction is itself reproducible.

If a number here cannot be reproduced from these commands, that is a bug in the corpus,
not a rounding difference — report it.
