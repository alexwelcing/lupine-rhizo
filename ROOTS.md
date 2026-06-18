# Root Ownership Ledger

Rhizo is organized around `glim-think` as the durable intelligence control
plane. A root belongs here only if it supports the science loop, the proof
layer, the evidence pipeline, or a public export contract.

## Active Roots

| Root | Purpose |
| --- | --- |
| `.github/` | Rhizo CI, proof, engine, benchmark, and control-plane deploy workflows. Public-site workflows moved to sibling repos. |
| `atlas/compute/` | Cloud Run physics compute lane for `glim-think`; this is the only active `atlas/` slice retained in Rhizo. |
| `atlas/nist_ipr/index/master_index.json` | Small NIST index consumed by `atlas/compute` deploy staging. |
| `atlas/scripts/generate_nist_demos.py` | Helper vendored into the compute deploy job. |
| `atlas-distill/` | Rust Distill scoring, policy, benchmark, and fault-line runtime. |
| `cloudflare/` | Edge helpers and control-plane infrastructure around `glim-think`. |
| `data/` | Small fixtures, manifests, and evidence payloads. Large artifacts belong in object storage with manifests. |
| `docs/` | Research corpus, runbooks, decisions, split packets, templates, and hypotheses. |
| `exports/` | Public contracts consumed by Lupine Science, Lupine Ledger, and Lupi. |
| `gcp/` | Cloud Run jobs/services for burst compute, MLIP cells, evals, and task consumers. |
| `glim-think/` | Primary research control plane: agenda, ledger, feed, evals, traces, agents, and public routes. |
| `lean-spec/` | Lean 4 specifications and proof obligations. |
| `lupine-ops/` | Operational helpers used by active science code. |
| `mlip_immi/` | Local real-data MLIP/IMMI analysis scripts and evidence payloads. |
| `paper/` | Manuscript source, figures, and publication build inputs. |
| `python/` | Active Python Distill packages and instrumented runtime code. |
| `replication/` | Public replication kits and reproducibility harnesses. |
| `scripts/` | Repo-level utility scripts, including public export generation. |
| `tools/` | Local CLIs, telemetry checks, promotion loops, and research helpers. |

## Moved Out

| Surface | New repo |
| --- | --- |
| `gcp/lupine-site-router/` | `alexwelcing/lupine-science` |
| `library-site/` | `alexwelcing/lupine-ledger` |
| `atlas/atlas-view/` viewer app and Firebase viewer support | `alexwelcing/Lupi` |

Do not remove the old paths from the historical monorepo until the destination
repos are live and verified. Rhizo starts clean by copying only the science and
contract roots.

## Public Contract Rule

Rhizo publishes explicit artifacts; public repos consume those artifacts. Public
repos should not reach into Rhizo source paths during normal build/deploy.

Current contract:

- `exports/library-content/latest/manifest.json`

Planned contracts:

- claim/status manifests
- viewer molecule/evidence manifests
- MCP/search schemas
- `glim-think` OpenAPI/routes summaries
- brand and agent-readable metadata

## Verification

Focused checks:

```bash
just think-lint
just engine-test
just live-build
```

Routine checks:

```bash
just verify-light
just verify
```

Heavy/release checks:

```bash
just verify-heavy
```

Lean checks must run from `lean-spec/`:

```bash
cd lean-spec
lake build
```
