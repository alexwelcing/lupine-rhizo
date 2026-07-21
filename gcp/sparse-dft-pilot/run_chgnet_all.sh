#!/bin/bash
# Continuation: finish chgnet's remaining 19 paths after the small sweep,
# then aggregate. Checkpoints shared with the small sweep (same OUTDIR).
set -u
MODEL=chgnet
REMAINING="0,1,2,3,5,6,8,9,10,11,15,17,18,19,20,23,24,25,28"
SMALL="7,16,4,29,12,13,27,14,21,22,26"
SCRIPT=/home/alex/Dev/lupine/lupine-rhizo/gcp/sparse-dft-pilot/run_local.sh

bash "$SCRIPT" "$MODEL" "$SMALL"
echo "== small sweep done; continuing with remaining chgnet paths =="
bash "$SCRIPT" "$MODEL" "$REMAINING"
echo "== chgnet panel complete; aggregating =="
ls /tmp/z1-sparse-local/chgnet/path-*.json | wc -l
