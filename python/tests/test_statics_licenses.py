"""Tests for the gate-license layer (lupine_distill.statics.licenses).

Synthetic registries only; no calculators load. Mirrors the registered
design docs/design/2026-07-13-gate-license-layer.md: statuses via the
|rho| >= 0.5 AND n >= 5 reference-bound rule, fail-closed descriptive
default, and the B0 license_ceiling override that caps positive licensing
without erasing an anti-correlated warning.
"""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path

import pytest

from lupine_distill.statics import InputValidationError
from lupine_distill.statics.licenses import (
    CORPUS_IN_SAMPLE,
    CORPUS_REFERENCE_BOUND,
    LICENSES_SCHEMA_ID,
    LICENSE_STATUSES,
    STATUS_ANTI_CORRELATED,
    STATUS_DESCRIPTIVE,
    STATUS_LICENSED,
    GateLicense,
    annotate_concordance,
    ceiling_for_property,
    derive_status,
    driving_license_summary,
    license_for,
    license_registry_block,
    load_license_registry,
    registry_program_note,
)

pytestmark = pytest.mark.unit


def _entry(
    status: str,
    rho: float | None,
    n: int,
    *,
    corpus_kind: str = CORPUS_REFERENCE_BOUND,
    caveats: list[str] | None = None,
) -> dict:
    return {
        "status": status,
        "rho": rho,
        "n": n,
        "corpus": "data/y_matrix_runs/bound",
        "corpus_kind": corpus_kind,
        "caveats": caveats or [],
    }


def _registry_payload() -> dict:
    return {
        "schema": LICENSES_SCHEMA_ID,
        "generated_at": "2026-07-13T00:00:00+00:00",
        "derived_from": {
            "path": "data/discovery_gates/dispersion_vs_error_by_class.json",
            "schema": "lupine.discovery_gates.dispersion_vs_error_by_class.v1",
            "generated_at": "2026-07-13T00:00:00+00:00",
        },
        "derivation_rule": {"n_min": 5},
        "program_overrides": [
            {
                "property": "b0",
                "license_ceiling": STATUS_DESCRIPTIVE,
                "provenance": "errata finding 4",
            }
        ],
        "by_class": {
            "metals-bcc": {
                "a0": _entry(STATUS_LICENSED, 0.893, 7),
                "b0": _entry(STATUS_DESCRIPTIVE, 0.321, 7),
            },
            "metals-fcc": {
                "a0": _entry(STATUS_DESCRIPTIVE, 0.067, 9),
                "B0": _entry(STATUS_ANTI_CORRELATED, -0.633, 9, caveats=["warn"]),
            },
            "perovskites": {
                "b0": _entry(
                    STATUS_DESCRIPTIVE, 1.0, 5, corpus_kind=CORPUS_IN_SAMPLE
                ),
            },
        },
    }


@pytest.fixture()
def registry_file(tmp_path: Path) -> Path:
    path = tmp_path / "licenses.v1.json"
    path.write_text(json.dumps(_registry_payload()), encoding="utf-8")
    return path


@pytest.fixture()
def registry(registry_file: Path):
    return load_license_registry(registry_file)


# --------------------------------------------------------------------------
# registered derivation rule
# --------------------------------------------------------------------------


class TestDeriveStatus:
    def test_licensed_at_rule_boundary(self) -> None:
        assert derive_status(0.5, 5, CORPUS_REFERENCE_BOUND) == STATUS_LICENSED

    def test_anti_correlated_at_rule_boundary(self) -> None:
        assert derive_status(-0.5, 5, CORPUS_REFERENCE_BOUND) == STATUS_ANTI_CORRELATED

    def test_weak_rho_is_descriptive(self) -> None:
        assert derive_status(0.49, 9, CORPUS_REFERENCE_BOUND) == STATUS_DESCRIPTIVE
        assert derive_status(-0.49, 9, CORPUS_REFERENCE_BOUND) == STATUS_DESCRIPTIVE

    def test_small_n_is_descriptive_even_at_perfect_rho(self) -> None:
        assert derive_status(1.0, 4, CORPUS_REFERENCE_BOUND) == STATUS_DESCRIPTIVE
        assert derive_status(-1.0, 4, CORPUS_REFERENCE_BOUND) == STATUS_DESCRIPTIVE

    def test_in_sample_corpus_confers_nothing(self) -> None:
        assert derive_status(1.0, 9, CORPUS_IN_SAMPLE) == STATUS_DESCRIPTIVE
        assert derive_status(-1.0, 9, CORPUS_IN_SAMPLE) == STATUS_DESCRIPTIVE

    def test_none_rho_is_descriptive(self) -> None:
        assert derive_status(None, 9, CORPUS_REFERENCE_BOUND) == STATUS_DESCRIPTIVE

    def test_nan_rho_is_descriptive(self) -> None:
        assert derive_status(float("nan"), 9, CORPUS_REFERENCE_BOUND) == (
            STATUS_DESCRIPTIVE
        )

    def test_ceiling_caps_positive_licensing_only(self) -> None:
        assert (
            derive_status(0.9, 9, CORPUS_REFERENCE_BOUND, ceiling=STATUS_DESCRIPTIVE)
            == STATUS_DESCRIPTIVE
        )
        # A ceiling can never erase the anti-correlated warning.
        assert (
            derive_status(-0.9, 9, CORPUS_REFERENCE_BOUND, ceiling=STATUS_DESCRIPTIVE)
            == STATUS_ANTI_CORRELATED
        )


class TestCeilingForProperty:
    def test_matches_property_case_insensitively(self) -> None:
        overrides = [{"property": "b0", "license_ceiling": STATUS_DESCRIPTIVE}]
        assert ceiling_for_property(overrides, "B0") == STATUS_DESCRIPTIVE
        assert ceiling_for_property(overrides, "a0") is None

    def test_unknown_ceiling_rejects(self) -> None:
        overrides = [{"property": "b0", "license_ceiling": "sometimes"}]
        with pytest.raises(InputValidationError, match="license_ceiling"):
            ceiling_for_property(overrides, "b0")


# --------------------------------------------------------------------------
# GateLicense record
# --------------------------------------------------------------------------


class TestGateLicense:
    def test_frozen(self) -> None:
        lic = GateLicense(
            class_name="metals-bcc",
            property_name="a0",
            status=STATUS_LICENSED,
            rho=0.9,
            n=7,
            corpus="bound",
            corpus_kind=CORPUS_REFERENCE_BOUND,
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            lic.status = STATUS_DESCRIPTIVE  # type: ignore[misc]

    def test_report_annotation_shape(self) -> None:
        lic = GateLicense(
            class_name="metals-fcc",
            property_name="b0",
            status=STATUS_ANTI_CORRELATED,
            rho=-0.633,
            n=9,
            corpus="bound",
            corpus_kind=CORPUS_REFERENCE_BOUND,
            caveats=("warn",),
        )
        annotation = lic.report_annotation("licenses.v1.json")
        assert annotation == {
            "status": STATUS_ANTI_CORRELATED,
            "rho": -0.633,
            "n": 9,
            "corpus": "bound",
            "corpus_kind": CORPUS_REFERENCE_BOUND,
            "source": "licenses.v1.json",
            "caveats": ["warn"],
        }


# --------------------------------------------------------------------------
# loading (fail-closed validation)
# --------------------------------------------------------------------------


class TestLoadLicenseRegistry:
    def test_loads_and_types_entries(self, registry, registry_file: Path) -> None:
        assert registry.path == registry_file.as_posix()
        assert registry.schema == LICENSES_SCHEMA_ID
        bcc_a0 = registry.licenses[("metals-bcc", "a0")]
        assert isinstance(bcc_a0, GateLicense)
        assert bcc_a0.status == STATUS_LICENSED
        assert bcc_a0.rho == pytest.approx(0.893)
        assert bcc_a0.n == 7
        assert registry_file.as_posix() in bcc_a0.registry

    def test_property_keys_lowercased(self, registry) -> None:
        # The payload spells fcc B0 uppercase; lookups are lowercase.
        assert ("metals-fcc", "b0") in registry.licenses
        assert ("metals-fcc", "B0") not in registry.licenses

    def test_missing_file_rejects(self, tmp_path: Path) -> None:
        with pytest.raises(InputValidationError, match="does not exist"):
            load_license_registry(tmp_path / "nope.json")

    def test_wrong_schema_rejects(self, tmp_path: Path) -> None:
        payload = _registry_payload()
        payload["schema"] = "lupine.something_else.v1"
        path = tmp_path / "bad.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        with pytest.raises(InputValidationError, match="schema"):
            load_license_registry(path)

    @pytest.mark.parametrize(
        ("field", "value", "match"),
        [
            ("status", "blessed", "unknown status"),
            ("rho", 1.5, "outside"),
            ("rho", "high", "rho"),
            ("n", -1, "non-negative"),
            ("n", True, "non-negative"),
            ("corpus_kind", "vibes", "corpus_kind"),
            ("caveats", "not-a-list", "caveats"),
        ],
    )
    def test_malformed_entry_rejects(
        self, tmp_path: Path, field: str, value: object, match: str
    ) -> None:
        payload = _registry_payload()
        payload["by_class"]["metals-bcc"]["a0"][field] = value
        path = tmp_path / "bad.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        with pytest.raises(InputValidationError, match=match):
            load_license_registry(path)

    def test_unearned_licensed_rejects(self, tmp_path: Path) -> None:
        payload = _registry_payload()
        payload["by_class"]["metals-bcc"]["a0"] = _entry(STATUS_LICENSED, 0.3, 7)
        path = tmp_path / "bad.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        with pytest.raises(InputValidationError, match="not supported"):
            load_license_registry(path)

    def test_licensed_through_ceiling_rejects(self, tmp_path: Path) -> None:
        # b0 carries a descriptive ceiling: even a strong rho cannot load
        # as licensed.
        payload = _registry_payload()
        payload["by_class"]["metals-bcc"]["b0"] = _entry(STATUS_LICENSED, 0.9, 7)
        path = tmp_path / "bad.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        with pytest.raises(InputValidationError, match="not supported"):
            load_license_registry(path)

    def test_registered_downgrade_loads(self, tmp_path: Path) -> None:
        # Downgrades are fail-safe: descriptive where the rule would allow
        # licensed must load fine.
        payload = _registry_payload()
        payload["by_class"]["metals-bcc"]["a0"] = _entry(STATUS_DESCRIPTIVE, 0.9, 7)
        path = tmp_path / "ok.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        registry = load_license_registry(path)
        assert registry.licenses[("metals-bcc", "a0")].status == STATUS_DESCRIPTIVE

    def test_override_without_property_rejects(self, tmp_path: Path) -> None:
        payload = _registry_payload()
        payload["program_overrides"] = [{"license_ceiling": STATUS_DESCRIPTIVE}]
        path = tmp_path / "bad.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        with pytest.raises(InputValidationError, match="property"):
            load_license_registry(path)


# --------------------------------------------------------------------------
# lookup (fail-closed default)
# --------------------------------------------------------------------------


class TestLicenseFor:
    def test_present_entry(self, registry) -> None:
        lic = license_for(registry, "metals-fcc", "b0")
        assert lic.status == STATUS_ANTI_CORRELATED

    def test_lookup_is_case_insensitive_on_property(self, registry) -> None:
        assert license_for(registry, "metals-fcc", "B0").status == (
            STATUS_ANTI_CORRELATED
        )

    def test_absent_entry_fails_closed(self, registry) -> None:
        lic = license_for(registry, "metals-fcc", "c44")
        assert lic.status == STATUS_DESCRIPTIVE
        assert lic.rho is None and lic.n == 0
        assert any("fail-closed" in caveat for caveat in lic.caveats)

    def test_absent_class_fails_closed(self, registry) -> None:
        assert license_for(registry, "ionics-rocksalt", "a0").status == (
            STATUS_DESCRIPTIVE
        )

    def test_absent_registry_fails_closed(self) -> None:
        lic = license_for(None, "metals-bcc", "a0")
        assert lic.status == STATUS_DESCRIPTIVE
        assert any("no license registry" in caveat for caveat in lic.caveats)


# --------------------------------------------------------------------------
# annotation (annotates, never re-gates, never mutates)
# --------------------------------------------------------------------------


def _gate(prop: str, level: str) -> dict:
    return {
        "gate": "concordance",
        "passed": level != "refuse",
        "values": {"property": prop, "dispersion": 0.01, "level": level},
        "criteria": {"flag_at": 0.05},
        "detail": "d",
        "wall_time_seconds": 0.0,
    }


class TestAnnotateConcordance:
    def test_attaches_license_and_preserves_verdict_fields(self, registry) -> None:
        gates = {"a0": _gate("a0", "pass"), "b0": _gate("b0", "flag")}
        annotated = annotate_concordance(gates, registry, "metals-fcc")
        assert annotated["a0"]["license"]["status"] == STATUS_DESCRIPTIVE
        assert annotated["b0"]["license"]["status"] == STATUS_ANTI_CORRELATED
        assert annotated["b0"]["license"]["rho"] == pytest.approx(-0.633)
        assert annotated["b0"]["license"]["source"] == registry.path
        # The verdict fields are untouched: a license never re-gates.
        assert annotated["b0"]["values"]["level"] == "flag"
        assert annotated["b0"]["passed"] is True

    def test_returns_new_dicts_without_mutating_input(self, registry) -> None:
        gates = {"b0": _gate("b0", "pass")}
        annotated = annotate_concordance(gates, registry, "metals-fcc")
        assert "license" not in gates["b0"]
        assert annotated["b0"] is not gates["b0"]

    def test_absent_registry_annotates_descriptive(self) -> None:
        gates = {"a0": _gate("a0", "pass")}
        annotated = annotate_concordance(gates, None, "metals-bcc")
        license_entry = annotated["a0"]["license"]
        assert license_entry["status"] == STATUS_DESCRIPTIVE
        assert license_entry["source"] is None

    def test_empty_gates_stay_empty(self, registry) -> None:
        assert annotate_concordance({}, registry, "metals-fcc") == {}


# --------------------------------------------------------------------------
# report wording helpers
# --------------------------------------------------------------------------


class TestDrivingLicenseSummary:
    def test_summarizes_flag_and_refuse_only(self, registry) -> None:
        gates = annotate_concordance(
            {
                "a0": _gate("a0", "pass"),
                "b0": _gate("b0", "flag"),
                "c44": _gate("c44", "refuse"),
            },
            registry,
            "metals-fcc",
        )
        summary = driving_license_summary(gates)
        assert "b0 - anti-correlated" in summary
        assert "must NOT be read as low error" in summary
        assert "c44 - descriptive" in summary
        assert "a0" not in summary

    def test_empty_when_nothing_drove_the_verdict(self, registry) -> None:
        gates = annotate_concordance(
            {"a0": _gate("a0", "pass")}, registry, "metals-fcc"
        )
        assert driving_license_summary(gates) == ""


class TestLicenseRegistryBlock:
    def test_loaded_block_pins_version(self, registry) -> None:
        block = license_registry_block(registry, None)
        assert block["loaded"] is True
        assert block["path"] == registry.path
        assert block["schema"] == LICENSES_SCHEMA_ID
        assert block["generated_at"] == registry.generated_at
        assert "path" in block["derived_from"]

    def test_absent_block_is_fail_closed(self, tmp_path: Path) -> None:
        block = license_registry_block(None, tmp_path / "missing.json")
        assert block["loaded"] is False
        assert "fail-closed" in block["note"]


class TestRegistryProgramNote:
    def test_generated_note_covers_override_anti_and_licensed(self, registry) -> None:
        note = registry_program_note(registry)
        assert "B0 concordance is capped at 'descriptive'" in note
        assert "metals-fcc b0" in note and "rho = -0.63" in note
        assert "metals-bcc a0 (rho = +0.89, n = 7)" in note
        assert "fail-closed" in note
        assert "Born stability" in note

    def test_statuses_enum_is_closed(self) -> None:
        assert LICENSE_STATUSES == (
            STATUS_LICENSED,
            STATUS_DESCRIPTIVE,
            STATUS_ANTI_CORRELATED,
        )
