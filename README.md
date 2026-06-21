# Lupine Rhizo

The Lupine science root system.

Rhizo is the deep workbench for the Lupine open-science program: Lean proofs,
Rust and Python science engines, MLIP benchmarking loops, evidence generation,
agents, telemetry, and the export contracts consumed by the public repos.

If you want the polished molecular viewer, clone **Lupi**. If you want the
public research record, read **Lupine Ledger**. If you want the math, LAMMPS
bridges, MLIP loops, proof obligations, and control-plane machinery, this is
the place.

## Boundary

Owns:

- `glim-think`: durable agenda, ledger, routes, feed, evals, and agent loop
- `cocoindex`: evidence indexing experiments for corpus export/query loops
- `atlas/compute`: Cloud Run physics compute lane used by `glim-think`
- `lean-spec`: Lean proof/specification layer
- `atlas-distill`: Rust scoring, policy, benchmark, and fault-line engine
- `python`: Python Distill packages and runtime helpers
- `mlip_immi`: real-data MLIP/IMMI analysis lane
- `gcp`: burst compute, MLIP cells, evidence indexing, and control-plane services
- `cloudflare`: edge/control-plane infrastructure helpers
- `tools`: local science CLIs, telemetry checks, promotion loops
- `docs`, `paper`, `replication`: source research corpus and reproducibility
- `exports`: public contracts consumed by Ledger, Lupi, and Science

Does not own:

- the `lupine.science` landing site
- the `library.lupine.site` reader app
- the `lupi.live` viewer app
- investor or private access surfaces
- generated caches, dependency folders, or large binary artifacts

## Sibling Repos

- **Lupine Science**: `https://github.com/alexwelcing/lupine-science`
  - Public front door.
  - Site: `https://lupine.science`
- **Lupine Ledger**: `https://github.com/alexwelcing/lupine-ledger`
  - Public evidence record and Library reader.
  - Site: `https://library.lupine.site`
- **Lupi**: `https://github.com/alexwelcing/Lupi`
  - Browser-native molecular viewer.
  - Site: `https://lupi.live`

Historical development remains in `https://github.com/alexwelcing/lupine`
during the transition.

## Quick Checks

Use Git Bash for Node and build tasks on Windows.

```bash
just think-lint
just engine-test
just live-build
```

Routine validation:

```bash
just verify-light
just verify
```

Lean proof gate:

```bash
cd lean-spec
lake build
```

Run Lean from inside `lean-spec/` so elan selects the pinned toolchain.

## Export Contracts

Rhizo publishes; public repos consume.

Current public export:

```text
exports/library-content/latest/
  manifest.json
  articles/
```

Regenerate the Library content bundle from this repo with:

```bash
node scripts/export_library_content.mjs
```

The Ledger repo verifies `library-content.v1` before rendering the public
Library.

Planned contract families:

- Library content bundles
- claim/status manifests
- molecule/evidence manifests
- viewer search and MCP schemas
- `glim-think` route/OpenAPI summaries
- brand and agent-readable text

## Orientation

- [LUPINE.md](LUPINE.md): how Rhizo fits the Lupine constellation
- [ROOTS.md](ROOTS.md): active root ownership ledger
- [AGENTS.md](AGENTS.md): operating rules for agents in this repo
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md): system map
- [docs/working-path.md](docs/working-path.md): practical checkout and checks
- [docs/repo-split-map.md](docs/repo-split-map.md): extraction map
- [docs/splits/science-control-plane.md](docs/splits/science-control-plane.md): split packet

## License

Project-owned code is licensed under AGPL-3.0-or-later. First-party non-code
content is licensed under CC BY-SA 4.0 unless noted. First-party structured
data and exported databases are licensed under ODbL 1.0 unless noted.

Third-party datasets, dependencies, papers, and imported scientific sources
retain their upstream licenses and notices.
