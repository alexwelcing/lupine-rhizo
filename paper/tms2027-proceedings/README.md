# TMS 2027 proceedings manuscript (poster contribution)

**Accepted title (unqualified):** *From Transferability to Prediction: The Error Geometry of Interatomic Potentials*
**Binding contract:** `docs/plans/2026-09-09-tms-manuscript-sprint.md` (claim freeze; abstract used verbatim)
**Deadline:** 2026-09-09

## Contents

| File | Role |
|---|---|
| `manuscript.tex` | LaTeX source. Four-panel structure: denominator funnel; geometry under finite-sample nulls; cross-paradigm + correction falsification; qualification protocol + DFT-reference stack (all-electron anchor **pending**). One compact table for non-elastic programs; no numeric pooling with elasticity. |
| `references.bib` | Embedded references (extracted from `lupine/paper/references.bib` and `paper/negative-results-preprint/references.bib`). |
| `build_artifacts.py` | Recomputes every derivable headline number from committed source rows, records the SHA-256 of every source file, writes `results.json`, and renders the four figures. Fails closed on a missing source or a headline mismatch. `--check` verifies `results.json` is current. |
| `check_claims.py` | Claim lock: fails if any phrase from the contract's *Remove or retire* list appears outside an explicit retirement sentence, or if a headline token in the text is missing from / disagrees with `results.json`. |
| `results.json` | Canonical results object. `derived` = recomputed from data; `quoted` = copied from named frozen reports (each with its source key). |
| `figures/` | `fig1_denominator_funnel.pdf`, `fig2_pr_vs_group_size.pdf`, `fig3_correction_arms.pdf`, `fig4_reference_stack.pdf` — all generated from `results.json`. |
| `manuscript.pdf` | Reviewer PDF built with Tectonic 0.15.0 (`SOURCE_DATE_EPOCH=1788912000 FORCE_SOURCE_DATE=1`). |

## Build

From the `lupine-rhizo` root (sibling `lupine` checkout required; override with `LUPINE_REPO`):

```bash
LUPINE_REPO=/path/to/lupine python paper/tms2027-proceedings/build_artifacts.py
python paper/tms2027-proceedings/check_claims.py
cd paper/tms2027-proceedings
SOURCE_DATE_EPOCH=1788912000 FORCE_SOURCE_DATE=1 tectonic manuscript.tex
```

## Omissions by contract rule

- The 352-row live-ledger elastic null test was **not recovered** at build time; its exact PR/null/correction numbers are omitted. `results.json` records `recovery_outputs_present: false` (no `data/candidates/tms2027/` outputs existed).
- The paired all-electron PBE/r2SCAN elastic anchor has not run and is described as a pending preregistered experiment (roster overlap 14 of 15/16 metals).
- Frozen economics (`72.4% fewer DFT evaluations`, `$14.65 per 129 anchors`) are deliberately **not** repeated in the manuscript because the contract retires "realized 72.4% savings" language for this venue; the Z1 row states only that a prospective savings claim is not defensible.

## Submission checklist (TMS)

- [x] Title (accepted, unqualified)
- [x] Abstract 150–250 words (contract text verbatim; 211 whitespace tokens)
- [x] ≥3 keywords (5)
- [x] References (BibTeX, `unsrtnat`)
- [x] Data availability statement
- [x] LaTeX source package + reviewer PDF
- [ ] Copyright form (owner action at submission)
- [ ] Independent statistics/physics referee pass (separate card)
