# Lupine Rhizo: overview

Moved from the root [README](../README.md) on 2026-11-13, when the README was cut
to one screen. The text is unchanged; only link paths are adjusted for this folder.

Rhizo is our research workbench. It holds the Lean checks, the Rust and Python
engines that score models, the benchmark loops that run them, the evidence records
each run leaves behind, and the export contracts that feed the public Library. It
records what failed as well as what held. Nothing in it has been peer-reviewed yet.

## Check it yourself

- **[Hypothesis ledger](conjectures/ledger.md)**: every registered campaign and
  tested claim with its status (Supported, Open, Failed, Abstained, Refuted by us,
  Self-corrected, Withdrawn) and a link to the file that holds its numbers.
- **[Negative-results preprint](../paper/negative-results-preprint/)**: three locked
  negative results (the preregistered Round-4 Z1 barrier and Z3
  adsorption-correction campaigns, and a separately locked global elastic
  operator) written up as a paper, with source data and hash-locked inputs.
- **[Replication kit](../replication/error-geometry/)**: recompute the error-geometry
  statistics from committed raw data (Tier 1, seconds) or from public checkpoints
  (Tier 2), with a status note on the preregistered follow-up that did not
  reproduce.
- **[Offline HPC lane](../hpc/)** and its **[facility review](../hpc/ADMIN_REVIEW.md)**:
  run benchmark cells on your own cluster with local inputs and local outputs;
  after a one-time connected pre-fetch of potentials and model checkpoints it needs
  no outbound connections. The container has not yet been built on a facility
  cluster.
- **[How we use AI agents and handle data](ai-and-data.md)**: which rules live in
  code, what each one covers, and where data goes.
- **[Formal proof ledger](formal-proof-ledger.md)**: what each Lean statement
  actually checks.

## What the Lean layer is

`lean-spec/` holds Lean 4 statements over recorded values. Lean 4 checks the
arithmetic and stated inequalities behind published numbers; it does not check the
physics, the reference data or the pipeline. The build must pass with no `sorry`,
and the theorem inventory is generated into
[`lean-spec/theorem-count.json`](../lean-spec/theorem-count.json), never typed by hand.
See [lean-spec/README.md](../lean-spec/README.md).

## More

- [Results in detail](results-detail.md)
- [Repository map](repository-map.md)
- [Development](development.md)
