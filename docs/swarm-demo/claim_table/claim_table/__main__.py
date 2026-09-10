"""CLI: python -m claim_table <results.json>"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from .core import (
    EXIT_DATA,
    EXIT_OK,
    EXIT_USAGE,
    ClaimTableError,
    load_results,
    render_markdown,
)

USAGE = "usage: python -m claim_table <results.json>"


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1 or args[0] in ("-h", "--help"):
        print(USAGE, file=sys.stderr)
        return EXIT_USAGE
    path = Path(args[0])
    try:
        print(render_markdown(load_results(path)))
    except FileNotFoundError:
        print(f"claim-table: no such file: {path}", file=sys.stderr)
        return EXIT_DATA
    except json.JSONDecodeError as exc:
        print(f"claim-table: invalid JSON in {path}: {exc}", file=sys.stderr)
        return EXIT_DATA
    except ClaimTableError as exc:
        print(f"claim-table: {exc}", file=sys.stderr)
        return EXIT_DATA
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
