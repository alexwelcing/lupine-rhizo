# Local MLIP validation report

- Run id: `cloud-cpu-baseline-2026-07-02`
- Generated: 2026-07-02T02:07:17+00:00
- Host: vm (Linux-6.18.5-x86_64-with-glibc2.39)
- Runner stack: python 3.11.15, numpy 2.4.6, ase 3.29.0, torch 2.12.1+cpu, mace-torch 0.3.16, chgnet 0.4.2, cuda_available False
- Manifest: `/home/user/lupine-rhizo/gcp/mlip-cell-runner/fixtures/ni_fcc_eam_distill_support_v1.json`

## Results

| row | mlip | device | ok | metric | error | unit | score | n | wall s | warm s |
|---|---|---|---|---|---|---|---|---|---|---|
| energy_volume | chgnet | cpu | yes | energy_mae_ev_per_atom | 1.294 | ev_per_atom_mae_vs_mishin_eam | 0 | 8 | 3.407 | 0.3368 |
| forces | chgnet | cpu | yes | force_rmse_ev_per_angstrom | 0.1244 | ev_per_angstrom_rmse_vs_mishin_eam | 0.378 | 5 | 4.123 | 1.046 |
| elastic_constants | chgnet | cpu | yes | elastic_cij_mae_gpa | 25.63 | gpa_mae_vs_literature_cij | 0.268 | 24 | 3.945 | 0.9647 |

## CPU vs GPU speedup

No (row, mlip) had both a successful cpu leg and a successful cuda leg.

## Notes

- Wall times are single-sample (one leg per combination, no repeats); treat small differences as noise.
- wall_seconds includes Python startup, manifest load, and model load; warm_inference_seconds isolates the inference loop.
- Checkpoints were disabled (--checkpoint-mode off) so every leg computed fresh predictions; no cached results inflate the speedups.
- Fixture: /home/user/lupine-rhizo/gcp/mlip-cell-runner/fixtures/ni_fcc_eam_distill_support_v1.json — a distill *support* fixture, not the sealed evaluation fixture; scores are row-native 0-1 scores against its references.
- No cuda leg was run on this host; cpu_vs_gpu speedups are unavailable.
