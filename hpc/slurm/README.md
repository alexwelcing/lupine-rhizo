# SLURM lane for the MLIP cell runner (offline)

Run the exact benchmark cell contract from `gcp/mlip-cell-runner/mlip_cell_runner.py`
on any Apptainer + SLURM cluster with no GCP account, no Cloudflare worker, and
no tokens. One array index runs one cell of a `lupine.mlip.batch_spec.v1` spec.

Contract guarantees (covered by `gcp/mlip-cell-runner/test_runner_offline.py`):

- `--manifest-url`, `--batch-spec-url`, `--distill-policy-url`, and
  `--checkpoint-url` accept plain local paths or `file://` URLs.
- `--artifact-prefix` may be a local directory; `cell_result.json`
  (schema `lupine.mlip.cell_artifact.v1`) and `cell_checkpoint.json` land there.
- Without `--beat-emit-url` (and no `--local-jsonl`), beats are skipped
  silently; the printed `lupine.mlip.cell_result.v1` metrics are the record.

## Zero to results

```bash
# 0. On a connected host: clone the repo and build the image (Apptainer >= 1.2).
git clone <repo> lupine-rhizo && cd lupine-rhizo
apptainer build --build-arg BACKEND=mace mlip-runner-mace.sif hpc/Apptainer.def
# Backends: mace | chgnet | sevennet | orb | matgl | uma (one .sif per backend).
# Copy the .sif, the repo checkout, and your fixture manifests to the cluster.

# 1. On the cluster: explode the batch spec into one cell per line.
python3 hpc/slurm/make_cells.py path/to/batch_spec.json \
    --out cells.jsonl \
    --artifact-root "$SCRATCH/mlip-results/cells"
# Prints the cell count and the exact sbatch command.

# 2. Submit the array (N = number of lines in cells.jsonl).
mkdir -p logs
N=$(wc -l < cells.jsonl)
sbatch --array=0-$((N-1)) \
    --export=ALL,SIF="$PWD/mlip-runner-mace.sif",CELLS_JSONL="$PWD/cells.jsonl",RESULTS_DIR="$SCRATCH/mlip-results" \
    hpc/slurm/run_cells.sbatch

# 3. Watch and collect.
squeue --me
ls "$SCRATCH/mlip-results"/task-*/batch_result.json
```

Notes:

- A batch spec is the same JSON the managed lane uses: `schema`,
  `batch_id`/`run_id`/`campaign_id`, `defaults` (e.g. `manifest_url`,
  `checkpoint_mode`), and a `cells` array (`cell_id`, `row_id`, `mlip_id`,
  `variant_id`). All referenced paths must be local (or `file://`) and visible
  to the compute node; release fixtures live in `gcp/mlip-cell-runner/fixtures/`
  and distill policies in `gcp/mlip-cell-runner/policies/`.
- `run-batch` requires one `mlip_id` per spec; keep one spec (and one `.sif`)
  per backend.
- MLIP weights: most backends download checkpoints on first use. On an
  air-gapped cluster, pre-fetch the model cache on the connected build host
  (run one cell there) and copy the cache directory (e.g. `~/.cache`) along
  with the `.sif`, binding it into the job.
- Set `EMIT_LOCAL_BEATS=1` in `--export` to also write a `beats.jsonl` per
  task (each line carries the `lupine.mlip.cell_result.v1` metrics).

## Resource guidance

Mirrors the managed Cloud Run job shape in `gcp/mlip-cell-runner/cloudbuild.yaml`
(`--cpu=4 --memory=16Gi --gpu=1 --gpu-type=nvidia-l4 --task-timeout=3600s`):

| Resource | Per array task |
| --- | --- |
| GPU | 1 (L4-class or better; `--nv` passes the host driver through) |
| CPU | 4 cores |
| Memory | 16 GiB |
| Walltime | minutes per cell; 1 h limit is generous headroom |

If your site uses `--gres=gpu:1` instead of `--gpus=1`, adjust the `#SBATCH`
line in `run_cells.sbatch` accordingly.

## Where results land

For array task `K`, under `RESULTS_DIR` (default `./results`):

```
task-000K/
  cell_spec.json             # the single-cell batch spec this task ran
  batch_result.json          # lupine.mlip.batch_result.v1 summary
  batch_result.stdout.json   # same summary, captured from stdout
  beats.jsonl                # only with EMIT_LOCAL_BEATS=1
<artifact-root>/<cell_id>/
  cell_result.json           # lupine.mlip.cell_artifact.v1 (per-cell evidence)
  cell_checkpoint.json       # unless checkpoint_mode: off
  distill_events.jsonl       # distill variants only
```

SLURM stdout/stderr logs land in `logs/mlip-cells-<jobid>_<index>.out`.
