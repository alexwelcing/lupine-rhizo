"""Table 1 (SI) — the full static results table, machine-generated.

Long format, one row per (model, material, property): predicted value,
bound reference, signed relative error. Emitted as CSV (machine) and
Markdown (human), both derived from the same records.
"""

from __future__ import annotations

import csv
import io

import common as C

CSV_NAME = "table1_static_results.csv"
MD_NAME = "table1_static_results.md"

TABLE_PROPERTIES = C.PROPERTY_ORDER + ("cohesive_energy",)


def _rows(dataset: C.Dataset) -> list[dict]:
    rows: list[dict] = []
    for model in C.MODELS:
        for material in C.MATERIAL_ORDER:
            cell = dataset.cell(material, model)
            for prop in TABLE_PROPERTIES:
                rec = cell.prop(prop)
                if rec is None:
                    continue
                rel = rec.rel_err
                rows.append(
                    {
                        "model": model,
                        "material": material,
                        "structure": cell.structure,
                        "property": prop,
                        "unit": rec.unit,
                        "predicted": rec.predicted,
                        "reference": rec.reference,
                        "rel_err": rel,
                        "rel_err_pct": None if rel is None else 100.0 * rel,
                    }
                )
    return rows


def _fmt(value, spec: str = ".6g") -> str:
    if value is None:
        return ""
    return format(value, spec)


def _write_csv(rows: list[dict]) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    header = [
        "model", "material", "structure", "property", "unit",
        "predicted", "reference", "rel_err", "rel_err_pct",
    ]
    writer.writerow(header)
    for row in rows:
        writer.writerow(
            [
                row["model"], row["material"], row["structure"],
                row["property"], row["unit"],
                _fmt(row["predicted"], ".10g"),
                _fmt(row["reference"], ".10g"),
                _fmt(row["rel_err"], ".6g"),
                _fmt(row["rel_err_pct"], ".4f"),
            ]
        )
    return buf.getvalue()


def _write_md(rows: list[dict]) -> str:
    lines = [
        "# Table 1 — static results per (model, material, property)",
        "",
        "Machine-generated from `data/y_matrix_runs/bound/*.evidence.json`",
        "(signed relative error = (pred - ref)/|ref|; blank reference =",
        "no bound literature value).",
        "",
    ]
    for model in C.MODELS:
        lines.append(f"## {C.MODEL_LABELS[model]} (`{model}`)")
        lines.append("")
        lines.append(
            "| Material | Property | Unit | Predicted | Reference "
            "| Rel. err (%) |"
        )
        lines.append("|---|---|---|---:|---:|---:|")
        for row in rows:
            if row["model"] != model:
                continue
            lines.append(
                f"| {row['material']} | {row['property']} | {row['unit']} "
                f"| {_fmt(row['predicted'], '.6g')} "
                f"| {_fmt(row['reference'], '.6g')} "
                f"| {_fmt(row['rel_err_pct'], '+.2f')} |"
            )
        lines.append("")
    return "\n".join(lines)


def build() -> dict:
    dataset = C.load_dataset()
    rows = _rows(dataset)
    csv_text = _write_csv(rows)
    md_text = _write_md(rows)
    csv_path = C.OUT_DIR / CSV_NAME
    md_path = C.OUT_DIR / MD_NAME
    csv_path.write_text(csv_text, encoding="utf-8", newline="\n")
    md_path.write_text(md_text, encoding="utf-8", newline="\n")
    outputs = {
        "csv": {
            "path": csv_path.relative_to(C.REPO_ROOT).as_posix(),
            "sha256": C.sha256_of(csv_path),
        },
        "md": {
            "path": md_path.relative_to(C.REPO_ROOT).as_posix(),
            "sha256": C.sha256_of(md_path),
        },
    }
    n_with_ref = sum(1 for r in rows if r["reference"] is not None)
    return {
        "figure": "table1_static_results",
        "outputs": outputs,
        "inputs": dict(dataset.input_hashes),
        "computation": {
            "table": (
                "long-format dump of every bound property per (model, "
                "material): predicted, reference, signed rel err; "
                "cohesive_energy included for completeness (no bound "
                "reference exists)"
            ),
        },
        "stats": {
            "n_rows": len(rows),
            "n_rows_with_reference": n_with_ref,
        },
    }


if __name__ == "__main__":
    build()
