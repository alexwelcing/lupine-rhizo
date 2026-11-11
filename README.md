# Lupine Rhizo

Lupine Science measures where machine-learned models of atoms go wrong, against
published references and pass/fail gates set in advance, and publishes every
verdict, failures included.

Rhizo is our research workbench. It holds the Lean checks, the Rust and Python
engines that score models, the benchmark loops that run them, the evidence records
each run leaves behind, and the export contracts that feed the public Library. It
records what failed as well as what held. Nothing in it has been peer-reviewed yet.

## Check it yourself

- **[Hypothesis ledger](docs/conjectures/ledger.md)**: every registered campaign and
  tested claim with its status (Supported, Open, Failed, Abstained, Refuted by us,
  Self-corrected, Withdrawn) and a link to the file that holds its numbers.
- **[Negative-results preprint](paper/negative-results-preprint/)**: the Round-4
  failures written up as a paper, with source data and hash-locked inputs.
- **[Replication kit](replication/error-geometry/)**: recompute the error-geometry
  statistics from committed raw data (Tier 1, seconds) or from public checkpoints
  (Tier 2), including the preregistered follow-up that did not reproduce.
- **[Offline HPC lane](hpc/)** and its **[facility review](hpc/ADMIN_REVIEW.md)**:
  run benchmark cells on your own cluster with local inputs, local outputs and no
  outbound connections at runtime.
- **[How we use AI agents and handle data](docs/ai-and-data.md)**: which rules live in
  code, what each one covers, and where data goes.
- **[Formal proof ledger](docs/formal-proof-ledger.md)**: what each Lean statement
  actually checks.

## Results, with their scope

Each result carries its qualifiers. Retired headlines and the reasons are listed at
[lupine.science/corrections](https://lupine.science/corrections/).

- **Round 4 (July 2026): no gate passed.** In four preregistered campaigns, three
  failed and one abstained. On a 30-path Li-ion migration-barrier panel, MACE-MP-0
  small and medium, MACE-MPA-0 medium and CHGNet missed a 40 meV gate (MAE
  135.0–242.5 meV on completed paths). A lattice- and elastic-constant correction on
  rocksalt ionics and perovskites failed (ionics 0/4; perovskites 0/1 after a
  post-measurement amendment). Every selected Δ-correction made catalyst-adsorption
  holdout error worse. The magnetism campaign abstained: no available model had the
  spin physics it needed. → [ledger](docs/conjectures/ledger.md)
- **An error field for fcc metals.** For nine fcc metals, an error field fitted to
  three other observables predicted the never-fitted (110) surface-energy error of
  four foundation MLIPs at r = 0.906 across 36 model–material cells
  (material-clustered 95% CI 0.82–0.96; permutation null centred near 0.44;
  significant for three of the four models).
  → [paper](paper/environment-error-field-2026-07-02.md)
- **Cubic-metal elastic constants: a ceiling, not a correction.** On 16 elemental
  cubic metals with four MatPES MLIPs (128 cases; r2SCAN targets approximate), one
  bias direction per functional transfers out of sample. When the held-out reference
  sets how far to correct, MAE falls from 17.84 to 10.36 GPa: a ceiling, not a
  deployable correction. A correction that works without seeing the answer is still
  open, and derived moduli are uncertified.
  → [paper](paper/lupine-layer2-3x3x3-final-paper.md)
- **Shared error patterns (October 2026).** A retrospective analysis of previously
  examined data: a learned shared direction added little or no advantage over a
  common-direction baseline. No new physical validation is claimed.
  → [explainer](https://lupine.science/articles/what-error-patterns-can-tell-us/)
- **We correct ourselves.** A BCC/FCC "causal shield" was about 1.5% data
  contamination; a d-band signal was a sample-size artifact; four of seven registered
  Projection Law predictions failed. → [ledger](docs/conjectures/ledger.md)

No Lupine paper has been peer-reviewed or accepted yet.

## What the Lean layer is

`lean-spec/` holds Lean 4 statements over recorded values. Lean 4 checks the
arithmetic and stated inequalities behind published numbers; it does not check the
physics, the reference data or the pipeline. The build must pass with no `sorry`,
and the theorem inventory is generated into
[`lean-spec/theorem-count.json`](lean-spec/theorem-count.json), never typed by hand.
See [lean-spec/README.md](lean-spec/README.md).

## Layout

| Path | What it is |
| --- | --- |
| `distill/`, `python/` | Rust and Python scoring engines, including fixed- and random-effects meta-analysis of correlation coefficients across independent groups |
| `lean-spec/` | Lean 4 checks of the arithmetic and inequalities behind published numbers |
| `gcp/`, `hpc/` | Benchmark cell runners: Cloud Run jobs, and the offline Apptainer/SLURM lane |
| `glim-think/` | The task scheduler and research record behind the public activity feed |
| `campaigns/`, `registry/`, `snapshots/`, `evidence/`, `data/` | Preregistered campaign manifests, claim registry, status snapshots and evidence records |
| `docs/`, `paper/`, `replication/` | Research notes, manuscripts and replication kits |
| `exports/` | Public export contracts read by the Library and the website |
| `tools/`, `scripts/` | Command-line tools, checks and export generators |

## Boundary

Rhizo publishes; the public sites consume. It does not hold the
[lupine.science](https://lupine.science) site, the
[Library](https://library.lupine.science) reader or the [Lupi](https://lupi.live)
viewer. The Library reads `exports/library-content/latest/`, regenerated with
`node scripts/export_library_content.mjs` and verified by the reader before it
renders.

Related repositories: [lupine-science](https://github.com/alexwelcing/lupine-science)
(public site) · [lupine-ledger](https://github.com/alexwelcing/lupine-ledger)
(Library reader) · [Lupi](https://github.com/alexwelcing/Lupi) (browser viewer) ·
[lupine](https://github.com/alexwelcing/lupine) (historical monorepo).

## Quick checks

```bash
just verify-light      # fast pre-commit checks
just verify            # routine pre-merge validation
cd lean-spec && lake build   # Lean gate; run from inside lean-spec/
```

Windows and toolchain notes are in [CONTRIBUTING.md](CONTRIBUTING.md) and
[AGENTS.md](AGENTS.md). More orientation: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md),
[ROOTS.md](ROOTS.md), [CHANGELOG.md](CHANGELOG.md).

## License

You can reuse our code (MIT) and our first-party text and data (CC BY 4.0) with
attribution and no share-alike obligations. Third-party datasets, potentials and
papers keep their own terms; see [NOTICE.md](NOTICE.md),
[LICENSE-CONTENT.md](LICENSE-CONTENT.md) and [LICENSE-DATA.md](LICENSE-DATA.md).

## Contact

Research partners, model builders, press and investors: alex@lupinesci.com.
