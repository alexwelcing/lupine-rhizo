# A6-DECIDE corrected source remediation

## Verdict

**INCONCLUSIVE under the frozen preregistered rule.**

The actual preregistered **MPtrj test** source exists, but it fails the mandatory pre-inference trajectory information gate. The pinned test parquet contains 10,273 rows. After the frozen schema, element, atom-count, finite-label, and nonzero-force filters, it has 8,933 valid configurations across 8,586 task/trajectory IDs; no block has the required eight configurations, and the observed maximum is 4. Therefore zero blocks are eligible: the source fails the frozen minimum of 30 independently bootstrappable blocks, at least 8 configurations per retained block, and at least 240 total configurations. It also cannot reach the deterministic 50-block × 8-configuration sampling target, so no MPtrj test model execution was launched.

OMat24 and MatPES retain their exact reviewed manifests and raw model outputs and still pass all three pairs at every seed. They do not rescue the global verdict because the frozen rule requires every source/integrity gate to pass before a support or scope-truncating verdict. The prior MPtrj train-shard result is excluded, not relabeled.

## Corrected source identity and exact failed gate

- Frozen identity: `MPtrj test`.
- Dataset: `nimashoghi/mptrj`.
- Pinned revision: `f88fbe46e16524223210654bad9e1b05a15c2adb`.
- Resolved split/file: `test` / `data/test-00000-of-00001.parquet`.
- Parquet SHA-256: `cb77ce289ba73357be0cc375df40631d0df0541e7120913cb2e89a17aae19add`.
- Input-lock SHA-256: `7eb304c4db4d4243bda01cd5928eba6df218ec06d2d842667f916c5159592b3a`.
- Failed gate: MPtrj test has 0 trajectory blocks with >= 8 eligible configurations; frozen minimum is 30 independently bootstrappable blocks with >= 8 configurations per retained block and >= 240 total configurations; deterministic sampling target is 50 blocks.

This is a source/information refusal, not a negative model result. Running the three-model panel on a hand-made nonconforming subset would violate the frozen gate and was not done.

## Frozen decision rule

The preregistration remains unchanged: each source must provide at least 30 independently bootstrappable blocks, at least 8 configurations per retained block, and at least 240 total configurations; 50 blocks × 8 configurations is the deterministic sampling target. The primary endpoint is `field_cos`; independent Haar SO(3) rotations are applied per model × configuration; 5,000 null and 2,000 trajectory/material-block bootstrap replicates run at seeds 42, 1729, and 20260803; Holm correction is within source; pair pass requires adjusted p <= 0.05 and bootstrap q025 above the geometry-null mean; source pass requires at least two pairs. Final support requires OMat24 plus MPtrj or MatPES, with all information/integrity gates and seed-stability gates satisfied. Otherwise the verdict is `INCONCLUSIVE` with the failed gate.

## Retained exact-hash evidence

The three-model panel is retained on MatPES and OMat24. Their manifests are byte-identical to the independently reviewed set:

- MatPES manifest SHA-256: `babbe09075f8827f04c7532e5bf58d4fe1ab763ed2a176a271813d973ceeca79`.
- OMat24 manifest SHA-256: `f15d949dd11527903c2025f0b011f95e06d6553d9c3f9f38a09a0235f7fb2bfa`.

| source | model pair | observed | null mean range | bootstrap q025 range | Holm p (all seeds) | pair passes |
|---|---|---:|---:|---:|---:|---|
| MatPES-PBE-2025.2 | CHGNet / M3GNet | 0.606520 | -0.000074–0.000684 | 0.506829–0.515708 | 0.00059988 | yes |
| MatPES-PBE-2025.2 | CHGNet / MACE-MP-small | 0.573168 | -0.000274–0.000295 | 0.502413–0.505027 | 0.00059988 | yes |
| MatPES-PBE-2025.2 | M3GNet / MACE-MP-small | 0.429047 | 0.000041–0.000128 | 0.352175–0.355930 | 0.00059988 | yes |
| OMat24 validation AIMD PBE-1000 NVT | CHGNet / M3GNet | 0.613469 | -0.000637–-0.000094 | 0.500112–0.506542 | 0.00059988 | yes |
| OMat24 validation AIMD PBE-1000 NVT | CHGNet / MACE-MP-small | 0.556731 | -0.000838–0.000235 | 0.399037–0.405987 | 0.00059988 | yes |
| OMat24 validation AIMD PBE-1000 NVT | M3GNet / MACE-MP-small | 0.459926 | -0.000070–0.000354 | 0.346854–0.348969 | 0.00059988 | yes |

Both retained sources remain seed-stable and pass 3/3 pairs. These retained results are subordinate to the global `INCONCLUSIVE` verdict because MPtrj test fails its information gate.

## Excluded MPtrj train-shard diagnostic

The historical `train/0000.parquet` executions and their hashes remain in the corrected ledger with `evidence_status: excluded_nonpreregistered_source` and `frozen_decision_eligible: false`. The previously observed CHGNet/M3GNet bootstrap heterogeneity is reproducible for that excluded train shard, but it is **not** evidence about MPtrj test and is not used in the corrected decision.

## Execution and cost ledger

- Historical Cloud Run records preserved: 12.
- Retained frozen-decision-eligible MatPES/OMat records: 8.
- Excluded MPtrj train-shard records: 4.
- New MPtrj test model executions: 0, because the pre-inference source gate yielded no conforming manifest.
- Actual billed cost: unavailable (`null`); no dollar estimate, substitute, or derived dollar claim is provided.

## Reproducibility and verification

- Build source lock/manifests: `python3 build_a6_manifests.py`.
- Analyze retained evidence and failed source gate: `python3 analyze_a6_decide.py`.
- Mechanical verification: `python3 verify_a6_decide.py`.
- Repository-owned retained-manifest validation: `PYTHONPATH=/home/alex/Dev/lupine/lupine-rhizo/python python3 run_repository_validator.py`.
- Corrected analysis SHA-256: `85e9ba9d46abb3b566d59a1b449abe0c0a35d75f403241735bbbcf77a863dffa`.
- Corrected execution ledger SHA-256: `305560bf47fc94b94326b33b281b9df8d915e1432f13144bbabcdddea10c33e4`.

No preregistration rewrite, canonical/public claim, repository commit, merge, deployment, or publication was performed.
