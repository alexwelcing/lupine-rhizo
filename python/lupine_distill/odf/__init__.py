"""Open Distillation Factory (ODF) integration package.

Houses the ATLAS-aware promotion machinery wired into the OperatorPack
promotion pipeline (ATLAS_Lean_Integration_Review.md §13):

  - ``schema_bridge``       — the shared benchmark/promotion contract with
                              lupine_distill (the canonical producer).
  - ``promotion_gate``      — the formal-verification promotion gate
                              ("[NEW] Formal specification check", §13.2).
  - ``model_card``          — the theorem-aware OperatorPack model-card emitter.
  - ``field_certificates``  — the environment-error-field certificate surface:
                              domain-gate admits/refusals with witnesses,
                              anchor-admissibility tiers, and ranking-inversion
                              impossibility certificates, each naming the
                              lean-spec theorem that backs it.
"""

from __future__ import annotations

__all__ = ["promotion_gate", "model_card", "schema_bridge", "field_certificates"]
