#!/usr/bin/env python3
"""Build fail-closed D1 updates for the nightly evidence/ontology feedback loop."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import date, datetime
from pathlib import Path
from typing import Any

HASH_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
ACCEPTANCE_PREDICATE_RE = re.compile(
    r"^(?P<metric>[a-z0-9_]+)_(?P<unit>mev)<=(?P<threshold>[0-9]+(?:\.[0-9]+)?)$"
)
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
            or comparator != "less_than_or_equal"
            or asserted_outcome not in {"pass", "fail"}
        ):
            raise ValueError("EvidenceBundle contains an invalid acceptance measurement")
        expected_threshold = float(predicate_match.group("threshold"))
        if (
            measurement.get("metric") != predicate_match.group("metric")
            or str(measurement.get("unit", "")).lower() != predicate_match.group("unit")
            or float(threshold) != expected_threshold
        ):
            raise ValueError(
                "EvidenceBundle acceptance threshold or metric disagrees with its bound predicate"
            )
        measured_outcome = "pass" if value <= threshold else "fail"
        if asserted_outcome != measured_outcome:
            raise ValueError(
                "EvidenceBundle asserted acceptance outcome disagrees with its measured value"
            )
        outcomes.append(measured_outcome)
    return outcomes


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
        outcomes = _acceptance_outcomes(bundle, as_of)
        if not outcomes:
            continue
        defined.append(bundle_id)
        if outcomes and all(outcome == "pass" for outcome in outcomes):
            passing.append(bundle_id)
            for reference in bundle.get("evidence_refs", []):
                if isinstance(reference, dict) and isinstance(reference.get("campaign"), str):
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
    chain_states = {
        chain: _chain_state(chain, assumption_rows, evidence_by_id, cycle_date)
        for chain in priority
    }
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

        states = [chain_states[chain] for chain in bound_chains]
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


def render_feedback_sql(plan: dict[str, Any]) -> str:
    """Render one atomic, reviewable D1 script from a feedback plan."""
    statements = ["-- Generated by tools/nightly_ontology_feedback.py", "BEGIN TRANSACTION;"]
    for bundle in plan.get("evidence", []):
        supersedes = bundle.get("supersedes") or []
        statements.append(
            "INSERT INTO evidence_bundle (bundle_id, claim_predicate, epistemic_status, scope_json, provenance_json, supersedes_bundle_id) "
            f"VALUES ({_sql(bundle['bundle_id'])}, {_sql(bundle['claim_predicate'])}, {_sql(bundle['epistemic_status'])}, "
            f"{_sql(_canonical(bundle['scope']))}, {_sql(_canonical(bundle['provenance']))}, {_sql(supersedes[0] if supersedes else None)}) "
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
    new_ids_payload = _load(args.new_bundle_ids)
    ingested_ids = set(new_ids_payload.get("ingested_bundle_ids", new_ids_payload))
    new_ids = ingested_ids - _known_bundle_ids(_load(args.known_bundle_ids))
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
