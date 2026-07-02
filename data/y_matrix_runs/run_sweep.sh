#!/usr/bin/env bash
# First cross-property Y-matrix sweep — 2026-07-01
# Serial through the single A4500. Failures are recorded loudly, never skipped silently.
cd "C:/Users/alexw/Downloads/lupine-rhizo"
PY=".venv-mlip312/Scripts/python"
OUT="data/y_matrix_runs"
LOG="$OUT/sweep.log"
echo "=== sweep start $(date) ===" >> "$LOG"
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
  # fcc metals: full Tier-1 battery
  for mat in Ni Cu Al; do
    run_cell "$mat" fcc "$model" "lattice,eos,vacancy,surfaces,sfe"
  done
  # bcc metals: no SFE lane
  for mat in Fe W; do
    run_cell "$mat" bcc "$model" "lattice,eos,vacancy,surfaces"
  done
  # Tier-3: beyond metals
  run_cell Si diamond "$model" "lattice,eos,vacancy"
  run_cell NiAl b2 "$model" "lattice,eos,formation"
  run_cell Ni3Al l12 "$model" "lattice,eos,formation"
done
echo "=== sweep end $(date) ===" >> "$LOG"
grep -c "^\[ok\]" "$LOG" | xargs echo "cells ok:"
grep -c "^\[FAIL\]" "$LOG" | xargs echo "cells failed:"
