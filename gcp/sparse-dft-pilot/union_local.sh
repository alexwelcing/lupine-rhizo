#!/bin/bash
# Local union-anchor sparse-DFT pilot (Amendment 01): serial GPAW, one anchor
# at a time, checkpointed per anchor under /tmp/z1-union-local — safe to
# interrupt and re-run (completed anchors are skipped, receipts imported).
#
# Usage:
#   gcp/sparse-dft-pilot/union_local.sh [PATHS] [EXTRA_ARGS...]
#     PATHS       active path indices, "7,16" or "0-29" (default: all 23)
#     EXTRA_ARGS  forwarded to union_pilot.py, e.g. --dry-run, --assemble-only,
#                 --min-free-gb 4, --minutes-per-anchor 120
#
# Examples:
#   gcp/sparse-dft-pilot/union_local.sh "" --dry-run          # cost report, no GPAW
#   gcp/sparse-dft-pilot/union_local.sh 7                     # finish path 7 (1 anchor)
#   gcp/sparse-dft-pilot/union_local.sh "" --assemble-only    # rebuild campaign.json
set -u
PATHS="${1:-}"
shift || true
WORKDIR=/tmp/z1-union-local
mkdir -p "$WORKDIR"
cd /home/alex/Dev/lupine/lupine-rhizo || exit 1

args=(gcp/sparse-dft-pilot/union_pilot.py --workdir "$WORKDIR")
if [ -n "$PATHS" ]; then
  args+=(--paths "$PATHS")
fi

echo "== union pilot $(date +%H:%M:%S) paths='${PATHS:-all-active}' $* =="
# Serial by construction: a single python process evaluates one anchor at a
# time; never launch two instances of this script concurrently.
.venv/bin/python "${args[@]}" "$@"
echo "== done: $(find "$WORKDIR/anchors" -name 'anchor-*.json' 2>/dev/null | wc -l) anchor checkpoints =="
