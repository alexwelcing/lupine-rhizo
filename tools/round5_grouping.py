#!/usr/bin/env python3
"""Derive the prospectively frozen Round-5 grouping keys.

This tool reads candidate metadata only. It never reads model measurements,
correction outcomes, or materialized Round-5 results.
"""

from __future__ import annotations

import argparse
import json
import math
from functools import reduce
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_VOCABULARY = ROOT / "data/contracts/round5-grouping-vocabulary.v1.json"


class GroupingRefusalError(ValueError):
    """Fail-closed candidate grouping refusal with a stable machine code."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


def load_vocabulary(path: Path = DEFAULT_VOCABULARY) -> dict[str, Any]:
    vocabulary = json.loads(path.read_text(encoding="utf-8"))
    if vocabulary.get("schema") != "lupine.round5.grouping-vocabulary.v1":
        raise GroupingRefusalError("REFUSE_VOCABULARY_SCHEMA", str(path))
    symbols = vocabulary["element_vocabulary"]["symbols_by_atomic_number"]
    if len(symbols) != 118 or len(set(symbols)) != 118:
        raise GroupingRefusalError("REFUSE_VOCABULARY_CARDINALITY", str(path))
    return vocabulary


def _positive_integer_composition(candidate: dict[str, Any]) -> dict[str, int]:
    composition = candidate.get("elemental_composition")
    if not isinstance(composition, dict) or not composition:
        raise GroupingRefusalError("REFUSE_EMPTY_COMPOSITION", "elemental_composition")

    normalized: dict[str, int] = {}
    for symbol, count in composition.items():
        if not isinstance(symbol, str) or not symbol:
            raise GroupingRefusalError("REFUSE_NON_ELEMENTAL_SPECIES", repr(symbol))
        if isinstance(count, bool) or not isinstance(count, int):
            raise GroupingRefusalError("REFUSE_NON_INTEGER_STOICHIOMETRY", symbol)
        if count <= 0:
            raise GroupingRefusalError("REFUSE_NON_POSITIVE_STOICHIOMETRY", symbol)
        normalized[symbol] = count

    divisor = reduce(math.gcd, normalized.values())
    return {symbol: count // divisor for symbol, count in normalized.items()}


def derive_groupings(
    candidate: dict[str, Any],
    vocabulary: dict[str, Any] | None = None,
) -> dict[str, str]:
    """Return all four v3 grouping keys or raise a stable refusal."""
    vocabulary = vocabulary or load_vocabulary()

    material_class = candidate.get("class")
    allowed_classes = vocabulary["class_vocabulary"]["allowed"]
    if not isinstance(material_class, str) or material_class not in allowed_classes:
        raise GroupingRefusalError("REFUSE_CLASS_VOCABULARY", repr(material_class))

    prototype = candidate.get("structure_prototype")
    allowed_prototypes = vocabulary["prototype_vocabulary"]["allowed_by_class"][material_class]
    if not isinstance(prototype, str) or prototype not in allowed_prototypes:
        raise GroupingRefusalError(
            "REFUSE_CLASS_PROTOTYPE_MISMATCH",
            f"{material_class!r}/{prototype!r}",
        )

    composition = _positive_integer_composition(candidate)
    symbols = vocabulary["element_vocabulary"]["symbols_by_atomic_number"]
    atomic_number = {symbol: index for index, symbol in enumerate(symbols, start=1)}
    unknown = sorted(set(composition) - set(atomic_number))
    if unknown:
        raise GroupingRefusalError("REFUSE_UNKNOWN_ELEMENT", ",".join(unknown))

    ordered_symbols = sorted(composition, key=atomic_number.__getitem__)
    chemistry = "-".join(ordered_symbols)

    band_width = vocabulary["composition_space_neighbourhood_derivation"][
        "atomic_number_band_width"
    ]
    band_labels = vocabulary["composition_space_neighbourhood_derivation"]["bands"]
    band_counts: dict[int, int] = {}
    for symbol, count in composition.items():
        band_index = (atomic_number[symbol] - 1) // band_width
        band_counts[band_index] = band_counts.get(band_index, 0) + count
    band_divisor = reduce(math.gcd, band_counts.values())
    terms = [
        f"{band_labels[index]}={band_counts[index] // band_divisor}"
        for index in sorted(band_counts)
    ]
    neighbourhood = "csn-zband10-v1:" + ",".join(terms)

    return {
        "class": material_class,
        "chemistry": chemistry,
        "structure_prototype": prototype,
        "composition_space_neighbourhood": neighbourhood,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidate", type=Path, help="candidate JSON object or array")
    parser.add_argument("--vocabulary", type=Path, default=DEFAULT_VOCABULARY)
    args = parser.parse_args()

    vocabulary = load_vocabulary(args.vocabulary)
    payload = json.loads(args.candidate.read_text(encoding="utf-8"))
    candidates = payload if isinstance(payload, list) else [payload]
    if not candidates or not all(isinstance(item, dict) for item in candidates):
        raise GroupingRefusalError("REFUSE_CANDIDATE_CONTAINER", str(args.candidate))

    derived = [derive_groupings(item, vocabulary) for item in candidates]
    output: Any = derived if isinstance(payload, list) else derived[0]
    print(json.dumps(output, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
