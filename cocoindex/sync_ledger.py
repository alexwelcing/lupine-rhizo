#!/usr/bin/env python3
"""
Sync the DEPLOYED Library content from the public lupine-ledger repo, and
measure publication drift against this repo's export bundle.

lupine-ledger (https://github.com/alexwelcing/lupine-ledger) is the repo
that actually serves https://library.lupine.science — its content/latest/
is the deployed library-content.v1 bundle. The copy in this repo
(exports/library-content/latest) is what rhizo *intends* to publish next.
The two drift: articles pending publication, articles changed since the
last deploy, and articles live that a regenerated bundle dropped.

This script:
  1. shallow-clones (or updates) lupine-ledger into ./.cache/lupine-ledger —
     main.py then prefers the ledger's articles as the `published_article`
     source, so "published" means *deployed*, with the ledger commit as
     provenance;
  2. with --drift, diffs the two manifests (per-article sha256) and writes
     the summary to ./data/publication_drift.jsonl (kind="publication_drift")
     so "what is awaiting publication?" is a semantic query like any other.
     The record is timestamp-free and rewritten only on change, keeping the
     re-index incremental.

Usage:
    python sync_ledger.py            # clone/update the deployed content
    python sync_ledger.py --drift    # also diff + write the drift record
    python sync_ledger.py --no-fetch --drift   # offline: use existing cache
"""
from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
LEDGER_URL = "https://github.com/alexwelcing/lupine-ledger"
CACHE = HERE / ".cache" / "lupine-ledger"
LOCAL_BUNDLE = HERE.parent / "exports" / "library-content" / "latest"
DRIFT_OUT = HERE / "data" / "publication_drift.jsonl"


def sync(cache: pathlib.Path = CACHE) -> str | None:
    """Clone or fast-update the ledger repo. Returns the HEAD commit, or
    None if the sync failed (offline) — an existing cache stays usable."""
    try:
        if (cache / ".git").is_dir():
            subprocess.run(["git", "-C", str(cache), "fetch", "--depth", "1", "origin"],
                           check=True, capture_output=True, text=True, timeout=120)
            subprocess.run(["git", "-C", str(cache), "reset", "--hard", "FETCH_HEAD"],
                           check=True, capture_output=True, text=True, timeout=60)
        else:
            cache.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run(["git", "clone", "--depth", "1", LEDGER_URL, str(cache)],
                           check=True, capture_output=True, text=True, timeout=300)
        head = subprocess.run(["git", "-C", str(cache), "rev-parse", "HEAD"],
                              check=True, capture_output=True, text=True, timeout=30)
        return head.stdout.strip()
    except (subprocess.SubprocessError, OSError) as e:
        msg = getattr(e, "stderr", "") or str(e)
        print(f"[ledger] sync failed ({str(msg)[:300]})", file=sys.stderr)
        return None


def _manifest_files(root: pathlib.Path) -> tuple[dict, dict[str, str]]:
    """(manifest header info, {bundleSource: sha256}) for a bundle dir."""
    m = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    return m, {f["bundleSource"]: f["sha256"]
               for f in m.get("files", []) if f.get("bundleSource") and f.get("sha256")}


def manifest_diff(local: dict[str, str], deployed: dict[str, str]) -> dict[str, list[str]]:
    """Classify per-article drift between the pending bundle and the deploy."""
    return {
        "pending_publication": sorted(set(local) - set(deployed)),
        "deployed_only": sorted(set(deployed) - set(local)),
        "changed": sorted(k for k in set(local) & set(deployed) if local[k] != deployed[k]),
        "in_sync": sorted(k for k in set(local) & set(deployed) if local[k] == deployed[k]),
    }


def drift_record(local_info: dict, deployed_info: dict, diff: dict[str, list[str]]) -> dict:
    """One evidence record summarizing publication drift, in prose so it
    embeds well. Deterministic for a given manifest pair (no wall-clock)."""
    def _names(key: str) -> str:
        return ", ".join(p.removeprefix("articles/") for p in diff[key]) or "none"
    lsrc, dsrc = local_info.get("source", {}), deployed_info.get("source", {})
    text = (
        f"Publication drift between the pending library-content bundle "
        f"(generated {local_info.get('generatedAt')}, commit {lsrc.get('commit', '')[:8]}) "
        f"and the deployed Library at library.lupine.science "
        f"(generated {deployed_info.get('generatedAt')}, commit {dsrc.get('commit', '')[:8]}). "
        f"Articles awaiting publication ({len(diff['pending_publication'])}): "
        f"{_names('pending_publication')}. "
        f"Deployed but absent from the regenerated bundle ({len(diff['deployed_only'])}): "
        f"{_names('deployed_only')}. "
        f"Content changed since deploy ({len(diff['changed'])}): {_names('changed')}. "
        f"In sync: {len(diff['in_sync'])} articles."
    )
    return {
        "id": "publication-drift",
        "kind": "publication_drift",
        "ref_id": "publication-drift",
        "text": text,
        "metadata": {k: len(v) for k, v in diff.items()},
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--drift", action="store_true",
                    help="diff pending bundle vs deployed ledger; write the drift record")
    ap.add_argument("--no-fetch", action="store_true",
                    help="skip clone/pull; use the existing cache (offline)")
    args = ap.parse_args(argv)

    if not args.no_fetch:
        commit = sync()
        if commit:
            print(f"[ledger] deployed content at {CACHE} @ {commit[:12]}")
        elif not (CACHE / "content" / "latest" / "manifest.json").exists():
            print("[ledger] no cache and fetch failed — published_article source "
                  "falls back to the local bundle", file=sys.stderr)
            return 1

    if args.drift:
        deployed_root = CACHE / "content" / "latest"
        if not (deployed_root / "manifest.json").exists() or \
           not (LOCAL_BUNDLE / "manifest.json").exists():
            print("[ledger] need both manifests for --drift", file=sys.stderr)
            return 1
        local_info, local_files = _manifest_files(LOCAL_BUNDLE)
        deployed_info, deployed_files = _manifest_files(deployed_root)
        diff = manifest_diff(local_files, deployed_files)
        rec = drift_record(local_info, deployed_info, diff)
        for key in ("pending_publication", "deployed_only", "changed"):
            print(f"{key} ({len(diff[key])}):")
            for p in diff[key]:
                print(f"  {p}")
        print(f"in_sync: {len(diff['in_sync'])}")
        from fetch_site_content import write_if_changed
        if write_if_changed([rec], DRIFT_OUT):
            print(f"wrote drift record -> {DRIFT_OUT}. Run `cocoindex update main.py` to index.")
        else:
            print("drift unchanged — no rewrite, re-index will be a no-op")
    return 0


if __name__ == "__main__":
    sys.exit(main())
