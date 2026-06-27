# What Is an Interatomic Potential?

> A five-minute primer for newcomers. No jargon required — we will meet the acronyms together.

---

## The one-sentence version

An **interatomic potential** is a mathematical recipe that takes the positions of a set of atoms and returns two numbers: the total energy of the group, and the force on each atom. If you know the energy and the forces, you can run a molecular-dynamics simulation: atoms move, bonds stretch, crystals melt, proteins fold.

In other words, it is a **function** that maps atomic geometry → physics.

---

## Why not just use quantum mechanics?

You could. Density Functional Theory (DFT) solves the Schrödinger equation for the electrons and gives highly accurate energies. But DFT is expensive: a few hundred atoms is a large calculation, and a nanosecond of simulation time can take weeks on a supercomputer.

An interatomic potential is a **shortcut**. It skips the electrons and writes the energy directly as a function of where the nuclei sit. The trade-off is accuracy: the potential is only as good as the approximations baked into it. The art is knowing *where* it will fail and *how much* that matters for the question you are asking.

---

## The classical end of the spectrum

The simplest potentials treat atoms as balls connected by springs. Lennard-Jones gives you noble-gas crystals; Coulomb + Buckingham gives you oxides. These work for ionic solids and simple fluids, but metals are trickier because the bonding is *many-body*: every atom feels the electron gas shared by all its neighbors.

For metals, the workhorse is **EAM** (Embedded Atom Method). EAM adds an "embedding" term: the energy of an atom depends on the total electron density contributed by its neighbors. **MEAM** (Modified EAM) extends this with angular terms, which matters when bonds have directionality — think silicon or carbon, not just copper.

These classical potentials are fast, interpretable, and often fitted to experimental lattice constants or elastic moduli. Their weakness is **transferability**: a potential fit to the perfect crystal may misbehave at a surface, a defect, or a phase transition.

---

## The machine-learning end of the spectrum

Over the last decade, researchers started training neural networks to act as potentials. Instead of hand-crafting a functional form, you feed a large database of DFT calculations into a model and let it learn the mapping from geometry to energy.

The result is a **Machine-Learning Interatomic Potential** (MLIP). Modern examples include:

- **MACE** — an equivariant message-passing network that respects the symmetries of rotating or reflecting a molecule.
- **CHGNet** — a graph neural network trained on the Materials Project, designed to handle charge degrees of freedom.
- **DeePMD**, **NequIP**, **TensorNet** — other architectures with different trade-offs between speed, accuracy, and training data requirements.

MLIPs are dramatically more accurate than classical potentials for many properties, but they are not magic. They inherit the biases of the DFT data they were trained on, and they can fail catastrophically when asked to predict structures far from their training set — the same transferability problem, just in a different costume.

---

## Why accuracy matters, and where it fails

In materials science, a small energy error can mean the wrong crystal structure is predicted stable, or a defect that should form is dismissed as too costly. The error is not random noise; it is **structured**. Different potentials tend to err in the same directions for the same materials, and different architectures (EAM vs. MACE vs. CHGNet) err in *different* directions. Understanding that structure — the geometry of error — is the central project of the Lupine library.

If you want to go deeper, the library tracks this through two lenses:

- **Error-geometry objects** — the mathematical tools we use to measure and describe how potentials fail.
- **The conjecture ledger** — a live register of every claim we have tested, which ones survived, and which ones we refuted (and why).

---

## What to read next

- If you are a researcher who wants the technical details: start with the [Methodology](methodology.md) and the [Hypothesis Ledger](conjectures/ledger.md).
- If you want to see the formal proofs: visit the [Formal Proof Ledger](formal-proof-ledger.md).
- If you just want to browse the catalog: the [Research Index](research-index.md) lists every document and its status.
