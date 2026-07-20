#!/usr/bin/env python3
"""Fit, select, and score the Z3 delta correction against the locked split.

Honesty contract (enforced here, not by convention):
  * fit uses ONLY delta_train references;
  * correction-form selection uses ONLY delta_validation;
  * the confirmatory statistic is computed ONLY on confirmatory_test,
    which is never read for fitting, selection, or tuning
    (data/candidates/z3_catbench_bm_delta_splits.lock.json `fit_exclusion`).

Correction forms (fixed menu, simplest first):
  A  global constant:       delta = mean(train errors)
  B  family constant:       delta = mean(train errors in candidate's family)
  C  family size-linear:    delta = a + b * n_adsorbate_atoms per family
                             (falls back to B when the family's train rows
                             have <2 distinct adsorbate sizes)
  D  global size-linear:    delta = a + b * n_adsorbate_atoms

The corrected prediction is baseline + (-delta); the score is MAE of the
corrected signed error against the locked DFT references on the 20
confirmatory-test candidates. Selection ties break toward the simpler form.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

SCHEMA = "lupine.z3.delta_correction_report.v1"
MODELS = ("chgnet", "mace-mp-small", "mace-mp-medium", "mace-mpa-0-medium")
FORMS = ("A_global_constant", "B_family_constant", "C_family_linear", "D_global_linear")


@dataclass(frozen=True)
class FitData:
    errors: dict[str, float]  # candidate_id -> baseline signed error (eV)
    natoms: dict[str, int]
    families: dict[str, str]


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_sidecar(path: Path) -> None:
    sidecar = path.with_name(path.name + ".sha256")
    expected = sidecar.read_text(encoding="utf-8").split()[0].strip()
    actual = sha256_file(path)
    if expected != actual:
        raise ValueError(f"sidecar hash mismatch for {path}: {expected} != {actual}")


def baseline_errors_from_gcs(run_id: str, model: str, candidate_ids: list[str],
                             work: Path, project: str, region: str) -> dict[str, float]:
    """Download raw artifacts for one model and extract signed errors, validating
    model/row/candidate on every artifact (no trust in paths alone)."""
    errors: dict[str, float] = {}
    for cid in candidate_ids:
        url = (f"gs://shed-489901-atlas-outputs/z3-campaign/raw/{run_id}/{model}/{cid}/"
               f"adsorption_energy/cell_result.json")
        dest = work / f"{cid}.{model}.cell_result.json"
        subprocess.run(["gcloud", "storage", "cp", url, str(dest), "--project", project],
                       check=True, capture_output=True)
        artifact = load_json(dest)
        if artifact.get("mlip_id") != model or artifact.get("row_id") != "adsorption_energy":
            raise ValueError(f"artifact identity mismatch for {model}/{cid}")
        preds = [p for p in artifact.get("predictions", []) if p.get("candidate_id") == cid]
        if len(preds) != 1:
            raise ValueError(f"expected exactly one prediction for {model}/{cid}")
        pred = preds[0]
        if pred.get("status") != "completed":
            raise ValueError(f"prediction not completed for {model}/{cid}: {pred.get('error_class')}")
        err = pred.get("signed_error_ev")
        if not isinstance(err, (int, float)):
            raise ValueError(f"missing signed error for {model}/{cid}")
        errors[cid] = float(err)
    return errors


def fit_form(form: str, train_ids: list[str], data: FitData):
    """Return delta(candidate_id) -> eV fitted on train only."""
    fams = {data.families[c] for c in train_ids}
    if form == "A_global_constant":
        shift = statistics.mean(data.errors[c] for c in train_ids)
        return lambda cid: shift
    if form == "B_family_constant":
        means = {f: statistics.mean(data.errors[c] for c in train_ids if data.families[c] == f)
                 for f in fams}
        global_mean = statistics.mean(data.errors[c] for c in train_ids)
        return lambda cid: means.get(data.families[cid], global_mean)
    if form == "C_family_linear":
        fits: dict[str, tuple[float, float] | None] = {}
        for f in fams:
            pts = [(data.natoms[c], data.errors[c]) for c in train_ids if data.families[c] == f]
            sizes = {n for n, _ in pts}
            if len(sizes) < 2:
                fits[f] = None
                continue
            n = len(pts)
            sx = sum(p[0] for p in pts); sy = sum(p[1] for p in pts)
            sxx = sum(p[0] ** 2 for p in pts); sxy = sum(p[0] * p[1] for p in pts)
            denom = n * sxx - sx * sx
            b = (n * sxy - sx * sy) / denom
            a = (sy - b * sx) / n
            fits[f] = (a, b)
        b_means = {f: statistics.mean(data.errors[c] for c in train_ids if data.families[c] == f)
                   for f in fams}
        global_mean = statistics.mean(data.errors[c] for c in train_ids)

        def delta(cid: str) -> float:
            f = data.families[cid]
            fit = fits.get(f)
            if fit is None:
                return b_means.get(f, global_mean)
            a, b = fit
            return a + b * data.natoms[cid]
        return delta
    if form == "D_global_linear":
        pts = [(data.natoms[c], data.errors[c]) for c in train_ids]
        if len({n for n, _ in pts}) < 2:
            shift = statistics.mean(p[1] for p in pts)
            return lambda cid: shift
        n = len(pts)
        sx = sum(p[0] for p in pts); sy = sum(p[1] for p in pts)
        sxx = sum(p[0] ** 2 for p in pts); sxy = sum(p[0] * p[1] for p in pts)
        denom = n * sxx - sx * sx
        b = (n * sxy - sx * sy) / denom
        a = (sy - b * sx) / n
        return lambda cid: a + b * data.natoms[cid]
    raise ValueError(f"unknown correction form {form}")


def mae(form, ids: list[str], data: FitData) -> float:
    return statistics.mean(abs(data.errors[c] - form(c)) for c in ids)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    ap.add_argument("--run-id", default="z3-20260719")
    ap.add_argument("--raw-dir", type=Path, help="local raw artifacts (skip GCS download)")
    ap.add_argument("--project", default="shed-489901")
    ap.add_argument("--region", default="us-central1")
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()

    root = args.root
    panel_path = root / "data/candidates/z3_catbench_bm_adsorption.lock.json"
    splits_path = root / "data/candidates/z3_catbench_bm_delta_splits.lock.json"
    verify_sidecar(panel_path)
    verify_sidecar(splits_path)
    panel = load_json(panel_path)
    splits = load_json(splits_path)["splits"]

    natoms, families = {}, {}
    for c in panel["candidates"]:
        gas = [s for s in c["systems"] if "gas" in s["system_id"]]
        if len(gas) != 1:
            raise ValueError(f"candidate {c['candidate_id']} needs exactly one gas system")
        natoms[c["candidate_id"]] = len(gas[0]["symbols"])
        families[c["candidate_id"]] = c["application_family"]

    train, val, test = splits["delta_train"], splits["delta_validation"], splits["confirmatory_test"]
    all_ids = train + val + test
    work = args.raw_dir or (root / "build" / "z3-campaign" / "raw")
    work.mkdir(parents=True, exist_ok=True)

    report = {
        "schema": SCHEMA,
        "run_id": args.run_id,
        "panel_sha256": sha256_file(panel_path),
        "splits_sha256": sha256_file(splits_path),
        "fit_exclusion": "delta_train fit; delta_validation selection; confirmatory_test scoring only",
        "models": {},
    }
    for model in MODELS:
        if args.raw_dir:
            errors = {}
            for cid in all_ids:
                artifact = load_json(work / f"{cid}.{model}.cell_result.json")
                preds = [p for p in artifact.get("predictions", []) if p.get("candidate_id") == cid]
                if len(preds) != 1 or preds[0].get("status") != "completed":
                    raise ValueError(f"bad artifact for {model}/{cid}")
                errors[cid] = float(preds[0]["signed_error_ev"])
        else:
            errors = baseline_errors_from_gcs(args.run_id, model, all_ids, work,
                                              args.project, args.region)
        data = FitData(errors=errors, natoms=natoms, families=families)
        form_scores = {form: mae(fit_form(form, train, data), val, data) for form in FORMS}
        selected = min(FORMS, key=lambda f: (form_scores[f], FORMS.index(f)))
        delta = fit_form(selected, train, data)
        test_rows = []
        for cid in test:
            corrected_err = errors[cid] - delta(cid)
            test_rows.append({
                "candidate_id": cid,
                "family": families[cid],
                "n_adsorbate_atoms": natoms[cid],
                "baseline_signed_error_ev": errors[cid],
                "delta_correction_ev": delta(cid),
                "corrected_signed_error_ev": corrected_err,
                "corrected_absolute_error_ev": abs(corrected_err),
            })
        report["models"][model] = {
            "validation_mae_by_form": form_scores,
            "selected_form": selected,
            "train_mae_after_correction": mae(delta, train, data),
            "validation_mae_after_correction": form_scores[selected],
            "baseline_test_mae": statistics.mean(abs(errors[c]) for c in test),
            "corrected_test_mae": statistics.mean(r["corrected_absolute_error_ev"] for r in test_rows),
            "gate_threshold_ev": 0.1,
            "gate_outcome": None,  # filled below
            "test_rows": test_rows,
        }
        outcome = "pass" if report["models"][model]["corrected_test_mae"] <= 0.1 else "fail"
        report["models"][model]["gate_outcome"] = outcome

    out = args.out or (root / "data/candidates/z3/delta-correction-report.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    sidecar = out.with_name(out.name + ".sha256")
    sidecar.write_text(f"{sha256_file(out)}  {out.name}\n", encoding="utf-8")
    print(json.dumps({m: {"form": r["selected_form"],
                          "baseline_test_mae": round(r["baseline_test_mae"], 4),
                          "corrected_test_mae": round(r["corrected_test_mae"], 4),
                          "gate": r["gate_outcome"]}
                      for m, r in report["models"].items()}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
