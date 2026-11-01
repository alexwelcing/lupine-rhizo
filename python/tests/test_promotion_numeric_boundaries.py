"""Fail-closed numeric evidence at promotion and saved benchmark boundaries."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from lupine_distill.odf.promotion_gate import CandidateMetadata, evaluate, evaluate_promotion
from lupine_distill.schemas import BenchmarkMetrics, BenchmarkResult
from pydantic import ValidationError

pytestmark = pytest.mark.unit
ROOT = Path(__file__).resolve().parents[2]
BASE = {
    "model_id": "numeric-boundary-fixture",
    "distill_version": 1,
    "overall_uplift_pct": 7.5,
    "atlas_theorem_refs": ["asserted-ref"],
    "formal_properties": ["asserted-property"],
}


def cli_environment():
    env = dict(os.environ, PYTHONPATH=str(ROOT / "python"))
    # These are local packet/validation tests; never inherit opt-in telemetry.
    env.pop("PHOENIX_OTLP_RELAY_URL", None)
    return env


@pytest.mark.parametrize("entrypoint", [evaluate, evaluate_promotion])
@pytest.mark.parametrize("mutation", ["pop", "nan", "inf"])
def test_public_gate_revalidates_mutated_typed_candidate(entrypoint, mutation):
    candidate = CandidateMetadata.model_validate(
        BASE | {"reference_ranking": [1, 2], "model_ranking": [1, 2]}
    )
    # frozen=True protects field assignment, not mutations of a contained list.
    if mutation == "pop":
        candidate.model_ranking.pop()
    else:
        candidate.model_ranking[1] = float(mutation)
    with pytest.raises(ValueError, match="Invalid promotion candidate metadata"):
        entrypoint(candidate)


@pytest.mark.parametrize("entrypoint", [evaluate, evaluate_promotion])
def test_public_gate_typed_candidate_keeps_valid_semantics(entrypoint):
    candidate = CandidateMetadata.model_validate(
        BASE | {"reference_ranking": [1, 2], "model_ranking": [1, 2]}
    )
    assert entrypoint(candidate).decision.value == "promote"
    assert candidate.model_ranking == [1, 2]


@pytest.mark.parametrize("value", [float("inf"), float("-inf"), float("nan")])
def test_nonfinite_uplift_mapping_is_rejected(value):
    with pytest.raises(ValueError, match="finite"):
        evaluate_promotion(BASE | {"overall_uplift_pct": value})


@pytest.mark.parametrize("literal", ["1e999", "-1e999", "NaN", "Infinity", "-Infinity"])
def test_nonfinite_uplift_json_is_rejected(literal):
    payload = json.dumps(BASE).replace("7.5", literal)
    with pytest.raises(ValidationError, match="finite"):
        CandidateMetadata.model_validate_json(payload)
    # Standard json.loads is also used by file-based callers.
    with pytest.raises(ValueError, match="finite"):
        evaluate_promotion(json.loads(payload))


@pytest.mark.parametrize("literal", ["1e999", "NaN", "Infinity"])
def test_nonfinite_ranking_json_is_rejected(literal):
    payload = json.dumps(BASE | {"reference_ranking": [1, 2], "model_ranking": [1, 0.125]})
    payload = payload.replace("0.125", literal)
    with pytest.raises(ValidationError, match="finite"):
        CandidateMetadata.model_validate_json(payload)


@pytest.mark.parametrize(
    "rankings",
    [
        {"reference_ranking": [1, 2]},
        {"model_ranking": [1, 2]},
        {"reference_ranking": [], "model_ranking": []},
        {"reference_ranking": [1], "model_ranking": [1]},
        {"reference_ranking": [1, 2], "model_ranking": [1]},
        {"reference_ranking": [1, float("nan")], "model_ranking": [1, 2]},
        {"reference_ranking": [1, 2], "model_ranking": [1, float("inf")]},
    ],
)
def test_supplied_invalid_rankings_are_rejected(rankings):
    with pytest.raises(ValueError, match="ranking|finite"):
        evaluate_promotion(BASE | rankings)


@pytest.mark.parametrize(
    "value,decision", [(-0.01, "reject"), (0, "review"), (5, "review"), (5.0001, "promote")]
)
def test_valid_uplift_boundaries_with_optional_rankings_absent(value, decision):
    assert evaluate_promotion(BASE | {"overall_uplift_pct": value}).decision.value == decision
    assert (
        evaluate_promotion(
            BASE | {"overall_uplift_pct": value, "reference_ranking": None, "model_ranking": None}
        ).decision.value
        == decision
    )


def test_valid_rankings_and_missing_uplift_keep_existing_semantics():
    assert (
        evaluate_promotion(
            BASE | {"reference_ranking": [1, 2], "model_ranking": [2, 3]}
        ).decision.value
        == "promote"
    )
    assert (
        evaluate_promotion(
            BASE | {"reference_ranking": [1, 2], "model_ranking": [3, 2]}
        ).decision.value
        == "review"
    )
    assert evaluate_promotion(BASE | {"overall_uplift_pct": None}).decision.value == "reject"


@pytest.mark.parametrize("field", ["mae_energy", "mae_forces", "mae_stress", "rmse_energy"])
@pytest.mark.parametrize("value", [-0.01, float("inf"), float("nan")])
def test_error_metrics_must_be_finite_and_nonnegative(field, value):
    with pytest.raises(ValidationError):
        BenchmarkMetrics(**{field: value}, wall_time_seconds=0)


def test_optional_zero_and_signed_physical_values_remain_valid():
    metrics = BenchmarkMetrics(
        mae_energy=0, energy_drift=-0.1, dft_reference={"energy": -1.2}, wall_time_seconds=0
    )
    assert metrics.mae_forces is None
    assert metrics.energy_drift == -0.1


@pytest.mark.parametrize("field", ["energy_drift", "temperature_stability", "wall_time_seconds"])
def test_other_benchmark_numeric_fields_must_be_finite(field):
    with pytest.raises(ValidationError):
        BenchmarkMetrics(**({"wall_time_seconds": 0} | {field: float("inf")}))


def test_nonfinite_reference_and_result_uplift_are_rejected():
    with pytest.raises(ValidationError):
        BenchmarkMetrics(dft_reference={"energy": float("nan")}, wall_time_seconds=0)
    with pytest.raises(ValidationError):
        BenchmarkResult(
            model_id="m",
            distill_version=1,
            backend="torchsim",
            timestamp="2026-11-01T00:00:00Z",
            torchsim_version="mock-0",
            benchmark_suite_version="fixture",
            overall_uplift_pct=float("inf"),
        )


@pytest.mark.parametrize("literal", ["1e999", "NaN", "Infinity"])
def test_actual_uplift_cli_rejects_saved_nonfinite_benchmark(tmp_path, literal):
    result = {
        "model_id": "numeric-boundary-fixture",
        "distill_version": 0,
        "backend": "torchsim",
        "timestamp": "2026-11-01T00:00:00Z",
        "torchsim_version": "mock-0",
        "benchmark_suite_version": "fixture",
        "results": {"static_energy": {"mae_energy": 0.125, "wall_time_seconds": 0}},
    }
    payload = json.dumps(result).replace("0.125", literal)
    with pytest.raises(ValidationError):
        BenchmarkResult.model_validate_json(payload)
    saved = tmp_path / "invalid.json"
    saved.write_text(payload, encoding="utf-8")
    output = tmp_path / "must-not-exist.json"
    env = cli_environment()
    process = subprocess.run(
        [
            sys.executable,
            "-m",
            "lupine_distill.uplift",
            "--model",
            result["model_id"],
            "--distill-v",
            "1",
            "--baseline",
            str(saved),
            "--distilled",
            str(saved),
            "--output",
            str(output),
        ],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert process.returncode != 0
    assert "finite" in process.stderr
    assert not output.exists()


@pytest.mark.parametrize("literal", ["1e999", "NaN", "Infinity"])
def test_actual_local_promotion_cli_rejects_nonfinite_uplift(tmp_path, literal):
    run = tmp_path / "run"
    cell = run / "artifacts" / "baseline"
    cell.mkdir(parents=True)
    (cell / "cell_result.json").write_text(
        json.dumps(
            {
                "variant_id": "baseline",
                "row_id": "energy_volume",
                "mlip_id": "fixture",
                "accuracy": {"score": 0.1},
            }
        ),
        encoding="utf-8",
    )
    output = tmp_path / "must-not-exist.json"
    process = subprocess.run(
        [
            sys.executable,
            str(ROOT / "tools/mlip_local_promotion.py"),
            "--run-dir",
            str(run),
            "--output",
            str(output),
            "--no-env-field-certificates",
            "--overall-uplift-pct",
            literal,
            "--atlas-theorem-refs",
            "asserted-ref",
            "--formal-properties",
            "asserted-property",
        ],
        cwd=ROOT,
        env=cli_environment(),
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert process.returncode != 0
    assert "finite" in process.stderr
    assert not output.exists()


@pytest.mark.parametrize("uplift,decision", [(0, "review"), (5, "review"), (5.0001, "promote")])
def test_actual_local_promotion_cli_keeps_valid_thresholds(tmp_path, uplift, decision):
    run = tmp_path / "run"
    cell = run / "artifacts" / "baseline"
    cell.mkdir(parents=True)
    (cell / "cell_result.json").write_text(
        json.dumps(
            {
                "variant_id": "baseline",
                "row_id": "energy_volume",
                "mlip_id": "fixture",
                "accuracy": {"score": 0.1},
            }
        ),
        encoding="utf-8",
    )
    output = tmp_path / "packet.json"
    process = subprocess.run(
        [
            sys.executable,
            str(ROOT / "tools/mlip_local_promotion.py"),
            "--run-dir",
            str(run),
            "--output",
            str(output),
            "--no-env-field-certificates",
            "--overall-uplift-pct",
            str(uplift),
            "--atlas-theorem-refs",
            "asserted-ref",
            "--formal-properties",
            "asserted-property",
        ],
        cwd=ROOT,
        env=cli_environment(),
        capture_output=True,
        text=True,
        timeout=20,
    )
    # The CLI reports a hold as exit 1 even when the packet was built successfully.
    assert process.returncode == 1, process.stderr
    packet = json.loads(output.read_text(encoding="utf-8"))
    assert packet["odf_gate"]["decision"] == decision
    # The synthetic, incomplete run never authorizes execution of a cloud canary.
    assert packet["gate"]["status"] == "hold_local"
