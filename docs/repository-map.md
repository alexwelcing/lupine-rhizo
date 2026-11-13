# Lupine Rhizo: repository map

Moved from the root [README](../README.md) on 2026-11-13, when the README was cut
to one screen. The text is unchanged; only link paths are adjusted for this folder.

## Layout

| Path | What it is |
| --- | --- |
| `distill/`, `python/` | Rust and Python scoring engines, including fixed- and random-effects meta-analysis of correlation coefficients across independent groups |
| `lean-spec/` | Lean 4 checks of the arithmetic and inequalities behind published numbers |
| `gcp/`, `hpc/` | Benchmark cell runners: Cloud Run jobs, and the offline Apptainer/SLURM lane |
| `glim-think/` | The task scheduler and research record behind the public activity feed |
| `campaigns/`, `registry/`, `snapshots/`, `evidence/`, `data/` | Preregistered campaign manifests, claim registry, status snapshots and evidence records |
| `docs/`, `paper/`, `replication/` | Research notes, manuscripts and replication kits |
| `exports/` | Public export contracts read by the Library and the website |
| `tools/`, `scripts/` | Command-line tools, checks and export generators |

## Boundary

Rhizo publishes; the public sites consume. It does not hold the
[lupine.science](https://lupine.science) site, the
[Library](https://library.lupine.science) reader or the [Lupi](https://lupi.live)
viewer. The Library reads `exports/library-content/latest/`, regenerated with
`node scripts/export_library_content.mjs` and verified by the reader before it
renders.

Related repositories: [lupine-science](https://github.com/alexwelcing/lupine-science)
(public site) · [lupine-ledger](https://github.com/alexwelcing/lupine-ledger)
(Library reader) · [Lupi](https://github.com/alexwelcing/Lupi) (browser viewer) ·
[lupine](https://github.com/alexwelcing/lupine) (historical monorepo).

## More

- [Overview](overview.md)
- [Results in detail](results-detail.md)
- [Development](development.md)
