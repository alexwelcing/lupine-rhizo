# Validation audit expands exclusion checks to 805 inspected cases

Date: 2026-10-06. Status: completed provenance audit; independently source-checked. **Fresh validation is not ready.** This visit ran no new predictions and inspected no candidate error outcomes.

## Question and decision

Can the pinned MPtrj test source support an outcome-blind validation of the fixed error-ranking scores from the [rank-fusion analysis](./2026-10-06-rank-fusion.md)?

The audit found that the earlier five-case pilot already used the same MPtrj test **source family**, at an unrecorded revision. Future exclusions must therefore cover **805 previously inspected configurations**, including those five cases and the 800 archived panel cases. This is additional known exposure to account for, not proof of overlap with the pinned candidate revision.

We constructed and independently checked an exclusion index covering **7,343 atoms**. All 805 exact ordered geometry fingerprints are distinct. The candidate parquet and an adequate saved identity receipt were absent from the declared local workspace/output search and corrected evidence bundle, so the candidate intersection remains **uncomputed**. This bounded search does not establish absence elsewhere.

Two explanations remain open: a suitable disjoint panel may exist after provenance recovery, or shared cases/materials and incompatible provenance may prevent the intended comparison. The discriminating observation is a hash-verified candidate identity comparison plus exact model/reference provenance, before inspecting new prediction errors.

## Eligibility gates

| Gate | Observation | Decision |
| --- | --- | --- |
| Candidate identity | A revision and parquet digest are recorded; candidate bytes were unavailable in the bounded local audit. | Recorded identity available; current bytes not rehashed. |
| Independence from score development | 805 inspected cases indexed, including five from an unpinned MPtrj test revision. | Candidate disjointness uncomputed. |
| Exact original models | Six archived headers contain package versions but no exact loaded weight digests or resolved checkpoint identity. | Original checkpoint identity not established. |
| Cached prediction provenance | Both M3GNet artifacts report 400 cached predictions loaded and zero newly written. | Final process metadata does not establish the original cache producer's weights. |
| Reference compatibility | Retained panel metadata labels MatPES DFT-PBE and OMat24 PBE+U; necessary per-case settings are incomplete. | Compatibility with candidate calculations not established. |
| Independence from model training | The candidate's source split is named test; exact model training/tuning membership is unavailable. | Training independence unknown. |
| Grouping | Historical A6 grouped task IDs; these are not proven independent materials. | A separate outcome-blind grouping contract is needed. |

Package versions, current loader defaults and image tags resolved after a run cannot fill the historical weight-identity gap. The available M3GNet loader has an overridable MatPES-named default; this does not prove what produced the archived predictions or establish training overlap. Missing provenance is not evidence of poor model performance.

The previous arithmetic results remain statements about their stored predictions and references. This audit narrows what can be claimed about transporting those results to a new panel.

## Source and grouping limits

The [preserved input lock](../../evidence/a6-decide/manifests/input-lock.json) records `nimashoghi/mptrj`, revision `f88fbe46e16524223210654bad9e1b05a15c2adb`, file `data/test-00000-of-00001.parquet`, SHA-256 `cb77ce289ba73357be0cc375df40631d0df0541e7120913cb2e89a17aae19add`.

Its historical counts are 8,933 valid configurations across 8,586 task IDs, maximum four per ID and zero groups satisfying the old eight-frame gate. These counts were checked against the preserved lock, **not recomputed from the absent parquet**. The [manifest builder](../../evidence/a6-decide/build_a6_manifests.py) groups by task ID and retains material ID separately. Those namespaces must remain separate. Historical A6 remains **INCONCLUSIVE**; excluded training-source executions and stopped jobs retain their original states.

The exact fingerprint contract hashes ordered element symbols, positions, cell and periodic flags, using finite binary64 hexadecimal numbers and normalized signed zero. It detects exact representation equality. It does not detect equivalence under atom permutation, rotation, periodic translation, lattice changes, tolerance or supercells. Distinct hashes or IDs alone cannot prove physical or material independence.

## Proposed test contract — not registered or executed

Freeze the existing full disagreement, three pair scores, force-magnitude control and rank fusion. The proposed primary question is whether full disagreement exceeds every individual pair on a new panel; rank fusion remains secondary. No additional score variants are selected on the 800 reused cases.

For a distinct future protocol, the grouping review proposes components linked by normalized material ID, task ID or exact geometry, excluding any component linked to the 805 known cases. Unresolved cross-source mappings must remain an explicit independence limitation. A bounded target of 400 components, one configuration each, would use a fixed identity-derived hash order and structural checks only, with no force/error thresholds. This is a resource bound, not a statistical power guarantee. If insufficient eligible components remain, do not silently change or backfill the target after outcomes are opened.

Sampling, tie/zero-error rules, completeness, uncertainty and multiplicity decisions must be frozen before unsealing outcomes. No candidate manifest was built or sampled during this audit. Continuing the original model comparison requires historical checkpoint provenance; substituting newly pinned models would define a separate study.

## Verification and next action

An independent verifier passed **4,129 assertions with zero failures**. It reconstructed all 805 fingerprints using IEEE754 bit fields independently of the primary formatter, checked IDs and atom counts, repeated the bounded file inventory, and confirmed preserved source counts and historical receipt hashes. This verifies the stored evidence audit and exclusion index, not unseen candidate bytes, physical independence or fresh scientific performance.

Next: perform one bounded read-only recovery of pinned candidate identity/geometry metadata and original checkpoint/cache provenance through existing authorized archive access. Verify source bytes against the recorded hash, then compute exclusions before opening candidate errors. If exact original weights cannot be recovered, record that limit and design a distinct pinned-roster protocol. Predictions remain gated on an eligible, frozen test.

## Evidence anchors

Raw archives, IDs, coordinates and detailed receipts remain private. These hashes identify local artifacts and do not supply public reproduction inputs.

- Frozen audit protocol: `b4791d82babf247d4084381d759d141b085602a3e3a2b2781dfd3a7492db06e2`
- Primary result: `c9cef4cac0e5f322c608ef4d959802e7a717c44817def9b16fcf000c25d57efb`
- Exclusion index: `56ca5907cf800521f300addeb348111688e03e304bf712f8e70a9a80b2b5bb61`
- Model/reference audit: `6712d260e9662d888d306c4357461d3b96e837c53bc1f2cc175d5cb7ee27dfdf`
- Independent verification: `4e07117a7ddd53f56af6246ca73547b306508bde4e5d68a9c249ea83b245c5b2`
