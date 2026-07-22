"""Diagnostic: path-0 (Ag-F-Li) image 3 — GPAW electronic state + grid sensitivity.

The union campaign measured a 4.2 eV T1 wander on path-0 (GPAW dense barrier
5.79 eV vs VASP reference 1.58 eV). This script recomputes image 3 (the saddle
region) at (a) adopted settings h=0.20/Gamma and (b) h=0.18/Gamma, with GPAW
text output kept, to check SCF behavior and grid sensitivity. Existing
checkpoint energies already cover the barrier itself.

Run:  .venv/bin/python gcp/sparse-dft-pilot/diagnose_path0_wander.py
Output: /tmp/z1-diagnose/{img3-adopted,img3-h018}.json + .txt
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "mlip-cell-runner"))

from z1_barrier import atoms_from_image  # noqa: E402

OUT = Path("/tmp/z1-diagnose")
OUT.mkdir(parents=True, exist_ok=True)

PANEL = Path("/tmp/z1-union-local/inputs/panel.lock.json")

SETTINGS = {
    "adopted": {"mode": "fd", "xc": "PBE", "h": 0.20, "kpts": (1, 1, 1)},
    "h018": {"mode": "fd", "xc": "PBE", "h": 0.18, "kpts": (1, 1, 1)},
}


def main():
    from gpaw import GPAW

    panel = json.loads(PANEL.read_text())
    images = panel["paths"][0]["input_images"]
    for label, params in SETTINGS.items():
        name = f"img3-{label}"
        dest = OUT / f"{name}.json"
        if dest.exists():
            print(f"{name}: {json.loads(dest.read_text())['energy_ev']:.4f} eV (cached)")
            continue
        atoms = atoms_from_image(images[3])
        atoms.calc = GPAW(txt=str(OUT / f"{name}.txt"), **params)
        e = float(atoms.get_potential_energy())
        dest.write_text(json.dumps({"energy_ev": e, "params": {k: str(v) for k, v in params.items()}}))
        print(f"{name}: {e:.4f} eV")

    print("\n--- checkpoint context (adopted settings, from campaign) ---")
    for idx in (0, 1, 2, 3, 4, 5, 6):
        ck = Path(f"/tmp/z1-union-local/anchors/path-0/anchor-{idx}.json")
        if ck.exists():
            d = json.loads(ck.read_text())
            print(f"img{idx}: gpaw {d['gpaw_energy_ev']:.4f}  ref {d['reference_energy_ev']:.4f}")


if __name__ == "__main__":
    main()
