# Local workstation validation (NVIDIA GPU + CPU)

Run the offline MLIP cell-runner lane on your own box and walk into the
meeting with `report.md`. No cloud, no beat endpoint: local manifest in,
local artifacts out.

## 1. Environment (your box, once)

CUDA build of torch (check <https://pytorch.org/get-started/locally/> for the
current CUDA tag; `cu126` is current as of this writing):

```bash
pip install torch --index-url https://download.pytorch.org/whl/cu126
pip install mace-torch
pip install -e ./python          # lupine_distill (from the repo root)
```

**Front-load the checkpoint on a networked node.** The first `mace_mp` call
downloads the MACE-MP medium checkpoint from GitHub releases; on restricted
networks that download 403s mid-run. Do one throwaway load while you still
have network:

```bash
python -c "from mace.calculators import mace_mp; mace_mp(model='medium', device='cpu')"
```

Zero-network fallback: **chgnet** ships its weights inside the pip wheel and
runs fully offline. On Debian-family systems install it as:

```bash
pip install --use-pep517 nvidia-ml-py3 bibtexparser   # works around the Debian setuptools install_layout bug
pip install chgnet
```

## 2. Run (CPU + GPU)

From the repo root:

```bash
python3 hpc/local_validation/run_validation.py \
  --run-id "$(hostname)-$(date +%Y%m%d)" \
  --mlip mace-mp-0 \
  --device cpu --device cuda
```

Defaults if you drop the flags: rows `energy_volume forces elastic_constants`,
manifest `gcp/mlip-cell-runner/fixtures/ni_fcc_eam_distill_support_v1.json`,
devices auto (cpu, plus cuda when torch sees a GPU). Add `--mlip chgnet` for
the offline fallback, `--row stress --row relaxation_stability` for more rows.

The driver runs `gcp/mlip-cell-runner/mlip_cell_runner.py run-cell` once per
(row, mlip, device): the CPU leg gets `CUDA_VISIBLE_DEVICES=''`, the CUDA leg
inherits your environment, and the runner auto-selects its device. Checkpoints
are disabled so every leg computes fresh predictions (honest timing).

## 3. Where results land

`tmp/local_validation_<run-id>/` (or `--out DIR`):

- `report.md` — the meeting handout: per row × mlip × device table with
  headline error metric, 0-1 score, wall time, and CPU-vs-GPU speedups, plus
  an honest-notes section (failed legs, mislabeled device legs, caveats).
- `report.json` — the same data, schema
  `lupine.mlip.local_validation_report.v1`, for downstream tooling.
- `cells/<row>/<mlip>/<device>/` — raw `cell_result.json` per leg plus the
  runner's stdout/stderr for debugging.

Exit code is 0 only if every leg succeeded.

## 4. Expected runtimes

Minutes-scale, not hours: on a recent workstation the default 3-row ×
1-mlip × 2-device grid is roughly 1-5 minutes end to end. Each leg pays
model load (a few seconds to ~1 min on first CUDA init) plus inference over
5-24 small fcc-Ni structures. CPU legs of mace-mp-0 are the slowest; the tiny
structures mean GPU speedups here are real but modest — this validates the
lane and gives honest workstation numbers, it is not a throughput benchmark.

## Smoke test without any MLIP install

```bash
python3 hpc/local_validation/run_validation.py --run-id smoke --mlip mock-mlip --device cpu
```

`mock-mlip` (any id starting with `mock`) routes through
`mock_backend_shim.py`: constant energy, zero forces/stress. It validates the
plumbing and the report format, not physics. The same path is exercised by
`gcp/mlip-cell-runner/test_local_validation.py` (`pytest -m integration`).
