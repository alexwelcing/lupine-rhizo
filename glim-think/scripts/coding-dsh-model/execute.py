#!/usr/bin/env python3
"""Two explicit phases; only the model process receives the scoped capability."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time


def main():
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


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        # Never render a config-bearing exception, command environment or prompt.
        print('{"schema":"lupine.dsh-model-command.v1","status":"failed","automaticReplay":false}', flush=True)
        sys.exit(1)
