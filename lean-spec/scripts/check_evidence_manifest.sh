#!/bin/sh
# Enforce the LupineEvidence manifest <-> source-tree bijection.
#
# Every generated module under LupineEvidence/ must be imported by the
# manifest root LupineEvidence.lean, and every import there must exist on
# disk. Orphans (file, no import) still BUILD via the `LupineEvidence.+`
# glob, but they fail here so unreviewed admissions are visible; stale
# imports (import, no file) would already fail `lake build`, this catches
# them without a toolchain. Pair with `lake build LupineEvidence`.

set -u

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
spec_dir=$(CDPATH= cd -- "$script_dir/.." && pwd)
cd "$spec_dir" || {
  echo "FATAL: cannot cd into lean-spec dir ($spec_dir)" >&2
  exit 2
}

manifest="LupineEvidence.lean"
tree="LupineEvidence"

for tool in find grep sed sort comm; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    echo "FATAL: '$tool' not found on PATH" >&2
    exit 2
  fi
done
if [ ! -f "$manifest" ]; then
  echo "FATAL: manifest not found: $spec_dir/$manifest" >&2
  exit 2
fi
if [ ! -d "$tree" ]; then
  echo "FATAL: source tree not found: $spec_dir/$tree" >&2
  exit 2
fi

tmp_dir=$(mktemp -d "${TMPDIR:-/tmp}/check_evidence_manifest.XXXXXX") || exit 2
trap 'rm -rf "$tmp_dir"' EXIT HUP INT TERM

# Modules on disk: LupineEvidence/YMatrix/Ni_chgnet.lean -> LupineEvidence.YMatrix.Ni_chgnet
find "$tree" -name '*.lean' -type f \
  | sed -e 's|\.lean$||' -e 's|[/\\]|.|g' \
  | sort > "$tmp_dir/on_disk"

# Modules the manifest imports.
grep -E '^import[[:space:]]+LupineEvidence\.' "$manifest" \
  | sed -e 's|^import[[:space:]]*||' -e 's|[[:space:]]*$||' \
  | sort > "$tmp_dir/imported"

status=0

orphans=$(comm -23 "$tmp_dir/on_disk" "$tmp_dir/imported")
if [ -n "$orphans" ]; then
  echo "error: generated modules on disk but MISSING from $manifest (orphans):"
  printf '%s\n' "$orphans" | sed 's|^|  |'
  status=1
fi

stale=$(comm -13 "$tmp_dir/on_disk" "$tmp_dir/imported")
if [ -n "$stale" ]; then
  echo "error: modules imported by $manifest but MISSING on disk (stale imports):"
  printf '%s\n' "$stale" | sed 's|^|  |'
  status=1
fi

if [ "$status" -eq 0 ]; then
  count=$(grep -c . "$tmp_dir/on_disk")
  echo "OK: $manifest matches $tree/ ($count modules)"
fi
exit "$status"
