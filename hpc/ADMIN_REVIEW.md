# Supercluster Admin Review — Lupine MLIP Cell Runner

Audience: HPC facility staff reviewing this software for execution on shared
compute resources. Every claim below is verifiable in-tree; verification
commands are at the end.

## What runs on your system

A single Python CLI (`gcp/mlip-cell-runner/mlip_cell_runner.py`) that scores
machine-learned interatomic potentials against sealed benchmark fixtures.
One invocation ("cell") = one (property, potential) pair: single-point
energies/forces, FIRE relaxations, and finite-strain elastic constants via
ASE. No MPI; one process per cell, optionally one GPU.

## Network posture

- The HPC lane is fully offline: inputs are local JSON manifests (plain
  paths or `file://` URLs), outputs are local JSON artifacts. With no
  `--beat-emit-url` flag the runner emits no beats and makes no outbound
  connections at runtime; this is exercised by integration tests that
  monkeypatch all network entry points to hard-fail
  (`gcp/mlip-cell-runner/test_runner_offline.py`).
- Interatomic potential files are fetched in a separate front-loaded step on
  a connected host (`tools/fetch_potentials.py`: URLs recorded in
  `data/mlip_benchmarks/manifest_sources.json`, SHA-256 verified,
  idempotent). MLIP model checkpoints (MACE, CHGNet, …) download on first
  use — air-gapped clusters need a one-time connected pre-fetch of the model
  cache (see `hpc/slurm/README.md`).
- Telemetry is opt-in and default-off: spans are emitted only when
  `LUPINE_OTEL_ENABLED` is truthy
  (`gcp/mlip-cell-runner/src/openinference_patcher.py`).

## Container

- `hpc/Apptainer.def` is a faithful translation of
  `gcp/mlip-cell-runner/Dockerfile.unified`: same base
  (`nvidia/cuda:12.1.1-devel-ubuntu22.04`), two-stage build (Rust engine →
  CUDA runtime), per-backend dependency groups selected at build time
  (`--build-arg BACKEND=<mace|chgnet|m3gnet|orb|sevennet>`, Apptainer ≥ 1.2;
  a sed-render fallback for older versions is documented in the def).
  Intentional deltas from the Dockerfile (no USER directive, runscript vs
  ENTRYPOINT) are annotated in-file.
- Runs rootless; `%post` performs only package installs. Honest caveat: the
  def has not yet been built on a real cluster — it is a reviewed
  translation, and the first facility build is the true test.
- Facilities standardized on Shifter or podman-hpc (e.g. NERSC) can pull the
  OCI image built from `Dockerfile.unified`; the runner is plain Python and
  also works from a site venv with `pip install -e ./python`.

## Filesystem contract

- All writes go under the caller-specified `--artifact-prefix` directory
  (per-cell results, batch summaries, checkpoints).
- Checkpointing is SHA-256 content-addressed and idempotent: preempted SLURM
  array tasks resume without recomputing finished cases.

## Resource envelope

- Per cell: 1 GPU (L4-class or better), ~16 GiB RAM, minutes-scale wall
  time — mirrors this project's Cloud Run job configuration
  (`gcp/mlip-cell-runner/cloudbuild.yaml`).
- Reference SLURM job array: `hpc/slurm/run_cells.sbatch` (one array index =
  one cell; embarrassingly parallel, no inter-task communication).

## Licenses

- Code: AGPL-3.0-or-later. Running unmodified code imposes no obligations on
  the facility or lab; AGPL's network clause applies only to parties who
  modify the code and offer it as a network service. Contributing results
  data creates no code obligations.
- First-party content: CC BY-SA 4.0; structured data: ODbL 1.0 (see NOTICE.md).
- Third-party potentials and datasets retain upstream licenses (NIST IPR,
  OpenKIM); `data/mlip_benchmarks/manifest_sources.json` records license and
  stewardship per source.

## Verification commands

```bash
# 1. Offline end-to-end, with network entry points forced to fail:
python3 -m pytest gcp/mlip-cell-runner/test_runner_offline.py -q

# 2. All URL/network handling in the runner is in one file — inspect it:
grep -n "urlopen\|urllib\|requests\|gs://" gcp/mlip-cell-runner/mlip_cell_runner.py

# 3. Telemetry default:
sed -n '15,25p' gcp/mlip-cell-runner/src/openinference_patcher.py

# 4. Full test suite (no GPU, no network, no credentials):
python3 -m pytest gcp tools -q && (cd python && python3 -m pytest -q)
```
