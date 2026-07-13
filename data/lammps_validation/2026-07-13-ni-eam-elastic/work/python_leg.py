"""Python-module leg of the LAMMPS validation (CPU only, no torch).

Leg A: drive the same examples/ELASTIC fcc-Ni EAM input via the native
       C:\\lammps\\Python `lammps` module (ctypes -> liblammps.dll).
Leg B: runtime probes for pair styles mliap / snap / eam (query only).
Leg C: SNAP static check: fcc Ni with Ni_Zuo_JPCA2020.snap[coeff|param],
       box/relax iso minimize -> a0 and cohesive E only. Classical CPU path.

Emits a JSON summary to python_leg_results.json.
"""

import json
import sys
import traceback

RESULTS = {"legA_elastic_via_module": {}, "legB_probes": {}, "legC_snap_static": {}}


def leg_a():
    from lammps import lammps

    lmp = lammps(cmdargs=["-log", "log.ni_eam_elastic.python", "-screen", "none", "-nocite"])
    out = {"lammps_version": lmp.version()}
    lmp.file("in.elastic.lmp")
    for var in ("C11cubic", "C12cubic", "C44cubic", "bulkmodulus", "shearmodulus1", "poissonratio"):
        out[var] = lmp.extract_variable(var, None, 0)
    out["natoms"] = lmp.get_natoms()
    lmp.close()
    return out


def leg_b():
    from lammps import lammps

    lmp = lammps(cmdargs=["-log", "none", "-screen", "none", "-nocite"])
    out = {
        "version": lmp.version(),
        "has_style_pair_mliap": bool(lmp.has_style("pair", "mliap")),
        "has_style_pair_snap": bool(lmp.has_style("pair", "snap")),
        "has_style_pair_eam": bool(lmp.has_style("pair", "eam")),
    }
    try:
        pkgs = lmp.installed_packages
        out["installed_packages_ml"] = sorted(p for p in pkgs if p.startswith("ML"))
    except Exception as exc:  # noqa: BLE001 - probe only, record and continue
        out["installed_packages_error"] = repr(exc)
    lmp.close()
    return out


def leg_c():
    from lammps import lammps

    lmp = lammps(cmdargs=["-log", "log.ni_snap_static.python", "-screen", "none", "-nocite"])
    lmp.commands_string(
        """
units metal
boundary p p p
lattice fcc 3.52
region box block 0 2 0 2 0 2
create_box 1 box
create_atoms 1 box
mass 1 58.71
pair_style snap
pair_coeff * * C:/lammps/Potentials/Ni_Zuo_JPCA2020.snapcoeff C:/lammps/Potentials/Ni_Zuo_JPCA2020.snapparam Ni
neighbor 1.0 bin
min_style cg
fix relax all box/relax iso 0.0
thermo 10
thermo_style custom step pe press lx
minimize 0.0 1.0e-10 200 2000
variable natoms equal count(all)
variable a0 equal lx/2.0
variable epa equal pe/count(all)
"""
    )
    out = {
        "natoms": int(lmp.extract_variable("natoms", None, 0)),
        "a0_angstrom": lmp.extract_variable("a0", None, 0),
        "energy_per_atom_eV": lmp.extract_variable("epa", None, 0),
        "potential": "Ni_Zuo_JPCA2020.snap (SNAP, Zuo et al. JPCA 2020)",
    }
    lmp.close()
    return out


def main():
    for name, fn in (("legA_elastic_via_module", leg_a), ("legB_probes", leg_b), ("legC_snap_static", leg_c)):
        try:
            RESULTS[name] = {"ok": True, **fn()}
        except Exception:  # noqa: BLE001 - validation harness: record full traceback
            RESULTS[name] = {"ok": False, "traceback": traceback.format_exc()}
    with open("python_leg_results.json", "w", encoding="utf-8") as fh:
        json.dump(RESULTS, fh, indent=2)
    print(json.dumps(RESULTS, indent=2))
    return 0 if all(v.get("ok") for v in RESULTS.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
