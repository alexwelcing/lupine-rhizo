# Running Lupine on Your Cluster — Visiting Lab Brief

Audience: experienced MD/LAMMPS researchers meeting this project for the
first time. Your facility staff should read the companion
[`ADMIN_REVIEW.md`](./ADMIN_REVIEW.md).

## The claim, honestly stated

Across hundreds of interatomic potentials, elastic-constant error vectors do
not fill their nominal error space — they collapse onto a low-dimensional
manifold (participation ratio ~1.1–2 out of 3–5 dimensions for classical
potentials; transfer to foundation MLIPs is under active re-audit after
Born-stability screening excluded several tensors). Structured error is
predictable error, and predictable error is correctable — that is the
distillation program.

What is unusual here is the bookkeeping, not just the claim:

- A conjecture ledger ([`docs/conjectures/ledger.md`](../docs/conjectures/ledger.md))
  that publishes refutations and self-corrections as prominently as
  confirmations.
- A Lean 4 layer ([`lean-spec/`](../lean-spec/)) where accepted empirical
  numbers become build-checked obligations: if a claimed inequality stops
  holding against the recorded data, `lake build` fails. Think of it as
  **CI for scientific claims** — machine-checked arithmetic gates over
  measured values, not "proven physics". The boundary is documented in
  [`docs/formal-methodology.md`](../docs/formal-methodology.md).

## The integration contract

Your LAMMPS campaigns stay yours: your scheduler, your potentials, your
scale. The handoff is a file contract over output you already produce.

```
your LAMMPS campaign (any scale)
    │  log files (stock examples/ELASTIC driver output, thermo logs)
    ▼
python3 -m lupine_distill.lammps_ingest parse …
    │  → lupine.mlip.lammps_evidence.v1 JSON
    │    (schema-validated, SHA-256 content provenance)
    ▼
python3 -m lupine_distill.lammps_ingest lean …
    │  → machine-generated Lean 4 evidence module
    ▼
lake build gate — your result becomes a standing, machine-checked claim
```

You never need to run Lean. The generated module plus its input hash is the
handoff artifact; admission into `lean-spec/` is our review step (the
production path is `tools/mlip_distill_atlas.py`).

## Quickstart (minutes, CPU only)

```bash
pip install -e ./python
python3 hpc/examples/lammps_to_lean_demo.py     # end-to-end on committed sample logs
```

Then against your own elastic run:

```bash
python3 -m lupine_distill.lammps_ingest parse /path/to/your/log.lammps \
    --material Ni --potential Ni_u3.eam --input-script in.elastic \
    --ref C11=246.5 --ref C12=147.3 --ref C44=124.7 \
    --ref-source "Simmons & Wang 1971" \
    -o my_evidence.json
python3 -m lupine_distill.lammps_ingest lean my_evidence.json -o MyModule.lean
```

`--kind thermo` handles plain MD logs; `--help` documents everything. See
[`examples/README.md`](./examples/README.md) for the committed demo
artifacts, including a generated `.lean` module you can read without
running anything.

## Running our benchmark cells at scale

The same cell contract that runs in our cloud runs offline on your cluster —
file-based inputs and outputs, no external services, no tokens
(design notes: [ADR 0005](../docs/decisions/0005-hpc-execution-lane.md)):

```bash
# on a connected host
apptainer build --build-arg BACKEND=mace mlip-runner-mace.sif hpc/Apptainer.def

# on the cluster
python3 hpc/slurm/make_cells.py batch_spec.json --out cells.jsonl \
    --artifact-root "$SCRATCH/mlip-results/cells"
N=$(wc -l < cells.jsonl)
sbatch --array=0-$((N-1)) \
    --export=ALL,SIF="$PWD/mlip-runner-mace.sif",CELLS_JSONL="$PWD/cells.jsonl",RESULTS_DIR="$SCRATCH/mlip-results" \
    hpc/slurm/run_cells.sbatch
```

Full submission runbook: [`slurm/README.md`](./slurm/README.md). Facilities
standardized on Shifter/podman-hpc can pull the OCI image built from
`gcp/mlip-cell-runner/Dockerfile.unified` instead; the runner is plain
Python and also works from a site venv.

## What we ask, and what you get

**Ask:** run screened campaign specs on materials and potentials beyond our
compute budget, and hand back the evidence JSONs — by pull request or as a
DOI'd deposit ([`replication/error-geometry/`](../replication/error-geometry/)
is our existing Zenodo-kit pattern).

**Get:** co-authored evidence modules with your runs as the load-bearing
data, standing machine-checked claims citing your lab, and the replication-kit
template for your own publications.

## Reading deeper

- [`docs/conjectures/ledger.md`](../docs/conjectures/ledger.md) — every hypothesis and its status, including what we refuted
- [`docs/formal-methodology.md`](../docs/formal-methodology.md) — what the Lean layer does and does not claim
- [`replication/error-geometry/`](../replication/error-geometry/) — self-contained reproduction of the core result (Tier 1: seconds; Tier 2: ~5 min on public checkpoints)
- [`docs/ARCHITECTURE.md`](../docs/ARCHITECTURE.md) — the full system map
