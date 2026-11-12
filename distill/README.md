# distill

**Mathematical discovery engine for molecular dynamics simulation data.**

[![Tests](https://github.com/alexwelcing/lupine-rhizo/actions/workflows/build-distill.yml/badge.svg)](https://github.com/alexwelcing/lupine-rhizo/actions/workflows/build-distill.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

`distill` is a Rust-based scientific engine for analyzing the geometric and statistical structure of interatomic potential prediction errors. It implements sloppy model theory, causal inference (Simpson's paradox detection), and random-effects meta-analysis for systematic benchmarking of classical and machine-learning potentials.

## Features

- **Manifold Analysis** — PCA/SVD eigenvalue analysis of prediction errors with hyper-ribbon detection
- **Bootstrap Uncertainty Quantification** — 95% confidence intervals for participation ratios and geometric fits
- **Meta-Analysis** — Standard fixed- and random-effects meta-analysis of correlation coefficients across independent groups (Fisher z, DerSimonian–Laird τ², Cochran's Q and I², t-based prediction interval); see [Meta-analysis](#meta-analysis) for scope and the 2026-11-12 fix
- **Simpson's Paradox Detection** — Pooled vs. within-group correlation comparison with reversal markers
- **Multi-Potential Benchmarking** — FCC (8 metals) and BCC (7 metals) elastic constant validation
- **Model Geometry Evidence** — Residual-SVD packets for MLIP/WBM/arena-scale model dumps, with accuracy gates and effective-rank guards
- **Literature Fetching** — CrossRef/arXiv abstract retrieval and value extraction
- **Lean 4 Formalization** — Export computationally validated relationships into formal specification

## Quick Start

### Installation

```bash
# From crates.io (when published)
cargo install --path distill --bin distill

# From source
git clone https://github.com/alexwelcing/lupine.git
cd lupine-rhizo/distill
cargo build --release
```

### Run the full validation suite

```bash
# FCC benchmark with manifold analysis
cargo run --bin distill -- validate --full

# BCC benchmark
cargo run --bin distill -- validate --full --bcc

# Manifold analysis only
cargo run --bin distill -- manifold

# Simpson's paradox demo
cargo run --bin distill -- detect-paradox --bcc

# Model/reference residual geometry from a tidy benchmark dump
cargo run --bin distill -- model-geometry \
  --input tests/fixtures/model_geometry_smoke.csv \
  --pair gen0:gen1 \
  --quality-gate accuracy \
  --top-k 3

# Same command shape used by glim-think/tasks-consumer
cargo run --bin distill -- model-geometry \
  --fixture-url tests/fixtures/model_geometry_smoke.csv \
  --hypothesis-id mlip-manifold-equivalence \
  --pair gen0:gen1 \
  --quality-gate accuracy \
  --top-k 5

# Canonical Lupine Distill runtime policy for one prediction
cargo run --bin distill -- distill-policy \
  --request tests/fixtures/distill_policy_energy_block.json \
  --ribbon-version hyperribbon-v1

# Apply a selected hill-climb policy limits object during runtime decisions
cargo run --bin distill -- distill-policy \
  --request tests/fixtures/distill_policy_energy_gate.json \
  --policy-limits tmp/selected-policy-limits.json \
  --ribbon-version hyperribbon-v1

# Batch mode used by MLIP cell runners; one request per JSONL line
cargo run --bin distill -- distill-policy \
  --request-jsonl tmp/distill-policy-requests.jsonl \
  --output tmp/distill-policy-decisions.jsonl \
  --ribbon-version hyperribbon-v1

# Local Distill ribbon hill climb for sealed MLIP replay cases
cargo run --bin distill -- distill-hill-climb \
  --cases tests/fixtures/distill_hill_climb_cases.jsonl \
  --selected-limits-output tmp/selected-policy-limits.json \
  --rounds 3 \
  --beam-width 4 \
  --report-top-k 8 \
  --ribbon-version hyperribbon-v1

# Offset-lattice equilibrium solve baseline scoring
cargo run --bin distill -- equilibrium-solve \
  --trajectory tests/fixtures/equilibrium_solve_al_fcc_offset.json \
  --continuation-window-steps 200
```

### Docker

```bash
docker build -t distill .
docker run --rm distill validate --full
```

## Development

`distill` is a Cargo workspace. The core engine builds without GPU dependencies:

```bash
cargo check --workspace
cargo test --workspace
cargo clippy --workspace -- -D warnings
```

The `gpu_experiment` binary is an optional WGPU proof-of-concept and is gated behind the `gpu` feature:

```bash
cargo run --bin gpu_experiment --features gpu
```

## Benchmark Datasets

| Dataset | Metals | Potentials | Properties |
|---------|--------|------------|------------|
| FCC | Al, Cu, Ni, Ag, Au, Pt, Pd, Pb | EAM, LJ, SW | C₁₁, C₁₂, C₄₄ |
| BCC | Fe, Cr, Mo, W, V, Nb, Ta | EAM, LJ | C₁₁, C₁₂, C₄₄ |
| **NIST** | **15 metals** | **170 real NIST potentials** | **C₁₁, C₁₂, C₄₄** |

All values in GPa. Reference data from room-temperature experimental crystallographic databases.
NIST data sourced from the [NIST Interatomic Potentials Repository](https://www.ctcms.nist.gov/potentials/) via local mirror.

## Architecture

```
distill/
├── src/
│   ├── main.rs           # CLI entrypoint (16 subcommands)
│   ├── stats.rs          # PCA, covariance, Fisher z, bootstrap CI
│   ├── manifold.rs       # Error vector analysis, hyper-ribbon detection
│   ├── meta_analysis.rs  # Fixed/random-effects meta-analysis
│   ├── causal.rs         # Simpson's paradox detection
│   ├── validation.rs     # Multi-potential benchmark harness
│   ├── benchmark.rs      # CSV/JSON benchmark database loader
│   ├── nist.rs           # NIST IPR catalog loader + scaffold generator
│   ├── autoresearch.rs   # Automated DOI→fetch→extract→benchmark pipeline
│   ├── fitting/          # Linear, power-law, Arrhenius, polynomial, symbolic regression
│   ├── observables/      # RDF, MSD, VACF, elastic constants
│   ├── ingest/           # LAMMPS log and dump parsers
│   ├── literature/       # CrossRef/arXiv fetch and extract
│   └── formalize.rs      # Lean 4 specification export
├── benchmarks/           # FCC, BCC, and NIST scaffold data
├── Dockerfile
└── cloudbuild.yaml       # GCP Cloud Run Job deployment
```

## CLI Commands

| Command | Description |
|---------|-------------|
| `validate [--full] [--bcc]` | Run ensemble operator validation |
| `manifold [--bcc]` | Analyze error manifold structure |
| `detect-paradox [--bcc] [--example]` | Detect Simpson's paradox |
| `benchmark <file> [--manifold] [--meta]` | Load external benchmark database |
| `model-geometry --input <csv/json> [--pair A:B]` | Distill model-to-model and model-to-reference residual geometry evidence |
| `model-geometry --fixture-url <path/gs/http> --hypothesis-id <id>` | Glim-think/task-consumer compatible model-geometry run with optional beat emission |
| `distill-policy --request <json> [--policy-limits <json>]` | Apply the canonical versioned Lupine Distill runtime policy to one MLIP prediction |
| `distill-policy --request-jsonl <jsonl>` | Batch canonical Distill runtime decisions for a cell runner |
| `distill-hill-climb --cases <json/jsonl>` | Search hyperribbon policy limits against sealed local MLIP replay cases |
| `equilibrium-solve --trajectory <json>` | Score an offset-lattice relaxation against known equilibrium and emit viewer-ready evidence |
| `nist [--element] [--pair-style] [--scaffold]` | Query NIST IPR catalog (675 potentials) |
| `auto-research [--elements] [--eam-only]` | Automated DOI→extract→benchmark pipeline |
| `thermo <log> [--x] [--y]` | Analyze LAMMPS thermo log |
| `trajectory <dump> [--msd] [--rdf] [--vacf]` | Analyze trajectory data |
| `fit <csv> [--model] [--degree]` | Fit model to CSV data |
| `elastic --c11 --c12 --c44` | Compute FCC elastic properties |
| `literature <action>` | Literature-based discovery |
| `scan --x --y <files...>` | Cross-run relationship scanning |
| `pipeline [--provider]` | Hermes pipeline orchestrator |
| `formalize` | Export to Lean 4 specification |

## Key Results

### FCC Hyper-Ribbon Structure

| Potential | PR / 3 | 95% CI | R²_log | Hyper-ribbon? |
|-----------|--------|--------|--------|---------------|
| EAM | 1.37 | [1.14, 2.16] | 0.940 | ✅ Yes |
| LJ | 1.17 | [1.04, 1.51] | 0.991 | ✅ Yes |
| SW | 1.38 | [1.09, 2.08] | 0.985 | ✅ Yes |

### BCC Simpson's Paradox

- **Pooled correlation:** r = −0.435
- **Within-group correlation:** r = +0.147
- **Reversal magnitude:** 0.581
- **Detection:** Complete reversal with ecological fallacy risk

## Citation

If you use `distill` in your research, please cite:

```bibtex
@unpublished{welcing2026causal,
  author  = {Welcing, Alexander},
  title   = {The Causal Geometry of Prediction Errors in Interatomic Potentials: A Hyper-Ribbon Manifold Analysis with Simpson's Paradox Detection},
  year    = {2026},
  note    = {Working paper, in preparation}
}
```

## License

MIT License — see [LICENSE](LICENSE) for details.

## Acknowledgments

This work builds on sloppy model theory (Brown & Sethna 2003, Transtrum et al. 2010–2013), causal inference methodology (Pearl 2014), and meta-analysis frameworks (DerSimonian & Laird 1986). Benchmark data sources include the OpenKIM consortium and NIST Interatomic Potential Database.

## Meta-analysis

`src/meta_analysis.rs` is a byte-identical copy of
`alexwelcing/lupine` `atlas-distill/src/meta_analysis.rs`. It implements
standard fixed- and random-effects meta-analysis of correlation coefficients
across independent groups: each group's r is Fisher z-transformed, weighted by
inverse variance, pooled and back-transformed; the random-effects model adds a
DerSimonian–Laird estimate of between-group variance τ² and a t-based
prediction interval. Both models report Cochran's Q (fixed-effect weights
around the fixed-effect mean), its p-value and I². It pools correlations, not
error magnitudes such as MAE, and it assumes the groups are independent. Rows
that share materials or models (for example C11, C12 and C44 of the same
metal) are not independent, and intervals built on such rows are
anti-conservative; for this reason `paper/tms2027-proceedings/manuscript.tex`
does not report such intervals as inference.

This crate uses the module as a library and through its unit tests. It has no
`meta-analyze` command; that command lives in `atlas-distill` in
`alexwelcing/lupine`.

**Fixed 2026-11-12.** The random-effects output used to recompute Q, its
p-value and I² around the random-effects mean (which can only make them
larger) and built the prediction interval with the normal quantile 1.96. It
now reports the fixed-effect Q for both models, uses
μ̂_RE ± t_{k−2, 0.975} · sqrt(τ² + SE²) for the prediction interval (undefined,
written as JSON `null`, for fewer than three groups), takes the Q p-value from
the regularized incomplete gamma function and uses z₀.₉₇₅ = 1.959963984540054
for confidence intervals. τ² was already computed from the correct Q and does
not change. Until this date `src/main.rs` did not declare `mod meta_analysis`,
so the module and its tests were never compiled; it is now declared and
`cargo test` runs its 15 tests. They compare every reported statistic, to
1e-6, with an independent numpy/scipy implementation copied from
`atlas-distill` into `tests/reference/` (`meta_reference.py` and its committed
output `meta_reference.json`; the generator paths inside them name
`atlas-distill`, where the values were produced, and the input
`benchmarks/nist_populated_all.csv` is byte-identical in both crates).

Published numbers that came from this engine, before and after the fix: the
15-element panel's random-effects Q went from 984 to 945, I² from 98.6% to
98.5%, and the 95% prediction interval from [−0.64, +0.99] to [−0.73, +0.99].
The pooled r (0.69), its CI [0.41, 0.85] and τ (0.80) are unchanged. See
`paper/README.md` for the corrected IMMI working paper.
