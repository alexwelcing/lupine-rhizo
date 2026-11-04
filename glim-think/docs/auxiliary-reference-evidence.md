# Auxiliary references and corrected target calculations

Reviewed 4 November 2026. This literature and arithmetic review adds one
publication to the failure map, without admitting new corpus records or
changing the earlier Al/Ni observations. It is not a simulation or an
independent reproduction.

## A linked Cu example

Zhu, Grabowski and Neugebauer,
[Efficient approach to compute melting properties fully from ab initio with
application to Cu](https://journals.aps.org/prb/pdf/10.1103/PhysRevB.96.224202),
Physical Review B 96, 224202 (2017), link these Cu calculations in Section III A
(PDF page 6) and Table V (page 8):

| Target | Ref1 melting, K | Final TOR-TILD, K | Ref1 minus 1358 K | Final minus 1358 K |
| --- | --- | --- | --- | --- |
| PBE | 1144 | 1251 +/- 15 | -214 | -107 |
| LDA | 1274 | 1494 +/- 5 | -84 | +136 |

Final uncertainties are standard deviations from propagating MD statistical
errors, not functional-bias bounds. The 1358 K experiment is a cited reference.

Solid-fitted ref1 anchors coexistence; liquid-fitted ref2 supports integration.
Figure 5 (liquid LDA, 1600 K) reports ref2 about three times faster than ref1.
This is author-reported efficiency.

## What follows, and what does not

Our nominal arithmetic gives corrections of +107 K and +220 K. Absolute
discrepancy from the selected cited experiment decreases by 107 K for PBE and
increases by 52 K for LDA. Those calculations do not isolate a physical cause,
validate the experimental reference, or turn statistical error bars into
deterministic bounds.

The evidence does not support a rule that a correction toward a chosen
electronic-structure target must improve agreement with experiment. It also
does not support rejecting an auxiliary reference solely because its
standalone transition temperature is discrepant. These are distinct decisions.

The following bookkeeping identity makes the separation explicit. At the same
pressure, temperature, composition and phase convention, let g_s and g_l be
solid and liquid Gibbs free energies. Superscripts r and t denote reference
and target. Define d_alpha = g_alpha^t - g_alpha^r. Then

    g_l^t - g_s^t = (g_l^r - g_s^r) + d_l - d_s.

This is exact algebra, not a new correction method. In an actual calculation,
both phase corrections need their own compatible state, numerical estimates
and convergence evidence. A correction to only one phase is sufficient only
when the other contribution is already on the target convention or otherwise
accounted for. The identity does not supply those missing estimates.

For a canonical phase calculation on a fixed configuration domain, an additive
constant c in the reference energy shifts its free energy by c. Subtracting c
from an exact reference-to-target correction leaves the target unchanged.
Under a linear coupling, the added constant does not change normalized
sampling probabilities and only shifts the energy-difference integrand by
-c; its variance is unchanged. Thus an auxiliary energy offset need not
improve or degrade sampling efficiency. This argument assumes a finite
partition function and consistent phase domain, measure and normalization.
It is not permission to change a physical interphase energy difference and
omit the compensating correction.

Neither this identity nor a small integrand variance establishes equilibration,
adequate independent samples, finite-size convergence, quadrature accuracy or
accuracy of the target physical model.

## Consequence for the research system

A useful comparison must keep four questions distinct:

- How does the standalone potential predict the requested observable?
- How efficiently does the auxiliary reference support a specified correction?
- How accurately has the target calculation been evaluated?
- How well does that target describe the physical reference?

The [earlier coexistence review](phase-coexistence-evidence.md) concerns
standalone Al/Ni reference-potential results. The Cu example does not provide
their corrected counterparts. Matching a method-family name is insufficient
to join different material, potential, functional or workflow records.

A source-aware baseline already makes these distinctions. We have not found
a current accepted report that collapses them, or measured improved review
time or decisions. No new inspector or correction formula follows from this
review. The next system test should inspect an actual producer-to-reader
handoff for loss of these roles before proposing another feature.

## Review boundary

The numerical review used successful primary-PDF text extraction. Page-render
requests encountered cache misses, and no page image was visually inspected.
No PDF SHA256 pin or exact potential-file identity was established here.
The original experimental sources and a matched pressure/state audit remain
outstanding. The calculation is therefore a nominal reported-value comparison,
not an admitted physical-error benchmark.

The separate 2020 Al/Ni primary PDF (DOI 10.1103/PhysRevB.101.144108) timed out and was not retried. Its title,
abstract and bibliographic linkage do not establish its numerical results.
The Cu review neither replaces that missing evidence nor clears the source stop.

The two rows' differences agreed between BigInt and Number arithmetic. A
same-agent exact-integer check also exercised the phase-difference identity;
it is not an independent review, Lean proof or physical validation. There were
no new model calls, local file writes, builds, research uploads or simulations.
Original corpus values, uncertainty meanings, timestamps and exclusions remain
unchanged. Only this reviewed summary enters the draft documentation.
