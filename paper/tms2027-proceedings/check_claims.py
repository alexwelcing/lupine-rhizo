#!/usr/bin/env python3
"""Claim-lock check for the TMS 2027 proceedings manuscript.

Fails if manuscript.tex asserts any phrase on the sprint contract's "Remove or retire" list
outside an explicit retirement sentence, or if a headline number in the text is not present in
results.json. Run from anywhere:

  python paper/tms2027-proceedings/check_claims.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEX = (HERE / "manuscript.tex").read_text(encoding="utf-8")
RES = json.loads((HERE / "results.json").read_text(encoding="utf-8"))

# Phrases that may only appear inside a sentence that explicitly retires/withdraws them.
RETIRED = [
    "roughly 900",
    "559 independent potentials",
    "1,677 independent observations",
    "universal hyper-ribbon",
    "sloppy-model universality class",
    "98% systematic error",
    "98\\% systematic error",
    "14 of 15",
    "deployable correction",
    "unconditional no-harm",
    "all-electron elastic anchor completed",
    "four independent architectures",
    "universal barrier underprediction",
    "DFT-grade",
    "strong win",
    "72.4%",
    "72.4\\%",
]
RETIRE_MARKERS = (
    "retired", "retire", "withdrawn", "withdraw", "replaces", "not defensible", "Not defensible",
    "does not support", "no cross-paradigm", "no strict hyper-ribbon", "not made", "different object",
    "inherits none", "is not", "are not", "do not infer", "neither a", "counted", "described a",
    "accepted poster abstract", "Every completed path", "External DFT accuracy",
)


def sentences(text: str):
    body = re.sub(r"%.*", "", text)
    return re.split(r"(?<=[.!?])\s+|\\\\|&", body)


def main() -> int:
    errors = []
    for s in sentences(TEX):
        for phrase in RETIRED:
            if phrase in s and not any(m in s for m in RETIRE_MARKERS):
                errors.append(f"unretired phrase {phrase!r} in: {s.strip()[:140]}")

    # Headline numbers that must be bound to results.json
    d = RES["derived"]
    q = RES["quoted"]
    bound = {
        "965": d["funnel"]["kim_model_objects_queried"],
        "559": d["funnel"]["born_stable_model_element_tensors"],
        "423": d["funnel"]["distinct_kim_model_ids"],
        "233": d["funnel"]["author_year_short_labels"],
        "1,677": d["funnel"]["scalar_cij_values"],
        "42": d["geometry"]["n_groups"],
        "1.09": round(d["geometry"]["pr_median"], 2),
        "2.29": round(d["geometry"]["pr_max"], 2),
        "21 groups": d["geometry"]["groups_with_n3"],
        "14.55": round(q["global_operator_raw_mae_gpa"]["value"], 2),
        "63.40": round(q["global_operator_corrected_mae_gpa"]["value"], 2),
        "17.84": q["layer2_raw_mae_gpa"]["value"],
        "10.36": q["layer2_oracle_loo_mae_gpa"]["value"],
        "0.26": round(q["classical_vs_mlip_spearman_rho"]["value"], 2),
        "0.34": round(q["classical_vs_mlip_spearman_p"]["value"], 2),
        "0.96": q["y_matrix_raw_cosine_max"]["value"],
        "0.98": q["y_matrix_null_p95_cosine"]["value"],
        "135.0": q["z1_mae_range_mev"]["value"][0],
        "242.5": q["z1_mae_range_mev"]["value"][1],
        "0.906": q["env_field_r"]["value"],
    }
    for token, value in bound.items():
        if token not in TEX:
            errors.append(f"headline token {token!r} (bound value {value}) not found in manuscript")
        expected = token.replace(",", "").replace(" groups", "")
        if str(value).rstrip("0").rstrip(".") not in (expected.rstrip("0").rstrip("."), f"{float(expected):g}" if re.fullmatch(r"[\d.]+", expected) else expected):
            try:
                if abs(float(expected) - float(value)) > 1e-6:
                    errors.append(f"token {token!r} disagrees with results.json value {value}")
            except ValueError:
                errors.append(f"token {token!r} disagrees with results.json value {value}")

    # The Lean inventory is never typed: the manuscript uses macros that
    # build_artifacts.py generates from lean-spec/theorem-count.json, and it carries
    # the scope sentence beside them.
    lean = d["lean"]
    lean_tex_path = HERE / "lean-count.tex"
    macros = dict(re.findall(r"\\newcommand\{\\(Lean\w+)\}\{([^}]*)\}", lean_tex_path.read_text(encoding="utf-8"))) if lean_tex_path.exists() else {}
    expected_macros = {
        "LeanDeclarationCount": str(lean["count"]),
        "LeanModuleCount": str(lean["modules"]),
        "LeanCountedAt": str(lean["counted_at"]),
    }
    if macros != expected_macros:
        errors.append(f"lean-count.tex {macros} disagrees with results.json {expected_macros}; rebuild with build_artifacts.py")
    if lean["zero_sorry"] is not True:
        errors.append("results.json Lean inventory reports sorry, but the manuscript says zero")
    if "\\input{lean-count}" not in TEX:
        errors.append("manuscript does not \\input the generated lean-count.tex")
    for name in expected_macros:
        if f"\\{name}" not in TEX.split("\\input{lean-count}", 1)[-1]:
            errors.append(f"manuscript body does not use \\{name}")
    if re.search(r"\d[\d,]*\s+theorem(?:/lemma)?\s+declarations", re.sub(r"%.*", "", TEX)):
        errors.append("hand-typed Lean declaration count in manuscript; use the generated macros")
    c10 = "Lean 4 checks the arithmetic and stated inequalities behind published numbers; it does not check the physics, the reference data or the pipeline."
    if c10 not in TEX:
        errors.append("Lean scope sentence missing beside the generated count")

    if RES["recovery_outputs_present"] is False and "352" in TEX and "omitted" not in TEX:
        errors.append("352-row ledger referenced without omission statement")

    if errors:
        print("\n".join(errors))
        return 1
    print(f"claim lock OK: {len(RETIRED)} retired phrases guarded, {len(bound)} headline tokens bound, Lean count generated ({lean['count']}, counted {lean['counted_at']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
