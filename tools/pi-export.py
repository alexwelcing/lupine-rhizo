#!/usr/bin/env python3
"""Export one verified private PI cycle for operator import. No network or execution."""
import argparse
import importlib.util
import json
from pathlib import Path
import re
import sqlite3
import stat
import sys

sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location("pi_cycle_export_source", Path(__file__).with_name("pi-cycle.py"))
cycle = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cycle)
runner = cycle.runner
MAX_BYTES = 196608
STAGES = [("discovery", "discovery", "codex", "proposer", "homebase-command-center", "mac"),
          ("independent_critique", "critique", "claude", "critic", "aledev", "aledev"),
          ("pi_decision", "decision", "codex", "adjudicator", "homebase-command-center", "mac")]
PRIVATE_PATH = re.compile(r"(?:/Users/|/home/|/private/(?:tmp|var)/|[A-Za-z]:[\\/](?:Users|Documents and Settings)[\\/])")


def read_json(path, limit=2_000_000):
    metadata = path.lstat()
    if not stat.S_ISREG(metadata.st_mode) or metadata.st_size > limit:
        raise ValueError("Saved evidence must be a bounded regular file")
    with path.open("rb") as stream:
        data = stream.read(limit + 1)
    if len(data) > limit:
        raise ValueError("Saved evidence exceeds its byte limit")
    return json.loads(data)


def saved_job(state, job_id):
    if not runner.ID.fullmatch(job_id):
        raise ValueError("Invalid saved job ID")
    folder = state / job_id
    if folder.is_symlink():
        raise ValueError("Saved job must be within the state directory")
    manifest = read_json(folder / "manifest.json")
    job = runner.checked_job(manifest["job"])
    if job["job_id"] != job_id or manifest.get("job_sha256") != runner.digest(job):
        raise ValueError("Saved job identity or fingerprint mismatch")
    return job


def safe_receipt(receipt):
    model = receipt.get("model") or receipt.get("model_requested")
    if isinstance(model, list) and all(isinstance(item, str) for item in model):
        model = ", ".join(model)
    if model is not None and (not isinstance(model, str) or not 0 < len(model) <= 600):
        raise ValueError("Invalid saved model identity")
    return {"jobId": receipt["job_id"], "jobSha256": receipt["job_sha256"], "status": receipt["status"],
            "completionUnknown": receipt.get("completion_unknown") is not False,
            "automaticRetry": False, "modelExecutionStarted": receipt.get("model_execution_started") is True,
            "sessionId": receipt.get("session_id"), "model": model,
            "startedAt": receipt.get("started_at"), "finishedAt": receipt.get("finished_at"),
            "resultSha256": receipt.get("result_sha256") if receipt["status"] == "completed" else None,
            "receiptOrigin": "controller_transport" if receipt.get("receipt_origin") == "controller_transport" else "local_cli"}


def export_cycle(state, cycle_id):
    state = Path(state).resolve()
    if not runner.ID.fullmatch(cycle_id):
        raise ValueError("Invalid cycle ID")
    # Read a consistent ledger snapshot, never create a missing database.
    db = sqlite3.connect((state / "pi-ledger.sqlite3").as_uri() + "?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    try:
        db.execute("BEGIN")
        row = db.execute("SELECT * FROM scientific_pi_cycles WHERE cycle_id=?", (cycle_id,)).fetchone()
        if row is None:
            raise ValueError("Cycle is not recorded in the private ledger")
        saved = {r["stage"]: r for r in db.execute("SELECT * FROM scientific_pi_stages WHERE cycle_id=?", (cycle_id,))}
    finally:
        db.close()
    if row["status"] not in ("running", "stopped", "completed"):
        raise ValueError("Unknown cycle status")
    stages = []
    packets = {}
    for name, suffix, provider, role, machine, public_machine in STAGES:
        stored = saved.get(name)
        job_id = stored["job_id"] if stored else cycle_id + "-" + suffix
        stage = {"stage": name, "jobId": None, "provider": provider, "role": role,
                 "machineId": None, "status": "not_started", "receipt": None, "packetJson": None}
        folder = state / job_id
        if stored is None and not (folder / "manifest.json").exists():
            stages.append(stage)
            continue
        job = saved_job(state, job_id)
        expected = {"provider": provider, "role": role, "machine_id": machine, "question": row["question"],
                    "tool_mode": "web" if role == "proposer" else "none"}
        if any(job.get(key) != value for key, value in expected.items()):
            raise ValueError("Saved job does not match this cycle's scientific role")
        if role != "proposer" and job["campaign_id"] != cycle_id:
            raise ValueError("Saved job belongs to another cycle")
        stage.update(jobId=job_id, machineId=public_machine, status="pending")
        if not (folder / "receipt.json").exists():
            if stored is not None:
                raise ValueError("Ledger receipt is missing from its job directory")
            # A manifest reserves identity, not completion or model activity.
            stages.append(stage)
            continue
        receipt = read_json(folder / "receipt.json", 131072)
        if stored is not None and receipt != json.loads(stored["receipt_json"]):
            raise ValueError("Local receipt differs from the durable ledger")
        expected_receipt = {"job_id": job_id, "job_sha256": runner.digest(job), "provider": provider, "role": role, "automatic_retry": False}
        if any(receipt.get(key) != value for key, value in expected_receipt.items()):
            raise ValueError("Receipt identity or fingerprint mismatch")
        status = receipt.get("status")
        if status != "completed" and status not in cycle.TERMINAL_FAILURES:
            raise ValueError("Unknown terminal receipt status")
        stage.update(status=status, receipt=safe_receipt(receipt))
        if status == "completed":
            if receipt.get("completion_unknown") is not False or receipt.get("model_execution_started") is not True or not receipt.get("session_id") or receipt.get("receipt_origin") == "controller_transport" or receipt.get("returncode") != 0 or receipt.get("stop_reason") is not None:
                raise ValueError("Receipt cannot prove completed research")
            packet = read_json(folder / "result.json", 49153)
            runner.scientific_checks(packet, job)
            if runner.digest(packet) != receipt.get("result_sha256"):
                raise ValueError("Result fingerprint mismatch")
            if stored is not None and packet != json.loads(stored["result_json"]):
                raise ValueError("Local packet differs from the durable ledger")
            if role != "proposer":
                previous = packets.get("discovery")
                if previous is None or job["review_of"]["job_id"] != stages[0]["jobId"] or job["review_of"]["packet_sha256"] != runner.digest(previous):
                    raise ValueError("Review does not match this cycle's discovery")
            if role == "adjudicator":
                previous = packets.get("independent_critique")
                if previous is None or job["critique_of"]["job_id"] != stages[1]["jobId"] or job["critique_of"]["packet_sha256"] != runner.digest(previous):
                    raise ValueError("Decision does not match this cycle's critique")
            packets[name] = packet
            stage["packetJson"] = runner.canonical(packet).decode()
        elif stored is not None and json.loads(stored["result_json"]) is not None:
            raise ValueError("Failed stage unexpectedly contains a result")
        stages.append(stage)
    if set(saved) - {s[0] for s in STAGES}:
        raise ValueError("Unexpected stage in ledger")
    if row["status"] == "completed":
        if any(s["status"] != "completed" for s in stages) or json.loads(row["decision_json"]) != packets.get("pi_decision"):
            raise ValueError("Completed ledger cycle lacks matching scientific packets")
    result = {"schemaVersion": 1, "id": cycle_id, "question": row["question"], "status": row["status"],
              "startedAt": row["started_at"], "finishedAt": row["finished_at"], "capturedAt": runner.now(),
              # Raw stop messages can contain host paths or transport diagnostics.
              "error": "Cycle stopped without automatic retry. See the stage receipt statuses; detailed diagnostics remain local." if row["status"] == "stopped" else None,
              "experiment": "not_started", "publication": "held", "stages": stages}
    encoded = runner.canonical(result)
    if len(encoded) > MAX_BYTES:
        raise ValueError("Research snapshot exceeds the import size limit")
    if PRIVATE_PATH.search(encoded.decode()):
        raise ValueError("Research content contains a private host path; review locally before any import")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state-dir", required=True)
    parser.add_argument("--cycle-id", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    try:
        result = export_cycle(Path(args.state_dir).expanduser(), args.cycle_id)
        output = Path(args.output).expanduser()
        # Exclusive output avoids accidentally replacing reviewed or immutable evidence.
        with output.open("xb") as stream:
            output.chmod(0o600)
            stream.write(runner.canonical(result) + b"\n")
        print(json.dumps({"id": result["id"], "status": result["status"], "stages": [{"stage": s["stage"], "status": s["status"]} for s in result["stages"]], "uploaded": False}))
        return 0
    except Exception as exc:
        # No transport logs, source packets or private paths in command output.
        print(json.dumps({"error": type(exc).__name__, "exported": False, "uploaded": False}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
