#!/usr/bin/env python3
"""End-to-end demo: LAMMPS logs -> lammps_evidence.v1 JSON -> Lean 4 module.

Runs the same code path a visiting LAMMPS user drives via the CLI
(``python3 -m lupine_distill.lammps_ingest``), on the synthetic sample logs in
``sample_logs/``. Everything is written under ``generated/`` — deliberately
OUTSIDE ``lean-spec/`` so nothing here enters the lake build; admission into
lean-spec is a reviewed step (see README.md).

Deterministic: provenance is the sha256 of the log text and no timestamp is
recorded, so re-running reproduces the committed artifacts byte-for-byte.

Run from the repo root (lupine_distill is pip-installed from ./python):

    python3 hpc/examples/lammps_to_lean_demo.py
"""

from __future__ import annotations

import json
from pathlib import Path

from lupine_distill.lammps_ingest import build_evidence, emit_lean_module, parse_thermo_log

HERE = Path(__file__).resolve().parent
LOGS = HERE / "sample_logs"
OUT = HERE / "generated"

# Experimental fcc Ni elastic constants at 300 K (GPa).
NI_REFERENCES = {"C11": 246.5, "C12": 147.3, "C44": 124.7}
NI_REF_SOURCE = "Simmons & Wang 1971 (300 K single-crystal experiment)"


def main() -> int:
    OUT.mkdir(exist_ok=True)

    elastic_text = (LOGS / "ni_eam_elastic.log").read_text(encoding="utf-8")
    elastic = build_evidence(
        elastic_text,
        material="Ni",
        potential_id="Ni_u3.eam",
        references=NI_REFERENCES,
        reference_source=NI_REF_SOURCE,
        input_script="in.elastic",
        log_name="ni_eam_elastic.log",
    )

    thermo_text = (LOGS / "ni_eam_thermo.log").read_text(encoding="utf-8")
    thermo = build_evidence(
        thermo_text,
        material="Ni",
        potential_id="Ni_u3.eam",
        properties=[],  # a plain thermo log carries no summary properties
        trajectory=parse_thermo_log(thermo_text),
        log_name="ni_eam_thermo.log",
    )

    for name, evidence in (("ni_eam_elastic", elastic), ("ni_eam_thermo", thermo)):
        path = OUT / f"{name}.evidence.json"
        payload = json.dumps(evidence.model_dump(mode="json", by_alias=True), indent=2)
        path.write_text(payload + "\n", encoding="utf-8")
        print(f"evidence -> {path.relative_to(HERE)}")

    lean_path = emit_lean_module([elastic, thermo], OUT / "Ni_EAM.lean")
    print(f"lean     -> {lean_path.relative_to(HERE)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
