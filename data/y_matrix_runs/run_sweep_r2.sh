#!/usr/bin/env bash
# Round 2: MACE-MPA-0 (OMat24 lineage) through the identical matrix — R2-H1 registered test
cd "C:/Users/alexw/Downloads/lupine-rhizo"
PY=".venv-mlip312/Scripts/python"; OUT="data/y_matrix_runs"; LOG="$OUT/sweep_r2.log"
model=mace-mpa-0-medium
run_cell () {
  local mat=$1 struct=$2 props=$3; local tag="${mat}_${struct}_${model}"
  if $PY python/scripts/run_y_matrix_statics.py --material "$mat" --structure "$struct" --model "$model" --device cuda --properties "$props" --out "$OUT/$tag.json" --evidence-out "$OUT/$tag.evidence.json" >> "$LOG" 2>&1; then
    echo "[ok]   $tag" >> "$LOG"; else echo "[FAIL] $tag (exit $?)" >> "$LOG"; fi
}
for mat in Ni Cu Al Ag Au Ca Pd Pt Sr; do run_cell "$mat" fcc "lattice,eos,vacancy,surfaces,sfe"; done
for mat in Fe W Cr Mo Nb Ta V; do run_cell "$mat" bcc "lattice,eos,vacancy,surfaces"; done
run_cell Si diamond "lattice,eos,vacancy"
run_cell NiAl b2 "lattice,eos,formation"; run_cell Ni3Al l12 "lattice,eos,formation"
run_cell MgO rocksalt "lattice,eos"; run_cell NaCl rocksalt "lattice,eos"
grep -c "^\[ok\]" "$LOG" | xargs echo "cells ok:"; grep -c "^\[FAIL\]" "$LOG" | xargs echo "cells failed:"
