# Z2 Abstention Audit — Round-4 spin-aware multi-fidelity campaign

**Status:** content-addressed audit · scope amended to abstention by director/owner decision 2026-07-19
**Campaign:** `discovery.round-4.z2-magnetic-anisotropy.v1` (`campaigns/v1/z2.campaign-manifest.v1.json`, content hash `sha256:` per manifest)
**Rows:** `data/candidates/z2/measurements.jsonl` (4 rows, RFC 8785, hash chain tail `sha256:1019cff0…`), `data/candidates/z2/artifact-manifest.json`
**Reconstruction note:** the original t_52df7aae deliverable was lost with its kanban scratch workspace. The findings below are re-derived from repository state and match the original audit's claims; the original blocker document's SHA-256 was `c0c0e31773fa06d51d7310ffe19de42a59e1db95870ac32636d31e1d5bb450c3`. No original content hashes are claimed here; all artifacts in this package carry their own, new content addresses.

## Question

Can the declared available models reproduce the complete held-out
magnetocrystalline-anisotropy ordering, including easy-axis sign, on a
locked reference panel (frozen hypothesis `h.z2.anisotropy-ranking`)?

## Verdict: this pipeline smoke must abstain — scientific execution is separately owner-gated

The same preregistration freezes `h.z2.scalar-abstention`: "scalar-energy rows
without spin-orbit-resolved evidence abstain and cannot count as ranking
successes." The repository now contains the prerequisites for a separate
scientific campaign: `gcp/mlip-cell-runner/z2_soc_tc.py`, the seven-material
`data/candidates/z2_soc_tc_panel.lock.json`, and
`registry/claims/discovery.z2.magnetic-anisotropy.v1.json`. The campaign
manifest also freezes both anisotropy ranking and Tc prediction hypotheses.

Those additions do not turn this B1 proof into a scientific result. This smoke
is intentionally limited to replaying four frozen abstention rows so it can
exercise unified-image packaging, GCS delivery, and authenticated beat delivery
without loading a calculator. The SOC/Tc runner and locked panel are deliberately
not evaluated, the ClaimContract remains `unsupported`/`pending`, and cloud
scientific executions for these rows remain **zero**.

## What was produced instead

Four content-addressed measurement rows — one per declared available model —
each recording `epistemic_status: unsupported`, `sample_count: 0`, and
`acceptance_test.outcome: abstained` with the explicit rationale. The rows are
RFC 8785 canonicalized and hash-chained to the campaign manifest hash, built
deterministically by `tools/build_z2_abstention_rows.py`.

## Path to scientific measurement scope

Run the separately owner-gated SOC/Tc campaign against the existing locked
seven-material panel, preserve its preregistered failure policy, and materialize
the resulting aggregate evidence into the existing ClaimContract and runtime
gate. Only successful content-addressed SOC/Tc measurements can supersede these
pipeline-proof abstention rows; the existence of the runner, panel, and contract
alone cannot do so.
