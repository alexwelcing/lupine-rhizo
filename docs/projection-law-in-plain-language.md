# The Projection Law in Plain Language

## The one-sentence version

The Lupine Projection Law is a geometric correction: it takes a single MLIP prediction, measures how far that model is likely to be from the truth, and projects the result back toward the right answer using a direction learned from earlier errors.

## Why this matters

Most ways of checking an interatomic potential are expensive. You either run a much more accurate quantum calculation, or you run many different potentials and hope their disagreements reveal the truth. The Projection Law asks a different question: *if this particular potential is wrong, what direction is it wrong in?* If that direction is stable across materials and configurations, you can correct a cheap prediction without paying for the expensive reference every time.

## How it works, in three steps

1. **Measure the error geometry.** Run the potential on a set of cases where you already know the truth — for example, 0 K DFT elastic constants for sixteen cubic elements. Record not just the size of the errors but their shape: which elastic constants are overestimated, which are underestimated, and whether the pattern repeats.

2. **Learn a correction direction.** The Projection Law extracts a low-dimensional bias vector from those errors. In practice, this bias often has a participation ratio close to one, meaning it points in a single, repeatable direction rather than scattering randomly through property space.

3. **Project a new prediction.** When the same potential is asked to predict a new material, the operator subtracts the learned bias vector from the prediction. The corrected value is closer to the reference than the raw prediction, and much cheaper than running a fresh DFT calculation.

## What the Round 2 benchmark showed

We tested four MatPES machine-learning potentials across sixteen cubic metals and two density functionals. The headline result is that the uncorrected potentials have a mean elastic-constant error of about 18 GPa, and the Projection Law correction removes a substantial fraction of that bias. The correction is applied *per potential*, not by averaging models, so it preserves the speed advantage of running a single cheap calculation.

A secondary result is just as important for practitioners: elastic constants are already converged at the 1×1×1 conventional cell. Running a 3×3×3 supercell adds runtime without improving accuracy, which means the correction can be evaluated on the cheapest reasonable cell.

## What this does not mean

The Projection Law is not a universal fix. It works when the error has stable geometry; if the potential encounters a chemistry or structure far outside the training distribution, the learned bias may not apply. That is why the operator is paired with a kill condition: if the measured error geometry stops being stable, the correction is withdrawn rather than extrapolated blindly.

## For a materials scientist

Think of it as a calibrated offset for a cheap instrument. You still need a few expensive measurements to build the calibration, but once you have it, you can correct many cheap measurements without re-running the expensive ones. The scientific work is showing that the calibration is stable enough to trust.
