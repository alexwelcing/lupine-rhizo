# Citation identifier verification: nine savings digests

Generated: 2026-07-21

## Scope and method

- Scanned the nine digests named by `savings-techniques-synthesis-2026-07-21.md`.
- Extracted 115 unique arXiv IDs and 48 unique DOI strings (163 unique identifiers total).
- Checked arXiv IDs against the official arXiv Atom API and DOI strings against Crossref Works metadata.
- Reviewed returned titles against the citing digest rows; this caught one live but unrelated DOI hidden in a link target.
- Deduplicated repeated identifiers across digests for network verification while retaining every source location in the machine-readable task artifact.
- The task estimate of 108 identifiers was stale: the nine current files contain 115 unique arXiv IDs plus 48 unique DOI strings.

## Result

- arXiv: **115/115 verified**.
- DOI: **48/48 verified through Crossref**.
- Unresolved identifiers: **none**.

This is an identifier-and-metadata audit. It does not upgrade abstract-only evidence, remove each digest's `[UNVERIFIED]` quantitative-claim flags, or independently reproduce reported savings factors.

## VASP MLFF 2019 venue reconciliation

- `arXiv:1904.12961` resolves to **On-the-fly machine learning force field generation: Application to melting points** (Jinnouchi, Karsai, Kresse), published as **Physical Review B 100, 014105 (2019)**, DOI `10.1103/PhysRevB.100.014105`.
- **Physical Review Letters 122, 225701 (2019)**, DOI `10.1103/PhysRevLett.122.225701`, is a distinct paper by Jinnouchi, Lahnsteiner, Karsai, Kresse, and Bokdam: **Phase Transitions of Hybrid Perovskites Simulated by Machine-Learning Force Fields Trained on the Fly with Bayesian Inference**.
- Therefore the melting-point / >99%-bypass claim belongs to PRB 100, 014105 / arXiv:1904.12961. PRL 122, 225701 supports the earlier hybrid-perovskite on-the-fly Bayesian MLFF demonstration, not the five-material melting-point claim.

## Corrections applied

- Corrected the Chen et al. multi-fidelity graph-network citation from the nonexistent `10.1038/s41524-021-00511-w` / npj venue to **Nature Computational Science 1, 46–53**, DOI `10.1038/s43588-020-00002-x`.
- Corrected the Nandi 2021 link target, which pointed to the live but unrelated DOI `10.1021/acs.jctc.1c00504`; the citation text's DOI `10.1063/5.0038301` was correct.
- Split the VASP MLFF row into the PRB melting-point paper and the distinct PRL hybrid-perovskite demonstration.

## Audit record

The task artifact `citation-verification.json` records every extracted identifier, returned title, publication metadata, source file, source line, and the two separately checked VASP DOI records. The reproducible checker is `verify_citations.py` in the same task artifact set.
