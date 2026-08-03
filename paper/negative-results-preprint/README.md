# Negative-results preprint

ArXiv-ready source bundle for the Z1 barrier, Z3 adsorption-correction, and global elastic-operator negative results.

## Build and verify the locked bundle

From the `lupine-rhizo` repository root:

```bash
python paper/negative-results-preprint/build_artifacts.py --check
```

This command verifies ten frozen source files by SHA-256, including the raw Z3 candidate–model registry and the global-operator lock, derives the plotted values and completeness counts, regenerates the PDF/PNG figure and artifact manifest, and checks critical manuscript claims. It fails closed on source drift.

Build the paper with Tectonic:

```bash
cd paper/negative-results-preprint
SOURCE_DATE_EPOCH=1785733200 FORCE_SOURCE_DATE=1 tectonic manuscript.tex
```

With Tectonic 0.17.0 this produces a deterministic 7-page PDF; the verified build SHA-256 is recorded in the task handoff rather than embedded in the source manifest.

The arXiv upload bundle consists of:

- `manuscript.tex`
- `references.bib`
- `figures/negative-results-panels.pdf`
- `figure-source-data.json`
- `artifact-manifest.json` and its SHA-256 sidecar
- `global-operator.lock.json`
- `build_artifacts.py`

## Claim-scope guard

`128/128` means all raw Z3 candidate–model cells completed. The correction result is 4/4 model-level holdout MAEs worse. The locked Z1 rows do not support the stale “all 26 paths underpredicted” summary: MACE-MP small has 17 negative and 9 positive signed errors in each precision chain. The paper preserves this correction explicitly.
