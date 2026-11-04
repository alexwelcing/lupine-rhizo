# Candidate energy ordering

A uniform shift can reduce formation-energy squared error while leaving every
candidate ordering unchanged. The candidate-order checker assesses the decision
among a fixed list of candidates directly, using exact signed energy gaps.
It applies to a declared common composition and reference convention; it does
not turn unlike defect stoichiometries or different reservoirs into comparable
energies.

## Input and output

From the repository root:

    cargo run --manifest-path atlas-distill/Cargo.toml --bin atlas-distill -- \
      candidate-order --input atlas-distill/tests/fixtures/candidate_order.input.json

The synthetic fixture intentionally has different reference and prediction
minima. A valid descriptive report exits successfully even when ordering
disagrees. Malformed inputs fail without a report. No provider, simulator,
database, network or output-file operation is performed.

The input is limited to 512 KiB and 2–32 unique candidates. Each candidate has
an ID, label, source anchor, and closed reference/prediction energy intervals
in eV. Interval endpoints are decimal strings of at most 64 characters, without
exponents or nonfinite values. The output also has a 512 KiB ceiling.
The exact-values mode requires zero-width intervals. Assumed printing bounds
and declared deterministic bounds are separately labeled. Statistical confidence
intervals are not silently interpreted as deterministic bounds.

Context retains source, model, material/composition, reference convention,
protocol, fitting exposure, candidate-set identity and search scope. Unknown
hashes and metadata remain null. A shared context is a declaration, not
independent verification that all structures have the same composition or
calculation protocol. Unknown comparability remains an explicit limit even
though arithmetic on the supplied values is possible.

The report embeds the interpreted input and fingerprints the original input
bytes. Hashes do not authenticate the source/model or establish that a search
was exhaustive. CLI struct parsing rejects duplicate and unknown fields.
Browser inspection uses JSON parsing and cannot authenticate the original
input bytes from their declared digest.

## Exact interval specification

For energies x_i in closed intervals [l_i,u_i], all combinations are allowed.
Candidate i:

- can be a minimizer iff l_i <= u_j for every j != i;
- is a minimizer throughout the box iff u_i <= l_j for every j != i;
- is uniquely lowest throughout the box iff u_i < l_j for every j != i.

Possible and guaranteed sets are distinct. Exact ties are retained rather than
broken by row order or candidate ID. Touching endpoints do not establish a
unique choice. If shared errors or other dependencies constrain the energies,
this Cartesian model may be conservative; possible choices under the full box
are not assertions of feasibility under an unknown correlated model.

For a pair (left,right), the exact right-minus-left gap is

    [l_right - u_left, u_right - l_left].

Positive means the left candidate is lower. Each pair includes reference and
prediction gaps, their difference, and whether both gaps have the same strict
sign, opposite strict signs, exact ties in both, or unresolved/tie semantics.
No tolerance, denominator floor or binary floating-point conversion is used.

Adding a constant to every prediction leaves every prediction gap unchanged.
With point references having a unique minimizer j and minimum gap delta > 0,
the actual choice is preserved iff

    (r_i-r_j) + (e_i-e_j) > 0  for every i != j, where e = p-r.

Writing C = ||e-mean(e)||²/n, every error in a ball C <= B preserves that unique
choice iff 2*n*B < delta². At equality, +delta/2 on j and -delta/2 on a closest
competitor creates a tie. Failure of this uniform norm guarantee does not mean
the actual prediction chooses incorrectly. The checker uses the direct interval
gaps; it does not infer a decision from aggregate RMSE.

These are standard interval and Euclidean margin arguments. They are separate
from the Lean vacancy loss decomposition and are not claimed as new Lean proofs,
executable correctness proofs or physical validation.

## Private inspection and verification

The existing private RUNS page offers **Inspect a candidate energy ordering**
even when no run is saved. One report stays in page memory. It is not uploaded,
persisted, attached to a saved run or published. Clear/new selection invalidates
pending reads. The inspector recomputes every gap and choice set from the
included bounds and rejects inconsistent producer assessments.

The summary distinguishes possible, guaranteed and guaranteed-unique minima.
Signed gaps, source anchors, original bounds and missing metadata remain visible.
A declared exhaustive candidate list is still unverified. The page never
certifies a global ground state, source authenticity, independent fitting
exposure, physical accuracy or simulation authorization.

This standalone inspection does not bypass the separate saved-run preview's
requirements for genuine discovery receipts and distinct model arms. A list of
defect configurations is not a list of models. Interstitials need not be
relabeled as vacancies to use this report.

Rust and TypeScript consume shared synthetic input/assessment fixtures.
Tests include closed endpoint ties, overlapping boxes, tiny exact gaps,
permutation/constant-shift invariance, forged assessments, and exhaustive corner
checks for 64 three-candidate boxes. Client checks cover rendered markup, local
file bounds and absence of network/persistence. They are not interactive browser
QA, independent scientific review, a materials benchmark or deployed acceptance.

For migration or reaction kinetics, energy ordering alone is insufficient.
The [anchored-barrier contract](anchored-barrier-evidence.md) distinguishes a
sampled range from a forward activation barrier and retains prefactor and
transport assumptions. This inspector does not supply those missing premises.

For the completed literature cases, source limits and comparison against existing
methods, see the [empirical failure map](exception-to-theorem-failure-map.md).

The [public-source acceptance bridge](candidate-order-source-acceptance.md) passes
actual Rust CLI output through the complete application reader. Its source and
runtime scope are separate from interactive browser or physical acceptance.
