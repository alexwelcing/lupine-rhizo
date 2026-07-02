#!/usr/bin/env bash
# Sweep 2: complete the 16-metal set (11 new elements x 3 models) — 2026-07-01
cd "C:/Users/alexw/Downloads/lupine-rhizo"
PY=".venv-mlip312/Scripts/python"
OUT="data/y_matrix_runs"
LOG="$OUT/sweep2.log"
echo "=== sweep2 start $(date) ===" >> "$LOG"
run_cell () {
  local mat=$1 struct=$2 model=$3 props=$4
  local tag="${mat}_${struct}_${model}"
  echo "[cell] $tag ($props)" >> "$LOG"
  if $PY python/scripts/run_y_matrix_statics.py \
      --material "$mat" --structure "$struct" --model "$model" --device cuda \
      --properties "$props" \
      --out "$OUT/$tag.json" --evidence-out "$OUT/$tag.evidence.json" >> "$LOG" 2>&1; then
    echo "[ok]   $tag" >> "$LOG"
  else
    echo "[FAIL] $tag (exit $?)" >> "$LOG"
  fi
}
for model in mace-mp-small mace-mp-medium chgnet; do
  for mat in Ag Au Ca Pd Pt Sr; do
    run_cell "$mat" fcc "$model" "lattice,eos,vacancy,surfaces,sfe"
  done
  for mat in Cr Mo Nb Ta V; do
    run_cell "$mat" bcc "$model" "lattice,eos,vacancy,surfaces"
  done
done
echo "=== sweep2 end $(date) ===" >> "$LOG"
grep -c "^\[ok\]" "$LOG" | xargs echo "cells ok:"
grep -c "^\[FAIL\]" "$LOG" | xargs echo "cells failed:"
