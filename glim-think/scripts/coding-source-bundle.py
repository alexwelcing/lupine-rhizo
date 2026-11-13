#!/usr/bin/env python3
"""Export an exact commit and its complete tree, with explicit shallow history.

No working-tree/untracked files or historical parent objects are included. The
output is only admissible as git-shallow-bundle-v1, never as complete history.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import threading


def export(repository, commit, output):
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("An exact SHA-1 commit is required")
    output = Path(output).resolve()
    if output.exists() or Path(str(output) + ".partial").exists():
        raise ValueError("Refusing to replace an existing export")
    env = dict(os.environ, GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL="/dev/null",
               GIT_NO_LAZY_FETCH="1", GIT_NO_REPLACE_OBJECTS="1", GIT_TERMINAL_PROMPT="0")
    def git(*args):
        return subprocess.check_output(["git", "-C", str(repository), *args], env=env, timeout=30)
    if git("cat-file", "-t", commit).strip() != b"commit":
        raise ValueError("Pinned object is not a commit")
    tree = git("rev-parse", commit + "^{tree}").decode().strip()
    objects = git("rev-list", "--objects", "--no-object-names", commit + "^{tree}")
    lines = objects.decode().splitlines()
    if not lines or len(lines) > 100000 or any(not re.fullmatch(r"[0-9a-f]{40}", x) for x in lines):
        raise ValueError("Invalid or oversized tree inventory")
    free = shutil.disk_usage(output.parent).free
    maximum = min(256 * 1024 * 1024, free - 32 * 1024 * 1024)
    if maximum < 1024 * 1024:
        raise ValueError("Insufficient free space for a bounded export")
    partial = Path(str(output) + ".partial")
    digest = hashlib.sha256()
    count = 0
    process = None
    watchdog = None
    with tempfile.TemporaryFile() as inputs, tempfile.TemporaryFile() as errors:
        inputs.write(commit.encode() + b"\n" + objects)
        inputs.seek(0)
        with partial.open("xb") as target:
            os.chmod(partial, 0o600)
            def retain(data):
                nonlocal count
                count += len(data)
                if count > maximum:
                    raise ValueError("Export exceeded its storage bound; partial retained")
                target.write(data)
                digest.update(data)
            try:
                retain(b"# v2 git bundle\n" + commit.encode() + b" refs/heads/lupine-coding-snapshot\n\n")
                process = subprocess.Popen(["git", "-C", str(repository), "pack-objects", "--stdout",
                                            "--threads=1"], stdin=inputs, stdout=subprocess.PIPE,
                                           stderr=errors, env=env)
                watchdog = threading.Timer(120, process.kill)
                watchdog.start()
                while True:
                    block = process.stdout.read(1024 * 1024)
                    if not block:
                        break
                    retain(block)
                if process.wait(timeout=30) != 0:
                    errors.seek(0)
                    raise RuntimeError(errors.read(4096).decode(errors="replace"))
                target.flush()
                os.fsync(target.fileno())
            finally:
                if watchdog is not None:
                    watchdog.cancel()
                if process is not None and process.poll() is None:
                    process.kill()
                    process.wait()
    # Atomic, exclusive publication of a completed export.
    os.link(partial, output)
    partial.unlink()
    return {"schema": "lupine.coding-source-export.v1", "commit": commit, "tree": tree,
            "historyScope": "exact commit and complete tree; historical parents excluded",
            "treeObjectCount": len(lines), "path": str(output),
            "source": {"kind": "git-shallow-bundle-v1", "boundaryCommit": commit,
                       "artifactKey": "sources/" + digest.hexdigest() + ".bundle",
                       "sha256": digest.hexdigest(), "bytes": count}}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repository")
    parser.add_argument("commit")
    parser.add_argument("output")
    args = parser.parse_args()
    print(json.dumps(export(args.repository, args.commit, args.output), indent=2))
