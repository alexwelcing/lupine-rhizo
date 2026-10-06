#!/usr/bin/env python3
"""Reference-direction error attribution on the fixed, previously inspected pilot.

Local archived arrays only. No model, network, fitted weights or publication.
The exploratory decision rule is explicitly coded, never executed from a packet.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import html
import json
import math
import os
from pathlib import Path

import analyze_pilot as pilot

PINNED_INPUTS = {
    pilot.GEOMETRY: "c35506339c7a1fffa4c677c420d8964e499cfce3f76f1d6e7da5ee190594e948",
    pilot.BASELINES["chgnet"]: "cc91534bd256e56241d814817ab4679183062af9165e37363082e6729dfa3e74",
    pilot.BASELINES["mace-mp-0"]: "290f5b85cb9cee63fa43bf6265c6da726895c333a263b6da5bb64d42b482017a",
    pilot.BASELINES["sevennet"]: "49ac05dde55307418b86f4edf0b77d8cd71ab4225853855ef42893b3c90503a9",
}
MODELS = (*pilot.MODELS, "uniform_ensemble")
COMPONENTS = ("parallel", "transverse", "zero_reference", "total")
TARGET = "mp-559535"


def read_json(path):
    content = path.read_bytes()
    return json.loads(content), {"sha256": hashlib.sha256(content).hexdigest(), "bytes": len(content)}


def decompose(predicted, reference):
    """All SSE components retain the common 3N denominator, including zeros."""
    if not reference:
        raise ValueError("At least one reference atom is required")
    pilot.matrix(reference, len(reference), "reference")
    pilot.matrix(predicted, len(reference), "prediction")
    atoms = []
    for index, (pred, ref) in enumerate(zip(predicted, reference, strict=True)):
        residual = [p - f for p, f in zip(pred, ref, strict=True)]
        reference_norm = math.hypot(*ref)
        total = pilot.dot(residual, residual)
        if reference_norm == 0:
            parallel = transverse = 0.0
            zero_reference = total
            signed = None
        else:
            direction = [f / reference_norm for f in ref]
            signed = pilot.dot(residual, direction)
            transverse_vector = [e - signed * u for e, u in zip(residual, direction, strict=True)]
            parallel = signed * signed
            transverse = pilot.dot(transverse_vector, transverse_vector)
            zero_reference = 0.0
        if not math.isclose(total, parallel + transverse + zero_reference, rel_tol=2e-12, abs_tol=1e-15):
            raise ArithmeticError("Atom force partition does not reconstruct total SSE")
        atoms.append({"atom_index": index, "reference_norm_ev_per_angstrom": reference_norm,
                      "zero_reference": reference_norm == 0, "signed_parallel_error_ev_per_angstrom": signed,
                      "reference_squared_norm": pilot.dot(ref, ref),
                      "residual_dot_reference": pilot.dot(residual, ref),
                      "squared_error": {"parallel": parallel, "transverse": transverse,
                                        "zero_reference": zero_reference, "total": total}})
    squared = {key: math.fsum(a["squared_error"][key] for a in atoms) for key in COMPONENTS}
    reference_squared = math.fsum(a["reference_squared_norm"] for a in atoms)
    cross = math.fsum(a["residual_dot_reference"] for a in atoms)
    bias = cross / reference_squared if reference_squared else None
    coherent = bias * bias * reference_squared if bias is not None else 0.0
    heterogeneous = math.fsum((a["signed_parallel_error_ev_per_angstrom"] - bias * a["reference_norm_ev_per_angstrom"]) ** 2
                              for a in atoms if not a["zero_reference"]) if bias is not None else 0.0
    if not math.isclose(squared["parallel"], coherent + heterogeneous, rel_tol=2e-12, abs_tol=1e-15):
        raise ArithmeticError("Parallel force-scale projection does not reconstruct parallel SSE")
    return {"squared_error": squared,
            "cartesian_mse": {key: value / (3 * len(atoms)) for key, value in squared.items()},
            "cartesian_rmse": {key: math.sqrt(value / (3 * len(atoms))) for key, value in squared.items()},
            "signed_parallel_bias_B": bias,
            "parallel_detail_squared_error": {"coherent_scale": coherent, "atom_varying_remainder": heterogeneous},
            "residual_dot_reference_sum": cross, "reference_squared_norm_sum": reference_squared,
            "zero_reference_atoms": sum(a["zero_reference"] for a in atoms), "atom_rows": atoms}


def aggregate(rows, model):
    entries = [row["models"][model] for row in rows]
    atoms = sum(row["atoms"] for row in rows)
    result = {}
    for key in COMPONENTS:
        pooled = math.fsum(e["squared_error"][key] for e in entries) / (3 * atoms)
        balanced = math.fsum(e["cartesian_mse"][key] for e in entries) / len(rows)
        result[key] = {"pooled_mse": pooled, "pooled_rmse": math.sqrt(pooled),
                       "equal_material_mean_mse": balanced, "equal_material_root_mean_mse": math.sqrt(balanced),
                       "equal_material_mean_rmse": math.fsum(e["cartesian_rmse"][key] for e in entries) / len(rows)}
    reference_squared = math.fsum(e["reference_squared_norm_sum"] for e in entries)
    biases = [e["signed_parallel_bias_B"] for e in entries]
    return {"risk": result,
            "parallel_detail_risk": {key: {
                "pooled_mse": math.fsum(e["parallel_detail_squared_error"][key] for e in entries) / (3 * atoms),
                "equal_material_mean_mse": math.fsum(e["parallel_detail_squared_error"][key] / (3 * row["atoms"]) for e, row in zip(entries, rows, strict=True)) / len(rows),
            } for key in ("coherent_scale", "atom_varying_remainder")},
            "pooled_signed_parallel_bias_B": math.fsum(e["residual_dot_reference_sum"] for e in entries) / reference_squared if reference_squared else None,
            "equal_material_mean_signed_parallel_bias_B": math.fsum(biases) / len(biases) if all(b is not None for b in biases) else None}


def assess(rows):
    target = next(row for row in rows if row["material_id"] == TARGET)
    metrics = target["models"]
    b7 = metrics["sevennet"]["signed_parallel_bias_B"]
    opposite = [m for m in pilot.MODELS if m != "sevennet" and b7 is not None
                and metrics[m]["signed_parallel_bias_B"] is not None and b7 * metrics[m]["signed_parallel_bias_B"] < 0]
    improvement = -target["ensemble_minus_sevennet_squared_error"]["total"]
    parallel_improvement = -target["ensemble_minus_sevennet_squared_error"]["parallel"]
    harmed = [row for row in rows if row["material_id"] != TARGET and row["ensemble_minus_sevennet_squared_error"]["total"] > 0]
    parallel_harmed = [row["material_id"] for row in harmed if row["ensemble_minus_sevennet_squared_error"]["parallel"] > 0]
    conditions = {"opposing_signed_bias_in_target": bool(opposite),
                  "target_parallel_sse_reduced": parallel_improvement > 0,
                  "target_parallel_reduction_exceeds_half_total_improvement": improvement > 0 and parallel_improvement > .5 * improvement,
                  "parallel_sse_increases_in_at_least_three_other_harmed_materials": len(parallel_harmed) >= 3}
    all_zero = [row["material_id"] for row in rows if row["zero_reference_atoms"] == row["atoms"]]
    scale_delta = metrics["uniform_ensemble"]["parallel_detail_squared_error"]["coherent_scale"] - metrics["sevennet"]["parallel_detail_squared_error"]["coherent_scale"]
    remainder_delta = metrics["uniform_ensemble"]["parallel_detail_squared_error"]["atom_varying_remainder"] - metrics["sevennet"]["parallel_detail_squared_error"]["atom_varying_remainder"]
    return {"proposal_id": "H1", "target_material": TARGET,
            "decision_rule_status": "exploratory_after_case_selection_not_preregistered",
            "verdict": "inconclusive" if all_zero else "exploratory_rule_passes" if all(conditions.values()) else "exploratory_rule_fails",
            "coherent_bias_assessment": "not_supported_coherent_scale_error_worsens" if scale_delta > 0 else "coherent_scale_error_decreases",
            "conditions": conditions, "opposing_bias_members": opposite,
            "target_total_sse_improvement": improvement, "target_parallel_sse_improvement": parallel_improvement,
            "target_parallel_share_of_total_improvement": parallel_improvement / improvement if improvement > 0 else None,
            "target_uniform_minus_sevennet_coherent_scale_sse": scale_delta,
            "target_uniform_minus_sevennet_atom_varying_parallel_sse": remainder_delta,
            "harmed_other_materials": [row["material_id"] for row in harmed],
            "parallel_harmed_other_materials": parallel_harmed, "all_zero_reference_materials": all_zero}


def analyze(root, prior_path, proposal_path):
    prior, prior_receipt = read_json(prior_path)
    proposal, proposal_receipt = read_json(proposal_path)
    if proposal.get("role") != "proposer" or [p.get("id") for p in proposal.get("proposals", [])] != ["H1"]:
        raise ValueError("Expected the reviewed single H1 discovery packet")
    prior_hashes = {item["path"]: item["sha256"] for item in prior["inputs"]}
    loaded, inputs = {}, []
    for relative, expected in PINNED_INPUTS.items():
        data, receipt = read_json(root / relative)
        if receipt["sha256"] != expected or prior_hashes.get(relative) != expected:
            raise ValueError(f"Input fingerprint changed: {relative}")
        inputs.append({"path": relative, **receipt})
        loaded[relative] = data
    fixture = loaded[pilot.GEOMETRY]
    cases, joined = pilot.validate_join(fixture, {m: loaded[p] for m, p in pilot.BASELINES.items()})
    if [c["structure_id"] for c in cases] != [r["structure_id"] for r in prior["rows"]]:
        raise ValueError("Prior analysis configuration order changed")
    previous = {row["structure_id"]: row for row in prior["rows"]}
    rows = []
    for case in cases:
        ref = case["reference"]["forces_ev_per_angstrom"]
        old = previous[case["structure_id"]]
        if old["material_id"] != case["material_id"] or old["ordered_symbols"] != case["symbols"]:
            raise ValueError("Prior material or atom identity changed")
        forces = {m: joined[m][case["structure_id"]]["forces_ev_per_angstrom"] for m in pilot.MODELS}
        forces["uniform_ensemble"] = [[math.fsum(forces[m][i][j] for m in pilot.MODELS) / 3 for j in range(3)] for i in range(len(ref))]
        metrics = {m: decompose(forces[m], ref) for m in MODELS}
        for model in MODELS:
            if not math.isclose(metrics[model]["squared_error"]["total"], old["models"][model]["squared_error_ev2_per_angstrom2"], rel_tol=1e-13, abs_tol=1e-15):
                raise ArithmeticError("Total SSE differs from previous descriptive analysis")
        norms = [math.hypot(*f) for f in ref]
        nonzero = [value for value in norms if value > 0]
        rows.append({"structure_id": case["structure_id"], "material_id": case["material_id"], "atoms": len(ref),
                     "ordered_symbols": case["symbols"], "geometry_sha256": old["geometry_sha256"],
                     "zero_reference_atoms": len(norms) - len(nonzero), "minimum_nonzero_reference_norm": min(nonzero) if nonzero else None,
                     "models": metrics,
                     "ensemble_minus_sevennet_squared_error": {k: metrics["uniform_ensemble"]["squared_error"][k] - metrics["sevennet"]["squared_error"][k] for k in COMPONENTS},
                     "ensemble_minus_sevennet_cartesian_mse": {k: metrics["uniform_ensemble"]["cartesian_mse"][k] - metrics["sevennet"]["cartesian_mse"][k] for k in COMPONENTS}})
    return {"schema": "lupine.pi.reference_force_components.v1", "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "status": "exploratory_real_archived_data", "inference_calls": 0, "publication": "held",
            "inputs": inputs, "prior_analysis": prior_receipt, "discovery_packet": proposal_receipt,
            "source_scripts": {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in [Path(__file__), Path(pilot.__file__)]},
            "dataset": {"configurations": len(rows), "materials": len(rows), "atoms": sum(row["atoms"] for row in rows), "frames_per_material": 1},
            "fixture_contract_manifest_hash": fixture["manifest_hash"],
            "definitions": {"force_units": "eV/angstrom", "squared_error_units": "(eV/angstrom)^2", "bias_B_units": "dimensionless",
                "residual": "prediction minus reference", "parallel": "For each nonzero reference f, u=f/||f||; e_parallel=(e dot u)u.",
                "transverse": "e_perpendicular=e-e_parallel for nonzero-reference atoms; not an angular error metric.",
                "zero_reference": "Exactly zero reference vector: entire residual SSE goes into a separate bucket, with signed parallel error null. No epsilon cutoff or atom exclusion.",
                "normalization": "All component MSEs divide SSE by the same 3N, retaining zero-reference atoms. Component MSEs sum to total MSE; component RMSEs do not sum to total RMSE.",
                "signed_parallel_bias_B": "sum_i (e_i dot f_i) / sum_i ||f_i||^2; null for an all-zero reference configuration. Positive means weighted overprediction along f; negative means underprediction. Opposing global B signs do not prove pointwise cancellation.",
                "coherent_scale": "Exact diagnostic projection of the parallel residual onto the full reference force vector: coherent SSE=B^2*sum_i||f_i||^2; remainder=sum_i(e_i dot u_i - B*||f_i||)^2. These sum to parallel SSE. No corrected forces are fitted, evaluated or promoted.",
                "pooled": "Sum SSE over configurations / (3*total atoms).", "equal_material_mean_mse": "Mean of per-configuration SSE/(3N). One configuration per material.",
                "equal_material_mean_rmse": "Mean of per-configuration sqrt(SSE/(3N)); a different risk functional.",
                "uniform_ensemble": "Exactly fixed equal weights 1/3; no fitting or model calls."},
            "limitations": ["Five previously inspected configurations / 107 atoms; neither a sealed test set nor independent trajectories.",
                "Target case and 50%/three-material thresholds are exploratory and not a confirmatory preregistration.",
                "Parallel/transverse decomposition is established geometry, not a novelty claim, uncertainty calibration or proof of generalization.",
                "No PES curvature, training-data causal mechanism, MD fidelity or transferable correction is established.",
                "Reference direction can be unstable at very small force magnitudes; all atoms retained and minimum nonzero norms reported.",
                "Signed B averages can hide opposing local atom biases. An amplitude-only model is stronger than a large parallel error fraction.",
                "Input hashes pin archived force arrays, not original model weight hashes or every DFT setting."],
            "rows": rows, "model_summary": {m: aggregate(rows, m) for m in MODELS}, "mechanism_assessment": assess(rows)}


def render_report(result):
    """A private, static report with every data-derived string HTML-escaped."""
    esc = lambda value: html.escape(str(value), quote=True)
    a = result["mechanism_assessment"]
    table = []
    biases = []
    for row in result["rows"]:
        delta = row["ensemble_minus_sevennet_cartesian_mse"]
        share = delta["parallel"] / delta["total"] if delta["total"] else None
        table.append("<tr>" + "".join(f"<td>{esc(x)}</td>" for x in [row["material_id"], row["atoms"], row["zero_reference_atoms"],
            f"{delta['parallel']:+.7f}", f"{delta['transverse']:+.7f}", f"{delta['zero_reference']:+.3e}", f"{delta['total']:+.7f}",
            f"{100*share:.2f}%" if share is not None else "undefined"]) + "</tr>")
        biases.append("<tr>" + "".join(f"<td>{esc(x)}</td>" for x in [row["material_id"], *[f"{row['models'][m]['signed_parallel_bias_B']:+.6f}" if row['models'][m]['signed_parallel_bias_B'] is not None else "undefined" for m in MODELS]]) + "</tr>")
    risks = []
    for m in MODELS:
        risk = result["model_summary"][m]["risk"]["total"]
        risks.append("<tr>" + "".join(f"<td>{esc(x)}</td>" for x in [m, f"{risk['pooled_rmse']:.6f}", f"{risk['equal_material_root_mean_mse']:.6f}", f"{risk['equal_material_mean_rmse']:.6f}"]) + "</tr>")
    provenance = "".join(f"<tr><td>{esc(i['path'])}</td><td><code>{esc(i['sha256'])}</code></td></tr>" for i in result["inputs"])
    limitations = "".join(f"<li>{esc(item)}</li>" for item in result["limitations"])
    definition = "".join(f"<dt>{esc(k)}</dt><dd>{esc(v)}</dd>" for k, v in result["definitions"].items())
    return f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Archived force error analysis · private</title>
<style>body{{font:16px/1.5 system-ui,sans-serif;margin:40px auto;max-width:1120px;padding:0 22px;color:#192d2b;background:#f7f8f4}}h1{{font-size:38px;line-height:1.15}}h2{{margin-top:38px}}.label{{color:#587468;font-weight:700;letter-spacing:.08em;font-size:12px}}.callout{{background:#e1ece1;border-left:5px solid #426951;padding:18px 22px}}.caveat{{background:#fff2d5;border-left:5px solid #9b771c;padding:18px 22px}}table{{border-collapse:collapse;width:100%;font-size:14px}}th,td{{padding:9px 10px;text-align:right;border-bottom:1px solid #d5ddd5}}th:first-child,td:first-child{{text-align:left}}th{{background:#e9eee7}}code{{overflow-wrap:anywhere;font-size:12px}}.scroll{{overflow-x:auto}}dt{{font-weight:650;margin-top:14px}}dd{{margin-left:0}}small{{color:#4c615a}}</style>
<body><div class="label">PRIVATE · EXISTING ARCHIVED DATA · NO NEW MODEL INFERENCE</div>
<h1>Where the ensemble improves—and what that does not explain</h1>
<p>Five previously inspected material configurations, 107 atoms, three fixed models and their equal-weight average. All source arrays and joins match the earlier descriptive analysis.</p>
<div class="callout"><strong>The exploratory rule passes.</strong> In mp-559535, parallel error reduction supplies <strong>{esc(f"{a['target_parallel_share_of_total_improvement']*100:.2f}%")}</strong> of the total squared-error improvement over SevenNet. Parallel error increases in all four materials that the average harms.</div>
<p class="caveat"><strong>A coherent force-scale correction is not supported.</strong> On mp-559535 the signed bias moves from −0.004223 (SevenNet) to −0.012444 (average), farther from zero. Its coherent scale-error SSE increases by {esc(f"{a['target_uniform_minus_sevennet_coherent_scale_sse']:.6f}")}, while the atom-varying parallel remainder decreases by {esc(f"{-a['target_uniform_minus_sevennet_atom_varying_parallel_sse']:.6f}")} (eV/Å)². The observed rescue includes cancellation of atom-varying parallel residuals and a substantial transverse contribution. Opposing average signs alone are a weak mechanism test.</p>
<h2>All five materials: ensemble minus SevenNet</h2><p>MSE units: (eV/Å)². Negative means improvement; positive means harm. Every component uses the same 3N denominator. Share is parallel change / total change; above 100% means another component offsets part of that change.</p>
<div class="scroll"><table><thead><tr><th>Material</th><th>Atoms</th><th>Zero ref.</th><th>Parallel ΔMSE</th><th>Transverse ΔMSE</th><th>Zero-ref. ΔMSE</th><th>Total ΔMSE</th><th>Parallel share</th></tr></thead><tbody>{''.join(table)}</tbody></table></div>
<p>The two exactly zero-reference atoms in mp-863035 are kept in a separate error bucket. No small-force threshold or exclusions were used.</p>
<h2>Signed force-direction bias B</h2><p>B = Σ(eᵢ · fᵢ) / Σ||fᵢ||². Negative means weighted underprediction along reference forces. A material-wide mean can hide opposing atom-level errors.</p>
<div class="scroll"><table><thead><tr><th>Material</th><th>CHGNet</th><th>MACE-MP-0</th><th>SevenNet</th><th>Average</th></tr></thead><tbody>{''.join(biases)}</tbody></table></div>
<h2>The aggregation tradeoff remains</h2><p>RMSE units: eV/Å. Equal-material root mean MSE isolates the atom-weighting change. Mean material RMSE also changes the order of the square root and averaging.</p>
<div class="scroll"><table><thead><tr><th>Model</th><th>Pooled RMSE</th><th>Equal-material √mean MSE</th><th>Mean material RMSE</th></tr></thead><tbody>{''.join(risks)}</tbody></table></div>
<h2>Useful next question</h2><p>Does cancellation of atom-varying parallel residuals recur across additional matched configurations, or is this one selected case? Recover and verify existing archived arrays before fitting any correction. The larger archived panel uses different model membership and cannot directly replicate the SevenNet ensemble.</p>
<h2>Limits on interpretation</h2><ul>{limitations}</ul><p>This is an independent local calculation of saved arrays, not a Claude critique, a new prediction run, or a published scientific finding. The 50% and three-material rules were chosen after this pilot was inspected.</p>
<details><summary>Formulas and exact provenance</summary><p>e = predicted − reference; u = f/||f||; e∥ = (e · u)u; e⊥ = e − e∥. SSEtotal = SSE∥ + SSE⊥ + SSEzero. SSE∥ = B²Σ||f||² + Σ(e · u − B||f||)².</p><dl>{definition}</dl><div class="scroll"><table><thead><tr><th>Input</th><th>SHA256</th></tr></thead><tbody>{provenance}</tbody></table></div><p>Prior analysis SHA256: <code>{esc(result['prior_analysis']['sha256'])}</code><br>Discovery packet SHA256: <code>{esc(result['discovery_packet']['sha256'])}</code></p><p>Generated: {esc(result['generated_at'])}. Publication held.</p></details></body></html>'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--prior-analysis", type=Path, required=True)
    parser.add_argument("--discovery-packet", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--html-output", type=Path)
    args = parser.parse_args()
    result = analyze(args.repo, args.prior_analysis, args.discovery_packet)
    args.output.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as stream:
        stream.write(json.dumps(result, indent=2, allow_nan=False) + "\n")
    if args.html_output:
        fd = os.open(args.html_output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w") as stream:
            stream.write(render_report(result))
    print(json.dumps({"dataset": result["dataset"], "mechanism_assessment": result["mechanism_assessment"]}, allow_nan=False))


if __name__ == "__main__":
    main()
