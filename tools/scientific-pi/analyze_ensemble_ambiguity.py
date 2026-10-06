#!/usr/bin/env python3
"""Fixed-ensemble identities and retrospective best-member comparisons.

Only pinned local pilot arrays are read. No inference, fitting, randomization,
force threshold, model routing, download, or publication is performed.
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
from analyze_force_components import PINNED_INPUTS


def read_json(path):
    content = path.read_bytes()
    return json.loads(content), {"sha256": hashlib.sha256(content).hexdigest(), "bytes": len(content)}


def force_ambiguity(predictions, reference):
    """G_ab = e_a dot e_b / (3N), retaining every Cartesian component."""
    if not reference:
        raise ValueError("Reference must contain atoms")
    pilot.matrix(reference, len(reference), "reference")
    for model in pilot.MODELS:
        pilot.matrix(predictions[model], len(reference), model)
    dimension = 3 * len(reference)
    reference_flat = pilot.flat(reference)
    forces = [pilot.flat(predictions[m]) for m in pilot.MODELS]
    residuals = [[p - f for p, f in zip(values, reference_flat, strict=True)] for values in forces]
    gram_sse = [[pilot.dot(a, b) for b in residuals] for a in residuals]
    gram_mse = [[value / dimension for value in row] for row in gram_sse]
    mean_force = [math.fsum(values[i] for values in forces) / 3 for i in range(dimension)]
    ensemble_residual = [p - f for p, f in zip(mean_force, reference_flat, strict=True)]
    ensemble_mse = pilot.dot(ensemble_residual, ensemble_residual) / dimension
    gram_ensemble_mse = math.fsum(pilot.flat(gram_mse)) / 9
    member_mse = {m: gram_mse[i][i] for i, m in enumerate(pilot.MODELS)}
    mean_member_mse = math.fsum(member_mse.values()) / 3
    disagreements = [[p - mean_force[i] for i, p in enumerate(force)] for force in forces]
    disagreement_mse = math.fsum(pilot.dot(diff, diff) for diff in disagreements) / (3 * dimension)
    ambiguity_error = ensemble_mse - (mean_member_mse - disagreement_mse)
    gram_error = ensemble_mse - gram_ensemble_mse
    for candidate in (gram_ensemble_mse, mean_member_mse - disagreement_mse):
        if not math.isclose(ensemble_mse, candidate, rel_tol=2e-12, abs_tol=1e-15):
            raise ArithmeticError("Fixed-ensemble squared-error identity failed")
    best_model = min(member_mse, key=member_mse.get)
    best = member_mse[best_model]
    return {"model_order": list(pilot.MODELS), "residual_gram_sse": gram_sse, "residual_gram_mse": gram_mse,
            "member_mse": member_mse, "member_rmse": {m: math.sqrt(v) for m, v in member_mse.items()},
            "mean_member_mse": mean_member_mse, "disagreement_mse": disagreement_mse,
            "ensemble_mse": ensemble_mse, "ensemble_rmse": math.sqrt(ensemble_mse),
            "ensemble_mse_from_gram": gram_ensemble_mse,
            "ambiguity_identity_error": ambiguity_error, "gram_identity_error": gram_error,
            "ensemble_over_mean_member_mse": ensemble_mse / mean_member_mse if mean_member_mse else None,
            "disagreement_fraction_of_mean_member_mse": disagreement_mse / mean_member_mse if mean_member_mse else None,
            "off_diagonal_gram_mse_sum": math.fsum(gram_mse[i][j] for i in range(3) for j in range(3) if i != j),
            "retrospective_best_member": best_model, "best_member_mse": best, "best_member_rmse": math.sqrt(best),
            "ensemble_beats_best_member": ensemble_mse < best,
            "ensemble_minus_best_member_mse": ensemble_mse - best,
            "ensemble_rmse_increase_over_best_percent": (math.sqrt(ensemble_mse / best) - 1) * 100 if best else None}


def aggregate(rows, atom_weighted):
    weights = [row["atoms"] if atom_weighted else 1 for row in rows]
    weight_sum = sum(weights)
    mean = lambda values: math.fsum(w * value for w, value in zip(weights, values, strict=True)) / weight_sum
    gram = [[mean([row["metrics"]["residual_gram_mse"][i][j] for row in rows]) for j in range(3)] for i in range(3)]
    member = {m: gram[i][i] for i, m in enumerate(pilot.MODELS)}
    ensemble = mean([row["metrics"]["ensemble_mse"] for row in rows])
    average = mean([row["metrics"]["mean_member_mse"] for row in rows])
    disagreement = mean([row["metrics"]["disagreement_mse"] for row in rows])
    if not math.isclose(ensemble, average - disagreement, rel_tol=2e-12, abs_tol=1e-15):
        raise ArithmeticError("Aggregated ambiguity identity failed")
    best = min(member, key=member.get)
    return {"weighting": "atom_weighted_pooled" if atom_weighted else "equal_material_mean_mse",
            "residual_gram_mse": gram, "member_mse": member, "member_rmse": {m: math.sqrt(v) for m, v in member.items()},
            "mean_member_mse": average, "disagreement_mse": disagreement, "ensemble_mse": ensemble,
            "ensemble_rmse": math.sqrt(ensemble), "ambiguity_identity_error": ensemble - (average - disagreement),
            "best_single_member_over_panel": best, "ensemble_beats_best_single_member_over_panel": ensemble < member[best],
            "ensemble_rmse_change_vs_best_single_member_percent": (math.sqrt(ensemble / member[best]) - 1) * 100,
            "retrospective_per_material_best_mse": mean([row["metrics"]["best_member_mse"] for row in rows])}


def analyze(root, prior_components_path, critique_path=None):
    previous, prior_receipt = read_json(prior_components_path)
    previous_hashes = {item["path"]: item["sha256"] for item in previous["inputs"]}
    loaded, inputs = {}, []
    for relative, expected in PINNED_INPUTS.items():
        data, receipt = read_json(root / relative)
        if receipt["sha256"] != expected or previous_hashes.get(relative) != expected:
            raise ValueError(f"Input fingerprint changed: {relative}")
        inputs.append({"path": relative, **receipt})
        loaded[relative] = data
    fixture = loaded[pilot.GEOMETRY]
    cases, joined = pilot.validate_join(fixture, {m: loaded[p] for m, p in pilot.BASELINES.items()})
    if [c["structure_id"] for c in cases] != [r["structure_id"] for r in previous["rows"]]:
        raise ValueError("Prior configuration order changed")
    rows = []
    for case, old in zip(cases, previous["rows"], strict=True):
        if case["material_id"] != old["material_id"] or case["symbols"] != old["ordered_symbols"]:
            raise ValueError("Material or ordered atom identity changed")
        predictions = {m: joined[m][case["structure_id"]]["forces_ev_per_angstrom"] for m in pilot.MODELS}
        metrics = force_ambiguity(predictions, case["reference"]["forces_ev_per_angstrom"])
        for m in (*pilot.MODELS, "uniform_ensemble"):
            mse = metrics["ensemble_mse"] if m == "uniform_ensemble" else metrics["member_mse"][m]
            if not math.isclose(mse, old["models"][m]["cartesian_mse"]["total"], rel_tol=1e-13, abs_tol=1e-15):
                raise ArithmeticError("Error differs from immutable prior analysis")
        rows.append({"material_id": case["material_id"], "structure_id": case["structure_id"],
                     "atoms": len(case["symbols"]), "ordered_symbols": case["symbols"], "metrics": metrics})
    target = next(row for row in rows if row["material_id"] == "mp-559535")
    target_metrics = target["metrics"]
    critique_receipt = None
    if critique_path:
        _, critique_receipt = read_json(critique_path)
        critique_receipt["acceptance"] = "rejected_structured_packet_not_an_accepted_PI_stage"
    scripts = [Path(__file__), Path(pilot.__file__), Path(__file__).with_name("analyze_force_components.py")]
    return {"schema": "lupine.pi.ensemble_ambiguity.v1", "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "status": "exploratory_real_archived_data", "inference_calls": 0, "publication": "held",
            "inputs": inputs, "prior_components_analysis": prior_receipt, "rejected_critique_context": critique_receipt,
            "source_scripts": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in scripts},
            "primary_sources": [{"id": "C1", "title": "Neural Network Ensembles, Cross Validation, and Active Learning",
                "authors": "Anders Krogh and Jesper Vedelsby", "venue": "NIPS 1994, volume 7 (printed 1995)",
                "url": "https://proceedings.neurips.cc/paper_files/paper/1994/file/b8c37e33defde51cf91e1e03e51657da-Paper.pdf",
                "locator": "PDF page 2, printed page 232, equation 6; extension to multiple outputs noted",
                "verification": "Parent agent directly retrieved and checked the primary paper in this session, separately from the rejected critique packet.",
                "supports": "Classical ensemble squared-error/ambiguity identity only; does not establish this pilot's physical mechanism, novelty or generalization."}],
            "fixture_contract_manifest_hash": fixture["manifest_hash"],
            "dataset": {"materials": len(rows), "configurations": len(rows), "atoms": sum(row["atoms"] for row in rows), "frames_per_material": 1},
            "definitions": {"force_units": "eV/angstrom", "mse_and_gram_mse_units": "(eV/angstrom)^2",
                "residual_gram_sse": "Raw uncentered 3x3 Gram G_ab=e_a dot e_b on the complete 3N Cartesian force residuals, in model_order. No mean centering, covariance estimation or translation projection.",
                "residual_gram_mse": "G_ab/(3N); diagonal entries are member MSEs.",
                "gram_identity": "ensemble MSE = sum_ab G_ab/(9*3N), for fixed weights1/3.",
                "ambiguity_identity": "ensemble MSE = mean member MSE - disagreement MSE; disagreement = (1/3)sum_m ||F_m - F_average||^2/(3N).",
                "best_member": "Retrospective minimum error against the reference labels, separately for each inspected material. Not a deployable selection policy, held-out model choice or fitted weight.",
                "risk_aggregation": "Report atom-weighted pooled MSE and equal-material mean MSE. The square root after aggregation differs from averaging per-material RMSEs.",
                "raw_alignment": "Off-diagonal dot products measure residual alignment. A negative sum is a descriptive property, not independence, covariance estimation or a null-test result."},
            "rows": rows, "pooled": aggregate(rows, True), "equal_material": aggregate(rows, False),
            "mean_material_rmse": {m: math.fsum(row["metrics"]["ensemble_rmse"] if m == "uniform_ensemble" else row["metrics"]["member_rmse"][m] for row in rows) / len(rows) for m in (*pilot.MODELS, "uniform_ensemble")},
            "findings": {"materials_ensemble_beats_retrospective_best": sum(row["metrics"]["ensemble_beats_best_member"] for row in rows),
                "rescue_material": target["material_id"], "rescue_material_best_member": target_metrics["retrospective_best_member"],
                "ensemble_beats_chgnet_in_rescue_material": target_metrics["ensemble_mse"] < target_metrics["member_mse"]["chgnet"],
                "rescue_ensemble_rmse_increase_over_chgnet_percent": (target_metrics["ensemble_rmse"] / target_metrics["member_rmse"]["chgnet"] - 1) * 100,
                "negative_off_diagonal_sum_materials": [row["material_id"] for row in rows if row["metrics"]["off_diagonal_gram_mse_sum"] < 0]},
            "limitations": ["Five previously inspected configurations, one per material; descriptive arithmetic, not confirmatory science or generalization.",
                "Beating SevenNet on the selected difficult case is not equivalent to beating the best member there.",
                "Disagreement is an exact algebraic reduction relative to average member error; it is not an established physical cause, calibrated uncertainty, novelty or evidence of independence.",
                "The best member varies across these cases and is identified using known reference labels. No deployable routing rule or weights are inferred.",
                "No random-direction null, force cutoff, exclusions, new predictions or corrected forces were used.",
                "The rejected Claude packet is context only. These arithmetic checks do not retroactively accept its scientific stage or verify its literature claims.",
                "Exact original DFT settings and original model weight hashes remain incomplete. Larger archived panels have different model membership."]}


def render_report(result):
    esc = lambda value: html.escape(str(value), quote=True)
    rows = []
    grams = []
    for row in result["rows"]:
        m = row["metrics"]
        values = [row["material_id"], m["retrospective_best_member"], f"{m['best_member_rmse']:.6f}", f"{m['ensemble_rmse']:.6f}",
                  f"{m['ensemble_rmse_increase_over_best_percent']:+.2f}%", f"{m['mean_member_mse']:.7f}", f"{m['disagreement_mse']:.7f}", f"{m['ensemble_mse']:.7f}"]
        rows.append("<tr>" + "".join(f"<td>{esc(v)}</td>" for v in values) + "</tr>")
        gram_rows = "".join("<tr><th>" + esc(pilot.MODELS[i]) + "</th>" + "".join(f"<td>{v:.9f}</td>" for v in values) + "</tr>" for i, values in enumerate(m["residual_gram_mse"]))
        grams.append(f"<h3>{esc(row['material_id'])}</h3><table><thead><tr><th>G/(3N)</th>" + "".join(f"<th>{esc(model)}</th>" for model in pilot.MODELS) + f"</tr></thead><tbody>{gram_rows}</tbody></table>")
    risk_rows = []
    for key, name in (("pooled", "Pooled"), ("equal_material", "Equal-material √mean MSE")):
        risk = result[key]
        risk_rows.append("<tr>" + "".join(f"<td>{esc(value)}</td>" for value in [name, risk["best_single_member_over_panel"],
            f"{risk['member_rmse'][risk['best_single_member_over_panel']]:.6f}", f"{risk['ensemble_rmse']:.6f}", f"{risk['ensemble_rmse_change_vs_best_single_member_percent']:+.2f}%"]) + "</tr>")
    macro = result["mean_material_rmse"]
    best = min(pilot.MODELS, key=lambda m: macro[m])
    risk_rows.append("<tr>" + "".join(f"<td>{esc(value)}</td>" for value in ["Mean material RMSE", best, f"{macro[best]:.6f}", f"{macro['uniform_ensemble']:.6f}", f"{(macro['uniform_ensemble']/macro[best]-1)*100:+.2f}%"]) + "</tr>")
    findings = result["findings"]
    inputs = "".join(f"<li><code>{esc(x['path'])}</code><br>SHA256 <code>{esc(x['sha256'])}</code></li>" for x in result["inputs"])
    scripts = "".join(f"<li><code>{esc(name)}</code>: <code>{esc(sha)}</code></li>" for name, sha in result["source_scripts"].items())
    limits = "".join(f"<li>{esc(value)}</li>" for value in result["limitations"])
    return f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Ensemble ambiguity · private arithmetic report</title>
<style>body{{font:16px/1.55 system-ui,sans-serif;color:#21352e;background:#f7f8f3;max-width:1140px;margin:42px auto;padding:0 24px}}h1{{font-size:38px;line-height:1.15}}h2{{margin-top:36px}}.label{{font-size:12px;font-weight:700;letter-spacing:.08em;color:#567863}}.callout{{padding:20px 24px;border-left:5px solid #ad791c;background:#fff0cc}}table{{width:100%;border-collapse:collapse;font-size:14px}}th,td{{padding:10px;text-align:right;border-bottom:1px solid #d5ded5}}th{{background:#e5ece2}}th:first-child,td:first-child{{text-align:left}}.scroll{{overflow-x:auto}}code{{font-size:12px;overflow-wrap:anywhere}}small{{color:#51645a}}</style><body>
<div class="label">PRIVATE · ALL 107 ARCHIVED ATOMS · NO NEW MODEL INFERENCE</div>
<h1>The ensemble does not beat the best member on any of these five materials</h1>
<div class="callout">On the rescued case <strong>mp-559535</strong>, CHGNet alone has lower error. The ensemble RMSE is <strong>{findings['rescue_ensemble_rmse_increase_over_chgnet_percent']:.2f}% higher</strong> than CHGNet. The earlier rescue was relative to SevenNet. Averaging still improves aggregate squared error across this mixed panel; the comparison depends on the risk measure.</div>
<p>This extends the <a href="force-components-report.html">earlier parallel/transverse report</a> without modifying its data or provenance. The best-per-material comparison uses reference labels retrospectively; it is not a model-selection strategy available before seeing those labels.</p>
<h2>Exact error–disagreement identity</h2><p>For eₘ = Fₘ − f and the fixed average F̄ = (F₁ + F₂ + F₃)/3:</p><p><strong>Ensemble MSE = mean member MSE − disagreement MSE.</strong><br>Disagreement MSE = (1/3) Σₘ ||Fₘ − F̄||² / (3N). Equivalently, with Gₐᵦ = eₐ · eᵦ, ensemble MSE = Σₐᵦ Gₐᵦ / (9 × 3N).</p><p>This classical identity is given by <a href="https://proceedings.neurips.cc/paper_files/paper/1994/file/b8c37e33defde51cf91e1e03e51657da-Paper.pdf" rel="noopener noreferrer">Krogh and Vedelsby, NIPS 1994, equation 6, printed page 232</a> (volume printed 1995). The primary paper was checked separately from the rejected critique. Our raw-array check verifies the arithmetic here; the identity does not supply a physical cause, confidence interval or novelty claim.</p>
<h2>Every material, with the strongest individual baseline</h2><p>RMSE units: eV/Å. MSE units: (eV/Å)². Positive ΔRMSE means the ensemble is worse than that material’s best member. “Mean member” averages all three member MSEs.</p><div class="scroll"><table><thead><tr><th>Material</th><th>Best member</th><th>Best RMSE</th><th>Ensemble RMSE</th><th>ΔRMSE</th><th>Mean member MSE</th><th>Disagreement</th><th>Ensemble MSE</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div>
<h2>Why the aggregate can still favor averaging</h2><p>The best member differs by material. A single fixed model across the panel is a weaker retrospective benchmark than choosing each material’s best member with its reference label in hand.</p><div class="scroll"><table><thead><tr><th>Risk measure</th><th>Best single model</th><th>Its value</th><th>Ensemble value</th><th>Relative change</th></tr></thead><tbody>{''.join(risk_rows)}</tbody></table></div>
<h2>What follows</h2><p>The selected case does not establish an ensemble advantage over CHGNet or a global force-scale correction. The new arithmetic is consistent with heterogeneous model quality and residual cancellation; it does not identify their scientific cause. The next useful data step remains exact-hash recovery of existing matched archive outputs. Its different model panel must be described separately.</p>
<h2>Interpretation limits</h2><ul>{limits}</ul>
<details><summary>All five 3×3 residual Gram matrices</summary><p>Raw, uncentered residual inner products normalized by 3N. Rows and columns: CHGNet, MACE-MP-0, SevenNet. Off-diagonal entries can be negative; these are not fitted covariance matrices.</p>{''.join(grams)}</details>
<details><summary>Exact provenance</summary><p>Generated {esc(result['generated_at'])}. Private publication held. The full data are in <a href="ensemble-ambiguity-analysis.json">the JSON artifact</a>.</p><ul>{inputs}</ul><p>Prior immutable force-components analysis SHA256: <code>{esc(result['prior_components_analysis']['sha256'])}</code></p><h3>Calculation source hashes</h3><ul>{scripts}</ul></details></body></html>'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--prior-components", type=Path, required=True)
    parser.add_argument("--rejected-critique", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--html-output", type=Path, required=True)
    args = parser.parse_args()
    result = analyze(args.repo, args.prior_components, args.rejected_critique)
    for path, content in ((args.output, json.dumps(result, indent=2, allow_nan=False) + "\n"), (args.html_output, render_report(result))):
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w") as stream:
            stream.write(content)
    print(json.dumps(result["findings"], allow_nan=False))


if __name__ == "__main__":
    main()
