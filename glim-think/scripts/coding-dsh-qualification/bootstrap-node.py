#!/usr/bin/env python3
"""One explicit pinned runtime download; no fallback, login or provider setup."""
import hashlib
import json
import os
from pathlib import Path
import platform
import signal
import sys
import tarfile
import tempfile
import time
import urllib.request

VERSION = "v22.22.3"
ARCHIVE = "node-v22.22.3-linux-x64.tar.gz"
URL = "https://nodejs.org/dist/" + VERSION + "/" + ARCHIVE
ARCHIVE_SHA256 = "c7a10d6816da8eaaa7534dd73c71c6e2b2c391dbbf845e364902d156615dd1b8"
UPSTREAM_SUMS_SHA256 = "b99296390cb403042da79c14d81e681076a9ac03af062d13f840dadc4ec751b3"
MAX_DOWNLOAD = 64 * 1024 * 1024
MAX_EXTRACTED = 512 * 1024 * 1024
MAX_MEMBERS = 32768
TOTAL_SECONDS = 850
PREP_SECONDS = 50
DOWNLOAD_SECONDS = 40


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise RuntimeError("Pinned Node archive redirect refused")


def sha_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def expired(_signum, _frame):
    raise TimeoutError("Pinned Node bootstrap preparation deadline exhausted")


def download(destination):
    # No environment proxy, HTTP downgrade or redirect is accepted. This one
    # request uses Python's default verified HTTPS context and system CA trust.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    with opener.open(urllib.request.Request(URL, method="GET"), timeout=DOWNLOAD_SECONDS) as response:
        if response.status != 200 or response.geturl() != URL:
            raise RuntimeError("Unexpected pinned Node archive response")
        declared = response.headers.get("Content-Length")
        if declared is not None and (not declared.isdigit() or int(declared) > MAX_DOWNLOAD):
            raise RuntimeError("Pinned Node archive exceeds declared download cap")
        total = 0
        with destination.open("xb") as target:
            while True:
                block = response.read(1024 * 1024)
                if not block:
                    break
                total += len(block)
                if total > MAX_DOWNLOAD:
                    raise RuntimeError("Pinned Node archive exceeds streamed download cap")
                target.write(block)
        if declared is not None and total != int(declared):
            raise RuntimeError("Pinned Node archive length mismatch")
        return total


def extract(archive, target):
    if not hasattr(tarfile, "data_filter"):
        raise RuntimeError("Python tarfile data filter required; no unsafe extraction fallback")
    expected_top = ARCHIVE.removesuffix(".tar.gz")
    with tarfile.open(archive, "r:gz") as source:
        members = []
        expanded = 0
        for member in source:
            if len(members) >= MAX_MEMBERS:
                raise RuntimeError("Node archive member cap exceeded")
            parts = Path(member.name).parts
            if not parts or parts[0] != expected_top or ".." in parts:
                raise RuntimeError("Unexpected Node archive path")
            if member.isfile():
                expanded += member.size
                if expanded > MAX_EXTRACTED:
                    raise RuntimeError("Node archive expanded-byte cap exceeded")
            members.append(member)
        source.extractall(target, members=members, filter="data")
    executable = target / expected_top / "bin" / "node"
    if not executable.is_file() or executable.is_symlink() or not os.access(executable, os.X_OK):
        raise RuntimeError("Pinned Node executable absent or unexpected")
    return executable, len(members), expanded


def main():
    started_mono = time.monotonic()
    started_epoch_ms = int(time.time() * 1000)
    here = Path(__file__).resolve().parent
    identity = {
        "schema": "lupine.pinned-node-bootstrap.v1", "status": "preparing",
        "version": VERSION, "archiveUrl": URL, "archiveSha256": ARCHIVE_SHA256,
        "upstreamChecksumReceiptSha256": UPSTREAM_SUMS_SHA256,
        "startedAtEpochMs": started_epoch_ms,
        "absoluteDeadlineEpochMs": started_epoch_ms + TOTAL_SECONDS * 1000,
        "totalBudgetSeconds": TOTAL_SECONDS, "preparationBudgetSeconds": PREP_SECONDS,
        "downloadBudgetSeconds": DOWNLOAD_SECONDS, "downloadAttempts": 0,
        "downloadBytes": None, "runtimeExecuted": False, "providerExecuted": False,
    }
    scratch = Path(tempfile.mkdtemp(prefix="lupine-dsh-node-"))
    previous = signal.signal(signal.SIGALRM, expired)
    try:
        signal.setitimer(signal.ITIMER_REAL, PREP_SECONDS)
        if platform.system() != "Linux" or platform.machine() not in ("x86_64", "amd64"):
            raise RuntimeError("Pinned Node bootstrap requires Linux x86-64; no platform fallback")
        archive = scratch / ARCHIVE
        identity["downloadAttempts"] = 1
        # The signal limits the entire single download, including repeated reads.
        signal.setitimer(signal.ITIMER_REAL, min(DOWNLOAD_SECONDS, PREP_SECONDS - (time.monotonic() - started_mono)))
        identity["downloadBytes"] = download(archive)
        remaining_prep = PREP_SECONDS - (time.monotonic() - started_mono)
        if remaining_prep <= 0:
            raise TimeoutError("Pinned Node preparation deadline exhausted")
        signal.setitimer(signal.ITIMER_REAL, remaining_prep)
        if sha_file(archive) != ARCHIVE_SHA256:
            raise RuntimeError("Pinned Node archive SHA256 mismatch")
        executable, members, expanded = extract(archive, scratch)
        identity.update({"status": "runtime-prepared", "executable": str(executable),
                         "executableSha256": sha_file(executable), "archiveMembers": members,
                         "expandedFileBytes": expanded,
                         "preparationElapsedMs": round((time.monotonic() - started_mono) * 1000)})
        if identity["preparationElapsedMs"] >= PREP_SECONDS * 1000:
            raise TimeoutError("Pinned Node preparation finished after deadline")
        identity_file = scratch / "bootstrap-identity.json"
        identity_file.write_text(json.dumps(identity, indent=2) + "\n")
        print(json.dumps(identity), flush=True)
        # The pinned distribution's npm uses this same pinned Node through PATH.
        child_env = {"PATH": str(executable.parent) + ":/usr/local/bin:/usr/bin:/bin",
                     "LUPINE_DSH_BOOTSTRAP_IDENTITY": str(identity_file),
                     "LUPINE_DSH_DEADLINE_EPOCH_MS": str(identity["absoluteDeadlineEpochMs"])}
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)
        os.execve(str(executable), [str(executable), str(here / "qualify.mjs")], child_env)
    except Exception as error:
        signal.setitimer(signal.ITIMER_REAL, 0)
        identity.update({"status": "failed-runtime-bootstrap", "error": str(error)[:2048],
                         "preparationElapsedMs": round((time.monotonic() - started_mono) * 1000)})
        print(json.dumps(identity), flush=True)
        return 1
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)
    return 1


if __name__ == "__main__":
    sys.exit(main())
