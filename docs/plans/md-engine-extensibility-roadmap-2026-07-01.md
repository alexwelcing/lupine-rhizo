# MD Engine Extensibility — Assessment and R&D Roadmap (2026-07-01)

Goal of this review: make the MLIP/MD engine extensible so that external
research teams can (a) onboard quickly, (b) run experiments on their own HPC
superclusters, and (c) contribute run data back in a form that drives further
theorem formalization.

Method: full read of the theory corpus (`docs/formal-*`, `docs/conjectures/`,
`lean-spec/`), a code map of the compute plane (`python/`, `gcp/`,
`mlip_immi/`, `atlas-distill/`, `tools/`, `replication/`), a map of the
data/contribution surfaces (`data/`, `exports/`, CI workflows), and hands-on
verification: the Python, tools/gcp, and Rust test suites were executed on a
clean Linux container.

---

## 1. What was verified to work and what was verified broken

Run on a fresh Linux checkout (Python 3.11, Rust stable):

| Gate | Result |
| --- | --- |
| `python/` unit+integration suite | **103 passed, 1 skipped** (after installing `pydantic`, `numpy`, `ase`, `click` by hand) |
| `atlas-distill` `cargo test` | **100 passed, 0 failed** |
| `tools/` + `gcp/` suite | **13 failed, 143 passed** |
| `config/mlip_elastic_benchmark.yaml` §9 repro contract | **Broken** — `Apptainer.def`, `lupine/data/targets_0K.json`, `lupine/python/lupine/operator.py`, `scripts/verify_mlip_elastic_benchmark.py` do not exist |

The 13 failures decompose into exactly two causes, both extensibility
failures rather than science failures:

1. **Machine-local data assumed present.** Tests and the default evidence
   campaign validate paths like `atlas-distill/lammps_runs/Ni_Mishin-1999/`
   (EAM potential files + `result.json`), which are not committed and exist
   only on the primary dev machine. `tools/test_mlip_evidence_campaign.py`
   reports 29 missing-source errors on a clean clone.
2. **Windows hardcoding.** `tools/build_ni_distill_support.py:203` constructs
   the potential path with `str(...).replace("/", "\\")`, which produces
   `atlas-distill\lammps_runs\...` on Linux and fails unconditionally.
   Sibling patterns: `python/scripts/run_ni_gpu_loop.py` docstring pins
   `C:/Users/alexw/...`; `mlip-elastic-benchmark/fill_benchmark_placeholders.py`
   defaults to `/home/alex/Dev/lupine/...`; `TORCHDYNAMO_DISABLE=1` Windows
   workaround is copy-pasted in 4+ modules.

Additional latent defects found by inspection:

- `python/lupine_distill/backends/torchsim.py:103` ignores the caller's
  `model_id` and always loads MACE-medium — silent wrong-model risk.
- `python/lupine_distill/runner.py:92`: the `ase` and `lammps` backends in the
  schema enum are `NotImplementedError` stubs.
- `gcp/mlip-cell-runner` is mid-migration (`DECOMMISSION.md`) with both old
  per-backend Dockerfiles and `Dockerfile.unified` live.
- `replication/error-geometry/patch_matgl.py` rewrites installed `matgl`
  sources in place to survive torch ≥ 2.11 — will silently break on upgrades.

## 2. Theory assessment — what the formal layer actually holds

The scientific core (hyper-ribbon low-dimensionality of potential error
vectors, the distillation/correction program built on it, and the
self-correcting conjecture ledger) is genuinely strong methodologically —
the refutation discipline in `docs/conjectures/ledger.md` is the most
defensible asset in the repo.

The formal layer is real but narrower than the prose implies, and external
teams will notice:

- The ~264 Lean declarations build green and sorry-free, but are almost
  entirely `native_decide`/`decide`/`rfl` over **embedded constants** —
  reproducible compile-time arithmetic, not symbolic mathematics. The
  headline empirical theorem (`HyperRibbonEmpirical.lean`) is one inequality
  over one hard-coded float.
- The six meta-scientific hypotheses (H1–H6) are `structure`s with
  `statement : String` — typed prose, not checked propositions.
- **Counter drift:** `Vision.lean` hand-types `computationallyProvenCount := 77`
  (guarded only `>= 10`); `ATLAS_Lean_Integration_Review.md` says 47;
  actual declaration count is ~264. Nothing reconciles these.
- **Retraction lag:** the 2026-06 Born-screening re-audit retracted the
  "14/15 on-ribbon" MLIP-transfer count, but `docs/formal-audit.md` still
  asserts the strong verdict. The formal narrative is ahead of the screened
  evidence.
- The data→theorem generators exist (`atlas-distill/src/formalize.rs`,
  `tools/mlip_distill_atlas.py`, `scripts/generate_lean_data.py`) but are
  hand-invoked, one-directional, and unchecked: no CI regenerates the
  generated `.lean` files from their source JSON/CSV and fails on drift. The
  "closed scientific loop" is currently a design document, not wired
  infrastructure.

## 3. The extensibility gap for an external HPC team

An outside team today can: read the corpus, compile the Rust engine, run the
Python unit suite, and reproduce `replication/error-geometry/` end-to-end
(the Zenodo kit is the one clean, first-class external artifact — it is the
template everything else should follow). They cannot do the three things the
program needs from them:

1. **Run on their cluster.** Execution lanes are Local-Windows (`uv`), GCP
   Cloud Run Jobs (hardcoded project `shed-489901`, `gs://` manifests), and
   HF Jobs. There is no SLURM/PBS/Apptainer lane, no LAMMPS backend, and the
   cell runner requires `--manifest-url gs://…` inputs and POSTs beats to the
   private worker.
2. **Contribute data back.** The only ingest path is
   `POST https://glim-think-v1.aw-ab5.workers.dev/...` gated by
   `INTERNAL_TASK_TOKEN` (`mlip_immi/ingest_to_worker.py`,
   `tools/glim_mlip.py`). There is no PR-based submission contract, and
   `verify.yml` validates code only — a malformed campaign JSON under
   `data/**` passes CI untouched despite excellent Pydantic schemas and
   validator CLIs existing.
3. **Extend the engine.** There are two divergent calculator registries
   (`gcp/mlip-cell-runner/mlip_cell_runner.py:load_calculator` vs
   `mlip_immi/elastic_constants.py:make_calculator`) with different model
   rosters, three copies of the strain-energy elastic harness
   (`mlip_immi/elastic_constants.py`, `replication/error-geometry/harness.py`,
   `fixture_contract.py:_fit_elastic_constants`), and at least three
   independent element/reference tables. Adding one backend today means
   editing an if/elif chain, `backend_catalog.json`, a `requirements-*.txt`,
   and `pyproject` extras in lockstep.

## 4. Most valuable path forward

The single highest-leverage insight: **the cell contract already exists and
is good.** `run-cell` takes a JSON manifest, produces a schema-versioned
`lupine.mlip.cell_result.v1` with SHA-256 checkpointing and runtime
provenance. Everything below generalizes that contract instead of inventing
a new one.

### P0 — Reproducibility floor (days; do first, it's blocking everything)

- Fix `tools/build_ni_distill_support.py:203` (drop the `replace("/", "\\")`;
  `pathlib` handles forward slashes on Windows).
- Replace machine-local `atlas-distill/lammps_runs/` dependencies with a
  `fetch_potentials.py` script (NIST IPR / OpenKIM URLs + SHA-256 checksums,
  same pattern as the source packet already records) and make the affected
  tests skip-with-reason when artifacts are absent instead of failing.
- Fill or delete the phantom files behind `config/mlip_elastic_benchmark.yaml`
  §9 (`Apptainer.def`, `targets_0K.json`, `operator.py`, verify script).
- One documented environment: `pip install -e ./python[dev]` (or a uv
  lockfile) in `ONBOARDING.md`; add a Linux-first quickstart alongside the
  PowerShell blocks.

### P1 — One engine surface (1–2 weeks)

- Consolidate the three elastic harnesses into a single
  `lupine_distill.elastic` module; `replication/` keeps its frozen copy by
  design, `mlip_immi` and `fixture_contract` import the shared one.
- Merge the two calculator registries into one loader keyed by
  `backend_catalog.json`, exposed as a Python entry-point group
  (`lupine_distill.backends`) so a new team adds a potential by publishing a
  package, not by editing an if/elif chain. `BenchmarkBackend`
  (`backends/base.py`) is already the right ABC — make everything implement it.
- One canonical materials/reference table (single JSON consumed by Python,
  Rust, and the Lean generators) replacing the duplicated
  `A0_GUESS`/`PUBLISHED_C_IJ`/`ELEMENTS` tables.
- Fix the torchsim `model_id` bug while in there.

### P2 — The HPC lane (2–4 weeks; this is the headline feature)

- Teach the cell runner file-based I/O: `--manifest-url file://…`,
  `--artifact-prefix ./out`, `--beat-emit-url` optional (results land as
  files when absent). The contract barely changes; the coupling to GCS and
  the private worker becomes optional transport.
- Ship `Apptainer.def` built from `Dockerfile.unified` (same backend
  build-args) and a reference SLURM array-job template where one array index
  = one cell from `run-batch`. That makes "run our benchmark on your
  supercluster" a copy-paste operation.
- Implement the `lammps` backend stub (`runner.py:92`) via
  ASE's LAMMPS calculators — for supercluster MD at scale, LAMMPS is the
  lingua franca, and the schema enum already promises it.

### P3 — The contribution contract (2–3 weeks, parallel to P2)

- Define a PR-based submission path:
  `data/contrib/<team>/<campaign>/{campaign.json, cells/*.json, MANIFEST}`.
  Export JSON-Schema files from the existing Pydantic models
  (`model_json_schema()`) and commit them under `data/schemas/`.
- Add a `verify.yml` job that runs the existing validator CLIs
  (`tools/mlip_benchmark_sources.py validate`,
  `tools/mlip_evidence_campaign.py validate`, schema validation) over any
  `data/**` diff. Contributed data becomes CI-enforced, not operator-trusted.
- Generalize ingest: worker URL + token from env/config, plus an offline
  "bundle" mode that emits the same `BenchmarkRecord` payloads to files a
  maintainer can replay. External teams contribute via PR; the private
  worker becomes an internal mirror, not the gate.

### P4 — Close the data→theorem loop (after P3)

- CI drift gate: regenerate the machine-authored Lean modules
  (`DistillAtlas/*.lean`, `EmpiricalParadox.lean`, `HyperRibbonEmpirical.lean`)
  from their source JSON/CSV in CI and fail on diff. This turns "the build is
  the claim" from aspiration into enforcement.
- Point `tools/mlip_distill_atlas.py` at the P3 contribution format so an
  accepted external campaign automatically mints candidate evidence theorems
  — the actual "contribute back data to drive theorem formalization" loop.
- Replace the hand-typed theorem counters in `Vision.lean` with counts
  computed in CI, and reconcile `docs/formal-audit.md` with the
  Born-screening retraction so the formal narrative matches the ledger.

### Sequencing rationale

P0 is table stakes — today a clean Linux clone fails 13 tests and the
flagship benchmark config points at missing files, so any external pilot
dies in hour one. P1 before P2 because the HPC lane should ship against one
registry, not three. P2 and P3 together are the product: "run anywhere,
contribute by PR" — modeled on `replication/error-geometry/`, which already
proves the pattern works. P4 is what makes the contribution *scientifically*
load-bearing rather than a data drop, and it is where this program is
genuinely differentiated: no other MLIP benchmarking effort turns external
runs into machine-checked build obligations.
