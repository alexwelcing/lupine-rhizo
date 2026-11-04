# Coexistence temperatures: observable identity before discrepancy

Reviewed 4 November 2026. This is a source and arithmetic review of eleven
retained observations in two publications, not new simulations, independent
validation or a pooled performance comparison. The observations were extracted
on 7 October; this review does not replace their original timestamps.

The decision is whether a reported solid-liquid coexistence temperature supports
validation of the intended equilibrium observable. Two separate obligations
matter: identifying that observable and stating what an uncertainty measures.

## Alloy liquidus: a close table is not independent boundary validation

Mahata, Mukhopadhyay and Asle Zaeem,
[Modified embedded-atom method interatomic potentials for Al-Cu, Al-Fe and
Al-Ni binary alloys: From room temperature to melting point](https://par.nsf.gov/servlets/purl/10324339),
Computational Materials Science 201 (2022), 110902,
DOI [10.1016/j.commatsci.2021.110902](https://doi.org/10.1016/j.commatsci.2021.110902),
is reviewed through the retained accepted manuscript.

The methods on pages 9-10 state that solidus/liquidus temperatures were priorities
during parameter optimization, and that the alloy composition is used to form
both solid and liquid. Pages 17-18 describe melting half the box, then 0.5 ns
of NPT for the melted half, 1 ns for the full box and approximately 10 ns of
NPH with normal-direction relaxation. The temperature estimate is iterated to
convergence. This is evidence of the stated procedure, not a new execution.

Table 6, page 19, gives these five alloy comparisons. Its star marks the eutectic
entry; it does not establish every phase identity or a general congruent-melting
condition.

| Overall alloy composition (atomic %) | Reported MD temperature, K | Cited liquidus, K | MD minus cited value, K |
| --- | --- | --- | --- |
| Al90Cu10 | 868 +/- 5 | 873.0 | -5 |
| Al85Cu15, marked eutectic | 821 +/- 5 | 821.2 | -0.2 |
| Al75Cu25 | 849 +/- 10 | 853.0 | -4 |
| Al50Cu50 | 1170 +/- 15 | 1148.0 | +22 |
| Al25Cu75 | 1310 +/- 8 | 1300 | +10 |

The printed +/- convention for this table is not established by the inspected
caption/methods; a confidence convention from another table must not be copied.
The original experimental phase-diagram reference was not independently audited.

The inspected methods do not establish final phase-resolved compositions,
phase fractions, chemical equilibration or the disappearance of the last solid
at each listed overall composition. This is a bounded evidence gap, not proof
that redistribution did not occur or that the results are wrong. Initial equal
composition does not prove equal final composition. Temperature convergence
alone does not supply the missing phase-composition evidence. Because the
temperature targets also informed fitting, close agreement is not an independent
held-out validation.

## Elemental melting: precision is distinct from physical discrepancy

Zhu et al.,
[A fully automated approach to calculate the melting temperature of elemental
crystals](https://pure.tudelft.nl/ws/files/86400576/1_s2.0_S0927025620305565_main.pdf),
Computational Materials Science 187 (2021), 110065,
DOI [10.1016/j.commatsci.2020.110065](https://doi.org/10.1016/j.commatsci.2020.110065),
is reviewed through the retained published PDF. The Delft cover shifts PDF page
numbers by one relative to the printed article.

The interface procedure rejects fully solid/liquid outcomes, estimates the
temperature at zero pressure from strained-interface NVE calculations and
iterates to a 1 K criterion. The paper then repeats runs with different velocity
seeds. Table 1 (PDF page 8, printed page 7) reports the standard deviation of the
mean. Figure 8 on that page instead labels three times the seed-distribution
standard deviation. These are different quantities; neither is a bound on
potential bias. The stated seed count varies from 50 to 150, and an exact
per-case count is not inferred from rounded error bars.

| Element and named potential | Reported mean +/- standard error, K | Cited experiment, K | Nominal discrepancy, K |
| --- | --- | --- | --- |
| Al, TOR-TILD EAM | 824 +/- 0.1 | 933 | -109 |
| Ni, TOR-TILD EAM | 1472 +/- 0.1 | 1728 | -256 |
| Al, litEAM | 926 +/- 0.1 | 933 | -7 |
| Mg, litEAM | 913 +/- 0.2 | 923 | -10 |
| Al, MTP | 847 +/- 0.2 | 933 | -86 |
| Ti, MTP | 1667 +/- 0.4 | 1941 | -274 |

For example, a reported 0.1 K standard error coexists with a 109 K nominal
Al discrepancy. This is arithmetic on the authors' reported table, not a
significance test or isolation of potential error from reference/state effects.

The source describes TOR-TILD reference potentials fitted to solid-phase free
energies and litEAM fitting to thermal properties. Such reference potentials can
serve a thermodynamic-integration workflow without being accurate stand-alone
melting predictors. The paper explicitly restricts its demonstrated automated
method to unary phases and leaves binary/multicomponent extension for further
development. Its elemental precision therefore does not validate the alloy
liquidus procedure above. Exact model digests, row-level selection exposure and
original experimental reference conditions remain unresolved.

## The missing comparison premise

NIST's [liquidus definition](https://www.ctcms.nist.gov/~kattner/solidifc/liquidus.html)
locates the boundary where liquid becomes saturated with solid; its
[lever-rule description](https://www.ctcms.nist.gov/~kattner/solidifc/lever.html)
retains equilibrium phase compositions, fractions and enthalpies.

For exactly one solid phase and one liquid phase, using consistent atom-fraction
and phase-amount conventions and neglecting interface inventory, conservation
gives

    x0 = phi_s * x_s + (1 - phi_s) * x_l,
    x0 - x_l = phi_s * (x_s - x_l).

Thus a finite solid fraction and unequal phase compositions do not identify the
liquid composition with the overall composition. Assigning a coexistence
temperature to the liquidus at the overall composition needs additional boundary
or phase-equilibrium evidence. This identity alone does not prove a temperature
difference: invariant or congruent cases and multiple solid phases need their
own phase description. It is standard mass balance, not a novel theorem or a
new Lean result.

The next decisive observation for an alloy claim is phase-resolved composition
and phase fraction versus preparation/time, with pressure and phase identities,
or a verified equilibrium calculation locating the relevant liquidus boundary.
For an elemental claim, numerical convergence and sampling precision still need
separate physical-reference and fitting-exposure qualifications. More digits
alone resolve neither problem.

## Outcome for the evidence system

The existing records already distinguish Mahata's reported liquidus values from
a fully audited equilibrium comparison, and Zhu's seed-sampling standard errors
from model error. All eleven retain their original exclusion from pooled
physical-error analysis. The four pinned qualification files contain no explicit
target for these selected IDs; that is not broader clearance.

A competent source-aware baseline reaches the same decision: retain the reported
numbers and uncertainty meanings, abstain from independent alloy-liquidus
validation, and avoid turning small seed errors into a physical-accuracy bound.
No new inspector, automatic classifier, correction formula or metadata rewrite
is justified by this review. A scalar energy-error certificate cannot establish
missing phase/observable identity. This strengthens the
[failure map](exception-to-theorem-failure-map.md) without claiming new physical
failure, novelty or measured user benefit.

A separate [auxiliary-reference review](auxiliary-reference-evidence.md) keeps
standalone prediction, correction efficiency, target evaluation and physical
accuracy as distinct roles. It does not supply corrected counterparts for the
Al/Ni observations above or change their qualifications.

## Verification and limits

Both retained PDF SHA256 pins matched:
- Mahata: `f282fbcd74520b4402f85ca4d5ef70a2af2a009ca17d3f10ce6d73dce438fa96`.
- Zhu: `890b17461bfef54fd2108cdf8283b647faa7c782d4cfd77943a3a69193048d95`.

The existing Mahata Table 6 and Zhu Table 1/Figure 8 and interface-method page
previews were visually checked without regeneration. Mahata's additional
methods and Zhu's unary-only limitation were checked in retained derived text;
those methods pages were not newly rendered. Derived text/preview hashes were
freshly observed, not matched against older pins. The base, manifest and all
four qualification pins matched.

All eleven nominal differences agreed between scaled-integer BigInt and
separate JavaScript Number arithmetic. These are same-agent checks, not
independent review, physical reproduction or executable-correctness proofs.
Original values, uncertainty labels and compatibility flags were not changed.
No model/provider call, simulation, source download or new corpus admission
occurred. Public documentation contains reviewed literature/methods only;
private corpus containers and campaign artifacts are excluded.
