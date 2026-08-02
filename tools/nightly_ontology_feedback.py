#!/usr/bin/env python3
"""Build fail-closed D1 updates for the nightly evidence/ontology feedback loop."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import statistics

import rfc8785
from datetime import date, datetime
from pathlib import Path
from typing import Any

HASH_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
ACCEPTANCE_PREDICATE_RE = re.compile(
    r"^(?P<metric>[a-z0-9_]+)_(?P<unit>mev|fraction)(?P<comparator><=|>)(?P<threshold>[0-9]+(?:\.[0-9]+)?)$"
)
PREDICATE_COMPARATORS = {"<=": "less_than_or_equal", ">": "greater_than"}
# Canonical auxiliary acceptance suite per predicate family: the exact frozen
# secondary measurements a receipt may carry. Must mirror the T1 demotion band
# in tools/lit_to_manifest.py (T1_MEDIAN_BAND_MEV). Auxiliary measurements
# outside the suite are rejected so permissive per-receipt thresholds cannot
# launder a falsified frozen prediction.
AUXILIARY_ACCEPTANCE_SUITES = {
    "signed_error_positive_fraction>0.5": {
        ("median_signed_error", "mev", "greater_than_or_equal", 400.0),
        ("median_signed_error", "mev", "less_than_or_equal", 600.0),
    }
}
READINESS_RANK = {"L": 0, "M": 1, "H": 2}


def _contract(value: Any) -> dict[str, Any]:
    if isinstance(value, str):
        value = json.loads(value)
    if not isinstance(value, dict):
        raise ValueError("literature hypothesis contract_json must be an object")
    return value


def _iso_date(value: str) -> date:
    if not isinstance(value, str):
        raise ValueError("as_of must be an ISO date")
    return date.fromisoformat(value)


def _timestamp_date(value: Any) -> date | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
    except ValueError:
        return None


def _measurement_outcome(comparator: Any, value: float, threshold: float) -> str | None:
    if comparator == "less_than_or_equal":
        return "pass" if value <= threshold else "fail"
    if comparator == "greater_than_or_equal":
        return "pass" if value >= threshold else "fail"
    if comparator == "greater_than":
        return "pass" if value > threshold else "fail"
    return None


def _acceptance_outcomes(bundle: dict[str, Any], as_of: date) -> list[str]:
    provenance = bundle.get("provenance")
    timestamp = provenance.get("timestamp") if isinstance(provenance, dict) else None
    measured_on = _timestamp_date(timestamp)
    if measured_on is None or measured_on > as_of:
        return []
    predicate = bundle.get("claim_predicate")
    predicate_match = (
        ACCEPTANCE_PREDICATE_RE.fullmatch(predicate)
        if isinstance(predicate, str)
        else None
    )
    outcomes: list[str] = []
    covered: set[tuple[Any, ...]] = set()
    for measurement in bundle.get("measurements", []):
        if not isinstance(measurement, dict):
            continue
        acceptance = measurement.get("acceptance_test")
        if not isinstance(acceptance, dict):
            continue
        value = measurement.get("value")
        threshold = acceptance.get("threshold")
        comparator = acceptance.get("comparator")
        asserted_outcome = acceptance.get("outcome")
        if (
            predicate_match is None
            or not isinstance(value, (int, float))
            or isinstance(value, bool)
            or not isinstance(threshold, (int, float))
            or isinstance(threshold, bool)
            or not math.isfinite(value)
            or not math.isfinite(threshold)
            or asserted_outcome not in {"pass", "fail"}
        ):
            raise ValueError("EvidenceBundle contains an invalid acceptance measurement")
        binds_predicate = (
            measurement.get("metric") == predicate_match.group("metric")
            and str(measurement.get("unit", "")).lower() == predicate_match.group("unit")
        )
        if binds_predicate:
            # The predicate-bound measurement is validated strictly against the
            # predicate it claims to satisfy.
            expected_comparator = PREDICATE_COMPARATORS[predicate_match.group("comparator")]
            if comparator != expected_comparator or float(threshold) != float(
                predicate_match.group("threshold")
            ):
                raise ValueError(
                    "EvidenceBundle acceptance threshold or metric disagrees with its bound predicate"
                )
        else:
            # Auxiliary typed measurements (e.g. a frozen median band) must be
            # part of the predicate family's canonical frozen acceptance suite;
            # arbitrary per-receipt thresholds are rejected.
            suite = AUXILIARY_ACCEPTANCE_SUITES.get(predicate, set())
            aux_key = (
                measurement.get("metric"),
                str(measurement.get("unit", "")).lower(),
                comparator,
                float(threshold),
            )
            if aux_key not in suite:
                raise ValueError(
                    "EvidenceBundle auxiliary measurement is outside the frozen acceptance suite"
                )
        measured_outcome = _measurement_outcome(comparator, value, threshold)
        if measured_outcome is None:
            raise ValueError("EvidenceBundle contains an invalid acceptance measurement")
        if asserted_outcome != measured_outcome:
            raise ValueError(
                "EvidenceBundle asserted acceptance outcome disagrees with its measured value"
            )
        outcomes.append(measured_outcome)
        covered.add(
            (
                measurement.get("metric"),
                str(measurement.get("unit", "")).lower(),
                comparator,
                float(threshold),
            )
        )
    if predicate in AUXILIARY_ACCEPTANCE_SUITES and outcomes:
        # The frozen acceptance suite is conjunctive: the predicate-bound
        # measurement plus every canonical auxiliary bound must be present, so
        # an omitted failing bound cannot count as a pass.
        required = set(AUXILIARY_ACCEPTANCE_SUITES[predicate])
        required.add(
            (
                predicate_match.group("metric"),
                predicate_match.group("unit"),
                PREDICATE_COMPARATORS[predicate_match.group("comparator")],
                float(predicate_match.group("threshold")),
            )
        )
        if covered < required:
            raise ValueError(
                "EvidenceBundle carries an incomplete acceptance suite for its bound predicate"
            )
    return outcomes


_REPO_ROOT = Path(__file__).resolve().parents[1]


def _artifact_rows(path: Path) -> list[dict] | None:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    rows = (document.get("per_row") or document.get("per_path")) if isinstance(document, dict) else None
    if not isinstance(rows, list) or not rows:
        return None
    return rows


def _fingerprint_from_rows(rows: list[dict]) -> str | None:
    observations = []
    seen: set[tuple[str, str]] = set()
    for row in rows:
        if not isinstance(row, dict):
            return None
        identity = row.get("path_id")
        model = row.get("model")
        status = row.get("status")
        if not isinstance(identity, str) or not isinstance(model, str):
            return None
        if (identity, model) in seen:
            return None
        seen.add((identity, model))
        if status == "measured":
            value = row.get("signed_error_mev")
            if (
                not isinstance(value, (int, float))
                or isinstance(value, bool)
                or not math.isfinite(value)
            ):
                return None
            observations.append([identity, model, "measured", round(float(value), 4)])
        elif status != "failed":
            return None
    observations.sort()
    canonical = json.dumps(observations, separators=(",", ":")).encode()
    return "sha256:" + hashlib.sha256(canonical).hexdigest()


def _artifact_fingerprint(path: Path) -> str | None:
    """Recompute a sign-skew dataset fingerprint from a cited artifact's rows."""
    rows = _artifact_rows(path)
    if rows is None:
        return None
    return _fingerprint_from_rows(rows)


def _artifact_path_statistics(rows: list[dict]) -> tuple[int, float, float] | None:
    per_path: dict[str, list[float]] = {}
    for row in rows:
        if not isinstance(row, dict) or row.get("status") != "measured":
            continue
        value = row.get("signed_error_mev")
        identity = row.get("path_id")
        if (
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and isinstance(identity, str)
        ):
            per_path.setdefault(identity, []).append(float(value))
    if not per_path:
        return None
    path_values = [statistics.median(values) for values in per_path.values()]
    fraction = sum(1 for value in path_values if value > 0) / len(path_values)
    return len(per_path), fraction, statistics.median(path_values)


def _receipt_matches_artifact(bundle: dict[str, Any], rows: list[dict]) -> bool:
    """Ingestion-grade reconciliation of typed measurements with artifact rows."""
    stats = _artifact_path_statistics(rows)
    if stats is None:
        return False
    measured_paths, fraction, median = stats
    for measurement in bundle.get("measurements", []):
        if not isinstance(measurement, dict):
            return False
        metric = measurement.get("metric")
        value = measurement.get("value")
        if (
            not isinstance(value, (int, float))
            or isinstance(value, bool)
            or not math.isfinite(value)
        ):
            return False
        if metric == "signed_error_positive" and abs(float(value) - fraction) > 5e-5:
            return False
        if metric == "median_signed_error" and abs(float(value) - median) > 0.01:
            return False
        if measurement.get("sample_count") != measured_paths:
            return False
    return True


SIGN_SKEW_PATH_FLOOR = 22

CANONICAL_RECORDED_SOURCE = "data/candidates/z1-union-campaign.json"
CANONICAL_SOURCE_FINGERPRINT = (
    "sha256:b9137ff7830c50cfdc59ec837ef2bb099326657c5d5e2d2ae158143360653989"
)


def _canonical_measured_observations() -> set[tuple[str, str, float]] | None:
    try:
        source = json.loads((_REPO_ROOT / CANONICAL_RECORDED_SOURCE).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    observations: set[tuple[str, str, float]] = set()
    for entry in source.get("per_path", []):
        if not isinstance(entry, dict):
            continue
        identity = entry.get("path_id")
        for model, record in (entry.get("per_model") or {}).items():
            value = record.get("vasp_signed_error_mev") if isinstance(record, dict) else None
            if (
                value is not None
                and record.get("complete", False)
                and isinstance(value, (int, float))
                and not isinstance(value, bool)
                and math.isfinite(value)
            ):
                observations.add((identity, model, round(float(value), 4)))
    return observations

# The sign-skew family's canonical model identities. Model ids are caller-controlled
# strings, so authentication binds the full (id, artifact hash, version) triple;
# a consistently renamed clone cannot keep these.
CANONICAL_MODEL_ENTRIES = {
    ("chgnet", "sha256:27dbc19f3fa710bbb58b6f5e64e0fde5a6941edcb538f92d228b2d90e93f8890", "chgnet 0.4.2"),
    ("mace-mp-small", "sha256:c69cbc43286d05a8e9974412a4fb5f4e28405f92ac15287537263475dfc3c694", "mace-torch 0.3.16 / small"),
    ("mace-mp-medium", "sha256:1d80b5c4898b2d22d73dc82b17e1cabe1111d9cd6be4c2a7403dea6fa0ac83f3", "mace-torch 0.3.16 / medium"),
    ("mace-mpa-0-medium", "sha256:59b5d1db18664525ad20358fe381b7ba71bdb260c8a3d6bbfe5fb5201e3be0d9", "mace-torch 0.3.16 / mpa-0 medium"),
}


def _locked_source_rows(
    manifest: dict[str, Any], row_label: str
) -> tuple[dict[tuple[str, str], tuple[str, float | None]], dict[int, str]] | None:
    """Load the manifest's locked recorded input as expectations and identities."""
    preregistration = manifest.get("preregistration")
    recorded_inputs = (
        preregistration.get("recorded_inputs")
        if isinstance(preregistration, dict)
        else None
    )
    if not isinstance(recorded_inputs, list) or len(recorded_inputs) != 1:
        return None
    declared = recorded_inputs[0]
    if not isinstance(declared, dict) or not isinstance(declared.get("path"), str):
        return None
    source_path = _REPO_ROOT / declared["path"]
    try:
        if "sha256:" + hashlib.sha256(source_path.read_bytes()).hexdigest() != declared.get("sha256"):
            return None
        source = json.loads(source_path.read_text(encoding="utf-8"))
    except OSError:
        return None
    except json.JSONDecodeError:
        return None
    expected: dict[tuple[str, str], tuple[str, float | None]] = {}
    identities: dict[int, str] = {}
    chemistries: dict[int, str] = {}
    seen_identities: set[str] = set()
    for position, entry in enumerate(source.get("per_path", [])):
        if not isinstance(entry, dict) or not isinstance(entry.get("path_id"), str):
            continue
        identity = entry["path_id"]
        index = entry.get("path_index", position)
        if not isinstance(index, int) or index in identities or identity in seen_identities:
            return None
        seen_identities.add(identity)
        identities[index] = identity
        if isinstance(entry.get("chemical_system"), str):
            chemistries[index] = entry["chemical_system"]
        for model, record in (entry.get("per_model") or {}).items():
            value = record.get("vasp_signed_error_mev") if isinstance(record, dict) else None
            if (
                value is not None
                and record.get("complete", False)
                and isinstance(value, (int, float))
                and not isinstance(value, bool)
                and math.isfinite(value)
            ):
                expected[(identity, model)] = ("measured", float(value))
        for model in (entry.get("models_missing") or {}):
            expected[(identity, model)] = ("failed", None)
    return expected, identities, chemistries


PREDICATE_MANIFEST_OPERATORS = {"<=": "lte", ">": "gt"}


def _authenticate_sign_skew(bundle: dict[str, Any], reference: dict[str, Any]) -> bool:
    """Ingestion-grade authentication of one sign-skew dataset reference."""
    fingerprint = reference.get("dataset_fingerprint")
    artifact = reference.get("artifact")
    if not (
        isinstance(fingerprint, str)
        and HASH_RE.fullmatch(fingerprint)
        and isinstance(artifact, str)
    ):
        return False
    rows = _artifact_rows(_REPO_ROOT / artifact)
    if rows is None or _fingerprint_from_rows(rows) != fingerprint:
        return False
    try:
        artifact_digest = "sha256:" + hashlib.sha256((_REPO_ROOT / artifact).read_bytes()).hexdigest()
    except OSError:
        return False
    if reference.get("artifact_hash") != artifact_digest:
        return False
    stats = _artifact_path_statistics(rows)
    if stats is None or stats[0] < SIGN_SKEW_PATH_FLOOR:
        return False
    manifest_rel = reference.get("campaign_manifest")
    if not isinstance(manifest_rel, str):
        return False
    manifest_path = _REPO_ROOT / manifest_rel
    try:
        manifest_bytes = manifest_path.read_bytes()
        manifest = json.loads(manifest_bytes.decode("utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return False
    if reference.get("campaign_manifest_hash") != (
        "sha256:" + hashlib.sha256(manifest_bytes).hexdigest()
    ):
        return False
    if reference.get("campaign") != manifest.get("campaign_id"):
        return False
    try:
        registry = json.loads((_REPO_ROOT / "registry" / "campaigns.v1.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    unhashed = {key: value for key, value in manifest.items() if key != "content_hash"}
    recomputed = "sha256:" + hashlib.sha256(rfc8785.dumps(unhashed)).hexdigest()
    if manifest.get("content_hash") != recomputed:
        return False
    campaign_id = manifest.get("campaign_id")
    if not any(
        isinstance(entry, dict)
        and entry.get("campaign_id") == campaign_id
        and entry.get("content_hash") == recomputed
        for entry in registry.get("campaigns", [])
    ):
        return False
    predicate = bundle.get("claim_predicate")
    predicate_match = (
        ACCEPTANCE_PREDICATE_RE.fullmatch(predicate) if isinstance(predicate, str) else None
    )
    acceptance = manifest.get("acceptance_test")
    if (
        predicate_match is None
        or not isinstance(acceptance, dict)
        or acceptance.get("metric") != predicate_match.group("metric")
        or acceptance.get("operator") != PREDICATE_MANIFEST_OPERATORS[predicate_match.group("comparator")]
        or float(acceptance.get("threshold", -1)) != float(predicate_match.group("threshold"))
        or str(acceptance.get("unit", "")).lower() != predicate_match.group("unit")
    ):
        return False
    canonical_measured = _canonical_measured_observations()
    if canonical_measured is None:
        return False
    if any(
        isinstance(row, dict)
        and row.get("status") == "measured"
        and not (isinstance(row.get("chemical_system"), str) and row.get("chemical_system", "").strip())
        for row in rows
    ):
        return False
    artifact_pairs = {
        (row.get("chemical_system"), row.get("model"))
        for row in rows
        if isinstance(row, dict)
        and row.get("status") == "measured"
        and isinstance(row.get("chemical_system"), str)
        and isinstance(row.get("model"), str)
    }
    # The overlap guard rejects borrowed evidence only for noncanonical
    # datasets; the canonical receipt necessarily shares its own observations.
    if fingerprint != CANONICAL_SOURCE_FINGERPRINT:
        used_pairs = set()
        try:
            canonical_source = json.loads((_REPO_ROOT / CANONICAL_RECORDED_SOURCE).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return False
        for entry in canonical_source.get("per_path", []):
            if not isinstance(entry, dict) or not isinstance(entry.get("chemical_system"), str):
                continue
            for model, record in (entry.get("per_model") or {}).items():
                value = record.get("vasp_signed_error_mev") if isinstance(record, dict) else None
                if value is not None and record.get("complete", False):
                    used_pairs.add((entry["chemical_system"], model))
        examples_dir = _REPO_ROOT / "evidence" / "v1" / "examples"
        if examples_dir.is_dir():
            for prior_path in sorted(examples_dir.glob("*.json")):
                try:
                    prior = json.loads(prior_path.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    continue
                if not isinstance(prior.get("claim_predicate"), str) or not prior[
                    "claim_predicate"
                ].startswith("signed_error_positive_fraction"):
                    continue
                for reference in prior.get("evidence_refs", []):
                    if not isinstance(reference, dict):
                        continue
                    if reference.get("campaign") == campaign_id:
                        continue
                    if reference.get("dataset_fingerprint") == fingerprint:
                        continue
                    prior_artifact = reference.get("artifact")
                    if isinstance(prior_artifact, str):
                        prior_rows = _artifact_rows(_REPO_ROOT / prior_artifact)
                        if prior_rows:
                            for prior_row in prior_rows:
                                if (
                                    isinstance(prior_row, dict)
                                    and prior_row.get("status") == "measured"
                                    and isinstance(prior_row.get("path_id"), str)
                                    and isinstance(prior_row.get("model"), str)
                                ):
                                    if isinstance(prior_row.get("chemical_system"), str):
                                        used_pairs.add((prior_row["chemical_system"], prior_row["model"]))
        if artifact_pairs & used_pairs:
            return False
    locked_result = _locked_source_rows(manifest, "receipt")
    if locked_result is None:
        return False
    expected, locked_identities, locked_chemistries = locked_result
    panel_lock = (
        manifest.get("execution", {}).get("candidate_panel")
        if isinstance(manifest.get("execution"), dict)
        else None
    )
    if not isinstance(panel_lock, dict) or not isinstance(panel_lock.get("path"), str):
        return False
    panel_path = _REPO_ROOT / panel_lock["path"]
    try:
        if "sha256:" + hashlib.sha256(panel_path.read_bytes()).hexdigest() != panel_lock.get("sha256"):
            return False
        panel = json.loads(panel_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    panel_rows = panel.get("per_path") or panel.get("paths") or []
    panel_identities = {}
    panel_chemistries = {}
    for position, entry in enumerate(panel_rows):
        if isinstance(entry, dict):
            key = entry.get("path_index", position)
            if isinstance(key, int):
                panel_identities[key] = entry.get("path_id")
                panel_chemistries[key] = entry.get("chemical_system")
    source_chemistries: dict[int, str] = {}
    preregistration = manifest.get("preregistration")
    recorded_inputs = (
        preregistration.get("recorded_inputs")
        if isinstance(preregistration, dict)
        else None
    )
    source_for_chemistry = None
    if isinstance(recorded_inputs, list) and recorded_inputs:
        try:
            source_for_chemistry = json.loads(
                (_REPO_ROOT / recorded_inputs[0]["path"]).read_text(encoding="utf-8")
            )
        except (OSError, json.JSONDecodeError, KeyError):
            source_for_chemistry = None
    if isinstance(source_for_chemistry, dict):
        for position, entry in enumerate(source_for_chemistry.get("per_path", [])):
            if isinstance(entry, dict):
                key = entry.get("path_index", position)
                if isinstance(key, int) and isinstance(entry.get("chemical_system"), str):
                    source_chemistries[key] = entry["chemical_system"]
    if any(panel_identities.get(index) != identity for index, identity in locked_identities.items()):
        return False
    if any(
        panel_chemistries.get(index) != source_chemistries.get(index)
        for index in locked_identities
    ):
        return False
    required_models = {
        model.get("model_id")
        for model in manifest.get("available_models", [])
        if isinstance(model, dict)
    }
    required_models.discard(None)
    declared_entries = {
        (model.get("model_id"), model.get("artifact_hash"), model.get("version"))
        for model in manifest.get("available_models", [])
        if isinstance(model, dict)
    }
    if declared_entries != CANONICAL_MODEL_ENTRIES:
        return False
    if required_models:
        pairs = {
            (row.get("path_id"), row.get("model"))
            for row in rows
            if isinstance(row, dict)
            and isinstance(row.get("path_id"), str)
            and isinstance(row.get("model"), str)
        }
        models_in_rows = {model for _, model in pairs}
        if any(model not in required_models for model in models_in_rows):
            return False
        paths = {path for path, _ in pairs}
        if any(
            (path, model) not in pairs
            for path in paths
            for model in required_models
        ):
            return False
    row_by_pair = {
        (row.get("path_id"), row.get("model")): row
        for row in rows
        if isinstance(row, dict)
    }
    if set(row_by_pair) != set(expected):
        return False
    for key, (status, value) in expected.items():
        row = row_by_pair.get(key)
        if row is None or row.get("status") != status:
            return False
        identity_index = next(
            (index for index, identity in locked_identities.items() if identity == key[0]),
            None,
        )
        if identity_index is not None and row.get("chemical_system") != locked_chemistries.get(identity_index):
            return False
        if status == "measured" and (
            not isinstance(row.get("signed_error_mev"), (int, float))
            or round(row["signed_error_mev"], 4) != round(value, 4)
        ):
            return False
    return _receipt_matches_artifact(bundle, rows)


def _confirms_instead(bundle: dict[str, Any], as_of: date) -> bool:
    """True when a self-labeled negative receipt's typed suite actually passes."""
    measurements = bundle.get("measurements")
    if not isinstance(measurements, list) or not measurements:
        return False
    outcomes = _acceptance_outcomes(bundle, as_of)
    return bool(outcomes) and all(outcome == "pass" for outcome in outcomes)


def _falsifies_consistently(bundle: dict[str, Any], as_of: date) -> bool:
    """A negative sign-skew receipt must reconcile with an artifact whose suite fails.

    Untyped dated refutation receipts remain supported; typed receipts must
    authenticate against their artifact and carry a genuinely failing outcome.
    """
    measurements = bundle.get("measurements")
    if not isinstance(measurements, list) or not measurements:
        return True
    if _confirms_instead(bundle, as_of):
        return False
    predicate = bundle.get("claim_predicate")
    if not isinstance(predicate, str) or not predicate.startswith(
        "signed_error_positive_fraction"
    ):
        return True
    outcomes = _acceptance_outcomes(bundle, as_of)
    if not outcomes or not any(outcome == "fail" for outcome in outcomes):
        return False
    # A typed negative must pass the full ingestion-grade authenticator: floor,
    # model coverage, campaign manifest, locked-source binding, and reconciled
    # statistics — falsification may not come from an invented artifact either.
    return any(
        isinstance(reference, dict) and _authenticate_sign_skew(bundle, reference)
        for reference in bundle.get("evidence_refs", [])
    )


def _chain_claim(chain: str, assumptions: list[dict[str, Any]]) -> dict[str, Any] | None:
    number = chain.removeprefix("C")
    marker = f".z{number}."
    discovery_prefix = f"discovery.z{number}."
    discovery_matches = [
        row
        for row in assumptions
        if str(row.get("claim_id", "")).startswith(discovery_prefix)
    ]
    matches = discovery_matches or [
        row for row in assumptions if marker in str(row.get("claim_id", ""))
    ]
    if len(matches) > 1:
        raise ValueError(f"multiple assumption claims bind {chain}")
    return matches[0] if matches else None


def _chain_state(
    chain: str,
    assumptions: list[dict[str, Any]],
    evidence_by_id: dict[str, dict[str, Any]],
    as_of: date,
    expected_predicate: str,
) -> dict[str, Any]:
    assumption = _chain_claim(chain, assumptions)
    if assumption is None:
        return {"grade": "L", "refuted": False, "bundle_ids": [], "passing": []}
    bundle_ids = [
        str(item["bundle_id"])
        for item in assumption.get("evidence", [])
        if isinstance(item, dict)
        and "bundle_id" in item
        and HASH_RE.fullmatch(str(item["bundle_id"]))
    ]
    missing = [bundle_id for bundle_id in bundle_ids if bundle_id not in evidence_by_id]
    if missing:
        raise ValueError(f"assumption for {chain} references missing EvidenceBundle {missing[0]}")
    defined = []
    passing = []
    campaigns: set[str] = set()
    for bundle_id in bundle_ids:
        bundle = evidence_by_id[bundle_id]
        provenance = bundle.get("provenance")
        measured_on = _timestamp_date(
            provenance.get("timestamp") if isinstance(provenance, dict) else None
        )
        if (
            assumption.get("disposition") == "refuted"
            and bundle.get("epistemic_status") == "negative"
            and measured_on is not None
            and measured_on <= as_of
        ):
            # Refutation receipts need dated provenance but need not use an
            # acceptance measurement schema. Their role is supersession, not
            # readiness promotion.
            defined.append(bundle_id)
        outcomes = _acceptance_outcomes(bundle, as_of)
        if not outcomes:
            continue
        if bundle_id not in defined:
            defined.append(bundle_id)
        family_authenticated: bool | None = None
        if expected_predicate.startswith("signed_error_positive_fraction"):
            family_authenticated = any(
                isinstance(reference, dict)
                and _authenticate_sign_skew(bundle, reference)
                for reference in bundle.get("evidence_refs", [])
            )
        if (
            bundle.get("claim_predicate") == expected_predicate
            and bundle.get("epistemic_status") == "confirmatory"
            and all(outcome == "pass" for outcome in outcomes)
            and family_authenticated is not False
        ):
            passing.append(bundle_id)
            counted_identity = False
            for reference in bundle.get("evidence_refs", []):
                if not isinstance(reference, dict):
                    continue
                if expected_predicate.startswith("signed_error_positive_fraction"):
                    # Independence is the dataset, not the campaign name: count
                    # at most one authenticated fingerprint per evaluated bundle.
                    if not counted_identity and _authenticate_sign_skew(bundle, reference):
                        campaigns.add(("dataset", reference["dataset_fingerprint"]))
                        counted_identity = True
                elif isinstance(reference.get("campaign"), str):
                    campaigns.add(reference["campaign"])
    grade = "H" if len(campaigns) >= 2 else "M" if passing else "L"
    return {
        "grade": grade,
        "refuted": assumption.get("disposition") == "refuted",
        "bundle_ids": defined,
        "passing": passing,
    }


def build_feedback_plan(
    *,
    atlas: dict[str, Any],
    assumptions: dict[str, Any],
    evidence_by_id: dict[str, dict[str, Any]],
    hypotheses: list[dict[str, Any]],
    new_bundle_ids: set[str],
    as_of: str,
) -> dict[str, Any]:
    """Plan monotonic readiness/status transitions and the priority-ordered queue."""
    cycle_date = _iso_date(as_of)
    chains = atlas.get("discoveryChains")
    acceptance = atlas.get("acceptanceTests")
    assumption_rows = assumptions.get("assumptions")
    if not isinstance(chains, list) or not isinstance(acceptance, list) or not isinstance(assumption_rows, list):
        raise ValueError("atlas and assumptions have invalid collections")
    priority = {row["id"]: index for index, row in enumerate(chains, 1)}
    acceptance_to_chain = {row["id"]: row["chain"] for row in acceptance}
    missing_new_bundles = sorted(new_bundle_ids - evidence_by_id.keys())
    if missing_new_bundles:
        raise ValueError(
            f"new EvidenceBundle is missing from the evidence directory: {missing_new_bundles[0]}"
        )

    updates: list[dict[str, Any]] = []
    queue: list[dict[str, Any]] = []


    for row in sorted(hypotheses, key=lambda item: item["literature_hypothesis_id"]):
        hypothesis_id = row["literature_hypothesis_id"]
        contract = _contract(row["contract_json"])
        bound_chains = contract.get("bindings", {}).get("chains", [])
        bound_acceptance = contract.get("bindings", {}).get("acceptanceTests", [])
        if not bound_chains or any(chain not in priority for chain in bound_chains):
            raise ValueError(f"{hypothesis_id} has invalid chain bindings")
        if any(acceptance_to_chain.get(test) not in bound_chains for test in bound_acceptance):
            raise ValueError(f"{hypothesis_id} acceptance tests do not match chain bindings")

        proposed_experiment = contract.get("proposedExperiment")
        expected_predicate = (
            proposed_experiment.get("predicate")
            if isinstance(proposed_experiment, dict)
            else None
        )
        if not isinstance(expected_predicate, str) or not ACCEPTANCE_PREDICATE_RE.fullmatch(
            expected_predicate
        ):
            raise ValueError(f"{hypothesis_id} has an invalid acceptance predicate")
        states = [
            _chain_state(
                chain,
                assumption_rows,
                evidence_by_id,
                cycle_date,
                expected_predicate,
            )
            for chain in bound_chains
        ]
        old_status = contract["status"]
        old_readiness = contract["readiness"]
        old_grade = old_readiness[0]
        new_status = old_status
        new_readiness = old_readiness
        authorization: str | None = None

        negative_new = sorted(
            bundle_id
            for state in states
            if state["refuted"]
            for bundle_id in state["bundle_ids"]
            if bundle_id in new_bundle_ids
            and evidence_by_id[bundle_id].get("epistemic_status") == "negative"
            # Supersession requires negative evidence on the hypothesis's own
            # predicate; a failure on a shared premise's other predicate must
            # not reject it.
            and evidence_by_id[bundle_id].get("claim_predicate") == expected_predicate
            # A mislabeled receipt whose typed suite actually passes is a
            # confirmation, not a refutation; a typed negative must reconcile
            # with an artifact whose suite genuinely fails.
            and _falsifies_consistently(evidence_by_id[bundle_id], cycle_date)
        )
        if old_status not in {"rejected", "superseded"} and negative_new:
            new_status = "superseded"
            authorization = negative_new[-1]
        elif old_status not in {"rejected", "superseded"}:
            target_grade = min(
                (state["grade"] for state in states),
                key=lambda grade: READINESS_RANK[grade],
            )
            passing_new = sorted(
                bundle_id
                for state in states
                for bundle_id in state["passing"]
                if bundle_id in new_bundle_ids
            )
            if READINESS_RANK[target_grade] > READINESS_RANK[old_grade] and passing_new:
                new_readiness = target_grade
                authorization = passing_new[-1]

        if authorization is not None:
            changed = json.loads(json.dumps(contract))
            changed["status"] = new_status
            changed["readiness"] = new_readiness
            updates.append(
                {
                    "hypothesis_id": hypothesis_id,
                    "from_status": old_status,
                    "to_status": new_status,
                    "from_readiness": old_readiness,
                    "to_readiness": new_readiness,
                    "evidence_bundle_id": authorization,
                    "contract_json": changed,
                }
            )
        effective_status = new_status
        if effective_status not in {"rejected", "superseded"}:
            for chain, state in zip(bound_chains, states, strict=True):
                if state["grade"] == "H":
                    continue
                queue.append(
                    {
                        "hypothesis_id": hypothesis_id,
                        "chain_id": chain,
                        "chain_priority": priority[chain],
                        "query": contract["claim_text"][:240],
                        "reason": f"{chain} has {state['grade']} readiness; fresh independent acceptance evidence is missing",
                        "evidence_gap": {
                            "current_readiness": state["grade"],
                            "required_readiness": "H",
                            "acceptance_tests": [
                                test for test in bound_acceptance if acceptance_to_chain.get(test) == chain
                            ],
                        },
                    }
                )
    queue.sort(key=lambda item: (item["chain_priority"], item["hypothesis_id"], item["chain_id"]))
    digest_lines = [f"# Hermes nightly ontology digest — {as_of}", ""]
    digest_lines.append(f"Status/readiness updates: {len(updates)}")
    for update in updates:
        digest_lines.append(
            f"- {update['hypothesis_id']}: {update['from_status']}/{update['from_readiness']} → "
            f"{update['to_status']}/{update['to_readiness']} ({update['evidence_bundle_id']})"
        )
    digest_lines.extend(["", f"Literature queue: {len(queue)}"])
    for item in queue:
        digest_lines.append(
            f"- P{item['chain_priority']} {item['chain_id']} · {item['hypothesis_id']}: {item['reason']}"
        )
    return {
        "as_of": as_of,
        "updates": updates,
        "queue": queue,
        "evidence": [evidence_by_id[key] for key in sorted(new_bundle_ids)],
        "digest_markdown": "\n".join(digest_lines) + "\n",
    }


def _sql(value: Any) -> str:
    if value is None:
        return "NULL"
    return "'" + str(value).replace("'", "''") + "'"


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def _topologically_order_evidence(bundles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Order bundles so every superseded predecessor inserts before its
    replacement (Codex P2 on PR #92: hash-order could insert a replacement
    before the row it supersedes)."""
    by_id = {b["bundle_id"]: b for b in bundles}
    ordered: list[dict[str, Any]] = []
    placed: set[str] = set()
    remaining = dict(by_id)
    while remaining:
        progressed = False
        for bundle_id in sorted(remaining):
            predecessors = [p for p in (remaining[bundle_id].get("supersedes") or []) if p in by_id]
            if all(p in placed for p in predecessors):
                ordered.append(remaining.pop(bundle_id))
                placed.add(bundle_id)
                progressed = True
        if not progressed:
            # Cycle or self-reference: fail closed with a deterministic order
            # rather than silently emitting a broken chain.
            ordered.extend(remaining.pop(k) for k in sorted(remaining))
    return ordered


def render_feedback_sql(plan: dict[str, Any]) -> str:
    """Render one atomic, reviewable D1 script from a feedback plan."""
    statements = ["-- Generated by tools/nightly_ontology_feedback.py", "BEGIN TRANSACTION;"]
    for bundle in _topologically_order_evidence(plan.get("evidence", [])):
        supersedes = sorted(set(bundle.get("supersedes") or []))
        statements.append(
            "INSERT INTO evidence_bundle (bundle_id, claim_predicate, epistemic_status, scope_json, provenance_json, supersedes_bundle_id, supersedes_bundle_ids_json) "
            f"VALUES ({_sql(bundle['bundle_id'])}, {_sql(bundle['claim_predicate'])}, {_sql(bundle['epistemic_status'])}, "
            f"{_sql(_canonical(bundle['scope']))}, {_sql(_canonical(bundle['provenance']))}, "
            f"{_sql(supersedes[0] if supersedes else None)}, {_sql(json.dumps(supersedes, ensure_ascii=False))}) "
            "ON CONFLICT(bundle_id) DO NOTHING;"
        )
    for update in plan.get("updates", []):
        metadata = {
            "from_readiness": update["from_readiness"],
            "to_readiness": update["to_readiness"],
            "producer": "lupine.nightly-ontology-feedback.v1",
        }
        event_seed = "|".join(
            [plan["as_of"], update["hypothesis_id"], update["evidence_bundle_id"], update["to_status"], update["to_readiness"]]
        )
        event_id = "nightly." + hashlib.sha256(event_seed.encode()).hexdigest()
        statements.append(
            "INSERT INTO status_event (status_event_id, entity_type, entity_id, from_status, to_status, evidence_bundle_id, occurred_at, actor, metadata_json) "
            f"VALUES ({_sql(event_id)}, 'literature_hypothesis', {_sql(update['hypothesis_id'])}, {_sql(update['from_status'])}, "
            f"{_sql(update['to_status'])}, {_sql(update['evidence_bundle_id'])}, {_sql(plan['as_of'] + 'T08:00:00Z')}, "
            f"'evidence-nightly', {_sql(_canonical(metadata))});"
        )
        statements.append(
            "UPDATE literature_hypotheses SET contract_json = "
            f"{_sql(_canonical(update['contract_json']))}, updated_at = {_sql(plan['as_of'] + 'T08:00:00Z')} "
            f"WHERE literature_hypothesis_id = {_sql(update['hypothesis_id'])};"
        )
    statements.append(
        f"DELETE FROM literature_reprioritization_queue WHERE cycle_date = {_sql(plan['as_of'])};"
    )
    for item in plan.get("queue", []):
        statements.append(
            "INSERT INTO literature_reprioritization_queue "
            "(cycle_date, literature_hypothesis_id, chain_id, chain_priority, query, reason, evidence_gap_json) "
            f"VALUES ({_sql(plan['as_of'])}, {_sql(item['hypothesis_id'])}, {_sql(item['chain_id'])}, "
            f"{item['chain_priority']}, {_sql(item['query'])}, {_sql(item['reason'])}, {_sql(_canonical(item['evidence_gap']))});"
        )
    statements.append("COMMIT;")
    return "\n\n".join(statements) + "\n"


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _hypothesis_rows(payload: Any) -> list[dict[str, Any]]:
    """Accept a plain export or Wrangler's JSON result envelope."""
    if (
        isinstance(payload, list)
        and payload
        and isinstance(payload[0], dict)
        and "results" in payload[0]
    ):
        payload = payload[0]["results"]
    if not isinstance(payload, list) or any(not isinstance(row, dict) for row in payload):
        raise ValueError("hypotheses export must be a JSON row array")
    return payload


def _known_bundle_ids(payload: Any) -> set[str]:
    """Read known D1 bundle hashes from a plain list or Wrangler envelope."""
    if (
        isinstance(payload, list)
        and payload
        and isinstance(payload[0], dict)
        and "results" in payload[0]
    ):
        payload = payload[0]["results"]
    if not isinstance(payload, list):
        raise ValueError("known EvidenceBundle export must be a JSON array")
    ids = set()
    for row in payload:
        value = row.get("bundle_id") if isinstance(row, dict) else row
        if not isinstance(value, str) or not HASH_RE.fullmatch(value):
            raise ValueError("known EvidenceBundle export contains an invalid bundle_id")
        ids.add(value)
    return ids


def _sync_candidate_bundle_ids(payload: Any) -> set[str]:
    """Read current or legacy nightly runner output."""
    if isinstance(payload, dict):
        payload = payload.get(
            "sync_candidate_bundle_ids", payload.get("ingested_bundle_ids")
        )
    if not isinstance(payload, list):
        raise ValueError("sync candidate EvidenceBundle export must be a JSON array")
    ids = set(payload)
    if len(ids) != len(payload) or any(
        not isinstance(value, str) or not HASH_RE.fullmatch(value) for value in payload
    ):
        raise ValueError("sync candidate EvidenceBundle export contains an invalid bundle_id")
    return ids


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--atlas", type=Path, required=True)
    parser.add_argument("--assumptions", type=Path, required=True)
    parser.add_argument("--evidence-dir", type=Path, required=True)
    parser.add_argument("--hypotheses", type=Path, required=True)
    parser.add_argument("--new-bundle-ids", type=Path, required=True)
    parser.add_argument("--known-bundle-ids", type=Path, required=True)
    parser.add_argument("--as-of", required=True)
    parser.add_argument("--out-sql", type=Path, required=True)
    parser.add_argument("--out-queue", type=Path, required=True)
    parser.add_argument("--out-digest", type=Path, required=True)
    parser.add_argument("--out-card", type=Path, required=True)
    args = parser.parse_args()
    evidence = {
        document["bundle_id"]: document
        for path in sorted(args.evidence_dir.glob("*.json"))
        for document in [_load(path)]
    }
    sync_candidate_ids = _sync_candidate_bundle_ids(_load(args.new_bundle_ids))
    new_ids = sync_candidate_ids - _known_bundle_ids(_load(args.known_bundle_ids))
    plan = build_feedback_plan(
        atlas=_load(args.atlas),
        assumptions=_load(args.assumptions),
        evidence_by_id=evidence,
        hypotheses=_hypothesis_rows(_load(args.hypotheses)),
        new_bundle_ids=new_ids,
        as_of=args.as_of,
    )
    for path in (args.out_sql, args.out_queue, args.out_digest, args.out_card):
        path.parent.mkdir(parents=True, exist_ok=True)
    args.out_sql.write_text(render_feedback_sql(plan), encoding="utf-8")
    args.out_queue.write_text(json.dumps(plan["queue"], indent=2) + "\n", encoding="utf-8")
    args.out_digest.write_text(plan["digest_markdown"], encoding="utf-8")
    args.out_card.write_text(
        json.dumps(
            {
                "schema": "hermes.digest-card.v1",
                "title": f"Ontology feedback digest — {args.as_of}",
                "body": plan["digest_markdown"],
                "assignee": "researcher",
                "priority": 18,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"updates": len(plan["updates"]), "queue": len(plan["queue"])}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
