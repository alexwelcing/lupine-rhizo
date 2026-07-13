# LAMMPS end-to-end validation — fcc Ni EAM elastic constants (2026-07-13)

Replaces the SYNTHETIC demo logs (`hpc/examples/sample_logs/ni_eam_elastic.log`)
with a REAL native-Windows LAMMPS run, piped through the full evidence bridge
(`lupine_distill.lammps_ingest`) to a Lean module.

## Environment

- LAMMPS: `C:\lammps\bin\lmp.exe`, banner `LAMMPS (30 Mar 2026)`, serial (MPI STUBS), MinGW.
- Python module: `C:\lammps\Python\lammps` (ctypes -> `C:\lammps\bin\liblammps.dll`),
  driven from `.venv-mlip312` (Python 3.12), `lmp.version()` = `20260330`.
- CPU only. No torch, no GPU, no MLIP model loads (GPU reserved for concurrent calibration).

## What ran

1. **Serial exe leg** — `C:\lammps\Examples\ELASTIC` copied to `work/`,
   `init.mod` adapted to fcc Ni (`lattice fcc 3.52`, mass 58.6934),
   `potential.mod` adapted to `pair_style eam` + `C:/lammps/Potentials/Ni_u3.eam`.
   Run: `lmp.exe -in in.elastic.lmp -log log.ni_eam_elastic.serial` (96 atoms, < 1 s).
2. **Python-module leg** — same input via `from lammps import lammps; lmp.file("in.elastic.lmp")`
   (`work/python_leg.py`, log `work/log.ni_eam_elastic.python`). Results identical to the exe leg
   to ~1e-9 GPa (`work/python_leg_results.json`).
3. **MLIAP/SNAP probes** (runtime, query-only): `has_style('pair','mliap')` = **True**,
   `has_style('pair','snap')` = **True**, `has_style('pair','eam')` = True.
   ML packages built in: ML-HDNNP, ML-IAP, ML-POD, ML-RANN, ML-SNAP, ML-UF3.
4. **SNAP static check** (MLIP-inside-LAMMPS lane, classical CPU path):
   fcc Ni, `Ni_Zuo_JPCA2020.snap[coeff|param]` (linear SNAP, Zuo et al. JPCA 2020),
   box/relax iso minimize -> **a0 = 3.5215 Å**, **E = -5.7807 eV/atom** (32 atoms).
5. **Ingest pipeline** — `python -m lupine_distill.lammps_ingest parse ... | lean ...`
   over the real serial log -> `evidence.json` (`lupine.mlip.lammps_evidence.v1`,
   log sha256 6e90a94246fc...) -> `Ni_EAM_real.lean`.
6. **Test suite** — `archive/2026-07-01/python/tests/test_lammps_ingest.py` restored to
   `python/tests/` unchanged: **24 passed** in 0.55 s.

## Numbers — real Ni_u3 EAM vs Simmons & Wang 1971 (experiment, 300 K)

| Property | Real EAM (this run) | Synthetic demo log | Reference | abs err | 5% tol | Verdict (theorem) |
|----------|--------------------:|-------------------:|----------:|--------:|-------:|-------------------|
| C11 (GPa) | 233.2731 | 246.79 | 246.5 | 13.2269 | 12.3250 | **EXCEEDS** (`lammps_exceeds_tol_...C11`) |
| C12 (GPa) | 154.2873 | 147.32 | 147.3 |  6.9873 |  7.3650 | within (`lammps_within_tol_...C12`) |
| C44 (GPa) | 127.6366 | 124.85 | 124.7 |  2.9366 |  6.2350 | within (`lammps_within_tol_...C44`) |

Bulk modulus 180.6159 GPa, shear modulus 1 = 127.6366 GPa, shear modulus 2 = 39.4929 GPa,
Poisson ratio 0.3981. Cubic symmetry holds to ~1e-9 GPa (C11=C22=C33 etc.; off-diagonal
couplings ~1e-9 GPa), i.e. genuine converged physics, not noise.

The real values match the published Foiles "universal 3" Ni EAM elastic constants
(C11 = 233, C12 = 154, C44 = 128 GPa) — the committed synthetic demo log
(`hpc/examples/generated/Ni_EAM.lean`, C11 = 246.79) was optimistic fiction. The pipeline
handles the honest outcome correctly: the real C11 misses the 5% experimental tolerance by
0.9 GPa and `emit_lean_module` encodes that as a decidable `exceeds_tol` theorem instead of
hiding it. Structure of `Ni_EAM_real.lean` is otherwise identical to the committed demo
(same namespace, same theorem naming, same x1000 Nat encoding, 0 sorry).

## Verdict

**PASS** — the system integrates correctly with native LAMMPS end-to-end with real physics:
exe leg, python-module leg (bit-identical physics), MLIAP/SNAP capability probes, a real SNAP
(MLIP) static evaluation, schema-validated evidence, Lean emission, and a green test suite.
The one `exceeds_tol` verdict is a property of the Ni_u3 potential vs experiment, not of the
integration.

## Files

- `evidence.json` — lammps_evidence.v1 payload from the real serial log.
- `Ni_EAM_real.lean` — emitted Lean module (2 within_tol + 1 exceeds_tol).
- `work/log.ni_eam_elastic.serial` — real exe-leg log (parsed one).
- `work/log.ni_eam_elastic.python` — python-module leg log.
- `work/log.ni_snap_static.python` — SNAP static check log.
- `work/python_leg.py`, `work/python_leg_results.json` — python legs driver + JSON summary.
- `work/init.mod`, `work/potential.mod`, `work/in.elastic.lmp`, `work/displace.mod` — inputs.
  (restart/dump files deleted; unused Si.sw / local Ni_u3.eam copy removed.)
