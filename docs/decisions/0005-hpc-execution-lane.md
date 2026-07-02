# ADR 0005: Vendor-neutral HPC execution lane for benchmark cells

**Status:** Accepted

**Date:** 2026-07-02

## Context

The MLIP benchmark cell contract lives in
`gcp/mlip-cell-runner/mlip_cell_runner.py` (`run-cell` / `run-batch`) and has so
far executed only on the managed GCP lane: Cloud Run Jobs built by
`gcp/mlip-cell-runner/cloudbuild.yaml`, `gs://` artifact storage, and beats
posted to the Cloudflare worker with GCP identity tokens.

External labs now need to run the same benchmark cells on their own
superclusters. Those environments are Apptainer + SLURM, frequently air-gapped:
no GCP service accounts, no Cloudflare worker, no tokens, and often no outbound
network from compute nodes. Asking a partner lab to adopt our cloud stack to
reproduce a benchmark is a non-starter, and results produced on a divergent
runner would not be comparable evidence.

## Decision

Add a vendor-neutral HPC lane under `hpc/` that reuses the existing cell
contract unchanged:

- **Same runner, file-based I/O.** `mlip_cell_runner.py` accepts plain local
  paths or `file://` URLs for manifests, batch specs, distill policies, and
  checkpoints; artifacts land in a local `--artifact-prefix` directory; without
  `--beat-emit-url` beats are skipped silently. The offline contract is pinned
  by integration tests in `gcp/mlip-cell-runner/test_runner_offline.py`.
- **Apptainer image.** `hpc/Apptainer.def` is a faithful translation of
  `gcp/mlip-cell-runner/Dockerfile.unified`: same CUDA base, same
  backend-at-build-time selection (`--build-arg BACKEND=<backend>` against the
  optional-deps groups in `python/pyproject.toml`), same fail-closed build
  checks.
- **SLURM array execution.** `hpc/slurm/make_cells.py` explodes a
  `lupine.mlip.batch_spec.v1` spec into `cells.jsonl`;
  `hpc/slurm/run_cells.sbatch` maps one array index to one cell via
  `apptainer exec --nv`. Submission and resource guidance live in
  `hpc/slurm/README.md`, mirroring the Cloud Run job shape
  (1 GPU / 4 CPU / 16Gi / minutes per cell).

The managed GCP lane remains production and is unchanged: same defaults, same
output schemas (`lupine.mlip.cell_result.v1`, `lupine.mlip.cell_artifact.v1`,
`lupine.mlip.batch_result.v1`). The HPC lane is a second consumer of the same
contract, not a fork of it.

## Alternatives considered

- **GCP-only (status quo).** Keeps one lane to operate, but external labs
  cannot legally or practically route their compute through our project, and
  air-gapped clusters cannot reach GCS or the worker at all. Rejected: it
  blocks exactly the collaborations the benchmark exists for.
- **Hugging Face Jobs (or similar hosted GPU runners).** Low setup cost and a
  familiar surface, but still a third-party cloud: requires tokens and outbound
  network, offers no SLURM integration, and does not run inside a partner
  lab's security boundary. Rejected for the external-lab case; it remains an
  option for ad-hoc public reproductions.
- **A separate lightweight runner script for HPC.** Tempting for simplicity,
  but a second implementation would drift from the fixture contract and make
  cross-lane results incomparable. Rejected: fidelity of evidence is the
  point.

## Consequences

### Positive

- A lab can go from `git clone` to `cell_result.json` with only Apptainer,
  SLURM, and a GPU; results carry the same schemas and fixture hashes as the
  managed lane, so they aggregate together.
- Offline behavior is now an explicitly tested contract, not an accident of
  code paths.

### Negative / mitigations

- Two execution lanes to keep honest. Mitigate: the sbatch script shells into
  the same `run-batch` entrypoint, and the offline integration tests run in the
  same CI as the runner.
- Apptainer builds cannot be verified in this repo's CI (no Apptainer, no
  GPU). Mitigate: the definition mirrors the Docker image line-for-line, keeps
  the fail-closed `--help` build checks, and `hpc/slurm/README.md` documents
  the honest limits.
- Model checkpoints still require a one-time connected pre-fetch; documented
  in `hpc/slurm/README.md`.

## Verification

```bash
python3 -m pytest gcp/mlip-cell-runner -q          # offline contract tests
bash -n hpc/slurm/run_cells.sbatch                 # sbatch syntax
python3 hpc/slurm/make_cells.py <spec.json> --out cells.jsonl
```

On a cluster: build the `.sif`, run one array task, and confirm
`batch_result.json` reports `"status": "completed"`.
