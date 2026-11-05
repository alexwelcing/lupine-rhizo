# Public-source candidate-report acceptance

This bridge tests the actual `atlas-distill candidate-order` executable's JSON
through the application validator, bounded local-file reader and static React
view. It uses reviewed public-table summaries from three publications. It does
not introduce a new ranking method or infer physical validity from report
acceptance.

## Cases and expected decisions

The fixture is
`atlas-distill/tests/fixtures/candidate_order_sources.json`.
Four reports contain eleven listed alternatives, not eleven new corpus
observations or independent studies.

| Fixture | Decision among supplied alternatives | Exposure and scope |
| --- | --- | --- |
| Olsson 2005 Cr | Model and VASP both choose the listed 110 interstitial. | Relaxed defects enter fitting; paramagnetic Cr; assumed independent ±0.005 eV printing bounds. |
| Ko 2015 Ni in hcp Ti | DFT selects the lower in-basal barrier; 2NN-MEAM selects the lower out-of-basal barrier. | Barrier ordering only. Exact initial/path identities, prefactors and per-defect fitting exposure remain unresolved. Assumed ±0.0005 eV printing bounds. |
| Kobayashi 2017 NN | PBE and NN choose Mg + Mg2Si over Mg3Si and the elements. | Each alternative contains 3 Mg + 1 Si. NN configurations enter training; static unconstrained mixtures; finite list. |
| Kobayashi 2017 reported Jelinek MEAM | PBE chooses Mg + Mg2Si; MEAM chooses the elements. | Same balanced alternatives. Exact MEAM row-level fitting exposure and model artifact remain unknown. |

Kobayashi's printed per-atom values are converted to total eV in a common
four-atom reaction unit. The Mg3Si term has printing radius 0.002 eV; Mg2Si plus
one Mg atom has radius 0.0015 eV. The elemental formation-energy endpoint is
exactly zero by convention. These independent printing assumptions are not
physical uncertainty bounds. The model's elemental cohesive reference need
not numerically equal the DFT reference; each balanced reaction uses its own
declared convention.

Source IDs, table/page anchors, protocol limits and explicit null artifact
identities are included in the producer input. A fixture digest does not
identify a physical candidate structure, and none is manufactured for that
purpose. Each case links the primary publication. These are manually reviewed,
known-outcome acceptance fixtures; no blind benchmark, new source acquisition,
private corpus packet or research-team artifact is included.

The [failure map](exception-to-theorem-failure-map.md) preserves the original
analysis dates, sources, scientific qualifications and competent-baseline
comparison. These acceptance inputs are a later representation of that evidence,
not a new independent validation.

## Full-path checks

The existing atlas CI test job first builds its release executable. A bounded
step then uses the existing locked Node dependencies and runs:

    ATLAS_DISTILL_BIN=/absolute/path/to/atlas-distill \
      node --test scripts/testing/candidate-order-cli.test.mjs

Run from `glim-think`. A missing binary is a failure, never a silently skipped
test. Every CLI invocation receives JSON on stdin, has a ten-second timeout and
a 512 KiB output ceiling. No model/provider/simulator is invoked. The workflow
reuses the release binary already built by its existing smoke test; it does not
add another Rust build or manual workflow dispatch. Dependency installation and
acceptance steps have three- and two-minute ceilings respectively.

The test bundles the actual application modules and their locked Zod/React
dependencies in memory using the existing esbuild dependency. It does not
replace the schema, assessor or renderer with transport doubles. No generated
report files are needed.

For every report it checks:

- The real CLI exit status, exact parsed input retention and SHA-256 of the
  submitted UTF-8 bytes.
- Every expected signed reference/prediction pair interval and both unique
  minima against explicit fixture expectations.
- Full report validation, the bounded file-reading function and static view.
- Retention of source anchors, fitting exposure or its absence, printing
  assumptions, incomplete search and unknown artifact identities.
- The unasserted source verification, scientific validation and global-minimum
  claims.
- Rejection of a forged gap, winner, issue list, scientific-validation claim and
  stale changed input by the complete file reader.

Additional cases keep missing reference/protocol/comparability visible, retain
a tie under a labeled synthetic endpoint perturbation, and remove the known
Mg + Mg2Si alternative. That restricted report legitimately chooses Mg3Si
among its remaining alternatives while still disclaiming search completeness
and global stability. The validator cannot recover an omitted physical phase
from information absent from the input.

The reader/render path is checked for calls to `fetch` and
`localStorage.setItem`; the test does not claim a general browser-storage or
network-isolation audit. The actual source contract has no upload or saved-run
operation in this path.

## What passing means

A passing bridge establishes interoperability of this Rust producer and the
complete Node-executed application reader for these inputs, plus the specified
corruption checks. This is stronger than the earlier dependency-free arithmetic
component evaluation. It is still distinct from interactive file-picker/clear
behavior, authenticated Access routes, browser rendering, deployment, independent
scientific review and a measured user-decision benefit.

The report's `input_sha256` is a declaration to the reader. The test verifies it
against bytes submitted to the real producer, but a reader without those original
bytes cannot authenticate it. A separate test deliberately substitutes another
well-formed digest and checks that the reader continues to say source and
original-byte identity were not verified. Likewise, internally consistent
fabricated source values could pass arithmetic; this is not a signature or
source-authentication scheme.

The outcomes match a competent source-aware signed-gap and convex-hull baseline.
Passing does not demonstrate improved physical prediction or novelty. The next
system-value comparison must identify an actual mistaken inference, stale
dependency, missed qualifier or measurable review cost under an explicit
protocol. Existing finite-list limitations must stay visible even when every
arithmetic check passes.
