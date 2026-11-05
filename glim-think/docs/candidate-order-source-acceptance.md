# Public-source candidate-report acceptance

This bridge tests the actual `distill candidate-order` executable's JSON
through the application validator, bounded local-file reader and static React
view. It uses reviewed public-table summaries from four publications. It does
not introduce a new ranking method or infer physical validity from report
acceptance.

## Cases and expected decisions

The fixture is
`distill/tests/fixtures/candidate_order_sources.json`.
Five reports contain fourteen listed alternatives, not fourteen new corpus
observations or independent studies.

| Fixture | Decision among supplied alternatives | Exposure and scope |
| --- | --- | --- |
| Olsson 2005 Cr | Model and VASP both choose the listed 110 interstitial. | Relaxed defects enter fitting; paramagnetic Cr; assumed independent ±0.005 eV printing bounds. |
| Ko 2015 Ni in hcp Ti | DFT selects the lower in-basal barrier; 2NN-MEAM selects the lower out-of-basal barrier. | Barrier ordering only. Exact initial/path identities, prefactors and per-defect fitting exposure remain unresolved. Assumed ±0.0005 eV printing bounds. |
| Kobayashi 2017 NN | PBE and NN choose Mg + Mg2Si over Mg3Si and the elements. | Each alternative contains 3 Mg + 1 Si. NN configurations enter training; static unconstrained mixtures; finite list. |
| Kobayashi 2017 reported Jelinek MEAM | PBE chooses Mg + Mg2Si; MEAM chooses the elements. | Same balanced alternatives. Exact MEAM row-level fitting exposure and model artifact remain unknown. |
| Suárez-Recio 2025 W | DFT and MLIP-W choose the listed 111 dumbbell. | Protocol and scientific implementation frozen before full-text inspection; abstract exposed; same-agent extraction; defect-family training exposure; assumed ±0.005 eV printing bounds. |

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
purpose. Each case links the primary publication. The first four are manually reviewed,
known-outcome acceptance fixtures. The fifth follows the separately frozen
[tungsten protocol](tungsten-task-review.md), with abstract exposure and
same-agent transcription disclosed. None is an independently validated physical
holdout. No private corpus packet or research-team artifact is included.

The [failure map](exception-to-theorem-failure-map.md) preserves the original
analysis dates, sources, scientific qualifications and competent-baseline
comparison. These acceptance inputs are a later representation of that evidence,
not a new independent validation.

## Full-path checks

The existing Distill CI test job first builds its release executable. A bounded
step then uses the existing locked Node dependencies and runs:

    DISTILL_BIN=/absolute/path/to/distill \
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


## Browser interaction acceptance

The same Distill CI acceptance step also runs
`scripts/testing/candidate-order-browser.test.mjs` against the runner's installed
Chrome. It bundles the actual `InspectCandidateOrderReport` component in memory,
serves it only on loopback, and selects temporary public/synthetic JSON files using
Chrome's file-input API. No browser package or binary is downloaded.

Twelve reader browser cases cover the five public fixture reports and their visible
limits/provenance, clear and same-file reselection, corrupt arithmetic replacing a
valid result, malformed/empty/oversized files, explicit unknowns, clearing during a
pending read, a newer selection superseding an older read, and application
network/storage boundaries. The race cases deliberately delay native
`File.text()`; the normal file, validator and React rendering paths remain real.
Mouse events operate the summary and clear controls. The test stops at its first
failed case. It has a 90-second ceiling within the existing two-minute acceptance
step; individual CLI calls remain bounded to ten seconds and 512 KiB.

The harness checks page requests and instruments application transport/storage
APIs; it does not claim to audit all browser-process network activity. It uses an
ephemeral browser profile and removes its temporary reports/profile afterward.
The installed browser version is recorded in the test output. GitHub's
[runner image inventory](https://github.com/actions/runner-images/blob/main/images/ubuntu/Ubuntu2404-Readme.md)
documents the preinstalled browser; the test fails if it is unavailable.

This is isolated-component browser acceptance, not an operating-system file-dialog
test, full RUNS feed or authenticated/deployed acceptance, source authentication,
scientific validation, or evidence of improved simulation decisions. The first four
known-outcome reports remain acceptance fixtures; the fifth has the separately
recorded frozen-code evaluation boundary. New pending-read timing
controls are test harness code, not product behavior. Hosted results must be
reported separately from this test's preparation.

## Existing verification-preview controls

The browser harness also mounts the actual verification-preview control using
explicitly synthetic proposal props. Three separate controls check optional
vacancy-attachment transport, invalidation after editing or draft replacement,
and server rejection without retry. Their response transport is a declared double;
no authenticated request is made. The native research-runs integration test
separately sends the actual client request through the actual route and assessor
against a receipt-validated synthetic run in SQLite. These controls do not turn
a candidate report into a vacancy attachment or a set of configurations into
model arms. Genuine-run and deployed acceptance remain separate.
