# Z2 Abstention Audit — Round-4 spin-aware multi-fidelity campaign

**Status:** content-addressed audit · scope amended to abstention by director/owner decision 2026-07-19
**Campaign:** `discovery.round-4.z2-magnetic-anisotropy.v1` (`campaigns/v1/z2.campaign-manifest.v1.json`, content hash `sha256:` per manifest)
**Rows:** `data/candidates/z2/measurements.jsonl` (4 rows, RFC 8785, hash chain tail `sha256:05d3b087…`), `data/candidates/z2/artifact-manifest.json`
**Reconstruction note:** the original t_52df7aae deliverable was lost with its kanban scratch workspace. The findings below are re-derived from repository state and match the original audit's claims; the original blocker document's SHA-256 was `c0c0e31773fa06d51d7310ffe19de42a59e1db95870ac32636d31e1d5bb450c3`. No original content hashes are claimed here; all artifacts in this package carry their own, new content addresses.

## Question

Can the declared available models reproduce the complete held-out
magnetocrystalline-anisotropy ordering, including easy-axis sign, on a
locked reference panel (frozen hypothesis `h.z2.anisotropy-ranking`)?

## Verdict: the campaign cannot be executed honestly — abstention is the preregistered answer

The same preregistration freezes the escape hatch: `h.z2.scalar-abstention` —
"scalar-energy rows without spin-orbit-resolved evidence abstain and cannot
count as ranking successes." Every precondition for honest execution is absent:

1. **No spin-capable runner.** The MLIP cell runner exposes rows
   `adsorption_energy, elastic_constants, energy_volume, forces, stress,
   relaxation_stability` (`python/lupine_distill/fixture_contract.py`,
   `ROW_IDS`) — all scalar energy/forces/stress-derived. No SOC,
   non-collinear magnetism, anisotropy, or Tc path exists for any declared
   model (chgnet 0.4.2; mace-torch 0.3.16 small / medium / mpa-0-medium).
2. **No reference panel.** The frozen manifest requires ≥5 held-out SOC/Tc
   reference materials with uncertainties; no such locked panel exists, and
   none was fabricated.
3. **No ClaimContract.** `registry/claims/discovery.z2.magnetic-anisotropy.v1.json`
   does not exist, so no ingestion target can lawfully receive Z2 rows;
   materialization stays fail-closed by design.
4. **Tc outside the frozen scope.** The manifest preregisters the anisotropy
   *ordering* only; no Tc metric or premise is frozen, so Tc numbers would be
   unpreregistered claims.

Executing anyway would require fabricating a panel, a runner capability, or a
claim — each independently disqualifying. Cloud compute spend for this audit:
**zero executions**.

## What was produced instead

Four content-addressed measurement rows — one per declared available model —
each recording `epistemic_status: unsupported`, `sample_count: 0`, and
`acceptance_test.outcome: abstained` with the explicit rationale. The rows are
RFC 8785 canonicalized and hash-chained to the campaign manifest hash, built
deterministically by `tools/build_z2_abstention_rows.py`.

## Path back to full scope

Kanban `t_052adac7` (parked per owner decision 2026-07-19 until Z1/Z3/Round-4
execution completes): build a spin-aware runner (SOC / non-collinear MAE
ranking + Tc), source an honest published ≥5-material SOC/Tc reference panel
with the Z1/Z3 locking conventions, author the missing Z2 ClaimContract, and
amend the manifest to bring Tc into preregistered scope. Only then does this
audit get superseded by real measurement rows.
