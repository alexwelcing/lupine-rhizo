#!/usr/bin/env python3
"""Publish canonical Lupine brand/agent files to explicit site roots.

Usage:
    python scripts/sync_brand_agent_text.py --site-root /path/to/site/public
    python scripts/sync_brand_agent_text.py --site-root /path/to/first/site --site-root /path/to/second/site
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "docs" / "brand" / "agent"
BRAND_CONFIG = ROOT / "brand.config.json"


def copy_text(source: Path, destination: Path) -> None:
    destination.write_text(source.read_text(encoding="utf-8"), encoding="utf-8", newline="\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync canonical brand/agent files to selected sites.")
    parser.add_argument(
        "--site-root",
        type=Path,
        action="append",
        required=True,
        help="Destination site root; repeat for multiple sites.",
    )
    args = parser.parse_args()
    brand = json.loads(BRAND_CONFIG.read_text(encoding="utf-8"))
    for site_root in args.site_root:
        site_root.mkdir(parents=True, exist_ok=True)
        copy_text(SOURCE_DIR / "llms.txt", site_root / "llms.txt")
        copy_text(SOURCE_DIR / "llms-full.txt", site_root / "llms-full.txt")
        (site_root / "brand.json").write_text(
            json.dumps(brand, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
            newline="\n",
        )
    print(f"Synced brand agent text to {len(args.site_root)} site roots.")


if __name__ == "__main__":
    main()
