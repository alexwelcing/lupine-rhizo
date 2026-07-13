"""Gate-license layer: what a concordance zone means epistemically.

Companion to :mod:`lupine_distill.statics.gates` (registered design:
``docs/design/2026-07-13-gate-license-layer.md``). The 2026-07-13
adversarial review (errata findings 4 and 6) established that a concordance
verdict does not automatically carry uncertainty content: fcc B0 dispersion
is ANTI-correlated with |error| (Spearman rho = -0.63, n = 9), and the
perovskite rho = 1.0 was computed on the very candidates the gate then
judged. The license registry (``licenses.v1.json``) turns that knowledge
into structured, versioned data; this module loads it and annotates
concordance gate dicts with it.

Honesty rules:

* A license ANNOTATES; it never re-gates. Concordance levels, verdicts and
  thresholds are untouched (v1 of this layer).
* Loading is fail-closed: a ``(class, property)`` absent from the registry
  -- or an absent registry -- yields ``descriptive``: the concordance level
  is arithmetic about model agreement ONLY, with no error claim.
* ``licensed`` / ``anti-correlated`` require rho >= +0.5 / rho <= -0.5 AND
  n >= 5 AND a reference-bound corpus. A program ``license_ceiling``
  override caps positive licensing only; it can never erase an
  ``anti-correlated`` warning.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Final, Mapping, Sequence

from lupine_distill.statics.errors import InputValidationError

LICENSES_SCHEMA_ID: Final[str] = "lupine.discovery_gates.licenses.v1"

STATUS_LICENSED: Final[str] = "licensed"
STATUS_DESCRIPTIVE: Final[str] = "descriptive"
STATUS_ANTI_CORRELATED: Final[str] = "anti-correlated"
LICENSE_STATUSES: Final[tuple[str, ...]] = (
    STATUS_LICENSED,
    STATUS_DESCRIPTIVE,
    STATUS_ANTI_CORRELATED,
)

CORPUS_REFERENCE_BOUND: Final[str] = "reference-bound"
CORPUS_IN_SAMPLE: Final[str] = "in-sample"
CORPUS_KINDS: Final[tuple[str, ...]] = (CORPUS_REFERENCE_BOUND, CORPUS_IN_SAMPLE)

#: Registered derivation-rule constants (gate-license design, section 2).
LICENSED_MIN_RHO: Final[float] = 0.5
ANTI_CORRELATED_MAX_RHO: Final[float] = -0.5
#: Deliberately matches ``gates._MIN_THRESHOLD_SAMPLES``: below five samples
#: neither a threshold nor a license is a distribution statement.
LICENSE_MIN_SAMPLES: Final[int] = 5

#: What each status means in a report (verdict wording discipline).
STATUS_MEANINGS: Final[Mapping[str, str]] = MappingProxyType(
    {
        STATUS_LICENSED: (
            "low dispersion may be read as empirically lower error, within "
            "the recorded rho/n"
        ),
        STATUS_DESCRIPTIVE: "agreement arithmetic only, no uncertainty claim",
        STATUS_ANTI_CORRELATED: "low dispersion must NOT be read as low error",
    }
)


@dataclass(frozen=True)
class GateLicense:
    """Empirical license of one (class, property) concordance channel."""

    class_name: str
    property_name: str
    status: str
    rho: float | None
    n: int
    corpus: str
    corpus_kind: str
    caveats: tuple[str, ...] = ()
    registry: str = ""

    def report_annotation(self, source: str | None) -> dict[str, object]:
        """The ``license`` sub-object attached to a concordance gate entry."""
        return {
            "status": self.status,
            "rho": self.rho,
            "n": self.n,
            "corpus": self.corpus or None,
            "corpus_kind": self.corpus_kind or None,
            "source": source,
            "caveats": list(self.caveats),
        }


@dataclass(frozen=True)
class LicenseRegistry:
    """One loaded, validated licenses.v1 registry file (immutable)."""

    path: str
    schema: str
    generated_at: str
    derived_from: Mapping[str, object]
    derivation_rule: Mapping[str, object]
    program_overrides: tuple[Mapping[str, object], ...]
    licenses: Mapping[tuple[str, str], GateLicense]

    def __post_init__(self) -> None:
        object.__setattr__(self, "derived_from", MappingProxyType(dict(self.derived_from)))
        object.__setattr__(
            self, "derivation_rule", MappingProxyType(dict(self.derivation_rule))
        )
        object.__setattr__(
            self,
            "program_overrides",
            tuple(MappingProxyType(dict(o)) for o in self.program_overrides),
        )
        object.__setattr__(self, "licenses", MappingProxyType(dict(self.licenses)))

    @property
    def provenance(self) -> str:
        return f"{self.path} (schema {self.schema}, generated_at {self.generated_at})"


def ceiling_for_property(
    program_overrides: Sequence[Mapping[str, object]], property_name: str
) -> str | None:
    """The ``license_ceiling`` a program override imposes on a property, if any."""
    prop = property_name.lower()
    for override in program_overrides:
        if str(override.get("property", "")).lower() != prop:
            continue
        ceiling = str(override.get("license_ceiling", ""))
        if ceiling not in LICENSE_STATUSES:
            raise InputValidationError(
                f"program override for {prop!r} has unknown license_ceiling "
                f"{ceiling!r}; known statuses: {', '.join(LICENSE_STATUSES)}"
            )
        return ceiling
    return None


def derive_status(
    rho: float | None,
    n: int,
    corpus_kind: str,
    *,
    ceiling: str | None = None,
) -> str:
    """Registered derivation rule: rho/n/corpus -> license status.

    ``licensed`` needs rho >= +0.5, n >= 5, a reference-bound corpus, and no
    program ceiling; ``anti-correlated`` needs rho <= -0.5, n >= 5, and a
    reference-bound corpus (a ceiling caps positive licensing only, so it
    never suppresses the warning); everything else is ``descriptive`` --
    the fail-closed default.
    """
    if (
        rho is not None
        and math.isfinite(float(rho))
        and n >= LICENSE_MIN_SAMPLES
        and corpus_kind == CORPUS_REFERENCE_BOUND
    ):
        if float(rho) <= ANTI_CORRELATED_MAX_RHO:
            return STATUS_ANTI_CORRELATED
        if float(rho) >= LICENSED_MIN_RHO and ceiling is None:
            return STATUS_LICENSED
    return STATUS_DESCRIPTIVE


def _validated_entry(
    class_name: str,
    prop: str,
    entry: object,
    *,
    ceiling: str | None,
    provenance: str,
    source: str,
) -> GateLicense:
    where = f"{source}: by_class[{class_name!r}][{prop!r}]"
    if not isinstance(entry, Mapping):
        raise InputValidationError(f"{where} must be an object, got {entry!r}")
    status = str(entry.get("status", ""))
    if status not in LICENSE_STATUSES:
        raise InputValidationError(
            f"{where}: unknown status {status!r}; known: {', '.join(LICENSE_STATUSES)}"
        )
    rho_raw = entry.get("rho")
    rho: float | None
    if rho_raw is None:
        rho = None
    else:
        try:
            rho = float(rho_raw)
        except (TypeError, ValueError) as exc:
            raise InputValidationError(f"{where}: rho must be a number or null") from exc
        if not math.isfinite(rho) or not -1.0 <= rho <= 1.0:
            raise InputValidationError(f"{where}: rho {rho!r} outside [-1, 1]")
    n_raw = entry.get("n")
    if not isinstance(n_raw, int) or isinstance(n_raw, bool) or n_raw < 0:
        raise InputValidationError(
            f"{where}: n must be a non-negative integer, got {n_raw!r}"
        )
    corpus_kind = str(entry.get("corpus_kind", ""))
    if corpus_kind not in CORPUS_KINDS:
        raise InputValidationError(
            f"{where}: unknown corpus_kind {corpus_kind!r}; known: "
            f"{', '.join(CORPUS_KINDS)}"
        )
    # Fail-closed integrity: a registry may DOWNGRADE (descriptive and
    # anti-correlated are fail-safe), but an unearned 'licensed' rejects.
    if status == STATUS_LICENSED and derive_status(
        rho, n_raw, corpus_kind, ceiling=ceiling
    ) != STATUS_LICENSED:
        raise InputValidationError(
            f"{where}: status 'licensed' is not supported by the registered "
            f"rule (rho={rho!r}, n={n_raw}, corpus_kind={corpus_kind!r}, "
            f"ceiling={ceiling!r})"
        )
    caveats_raw = entry.get("caveats", [])
    if not isinstance(caveats_raw, Sequence) or isinstance(caveats_raw, str):
        raise InputValidationError(f"{where}: caveats must be a list of strings")
    return GateLicense(
        class_name=class_name,
        property_name=prop,
        status=status,
        rho=rho,
        n=n_raw,
        corpus=str(entry.get("corpus", "")),
        corpus_kind=corpus_kind,
        caveats=tuple(str(c) for c in caveats_raw),
        registry=provenance,
    )


def load_license_registry(path: str | Path) -> LicenseRegistry:
    """Load and validate a ``licenses.v1`` registry file (fail-closed).

    Schema id, status enum, rho range [-1, 1], n, corpus_kind and program
    overrides are all validated; any violation rejects the whole file.
    """
    path = Path(path)
    if not path.is_file():
        raise InputValidationError(f"license registry does not exist: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise InputValidationError(f"cannot read license registry {path}: {exc}") from exc
    if not isinstance(payload, Mapping) or payload.get("schema") != LICENSES_SCHEMA_ID:
        raise InputValidationError(
            f"{path}: expected schema {LICENSES_SCHEMA_ID!r}, got "
            f"{payload.get('schema') if isinstance(payload, Mapping) else payload!r}"
        )
    generated_at = str(payload.get("generated_at", ""))
    if not generated_at:
        raise InputValidationError(f"{path}: missing generated_at")
    derived_from = payload.get("derived_from", {})
    if not isinstance(derived_from, Mapping):
        raise InputValidationError(f"{path}: derived_from must be an object")
    derivation_rule = payload.get("derivation_rule", {})
    if not isinstance(derivation_rule, Mapping):
        raise InputValidationError(f"{path}: derivation_rule must be an object")
    overrides_raw = payload.get("program_overrides", [])
    if not isinstance(overrides_raw, Sequence) or isinstance(overrides_raw, str):
        raise InputValidationError(f"{path}: program_overrides must be a list")
    overrides: list[Mapping[str, object]] = []
    for override in overrides_raw:
        if not isinstance(override, Mapping) or not str(override.get("property", "")):
            raise InputValidationError(
                f"{path}: every program override needs a 'property'"
            )
        ceiling_for_property([override], str(override["property"]))  # validates ceiling
        overrides.append(dict(override))
    by_class = payload.get("by_class")
    if not isinstance(by_class, Mapping):
        raise InputValidationError(f"{path}: expected a 'by_class' mapping")
    provenance = f"{path.as_posix()} (schema {LICENSES_SCHEMA_ID}, generated_at {generated_at})"
    licenses: dict[tuple[str, str], GateLicense] = {}
    for class_name, per_prop in by_class.items():
        if not isinstance(per_prop, Mapping):
            raise InputValidationError(
                f"{path}: by_class[{class_name!r}] must be an object"
            )
        for prop_raw, entry in per_prop.items():
            prop = str(prop_raw).lower()
            licenses[(str(class_name), prop)] = _validated_entry(
                str(class_name),
                prop,
                entry,
                ceiling=ceiling_for_property(overrides, prop),
                provenance=provenance,
                source=path.as_posix(),
            )
    return LicenseRegistry(
        path=path.as_posix(),
        schema=LICENSES_SCHEMA_ID,
        generated_at=generated_at,
        derived_from=derived_from,
        derivation_rule=derivation_rule,
        program_overrides=tuple(overrides),
        licenses=licenses,
    )


def license_for(
    registry: LicenseRegistry | None, class_name: str, property_name: str
) -> GateLicense:
    """The license of one (class, property); fail-closed ``descriptive`` default."""
    prop = str(property_name).lower()
    if registry is not None:
        found = registry.licenses.get((str(class_name), prop))
        if found is not None:
            return found
    reason = (
        "no license entry for this (class, property)"
        if registry is not None
        else "no license registry loaded"
    )
    return GateLicense(
        class_name=str(class_name),
        property_name=prop,
        status=STATUS_DESCRIPTIVE,
        rho=None,
        n=0,
        corpus="",
        corpus_kind="",
        caveats=(f"{reason}; descriptive is the fail-closed default",),
        registry=registry.provenance if registry is not None else "",
    )


def annotate_concordance(
    gates: Mapping[str, Mapping[str, object]],
    registry: LicenseRegistry | None,
    class_name: str,
) -> dict[str, dict[str, object]]:
    """New concordance gates dict with a ``license`` sub-object per property.

    Returns new dicts (verdict fields are copied, never mutated); the
    concordance level and passed flag are untouched -- a license annotates,
    it never re-gates.
    """
    source = registry.path if registry is not None else None
    annotated: dict[str, dict[str, object]] = {}
    for prop, gate in gates.items():
        entry = dict(gate)
        entry["license"] = license_for(registry, class_name, prop).report_annotation(source)
        annotated[str(prop)] = entry
    return annotated


def license_registry_block(
    registry: LicenseRegistry | None, path: str | Path | None
) -> dict[str, object]:
    """Top-level report block pinning the registry version a report used."""
    if registry is None:
        return {
            "path": Path(path).as_posix() if path is not None else None,
            "loaded": False,
            "note": (
                "license registry absent: every concordance license defaults "
                "to descriptive (fail-closed); concordance levels are "
                "agreement arithmetic only, carrying no dispersion-error claim"
            ),
        }
    return {
        "path": registry.path,
        "loaded": True,
        "schema": registry.schema,
        "generated_at": registry.generated_at,
        "derived_from": dict(registry.derived_from),
    }


def _license_phrase(license_entry: Mapping[str, object]) -> str:
    status = str(license_entry.get("status", STATUS_DESCRIPTIVE))
    meaning = STATUS_MEANINGS.get(status, STATUS_MEANINGS[STATUS_DESCRIPTIVE])
    rho = license_entry.get("rho")
    n = license_entry.get("n")
    if status != STATUS_DESCRIPTIVE and isinstance(rho, (int, float)):
        return f"{meaning} (rho={float(rho):+.2f}, n={n})"
    return meaning


def driving_license_summary(
    concordance_gates: Mapping[str, Mapping[str, object]],
    *,
    levels: tuple[str, ...] = ("flag", "refuse"),
) -> str:
    """License summary for the properties that drove a verdict.

    E.g. ``"b0 - descriptive: agreement arithmetic only, no uncertainty
    claim"`` for every property whose concordance level is in ``levels``;
    empty string when none did.
    """
    parts: list[str] = []
    for prop, gate in concordance_gates.items():
        values = gate.get("values")
        level = values.get("level") if isinstance(values, Mapping) else None
        if level not in levels:
            continue
        license_entry = gate.get("license")
        if not isinstance(license_entry, Mapping):
            continue
        parts.append(
            f"{prop} - {license_entry.get('status')}: {_license_phrase(license_entry)}"
        )
    return "; ".join(parts)


def registry_program_note(registry: LicenseRegistry) -> str:
    """Program-wide license note GENERATED from the registry entries.

    Replaces hard-coded prose (the old ``B0_CONCORDANCE_DESCRIPTIVE_NOTE``)
    in reports whenever a registry is loaded.
    """
    sentences: list[str] = []
    for override in registry.program_overrides:
        sentences.append(
            f"{str(override.get('property', '?')).upper()} concordance is capped at "
            f"'{override.get('license_ceiling')}' program-wide "
            f"({override.get('provenance', 'registered override')})"
        )
    anti = sorted(
        (lic for lic in registry.licenses.values() if lic.status == STATUS_ANTI_CORRELATED),
        key=lambda lic: (lic.class_name, lic.property_name),
    )
    for lic in anti:
        sentences.append(
            f"{lic.class_name} {lic.property_name} dispersion is ANTI-correlated "
            f"with |error| (rho = {lic.rho:+.2f}, n = {lic.n}): "
            f"{STATUS_MEANINGS[STATUS_ANTI_CORRELATED]}"
        )
    licensed = sorted(
        (lic for lic in registry.licenses.values() if lic.status == STATUS_LICENSED),
        key=lambda lic: (lic.class_name, lic.property_name),
    )
    if licensed:
        channels = ", ".join(
            f"{lic.class_name} {lic.property_name} (rho = {lic.rho:+.2f}, n = {lic.n})"
            for lic in licensed
        )
        sentences.append(
            f"only Born stability (exact physics, needs no license) and "
            f"{channels} carry a dispersion-error license"
        )
    else:
        sentences.append(
            "only Born stability (exact physics, needs no license) carries "
            "any uncertainty content"
        )
    sentences.append(
        "every other (class, property) concordance is descriptive "
        "(fail-closed): agreement arithmetic only, no error claim"
    )
    return f"License registry {registry.provenance}: " + "; ".join(sentences) + "."


__all__ = [
    "ANTI_CORRELATED_MAX_RHO",
    "CORPUS_IN_SAMPLE",
    "CORPUS_KINDS",
    "CORPUS_REFERENCE_BOUND",
    "GateLicense",
    "LICENSED_MIN_RHO",
    "LICENSES_SCHEMA_ID",
    "LICENSE_MIN_SAMPLES",
    "LICENSE_STATUSES",
    "LicenseRegistry",
    "STATUS_ANTI_CORRELATED",
    "STATUS_DESCRIPTIVE",
    "STATUS_LICENSED",
    "STATUS_MEANINGS",
    "annotate_concordance",
    "ceiling_for_property",
    "derive_status",
    "driving_license_summary",
    "license_for",
    "license_registry_block",
    "load_license_registry",
    "registry_program_note",
]
