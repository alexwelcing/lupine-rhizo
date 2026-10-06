# Proposed MPtrj validation stops at training and reference eligibility

Date: 2026-10-06. **Source audit completed; proposed validation STOPPED BEFORE EXECUTION.**

## Decision

The bounded four-packet review does **not establish** that the pinned MPtrj candidate is independent of the proposed CHGNet, original M3GNet and MACE-MP-small checkpoints' training, validation and model-selection data. Reference compatibility is also incomplete. The [proposed 128-group study](./2026-10-06-prospective-ranking-protocol.md) therefore stops before selection or inference under its own rule.

This is a concrete eligibility decision, not a measured contamination rate or a failure of the ranking hypothesis. Shared Materials Project provenance raises an exposure question; it does not show which candidate rows trained a checkpoint. The 9,304 structurally eligible rows in 8,844 linked groups remain an inventory, not a certified holdout. Previous archived ranking results and historical A6 **INCONCLUSIVE** are unchanged.

## Four packets and what they establish

Sources were inspected on 2026-10-06. Model locations below are candidates, not a sealed or loaded roster.

| Packet | Located evidence | Missing evidence / decision |
| --- | --- | --- |
| CHGNet 0.3.0, package 0.4.2 | Versioned model card specifies **90/5/5** training/validation/test splitting. The older paper describes **80/10/10 by material ID**, with code version 0.2.0. | The paper's split cannot certify the newer checkpoint's holdout. No exact checkpoint membership-to-candidate crosswalk was recovered. **STOP**. |
| Original TensorFlow M3GNet, MP-2021.2.8-EFS | Official project identifies MPF.2021.2.8. Documentation includes a material-grouped training example and validation-based stopping. | A training example is not the shipped checkpoint's membership record. No candidate exclusion crosswalk recovered. **STOP**. |
| Original MACE-MP0 small | Original release names `2023-12-10-mace-128-L0_energy_epoch-249.model`. The associated published script names separate MPtrj train and validation files. | File names and shared dataset ancestry do not map this candidate to excluded checkpoint-development data. **STOP**. |
| Pinned `nimashoghi/mptrj` source | Revision `f88fbe46e16524223210654bad9e1b05a15c2adb` README lists schema and 1,559,916 train / 10,206 validation / 10,273 test rows. | Inspected README supplies no split-generation crosswalk, force unit/sign conversion lineage or per-row calculation-setting provenance sufficient for this claim. **STOP**. |

Primary evidence: [CHGNet versioned model card](https://github.com/CederGroupHub/chgnet/blob/8d04abc467630b30cd8349c2fe12eeab10f62171/chgnet/pretrained/0.3.0/README.md), [original CHGNet paper, 14 September 2023](https://www.nature.com/articles/s42256-023-00716-3), [original M3GNet project at inspected revision](https://github.com/materialyzeai/m3gnet/tree/c00c1be927ea60ab9708ac55c99953a7651d6f27), [original MACE release, 11 January 2024](https://github.com/ACEsuit/mace-foundations/releases/tag/mace_mp_0), [MACE training script](https://github.com/ACEsuit/mace-foundations/blob/16a9f178706ce053f3ca8531efbab00a305d0854/mace_mp_0a/2023-12-10-mace-128-L0_energy.sh), and [exact pinned dataset README](https://huggingface.co/datasets/nimashoghi/mptrj/blob/f88fbe46e16524223210654bad9e1b05a15c2adb/README.md).

## Predictor and reference boundaries

CHGNet's package tag resolves to `8d04abc467630b30cd8349c2fe12eeab10f62171`; original M3GNet source resolves to `c00c1be927ea60ab9708ac55c99953a7651d6f27`. MACE's original release tag was observed at `a2e6dec371933d3323a4439c37a8c51bfb4908f0`, with asset ID 145021750 and no advertised digest. These locate source/artifact metadata. They are **not measured checkpoint hashes or loaded-state identities**. No weights were downloaded or loaded.

CHGNet documents force output in eV/angstrom and source code computes a negative positional energy gradient. Original M3GNet documents eV/angstrom forces. The original MACE paper describes a PBE+U target without dispersion. These model-side conventions do not establish the candidate's extraction/conversion lineage, per-case U, pseudopotential, electronic/magnetic or convergence settings. The original MACE and CHGNet energy-correction conventions differ; that difference alone is not proof of a force-label mismatch. [CHGNet pinned loader](https://github.com/CederGroupHub/chgnet/blob/8d04abc467630b30cd8349c2fe12eeab10f62171/chgnet/model/model.py), [original M3GNet documentation](https://github.com/materialyzeai/m3gnet/tree/c00c1be927ea60ab9708ac55c99953a7651d6f27), [original MACE paper v1](https://arxiv.org/html/2401.00096v1).

This review did not inspect complete training archives, recover exact checkpoint-development memberships, decode candidate outcomes, select a panel, run inference or deploy a runner. Missing evidence refers to this bounded inspection, not a claim that it exists nowhere. The offline CHGNet provenance repair remains useful but cannot close scientific eligibility gates. Additional adapter implementation is no longer the immediate next step for this stopped study.

## Next distinct question — planned, not started

On the **existing, repeatedly inspected** 800 archived configurations, how much of the fixed ensemble's squared force error occurs where a common residual component exceeds inter-model contrast and the three model residuals are pairwise aligned?

Use the original three force arrays and reference, with no new predictions, score variants, row exclusions or fitted thresholds. For residuals `e_m = F_m - F*`, define `c = mean(e_m)`, `y = ||c||²`, and `v = mean(||e_m-c||²)`. Verify both identities: `mean(||e_m||²) = y + v` and `mean(pairwise e_a dot e_b) = y - v/2`.

Before calculation, freeze one descriptive test: for each configuration, measure the fraction of unchanged ensemble squared error on atoms satisfying **both** `y > v` and `e_a dot e_b > 0` for all three pairs. Average the eight configuration fractions within each original group, then equally average the 50 groups in each panel. The resulting mean must exceed one half on both panels; equality fails. Preserve all atom/configuration/group values and report pooled squared-error fractions as a fixed secondary. Independently verify arithmetic from saved forces. Any zero-total-error configuration or decision-changing numerical ambiguity withholds the primary verdict; no dropping or replacement. This is an archival common-error diagnostic, not a causal explanation, training-independence test, calibrated alarm, new score or generalization claim. Reference mismatch remains a competing explanation.

Do not resume the stopped prospective study, choose another split, or repeat a generic provenance search. A future independent validation needs a separately justified source/roster design with affirmative eligibility evidence.

## Private evidence anchors

The source packets stay local. Published hashes identify those records, not public access to their contents or full empirical reproducibility.

- CHGNet/M3GNet source packet: `cf3ce41bb87da66dea6d1bc2b580d6821b3326621bf957ba455291ea3934c523`.
- MACE source packet: `1e42e24160a9c8090d4295f22237f6de30347a5e9b48782a8217cf6d35339d07`.
