import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parent


def copied_corpus(tmp_path):
    corpus = tmp_path / "partnerships"
    shutil.copytree(ROOT, corpus)
    return corpus


def run_validator(corpus, cwd):
    return subprocess.run(
        [sys.executable, str(corpus / "validate_partnerships.py")],
        cwd=cwd,
        capture_output=True,
        check=False,
        text=True,
    )


def test_partnership_validator_passes_from_external_working_directory(tmp_path):
    corpus = copied_corpus(tmp_path)
    result = run_validator(corpus, tmp_path)

    assert result.returncode == 0, result.stderr or result.stdout
    report = json.loads(result.stdout)
    assert report == json.loads((corpus / "validation-report.json").read_text())
    assert report["status"] == "PASS"
    assert report["checks"] == 2071
    assert report["errors"] == []
    assert report["official_source_validated_records"] == 33
    assert report["needs_verification_records"] == 60


@pytest.mark.parametrize(
    ("claim", "expected_error"),
    [
        (" Unauthorized pilot economics: 50% lower cost.", "canonical outreach has no unauthorized percentage economics"),
        (" Unauthorized pilot economics: $99 per run.", "canonical outreach has no unauthorized dollar economics"),
    ],
)
def test_partnership_validator_rejects_unauthorized_outreach_economics(tmp_path, claim, expected_error):
    corpus = copied_corpus(tmp_path)
    data_path = corpus / "partner-prospects.json"
    data = json.loads(data_path.read_text())
    data["prospects"][0]["why_lupine_fits"] += claim
    data_path.write_text(json.dumps(data, indent=2) + "\n")

    result = run_validator(corpus, tmp_path)

    assert result.returncode == 1
    report = json.loads(result.stdout)
    assert report["status"] == "FAIL"
    assert expected_error in report["errors"]
