#!/usr/bin/env python3
"""Assemble the dated production nightly cycle from the frozen row corpus.

The nightly consumer (``ontology-feedback`` in ``evidence-nightly.yml``) reads
``gs://shed-489901-atlas-outputs/evidence-nightly/<date>/cycle.json`` after
staging that directory under ``nightly-input/<date>/`` in its checkout. This
module is the producer for that contract: it derives which campaigns enter
tonight's cycle from the repository's own registry, validates the result by
running the consumer's own ingest over it, and stages a dated, self-contained
directory whose ``cycle.json`` the consumer can ingest.

Selection is deliberately strict, in three steps:

1. A row file belongs to a campaign only when its hash chain is bound to that
   campaign's registered manifest (``campaign_manifest_hash`` equals the
   registry's ``content_hash``).
2. A campaign enters the cycle only when every one of its rows already has
   its EvidenceBundle in the committed corpus (``evidence/v1/examples``),
   using the ingester's own filename rule. Rows never ingested into the
   registry are research output awaiting an owner-reviewed ingest, not
   nightly filler; a nightly timer must not be the thing that first commits
   them.
3. ``cycle.json`` references the checked-out repository's own manifest and
   row files with ``../../`` paths (relative to its staged location under
   ``nightly-input/<date>/``), because EvidenceBundles embed the
   repository-relative manifest path — pointing the cycle at copied files
   would mint bundles that differ from the committed corpus and be refused.
   The dated directory still carries byte-identical copies of every manifest
   and row file under ``campaigns/`` and ``rows/`` so the published cycle is
   a self-describing archive of exactly what it bound to.

Why replaying the frozen corpus is the honest daily producer: the loops that
mint new rows (MLIP cell campaigns, the sign-skew replication) run on
explicit owner spend decisions against preregistered panels, not on a nightly
timer. Between spends, the verifiable daily cycle is exactly the replay of
the frozen corpus — same rows, same hashes, same bundles — which keeps the
nightly gate meaningful (a drifted row or manifest fails the chain/hash
checks) and keeps production D1 converging with the repository's durable
evidence state.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.run_nightly_cycle import _load_cycle, run_cycle  # noqa: E402

REPO_ROW_DIRS = ("data/candidates",)
EVIDENCE_DIR = Path("evidence") / "v1" / "examples"


def safe_filename(campaign_id: str, row_id: str) -> str:
    """Mirror tools/ingest_campaign_results.py's bundle filename rule."""
    stem = re.sub(r"[^a-z0-9]+", "-", f"{campaign_id}-{row_id}".lower()).strip("-")
    return f"round4-{stem}.json"


def _load_registry_campaigns(root: Path) -> list[dict]:
    registry = json.loads((root / "registry" / "campaigns.v1.json").read_text(encoding="utf-8"))
    campaigns = registry.get("campaigns")
    if not isinstance(campaigns, list) or not campaigns:
        raise ValueError("registry/campaigns.v1.json contains no campaigns")
    return campaigns


def _manifest_filename(root: Path, campaign_id: str) -> str:
    """Return the registered manifest filename for a campaign id."""
    for path in sorted((root / "campaigns" / "v1").glob("*.json")):
        document = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(document, dict) and document.get("campaign_id") == campaign_id:
            return path.name
    raise ValueError(f"registered campaign {campaign_id} has no manifest in campaigns/v1")


def _row_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for directory in REPO_ROW_DIRS:
        base = root / directory
        if base.is_dir():
            files.extend(sorted(base.glob("**/measurements.jsonl")))
    return files


def _read_rows(path: Path) -> list[dict]:
    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if not isinstance(row, dict):
            raise ValueError(f"measurement line in {path} is not a JSON object")
        rows.append(row)
    return rows


def select_campaigns(root: Path) -> tuple[list[dict[str, str]], dict[str, str]]:
    """Map registered campaigns to the row files that may enter the cycle.

    Returns ``(selected, skipped)``: selected entries carry the campaign id
    plus repository-relative ``manifest`` / ``measurements`` paths; skipped
    maps a campaign id to the reason it is not in tonight's cycle.
    """
    chains: dict[Path, list[dict]] = {}
    bound: dict[Path, str | None] = {}
    for path in _row_files(root):
        rows = _read_rows(path)
        if not rows:
            continue
        chains[path] = rows
        manifest_hash = rows[0].get("campaign_manifest_hash")
        bound[path] = manifest_hash if isinstance(manifest_hash, str) else None

    selected: list[dict[str, str]] = []
    skipped: dict[str, str] = {}
    for campaign in _load_registry_campaigns(root):
        campaign_id = campaign.get("campaign_id")
        content_hash = campaign.get("content_hash")
        if not isinstance(campaign_id, str) or not isinstance(content_hash, str):
            raise ValueError("registered campaign is missing campaign_id or content_hash")
        matches = sorted(
            (path for path, hash_value in bound.items() if hash_value == content_hash),
            key=lambda path: (len(path.parts), path.as_posix()),
        )
        if not matches:
            skipped[campaign_id] = "no measurement row file is hash-bound to the registered manifest"
            continue
        # Multiple row files can bind the same frozen manifest (e.g. the z1
        # f64 re-execution). They are distinct measurement sets over the same
        # panel; ingesting both would collide on row_id. Use the canonical
        # file — the campaign's own candidate directory sorts first — and say
        # so about the others.
        canonical, extras = matches[0], matches[1:]
        rows = chains[canonical]
        if any(not isinstance(row.get("row_id"), str) or not row.get("row_id") for row in rows):
            skipped[campaign_id] = (
                f"row file {canonical.relative_to(root).as_posix()} predates the row_id contract"
            )
            continue
        missing_bundles = sorted(
            row["row_id"]
            for row in rows
            if not (root / EVIDENCE_DIR / safe_filename(campaign_id, row["row_id"])).is_file()
        )
        if missing_bundles:
            skipped[campaign_id] = (
                "rows not yet ingested into the committed corpus (missing EvidenceBundle for "
                f"{missing_bundles[0]}"
                + (f" and {len(missing_bundles) - 1} more" if len(missing_bundles) > 1 else "")
                + "); ingest them through a reviewed change first"
            )
            continue
        for extra in extras:
            print(
                f"note: {extra.relative_to(root).as_posix()} is bound to the same frozen "
                f"manifest as {canonical.relative_to(root).as_posix()}; using the canonical file",
                file=sys.stderr,
            )
        selected.append(
            {
                "campaign_id": campaign_id,
                "manifest": (Path("campaigns") / "v1" / _manifest_filename(root, campaign_id)).as_posix(),
                "measurements": canonical.relative_to(root).as_posix(),
            }
        )
    if not selected:
        raise ValueError(f"no registered campaign is replayable tonight: {skipped}")
    return selected, skipped


def write_cycle(*, root: Path, output_dir: Path, cycle_date: str, validate: bool = False) -> dict:
    """Materialize the dated cycle directory and return a report.

    Layout:

        <output_dir>/cycle.json          references ../../<repo-relative> files
        <output_dir>/campaigns/*.json    byte-identical copies of the manifests
        <output_dir>/rows/*.jsonl        byte-identical copies of the row files
        <output_dir>/producer-report.json

    ``cycle.json`` paths are relative to its staged location inside the
    consumer's ``nightly-input/<date>/`` directory, so they point back into
    the checkout (see the module docstring for why copies cannot be ingested
    directly). With ``validate``, the consumer's own ingest runs over the
    staged cycle — staged exactly where the consumer will stage it — before
    success is declared, and the staging is removed afterwards.
    """
    selected, skipped = select_campaigns(root)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "campaigns").mkdir(parents=True, exist_ok=True)
    (output_dir / "rows").mkdir(parents=True, exist_ok=True)

    entries = []
    written: list[str] = []
    for campaign in selected:
        staged_manifest = output_dir / "campaigns" / Path(campaign["manifest"]).name
        staged_rows = output_dir / "rows" / _row_stem(campaign["measurements"])
        staged_manifest.write_bytes((root / campaign["manifest"]).read_bytes())
        staged_rows.write_bytes((root / campaign["measurements"]).read_bytes())
        # ../../ escapes nightly-input/<date>/ back to the checkout root.
        entries.append(
            {
                "campaign_id": campaign["campaign_id"],
                "manifest": f"../../{campaign['manifest']}",
                "measurements": f"../../{campaign['measurements']}",
            }
        )
        written.append(staged_manifest.relative_to(output_dir).as_posix())
        written.append(staged_rows.relative_to(output_dir).as_posix())

    cycle = {"cycle_date": cycle_date, "campaigns": entries}
    (output_dir / "cycle.json").write_text(json.dumps(cycle, indent=2) + "\n", encoding="utf-8")
    written.append("cycle.json")

    validated = False
    if validate:
        # Mirror the consumer exactly: stage the dated directory under
        # <root>/nightly-input/<date>/ and run the nightly ingest over it.
        staged = root / "nightly-input" / cycle_date
        if staged.exists():
            shutil.rmtree(staged)
        shutil.copytree(output_dir, staged)
        try:
            run_cycle(
                root=root,
                campaigns=_load_cycle(staged / "cycle.json"),
                output_dir=output_dir / "validation",
            )
        finally:
            shutil.rmtree(staged)
        validated = True
        written.append("validation/")

    report = {
        "cycle_date": cycle_date,
        "campaign_count": len(entries),
        "campaign_ids": sorted(campaign["campaign_id"] for campaign in selected),
        "skipped_campaigns": dict(sorted(skipped.items())),
        "validated": validated,
        "written": sorted(written),
    }
    (output_dir / "producer-report.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    return report


def _row_stem(measurements_rel: str) -> str:
    """Stage name for a row file: parent dir + suffix, unique per campaign.

    Row files all share the basename ``measurements.jsonl``; the parent
    candidate directory (``z1``, ``z3``, ``round4``, ...) is what
    distinguishes them, so keep it in the staged name.
    """
    path = Path(measurements_rel)
    prefix = path.parent.name
    return f"{prefix}-{path.name}" if prefix else path.name


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--cycle-date",
        required=True,
        help="UTC date of the cycle (YYYY-MM-DD); pass the run's own date semantics",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="run the consumer's own ingest over the assembled cycle before declaring success",
    )
    args = parser.parse_args()
    report = write_cycle(
        root=args.root.resolve(),
        output_dir=args.output_dir.resolve(),
        cycle_date=args.cycle_date,
        validate=args.validate,
    )
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
