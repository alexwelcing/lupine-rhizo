# Pinned validation source contains all five previously inspected pilot cases

Date: 2026-10-06. Status: completed identity and provenance recovery. No candidate force, energy, stress or error columns were decoded; no new predictions were run.

## Question and finding

The [preceding eligibility audit](./2026-10-06-validation-eligibility.md) established prior exposure to the MPtrj test source family but could not determine overlap with the pinned revision. We recovered that exact file and verified its SHA-256 against the historical input lock.

**All five earlier pilot configurations occur in the pinned candidate file.** Each matches both the exact ordered geometry fingerprint and the material/task/calculation/ionic-step identity. This resolves the earlier uncertainty about those cases. The whole source cannot be described as uninspected validation data.

One further candidate row shares a recorded Materials Project material ID with the MatPES development panel, without an exact geometry match. It is excluded conservatively as a material link. No exact geometry matches were found against the 800 archived panel configurations; this does not rule out physically equivalent or related structures.

## Outcome-blind inventory

Only nine identity/geometry columns were read. Structural checks require finite, correctly shaped geometry, matching atom counts, 2–80 atoms, atomic numbers 1–83 and nonempty material/task IDs. No force, energy or prediction threshold entered these checks. These rules differ from the historical A6 label-based gate; its old counts and **INCONCLUSIVE** verdict are unchanged.

| Stage | Configurations | Linked groups |
| --- | ---: | ---: |
| Whole pinned source | 10,273 | 9,750 |
| Pass structural checks | 9,309 | 8,849 |
| Pass structural checks and known exposure exclusions | **9,304** | **8,844** |

Groups are connected components under shared material ID, shared task ID or exact ordered geometry, with namespaces kept separate. Components were formed over the whole source before exclusions. Six components touch known exposure: the five pilot cases and one additional MatPES material link. One pilot case already fails the atomic-number rule, so five additional structurally eligible rows are removed. No final panel was sampled.

Exact hashes preserve atom ordering, coordinates, cell and periodic flags; they are not invariant to permutation, rotation, periodic translation, lattice changes or numerical tolerance. The MatPES link uses recorded original-MP-derived group labels. An OMat24-to-MP material crosswalk remains unavailable. Thus the 8,844 remaining groups are a **candidate pool**, not proven independent materials or model-training holdouts.

## Model provenance recovered, with a remaining gap

Read-only inspection of six original execution records recovered digest-qualified container image references. These are stronger evidence for execution-image identity than the previously retained after-run tag resolutions. The two known archive prefixes also retain prediction checkpoint objects.

Neither inspected execution nor object metadata establishes the exact loaded model weight bytes or the original weight identity behind reused prediction caches. A container digest and a stored prediction-checkpoint object digest have different meanings from a model-weight digest. Per-case reference compatibility and model-training independence also remain unresolved. The bounded search did not prove that stronger provenance is unavailable everywhere, and failed historical executions retain their failed states.

## Decision and next step

The identity-recovery task is complete. Fresh performance validation remains gated on predictor and reference provenance. Earlier ranking results still describe their stored arrays; they are not newly validated by this recovery.

Next, make model identity enforceable before new inference: require explicit checkpoint identity, record loaded-weight digests, and bind cached predictions to their original producer identity. Verify the behavior with small fake fixtures, without starting a model. Then freeze a distinct prospective validation protocol using the existing fixed scores and known exposure exclusions. Newly pinned models must not be presented as a replication of unresolved historical weights. Any claim about independence from model training needs separate evidence.

## Independent verification

A separate implementation reconstructed all 805 prior geometry fingerprints and compared all 10,273 candidate fingerprints, 82,184 identity/geometry/eligibility fields, both component partitions and every exclusion reason. All agreed. Its code was saved before it received the primary counts; aggregate counts arrived before execution, and its method and thresholds were unchanged. This is an independent implementation check, not a blinded replication or performance experiment.

## Evidence anchors

The [pinned public source](https://huggingface.co/datasets/nimashoghi/mptrj/resolve/f88fbe46e16524223210654bad9e1b05a15c2adb/data/test-00000-of-00001.parquet) is 11,285,531 bytes and matches SHA-256 `cb77ce289ba73357be0cc375df40631d0df0541e7120913cb2e89a17aae19add`. Column projection used [PyArrow 20's ParquetFile interface](https://arrow.apache.org/docs/20.0/python/generated/pyarrow.parquet.ParquetFile.html).

Raw recovered files, identities, detailed metadata and verification artifacts remain private. Hashes provide traceability, not public reproduction inputs.

- Frozen recovery protocol: `bff219532d721a40e0550ebe876acef382ce5a065733ef087058b7564c2fc3a8`
- Primary identity result: `6ba1a547219b92b32850a92e5ce6f47dc46ba5dc302bdd171a14b50da24d6048`
- Private candidate identity index: `1e05c5d08e4ca07e198727e3e63e4042f35268e528d176ef3822d573549bdb12`
- Independent agreement receipt: `44dc4dcbd2dbf4df1e7c2bb56fd70669b719b8dba9971304b202c8ca7f5e847b`
- Read-only execution/object metadata recovery: `4576746646c6af493a7d0f5c0a8d04ddfa3dd37c8278b12abb7ad94e6b508ecd`
