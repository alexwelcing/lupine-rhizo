"""Unit-conversion constants for the statics core.

The eV/A^3 -> GPa factor matches the one used by
``python/scripts/run_ni_gpu_loop.py`` so pressures agree across the repo.
"""

from __future__ import annotations

from typing import Final

# 1 eV/A^3 in GPa.
EV_PER_A3_TO_GPA: Final[float] = 160.21766208

# 1 eV/A^2 in J/m^2 (1 eV = 1.602176634e-19 J, 1 A^2 = 1e-20 m^2).
EV_PER_A2_TO_J_PER_M2: Final[float] = 16.02176634

# 1 J/m^2 in mJ/m^2 (stacking-fault energies are quoted in mJ/m^2).
J_PER_M2_TO_MJ_PER_M2: Final[float] = 1000.0

__all__ = [
    "EV_PER_A2_TO_J_PER_M2",
    "EV_PER_A3_TO_GPA",
    "J_PER_M2_TO_MJ_PER_M2",
]
