#!/usr/bin/env python3
"""A manual discovery -> independent critique -> PI decision, with a private ledger.

Uses signed-in official CLIs on the named Mac and aledev. Does not launch any
experiments, publish research, or start a polling daemon. Never replays a job.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import importlib.util
import json
from pathlib import Path
import shlex
import sqlite3
import subprocess
import sys
import time
import zlib

RUNNER = Path(__file__).resolve().parent / "scientific-pi" / "pi_runner.py"
RUNNER_SOURCE = RUNNER.read_text()
spec = importlib.util.spec_from_file_location("scientific_pi_runner", RUNNER)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)
if RUNNER.read_text() != RUNNER_SOURCE:
    raise RuntimeError("Runner source changed during controller import; no work was launched")
CODEX = "/Applications/ChatGPT.app/Contents/Resources/codex-cli/CodexCLI.app/Contents/MacOS/codex"
HOMEBASE = "/Users/alexwelcing/Documents/Codex/2026-10-01/new-chat/outputs/homebase-command-center/homebase-cli"


def emit(value):
    print(json.dumps(value, ensure_ascii=False), flush=True)


REMOTE_WAIT_SECONDS = 360
REMOTE_POLL_SECONDS = 15
REMOTE_CALL_SECONDS = 25
TERMINAL_FAILURES = {
    "blocked", "failed", "timeout", "output_limit", "interrupted", "invalid_result", "policy_violation",
    "launch_unknown", "launch_failed", "transport_unknown", "status_unknown", "poll_timeout",
}


def remote_command(job, source, action="launch"):
    """Install once for launch; status loads only that exact reviewed source.

    The status program performs no installation, process launch, or model call.
    Job data is JSON, never executable text. Source stays pinned for the cycle.
    """
    if action not in ("launch", "status"):
        raise ValueError("unsupported remote operation")
    source_bytes = source.encode()
    data = {"action": action, "job_id": job["job_id"], "job_sha256": runner.digest(job),
            "source_sha256": hashlib.sha256(source_bytes).hexdigest(), "source_bytes": len(source_bytes)}
    if action == "launch":
        data.update(job=job, source=source)
    payload = base64.b64encode(zlib.compress(runner.canonical(data))).decode()
    program = """import base64,hashlib,importlib.util,json,os,pathlib,sys,zlib
sys.dont_write_bytecode=True
p=json.loads(zlib.decompress(base64.b64decode(PAYLOAD)))
root=pathlib.Path.home()/'.local/share/lupine-scientific-pi'
if root.is_symlink():raise RuntimeError('worker directory must not be a symlink')
if p['action']=='launch':
 os.umask(0o077)
 root.mkdir(parents=True,exist_ok=True,mode=0o700)
if not root.is_dir():raise RuntimeError('reviewed worker installation is missing')
script=root/('runner-'+p['source_sha256']+'.py')
if script.is_symlink():raise RuntimeError('reviewed worker must not be a symlink')
if p['action']=='launch' and not script.exists():
 source=p['source'].encode()
 if hashlib.sha256(source).hexdigest()!=p['source_sha256']:raise RuntimeError('source hash mismatch')
 with script.open('xb') as f:f.write(source)
with script.open('rb') as f:installed=f.read(p['source_bytes']+1)
if len(installed)!=p['source_bytes'] or hashlib.sha256(installed).hexdigest()!=p['source_sha256']:raise RuntimeError('installed source version mismatch')
spec=importlib.util.spec_from_file_location('scientific_pi',script)
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
if p['action']=='launch':
 job=mod.checked_job(p['job'])
 if job['job_id']!=p['job_id'] or mod.digest(job)!=p['job_sha256']:raise RuntimeError('job identity mismatch')
 value=mod.launch_job(job,root/'runs','/home/alex/.local/bin/claude')
else:
 value=mod.read_state(root/'runs',p['job_id'])
envelope=json.dumps({'action':p['action'],'job_id':p['job_id'],'job_sha256':p['job_sha256'],'source_sha256':p['source_sha256'],'value':value},ensure_ascii=False)
if len(envelope.encode())>60000:raise RuntimeError('research state exceeds transport bound; retained on aledev')
print(envelope)
""".replace("PAYLOAD", repr(payload))
    return "python3 -c " + shlex.quote(program)


def remote_critique(job, state):
    job = runner.checked_job(job)
    # Exclusive local intent precedes transmission. Neither transport loss nor
    # an expired controller wait is permission to launch the job again.
    folder = state / job["job_id"]
    folder.mkdir(mode=0o700)
    source = RUNNER_SOURCE
    job_hash = runner.digest(job)
    source_hash = hashlib.sha256(source.encode()).hexdigest()
    runner.write_json(folder / "manifest.json", {
        "job": job, "job_sha256": job_hash, "runner_source_sha256": source_hash,
        "automatic_retry": False, "transport": "Homebase pinned linux-laptop",
        "created_at": runner.now(), "remote_launch_intent": True,
    })
    started = runner.now()
    deadline = time.monotonic() + REMOTE_WAIT_SECONDS
    acknowledged = False
    sequence = 0

    def stopped(status, message, unknown=True):
        # This is controller evidence of an unresolved/failed handoff, never a
        # fabricated remote scientific completion or proof the remote stopped.
        receipt = {"job_id": job["job_id"], "job_sha256": job_hash, "provider": job["provider"],
                   "role": job["role"], "status": status, "completion_unknown": unknown,
                   "automatic_retry": False, "model_execution_started": None if unknown else False,
                   "session_id": None, "started_at": started, "finished_at": runner.now(),
                   "receipt_origin": "controller_transport", "error": message,
                   "runner_source_sha256": source_hash, "launch_acknowledged": acknowledged}
        runner.write_json(folder / "receipt.json", receipt)
        return receipt

    def request(action):
        nonlocal sequence
        sequence += 1
        command = remote_command(job, source, action)
        if len(command.encode()) > 100000:
            raise RuntimeError("research handoff exceeds command transport bound")
        process = runner.bounded_process([
            HOMEBASE, "exec", "linux-laptop", command, "--timeout", "20", "--label",
            "Launch one bounded independent critique" if action == "launch" else "Read the same independent critique status",
        ], b"", str(Path.cwd()), runner.cli_environment(), REMOTE_CALL_SECONDS, 262144)
        transport_path = folder / f"transport-{sequence:03d}-{action}.json"
        summary = {"action": action, "job_id": job["job_id"], "runner_source_sha256": source_hash,
                   "stop_reason": process["stop_reason"], "returncode": process["returncode"], "automatic_retry": False}
        runner.write_json(transport_path, summary)
        if process["stop_reason"] or process["returncode"] != 0:
            raise RuntimeError("Homebase transport did not complete; outcome unknown, no retry")
        transport = json.loads(process["stdout"])
        summary.update({key: transport.get(key) for key in ("exit_code", "timed_out", "output_truncated")})
        runner.write_json(transport_path, summary)
        if transport.get("timed_out") is not False or transport.get("output_truncated") is not False or transport.get("exit_code") != 0:
            raise RuntimeError("Homebase returned incomplete remote output; no retry")
        raw = transport.get("stdout")
        if not isinstance(raw, str) or len(raw.encode()) > 60000:
            raise RuntimeError("remote state is missing or exceeds its bound")
        envelope = json.loads(raw)
        expected = {"action": action, "job_id": job["job_id"], "job_sha256": job_hash, "source_sha256": source_hash}
        if not isinstance(envelope, dict) or any(envelope.get(key) != value for key, value in expected.items()):
            raise RuntimeError("remote state has a different job or reviewed source identity")
        value = envelope.get("value")
        if not isinstance(value, dict) or value.get("job_id") != job["job_id"]:
            raise RuntimeError("remote state has an invalid job identity")
        runner.write_json(folder / f"remote-{sequence:03d}-{action}.json", value)
        return value

    try:
        # Exactly one launch request. Even a definite launch failure is retained
        # under this immutable ID; a later action requires an explicit new job.
        launch = request("launch")
        if launch.get("job_sha256") != job_hash or launch.get("automatic_retry") is not False:
            return stopped("launch_unknown", "launch acknowledgment did not match the immutable job")
        if launch.get("status") != "launched":
            known_failure = launch.get("status") == "launch_failed"
            return stopped("launch_failed" if known_failure else "launch_unknown",
                           "remote launch was not acknowledged; no status polling or relaunch", not known_failure)
        if (type(launch.get("worker_pid")) is not int or launch["worker_pid"] <= 0
                or not isinstance(launch.get("launch_id"), str) or not runner.ID.fullmatch(launch["launch_id"])):
            return stopped("launch_unknown", "launch lacked a valid worker identity; no status polling")
        acknowledged = True
        runner.write_json(folder / "launch.json", launch)
        while True:
            if time.monotonic() + REMOTE_POLL_SECONDS + REMOTE_CALL_SECONDS > deadline:
                return stopped("poll_timeout", "controller wait expired; remote completion remains unknown, no replay")
            time.sleep(REMOTE_POLL_SECONDS)
            observed = request("status")
            saved_launch = observed.get("launch")
            if not isinstance(saved_launch, dict) or any(saved_launch.get(key) != launch.get(key) for key in (
                    "job_id", "job_sha256", "launch_id", "worker_pid", "automatic_retry")):
                raise RuntimeError("status does not belong to the acknowledged launch")
            remote_receipt, result = observed.get("receipt"), observed.get("result")
            if observed.get("status") == "pending":
                if remote_receipt is not None or result is not None or observed.get("completion_unknown") is not True:
                    raise RuntimeError("pending status contains inconsistent completion evidence")
                continue
            if not isinstance(remote_receipt, dict) or any(remote_receipt.get(key) != value for key, value in {
                "job_id": job["job_id"], "job_sha256": job_hash, "provider": job["provider"], "role": job["role"],
            }.items()):
                raise RuntimeError("remote receipt does not match the dispatched research job")
            status = remote_receipt.get("status")
            if observed.get("status") != status or observed.get("completion_unknown") is not remote_receipt.get("completion_unknown"):
                raise RuntimeError("remote receipt and status disagree")
            if remote_receipt.get("automatic_retry") is not False or type(remote_receipt.get("completion_unknown")) is not bool:
                raise RuntimeError("remote receipt has invalid completion metadata")
            if status == "completed":
                if (remote_receipt["completion_unknown"] is not False or remote_receipt.get("model_execution_started") is not True
                        or remote_receipt.get("returncode") != 0 or remote_receipt.get("stop_reason") is not None
                        or not remote_receipt.get("session_id")):
                    raise RuntimeError("remote completion lacks verified session evidence")
                runner.scientific_checks(result, job)
                if remote_receipt.get("result_sha256") != runner.digest(result):
                    raise RuntimeError("remote scientific result hash mismatch")
                runner.write_json(folder / "result.json", result)
            elif status not in TERMINAL_FAILURES or result is not None:
                raise RuntimeError("remote state has no recognized terminal receipt")
            runner.write_json(folder / "receipt.json", remote_receipt)
            return remote_receipt
    except (Exception, KeyboardInterrupt) as exc:
        return stopped("status_unknown" if acknowledged else "launch_unknown",
                       f"{'Status' if acknowledged else 'Launch'} stopped: {str(exc)[:500]}; no automatic retry")


def read_manifest(state, job_id):
    if not isinstance(job_id, str) or not runner.ID.fullmatch(job_id):
        raise ValueError("job id must be a safe identifier")
    folder = state / job_id
    if folder.is_symlink():
        raise RuntimeError("Saved job must be a real directory within the state directory")
    manifest = json.loads((folder / "manifest.json").read_text())
    job = runner.checked_job(manifest["job"])
    if job["job_id"] != job_id or manifest.get("job_sha256") != runner.digest(job):
        raise RuntimeError("Saved manifest job identity or hash mismatch")
    return job


def read_receipt(state, job_id):
    job = read_manifest(state, job_id)
    folder = state / job_id
    receipt = json.loads((folder / "receipt.json").read_text())
    if any(receipt.get(key) != expected for key, expected in {
        "job_id": job_id, "job_sha256": runner.digest(job),
        "provider": job["provider"], "role": job["role"],
    }.items()):
        raise RuntimeError("Saved receipt does not match the job manifest")
    return job, receipt


def read_completed(state, job_id):
    job, receipt = read_receipt(state, job_id)
    if (receipt.get("status") != "completed" or receipt.get("completion_unknown") is not False
            or receipt.get("model_execution_started") is not True
            or receipt.get("automatic_retry") is not False or not receipt.get("session_id")):
        raise RuntimeError(f"{job_id} did not complete; cycle stopped without replay")
    result = json.loads((state / job_id / "result.json").read_text())
    if receipt["result_sha256"] != runner.digest(result):
        raise RuntimeError("Saved result hash mismatch")
    runner.scientific_checks(result, job)
    return receipt, result


def validate_adopted_discovery(state, job_id, brief):
    job = read_manifest(state, job_id)
    expected = {"question": brief["question"], "context": brief["context"],
                "provider": "codex", "role": "proposer", "tool_mode": "web",
                "machine_id": "homebase-command-center"}
    if any(job[key] != value for key, value in expected.items()):
        raise RuntimeError("Existing discovery does not match this brief and discovery role")
    read_completed(state, job_id)


def run_cycle(brief, state, cycle_id, adopt_discovery=None):
    if not runner.ID.fullmatch(cycle_id) or len(cycle_id) > 70:
        raise ValueError("cycle-id must be a safe identifier of at most 70 characters")
    state = state.resolve()
    if adopt_discovery is not None:
        validate_adopted_discovery(state, adopt_discovery, brief)
    state.mkdir(parents=True, exist_ok=True, mode=0o700)
    state.chmod(0o700)
    folder = state / (cycle_id + "-cycle")
    folder.mkdir(mode=0o700)  # Exclusive: reusing the cycle ID never starts work.
    runner.write_json(folder / "brief.json", brief)
    db_path = state / "pi-ledger.sqlite3"
    db = sqlite3.connect(db_path)
    db_path.chmod(0o600)
    db.executescript("""CREATE TABLE IF NOT EXISTS scientific_pi_cycles (
      cycle_id TEXT PRIMARY KEY, question TEXT NOT NULL, started_at TEXT NOT NULL,
      finished_at TEXT, status TEXT NOT NULL, decision_json TEXT, error TEXT);
      CREATE TABLE IF NOT EXISTS scientific_pi_stages (
      cycle_id TEXT NOT NULL, stage TEXT NOT NULL, job_id TEXT NOT NULL UNIQUE,
      receipt_json TEXT NOT NULL, result_json TEXT NOT NULL,
      PRIMARY KEY(cycle_id,stage));""")
    db.execute("INSERT INTO scientific_pi_cycles(cycle_id,question,started_at,status) VALUES(?,?,?,'running')",
               (cycle_id, brief["question"], runner.now()))
    db.commit()

    def save(stage, job_id):
        _, receipt = read_receipt(state, job_id)
        failed = receipt.get("status") in TERMINAL_FAILURES
        # Preserve an identity-checked failure even when there is no result file.
        # A terminal failure receipt never supplies scientific output, even if a
        # stale result file happens to exist. Unknown/completed receipts still
        # pass the full completion checks before they can enter the ledger.
        result = None
        if not failed:
            receipt, result = read_completed(state, job_id)
        db.execute("INSERT INTO scientific_pi_stages VALUES(?,?,?,?,?)", (cycle_id, stage, job_id,
                   json.dumps(receipt), json.dumps(result)))
        db.commit()
        emit({"stage": stage, "job_id": job_id, "status": receipt["status"],
              "session_id": receipt.get("session_id"),
              "completion_unknown": receipt.get("completion_unknown")})
        if failed:
            raise RuntimeError(f"{job_id} did not complete; cycle stopped without replay")
        return result

    base = {"schema_version": 1, "campaign_id": cycle_id, "question": brief["question"],
            "context": brief["context"], "model": None, "max_output_bytes": 524288, "max_turns": 8}
    try:
        discovery_id = adopt_discovery or cycle_id + "-discovery"
        if not adopt_discovery:
            runner.run_job({**base, "job_id": discovery_id, "machine_id": "homebase-command-center", "provider": "codex",
                            "role": "proposer", "tool_mode": "web", "timeout_seconds": 300, "review_of": None}, state, CODEX)
        discovery = save("discovery", discovery_id)
        review_of = {"job_id": discovery_id, "packet_sha256": runner.digest(discovery), "packet": discovery}
        critique_id = cycle_id + "-critique"
        job = runner.checked_job({**base, "job_id": critique_id, "machine_id": "aledev", "provider": "claude",
                  "role": "critic", "tool_mode": "none", "timeout_seconds": 300, "review_of": review_of})
        remote_critique(job, state)
        critique = save("independent_critique", critique_id)
        adjudication_id = cycle_id + "-decision"
        runner.run_job({**base, "job_id": adjudication_id, "machine_id": "homebase-command-center", "provider": "codex",
             "role": "adjudicator", "tool_mode": "none", "timeout_seconds": 180, "review_of": review_of,
             "critique_of": {"job_id": critique_id, "packet_sha256": runner.digest(critique), "packet": critique}}, state, CODEX)
        decision = save("pi_decision", adjudication_id)
        db.execute("UPDATE scientific_pi_cycles SET status='completed',finished_at=?,decision_json=? WHERE cycle_id=?",
                   (runner.now(), json.dumps(decision), cycle_id))
        db.commit()
        runner.write_json(folder / "decision.json", decision)
        emit({"cycle_id": cycle_id, "status": "completed", "ledger": str(db_path), "decision": str(folder / "decision.json"),
              "experiments": "not_started", "publication": "held"})
    except Exception as exc:
        db.execute("UPDATE scientific_pi_cycles SET status='stopped',finished_at=?,error=? WHERE cycle_id=?",
                   (runner.now(), str(exc)[:1000], cycle_id))
        db.commit()
        raise
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--brief", required=True, help="JSON with question and context")
    parser.add_argument("--state-dir", required=True)
    parser.add_argument("--cycle-id", required=True)
    parser.add_argument("--adopt-discovery", help="Use a matching completed local discovery; never rerun it")
    args = parser.parse_args()
    try:
        brief = json.loads(Path(args.brief).read_text())
        if set(brief) != {"question", "context"} or not all(isinstance(v, str) for v in brief.values()):
            raise ValueError("brief must contain only question and context strings")
        run_cycle(brief, Path(args.state_dir).expanduser(), args.cycle_id, args.adopt_discovery)
    except Exception as exc:
        emit({"error": str(exc), "automatic_retry": False})
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
