#!/usr/bin/env python3
"""Submit one Z3 model measurement to Cloud Run and capture its raw artifact.

The command is deliberately transport-only: the fixture defines the scientific
observable and candidate systems. It fails closed when the returned artifact
has a different model or row than requested.
"""

from __future__ import annotations

import argparse
import json
import math
import pathlib
import re
import subprocess
import sys
from dataclasses import dataclass
from typing import Any, Sequence

PROJECT = "shed-489901"
REGION = "us-central1"
DEFAULT_MANIFEST = pathlib.Path("campaigns/v1/z3.campaign-manifest.v1.json")
DEFAULT_OUTPUT_ROOT = "gs://shed-489901-atlas-outputs/z3-campaign/raw"
SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


@dataclass(frozen=True)
class Endpoint:
    model_id: str
    job: str


ENDPOINTS = {
    endpoint.model_id: endpoint
    for endpoint in (
        Endpoint("chgnet", "mlip-cell-chgnet"),
        Endpoint("mace-mp-small", "mlip-cell-mace-mp-small"),
        Endpoint("mace-mp-medium", "mlip-cell-mace-mp-medium"),
        Endpoint("mace-mpa-0-medium", "mlip-cell-mace-mpa-0-medium"),
    )
}


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--model-id", required=True, choices=sorted(ENDPOINTS))
    result.add_argument("--fixture-url", required=True, help="Single-candidate fixture manifest (gs:// or HTTPS).")
    result.add_argument("--candidate-id", required=True)
    result.add_argument("--run-id", required=True)
    result.add_argument("--row-id", default="adsorption_energy")
    result.add_argument("--campaign-manifest", type=pathlib.Path, default=DEFAULT_MANIFEST)
    result.add_argument("--artifact-prefix", help="Defaults to the content-separated Z3 raw-output prefix.")
    result.add_argument("--capture-dir", type=pathlib.Path, help="Download and verify cell_result.json here.")
    result.add_argument("--project", default=PROJECT)
    result.add_argument("--region", default=REGION)
    result.add_argument("--dry-run", action="store_true")
    return result


def require_safe_id(label: str, value: str) -> None:
    if not SAFE_ID.fullmatch(value):
        raise ValueError(f"{label} must match {SAFE_ID.pattern!r}: {value!r}")


def load_campaign(path: pathlib.Path) -> dict[str, Any]:
    campaign = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(campaign, dict) or not isinstance(campaign.get("available_models"), list):
        raise ValueError(f"invalid campaign manifest: {path}")
    return campaign


def validate_model(campaign: dict[str, Any], model_id: str) -> dict[str, Any]:
    matches = [model for model in campaign["available_models"] if model.get("model_id") == model_id]
    if len(matches) != 1:
        raise ValueError(f"model {model_id!r} is not uniquely declared by the campaign manifest")
    model = matches[0]
    if not isinstance(model.get("artifact_hash"), str) or not model["artifact_hash"].startswith("sha256:"):
        raise ValueError(f"model {model_id!r} has no content-addressed artifact_hash")
    return model


def artifact_prefix(args: argparse.Namespace) -> str:
    if args.artifact_prefix:
        return args.artifact_prefix.rstrip("/")
    return "/".join(
        (
            DEFAULT_OUTPUT_ROOT,
            args.run_id,
            args.model_id,
            args.candidate_id,
            args.row_id,
        )
    )


def execution_command(args: argparse.Namespace, prefix: str) -> list[str]:
    endpoint = ENDPOINTS[args.model_id]
    cell_id = f"{args.run_id}:{args.row_id}:{args.model_id}:{args.candidate_id}"
    runner_args = [
        "run-cell",
        "--run-id",
        args.run_id,
        "--campaign-id",
        "discovery.round-4.z3-adsorption.v1",
        "--cell-id",
        cell_id,
        "--row-id",
        args.row_id,
        "--mlip-id",
        args.model_id,
        "--manifest-url",
        args.fixture_url,
        "--artifact-prefix",
        prefix,
        "--local-jsonl",
        "/tmp/z3-measurement-beats.jsonl",
    ]
    return [
        "gcloud",
        "run",
        "jobs",
        "execute",
        endpoint.job,
        f"--project={args.project}",
        f"--region={args.region}",
        "--wait",
        "--args=" + ",".join(runner_args),
    ]


def collect_artifact(args: argparse.Namespace, prefix: str) -> pathlib.Path | None:
    if args.capture_dir is None:
        return None
    args.capture_dir.mkdir(parents=True, exist_ok=True)
    destination = args.capture_dir / f"{args.candidate_id}.{args.model_id}.cell_result.json"
    subprocess.run(
        ["gcloud", "storage", "cp", f"{prefix}/cell_result.json", str(destination)],
        check=True,
    )
    payload = json.loads(destination.read_text(encoding="utf-8"))
    expected = {
        "schema": "lupine.mlip.cell_artifact.v1",
        "mlip_id": args.model_id,
        "row_id": args.row_id,
    }
    mismatches = {key: (expected_value, payload.get(key)) for key, expected_value in expected.items() if payload.get(key) != expected_value}
    if mismatches:
        raise ValueError(f"captured artifact does not match request: {mismatches}")
    if not isinstance(payload.get("predictions"), list) or not payload["predictions"]:
        raise ValueError("captured artifact contains no raw predictions")
    if args.row_id == "adsorption_energy":
        matching = [
            prediction
            for prediction in payload["predictions"]
            if prediction.get("candidate_id") == args.candidate_id
        ]
        if len(matching) != 1:
            raise ValueError(
                "captured artifact must contain exactly one prediction for "
                f"candidate {args.candidate_id!r}; found {len(matching)}"
            )
        prediction = matching[0]
        energy = prediction.get("adsorption_energy_ev")
        if (
            prediction.get("status") != "completed"
            or not isinstance(energy, (int, float))
            or not math.isfinite(float(energy))
        ):
            raise ValueError(
                "captured adsorption prediction is not completed with a finite "
                "adsorption_energy_ev"
            )
    return destination


def run(argv: Sequence[str] | None = None) -> int:
    args = parser().parse_args(argv)
    for label in ("candidate_id", "run_id", "row_id"):
        require_safe_id(label, getattr(args, label))
    campaign = load_campaign(args.campaign_manifest)
    model = validate_model(campaign, args.model_id)
    prefix = artifact_prefix(args)
    command = execution_command(args, prefix)
    request = {
        "campaign_id": campaign.get("campaign_id"),
        "campaign_content_hash": campaign.get("content_hash"),
        "model": model,
        "endpoint": {
            "project": args.project,
            "region": args.region,
            "job": ENDPOINTS[args.model_id].job,
        },
        "candidate_id": args.candidate_id,
        "row_id": args.row_id,
        "fixture_url": args.fixture_url,
        "artifact_prefix": prefix,
        "command": command,
    }
    print(json.dumps(request, indent=2, sort_keys=True))
    if args.dry_run:
        return 0
    subprocess.run(command, check=True)
    captured = collect_artifact(args, prefix)
    if captured is not None:
        print(json.dumps({"captured_artifact": str(captured)}, sort_keys=True))
    return 0


def main() -> None:
    try:
        raise SystemExit(run())
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
