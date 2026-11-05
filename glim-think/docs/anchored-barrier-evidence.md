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
