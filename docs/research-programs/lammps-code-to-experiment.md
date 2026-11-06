# LAMMPS as a research instrument: from source code to trustworthy experiments

Date: 2026-10-31

*31 October 2026 · Local source review and proposed research program · No new simulation results*

LAMMPS should be a first-class research instrument in Lupine: software whose numerical choices we understand, a controlled execution backend, and a source of testable scientific questions. This article starts that work by reading an immutable source revision, connecting its implementation boundaries to our existing materials research, and proposing a small experiment that can expose mistakes before a larger campaign begins.

The inspected release is **LAMMPS 30 September 2026**, pinned to commit **8de817dd79bfe4525d5d39246a212d833e6dee07**. The pin identifies source code, not an installed executable. We have not compiled or executed that revision in this study. A local Codex source review and separate design review produced this orientation; it is not a hosted research-agent report, external peer review, or experimental validation. [Release](https://github.com/lammps/lammps/releases/tag/stable_30Sep2026)

## The code path is part of the scientific method

A simulation result depends on more than the named potential. LAMMPS's timestep coordinates integration, atom migration, neighbor-list construction, interaction kernels, communication, fix hooks, and measurement. Reading those stages together helps explain how a plausible input can produce the wrong observable.

In `Verlet::run`, initial integration precedes the decision to rebuild neighbors. The code then clears forces, invokes force calculations, handles reverse communication when required, runs post-force hooks, and finishes integration. A force reported after a modifying fix therefore needs a different interpretation from the force produced by the pair kernel alone. This is a reason to inspect the complete measurement path, rather than treating a successful `Pair::compute` call as validation of a trajectory. [Pinned timestep source](https://github.com/lammps/lammps/blob/8de817dd79bfe4525d5d39246a212d833e6dee07/src/verlet.cpp)

| Surface to read | What it controls | Research question it creates |
| --- | --- | --- |
| `src/verlet.cpp`, `src/fix_nve.cpp` | Integration order and velocity/position updates | Does an apparent model instability survive timestep refinement? |
| `src/neighbor.cpp`, pair-style neighbor requests | Which interactions are visited and when lists are rebuilt | Do energies and forces remain consistent under qualified neighbor-list settings? |
| `src/MANYBODY/pair_eam.cpp` | Density accumulation, embedding derivatives, communication, and forces | Does the many-body force agree with the derivative of the same total energy? |
| `src/compute_pressure.cpp`, `src/compute_stress_atom.cpp` | Global pressure and per-atom stress conventions | Are signs, volume factors, tensor ordering, and kinetic contributions being compared correctly? |
| `src/ML-SNAP/pair_snap.cpp`, `src/ML-IAP/pair_mliap.cpp`, `src/ML-PACE/pair_pace.cpp` | Descriptor/model interfaces and force evaluation | Which parts of an ML potential's error come from representation, learned coefficients, or integration? |

The Lennard–Jones implementation provides a compact reading exercise. `PairLJCut::compute` gates interactions on squared separation, scales special-neighbor interactions, accumulates equal-and-opposite contributions subject to the Newton/local-atom rules, and tallies energy and virial. `init_one` constructs coefficient combinations and an optional energy offset. That offset appears in the energy expression without entering the force expression. This is a useful concrete reminder that energy shifting at a cutoff does not, by itself, smooth the force. It motivates a cutoff study; it is not a new finding about a material. [Pinned LJ source](https://github.com/lammps/lammps/blob/8de817dd79bfe4525d5d39246a212d833e6dee07/src/pair_lj_cut.cpp)

EAM is a more relevant first instrument check for metals. Its source evaluates accumulated density and embedding derivatives before assembling the final force. A check that only exercises an isolated pair formula would miss this structure. ML-IAP, SNAP, and PACE add other interfaces and package requirements; availability of a style name does not establish that a particular executable, model file, element mapping, or accelerator path is qualified. [Pinned EAM source](https://github.com/lammps/lammps/blob/8de817dd79bfe4525d5d39246a212d833e6dee07/src/MANYBODY/pair_eam.cpp), [ML-IAP documentation at the inspected revision](https://github.com/lammps/lammps/blob/8de817dd79bfe4525d5d39246a212d833e6dee07/doc/src/pair_mliap.rst)

## First experiment: reconcile energy, force, and the full stress tensor

The proposed first experiment is a **108-atom periodic copper EAM source-contract study**, with a fixed, deterministically perturbed geometry. It is distinct from our completed four-atom ASE/EMT exercise and the earlier two-atom teaching example. Its purpose is to qualify the LAMMPS many-body calculation and our interpretation of its outputs.

The design uses **55 static evaluations and zero integration timesteps**: one base configuration, centered coordinate differences for three components of one atom at three step sizes, and centered homogeneous-strain differences for six tensor components at three step sizes. Geometry, potential, executable, enabled packages, precision, units, neighbor settings, and output schema must be frozen before execution. The proposed EAM file is the release's `Cu_u3.eam`; choosing a bundled example does not establish its accuracy for every copper property. [Pinned potential](https://github.com/lammps/lammps/blob/8de817dd79bfe4525d5d39246a212d833e6dee07/potentials/Cu_u3.eam)

For the selected coordinate, compare the reported force with the centered energy derivative:

$$F_{i\alpha}^{FD}(h)=-\frac{E(x+h e_{i\alpha})-E(x-h e_{i\alpha})}{2h}.$$

For stress, compare the energy response to a precisely defined homogeneous deformation with the pair-only pressure tensor. At zero velocity, and with the selected pair-only contributions, the sum of the corresponding per-atom stress entries should match negative volume times global pressure after the documented unit conversion. Per-atom stress has units of pressure times volume; it is not directly a per-atom pressure. A shear derivative also depends on whether the deformation parameter is an engineering shear or a symmetric tensor component. The manifest must define that mapping explicitly. [Pinned pressure documentation](https://github.com/lammps/lammps/blob/8de817dd79bfe4525d5d39246a212d833e6dee07/doc/src/compute_pressure.rst), [pinned stress documentation](https://github.com/lammps/lammps/blob/8de817dd79bfe4525d5d39246a212d833e6dee07/doc/src/compute_stress_atom.rst)

The decisive outcome is whether derivative errors converge across the fixed step-size ladder and satisfy preregistered numerical tolerances, while the global/per-atom tensor identity closes. A persistent component-specific discrepancy would direct us to signs, shear factors, atom mapping, units, or tally contributions before blaming the potential. A clean result would establish numerical consistency for that exact configuration and executable. It would not establish physical accuracy, defect energetics, finite-temperature stability, or transferability to Cr–Co–Ni.

The [downloadable experiment proposal](/downloads/lammps-static-contract-proposal-20261031.json) specifies the geometry, displacement and strain ladders, numerical tolerances, resource limits, source hashes, and unresolved executable/runner identities. It is a proposal, not an executable authorization.

**Status: proposed, not run.** Execution remains held until the exact executable and potential identities, resource bounds, input deck, parser, and independent numerical review are complete. Failure or an unknown outcome stops the experiment; it does not automatically enlarge the run or authorize a follow-on.

## What comes after that check

Three questions form a useful progression, with separate admission decisions for each.

1. **Numerical invariance.** Compare qualified neighbor-list settings and, later, serial/MPI or CPU/accelerator paths on identical configurations. Require tolerances appropriate to floating-point reduction order; byte-identical trajectories are not a general scientific requirement. A disagreement is an implementation or configuration lead, not immediate evidence of new physics.
2. **Dynamics versus model error.** On a smooth, qualified potential, compare bounded NVE runs at a preregistered timestep ladder. Separate integration error, cutoff effects, and force consistency from genuine physical instabilities. Thermostat-controlled temperature alone is not an energy-conservation test.
3. **Transferability and useful uncertainty.** Evaluate strained, low-coordination, vacancy, and stacking-fault environments against independent reference calculations selected before seeing model errors. Where PACE supplies an extrapolation grade, test whether that grade predicts held-out error or enables useful abstention. A large or small grade is not itself an error bound. [Pinned PACE documentation](https://github.com/lammps/lammps/blob/8de817dd79bfe4525d5d39246a212d833e6dee07/doc/src/pair_pace.rst)

The aim is to learn which failure a measurement can discriminate. A broad sweep without a defined reference can generate many numbers while leaving that question unanswered. Likewise, a potential fitted to bulk data should not be promoted for a defect property solely because its bulk error is small.

## How this connects to Lupine's existing evidence

Our [research-team study](../research-progress/2026-10-26-cloudflare-research-team.md) separates calculator consistency, supplied-label agreement, and independent physical validation. The completed Cr–Co–Ni NEP audit remains a development-evidence comparison; this LAMMPS program does not convert it into a held-out test. The copper EAM proposal establishes a new execution-boundary question, not a replacement outcome for the earlier EMT calculation.

The [data and provenance guide](../data-provenance.md) supplies the corresponding record discipline: identify the potential and reference data, preserve units and conventions, and link conclusions to exact inputs and outputs. [Formal methodology](../formal-methodology.md) motivates another useful boundary: a proved relation between mathematical quantities is distinct from evidence that a simulator, parser, and dataset instantiate those quantities. Future formal work should make that connection explicit rather than treating all LAMMPS output as ground truth.

The research loop should record **source revision → implementation question → proposed manifest → execution receipt → measured result → review → next question**. These are different types of knowledge. In the Library, this article is a source-review and research-program entry. It is linked to the earlier research and provenance articles; it does not create a fictitious completed experiment or a hosted-agent evidence record.

An associated review of Lupine's own integration identified an immediate qualification gap: the inspected experiment queue computes a heuristic validation result without enforcing rejection before insertion. It also uses a generic potential placeholder and infers experiment type from text. Those are source-level observations, not evidence that an invalid experiment ran. Before autonomous LAMMPS admission, the integration needs explicit experiment types, exact potential/executable identities, property-specific outputs, and a hard rejection path. A design score may help prioritize work; it cannot substitute for those conditions. [Inspected Lupine queue source](https://github.com/alexwelcing/lupine-rhizo/blob/1a218590d10e42238ed02bac4153de7e516cea11/glim-think/src/agents/experiment.ts)

## A working reading route

Start with the timestep and EAM implementation, then read pressure/stress definitions alongside the proposed finite-difference experiment. Next compare the SNAP, ML-IAP, and PACE interfaces. Only then select a transferability or dynamics question with the required independent reference and compute budget. The [research index](../research-index.md) provides the wider context; [the history of atomistic computing](../../lit-review/supercomputing-atomistic-history.md) places these choices in a longer methodological progression.

The immediate deliverable is understanding that can change an experimental decision: knowing which quantity was calculated, which implementation path produced it, and what result would make us revise our explanation. That is the standard for making LAMMPS a productive part of the research program.
