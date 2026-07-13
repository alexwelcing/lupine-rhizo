"""Round-2 correction arms for the unbiased accuracy campaign.

Round 1 falsified the cross-class de-bias on the HEA group (fcc-elemental
bias has the wrong SIGN for alloys), which is now a kernel-checked law
(Shapes.Certificates wrong_direction_inflation_worsens / directionVerified).
Round 2 applies the theorem: corrections are licensed only by in-class
direction evidence, else they ABSTAIN.

Arms computed from the Round-1 raw measurements (the instrument is
deterministic and seed-pinned; the independent round2-verify rerun checks
raw-value reproducibility separately):
  raw            - unchanged model predictions,
  cross_class    - Round-1 arm (kept for comparison),
  in_class_loo   - per-candidate leave-one-out median bias over the OTHER
                   group members with a non-null reference (never the
                   candidate itself),
  sign_gated_loo - in_class_loo applied ONLY when every LOO calibration
                   member's (pred/ref) sits on the same side of 1 for that
                   (model, property); otherwise abstain (corrected = raw).

Output: data/candidates/round2/report.json + REPORT.md.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path

_HERE = Path(__file__).resolve()
_REPO_ROOT = _HERE.parents[2]

PROPS = ("a0", "b0", "c11", "c12", "c44")
ARMS = ("raw", "cross_class", "in_class_loo", "sign_gated_loo")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--round1-report",
        default=str(_REPO_ROOT / "data" / "candidates" / "round1" / "report.json"),
    )
    parser.add_argument(
        "--out-dir",
        default=str(_REPO_ROOT / "data" / "candidates" / "round2"),
    )
    parser.add_argument("--min-calibration-members", type=int, default=2)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    r1 = json.loads(Path(args.round1_report).read_text(encoding="utf-8"))
    cands = r1["candidates"]

    # group -> candidate id list
    groups: dict[str, list[str]] = {}
    for cid, c in cands.items():
        groups.setdefault(c["group"], []).append(cid)

    # per (candidate, model, prop): raw pred, reference, round-1 corrected
    def raw(cid: str, model: str, prop: str) -> float | None:
        rec = cands[cid]["per_model"].get(model, {})
        if "error" in rec:
            return None
        return rec["properties"].get(prop)

    def ref(cid: str, prop: str) -> float | None:
        return cands[cid].get("references", {}).get(prop)

    models = r1["models"]
    rows: list[dict[str, object]] = []
    abstentions = 0
    applications = 0
    for group, members in groups.items():
        for cid in members:
            for model in models:
                for prop in PROPS:
                    pred = raw(cid, model, prop)
                    reference = ref(cid, prop)
                    if pred is None or reference is None:
                        continue
                    # Round-1 cross-class corrected value (candidate-level
                    # corrected_arm block; falls back to raw when the arm
                    # did not correct that property).
                    r1_corr = (
                        cands[cid]
                        .get("corrected_arm", {})
                        .get(model, {})
                        .get("values", {})
                        .get(prop, {})
                        .get("value", pred)
                    )
                    # LOO calibration ratios from the other group members.
                    ratios = []
                    for other in members:
                        if other == cid:
                            continue
                        p_o, r_o = raw(other, model, prop), ref(other, prop)
                        if p_o is not None and r_o is not None and r_o != 0:
                            ratios.append(p_o / r_o)
                    if len(ratios) >= args.min_calibration_members:
                        bias = statistics.median(ratios)
                        loo = pred / bias
                        same_side = all(x > 1 for x in ratios) or all(
                            x < 1 for x in ratios
                        )
                        gated = loo if same_side else pred
                        if same_side:
                            applications += 1
                        else:
                            abstentions += 1
                    else:
                        loo = pred
                        gated = pred
                        abstentions += 1
                    rows.append(
                        {
                            "group": group,
                            "candidate": cid,
                            "model": model,
                            "prop": prop,
                            "reference": reference,
                            "raw": pred,
                            "cross_class": r1_corr,
                            "in_class_loo": loo,
                            "sign_gated_loo": gated,
                        }
                    )

    def metrics() -> dict[str, dict[str, dict[str, object]]]:
        out: dict[str, dict[str, dict[str, object]]] = {}
        for group in sorted(groups):
            out[group] = {}
            for prop in PROPS:
                sel = [
                    row for row in rows if row["group"] == group and row["prop"] == prop
                ]
                if not sel:
                    continue
                entry: dict[str, object] = {"n": len(sel)}
                for arm in ARMS:
                    errs = [
                        abs(row[arm] - row["reference"]) / abs(row["reference"])
                        for row in sel
                    ]
                    entry[f"median_abs_rel_err_{arm}"] = statistics.median(errs)
                out[group][prop] = entry
        return out

    arm_metrics = metrics()
    report = {
        "schema": "lupine.campaign_round2.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "round1_report": args.round1_report,
        "theorem_basis": (
            "Shapes.Certificates: wrong_direction_inflation_worsens / "
            "wrong_direction_deflation_worsens / directionVerified — a "
            "correction without in-class same-side direction evidence "
            "abstains (corrected = raw), which is risk-free."
        ),
        "sign_gate": {
            "rule": (
                "apply LOO bias iff every LOO calibration member's pred/ref "
                "is on the same side of 1 for that (model, property)"
            ),
            "applications": applications,
            "abstentions": abstentions,
        },
        "arm_metrics": arm_metrics,
        "rows": rows,
    }
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    lines = [
        "# Round 2 — theorem-gated corrections (unbiased accuracy campaign)",
        "",
        f"Generated {report['generated_at']} from {args.round1_report}.",
        "",
        f"Sign gate: {applications} corrections applied, {abstentions} abstained.",
        "",
        "| group | prop | n | raw | cross-class (R1) | in-class LOO | sign-gated LOO |",
        "|---|---|---|---|---|---|---|",
    ]
    for group, per_prop in arm_metrics.items():
        for prop, entry in per_prop.items():
            lines.append(
                f"| {group} | {prop} | {entry['n']} | "
                + " | ".join(
                    f"{entry[f'median_abs_rel_err_{arm}'] * 100:.2f}%" for arm in ARMS
                )
                + " |"
            )
    (out_dir / "REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    for group, per_prop in arm_metrics.items():
        for prop, entry in per_prop.items():
            print(
                group,
                prop,
                {arm: round(entry[f"median_abs_rel_err_{arm}"], 4) for arm in ARMS},
            )
    print(f"gate: {applications} applied, {abstentions} abstained -> {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
