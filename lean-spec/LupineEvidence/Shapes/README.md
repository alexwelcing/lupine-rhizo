# Shapes — typed claim-shapes for the discovery workflow

Define the TYPE of fact an experiment can establish **before** running it;
the run then either produces a witness or it does not. This is registration
without threshold theater (formalization ladder, L3 groundwork): the shape —
structure fields, scaling convention, decidable predicate — is fixed and
reviewed ahead of the data, and a claim exists only as a kernel-checked
instance of a shape. No witness, no claim; a refusal is itself a certificate.

`Certificates.lean` is HAND-WRITTEN and dependency-free (core Lean only,
integers x10000 as everywhere in the corpus). It ships the shapes —
`CubicElastic`/`bornStable`, `ConcordanceWindow` with the
concordant/flagged/refused trichotomy, `AnchorCalibration`/`wellAnchored`,
`Refusal`/`orderJustified` plus the `no_monotone_fix` finality lemma — and
the exact integer `roundingRobustInflationGate` and
`roundingRobustDeflationGate` predicates for nearest-rounded correction inputs.
It also includes worked examples showing the instantiation pattern: structure literal,
predicate, `by decide`.

## Instantiation contract (generators)

- Emitters (binder CLI `--emit-lean`, Round emitters) produce instances; they
  never edit this module. One module per run cell, named
  `Certificates_<system>_<model>.lean`, landing in `LupineEvidence/Discovery/`.
- Generated modules import `LupineEvidence.Shapes.Certificates`, carry the
  standard `/- AUTHORED by/from ... -/` header with input sha256, prove every
  claim by `decide`/`omega` (0 sorry), and must be added to the
  `LupineEvidence.lean` manifest (`scripts/check_evidence_manifest.sh` gates
  the bijection; `lake build LupineEvidence` must stay green).
