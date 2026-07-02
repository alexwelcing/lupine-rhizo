#!/usr/bin/env bash
# Reference SLURM array job for the offline MLIP cell runner.
# One array index == one cell of a run-batch spec, exploded to cells.jsonl by
# hpc/slurm/make_cells.py. Fully offline: local files in, local files out,
# no GCP, no beat endpoint (beats are skipped silently without --beat-emit-url).
#
# Submit (N = line count of cells.jsonl; make_cells.py prints the command):
#   sbatch --array=0-$((N-1)) hpc/slurm/run_cells.sbatch
#
# Tunables (environment, override at submit time with --export or inline):
#   SIF          path to the Apptainer image        (default: mlip-runner.sif)
#   CELLS_JSONL  path to the exploded cell specs    (default: cells.jsonl)
#   RESULTS_DIR  where per-task results land        (default: $PWD/results)
#   EMIT_LOCAL_BEATS=1  also write beats.jsonl per task (optional)
#
# Resource shape mirrors the managed Cloud Run job config in
# gcp/mlip-cell-runner/cloudbuild.yaml: 4 CPU, 16Gi, 1 GPU (L4-class),
# 1h task timeout. Typical cells finish in minutes.
#SBATCH --job-name=mlip-cells
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --gpus=1
#SBATCH --time=01:00:00
#SBATCH --output=logs/%x-%A_%a.out

set -euo pipefail

SIF="${SIF:-mlip-runner.sif}"
CELLS_JSONL="${CELLS_JSONL:-cells.jsonl}"
RESULTS_DIR="${RESULTS_DIR:-${PWD}/results}"

if [ -z "${SLURM_ARRAY_TASK_ID:-}" ]; then
    echo "SLURM_ARRAY_TASK_ID is not set; submit with sbatch --array=0-(N-1)" >&2
    exit 2
fi

line_no=$((SLURM_ARRAY_TASK_ID + 1))
spec_line="$(sed -n "${line_no}p" "${CELLS_JSONL}")"
if [ -z "${spec_line}" ]; then
    echo "no cell at array index ${SLURM_ARRAY_TASK_ID} in ${CELLS_JSONL}" >&2
    exit 2
fi

task_dir="${RESULTS_DIR}/task-$(printf '%05d' "${SLURM_ARRAY_TASK_ID}")"
mkdir -p "${task_dir}"
printf '%s\n' "${spec_line}" > "${task_dir}/cell_spec.json"

beat_args=()
if [ "${EMIT_LOCAL_BEATS:-0}" = "1" ]; then
    beat_args+=(--local-jsonl "${task_dir}/beats.jsonl")
fi

# --nv exposes the host GPU driver; bind the working dir and results dir so
# the spec's local manifest / policy / artifact paths resolve in-container.
apptainer exec --nv \
    --bind "${PWD},${RESULTS_DIR}" \
    "${SIF}" \
    python3 /app/mlip_cell_runner.py run-batch \
    --batch-spec-url "file://${task_dir}/cell_spec.json" \
    --batch-artifact-prefix "${task_dir}" \
    ${beat_args[@]+"${beat_args[@]}"} \
    > "${task_dir}/batch_result.stdout.json"

echo "task ${SLURM_ARRAY_TASK_ID} done: ${task_dir}/batch_result.json"
