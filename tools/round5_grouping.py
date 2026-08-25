#!/usr/bin/env python3
"""Derive the prospectively frozen Round-5 grouping keys."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from collections import defaultdict
from functools import reduce
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_VOCABULARY = ROOT / "data/contracts/round5-grouping-vocabulary.v1.json"
DEFAULT_VOCABULARY_SHA256 = "80686eacc5a5e14bc516389c707d49305ff82db13e8d2cd71ea180f963f35adc"
DEFAULT_SPLIT_SEED = "round5-grouping-heldout-20260825-v4"
ALLOWED_RULES = (
    "class",
    "chemistry",
    "structure_prototype",
    "composition_space_neighbourhood",
)


class GroupingRefusalError(ValueError):
    """Fail-closed candidate grouping refusal with a stable machine code."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


def load_vocabulary(path: Path = DEFAULT_VOCABULARY) -> dict[str, Any]:
    if path.resolve() != DEFAULT_VOCABULARY.resolve():
        raise GroupingRefusalError("REFUSE_VOCABULARY_PATH", str(path))
    raw = path.read_bytes()
    actual_sha256 = hashlib.sha256(raw).hexdigest()
    if actual_sha256 != DEFAULT_VOCABULARY_SHA256:
        raise GroupingRefusalError("REFUSE_VOCABULARY_DIGEST", actual_sha256)
    vocabulary = json.loads(raw)
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
        if (
            not isinstance(symbol, str)
            or not re.fullmatch(r"[A-Z][a-z]?", symbol)
            or symbol in {"D", "T"}
        ):
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
    """Return all four v4 grouping keys or raise a stable refusal."""
    forbidden = {
        "chemistry",
        "composition_space_neighbourhood",
    }.intersection(candidate)
    if forbidden:
        raise GroupingRefusalError(
            "REFUSE_PRECOMPUTED_GROUPING_VALUE", ",".join(sorted(forbidden))
        )
    vocabulary = vocabulary or load_vocabulary()
    material_class = candidate.get("class")
    allowed_classes = vocabulary["class_vocabulary"]["allowed"]
    if not isinstance(material_class, str) or material_class not in allowed_classes:
        raise GroupingRefusalError("REFUSE_CLASS_VOCABULARY", repr(material_class))
    prototype = candidate.get("structure_prototype")
    allowed_prototypes = vocabulary["prototype_vocabulary"]["allowed_by_class"][material_class]
    if not isinstance(prototype, str) or prototype not in allowed_prototypes:
        raise GroupingRefusalError(
            "REFUSE_CLASS_PROTOTYPE_MISMATCH", f"{material_class!r}/{prototype!r}"
        )
    composition = _positive_integer_composition(candidate)
    symbols = vocabulary["element_vocabulary"]["symbols_by_atomic_number"]
    atomic_number = {symbol: index for index, symbol in enumerate(symbols, start=1)}
    unknown = sorted(set(composition) - set(atomic_number))
    if unknown:
        raise GroupingRefusalError("REFUSE_UNKNOWN_ELEMENT", ",".join(unknown))
    ordered_symbols = sorted(composition, key=atomic_number.__getitem__)
    chemistry = "-".join(ordered_symbols)
    contract = vocabulary["composition_space_neighbourhood_derivation"]
    band_width = contract["atomic_number_band_width"]
    band_labels = contract["bands"]
    band_counts: dict[int, int] = {}
    for symbol, count in composition.items():
        band_index = (atomic_number[symbol] - 1) // band_width
        band_counts[band_index] = band_counts.get(band_index, 0) + count
    band_divisor = reduce(math.gcd, band_counts.values())
    terms = [
        f"{band_labels[index]}={band_counts[index] // band_divisor}"
        for index in sorted(band_counts)
    ]
    return {
        "class": material_class,
        "chemistry": chemistry,
        "structure_prototype": prototype,
        "composition_space_neighbourhood": "csn-zband10-v1:" + ",".join(terms),
    }


def assign_panel_roles(
    candidates: list[dict[str, Any]],
    vocabulary: dict[str, Any] | None = None,
    *,
    seed: str = DEFAULT_SPLIT_SEED,
) -> list[dict[str, Any]]:
    """Assign one immutable class-stratified calibration/test role per structure."""
    if seed != DEFAULT_SPLIT_SEED:
        raise GroupingRefusalError("REFUSE_SPLIT_SEED", repr(seed))
    if not isinstance(candidates, list) or not candidates:
        raise GroupingRefusalError("REFUSE_CANDIDATE_CONTAINER", "non-empty list required")
    vocabulary = vocabulary or load_vocabulary()
    by_class: dict[str, list[dict[str, Any]]] = defaultdict(list)
    seen_ids: set[str] = set()
    for candidate in candidates:
        if not isinstance(candidate, dict):
            raise GroupingRefusalError("REFUSE_CANDIDATE_CONTAINER", repr(candidate))
        source_id = candidate.get("source_structure_id")
        if not isinstance(source_id, str) or not source_id:
            raise GroupingRefusalError("REFUSE_SOURCE_STRUCTURE_ID", repr(source_id))
        if source_id in seen_ids:
            raise GroupingRefusalError("REFUSE_DUPLICATE_SOURCE_STRUCTURE_ID", source_id)
        seen_ids.add(source_id)
        groupings = derive_groupings(candidate, vocabulary)
        material_class = groupings["class"]
        rank_payload = f"{seed}\0{material_class}\0{source_id}".encode("utf-8")
        by_class[material_class].append(
            {
                "source_structure_id": source_id,
                "groupings": groupings,
                "split_rank": hashlib.sha256(rank_payload).hexdigest(),
            }
        )
    assignments: list[dict[str, Any]] = []
    for material_class in vocabulary["class_vocabulary"]["allowed"]:
        rows = sorted(
            by_class.get(material_class, []),
            key=lambda row: (row["split_rank"], row["source_structure_id"]),
        )
        if len(rows) < 6:
            raise GroupingRefusalError(
                "REFUSE_CLASS_SPLIT_UNDEROCCUPIED", f"{material_class}:{len(rows)}"
            )
        calibration_count = (2 * len(rows)) // 3
        if calibration_count < 4 or calibration_count >= len(rows):
            raise GroupingRefusalError(
                "REFUSE_CLASS_SPLIT_CARDINALITY",
                f"{material_class}:{len(rows)}:{calibration_count}",
            )
        for index, row in enumerate(rows):
            assignments.append(
                {
                    **row,
                    "split_seed": seed,
                    "class_size": len(rows),
                    "class_calibration_count": calibration_count,
                    "class_target_count": len(rows) - calibration_count,
                    "role": "calibration" if index < calibration_count else "held_out_target",
                }
            )
    if len(assignments) != len(candidates):
        raise GroupingRefusalError(
            "REFUSE_CLASS_VOCABULARY_COVERAGE",
            f"assigned={len(assignments)} candidates={len(candidates)}",
        )
    return assignments


def calibration_ids_for_target(
    assignments: list[dict[str, Any]],
    target_source_structure_id: str,
    rule: str,
    *,
    minimum_calibration: int = 4,
) -> list[str]:
    """Return fixed calibration IDs for one genuinely held-out target and rule."""
    if rule not in ALLOWED_RULES:
        raise GroupingRefusalError("REFUSE_GROUPING_RULE", repr(rule))
    if minimum_calibration != 4:
        raise GroupingRefusalError(
            "REFUSE_MINIMUM_CALIBRATION", str(minimum_calibration)
        )
    matches = [
        row for row in assignments if row["source_structure_id"] == target_source_structure_id
    ]
    if len(matches) != 1:
        raise GroupingRefusalError("REFUSE_TARGET_IDENTITY", target_source_structure_id)
    target = matches[0]
    if target["role"] != "held_out_target":
        raise GroupingRefusalError("REFUSE_TARGET_ROLE", target_source_structure_id)
    key = target["groupings"][rule]
    calibration_ids = sorted(
        row["source_structure_id"]
        for row in assignments
        if row["role"] == "calibration" and row["groupings"][rule] == key
    )
    if len(calibration_ids) < minimum_calibration:
        raise GroupingRefusalError(
            "INSUFFICIENT_GROUP_CALIBRATION", f"{rule}:{key}:{len(calibration_ids)}"
        )
    if target_source_structure_id in calibration_ids:
        raise GroupingRefusalError("REFUSE_HELDOUT_LEAKAGE", target_source_structure_id)
    return calibration_ids


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidate", type=Path, help="candidate JSON object or array")
    parser.add_argument("--vocabulary", type=Path, default=DEFAULT_VOCABULARY)
    parser.add_argument("--assign-heldout-roles", action="store_true")
    parser.add_argument("--split-seed", default=DEFAULT_SPLIT_SEED)
    args = parser.parse_args()
    vocabulary = load_vocabulary(args.vocabulary)
    payload = json.loads(args.candidate.read_text(encoding="utf-8"))
    if args.assign_heldout_roles:
        if not isinstance(payload, list):
            raise GroupingRefusalError("REFUSE_CANDIDATE_CONTAINER", "array required")
        output: Any = assign_panel_roles(payload, vocabulary, seed=args.split_seed)
    else:
        candidates = payload if isinstance(payload, list) else [payload]
        if not candidates or not all(isinstance(item, dict) for item in candidates):
            raise GroupingRefusalError("REFUSE_CANDIDATE_CONTAINER", str(args.candidate))
        derived = [derive_groupings(item, vocabulary) for item in candidates]
        output = derived if isinstance(payload, list) else derived[0]
    print(json.dumps(output, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
