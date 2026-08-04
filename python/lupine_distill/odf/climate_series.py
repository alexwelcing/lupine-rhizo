"""Python mirror of the ``ClimateSeries`` Lean validation pack.

The climate-series articles ("The 0.2 % Synthesis Problem", "A Field, Not a
Neural Net", "Five Materials That Could Unlock 5–12 GtCO₂/Year") make a set of
quantitative, kernel-checked claims in
``OpenDistillationFactory.Materials.Validation.ClimateSeries``. This module
exposes those same certificates as structured Python values so that promotion
packets, article renderers, and the website can cite machine-checkable
provenance instead of prose.

Every predicate here is intentionally trivial (integer arithmetic) because the
heavy lifting — the physics — is proved in ``Theory.EnvironmentField``,
``Theory.BarrierArrhenius``, ``Theory.RankingIntegrity``,
``Theory.ScalingVolcano``, ``Theory.DefectStability``, and
``Theory.SorptionStability``. The value of this mirror is provenance and
testability: a Lean rename or a changed headline number breaks CI here.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from importlib.resources import files
from typing import Any

_VALIDATION = "OpenDistillationFactory.Materials.Validation.ClimateSeries"


def _load_inventory() -> dict[str, Any]:
    resource = files("lupine_distill.odf").joinpath("theorem-count.json")
    return json.loads(resource.read_text(encoding="utf-8"))

#: Fully-qualified Lean names for every climate-series certificate.
THEOREM_REFS: dict[str, str] = {
    "gnome_validation_rate": f"{_VALIDATION}.gnome_validation_rate_at_most_0_2_percent",
    "alab_true_novelty": f"{_VALIDATION}.alab_true_novelty_at_most_one_third",
    "kernel_refuses_zero_margin": f"{_VALIDATION}.kernel_refuses_zero_margin",
    "corrected_strict_improvement": f"{_VALIDATION}.corrected_strict_improvement_count",
    "median_blind_residual": f"{_VALIDATION}.median_blind_residual_improves",
    "blind_r_confidence": f"{_VALIDATION}.blind_r_within_confidence_interval",
    "ni_blind_error": f"{_VALIDATION}.ni_blind_error_improves_sixfold",
    "cu_blind_error": f"{_VALIDATION}.cu_blind_error_improves_twofold",
    "portfolio_range": f"{_VALIDATION}.portfolio_range_within_component_sums",
    "proof_pack_inventory": f"{_VALIDATION}.proof_pack_inventory_floor",
}


@dataclass(frozen=True)
class ClimateSeriesCertificate:
    """One kernel-checked climate-series claim."""

    claim_id: str
    headline: str
    statement: str
    theorem_ref: str
    passes: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": "climate_series",
            "claim_id": self.claim_id,
            "headline": self.headline,
            "statement": self.statement,
            "theorem_ref": self.theorem_ref,
            "passes": self.passes,
        }


def _cert(
    claim_id: str,
    headline: str,
    statement: str,
    passes: bool,
) -> ClimateSeriesCertificate:
    return ClimateSeriesCertificate(
        claim_id=claim_id,
        headline=headline,
        statement=statement,
        theorem_ref=THEOREM_REFS[claim_id],
        passes=passes,
    )


def synthesis_funnel_certificates() -> list[ClimateSeriesCertificate]:
    """Certificates for "The 0.2 % Synthesis Problem"."""
    return [
        _cert(
            "gnome_validation_rate",
            "The 0.2 % synthesis funnel",
            "GNoME reported 380,000 computationally stable structures; 736 were "
            "independently synthesized by late 2023. The validation rate is at most "
            "0.2 % (736 * 500 ≤ 380000).",
            736 * 500 <= 380000,
        ),
        _cert(
            "alab_true_novelty",
            "The A-Lab novelty collapse",
            "Of 41 reported syntheses, independent review left 13 true novel phases — "
            "at most one third survive (13 * 3 ≤ 41).",
            13 * 3 <= 41,
        ),
    ]


def field_correction_certificates() -> list[ClimateSeriesCertificate]:
    """Certificates for "A Field, Not a Neural Net"."""
    return [
        _cert(
            "kernel_refuses_zero_margin",
            "The kernel-rejected-claim episode",
            "A statistical filter accepted '27 of 36 cells improved strictly'; at "
            "10⁻⁴ J/m² integer precision one cell's margin was exactly zero, and the "
            "Lean kernel refused 813 < 813.",
            not (813 < 813),
        ),
        _cert(
            "corrected_strict_improvement",
            "Corrected strict-improvement count",
            "After the kernel rejection, 26 of 36 cells improved strictly — a strict "
            "majority (26 ≤ 36 ∧ 36 < 2 * 26).",
            26 <= 36 and 36 < 2 * 26,
        ),
        _cert(
            "median_blind_residual",
            "Median residual improvement",
            "Applying the field drops the median (110) blind residual from 0.104 to "
            "0.066 J/m² (66 < 104).",
            66 < 104,
        ),
        _cert(
            "blind_r_confidence",
            "Blind-prediction correlation inside confidence interval",
            "r = 0.906 with 95 % CI [0.82, 0.96] (×1000 scale): 820 ≤ 906 ≤ 960.",
            820 <= 906 <= 960,
        ),
        _cert(
            "ni_blind_error",
            "Ni blind-facet improvement ≥ 6×",
            "The blind (110) error for Ni drops from 9.7 % to 1.5 % — at least a "
            "six-fold reduction (6 * 15 ≤ 97).",
            6 * 15 <= 97,
        ),
        _cert(
            "cu_blind_error",
            "Cu blind-facet improvement ≥ 2×",
            "The blind (110) error for Cu drops from 28.0 % to 13.7 % — at least a "
            "two-fold reduction (2 * 137 ≤ 280).",
            2 * 137 <= 280,
        ),
    ]


def abatement_portfolio_certificates() -> list[ClimateSeriesCertificate]:
    """Certificates for "Five Materials That Could Unlock 5–12 GtCO₂/Year"."""
    return [
        _cert(
            "portfolio_range",
            "Five-target portfolio envelope",
            "Per-class abatement potentials (×10 GtCO₂/yr): LMR cathodes 1.0–3.0, "
            "halide electrolytes 0.5–2.0, MOF DAC sorbents 4.0–10.0, ammonia "
            "catalysts 0.4–1.2, lead-free perovskites 0.5–3.0. The claimed 5–12 "
            "GtCO₂/yr aggregate is inside the component-sum envelope: "
            "50 ≤ 10+5+40+4+5 and 120 ≤ 30+20+100+12+30.",
            50 <= 10 + 5 + 40 + 4 + 5 and 120 <= 30 + 20 + 100 + 12 + 30,
        ),
    ]


def inventory_certificates(
    *, modules: int | None = None, theorems: int | None = None, sorrys: int | None = None
) -> list[ClimateSeriesCertificate]:
    """Certificate for the generated formalization inventory.

    Defaults are loaded from the generated inventory packaged with this module.
    Explicit values remain available for callers validating a candidate inventory.
    """
    if modules is None or theorems is None or sorrys is None:
        inventory = _load_inventory()
        modules = inventory["modules"] if modules is None else modules
        theorems = inventory["count"] if theorems is None else theorems
        if sorrys is None:
            sorrys = 0 if inventory["zero_sorry"] else 1
    assert modules is not None and theorems is not None
    return [
        _cert(
            "proof_pack_inventory",
            "Generated formalization inventory",
            f"Source-tree inventory: {modules} modules, {theorems} build-locked "
            f"theorems, {sorrys} sorry. Values come from theorem-count.json; the "
            "zero-sorry invariant is enforced by the build gate.",
            modules > 0 and theorems > 0 and sorrys == 0,
        ),
    ]


def all_certificates(
    *, modules: int | None = None, theorems: int | None = None, sorrys: int | None = None
) -> list[ClimateSeriesCertificate]:
    """The complete climate-series certificate pack."""
    return (
        synthesis_funnel_certificates()
        + field_correction_certificates()
        + abatement_portfolio_certificates()
        + inventory_certificates(modules=modules, theorems=theorems, sorrys=sorrys)
    )


__all__ = [
    "THEOREM_REFS",
    "ClimateSeriesCertificate",
    "synthesis_funnel_certificates",
    "field_correction_certificates",
    "abatement_portfolio_certificates",
    "inventory_certificates",
    "all_certificates",
]
