from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUNNER = ROOT / "gcp" / "mlip-cell-runner"


def test_z2_image_packages_spin_runner_gpaw_manifest_and_panel() -> None:
    dockerfile = (RUNNER / "Dockerfile.z2").read_text(encoding="utf-8")
    assert "gpaw==26.7.0" in dockerfile
    assert "COPY gcp/mlip-cell-runner/z2_soc_tc.py ./" in dockerfile
    assert "COPY campaigns/v1/z2.campaign-manifest.v1.json" in dockerfile
    assert "COPY data/candidates/z2_soc_tc_panel.lock.json" in dockerfile
    assert "COPY gcp/mlip-cell-runner/verify_z2_image_contract.py ./" in dockerfile
    assert "python3 /app/verify_z2_image_contract.py" in dockerfile
    assert "chmod -R a+rX /app" in dockerfile
    assert 'ENTRYPOINT ["python3", "/app/mlip_cell_runner.py"]' in dockerfile


def test_z2_packaged_contract_verifier_accepts_only_current_reviewed_inputs() -> None:
    verifier = (RUNNER / "verify_z2_image_contract.py").read_text(encoding="utf-8")
    assert "73f7b9bf8e03d76fc46936911ddd95da7479289fabfd0375cd9b3a66132c7bbc" in verifier
    assert "7d37fd513d3e77c0fced043283bbb8b9a8b98cd241677de00665fe5095c704d8" in verifier
    assert "exchange_mev" in verifier
    assert "exchange_anisotropy" in verifier

    result = subprocess.run(
        [sys.executable, str(RUNNER / "verify_z2_image_contract.py")],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def test_z2_cloud_build_deploys_isolated_job_without_executing_it() -> None:
    cloudbuild = (RUNNER / "cloudbuild.z2.yaml").read_text(encoding="utf-8")
    assert "Dockerfile.z2" in cloudbuild
    assert "mlip-cell-z2-chgnet" in cloudbuild
    assert "jobs" in cloudbuild and "deploy" in cloudbuild
    assert "jobs execute" not in cloudbuild
    assert "image_summary.digest" in cloudbuild
    assert "RUNNER_IMAGE_DIGEST=$${DIGEST}" in cloudbuild
    assert "RUNNER_IMAGE_URI=$${IMAGE_URI}@$${DIGEST}" in cloudbuild
    assert "--image=$${IMAGE_URI}@$${DIGEST}" in cloudbuild


def test_unified_image_packages_zero_spend_z2_abstention_smoke() -> None:
    dockerfile = (RUNNER / "Dockerfile.unified").read_text(encoding="utf-8")
    assert '"torch==2.4.1+cu121"' in dockerfile
    assert '"numpy==1.26.4"' in dockerfile
    assert "requirements-orb.txt" in dockerfile
    assert "requirements-uma.txt" in dockerfile
    assert "https://download.pytorch.org/whl/cu118" in dockerfile
    assert '"${BACKEND}" = "orb"' in dockerfile
    assert '"${BACKEND}" = "uma"' in dockerfile
    assert dockerfile.count('"pydantic>=2.0,<3"') == 2
    assert dockerfile.count('"jsonschema>=4.0,<5"') == 2
    assert "COPY gcp/mlip-cell-runner/z1_sparse_dft.py ./" in dockerfile
    assert "COPY data/candidates/z2/measurements.jsonl" in dockerfile
    assert "COPY data/candidates/z2/artifact-manifest.json" in dockerfile
    assert "COPY campaigns/v1/z2.campaign-manifest.v1.json" in dockerfile

    cloudbuild = (RUNNER / "cloudbuild.unified.yaml").read_text(encoding="utf-8")
    assert "gcr.io/${PROJECT_ID}/mlip-runner:${_BACKEND}" in cloudbuild
    assert "jobs" in cloudbuild and "deploy" in cloudbuild
    assert "jobs execute" not in cloudbuild

    requirements = (RUNNER / "requirements-common.txt").read_text(encoding="utf-8")
    assert "rfc8785" in requirements
    for backend in ("m3gnet", "orb", "uma"):
        isolated = (RUNNER / f"requirements-{backend}.txt").read_text(encoding="utf-8")
        assert "pydantic" in isolated
        assert "jsonschema" in isolated
        assert "rfc8785" in isolated


def test_z2_abstention_audit_tracks_current_chain_tail() -> None:
    manifest = json.loads(
        (ROOT / "data" / "candidates" / "z2" / "artifact-manifest.json").read_text(
            encoding="utf-8"
        )
    )
    chain_tail_prefix = manifest["chain_tail"][:15] + "…"
    for path in (
        ROOT / "docs" / "campaigns" / "z2-abstention-audit.md",
        ROOT
        / "exports"
        / "library-content"
        / "latest"
        / "articles"
        / "docs"
        / "campaigns"
        / "z2-abstention-audit.md",
    ):
        assert chain_tail_prefix in path.read_text(encoding="utf-8")


def test_z2_endpoint_lock_binds_deployed_image_and_help_only_smoke() -> None:
    lock_path = RUNNER / "z2_endpoints.lock.json"
    lock = json.loads(lock_path.read_text(encoding="utf-8"))

    assert lock["schema"] == "lupine.z2.execution_endpoints.v1"
    assert lock["candidate_lock"]["path"] == "data/candidates/z2_soc_tc_panel.lock.json"
    assert lock["gcp"] == {
        "project": "shed-489901",
        "region": "us-central1",
        "service_account": "atlas-distill-runner@shed-489901.iam.gserviceaccount.com",
    }
    endpoint = lock["endpoints"][0]
    assert endpoint["mlip_id"] == "chgnet"
    assert endpoint["job"] == "mlip-cell-z2-chgnet"
    assert endpoint["ready"] is True
    assert endpoint["image_digest"].startswith("sha256:")
    assert endpoint["smoke"]["args"] == ["--help"]
    assert endpoint["smoke"]["status"] == "EXECUTION_SUCCEEDED"
    assert lock["heavy_soc_campaign_executed"] is False

    digest = hashlib.sha256(lock_path.read_bytes()).hexdigest()
    sidecar = lock_path.with_suffix(lock_path.suffix + ".sha256")
    assert sidecar.read_text(encoding="utf-8").split()[0] == digest
