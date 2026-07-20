from __future__ import annotations

import json
import os
import pathlib
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from typing import Any, Protocol

import numpy as np

from .policy import RuntimePolicy


def _domain_action(prediction: dict[str, Any], context: dict[str, Any] | None) -> dict[str, Any] | None:
    """Run the Lean-mirror field-domain gate when coordination data is present.

    If the prediction or context carries ``first_shell_coordinations`` and any
    atom is outside the measured first-shell domain ``[cmin, cmax]``, return a
    ``skip_correction`` action backed by ``FieldDomain.refusal_has_witness``.
    The absence of coordination data is inert — the gate never refuses a
    prediction just because the runner did not supply it.
    """
    coords = prediction.get("first_shell_coordinations")
    if coords is None and context is not None:
        coords = context.get("first_shell_coordinations")
    if coords is None:
        return None
    try:
        coord_seq = [int(c) for c in coords]
    except (TypeError, ValueError):
        return None
    if not coord_seq:
        return None
    from lupine_distill.odf.field_certificates import check_field_domain

    cert = check_field_domain(coord_seq)
    if cert.admitted:
        return None
    return {
        "action": "skip_correction",
        "reason": f"lean_certificate_refusal: {cert.reason}",
        "kind": "field_domain",
        "cmin": cert.cmin,
        "cmax": cert.cmax,
        "witnesses": [list(w) for w in cert.witnesses],
        "theorem_ref": cert.theorem_ref,
    }


def _repo_root() -> pathlib.Path:
    return pathlib.Path(__file__).resolve().parents[2]


def _default_atlas_distill_bin() -> pathlib.Path:
    exe = "atlas-distill.exe" if os.name == "nt" else "atlas-distill"
    found = shutil.which("atlas-distill")
    if found:
        return pathlib.Path(found)
    return _repo_root() / "atlas-distill" / "target" / "debug" / exe


#: Default env-field binding report (emitted by
#: ``python/scripts/bind_env_field_instances.py``) consulted by the run-time
#: certificate gate when the session runs from a repo checkout.
def _default_env_field_report() -> pathlib.Path:
    return (
        _repo_root() / "data" / "y_matrix_runs" / "env_field_binding_report.json"
    )


def jsonable(value: Any) -> Any:
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, np.ndarray):
        return jsonable(value.tolist())
    if isinstance(value, dict):
        return {str(key): jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [jsonable(item) for item in value]
    return value


@dataclass
class DistillDecision:
    corrected_prediction: dict[str, Any]
    actions: list[dict[str, Any]]
    refused: bool = False
    decision: str = "accept"
    decision_id: str | None = None
    ribbon_version: str | None = None
    policy_engine: str = "python"
    theorem_hooks: dict[str, Any] | None = None
    raw: dict[str, Any] = field(default_factory=dict)


class DistillPolicyEngine(Protocol):
    name: str

    def decide(
        self,
        *,
        row_id: str,
        mlip_id: str,
        prediction: dict[str, Any],
        support_model: Any | None,
        context: dict[str, Any] | None = None,
    ) -> DistillDecision:
        ...

    def decide_many(
        self,
        *,
        row_id: str,
        mlip_id: str,
        predictions: list[dict[str, Any]],
        support_model: Any | None,
        contexts: list[dict[str, Any]] | None = None,
    ) -> list[DistillDecision]:
        ...


def _decision_from_payload(payload: dict[str, Any], *, policy_engine: str) -> DistillDecision:
    corrected = payload.get("corrected_prediction")
    if not isinstance(corrected, dict):
        raise ValueError("distill-policy decision missing corrected_prediction object")
    actions = payload.get("actions")
    if not isinstance(actions, list):
        raise ValueError("distill-policy decision missing actions list")
    return DistillDecision(
        corrected_prediction=corrected,
        actions=[action for action in actions if isinstance(action, dict)],
        refused=bool(payload.get("refused")),
        decision=str(payload.get("decision", "accept")),
        decision_id=str(payload.get("decision_id")) if payload.get("decision_id") else None,
        ribbon_version=str(payload.get("ribbon_version")) if payload.get("ribbon_version") else None,
        policy_engine=policy_engine,
        theorem_hooks=payload.get("theorem_hooks") if isinstance(payload.get("theorem_hooks"), dict) else None,
        raw=payload,
    )


def _annotate_domain_action(
    decision: DistillDecision, action: dict[str, Any] | None
) -> DistillDecision:
    if action is None:
        return decision
    existing = next(
        (item for item in decision.actions if item.get("kind") == "field_domain"),
        None,
    )
    effective = existing or action
    if existing is None:
        decision.actions = list(decision.actions) + [action]
    hooks = dict(decision.theorem_hooks or {})
    hooks["field_domain_certificate"] = effective
    decision.theorem_hooks = hooks
    return decision


class PythonPolicyEngine:
    name = "python"

    def __init__(self, profile: str) -> None:
        self.policy = RuntimePolicy(profile)

    def decide(
        self,
        *,
        row_id: str,
        mlip_id: str,
        prediction: dict[str, Any],
        support_model: Any | None,
        context: dict[str, Any] | None = None,
    ) -> DistillDecision:
        current = prediction
        actions: list[dict[str, Any]] = []
        domain_action = _domain_action(prediction, context)
        if domain_action is not None:
            actions.append(domain_action)
            support_model = None
        if support_model is not None:
            current, actions = support_model.correct_prediction(prediction)
            actions = actions + self.policy.guard_prediction(row_id, current)
        else:
            actions = actions + self.policy.guard_prediction(row_id, current)
        return DistillDecision(
            corrected_prediction=current,
            actions=actions,
            refused=any(action.get("action") == "refuse" for action in actions),
            decision="refuse" if any(action.get("action") == "refuse" for action in actions) else "accept",
            policy_engine=self.name,
        )

    def decide_many(
        self,
        *,
        row_id: str,
        mlip_id: str,
        predictions: list[dict[str, Any]],
        support_model: Any | None,
        contexts: list[dict[str, Any]] | None = None,
    ) -> list[DistillDecision]:
        contexts = contexts or [{} for _ in predictions]
        return [
            self.decide(
                row_id=row_id,
                mlip_id=mlip_id,
                prediction=prediction,
                support_model=support_model,
                context=contexts[idx] if idx < len(contexts) else {},
            )
            for idx, prediction in enumerate(predictions)
        ]


class RustPolicyEngine:
    name = "rust"

    def __init__(
        self,
        *,
        atlas_distill_bin: str | os.PathLike[str] | None = None,
        ribbon_version: str = "hyperribbon-v1",
        policy_limits_path: str | os.PathLike[str] | None = None,
        timeout_s: int = 30,
    ) -> None:
        configured = atlas_distill_bin or os.environ.get("ATLAS_DISTILL_BIN")
        self.atlas_distill_bin = pathlib.Path(configured) if configured else _default_atlas_distill_bin()
        self.ribbon_version = ribbon_version
        self.policy_limits_path = pathlib.Path(policy_limits_path) if policy_limits_path else None
        self.timeout_s = timeout_s

    @property
    def available(self) -> bool:
        return self.atlas_distill_bin.exists()

    def _policy_limits_args(self) -> list[str]:
        if not self.policy_limits_path:
            return []
        return ["--policy-limits", str(self.policy_limits_path)]

    def decide(
        self,
        *,
        row_id: str,
        mlip_id: str,
        prediction: dict[str, Any],
        support_model: Any | None,
        context: dict[str, Any] | None = None,
    ) -> DistillDecision:
        if not self.available:
            raise FileNotFoundError(f"atlas-distill binary not found: {self.atlas_distill_bin}")
        domain_action = _domain_action(prediction, context)
        request = self._request(
            row_id=row_id,
            mlip_id=mlip_id,
            prediction=prediction,
            support_model=None if domain_action is not None else support_model,
            context=context,
        )
        with tempfile.TemporaryDirectory(prefix="lupine-distill-policy-") as tmp:
            request_path = pathlib.Path(tmp) / "request.json"
            request_path.write_text(json.dumps(request, sort_keys=True), encoding="utf-8")
            proc = subprocess.run(
                [
                    str(self.atlas_distill_bin),
                    "distill-policy",
                    "--request",
                    str(request_path),
                    "--ribbon-version",
                    self.ribbon_version,
                    *self._policy_limits_args(),
                ],
                check=False,
                capture_output=True,
                text=True,
                timeout=self.timeout_s,
            )
        if proc.returncode != 0:
            raise RuntimeError(
                "atlas-distill distill-policy failed "
                f"(exit {proc.returncode}): {(proc.stderr or proc.stdout).strip()}"
            )
        decision = _decision_from_payload(json.loads(proc.stdout), policy_engine=self.name)
        return _annotate_domain_action(decision, domain_action)

    def decide_many(
        self,
        *,
        row_id: str,
        mlip_id: str,
        predictions: list[dict[str, Any]],
        support_model: Any | None,
        contexts: list[dict[str, Any]] | None = None,
    ) -> list[DistillDecision]:
        if not predictions:
            return []
        if not self.available:
            raise FileNotFoundError(f"atlas-distill binary not found: {self.atlas_distill_bin}")
        contexts = contexts or [{} for _ in predictions]
        domain_actions = [
            _domain_action(prediction, contexts[idx] if idx < len(contexts) else {})
            for idx, prediction in enumerate(predictions)
        ]
        requests = [
            self._request(
                row_id=row_id,
                mlip_id=mlip_id,
                prediction=prediction,
                support_model=None if domain_actions[idx] is not None else support_model,
                context=contexts[idx] if idx < len(contexts) else {},
            )
            for idx, prediction in enumerate(predictions)
        ]
        with tempfile.TemporaryDirectory(prefix="lupine-distill-policy-batch-") as tmp:
            tmp_path = pathlib.Path(tmp)
            request_path = tmp_path / "requests.jsonl"
            output_path = tmp_path / "decisions.jsonl"
            request_path.write_text(
                "".join(json.dumps(request, sort_keys=True) + "\n" for request in requests),
                encoding="utf-8",
            )
            proc = subprocess.run(
                [
                    str(self.atlas_distill_bin),
                    "distill-policy",
                    "--request-jsonl",
                    str(request_path),
                    "--output",
                    str(output_path),
                    "--ribbon-version",
                    self.ribbon_version,
                    *self._policy_limits_args(),
                ],
                check=False,
                capture_output=True,
                text=True,
                timeout=max(self.timeout_s, self.timeout_s * len(predictions)),
            )
            output_text = output_path.read_text(encoding="utf-8") if output_path.exists() else proc.stdout
        if proc.returncode != 0:
            raise RuntimeError(
                "atlas-distill distill-policy batch failed "
                f"(exit {proc.returncode}): {(proc.stderr or proc.stdout).strip()}"
            )
        decisions = [
            _decision_from_payload(json.loads(line), policy_engine=self.name)
            for line in output_text.splitlines()
            if line.strip()
        ]
        if len(decisions) != len(predictions):
            raise ValueError(
                "distill-policy batch returned "
                f"{len(decisions)} decisions for {len(predictions)} predictions"
            )
        return [
            _annotate_domain_action(decision, domain_actions[idx])
            for idx, decision in enumerate(decisions)
        ]

    def _request(
        self,
        *,
        row_id: str,
        mlip_id: str,
        prediction: dict[str, Any],
        support_model: Any | None,
        context: dict[str, Any] | None,
    ) -> dict[str, Any]:
        return {
            "schema": "lupine.distill.policy_request.v1",
            "ribbon_version": self.ribbon_version,
            "row_id": row_id,
            "mlip_id": mlip_id,
            "prediction": jsonable(prediction),
            "support": support_evidence(support_model),
            "context": context or {},
        }


def _material_roots_for_prediction(prediction: dict[str, Any]) -> set[str]:
    """Candidate material keys for certificate lookup: the normalized
    ``material_id`` root (and its leading token), plus the element symbol of
    single-species configurations. Conservative by design — multi-species
    systems only match on an explicit material id."""
    roots: set[str] = set()
    material_id = prediction.get("material_id")
    if isinstance(material_id, str) and material_id.strip():
        normalized = material_id.strip().lower()
        for suffix in ("-support", "_support"):
            if normalized.endswith(suffix):
                normalized = normalized[: -len(suffix)]
        if normalized:
            roots.add(normalized)
            head = re.split(r"[-_:/ ]", normalized, maxsplit=1)[0]
            if head:
                roots.add(head)
    species: set[str] = set()
    chemical_system = prediction.get("chemical_system")
    if isinstance(chemical_system, str) and chemical_system.strip():
        species = {
            part.strip().lower()
            for part in chemical_system.replace(",", "-").split("-")
            if part.strip()
        }
    elif isinstance(prediction.get("symbols"), list):
        species = {
            str(symbol).strip().lower()
            for symbol in prediction["symbols"]
            if str(symbol).strip()
        }
    if len(species) == 1:
        roots.add(next(iter(species)))
    return roots


@dataclass(frozen=True)
class CertificateGate:
    """Run-time mirror of the Lean tier-2 refusal certificates.

    A (model, material) cell whose measured anchors violate monotone
    softening carries a kernel-checked refusal
    (``¬ scaledAnchorsValid …`` and friends in
    ``lean-spec … Theory/AnchoredField.lean``): the directional correction is
    provably outside its domain there, so the cell must be EXCLUDED from
    correction at run time — not corrected and flagged after the fact. The
    gate indexes those refusals from the env-field binding report and the
    wrapping engine strips the support model for matching predictions (the
    finite/explosion guards still run; the prediction itself is not refused).
    """

    #: (binder model_id, lowercase material) -> report entry with certificate.
    refusals: dict[tuple[str, str], dict[str, Any]]
    report_path: str
    corpus_sha256_12: str | None

    @classmethod
    def load(
        cls, report_path: str | os.PathLike[str] | None
    ) -> CertificateGate:
        """Build the gate from a validated expected binding report."""
        path = pathlib.Path(report_path) if report_path else _default_env_field_report()
        if not path.exists():
            raise FileNotFoundError(f"expected binding report not found: {path}")
        try:
            report = json.loads(path.read_text(encoding="utf-8"))
        except OSError as exc:
            raise ValueError(f"cannot read expected binding report {path}: {exc}") from exc
        except ValueError as exc:
            raise ValueError(f"malformed binding report JSON {path}: {exc}") from exc
        if not isinstance(report, dict):
            raise ValueError(f"binding report must be a JSON object: {path}")
        from lupine_distill.odf.field_certificates import (
            RUNTIME_MLIP_ALIASES,
            certificates_from_binding_report,
        )

        refusals: dict[tuple[str, str], dict[str, Any]] = {}
        for entry in certificates_from_binding_report(report, report_path=path):
            if entry["certificate"].tier != "measured_field":
                continue
            model_id = str(entry["model_id"])
            material = str(entry["material"]).lower()
            refusals[(model_id, material)] = entry
        # Index each refusal under the runtime backend id too (the runner's
        # "mace-mp-0" is the binder's "mace-mp-medium"): production cells
        # look up with the runtime id, and an exact-only index would let
        # aliased models slip past the gate and still be corrected.
        for runtime_id, binder_id in RUNTIME_MLIP_ALIASES.items():
            for (model_id, material), entry in list(refusals.items()):
                if model_id == binder_id:
                    refusals.setdefault((runtime_id, material), entry)
        return cls(
            refusals=refusals,
            report_path=str(path),
            corpus_sha256_12=report.get("corpus_sha256_12"),
        )

    def refusal_for(
        self, mlip_id: str, prediction: dict[str, Any]
    ) -> dict[str, Any] | None:
        for root in _material_roots_for_prediction(prediction):
            entry = self.refusals.get((mlip_id, root))
            if entry is not None:
                return entry
        return None

    def skip_action(self, entry: dict[str, Any]) -> dict[str, Any]:
        certificate = entry["certificate"]
        return {
            "action": "skip_correction",
            "reason": f"lean_certificate_refusal: {certificate.reason}",
            "material": entry["material"],
            "structure": entry["structure"],
            "lean_name": entry["lean_name"],
            "theorem_ref": entry["outcome_theorem_ref"],
            "anchors_scaled": list(certificate.anchors_scaled),
            "corpus_sha256_12": self.corpus_sha256_12,
        }


class CertificateGatedPolicyEngine:
    """Wrap any policy engine with the Lean certificate gate: predictions on
    tier-2-refused (model, material) cells are decided WITHOUT the support
    model — no correction is applied — and the decision carries a
    ``skip_correction`` action naming the refusal theorem. Everything else
    passes through untouched."""

    def __init__(self, inner: DistillPolicyEngine, gate: CertificateGate) -> None:
        self.inner = inner
        self.gate = gate

    @property
    def name(self) -> str:
        return f"certificate_gated({getattr(self.inner, 'name', 'unknown')})"

    def _annotate(self, decision: DistillDecision, entry: dict[str, Any]) -> DistillDecision:
        action = self.gate.skip_action(entry)
        decision.actions = list(decision.actions) + [action]
        hooks = dict(decision.theorem_hooks or {})
        hooks["env_field_certificate"] = action
        decision.theorem_hooks = hooks
        return decision

    def decide(
        self,
        *,
        row_id: str,
        mlip_id: str,
        prediction: dict[str, Any],
        support_model: Any | None,
        context: dict[str, Any] | None = None,
    ) -> DistillDecision:
        entry = (
            self.gate.refusal_for(mlip_id, prediction)
            if support_model is not None
            else None
        )
        decision = self.inner.decide(
            row_id=row_id,
            mlip_id=mlip_id,
            prediction=prediction,
            support_model=None if entry is not None else support_model,
            context=context,
        )
        return self._annotate(decision, entry) if entry is not None else decision

    def decide_many(
        self,
        *,
        row_id: str,
        mlip_id: str,
        predictions: list[dict[str, Any]],
        support_model: Any | None,
        contexts: list[dict[str, Any]] | None = None,
    ) -> list[DistillDecision]:
        contexts = contexts or [{} for _ in predictions]
        entries = [
            self.gate.refusal_for(mlip_id, prediction)
            if support_model is not None
            else None
            for prediction in predictions
        ]
        gated = [idx for idx, entry in enumerate(entries) if entry is not None]
        if not gated:
            return self.inner.decide_many(
                row_id=row_id,
                mlip_id=mlip_id,
                predictions=predictions,
                support_model=support_model,
                contexts=contexts,
            )
        allowed = [idx for idx, entry in enumerate(entries) if entry is None]
        decisions: list[DistillDecision | None] = [None] * len(predictions)
        if allowed:
            for idx, decision in zip(
                allowed,
                self.inner.decide_many(
                    row_id=row_id,
                    mlip_id=mlip_id,
                    predictions=[predictions[idx] for idx in allowed],
                    support_model=support_model,
                    contexts=[contexts[idx] for idx in allowed],
                ),
                strict=True,
            ):
                decisions[idx] = decision
        for idx, decision in zip(
            gated,
            self.inner.decide_many(
                row_id=row_id,
                mlip_id=mlip_id,
                predictions=[predictions[idx] for idx in gated],
                support_model=None,
                contexts=[contexts[idx] for idx in gated],
            ),
            strict=True,
        ):
            decisions[idx] = self._annotate(decision, entries[idx])
        return [decision for decision in decisions if decision is not None]


class AutoPolicyEngine:
    def __init__(
        self,
        *,
        profile: str,
        atlas_distill_bin: str | os.PathLike[str] | None = None,
        ribbon_version: str = "hyperribbon-v1",
        policy_limits_path: str | os.PathLike[str] | None = None,
    ) -> None:
        self.rust = RustPolicyEngine(
            atlas_distill_bin=atlas_distill_bin,
            ribbon_version=ribbon_version,
            policy_limits_path=policy_limits_path,
        )
        self.python = PythonPolicyEngine(profile)

    @property
    def name(self) -> str:
        return "rust" if self.rust.available else "python_fallback"

    @staticmethod
    def _direction_gate_present(support_model: Any | None) -> bool:
        """Direction-gated corrections are implemented only by the Python
        engine; the Rust engine silently ignores the gated block (Codex
        PR#53 P1), so its presence must route around Rust."""
        evidence = support_evidence(support_model)
        if not isinstance(evidence, dict):
            return False
        correction = evidence.get("correction")
        return isinstance(correction, dict) and "direction_gated_correction_v1" in correction

    def decide(self, **kwargs: Any) -> DistillDecision:
        if self.rust.available and not self._direction_gate_present(kwargs.get("support_model")):
            return self.rust.decide(**kwargs)
        decision = self.python.decide(**kwargs)
        decision.policy_engine = "python_fallback"
        decision.raw.setdefault("route_reason", "direction_gate_python_engine")
        return decision

    def decide_many(self, **kwargs: Any) -> list[DistillDecision]:
        if self.rust.available and not self._direction_gate_present(kwargs.get("support_model")):
            return self.rust.decide_many(**kwargs)
        decisions = self.python.decide_many(**kwargs)
        for decision in decisions:
            decision.policy_engine = "python_fallback"
            decision.raw.setdefault("route_reason", "direction_gate_python_engine")
        return decisions


def support_evidence(support_model: Any | None) -> dict[str, Any] | None:
    if support_model is None:
        return None
    correction = (
        support_model.correction_evidence()
        if hasattr(support_model, "correction_evidence")
        else getattr(support_model, "correction", {})
    )
    diagnostics = getattr(support_model, "diagnostics", {})
    return {
        "correction": jsonable(correction),
        "diagnostics": jsonable(diagnostics),
    }


def build_policy_engine(
    name: str,
    *,
    profile: str,
    atlas_distill_bin: str | os.PathLike[str] | None = None,
    ribbon_version: str = "hyperribbon-v1",
    policy_limits_path: str | os.PathLike[str] | None = None,
    env_field_report_path: str | os.PathLike[str] | None = "auto",
) -> DistillPolicyEngine:
    """Build the requested engine, wrapped in the Lean certificate gate.

    ``env_field_report_path`` selects the env-field binding report backing
    the gate: the default ``"auto"`` requires the repo's validated report,
    an explicit path requires that report, and ``None`` is the only way to
    disable the gate.
    """
    engine: DistillPolicyEngine
    if name == "python":
        engine = PythonPolicyEngine(profile)
    elif name == "rust":
        engine = RustPolicyEngine(
            atlas_distill_bin=atlas_distill_bin,
            ribbon_version=ribbon_version,
            policy_limits_path=policy_limits_path,
        )
    elif name == "auto":
        engine = AutoPolicyEngine(
            profile=profile,
            atlas_distill_bin=atlas_distill_bin,
            ribbon_version=ribbon_version,
            policy_limits_path=policy_limits_path,
        )
    else:
        raise ValueError(f"unsupported distill policy engine: {name}")
    if env_field_report_path is not None:
        gate = CertificateGate.load(
            None if env_field_report_path == "auto" else env_field_report_path
        )
        engine = CertificateGatedPolicyEngine(engine, gate)
    return engine
