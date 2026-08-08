#!/usr/bin/env python3
"""Verify the Lean evidence manifest pins a revision that can actually reproduce it.

Originating incident (Codex P1 on PR #116, shipped to main via PR #117):
`config/lean_build_evidence.json` marked the rounded-gate theorems as built while
`proof_revision` still identified `c0b52e7`, a revision whose SharpLicense.lean
contained none of them. An auditor resolving the pinned revision got source that
could not reproduce the advertised module hashes or theorem inventory, so formal
evidence was attributed to the wrong commit. Nothing in CI noticed, because every
field was internally well-formed — the manifest was simply about a different tree
than the one it named.

This is a ratchet, not a fence: it forbids a state already known to be wrong
(manifest disagrees with its own pinned revision) and is silent about anything
else. Adding proofs, modules or gates never trips it. Only a stale pin does.

Checks, in order of how badly each would corrupt the evidence chain:
  1. proof_revision resolves to a commit in this repository
  2. every module's source_hash matches that file's content AT the pinned revision
  3. every theorem the manifest marks built is present in that revision's source
  4. the pinned revision is an ancestor of HEAD (so it survives on main and cannot
     be garbage-collected with a deleted branch)

Check 4 is the one that catches the recurrence rather than the incident: pinning a
feature-branch tip passes 1-3 today and silently rots when the branch is squashed
away. It reports rather than fails when HEAD is unrelated (fresh clone, detached
CI checkout), because that is an environment fact, not a defect in the manifest.

Usage:  python3 tools/check_evidence_pin.py [--manifest config/lean_build_evidence.json]
Exit 0 = manifest is reproducible from what it pins.  Exit 1 = it is not.
"""
import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

# Lean identifiers admit primes, bangs, questions and unicode subscripts/greek, so
# `\b` is the wrong boundary twice over: it rejects a present `distToSet_nonneg'`
# (no word boundary after the quote), and it lets `foo` match inside `foo'`, which
# would mask a genuinely missing primed theorem behind its unprimed neighbour.
_ID = r"[A-Za-z0-9_'!?₀-ₜͰ-Ͽ]"


def declared(leaf: str, text: str) -> bool:
    return re.search(rf"(?<!{_ID}){re.escape(leaf)}(?!{_ID})", text) is not None


def git(*args, binary=False):
    """Return stdout, or None when git itself refuses (missing object, bad path)."""
    out = subprocess.run(
        ["git", "-C", str(REPO), *args],
        capture_output=True,
        timeout=120,
    )
    if out.returncode != 0:
        return None
    return out.stdout if binary else out.stdout.decode("utf-8", "replace")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default="config/lean_build_evidence.json")
    args = ap.parse_args()

    path = REPO / args.manifest
    if not path.exists():
        print(f"SKIP no manifest at {args.manifest}")
        return 0
    manifest = json.loads(path.read_text())
    rev = (manifest.get("proof_revision") or "").strip()
    modules = manifest.get("modules") or []
    print(f"manifest {args.manifest}")
    print(f"  pins    {rev[:12] or '(none)'}  ·  {len(modules)} module(s)")

    if not re.fullmatch(r"[0-9a-f]{40}", rev):
        print(f"FAIL proof_revision is not a full 40-hex sha: {rev!r}")
        return 1

    # 1. the pinned commit must exist here at all. A shallow CI clone legitimately
    # lacks it, and so does a fresh clone when the pinned revision was a feature
    # branch that has since been deleted — GitHub keeps those objects reachable
    # under refs/pull/N/head, but no default fetch pulls them. Try before failing,
    # so this reports genuine provenance loss rather than clone depth.
    if git("cat-file", "-e", f"{rev}^{{commit}}") is None:
        print(f"  fetch   {rev[:12]} not present locally, fetching…")
        git("fetch", "--quiet", "--depth=1", "origin", rev)
    if git("cat-file", "-e", f"{rev}^{{commit}}") is None:
        git("fetch", "--quiet", "origin", "+refs/pull/*/head:refs/remotes/origin/pr/*")
    if git("cat-file", "-e", f"{rev}^{{commit}}") is None:
        print(f"FAIL pinned revision {rev[:12]} is not a commit obtainable from this remote.")
        print("     Evidence names a tree nobody can fetch, so no auditor can ever")
        print("     reproduce it. Regenerate from a revision reachable on main.")
        return 1

    # 2. + 3. the pinned tree must reproduce every hash and contain every theorem
    hash_mismatch, missing_src, missing_thm = [], [], []
    for m in modules:
        src = m.get("source_path")
        if not src:
            continue
        blob = git("show", f"{rev}:{src}", binary=True)
        if blob is None:
            missing_src.append(src)
            continue
        if m.get("source_hash") and hashlib.sha256(blob).hexdigest() != m["source_hash"]:
            hash_mismatch.append(src)
            continue  # content differs; theorem check below would be noise
        text = blob.decode("utf-8", "replace")
        for t in m.get("theorems") or []:
            if not (t.get("name") and m.get("built")):
                continue
            leaf = t["name"].rsplit(".", 1)[-1]
            if not declared(leaf, text):
                missing_thm.append(f"{leaf} claimed built in {src}")

    for label, items, why in (
        ("source file absent at pinned revision", missing_src,
         "the manifest inventories modules that revision does not have"),
        ("source_hash does not match pinned revision", hash_mismatch,
         "the advertised module hash is not reproducible from what is pinned"),
        ("theorem claimed built but not in pinned source", missing_thm,
         "formal evidence is attributed to a commit lacking the proof"),
    ):
        if items:
            print(f"FAIL {len(items)} × {label} — {why}")
            for i in items[:8]:
                print(f"       {i}")
            if len(items) > 8:
                print(f"       … and {len(items) - 8} more")
            print(f"     Fix: regenerate from a committed revision that contains them:")
            print(f"       python3 tools/build_lean_evidence.py --out {args.manifest}")
            return 1

    print(f"  OK      all {len(modules)} module hashes and theorem claims reproduce from {rev[:12]}")

    # 4. reachability — a warning, because HEAD is an environment fact
    head = (git("rev-parse", "HEAD") or "").strip()
    if head and git("merge-base", "--is-ancestor", rev, "HEAD") is None:
        print(f"  WARN    {rev[:12]} is not an ancestor of HEAD ({head[:12]}).")
        print("          It reproduces today, but a pin outside main's history is lost")
        print("          when its branch is squashed or deleted. Re-pin after merge.")
    elif head:
        print(f"  OK      {rev[:12]} is an ancestor of HEAD — survives on main")
    return 0


if __name__ == "__main__":
    sys.exit(main())
