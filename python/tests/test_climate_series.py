"""Mirror tests for lupine_distill.odf.climate_series.

Every certificate here maps to a theorem in
``OpenDistillationFactory.Materials.Validation.ClimateSeries``. The tests do
not re-prove the arithmetic — they verify that the Python mirror emits the
expected claims, theorem references, and pass/fail outcomes.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from lupine_distill.odf.climate_series import (
    THEOREM_REFS,
    all_certificates,
    synthesis_funnel_certificates,
)

pytestmark = pytest.mark.unit

_REPO_ROOT = Path(__file__).resolve().parents[2]
_LEAN_MATERIALS = _REPO_ROOT / "lean-spec" / "OpenDistillationFactory" / "Materials"


def test_synthesis_funnel_passes():
    certs = synthesis_funnel_certificates()
    assert all(cert.passes for cert in certs)
    assert any(cert.claim_id == "gnome_validation_rate" for cert in certs)
    assert any(cert.claim_id == "alab_true_novelty" for cert in certs)


def test_all_certificates_pass():
    certs = all_certificates()
    assert len(certs) == 10
    assert all(cert.passes for cert in certs)


def test_inventory_floor_respects_current_counts():
    from lupine_distill.odf.climate_series import inventory_certificates

    certs = inventory_certificates(modules=52, theorems=191, sorrys=0)
    assert len(certs) == 1
    assert certs[0].passes
    assert "52 modules" in certs[0].statement
    assert "191" in certs[0].statement


def test_inventory_floor_fails_on_sorry():
    from lupine_distill.odf.climate_series import inventory_certificates

    certs = inventory_certificates(modules=51, theorems=190, sorrys=1)
    assert not certs[0].passes


def test_every_theorem_ref_resolves_in_lean_sources():
    lean_text = "\n".join(
        p.read_text(encoding="utf-8") for p in _LEAN_MATERIALS.rglob("*.lean")
    )
    for key, ref in THEOREM_REFS.items():
        short = ref.rsplit(".", 1)[-1]
        pattern = rf"theorem\s+{re.escape(short)}\b"
        assert re.search(pattern, lean_text), (
            f"THEOREM_REFS[{key!r}] = {ref!r}: no declaration named {short!r} "
            "found in lean-spec Materials sources — Lean rename without "
            "updating the Python mirror?"
        )
