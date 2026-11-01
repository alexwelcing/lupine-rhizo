#!/usr/bin/env python3
"""Two explicit phases; only the model process receives the scoped capability."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time


ARTIFACT_NAMES = (
    "dsh-qualification.json", "dsh-package-lock.json", "dsh-installed-identities.json",
    "dsh-build-identity.json", "dsh-pinned-snapshot.json", "dsh-source-lock.json",
    "model-prepared.json", "model-runtime-result.json", "model-worktree.patch",
    "repository-assessment.md", "repository-assessment.json",
)


def preserve_absences(root, command_exit):
    """Absent artifacts are explicit diagnostics, never substituted evidence."""
    output = root / ".lupine-coding-evidence"
    output.mkdir(exist_ok=True)
    missing = []
    for name in ARTIFACT_NAMES:
        target = output / name
        if target.exists():
            continue
        missing.append(name)
        value = {"schema": "lupine.coding-artifact-absent.v1", "artifact": name,
                 "produced": False, "reasonCode": "COMMAND_DID_NOT_PRODUCE_ARTIFACT",
                 "commandExitCode": command_exit, "assessmentAvailable": False,
                 "qualification": False, "automaticReplay": False}
        text = json.dumps(value, indent=2) + "\n"
        if name.endswith(".md"):
            text = "# Repository assessment not produced\n\nThis is an absence record, not a repository assessment.\n\n```json\n" + text + "```\n"
        # The .patch absence is also schema-labelled JSON, never a fabricated
        # empty/clean diff. Every existing artifact remains byte-for-byte intact.
        with target.open("x") as handle:
            handle.write(text)
    return missing


def run_phases():
    raw = os.environ.pop("LUPINE_CODING_MODEL_CONFIG_JSON", None)
    if raw is None or len(raw.encode()) > 8192:
        raise RuntimeError("Missing or oversized scoped model configuration")
    config = json.loads(raw)
    deadline = config.get("deadlineAtMs")
    now = int(time.time() * 1000)
    if type(deadline) is not int or not now < deadline <= now + 900000:
        raise RuntimeError("Invalid original coding deadline")
    root = Path.cwd().resolve()
    here = Path(__file__).resolve().parent
    clean = {"PATH": "/usr/local/bin:/usr/bin:/bin"}

    def remaining():
        seconds = (deadline - int(time.time() * 1000)) / 1000 - 15
        if seconds <= 0:
            raise RuntimeError("Original coding deadline exhausted")
        return seconds

    # Neither Node bootstrap nor Git/npm/build children receive the capability.
    prep = subprocess.run([sys.executable, str(here / "bootstrap-node.py")],
                          cwd=root, env=clean, timeout=min(850, remaining()), check=False)
    if prep.returncode != 0:
        raise RuntimeError("Model preparation failed; inference not started")
    prepared = json.loads((root / ".lupine-coding-evidence/model-prepared.json").read_text())
    if prepared.get("schema") != "lupine.dsh-model-prepared.v1" or prepared.get("targetRoot") != str(root):
        raise RuntimeError("Prepared runtime identity differs")
    node = Path(prepared["nodeExecutable"])
    if not node.is_absolute() or not node.is_file() or prepared.get("nodeVersion") != "v22.22.3":
        raise RuntimeError("Declared Node runtime missing")
    # The transport performs complete config validation before a broker request.
    model_env = {"PATH": str(node.parent) + ":/usr/local/bin:/usr/bin:/bin",
                 "LUPINE_CODING_MODEL_CONFIG_JSON": raw}
    model = subprocess.run([str(node), str(here / "run-agent.mjs")],
                           cwd=root, env=model_env, timeout=remaining(), check=False)
    return model.returncode


def main():
    root = Path.cwd().resolve()
    command_exit = None
    try:
        command_exit = run_phases()
    finally:
        missing = preserve_absences(root, command_exit)
    # A process exit 0 without its required deliverables is not task success.
    return 1 if command_exit == 0 and missing else command_exit


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        # Never render a config-bearing exception, command environment or prompt.
        print('{"schema":"lupine.dsh-model-command.v1","status":"failed","automaticReplay":false}', flush=True)
        sys.exit(1)
