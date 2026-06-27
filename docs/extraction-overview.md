# Extraction Overview — How the Source Reports Entered the Library

> **Redirect note.** This article consolidates three former catalog entries —
> `extraction-complete`, `extraction-report`, and `extraction-notes` — into a
> single operations reference. Those legacy ids are no longer cataloged, but
> their source files (`docs/EXTRACTION_COMPLETE.md`, `docs/EXTRACTION_REPORT.md`,
> `docs/EXTRACTION_NOTES.md`) are preserved in the repository for provenance.

## Summary

Several foundational library reports originated as **Kimi Deep Research**
interactive reports — large, web-rendered technical reviews that had to be
extracted from the browser session and converted to Markdown before they could
be version-controlled and published. This article records how that one-time
extraction was performed, the per-report statistics, and the edge cases
encountered.

All three original logs are **stale process artifacts**: they describe a single
extraction run, contain dead `/sessions/...` paths, and each points to the
*live* report that superseded it. They are retained here for build provenance,
not as active reader content.

| Source report (extracted) | Kimi tab | Live report in this library |
|---|---|---|
| Information-Theoretic Model Compression | 1899282382 | [`info_theoretic_report.md`](./info_theoretic_report.md) |
| Phonon Frequency Spectrum Benchmarking | 1899282427 | [`phonon_benchmarking_report.md`](./phonon_benchmarking_report.md) |
| Renormalization Group Coarse-Graining | 1899282406 | [`rg_coarsegraining_report.md`](./rg_coarsegraining_report.md) |

---

<details>
<summary><strong>Extraction — Complete</strong> (information-theoretic report)</summary>

*Original file: [`EXTRACTION_COMPLETE.md`](./EXTRACTION_COMPLETE.md) — extraction-completion log for the information-theoretic report.*

### File details
- **Report title:** Information-Theoretic Bounds on Model Error Compression in Computational Physics: A Comprehensive Review
- **File path (dead, session-relative):** `/sessions/friendly-gracious-hamilton/breadth_exploration/dr_reports/info_theoretic_report.md`
- **File size:** 16 KB · **329 lines** · **Format:** Markdown
- **Source:** Kimi Deep Research Interactive Report (Tab 1899282382)

### Report structure
1. Executive Summary
2. Fundamental Theoretical Frameworks — Rate-Distortion Theory, Kolmogorov Complexity, Shannon Entropy
3. Model Selection and Error Compression Criteria — MDL, Information-Theoretic Criteria, QoL-Preserving Frameworks
4. Error Manifold Geometry and Dimensionality — Crystal Symmetry Groups, Physical Constraints, Spectral Analysis
5. Classical vs. Machine Learning Potentials
6. Theoretical Lower Bounds — Existence, form, and limitations; uncomputability implications
7. Practical Implications and Recent Developments
8. Synthesis and Open Questions

### Key assessment
- **Core finding:** Bounds are family-specific and context-dependent, not universal.
- **Final assessment:** Absolute bounds exist (Kolmogorov complexity, rate-distortion limits) but are uncomputable or family-specific; practical bounds require physics-informed frameworks.
- **Main conclusion:** The most productive direction is developing physics-informed frameworks that exploit structure, rather than seeking universal bounds.

### Theoretical frameworks covered
Rate-Distortion Theory · Kolmogorov Complexity & Algorithmic Information Theory · Shannon Entropy · Information Bottleneck · Bayesian Model Comparison · Representation Theory (Crystallography) · Spectral Analysis

### Status
✓ Extraction complete · ✓ Comprehensive markdown document created · ✓ All major sections captured · ✓ Key findings and final assessment included · ✓ Applications documented

</details>

<details>
<summary><strong>Extraction — Report</strong> (phonon benchmarking report)</summary>

*Original file: [`EXTRACTION_REPORT.md`](./EXTRACTION_REPORT.md) — conversion statistics and fidelity notes for the phonon benchmarking report.*

### Extraction task summary
- **Source:** Kimi Tab 1899282427 — GLIM Phonon Benchmarking Review
- **Report title:** Phonon Frequency Spectrum Benchmarking for Interatomic Potentials: A Technical Review for the GLIM Project
- **Report size:** 63,005 characters (63,112 expected)
- **Method:** JavaScript content extraction via the Kimi web interface
- **Completed:** March 28, 2026

### Files generated
1. **Main report** — `phonon_benchmarking_report.md`, 19.4 KB (229 lines). Comprehensive framework: foundational concepts, phonon calculation methodology, JARVIS-DFT reference data, metrics & evaluation framework, potential family comparison, computational cost, ML benchmarks, community engagement.
2. **Key findings summary** — `KEY_FINDINGS_SUMMARY.md`, 8.3 KB (154 lines). Ten critical findings for GLIM implementation.

### Core methodology
- 23 interatomic potentials × 12,000 materials = **276,000 phonon calculations**
- JARVIS-DFT database: ~90,000 materials, 17,402 with complete phonon data
- Multi-level hierarchy: band structure → PDOS → thermodynamic properties
- Standardized displacement magnitudes: 0.01–0.03 Å

### Performance metrics (accuracy hierarchy)
- Universal MLIPs: 2–10 meV
- Fine-tuned MLIPs: <2 meV (sub-meV achievable)
- Classical potentials: 20–100+ meV

Top performers: **ORB v3** (~10× more efficient than OMat24), **SevenNet-0**, **MatterSim**, **eqV2-M** (fine-tuned, 0.174 log(W/m·K) for thermal conductivity).

### Critical findings
1. **Force-constant collapse** — neural networks can predict correct forces but severely inaccurate force constants; explicit phonon validation required.
2. **Stability prediction** — only 25.83% of AI-generated structures are dynamically stable.
3. **Fine-tuning opportunity** — 55% improvement in phonon properties with a modest 60–140 GPU-hour investment.
4. **Functional sensitivity** — phonon frequency shifts of 2–6% (dense) to 20%+ (van der Waals) depending on functional (PBE vs. optB88).
5. **Displacement-dependent errors** — ORB and OMat show drastic MAE increase at small displacements.
6. **Composition variation** — main-group > transition metals > heavy elements / rare earths in typical accuracy.
7. **Computational cost** — ~10⁶ GPU-hours base estimate for a full benchmark, ~1.5×10⁶ with contingency.

### Extraction challenges & solutions
- **Content filtering** — some chunks returned `[BLOCKED: Cookie/query string data]`; resolved by extracting from multiple access points and reassembling.
- **Large content size** — 63,005 characters exceeded direct retrieval limits; segmented into 13 × 5 KB chunks and retrieved sequentially.
- **Concatenation blocking** — combining chunks returned blocked messages; assembled from individual chunks via JavaScript.
- **Character encoding** — Unicode characters (subscripts, special symbols) preserved as UTF-8.

</details>

<details>
<summary><strong>Extraction — Notes</strong> (RG coarse-graining report)</summary>

*Original file: [`EXTRACTION_NOTES.md`](./EXTRACTION_NOTES.md) — edge cases and structural notes for the RG coarse-graining report.*

### Source information
- **URL:** Kimi Deep Research Interactive Report (Tab 1899282406)
- **Report title:** "Renormalization Group Methods for Coarse-Graining"
- **Subtitle:** A comprehensive review of RG applications in molecular dynamics and atomistic simulation
- **Tags:** Statistical Mechanics · Molecular Dynamics · Biophysics

### Report structure overview
1. **Historical Foundations** — origins of RG in statistical mechanics; Wilson's formulation; Kadanoff's block-spin transformation; Migdal-Kadanoff approximation; adaptation to molecular systems; early coarse-graining attempts; biomolecular challenges; information-theoretic perspectives.
2. **Modern Methodology** — Molecular Renormalization Group Coarse-Graining (MRG-CG); the Savelyev-Papoian framework; partition-function matching; correlator-matching optimization; inverse Monte Carlo generalization; linear response theory.
3. **Advanced Theory** — information-geometric perspective; Fisher information metric; model manifolds; non-equilibrium RG for active matter; biomolecular applications.
4. **Practical Implementation** — error propagation and information loss; optimization landscapes; comparison with alternative methods; implementation challenges; validation strategies.
5. **Future Directions** — integration with information geometry; non-equilibrium extensions; hierarchical RG schemes; machine-learning integration.

### Key concepts highlighted
1. **Non-equilibrium RG framework for active matter** — extension beyond equilibrium statistical mechanics.
2. **Information-geometric perspective** — Sethna and colleagues, Fisher information metrics for model selection and information loss.
3. **Systematic coarse-graining** — deriving effective potentials while preserving thermodynamic properties.
4. **Partition-function matching** — rigorous theoretical foundation for coarse-grain potential development.
5. **Correlator matching** — alternative optimization criterion focusing on collective coordinate dynamics.

### Key authors and contributors referenced
Kenneth Wilson (RG foundations) · Leo Kadanoff (block-spin transformations) · Alexey Savelyev & Garegin Papoian (MRG-CG framework) · James Sethna (information-geometric approaches) · Sethna group at Cornell (modern information-theoretic perspective).

### Report statistics
- **Total words:** 1,804 · **Major sections:** 7 · **Heading depth:** up to 4 levels
- **Output file (dead, session-relative):** `/sessions/friendly-gracious-hamilton/breadth_exploration/dr_reports/rg_coarsegraining_report.md`
- **File size:** 15K · **Generated:** March 28, 2026

### Extraction method
Identify Kimi Deep Research report structure → map section hierarchy and content blocks → synthesize detailed content from identified sections → organize into comprehensive markdown → include key findings, headers, and conclusions.

### Completeness notes
✓ Complete structural outline · ✓ All major section/subsection headers · ✓ Key concepts and theoretical frameworks · ✓ Important methodological details · ✓ References to key researchers · ✓ Practical implementation considerations · ✓ Future research directions · ✓ Executive summary

</details>
