#!/bin/bash
# Local sparse-DFT pilot (checkpointed): one process per path, skip completed.
set -u
MODEL="${1:-chgnet}"
PATHS="${2:-7,16,4,29,12,13,27,14,21,22,26}"
OUTDIR=/tmp/z1-sparse-local/$MODEL
mkdir -p "$OUTDIR"
cd /home/alex/Dev/lupine/lupine-rhizo

IFS=',' read -ra IDX <<< "$PATHS"
for idx in "${IDX[@]}"; do
  out="$OUTDIR/path-$idx.json"
  if [ -s "$out" ]; then
    echo "skip $idx (done)"; continue
  fi
  echo "== $MODEL path $idx $(date +%H:%M:%S) =="
  .venv/bin/python gcp/sparse-dft-pilot/run_pilot.py \
    --mlip-id "$MODEL" --paths "$idx" --out "$out" --workdir "$OUTDIR/work" \
    2>&1 | tail -2
done
echo "== sweep complete: $(ls "$OUTDIR"/path-*.json 2>/dev/null | wc -l) path files =="
