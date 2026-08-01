"""Contracts for LiteratureHypothesis v1 fixtures and D1 persistence."""

from __future__ import annotations

import json
import sqlite3
from copy import deepcopy
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "schemas" / "literature-hypothesis.v1.schema.json"
EXAMPLES_DIR = ROOT / "examples" / "literature-hypotheses"
MIGRATION_PATH = ROOT / "glim-think" / "migrations" / "0012_literature_hypotheses.sql"
SCHEMA_SQL_PATH = ROOT / "glim-think" / "schema.sql"
EXPECTED_TOP_LEVEL_FIELDS = {
    "source",
    "claim_text",
    "bindings",
    "epistemicMarker",
    "readiness",
    "confidence",
    "proposedExperiment",
    "status",
}
BARRIER_PREDICATE = "barrier_mae_mev<=40"
SQLITE_MAX_INTEGER = 9_223_372_036_854_775_807


def load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture
def schema() -> dict[str, object]:
    value = load_json(SCHEMA_PATH)
    Draft202012Validator.check_schema(value)
    return value


@pytest.fixture
def examples() -> list[dict[str, object]]:
    paths = sorted(EXAMPLES_DIR.glob("*.json"))
    assert [path.name for path in paths] == [
        "deng-underbinding.json",
        "lian-ts-finetuning.json",
        "migration-underprediction.json",
    ]
    return [load_json(path) for path in paths]


def test_three_hand_authored_examples_validate_deterministically(schema, examples) -> None:
    validator = Draft202012Validator(schema, format_checker=FormatChecker())

    for example in examples:
        assert set(example) == EXPECTED_TOP_LEVEL_FIELDS
        validator.validate(example)

    assert {example["proposedExperiment"]["predicate"] for example in examples} == {
        BARRIER_PREDICATE
    }


def test_schema_rejects_predicates_outside_existing_barrier_whitelist(schema, examples) -> None:
    invalid = deepcopy(examples[0])
    invalid["proposedExperiment"]["predicate"] = "adsorption_energy_mae<=0.1"

    errors = list(Draft202012Validator(schema).iter_errors(invalid))

    assert errors
    assert any(BARRIER_PREDICATE in error.message for error in errors)


def test_schema_rejects_untyped_bindings_and_unannotated_readiness(schema, examples) -> None:
    invalid_binding = deepcopy(examples[0])
    invalid_binding["bindings"]["chains"] = ["chain-1"]
    invalid_readiness = deepcopy(examples[0])
    invalid_readiness["readiness"] = "Medium"
    trailing_newline_readiness = deepcopy(examples[0])
    trailing_newline_readiness["readiness"] += "\n"
    validator = Draft202012Validator(schema)

    assert list(validator.iter_errors(invalid_binding))
    assert list(validator.iter_errors(invalid_readiness))
    assert list(validator.iter_errors(trailing_newline_readiness))


def test_schema_rejects_estimated_cells_outside_d1_integer_range(schema, examples) -> None:
    validator = Draft202012Validator(schema)
    largest_valid = deepcopy(examples[0])
    largest_valid["proposedExperiment"]["estimated_cells"] = SQLITE_MAX_INTEGER
    too_large = deepcopy(largest_valid)
    too_large["proposedExperiment"]["estimated_cells"] = 1e100

    assert not list(validator.iter_errors(largest_valid))
    assert list(validator.iter_errors(too_large))


def test_d1_migration_persists_contract_and_enforces_enums(examples) -> None:
    connection = sqlite3.connect(":memory:")
    try:
        connection.executescript(MIGRATION_PATH.read_text(encoding="utf-8"))
        example = examples[0]
        connection.execute(
            """
            INSERT INTO literature_hypotheses (literature_hypothesis_id, contract_json)
            VALUES (?, ?)
            """,
            (
                "lit-hypothesis.deng-underbinding.v1",
                json.dumps(example, sort_keys=True),
            ),
        )
        assert connection.execute(
            "SELECT claim_text, status FROM literature_hypotheses"
        ).fetchone() == (example["claim_text"], "proposed")

        invalid_predicate = deepcopy(example)
        invalid_predicate["proposedExperiment"]["predicate"] = (
            "adsorption_energy_mae<=0.1"
        )
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                """
                INSERT INTO literature_hypotheses (literature_hypothesis_id, contract_json)
                VALUES ('invalid-predicate', ?)
                """,
                (json.dumps(invalid_predicate, sort_keys=True),),
            )

        invalid_status = deepcopy(example)
        invalid_status["status"] = "testing"
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                """
                INSERT INTO literature_hypotheses (literature_hypothesis_id, contract_json)
                VALUES ('invalid-status', ?)
                """,
                (json.dumps(invalid_status, sort_keys=True),),
            )

        invalid_source = deepcopy(example)
        invalid_source["source"] = None
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                """
                INSERT INTO literature_hypotheses (literature_hypothesis_id, contract_json)
                VALUES ('invalid-source', ?)
                """,
                (json.dumps(invalid_source, sort_keys=True),),
            )

        missing_status = deepcopy(example)
        del missing_status["status"]
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                """
                INSERT INTO literature_hypotheses (literature_hypothesis_id, contract_json)
                VALUES ('missing-status', ?)
                """,
                (json.dumps(missing_status, sort_keys=True),),
            )

        with pytest.raises(sqlite3.OperationalError, match="generated column"):
            connection.execute(
                "UPDATE literature_hypotheses SET status = 'accepted'"
            )

        invalid_contracts = []
        extra_property = deepcopy(example)
        extra_property["unexpected"] = True
        invalid_contracts.append(extra_property)
        missing_source_fields = deepcopy(example)
        missing_source_fields["source"] = {}
        invalid_contracts.append(missing_source_fields)
        bogus_binding = deepcopy(example)
        bogus_binding["bindings"]["chains"] = ["bogus"]
        invalid_contracts.append(bogus_binding)
        duplicate_binding = deepcopy(example)
        duplicate_binding["bindings"]["errorTypes"] = ["T2", "T2"]
        invalid_contracts.append(duplicate_binding)
        incomplete_experiment = deepcopy(example)
        del incomplete_experiment["proposedExperiment"]["estimated_cells"]
        invalid_contracts.append(incomplete_experiment)
        invalid_calendar_date = deepcopy(example)
        invalid_calendar_date["source"]["asOf"] = "2026-02-31"
        invalid_contracts.append(invalid_calendar_date)
        invalid_doi = deepcopy(example)
        invalid_doi["source"]["doi"] = "10.1234/a b"
        invalid_contracts.append(invalid_doi)
        whitespace_claim = deepcopy(example)
        whitespace_claim["claim_text"] = "\t"
        invalid_contracts.append(whitespace_claim)
        whitespace_panel = deepcopy(example)
        whitespace_panel["proposedExperiment"]["panel_ref"] = "\t"
        invalid_contracts.append(whitespace_panel)
        year_zero = deepcopy(example)
        year_zero["source"]["asOf"] = "0000-01-01"
        invalid_contracts.append(year_zero)
        for whitespace in (
            "\t",
            "\n",
            "\v",
            "\f",
            "\r",
            "\u001c",
            "\u001d",
            "\u001e",
            "\u001f",
            "\u00a0",
            "\u2003",
        ):
            whitespace_claim = deepcopy(example)
            whitespace_claim["claim_text"] = whitespace
            invalid_contracts.append(whitespace_claim)
            whitespace_external_id = deepcopy(example)
            whitespace_external_id["source"]["doi"] = None
            whitespace_external_id["source"]["arxiv_id"] = whitespace
            invalid_contracts.append(whitespace_external_id)
            whitespace_doi = deepcopy(example)
            whitespace_doi["source"]["doi"] = f"10.1234/a{whitespace}b"
            invalid_contracts.append(whitespace_doi)
            whitespace_readiness = deepcopy(example)
            whitespace_readiness["readiness"] = f"M ({whitespace})"
            invalid_contracts.append(whitespace_readiness)
        uppercase_scheme = deepcopy(example)
        uppercase_scheme["source"]["url"] = "HTTPS://doi.org/example"
        invalid_contracts.append(uppercase_scheme)
        empty_host_url = deepcopy(example)
        empty_host_url["source"]["url"] = "https://"
        invalid_contracts.append(empty_host_url)
        whitespace_url = deepcopy(example)
        whitespace_url["source"]["url"] = "https:// space"
        invalid_contracts.append(whitespace_url)
        bracket_url = deepcopy(example)
        bracket_url["source"]["url"] = "https://["
        invalid_contracts.append(bracket_url)
        trailing_newline_readiness = deepcopy(example)
        trailing_newline_readiness["readiness"] += "\n"
        invalid_contracts.append(trailing_newline_readiness)

        for ordinal, invalid_contract in enumerate(invalid_contracts):
            with pytest.raises(sqlite3.IntegrityError):
                connection.execute(
                    """
                    INSERT INTO literature_hypotheses (
                      literature_hypothesis_id, contract_json
                    ) VALUES (?, ?)
                    """,
                    (f"schema-invalid-{ordinal}", json.dumps(invalid_contract)),
                )

        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                """
                UPDATE literature_hypotheses SET contract_json = ?
                WHERE literature_hypothesis_id = 'lit-hypothesis.deng-underbinding.v1'
                """,
                (json.dumps(extra_property),),
            )

        accepted_contract = deepcopy(example)
        accepted_contract["status"] = "accepted"
        connection.execute(
            """
            UPDATE literature_hypotheses SET contract_json = ?
            WHERE literature_hypothesis_id = 'lit-hypothesis.deng-underbinding.v1'
            """,
            (json.dumps(accepted_contract),),
        )
        assert connection.execute(
            """
            SELECT status FROM literature_hypotheses
            WHERE literature_hypothesis_id = 'lit-hypothesis.deng-underbinding.v1'
            """
        ).fetchone() == ("accepted",)

        integral_real_cells = deepcopy(example)
        integral_real_cells["proposedExperiment"]["estimated_cells"] = 1.0
        connection.execute(
            """
            INSERT INTO literature_hypotheses (literature_hypothesis_id, contract_json)
            VALUES ('integral-real-cells', ?)
            """,
            (json.dumps(integral_real_cells),),
        )

        largest_valid_cells = deepcopy(example)
        largest_valid_cells["proposedExperiment"]["estimated_cells"] = (
            SQLITE_MAX_INTEGER
        )
        connection.execute(
            """
            INSERT INTO literature_hypotheses (literature_hypothesis_id, contract_json)
            VALUES ('largest-valid-cells', ?)
            """,
            (json.dumps(largest_valid_cells),),
        )

        for ordinal, value in enumerate(
            (SQLITE_MAX_INTEGER + 1, SQLITE_MAX_INTEGER + 2, 1e100)
        ):
            too_large_cells = deepcopy(example)
            too_large_cells["proposedExperiment"]["estimated_cells"] = value
            with pytest.raises(sqlite3.IntegrityError):
                connection.execute(
                    """
                    INSERT INTO literature_hypotheses (
                      literature_hypothesis_id, contract_json
                    ) VALUES (?, ?)
                    """,
                    (f"too-large-cells-{ordinal}", json.dumps(too_large_cells)),
                )

        too_large_update = deepcopy(example)
        too_large_update["proposedExperiment"]["estimated_cells"] = (
            SQLITE_MAX_INTEGER + 1
        )
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                """
                UPDATE literature_hypotheses SET contract_json = ?
                WHERE literature_hypothesis_id = 'lit-hypothesis.deng-underbinding.v1'
                """,
                (json.dumps(too_large_update),),
            )
    finally:
        connection.close()


def test_d1_rejects_null_hypothesis_identifier(examples) -> None:
    connection = sqlite3.connect(":memory:")
    try:
        connection.executescript(MIGRATION_PATH.read_text(encoding="utf-8"))
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                """
                INSERT INTO literature_hypotheses (
                  literature_hypothesis_id, contract_json
                ) VALUES (NULL, ?)
                """,
                (json.dumps(examples[0], sort_keys=True),),
            )
    finally:
        connection.close()


def test_latest_state_schema_sql_mirrors_literature_hypotheses(examples) -> None:
    connection = sqlite3.connect(":memory:")
    try:
        connection.executescript(SCHEMA_SQL_PATH.read_text(encoding="utf-8"))
        connection.execute(
            """
            INSERT INTO literature_hypotheses (literature_hypothesis_id, contract_json)
            VALUES ('latest-state.deng-underbinding.v1', ?)
            """,
            (json.dumps(examples[0], sort_keys=True),),
        )
        invalid_status = deepcopy(examples[0])
        invalid_status["status"] = "testing"
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                """
                INSERT INTO literature_hypotheses (
                  literature_hypothesis_id, contract_json
                ) VALUES ('latest-state.invalid-status', ?)
                """,
                (json.dumps(invalid_status, sort_keys=True),),
            )
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                """
                INSERT INTO literature_hypotheses (
                  literature_hypothesis_id, contract_json
                ) VALUES (NULL, ?)
                """,
                (json.dumps(examples[0], sort_keys=True),),
            )
    finally:
        connection.close()
