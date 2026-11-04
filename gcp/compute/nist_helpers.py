"""NIST paths, crystal heuristics, and LAMMPS execution for the compute lane.

These helpers are shared by the production queue runner and its local driver.
LAMMPS is imported only when execution is requested.
"""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
NIST_ROOT = REPO_ROOT / "gcp" / "nist_ipr"
INDEX_PATH = NIST_ROOT / "index" / "master_index.json"

STRUCTURE_MAP = {
    # FCC
    "Al": ("fcc", 4.05),
    "Cu": ("fcc", 3.615),
    "Ni": ("fcc", 3.524),
    "Ag": ("fcc", 4.09),
    "Au": ("fcc", 4.08),
    "Pt": ("fcc", 3.92),
    "Pd": ("fcc", 3.89),
    "Pb": ("fcc", 4.95),
    "Ca": ("fcc", 5.58),
    "Sr": ("fcc", 6.08),
    "Ir": ("fcc", 3.84),
    "Rh": ("fcc", 3.80),
    # BCC
    "Fe": ("bcc", 2.87),
    "Cr": ("bcc", 2.88),
    "Mo": ("bcc", 3.15),
    "W": ("bcc", 3.16),
    "V": ("bcc", 3.03),
    "Nb": ("bcc", 3.30),
    "Ta": ("bcc", 3.31),
    "Ba": ("bcc", 5.02),
    # HCP
    "Mg": ("hcp", 3.21),
    "Ti": ("hcp", 2.95),
    "Zn": ("hcp", 2.66),
    "Zr": ("hcp", 3.23),
    "Co": ("hcp", 2.51),
    # Diamond
    "Si": ("diamond", 5.43),
    "Ge": ("diamond", 5.66),
    "C": ("diamond", 3.57),
}


def guess_structure(elements: list[str]) -> tuple[str, float]:
    """Guess crystal structure and lattice constant from element list."""
    if len(elements) == 1:
        el = elements[0]
        if el in STRUCTURE_MAP:
            return STRUCTURE_MAP[el]
        # Default fallback
        return ("fcc", 4.0)
    # For binaries, default to FCC with average lattice constant
    lats = [STRUCTURE_MAP.get(el, ("fcc", 4.0))[1] for el in elements if el in STRUCTURE_MAP]
    avg_lat = sum(lats) / len(lats) if lats else 4.0
    return ("fcc", avg_lat)


def run_lammps(input_script: str, work_dir: Path) -> bool:
    """Run LAMMPS through its Python bindings; return False on failure."""
    try:
        from lammps import lammps
        lmp = lammps(cmdargs=["-screen", "none", "-log", "none"])
        lmp.command("clear")
        for line in input_script.strip().splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                lmp.command(line)
        lmp.close()
        return True
    except Exception as e:
        print(f"  LAMMPS run failed: {e}")
        return False
