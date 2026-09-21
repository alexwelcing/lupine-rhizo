# ADR 0007: Browser-agent evidence enters only as receipts; trial Prove2Me as the theorem commons, private first

**Status:** Proposed

**Date:** 2026-09-21

**Author:** Research loop (discovery-tooling evaluation)

**Context doc:** [`docs/research/discovery-tools-fastbrowse-prove2me-2026-09-21.md`](../research/discovery-tools-fastbrowse-prove2me-2026-09-21.md)

---

## 1. Context

Two external tools were evaluated for the gather and prove ends of the
research loop.

- **fastbrowse** (MIT, pre-alpha, v0.4.2) is a browser agent whose every
  answer carries verbatim page quotes with URL and page-capture hash, at a
  median cost near half a cent per task in its own evals.
- **Prove2Me** (API v0.10.7, paper arXiv:2608.28433) is a crowdsourced Lean 4
  formalization platform with server-side kernel checking, disproofs,
  blind read-back audits, permanent attribution, and Apache 2.0 public
  theorems.

This repo already treats every number as needing a receipt (LAMMPS traces
with hashes, citation audits, Lean gates). The Research Command Center names a
shared theorem commons as the program's amplifier. Neither tool is in use yet.

## 2. Decision

1. **Browser-agent output never enters the ledger directly.** The only path is
   a `web-evidence-receipt.v1` record built by `tools/web_evidence_receipt.py`
   from the agent's raw JSON. A receipt is `citable` only when the run ended
   `complete` with at least one quote. Receipts are `observed` evidence and
   never change a claim's status on their own. Digests cite quotes, not the
   agent's answer.
2. **v0 browser runs touch public pages only.** No `--authorize`, no secrets,
   no Lupine credentials, dollar and step caps on every run, raw run JSON
   committed next to its receipt.
3. **Trial Prove2Me with a private mission first.** Port the Mathlib-light
   correction-license theorems (`Materials/Theory/SharpLicense.lean` plus the
   `Shapes/Certificates.lean` definitions) to a platform environment and
   round-trip an `ACCEPTED` verdict. Modules that use `native_decide` are
   excluded because the platform rejects the axiom it introduces.
4. **Public release is a separate owner decision**, taken per mission, because
   it is permanent and relicenses the published statement and proof under
   Apache 2.0 (this repo's code is AGPL-3.0).

## 3. Consequences

- **Positive:** cheap, cited web lookups with a tamper-evident hash chain;
  independent adversarial checking of our Lean statements; a working commons
  with attribution that we do not have to build.
- **Cost:** two API keys and a small OpenRouter spend for browser runs; an
  elaboration port from Lean v4.29.0 to v4.33.1 for any theorem we publish.
- **Risk accepted:** fastbrowse is pre-alpha, so the receipt tool validates
  field by field and fails closed rather than trusting the shape.
- **Not decided here:** any change to the `library-content.v1` contract, any
  public mission, any use of browser agents on authenticated pages.

## 4. Review trigger

Revisit after experiments E1 and E3 in the context doc report, or if
fastbrowse changes its result schema, or if Prove2Me drops the v4.29.0-rc3
environment.
