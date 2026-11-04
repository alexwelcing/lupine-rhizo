# Sampled ranges, forward barriers and rate bounds

The existing finite-profile `barrier` in
`OpenDistillationFactory.Materials.Theory.UniversalCorrection.BarrierTransfer`
is an energy range. It remains defined as maximum minus minimum. A forward
activation barrier uses a designated initial state instead. These are different
observables unless that initial state is a sampled minimizer.

## Explicit initial-state contract

For a nonempty finite sample S and a designated i in S, define

    R(F) = max_S F - min_S F
    A_i(F) = max_S F - F(i).

Then

    R(F) - A_i(F) = F(i) - min_S F >= 0.

Equality holds exactly when i is a sampled minimizer, including ties. The Lean
definition `forwardBarrier` requires a proof of initial-image membership.
`barrier_eq_forwardBarrier_iff` proves the equality condition.

For example, F = [1, 3, 0] and G = [2, 3, 0], with the first image designated
initial, both have range 3. Their forward barriers are 2 and 1. Equal ranges
do not certify equal forward barriers. This synthetic example does not identify
an error in any historical physical profile.

If, on the same sample,

    a <= G(x) - F(x) <= b,

then

    |A_i(G) - A_i(F)| <= b-a.

The proof bounds the shift in the sampled maximum by [a,b] and subtracts the
initial-image offset, also in [a,b]. It needs the same designated initial
configuration, but no shared extrema or initial-minimizer assumption.
`abs_forwardBarrier_sub_le_wander` formalizes this statement.
`forwardBarrier_mono_subset` also proves that retaining the same initial image
in a smaller sample cannot increase the sampled forward barrier.

These are finite real-arithmetic statements. They do not establish continuous
path coverage, the true saddle, matching physical configurations, free-energy
barriers, numerical execution or physical accuracy.

## Separately optimized paths need a search and initial-state budget

A read-only review on 4 November 2026 inspected the paper-linked
[mlearn NEB calculator at its archived commit](https://github.com/materialyzeai/mlearn/blob/10c427a5480c6281c15c64efaf869b03be04818f/mlearn/potentials/lammps/calcs.py#L481)
and the [20 May 2019 version](https://github.com/materialyzeai/mlearn/blob/01a9f653ffcdfae078b84eeac53d8efca88157d1/mlearn/potentials/lammps/calcs.py).
Both use the supplied potential for lattice relaxation, vacancy endpoint
relaxation and the NEB calculation. This is a recipe observation, not proof
that this exact revision or these paths generated Zuo's reported barriers.
The current [LAMMPS NEB documentation](https://docs.lammps.org/stable/neb.html)
describes optimization of image positions and warns that an unsuitable
initial path can give bad results. It does not certify a global optimum.

Thus a common training/test sample does not establish common migration
configurations. The fixed-sample theorem above remains valid. Applying it to
two separately selected paths requires additional evidence.

Let C be a common, nonempty finite family of candidate profiles, each with a
nonempty set of configurations S_p. The two energy functions F and G must be
defined on every configuration in the family. Define profile heights

    H_F(p) = max_(x in S_p) F(x)
    m_F = min_(p in C) H_F(p),

and analogously for G. Suppose the reported paths are p_F and p_G, and that
their certified additive search gaps satisfy

    0 <= H_F(p_F) - m_F <= eta_F,
    0 <= H_G(p_G) - m_G <= eta_G.

These are bounds relative to the declared finite family. They say nothing
about an omitted physical path. For model-specific initial configurations
i in S_pF and j in S_pG, retain the actual initial-energy difference

    delta_0 = G(j) - F(i).

If a <= G(x)-F(x) <= b on every candidate configuration, the selected forward
barrier difference D obeys

    a - delta_0 - eta_F <= D <= b - delta_0 + eta_G,
    D = [H_G(p_G)-G(j)] - [H_F(p_F)-F(i)].

Proof: every profile's maximum changes by a value in [a,b], so the minimum
of those maxima does too. The exact identity is

    H_G(p_G)-H_F(p_F)
      = (m_G-m_F)
        + [H_G(p_G)-m_G] - [H_F(p_F)-m_F].

Subtract delta_0 and use the certified gap bounds. The Lean statements
`selected_path_score_sub_decomposition`,
`selected_path_score_sub_bounds` and
`selected_forwardBarrier_sub_bounds` express these steps.

If i=j as a physical configuration, a <= delta_0 <= b and this yields

    -(b-a)-eta_F <= D <= (b-a)+eta_G.

`selected_forwardBarrier_sub_bounds_same_initial` proves this corollary.
Zero gaps recover the wander bound for optimal choices within the common
family. A solver success status, force tolerance or named NEB method does
not establish eta=0. A bound measured only on one returned path does not
establish the required bound over the full candidate family.

Two exact synthetic obstructions make the extra terms necessary:

- **Search:** identical energy functions give energies [0,1,3] at three
  configurations. Candidate profiles are [0,1] and [0,2], both anchored at
  configuration 0. Selecting the first for F and the second for G yields
  barriers 1 and 3, despite zero residual everywhere. The G search gap is 2.
  Swapping the selections attains the lower-side gap term.
- **Initial state:** identical functions give [0,5,6]. Profiles [0,2] and
  [1,2], anchored at 0 and 1 respectively, both have height 6 and zero
  height-search gap in this family. Their barriers are 6 and 1.
  The difference -5 equals minus the initial-energy difference; zero
  residual does not remove it.

These are arbitrary finite configurations, not claimed continuous paths,
stationary saddles or observed defects in a publication. They distinguish
logical premises without asserting that the source authors violated them.
One in-memory scaled-integer check covered 78,732 energy/profile/anchor/shift
cases, including 26,244 shared-initial cases. The interval and the exact
decomposition agreed in all cases. This was a same-agent check, not an
independent review or a reproduction.

### Next-version evidence requirement

A future barrier report must separate three quantities: energy disagreement
on shared configurations, path-search error within a declared family, and
initial-state relaxation. Retain the candidate-family identity, both selected
path identities, configuration/cell correspondence, both initial identities,
cross-evaluation coverage, offset bounds and their provenance, and certified
search-gap bounds or explicit unknowns. Changing the family changes the
minimum against which the gaps are measured.

A reviewed finite set can supply exact finite-family gaps when every height
is evaluated. It cannot certify global physical search completeness. Different
cells or different endpoint basins require an explicit physical comparison
contract before the algebra is interpreted as a barrier comparison. Missing
cross-evaluations or search certificates must leave the bound unavailable;
they must not become zero error.

No additional inspector or simulation dispatch is introduced here. The
existing candidate-order inspector can compare supplied comparable scores,
but does not authenticate these path premises. The stronger specification
still needs a source-bound end-to-end test and measured decision or review
value. This is standard finite-extremum perturbation algebra, with novelty
unestablished.

## Prefactors are separate inputs

For positive temperature theta and positive prefactors, define

    k_F = nu_F exp(-A_i(F)/theta)
    k_G = nu_G exp(-A_i(G)/theta).

The exact rate-ratio identity is

    k_G/k_F = (nu_G/nu_F) exp((A_i(F)-A_i(G))/theta).

Thus an energy-difference bound w and a prefactor-ratio interval [l,u] give

    l exp(-w/theta) <= k_G/k_F <= u exp(w/theta).

`BarrierArrhenius.hopRate_ratio_eq` and `hopRate_ratio_bounds` expose the
prefactor term. `forward_hopRate_ratio_bounds` composes the latter with
w = b-a. Existing same-prefactor theorems remain valid; equality of prefactors
is an assumption, not a consequence of energy agreement.

A barrier-order comparison alone does not fix a rate ordering with unknown
prefactors. Nor does a scalar jump rate determine a diffusion tensor or
conductivity without the required populations, geometry, network and correlation
model. Historical theorem names are retained, while their documentation now
distinguishes scalar-rate algebra and barrier-threshold proxies from transport.

## Use in the evidence system

Keep the current candidate-energy inspector scoped to ordering the supplied
energies. It does not certify activation barriers or kinetic outcomes. Before a
future forward-rate interpretation, the evidence contract must retain:

- The observable convention: sampled range or initial-anchored barrier.
- The designated initial configuration and sample/path identity in each profile.
- Evidence for alignment across profiles and any missing continuous-path coverage.
- Temperature and prefactor identity or explicit ratio bounds.
- Fitting exposure, protocol limits and the scope of any transport conclusion.

Unknown fields stay unknown; a generic eV value or equal-range score cannot
supply these premises. No new transport inspector or migration campaign is
introduced by this formalization.

The existing Z1 producer explicitly records `max(energies)-min(energies)`.
Its saved observations and range-transfer theorems are preserved. No historical
profile is reclassified here, and no omission of initial endpoints is inferred.

## Verification scope

The existing pinned Lean workflow explicitly builds the barrier module, then
the full package and no-placeholder gate. The three main anchored statements
print their axiom dependencies. The maintained inventory generator counts the
current source tree. Successful formal checks validate the real-valued
specification, not a Rust/TypeScript parser or physical source premises.

The identities and bounds are standard finite-extremum and Arrhenius algebra;
novelty and downstream decision benefit are unestablished. The next system test
must assess whether exposing these premises changes an actual decision relative
to a competent source-aware baseline.
