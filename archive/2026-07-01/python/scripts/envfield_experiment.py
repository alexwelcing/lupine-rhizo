"""Run-level environment-field correction experiment (paper §2.5).

Fits the coordination error field for (CHGNet, Ni) and (CHGNet, Cu) from the
bound Y-matrix evidence, deploys it as a force-bearing correction beside the
live CHGNet calculator, and validates at three levels:

  1. statics — corrected surface energies (γ₁₀₀, γ₁₁₀ BLIND, γ₁₁₁), vacancy
     formation, and bulk sanity (a₀, B₀ shift);
  2. forces — RMSE against a stronger-model proxy (MACE-MPA-0) on rattled
     Ni(110) slabs, surface layer and all atoms;
  3. dynamics — 1,000-step 300 K Langevin NVT on the Ni(110) slab: stability,
     energy drift, and wall-time overhead of the correction.

Results are written to data/y_matrix_runs/envfield_experiment/ as measured,
favorable or not. GPU venv required (chgnet + mace).
"""

from __future__ import annotations

import json
import math
import pathlib
import sys
import time

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "python"))

EV_PER_JM2_A2 = 1.0 / 16.0218
OUT = ROOT / "data" / "y_matrix_runs" / "envfield_experiment"
SEED = 20260702


def load_field_knots(model_id: str, material: str) -> tuple[dict[float, float], float]:
    """Measure the field knots from bound evidence; return (knots, model a0)."""
    ev_path = ROOT / "data" / "y_matrix_runs" / "bound" / f"{material}_fcc_{model_id}.evidence.json"
    run_path = ROOT / "data" / "y_matrix_runs" / f"{material}_fcc_{model_id}.json"
    ev = json.loads(ev_path.read_text(encoding="utf-8"))
    run = json.loads(run_path.read_text(encoding="utf-8"))
    a0 = run["results"]["lattice"]["values"]["a0_angstrom"]
    err = {}
    for p in ev["properties"]:
        if p.get("reference_value") is not None:
            err[p["name"]] = p["value"] - p["reference_value"]
    a100, a111 = a0 * a0 / 2.0, math.sqrt(3.0) / 4.0 * a0 * a0
    knots = {
        8.0: err["gamma_100"] * a100 * EV_PER_JM2_A2,
        9.0: err["gamma_111"] * a111 * EV_PER_JM2_A2,
        11.0: err["vacancy_formation_energy"] / 12.0,
        12.0: 0.0,
    }
    return knots, a0


def main() -> int:
    import os

    os.environ.setdefault("TORCHDYNAMO_DISABLE", "1")
    from ase.build import fcc110
    from ase.calculators.mixing import SumCalculator
    from ase.md.langevin import Langevin
    from ase import units
    from chgnet.model.dynamics import CHGNetCalculator
    from mace.calculators import mace_mp

    from lupine_distill.statics import (
        compute_lattice,
        compute_surface_energy,
        compute_vacancy_formation,
    )
    from lupine_distill.statics.envfield import FieldCorrectionCalculator, fcc_cutoffs

    OUT.mkdir(parents=True, exist_ok=True)
    report: dict = {"seed": SEED, "device": "cuda", "materials": {}}

    chgnet = CHGNetCalculator(use_device="cuda")

    # ---- 1. statics per material ---------------------------------------
    refs = {}
    for mat in ("Ni", "Cu"):
        knots, a0 = load_field_knots("chgnet", mat)
        r_on, r_off = fcc_cutoffs(a0)
        corr = FieldCorrectionCalculator(knots, r_on=r_on, r_off=r_off)
        summed = SumCalculator([chgnet, corr])

        ev = json.loads(
            (ROOT / "data/y_matrix_runs/bound" / f"{mat}_fcc_chgnet.evidence.json").read_text(
                encoding="utf-8"
            )
        )
        refs[mat] = {
            p["name"]: p["reference_value"]
            for p in ev["properties"]
            if p.get("reference_value") is not None
        }
        raw = {p["name"]: p["value"] for p in ev["properties"]}

        block = {"knots": {str(k): v for k, v in knots.items()}, "a0_model": a0,
                 "properties": {}}
        t0 = time.perf_counter()
        lat = compute_lattice(summed, mat, "fcc")
        block["bulk_sanity"] = {
            "a0_raw": a0,
            "a0_corrected": lat.a0_angstrom,
            "a0_shift_A": lat.a0_angstrom - a0,
        }
        for miller in ("100", "110", "111"):
            g = compute_surface_energy(summed, mat, "fcc", miller, lat.a0_angstrom)
            block["properties"][f"gamma_{miller}"] = {
                "raw": raw[f"gamma_{miller}"],
                "corrected": g.gamma_j_per_m2,
                "reference": refs[mat][f"gamma_{miller}"],
                "blind": miller == "110",
            }
        v = compute_vacancy_formation(summed, mat, "fcc", lat.a0_angstrom)
        block["properties"]["E_vac"] = {
            "raw": raw["vacancy_formation_energy"],
            "corrected": v.vacancy_formation_ev,
            "reference": refs[mat]["vacancy_formation_energy"],
            "blind": False,
        }
        block["statics_wall_s"] = round(time.perf_counter() - t0, 1)
        report["materials"][mat] = block
        print(f"[statics] {mat} done in {block['statics_wall_s']}s", flush=True)

    # ---- 2. force validation vs proxy on rattled Ni(110) ----------------
    knots, a0 = load_field_knots("chgnet", "Ni")
    r_on, r_off = fcc_cutoffs(a0)
    corr = FieldCorrectionCalculator(knots, r_on=r_on, r_off=r_off)
    proxy = mace_mp(model="medium-mpa-0", device="cuda", default_dtype="float64")
    rng = np.random.default_rng(SEED)
    base_slab = fcc110("Ni", size=(3, 3, 8), a=a0, vacuum=12.0)
    z = base_slab.positions[:, 2]
    surface_mask = (z > z.max() - 0.1) | (z < z.min() + 0.1)

    def forces_of(calc, atoms):
        a = atoms.copy()
        a.calc = calc
        return a.get_forces()

    sq_raw_all = sq_cor_all = sq_raw_surf = sq_cor_surf = 0.0
    n_all = n_surf = 0
    for _ in range(20):
        cfg = base_slab.copy()
        cfg.positions += rng.normal(0.0, 0.08, cfg.positions.shape)
        f_ref = forces_of(proxy, cfg)
        f_raw = forces_of(chgnet, cfg)
        f_cor = f_raw + forces_of(corr, cfg)
        d_raw, d_cor = f_raw - f_ref, f_cor - f_ref
        sq_raw_all += float(np.sum(d_raw**2)); sq_cor_all += float(np.sum(d_cor**2))
        n_all += d_raw.size
        sq_raw_surf += float(np.sum(d_raw[surface_mask] ** 2))
        sq_cor_surf += float(np.sum(d_cor[surface_mask] ** 2))
        n_surf += int(surface_mask.sum()) * 3
    report["forces_vs_proxy"] = {
        "proxy": "mace-mpa-0-medium",
        "configs": 20, "rattle_A": 0.08,
        "rmse_all_raw": math.sqrt(sq_raw_all / n_all),
        "rmse_all_corrected": math.sqrt(sq_cor_all / n_all),
        "rmse_surface_raw": math.sqrt(sq_raw_surf / n_surf),
        "rmse_surface_corrected": math.sqrt(sq_cor_surf / n_surf),
    }
    print(f"[forces] {report['forces_vs_proxy']}", flush=True)

    # ---- 3. MD: 1000-step NVT, corrected vs raw wall time ---------------
    def run_md(calc, steps):
        slab = fcc110("Ni", size=(3, 3, 8), a=a0, vacuum=12.0)
        slab.calc = calc
        dyn = Langevin(slab, 2.0 * units.fs, temperature_K=300.0, friction=0.02,
                       rng=np.random.default_rng(SEED))
        energies = []
        dyn.attach(lambda: energies.append(slab.get_total_energy()), interval=50)
        t0 = time.perf_counter()
        dyn.run(steps)
        return time.perf_counter() - t0, energies

    t_raw, _ = run_md(chgnet, 200)
    summed = SumCalculator([chgnet, FieldCorrectionCalculator(knots, r_on=r_on, r_off=r_off)])
    t_cor, energies = run_md(summed, 1000)
    report["md"] = {
        "steps": 1000, "timestep_fs": 2.0, "temperature_K": 300.0,
        "wall_s_corrected_1000": round(t_cor, 1),
        "wall_s_raw_200": round(t_raw, 1),
        "overhead_pct": round((t_cor / 5.0 / t_raw - 1.0) * 100.0, 1),
        "total_energy_first_eV": energies[0], "total_energy_last_eV": energies[-1],
        "stable": bool(np.isfinite(energies).all()),
    }
    print(f"[md] {report['md']}", flush=True)

    (OUT / "report.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    print(f"wrote {OUT / 'report.json'}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
