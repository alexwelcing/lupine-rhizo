#!/usr/bin/env python3
"""Run mlip_cell_runner with a deterministic mock calculator.

Used by run_validation.py for mlip ids starting with "mock" so the local
validation plumbing (subprocess invocation, artifact aggregation, report
rendering) can be exercised without downloading any MLIP checkpoint. The mock
mirrors the ConstantEnergyCalculator used by the offline contract tests in
gcp/mlip-cell-runner/test_runner_offline.py: constant energy, zero forces and
stress. Metrics produced this way validate plumbing, not physics.
"""

from __future__ import annotations

import pathlib
import sys

RUNNER_DIR = pathlib.Path(__file__).resolve().parents[2] / "gcp" / "mlip-cell-runner"
sys.path.insert(0, str(RUNNER_DIR))

import mlip_cell_runner as runner  # noqa: E402
import numpy as np  # noqa: E402
from ase.calculators.calculator import Calculator, all_changes  # noqa: E402


class MockCalculator(Calculator):
    implemented_properties = ["energy", "forces", "stress"]

    def calculate(self, atoms=None, properties=("energy",), system_changes=all_changes):
        super().calculate(atoms, properties, system_changes)
        n = len(atoms)
        self.results = {
            "energy": -1.0 * n,
            "forces": np.zeros((n, 3)),
            "stress": np.zeros(6),
        }


def main() -> int:
    runner.load_calculator = lambda mlip_id: MockCalculator()
    return runner.main()


if __name__ == "__main__":
    raise SystemExit(main())
