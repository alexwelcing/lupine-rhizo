"""Shared loading, styling, and statistics for the envfield paper figures.

Every figure script in this directory consumes the repo's bound evidence
(``data/y_matrix_runs/bound/*.evidence.json``), the statics runs
(``data/y_matrix_runs/<Mat>_<struct>_<model>.json``), and the confirmatory
analysis artifacts (``data/y_matrix_runs/analysis/*.json``). Nothing is
hand-typed: all plotted numbers are recomputed here, and every consumed
file's SHA-256 goes into ``figures_manifest.json``.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Mapping

import matplotlib

matplotlib.use("Agg")  # deterministic, headless

import numpy as np  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[3]
RUNS_DIR = REPO_ROOT / "data" / "y_matrix_runs"
BOUND_DIR = RUNS_DIR / "bound"
ANALYSIS_DIR = RUNS_DIR / "analysis"
ENVFIELD_EXPERIMENT_DIR = RUNS_DIR / "envfield_experiment"
OUT_DIR = Path(__file__).resolve().parent

EVIDENCE_SCHEMA = "lupine.mlip.calc_evidence.v1"
STATICS_SCHEMA = "lupine.statics_run.v1"

EV_PER_A2_TO_J_PER_M2 = 16.0218  # 1 eV/Angstrom^2 in J/m^2

MODELS: tuple[str, ...] = (
    "chgnet",
    "mace-mp-small",
    "mace-mp-medium",
    "mace-mpa-0-medium",
)
MPTRJ_MODELS: tuple[str, ...] = ("chgnet", "mace-mp-small", "mace-mp-medium")

MODEL_LABELS: Mapping[str, str] = MappingProxyType(
    {
        "chgnet": "CHGNet",
        "mace-mp-small": "MACE-MP small",
        "mace-mp-medium": "MACE-MP medium",
        "mace-mpa-0-medium": "MACE-MPA-0",
    }
)

# Okabe-Ito colorblind-safe palette.
MODEL_COLORS: Mapping[str, str] = MappingProxyType(
    {
        "chgnet": "#E69F00",  # orange
        "mace-mp-small": "#56B4E9",  # sky blue
        "mace-mp-medium": "#009E73",  # bluish green
        "mace-mpa-0-medium": "#CC79A7",  # reddish purple
    }
)
MODEL_MARKERS: Mapping[str, str] = MappingProxyType(
    {
        "chgnet": "o",
        "mace-mp-small": "s",
        "mace-mp-medium": "^",
        "mace-mpa-0-medium": "D",
    }
)
OKABE_ITO_EXTRA = ("#0072B2", "#D55E00", "#F0E442", "#000000")

SINGLE_COL_IN = 3.5
DOUBLE_COL_IN = 7.0

# Display order: fcc metals, bcc metals, then non-metal / compound lanes.
MATERIAL_ORDER: tuple[str, ...] = (
    "Ag", "Al", "Au", "Ca", "Cu", "Ni", "Pd", "Pt", "Sr",
    "Cr", "Fe", "Mo", "Nb", "Ta", "V", "W",
    "Si", "MgO", "NaCl", "NiAl", "Ni3Al",
)
FCC_MATERIALS: tuple[str, ...] = (
    "Ag", "Al", "Au", "Ca", "Cu", "Ni", "Pd", "Pt", "Sr",
)

PROPERTY_ORDER: tuple[str, ...] = (
    "a0",
    "B0",
    "B0_prime",
    "formation_enthalpy",
    "vacancy_formation_energy",
    "gamma_100",
    "gamma_110",
    "gamma_111",
    "stacking_fault_energy",
)
PROPERTY_TEX: Mapping[str, str] = MappingProxyType(
    {
        "a0": r"$a_0$",
        "B0": r"$B_0$",
        "B0_prime": r"$B_0'$",
        "formation_enthalpy": r"$\Delta H_f$",
        "vacancy_formation_energy": r"$E_\mathrm{vac}$",
        "gamma_100": r"$\gamma_{100}$",
        "gamma_110": r"$\gamma_{110}$",
        "gamma_111": r"$\gamma_{111}$",
        "stacking_fault_energy": r"$\gamma_\mathrm{SFE}$",
        "cohesive_energy": r"$E_\mathrm{coh}$",
    }
)
MATERIAL_TEX: Mapping[str, str] = MappingProxyType(
    {"Ni3Al": r"Ni$_3$Al"}
)


class DataConsistencyError(RuntimeError):
    """Raised when an artifact violates the schema this pipeline expects."""


@dataclass(frozen=True)
class PropertyRecord:
    """One bound property: model prediction plus its literature reference."""

    name: str
    unit: str
    predicted: float
    reference: float | None
    reference_source: str | None

    @property
    def rel_err(self) -> float | None:
        """Signed relative error (pred - ref) / |ref| (registered convention)."""
        if self.reference is None or self.reference == 0.0:
            return None
        return (self.predicted - self.reference) / abs(self.reference)


@dataclass(frozen=True)
class CellRecord:
    """One (material, structure, model) cell with bound properties and a0."""

    material: str
    structure: str
    model_id: str
    a0_model: float
    properties: Mapping[str, PropertyRecord]

    def prop(self, name: str) -> PropertyRecord | None:
        return self.properties.get(name)


@dataclass(frozen=True)
class Dataset:
    """All cells plus SHA-256 hashes of every file consumed."""

    cells: tuple[CellRecord, ...]
    input_hashes: Mapping[str, str]

    def cell(self, material: str, model_id: str) -> CellRecord:
        for c in self.cells:
            if c.material == material and c.model_id == model_id:
                return c
        raise DataConsistencyError(f"no cell for ({material}, {model_id})")

    def cells_for_model(self, model_id: str) -> tuple[CellRecord, ...]:
        return tuple(c for c in self.cells if c.model_id == model_id)


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def _load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DataConsistencyError(f"cannot read {path}: {exc}") from exc


def load_dataset() -> Dataset:
    """Load every bound evidence file and its statics companion."""
    hashes: dict[str, str] = {}
    cells: list[CellRecord] = []
    evidence_paths = sorted(BOUND_DIR.glob("*.evidence.json"))
    if not evidence_paths:
        raise DataConsistencyError(f"no evidence files in {BOUND_DIR}")
    for ev_path in evidence_paths:
        payload = _load_json(ev_path)
        if payload.get("schema") != EVIDENCE_SCHEMA:
            raise DataConsistencyError(
                f"{ev_path}: expected schema {EVIDENCE_SCHEMA}, "
                f"got {payload.get('schema')!r}"
            )
        base = ev_path.name.removesuffix(".evidence.json")
        parts = base.split("_")
        if len(parts) < 3:
            raise DataConsistencyError(f"unparseable evidence name: {ev_path.name}")
        model_id = parts[-1]
        structure = parts[-2]
        material = "_".join(parts[:-2])
        if payload.get("material") != material:
            raise DataConsistencyError(
                f"{ev_path}: filename material {material!r} != "
                f"payload {payload.get('material')!r}"
            )
        props: dict[str, PropertyRecord] = {}
        for raw in payload.get("properties", []):
            value = raw.get("value")
            if not isinstance(value, (int, float)) or not math.isfinite(value):
                raise DataConsistencyError(
                    f"{ev_path}: non-finite value for {raw.get('name')!r}"
                )
            ref = raw.get("reference_value")
            if ref is not None and (
                not isinstance(ref, (int, float)) or not math.isfinite(ref)
            ):
                raise DataConsistencyError(
                    f"{ev_path}: non-finite reference for {raw.get('name')!r}"
                )
            props[str(raw["name"])] = PropertyRecord(
                name=str(raw["name"]),
                unit=str(raw.get("unit", "")),
                predicted=float(value),
                reference=None if ref is None else float(ref),
                reference_source=raw.get("reference_source"),
            )
        statics_path = RUNS_DIR / f"{material}_{structure}_{model_id}.json"
        statics = _load_json(statics_path)
        if statics.get("schema") != STATICS_SCHEMA:
            raise DataConsistencyError(
                f"{statics_path}: expected schema {STATICS_SCHEMA}"
            )
        a0_model = (
            statics.get("results", {})
            .get("lattice", {})
            .get("values", {})
            .get("a0_angstrom")
        )
        if not isinstance(a0_model, (int, float)) or not math.isfinite(a0_model):
            raise DataConsistencyError(f"{statics_path}: missing lattice a0")
        rel_ev = ev_path.relative_to(REPO_ROOT).as_posix()
        rel_st = statics_path.relative_to(REPO_ROOT).as_posix()
        hashes[rel_ev] = sha256_of(ev_path)
        hashes[rel_st] = sha256_of(statics_path)
        cells.append(
            CellRecord(
                material=material,
                structure=structure,
                model_id=model_id,
                a0_model=float(a0_model),
                properties=MappingProxyType(props),
            )
        )
    found_models = {c.model_id for c in cells}
    if found_models != set(MODELS):
        raise DataConsistencyError(
            f"model set mismatch: found {sorted(found_models)}"
        )
    return Dataset(cells=tuple(cells), input_hashes=MappingProxyType(hashes))


def load_analysis_artifact(name: str) -> tuple[dict, tuple[str, str]]:
    """Load one analysis artifact; returns (payload, (relpath, sha256))."""
    path = ANALYSIS_DIR / name
    payload = _load_json(path)
    return payload, (path.relative_to(REPO_ROOT).as_posix(), sha256_of(path))


# ---------------------------------------------------------------- statistics


def spearman_rho(x: np.ndarray, y: np.ndarray) -> float:
    from scipy import stats

    rho = stats.spearmanr(np.asarray(x, float), np.asarray(y, float)).statistic
    return float(rho)


def pearson_r(x: np.ndarray, y: np.ndarray) -> float:
    from scipy import stats

    return float(stats.pearsonr(np.asarray(x, float), np.asarray(y, float))[0])


def loglog_fit(pred: np.ndarray, ref: np.ndarray) -> tuple[float, float, float]:
    """OLS of log(pred) on log(ref): returns (alpha, prefactor c, R^2).

    Model: pred ~= c * ref^alpha. Inputs must be strictly positive.
    """
    pred = np.asarray(pred, float)
    ref = np.asarray(ref, float)
    if np.any(pred <= 0) or np.any(ref <= 0):
        raise DataConsistencyError("loglog_fit requires strictly positive values")
    x = np.log(ref)
    y = np.log(pred)
    alpha, intercept = np.polyfit(x, y, 1)
    fitted = alpha * x + intercept
    ss_res = float(np.sum((y - fitted) ** 2))
    ss_tot = float(np.sum((y - np.mean(y)) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else float("nan")
    return float(alpha), float(math.exp(intercept)), r2


def bootstrap_alpha_ci(
    pred: np.ndarray,
    ref: np.ndarray,
    *,
    rng: np.random.Generator,
    n_bootstrap: int = 1000,
) -> tuple[float, float]:
    """Percentile 95% CI for the log-log slope (points resampled)."""
    pred = np.asarray(pred, float)
    ref = np.asarray(ref, float)
    n = pred.size
    slopes = np.empty(n_bootstrap, dtype=float)
    for i in range(n_bootstrap):
        idx = rng.integers(0, n, size=n)
        slopes[i] = np.polyfit(np.log(ref[idx]), np.log(pred[idx]), 1)[0]
    return float(np.percentile(slopes, 2.5)), float(np.percentile(slopes, 97.5))


# ------------------------------------------------------- environment field


def fcc_area_per_surface_atom(a0: float, miller: str) -> float:
    """Area per surface atom (A^2) of an fcc facet with lattice constant a0."""
    if miller == "100":
        return a0 * a0 / 2.0
    if miller == "111":
        return math.sqrt(3.0) / 4.0 * a0 * a0
    if miller == "110":
        return a0 * a0 / math.sqrt(2.0)
    raise DataConsistencyError(f"unknown fcc facet {miller!r}")


@dataclass(frozen=True)
class EnvFieldCell:
    """The measured error field for one (model, material) fcc cell."""

    model_id: str
    material: str
    a0_model: float
    de8: float  # eV/surface atom, from gamma_100 error (coordination 8)
    de9: float  # eV/surface atom, from gamma_111 error (coordination 9)
    de11: float  # eV/atom, from E_vac error / 12 (coordination 11)
    predicted_gamma110_error: float  # J/m^2, blind linear continuation
    actual_gamma110_error: float  # J/m^2


def environment_field_cells(dataset: Dataset) -> tuple[EnvFieldCell, ...]:
    """Compute the anchor errors and the blind gamma_110 prediction.

    Delta-eps(c) = per-atom energy error at first-shell coordination c:
      c=8  <- (gamma_100 err) * A_100 / 16.0218
      c=9  <- (gamma_111 err) * A_111 / 16.0218
      c=11 <- (E_vac err) / 12
    Blind prediction for gamma_110 (probes c=7 top layer + c=11 subsurface):
      de7 ~ 2*de8 - de9  (linear continuation in c)
      gamma_110 err ~ (de7 + de11) * 16.0218 / A_110
    Areas use the model's own relaxed a0 (the slabs were built at model a0).
    """
    out: list[EnvFieldCell] = []
    for model in MODELS:
        for material in FCC_MATERIALS:
            cell = dataset.cell(material, model)
            required = (
                "gamma_100",
                "gamma_111",
                "gamma_110",
                "vacancy_formation_energy",
            )
            recs = {name: cell.prop(name) for name in required}
            missing = [
                n for n, r in recs.items() if r is None or r.reference is None
            ]
            if missing:
                raise DataConsistencyError(
                    f"({material}, {model}) missing references: {missing}"
                )
            a0 = cell.a0_model
            a100 = fcc_area_per_surface_atom(a0, "100")
            a111 = fcc_area_per_surface_atom(a0, "111")
            a110 = fcc_area_per_surface_atom(a0, "110")
            g100, g111 = recs["gamma_100"], recs["gamma_111"]
            g110, evac = recs["gamma_110"], recs["vacancy_formation_energy"]
            de8 = (g100.predicted - g100.reference) * a100 / EV_PER_A2_TO_J_PER_M2
            de9 = (g111.predicted - g111.reference) * a111 / EV_PER_A2_TO_J_PER_M2
            de11 = (evac.predicted - evac.reference) / 12.0
            predicted = (2.0 * de8 - de9 + de11) / (a110 / EV_PER_A2_TO_J_PER_M2)
            actual = g110.predicted - g110.reference
            out.append(
                EnvFieldCell(
                    model_id=model,
                    material=material,
                    a0_model=a0,
                    de8=de8,
                    de9=de9,
                    de11=de11,
                    predicted_gamma110_error=predicted,
                    actual_gamma110_error=actual,
                )
            )
    return tuple(out)


# ------------------------------------------------------------------ styling


def apply_style() -> None:
    matplotlib.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["DejaVu Sans"],
            "font.size": 8.0,
            "axes.labelsize": 8.0,
            "axes.titlesize": 8.0,
            "xtick.labelsize": 7.0,
            "ytick.labelsize": 7.0,
            "legend.fontsize": 6.5,
            "legend.frameon": False,
            "axes.linewidth": 0.6,
            "xtick.major.width": 0.6,
            "ytick.major.width": 0.6,
            "xtick.minor.width": 0.45,
            "ytick.minor.width": 0.45,
            "lines.linewidth": 1.0,
            "lines.markersize": 3.5,
            "pdf.fonttype": 42,  # embed TrueType, no Type-3
            "ps.fonttype": 42,
            "svg.fonttype": "none",
            "figure.dpi": 150,
            "savefig.dpi": 300,
        }
    )


def panel_label(ax, text: str, *, x: float = -0.12, y: float = 1.04) -> None:
    ax.text(
        x, y, text, transform=ax.transAxes, fontsize=9,
        fontweight="bold", va="bottom", ha="right",
    )


def save_figure(fig, stem: str) -> dict[str, dict[str, str]]:
    """Write vector PDF + 300 dpi PNG; return relative paths and hashes."""
    outputs: dict[str, dict[str, str]] = {}
    pdf_path = OUT_DIR / f"{stem}.pdf"
    fig.savefig(pdf_path, format="pdf", metadata={"CreationDate": None})
    png_path = OUT_DIR / f"{stem}.png"
    fig.savefig(png_path, format="png", dpi=300)
    for path in (pdf_path, png_path):
        outputs[path.suffix.lstrip(".")] = {
            "path": path.relative_to(REPO_ROOT).as_posix(),
            "sha256": sha256_of(path),
        }
    return outputs


def material_label(material: str) -> str:
    return MATERIAL_TEX.get(material, material)


__all__ = [
    "ANALYSIS_DIR",
    "BOUND_DIR",
    "CellRecord",
    "DataConsistencyError",
    "Dataset",
    "DOUBLE_COL_IN",
    "ENVFIELD_EXPERIMENT_DIR",
    "EV_PER_A2_TO_J_PER_M2",
    "EnvFieldCell",
    "FCC_MATERIALS",
    "MATERIAL_ORDER",
    "MODEL_COLORS",
    "MODEL_LABELS",
    "MODEL_MARKERS",
    "MODELS",
    "MPTRJ_MODELS",
    "OUT_DIR",
    "PROPERTY_ORDER",
    "PROPERTY_TEX",
    "PropertyRecord",
    "REPO_ROOT",
    "RUNS_DIR",
    "SINGLE_COL_IN",
    "apply_style",
    "bootstrap_alpha_ci",
    "environment_field_cells",
    "fcc_area_per_surface_atom",
    "load_analysis_artifact",
    "load_dataset",
    "loglog_fit",
    "material_label",
    "panel_label",
    "pearson_r",
    "save_figure",
    "sha256_of",
    "spearman_rho",
]
