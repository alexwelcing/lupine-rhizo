"""Deterministic LiteratureHypothesis to CampaignManifest conversion contracts."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
from copy import deepcopy
from pathlib import Path

import pytest
import rfc8785
from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[2]
CONVERTER_PATH = ROOT / "tools" / "lit_to_manifest.py"
INPUTS = ROOT / "examples" / "literature-hypotheses"
OUTPUTS = ROOT / "examples" / "lit-to-manifest"
CAMPAIGN_SCHEMA = ROOT / "schemas" / "campaign-manifest.v1.schema.json"
PANEL_PATH = "data/candidates/z1_nebdft2k_barriers.lock.json"
PANEL_SHA256 = "sha256:192fe54a5579cc421f6644d5d76fb442c6dfb985f014dc4741549e29052efb68"
REGISTERED_AT = "2026-08-01T04:55:29Z"
EXPECTED_OUTPUTS = [
    "deng-underbinding.campaign-manifest.v1.json",
    "lian-ts-finetuning.campaign-manifest.v1.json",
    "migration-underprediction.campaign-manifest.v1.json",
]


def load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_converter():
    spec = importlib.util.spec_from_file_location("lit_to_manifest", CONVERTER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def convert(converter, hypothesis, *, hypothesis_id="deng-underbinding", root=ROOT):
    return converter.convert_hypothesis(
        hypothesis,
        hypothesis_id=hypothesis_id,
        hypothesis_ref=f"examples/literature-hypotheses/{hypothesis_id}.json",
        registered_at=REGISTERED_AT,
        root=root,
    )


def test_three_a3_examples_convert_to_checked_in_deterministic_fixtures() -> None:
    converter = load_converter()
    validator = Draft202012Validator(
        load_json(CAMPAIGN_SCHEMA), format_checker=FormatChecker()
    )
    output_paths = sorted(OUTPUTS.glob("*.json"))
    assert [path.name for path in output_paths] == EXPECTED_OUTPUTS

    for input_path, output_path in zip(sorted(INPUTS.glob("*.json")), output_paths, strict=True):
        hypothesis = load_json(input_path)
        expected = load_json(output_path)
        first = convert(converter, hypothesis, hypothesis_id=input_path.stem)
        second = convert(converter, deepcopy(hypothesis), hypothesis_id=input_path.stem)

        assert first == second == expected
        validator.validate(first)
        assert hypothesis["bindings"]["materialClasses"] == ["MC4"]
        assert first["preregistration"]["frozen_before_execution"] is True
        assert first["preregistration"]["registered_at"] == REGISTERED_AT
        assert first["preregistration"]["source_as_of"] == hypothesis["source"]["asOf"]
        assert first["preregistration"]["input_document"] == {
            "path": f"examples/literature-hypotheses/{input_path.name}",
            "sha256": "sha256:" + hashlib.sha256(input_path.read_bytes()).hexdigest(),
        }
        assert first["frozen_hypotheses"] == [
            {
                "hypothesis_id": f"lit-hypothesis.{input_path.stem}.v1",
                "statement": hypothesis["claim_text"],
                "frozen": True,
            }
        ]
        assert first["target_premises"] == [
            {
                "claim_id": "discovery.z1.barrier-accuracy.v1",
                "premise_id": "chemistry-held-out-neb",
            }
        ]
        assert first["acceptance_test"] == {
            "metric": "barrier_mae",
            "operator": "lte",
            "threshold": 40,
            "unit": "meV",
        }
        assert first["execution"]["candidate_panel"] == {
            "path": PANEL_PATH,
            "sha256": PANEL_SHA256,
        }
        unhashed = {key: value for key, value in first.items() if key != "content_hash"}
        canonical = rfc8785.dumps(unhashed)
        assert first["content_hash"] == "sha256:" + hashlib.sha256(canonical).hexdigest()


def test_missing_panel_ref_uses_nearest_locked_panel(tmp_path: Path) -> None:
    converter = load_converter()
    hypothesis = load_json(INPUTS / "deng-underbinding.json")
    del hypothesis["proposedExperiment"]["panel_ref"]
    template = tmp_path / "campaigns" / "v1" / "z1.campaign-manifest.v1.json"
    template.parent.mkdir(parents=True)
    template.write_bytes((ROOT / "campaigns" / "v1" / template.name).read_bytes())
    panel = tmp_path / PANEL_PATH
    panel.parent.mkdir(parents=True)
    panel.write_bytes((ROOT / PANEL_PATH).read_bytes())
    source = tmp_path / "examples" / "literature-hypotheses" / "deng-underbinding.json"
    source.parent.mkdir(parents=True)
    source.write_text(json.dumps(hypothesis), encoding="utf-8")

    manifest = convert(converter, hypothesis, root=tmp_path)

    assert manifest["execution"]["candidate_panel"] == {
        "path": PANEL_PATH,
        "sha256": PANEL_SHA256,
    }


@pytest.mark.parametrize("status", ["rejected", "superseded"])
def test_converter_rejects_hypotheses_that_are_not_executable(status: str) -> None:
    converter = load_converter()
    hypothesis = load_json(INPUTS / "deng-underbinding.json")
    hypothesis["status"] = status

    with pytest.raises(converter.ConversionError, match="status"):
        convert(converter, hypothesis)


def test_bindings_drive_mapped_fields_even_if_template_semantics_drift(tmp_path: Path) -> None:
    converter = load_converter()
    hypothesis = load_json(INPUTS / "deng-underbinding.json")
    template_path = tmp_path / "campaigns" / "v1" / "z1.campaign-manifest.v1.json"
    template_path.parent.mkdir(parents=True)
    template = load_json(ROOT / "campaigns" / "v1" / "z1.campaign-manifest.v1.json")
    template["target_premises"] = [
        {"claim_id": "unrelated.claim.v1", "premise_id": "unrelated-premise"}
    ]
    template["acceptance_test"] = {
        "metric": "unrelated_metric",
        "operator": "gte",
        "threshold": 1,
        "unit": "arbitrary",
    }
    template_path.write_text(json.dumps(template), encoding="utf-8")
    panel_path = tmp_path / PANEL_PATH
    panel_path.parent.mkdir(parents=True)
    panel_path.write_bytes((ROOT / PANEL_PATH).read_bytes())
    source = tmp_path / "examples" / "literature-hypotheses" / "deng-underbinding.json"
    source.parent.mkdir(parents=True)
    source.write_bytes((INPUTS / "deng-underbinding.json").read_bytes())

    manifest = convert(converter, hypothesis, root=tmp_path)

    assert manifest["target_premises"] == [
        {
            "claim_id": "discovery.z1.barrier-accuracy.v1",
            "premise_id": "chemistry-held-out-neb",
        }
    ]
    assert manifest["acceptance_test"] == {
        "metric": "barrier_mae",
        "operator": "lte",
        "threshold": 40,
        "unit": "meV",
    }


@pytest.mark.parametrize(
    "mutate",
    [
        lambda value: value.pop("status"),
        lambda value: value.__setitem__("unknown", True),
        lambda value: value["source"].__setitem__("asOf", "2026-02-30"),
        lambda value: value["proposedExperiment"].__setitem__("estimated_cells", 0),
        lambda value: value["bindings"].__setitem__("errorTypes", ["T8"]),
    ],
)
def test_converter_rejects_schema_invalid_literature_hypotheses(mutate) -> None:
    converter = load_converter()
    hypothesis = load_json(INPUTS / "deng-underbinding.json")
    mutate(hypothesis)

    with pytest.raises(converter.ConversionError, match="LiteratureHypothesis schema"):
        convert(converter, hypothesis)


def test_converter_rejects_identifier_that_would_exceed_manifest_schema() -> None:
    converter = load_converter()
    hypothesis = load_json(INPUTS / "deng-underbinding.json")

    with pytest.raises(converter.ConversionError, match="CampaignManifest schema"):
        convert(converter, hypothesis, hypothesis_id="x" * 160)


def test_converter_rejects_panel_symlink_that_escapes_repo(tmp_path: Path) -> None:
    converter = load_converter()
    hypothesis = load_json(INPUTS / "deng-underbinding.json")
    template = tmp_path / "campaigns" / "v1"
    template.mkdir(parents=True)
    template.joinpath("z1.campaign-manifest.v1.json").write_bytes(
        (ROOT / "campaigns" / "v1" / "z1.campaign-manifest.v1.json").read_bytes()
    )
    panel = tmp_path / PANEL_PATH
    panel.parent.mkdir(parents=True)
    source = tmp_path / "examples" / "literature-hypotheses" / "deng-underbinding.json"
    source.parent.mkdir(parents=True)
    source.write_bytes((INPUTS / "deng-underbinding.json").read_bytes())
    outside = tmp_path.parent / "outside-panel.json"
    outside.write_text("{}", encoding="utf-8")
    panel.symlink_to(outside)

    with pytest.raises(converter.ConversionError, match="panel_ref escapes"):
        convert(converter, hypothesis, root=tmp_path)


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (
            lambda value: value["proposedExperiment"].__setitem__(
                "predicate", "adsorption_energy_mae<=0.1"
            ),
            "predicate",
        ),
        (
            lambda value: value["bindings"].__setitem__("acceptanceTests", ["Z3"]),
            "acceptanceTests",
        ),
        (
            lambda value: value["bindings"].__setitem__("chains", ["C3"]),
            "chains",
        ),
        (
            lambda value: value["bindings"].__setitem__("materialClasses", ["MC1"]),
            "materialClasses",
        ),
        (
            lambda value: value["proposedExperiment"].__setitem__(
                "panel_ref", "data/candidates/round4_targets.lock.json"
            ),
            "panel_ref",
        ),
        (
            lambda value: value["proposedExperiment"].__setitem__(
                "panel_ref", "../../outside.lock.json"
            ),
            "panel_ref",
        ),
    ],
)
def test_converter_fails_closed_outside_existing_z1_allowlists(mutate, message) -> None:
    converter = load_converter()
    hypothesis = load_json(INPUTS / "deng-underbinding.json")
    mutate(hypothesis)

    with pytest.raises(converter.ConversionError, match=message):
        convert(converter, hypothesis)


def test_converter_requires_explicit_registration_event() -> None:
    converter = load_converter()
    hypothesis = load_json(INPUTS / "deng-underbinding.json")

    with pytest.raises(converter.ConversionError, match="registered_at"):
        converter.convert_hypothesis(
            hypothesis,
            hypothesis_id="deng-underbinding",
            hypothesis_ref="examples/literature-hypotheses/deng-underbinding.json",
            registered_at="2026-02-30T00:00:00Z",
            root=ROOT,
        )


def test_converter_rejects_input_that_does_not_match_reviewed_artifact() -> None:
    converter = load_converter()
    hypothesis = load_json(INPUTS / "deng-underbinding.json")
    hypothesis["claim_text"] = "Different unreviewed claim."

    with pytest.raises(converter.ConversionError, match="does not match"):
        convert(converter, hypothesis)


def test_reviewed_artifact_comparison_distinguishes_booleans_from_numbers(
    tmp_path: Path,
) -> None:
    converter = load_converter()
    hypothesis = load_json(INPUTS / "deng-underbinding.json")
    hypothesis["proposedExperiment"]["estimated_cells"] = 1
    reviewed = deepcopy(hypothesis)
    reviewed["proposedExperiment"]["estimated_cells"] = True
    source = tmp_path / "examples" / "literature-hypotheses" / "deng-underbinding.json"
    source.parent.mkdir(parents=True)
    source.write_text(json.dumps(reviewed), encoding="utf-8")

    with pytest.raises(converter.ConversionError, match="does not match"):
        converter._hypothesis_lock(
            hypothesis,
            hypothesis_id="deng-underbinding",
            hypothesis_ref="examples/literature-hypotheses/deng-underbinding.json",
            root=tmp_path,
        )


def test_cli_writes_canonical_fixture_bytes(tmp_path: Path) -> None:
    output = tmp_path / "manifest.json"
    subprocess.run(
        [
            sys.executable,
            str(CONVERTER_PATH),
            str(INPUTS / "deng-underbinding.json"),
            "--registered-at",
            REGISTERED_AT,
            "--output",
            str(output),
        ],
        cwd=ROOT,
        check=True,
    )

    expected = OUTPUTS / "deng-underbinding.campaign-manifest.v1.json"
    assert output.read_bytes() == expected.read_bytes()
