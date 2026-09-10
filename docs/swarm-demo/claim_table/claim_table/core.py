"""Headline extraction from the TMS 2027 proceedings canonical results object.

The canonical object separates:

``derived``
    Numbers recomputed from committed source rows (denominator funnel, geometry
    summary, Lean theorem count).
``quoted``
    Numbers copied verbatim from frozen reports, each entry carrying its
    ``source`` binding key so provenance is explicit.

A *headline value* is:

- under ``derived``: any scalar leaf reachable by recursion (compact scalar
  mappings such as ``tensors_by_element`` decompose to one row per element);
- under ``quoted``: exactly each entry's ``value`` field, bound at
  ``quoted.<name>.value`` — the sibling ``source``/``note`` fields are
  provenance metadata, not headline values, and a quoted entry without a
  ``value`` key is a hard error.

Per-record arrays such as ``derived.geometry.per_group`` are record-level
detail rather than headline values and are skipped. Binding keys are dotted
paths from the section root (e.g. ``quoted.layer2_raw_mae_gpa.value``), and
rows are ordered lexicographically by binding key, so rendered output is
byte-for-byte deterministic regardless of JSON key insertion order.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator

SCHEMA = "lupine.tms2027.proceedings.results.v1"
REQUIRED_KEYS = ("schema", "derived", "quoted")
ROOT_SECTIONS = ("derived", "quoted")

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_DATA = 3


class ClaimTableError(Exception):
    """Base error for malformed results objects."""


class MissingKeyError(ClaimTableError):
    """A required top-level key is absent from the results object."""


class SchemaMismatchError(ClaimTableError):
    """The results object declares a different schema than this tool supports."""


@dataclass(frozen=True)
class HeadlineRow:
    """One headline value bound to its dotted key inside the results object."""

    binding_key: str
    value: Any

    @property
    def rendered(self) -> str:
        text = json.dumps(self.value)
        return text.replace("|", "\\|").replace("\n", " ")


def load_results(path: str | Path) -> dict[str, Any]:
    """Load and validate a canonical results JSON file."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ClaimTableError(f"results object must be a JSON object, got {type(data).__name__}")
    for key in REQUIRED_KEYS:
        if key not in data:
            raise MissingKeyError(f"results object is missing required key {key!r}")
    if data["schema"] != SCHEMA:
        raise SchemaMismatchError(
            f"unsupported schema {data['schema']!r}; expected {SCHEMA!r}"
        )
    for section in ROOT_SECTIONS:
        if not isinstance(data[section], dict):
            raise ClaimTableError(f"section {section!r} must be an object")
    return data


def _is_scalar(value: Any) -> bool:
    return value is None or isinstance(value, (bool, int, float, str))


def _is_scalar_pair_list(value: list[Any]) -> bool:
    """True for [[a, b], [c, d], ...] with scalar entries (e.g. z3 holdout arms)."""
    return bool(value) and all(
        isinstance(item, list) and item and all(_is_scalar(x) for x in item) for item in value
    )


def _iter_leaves(node: Any, prefix: str) -> Iterator[tuple[str, Any]]:
    if _is_scalar(node):
        yield prefix, node
    elif isinstance(node, list):
        if not node or all(_is_scalar(x) for x in node) or _is_scalar_pair_list(node):
            yield prefix, node
        # else: per-record array (list of objects) — record detail, not a headline.
    elif isinstance(node, dict):
        for key in sorted(node):
            yield from _iter_leaves(node[key], f"{prefix}.{key}")


def _iter_quoted(quoted: dict[str, Any]) -> Iterator[tuple[str, Any]]:
    for name, entry in sorted(quoted.items()):
        if not isinstance(entry, dict) or "value" not in entry:
            raise MissingKeyError(
                f"quoted entry {name!r} must be an object with a 'value' key"
            )
        yield f"quoted.{name}.value", entry["value"]


def build_rows(results: dict[str, Any]) -> list[HeadlineRow]:
    """Collect every headline row from ``derived`` and ``quoted`` in binding-key order."""
    rows = [
        HeadlineRow(binding_key=key, value=value)
        for section, iterator in (
            ("derived", _iter_leaves(results["derived"], "derived")),
            ("quoted", _iter_quoted(results["quoted"])),
        )
        for key, value in iterator
    ]
    rows.sort(key=lambda row: row.binding_key)
    return rows


def render_markdown(results: dict[str, Any]) -> str:
    """Render the two-column headline table (value, binding key) as markdown."""
    lines = ["| Value | Binding key |", "|---|---|"]
    lines += [f"| {row.rendered} | `{row.binding_key}` |" for row in build_rows(results)]
    return "\n".join(lines)
