# What Is an Interatomic Potential?

An **interatomic potential** is a mathematical shortcut.

If you wanted to simulate a piece of metal, a battery electrolyte, or a protein folding in water, the most accurate thing you could do is solve the Schrödinger equation for every electron in the system. That is correct, and impossibly expensive for more than a few hundred atoms. A potential replaces that quantum calculation with a much cheaper energy function that takes only the positions of the atomic nuclei and returns the energy (and forces) of the whole configuration.

## Why we need them

Materials scientists use potentials to ask questions that experiments cannot easily answer:

- How does a crack propagate through a slab of nickel?
- Which crystal surface will a catalyst prefer?
- What happens to a battery anode after ten thousand charge cycles?

These simulations routinely involve millions of atoms and billions of timesteps. Potentials make that tractable.

## The family tree

Not all potentials are the same. The major families differ in what they assume and what data they learn from:

| Family | Examples | What it learns from | Speed | Typical accuracy |
|---|---|---|---|---|
| **Classical / empirical** | EAM, MEAM, ReaxFF | Fitted to a small set of experiments or DFT calculations | Very fast | Good near the data it was fit to |
| **Machine-learning interatomic potentials (MLIPs)** | M3GNet, CHGNet, MACE, ORB, SevenNet | Large DFT databases such as MPTrj or Alexandria | Fast | Better transfer, but still fails outside training |
| **Active-learning / corrected** | Lupine operator, various Δ-learning schemes | Selected DFT + model error geometry | Fast after setup | Targeted correction of known failure modes |

## The central problem

A potential is **necessary and wrong**. It is necessary because full quantum mechanics is too expensive; it is wrong because any function that ignores electrons is an approximation. The real question is not whether it is perfect, but whether it is wrong in predictable, structured ways — and whether we can detect and correct those wrongs before they poison a scientific conclusion.

That is the project Lupine is built around.

## The Lupine stance

We treat prediction error as a signal, not noise. Across potentials, elements, and properties, the errors often form low-dimensional geometry. If that geometry is stable, it tells us what the model gets wrong and what correction target follows. The library you are reading documents the measurements of that geometry, the claims we have tested, and the corrections we have built.

If you want the shortest possible path from here to understanding our flagship result, read [*The Projection Law in Plain Language*](/#/read/projection-law-in-plain-language) next.
