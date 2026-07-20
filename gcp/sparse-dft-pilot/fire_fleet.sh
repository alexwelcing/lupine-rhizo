#!/bin/bash
# Sparse-DFT pilot fleet: 4 models x 30 paths, one execution per (model, path).
# Guidance comes from recorded Round-4 artifacts; GPAW runs at the frozen anchors.
set -u
MODELS="chgnet mace-mp-small mace-mp-medium mace-mpa-0-medium"
OUTROOT="gs://shed-489901-atlas-outputs/z1-sparse-dft"
JOB=sparse-dft-pilot
PROJECT=shed-489901
REGION=us-central1

echo "== bump job timeout to 6h for serial per-path anchors =="
gcloud run jobs update $JOB --region $REGION --project $PROJECT --task-timeout=21600s >/dev/null

echo "== fire 120 executions =="
for model in $MODELS; do
  for idx in $(seq 0 29); do
    gcloud run jobs execute $JOB \
      --region $REGION --project $PROJECT --async \
      --args="--mlip-id,$model,--paths,$idx,--out,$OUTROOT/$model/path-$idx.json" \
      --format="value(metadata.name)" 2>/dev/null || echo "EXEC-FAIL $model $idx"
    sleep 0.3
  done
done
echo "== all submitted =="
