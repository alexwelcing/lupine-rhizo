# Independent primary-source audit of load-bearing reference values

- Date: 2026-07-13
- Auditor: independent verification agent (blinded protocol)
- Protocol: every quantity was sourced from the literature FIRST (web search + primary
  PDFs where fetchable), values and citations recorded, and ONLY THEN were the repo's
  targets files opened for comparison. No git commits. No GPU.
- Scope: the five most load-bearing reference values behind the gates-licenses
  manuscript (`paper/gates-licenses-paper/manuscript.md`), plus the Schottky h_S
  anchor set used in its "defect formation energetics collapse" paragraph.

Severity scale: OK (agrees), MINOR (cosmetic / caveat gap), MODERATE (band or
uncertainty misstated), MAJOR (manuscript number unsupported by primary literature).

---

## 1. LiF cation-vacancy migration enthalpy + intrinsic activation

**Independently sourced.** Stoebe & Huggins, "Measurement of ionic diffusion in
lithium fluoride by nuclear magnetic resonance techniques", J. Mater. Sci. 1, 117
(1966), doi:10.1007/BF00550100 (abstract values confirmed via web search of the
Springer record this session):

- extrinsic free-vacancy region: **0.66 ± 0.03 eV** (cation-vacancy motion)
- intrinsic region: **1.87 ± 0.09 eV**
- association region: 0.91 ± 0.05 eV
- Schottky formation (their own number): **2.42 eV**

Corroboration: a first-principles LiF defect study (OSTI purl 1370674) cites the same
Stoebe & Huggins 2.42 eV (its ref. 60) and experimental diffusion barriers
0.65–0.73 eV; other reported LiF Schottky values it lists: 2.68, 2.34–2.68 eV.

**Stored.** `data/candidates/kinetics_targets.json` → LiF: dH_m = 0.66 ± 0.03 eV
(extrinsic), intrinsic 1.87 ± 0.09 eV noted, h_S = 2.42 eV derived; target barrier
0.66 eV.

**Verdict: AGREE (exact). Severity: none.**

---

## 2. NaCl cation-vacancy migration enthalpy, intrinsic activation, and h_S

**Independently sourced.**

- Dreyfus & Nowick, "Ionic Conductivity of Doped NaCl Crystals", Phys. Rev. 126,
  1367 (1962) — full text fetched and read this session:
  - cation-vacancy motion: **0.796 ± 0.02 eV**
  - intrinsic-region activation (their compilation across authors): **1.86 ± 0.03 eV**
  - Schottky pair formation (published, = 2×(1.86 − 0.796)): **2.12 ± 0.07 eV**
  - they note the pre-1962 literature spread for cation migration: 0.72–0.85 eV.
- Hooton & Jacobs, Can. J. Chem. 66, 830 (1988): paywalled everywhere tried
  (publisher 403/Cloudflare, no OA copy, no Wayback, Unpaywall closed, thesis record
  has no fulltext). Verified from the abstract/indexes only: **anion**-vacancy
  migration 0.744 eV and "Schottky model entirely adequate". Their fitted cation
  migration and Δh_S could NOT be independently read this session; the classic
  compilation value attributed to them in secondary literature is ~2.4–2.5 eV.

**Derived h_S = 2(E_intrinsic − ΔH_m), computed by auditor:**

- LiF: 2×(1.87 − 0.66) = **2.42 eV** — matches Stoebe & Huggins' own published value.
- NaCl (Dreyfus & Nowick inputs): 2×(1.86 − 0.796) = **2.13 eV** — matches their
  published 2.12 ± 0.07 eV.
- NaCl (modern-consensus inputs h_m ≈ 0.65–0.72): h_S = 2×(1.86…1.97 − 0.69) ≈
  **2.3–2.6 eV**. No fetched primary supports E_intrinsic = 2.10 eV for NaCl.

**Stored.** `data/candidates/kinetics_targets.json` → NaCl: dH_m = 0.69 eV (range
0.65–0.71, attributed to Hooton & Jacobs 1988 + Nelson & Friauf 1970);
schottky_formation_enthalpy = **2.44 eV** ("Hooton & Jacobs 1988; Barr & Lidiard
compilation"); caveat text states intrinsic activation "~2.10 eV".

**Manuscript.** `paper/gates-licenses-paper/manuscript.md` (line 24) anchors NaCl at
**h_S = 2.83 eV**, described as "conductivity-derived experimental values
h_S = 2(E_intrinsic − ΔH_m)".

**Verdict: DISAGREE on the manuscript anchor. Severity: MAJOR (manuscript),
MODERATE (kinetics file internal inconsistency).**

- 2.83 eV is reproducible only as 2×(2.10 − 0.685). The 2.10 eV "intrinsic
  activation" is unsupported by the primaries fetched (Dreyfus & Nowick compilation:
  1.86 ± 0.03 eV) and is inconsistent with the repo's own stored h_S = 2.44 eV
  (2.44 requires E_intrinsic = h_S/2 + h_m = 1.91 eV, not 2.10).
- The trio stored in kinetics_targets.json — h_m = 0.69, E_int ≈ 2.10, h_S = 2.44 —
  is not self-consistent under the very formula the manuscript cites.
- Directly published experimental h_S values found: 2.12 ± 0.07 eV (Dreyfus &
  Nowick 1962); classic compilation ~2.44 eV (H&J-era, not independently readable
  this session). Every supported value is 0.4–0.7 eV BELOW the manuscript's 2.83.
- Impact: the "underestimated by 40–105 %" NaCl deficit is overstated; with
  h_S = 2.44 (repo's own number) or 2.12 the deficit shrinks but remains large, so
  the qualitative collapse claim survives. Any claim placing NaCl above LiF in the
  Schottky series does NOT survive if h_S(NaCl) ≈ 2.12–2.44 vs LiF 2.42.
- Also MINOR: stored NaCl dH_m band 0.65–0.71 eV excludes Dreyfus & Nowick's
  0.796 ± 0.02 eV; the experimental spread is honestly 0.65–0.85 eV.

---

## 3. KCl single-crystal elastic constants (RT)

**Independently sourced.** Norwood & Briscoe, "Elastic Constants of Potassium Iodide
and Potassium Chloride", Phys. Rev. 112, 45 (1958) — full text fetched and Table II
read directly this session. 300 K row (units 10^11 dyn/cm² = 10 GPa):

- C11 = 4.032 → **40.32 GPa** (max error ±0.3 %)
- C12 = 0.66 → **6.6 GPa** (difference-of-large-numbers; ~9 % plausible error)
- C44 = 0.629 → **6.29 GPa** (max error ±0.5 %)
- Cross-check in same paper (Eros & Reitz 1958, RT): 40.35 / 6.51 / 6.33 GPa.

**Stored.** `data/candidates/round3_targets.json` → rs-kcl: c11 = 40.32, c12 = 6.6,
c44 = 6.29 GPa, B0 = 17.84 GPa derived; same primary, same table, same caveats.

**Verdict: AGREE (exact, primary confirmed page-level). Severity: none.**
(Auditor's B0 check: (40.32 + 13.2)/3 = 17.84 GPa ✓.)

---

## 4. CoCrNi equiatomic single-crystal elastic constants (RT)

**Independently sourced.** Laplanche, Schneider, Scholz, Frenzel, Eggeler, Schreuer,
Scripta Mater. 177, 44–48 (2020), doi:10.1016/j.scriptamat.2019.09.020 (RUS on a
Bridgman-grown CrCoNi single crystal; paper itself hybrid-OA but PDF not fetchable
this session). Values read verbatim from an independent primary that quotes them:
Shih, Miao, Mills, Ghazisaeidi, "Stacking fault energy in concentrated alloys",
Nat. Commun. (2021), full text fetched: "The elastic constants used here are
**C11 = 249.4 GPa, C12 = 159.0 GPa, and C44 = 138.4 GPa** from Laplanche et al."

**Stored.** `data/candidates/round1_targets.json` → hea-cocrni: c11 = 249, c12 = 159,
c44 = 138 GPa, a0 = 3.56 Å, B0 = 189 GPa derived — same primary (verified there via
arXiv:2603.25616 Table 2, a different secondary than the one used in this audit).

**Verdict: AGREE (within stated rounding, two independent secondary quotations of the
same primary now concur). Severity: none.**
(Auditor's B0 check: (249.4 + 2×159.0)/3 = 189.1 GPa ✓ vs stored 189.)

---

## 5. Li2S antifluorite: experimental lattice constant + elastic constants

**Independently sourced.**

- Lattice constant: **a = 5.708 Å** (Zintl, Harder & Dauth, Z. Elektrochem. 40, 588
  (1934)); modern RT synchrotron XRD **a = 5.7158(1) Å** (Grzechnik et al., J. Solid
  State Chem. 154, 603 (2000)); low-T value 5.689 Å. Deng et al., J. Electrochem.
  Soc. 163, A67 (2016) (the compilation named in the audit scope) is closed-access;
  its primaries were used instead.
- Elastic constants (experimental, elastic/inelastic neutron scattering, low
  temperature; Bührer & Bill lineage): **C11 = 95.4, C12 = 21.9, C44 = 32.9 GPa;
  B0 = 45.7 GPa** — read from Table 1 of Pandit, Rakshit & Sanyal, Indian J. Pure
  Appl. Phys. 47, 804 (2009) (open access, NOPR), whose table footnote attributes
  them to Bührer & Bill, Helv. Phys. Acta 50, 431 (1977) [their ref. 10; companion
  refs: Bührer et al., J. Phys.: Condens. Matter 3, 1055 (1991) neutron; Mjwara
  et al., J. Phys.: Condens. Matter 3, 4289 (1991) Brillouin, RT→800 K].
  Consistency check: (95.4 + 2×21.9)/3 = 46.4 GPa ≈ quoted exp B0 45.7 GPa ✓.

**Stored.** No experimental Li2S targets exist in kinetics_targets.json,
round1_targets.json, or round3_targets.json. Li2S appears only in the
reference-free discovery-gates panel (`data/discovery_gates/REPORT.md`,
`python/scripts/run_discovery_gates.py`), which by design consults no experimental
values and describes Li2S as "known-good (cubic, mp-1153-like, a0 ~ 5.7 A)".

**Verdict: AGREE with the only stored claim (a0 ~ 5.7 Å: exp 5.708–5.716 Å).
Severity: none.** Context the audit adds: the four MLIP a0 values (5.70–5.73 Å)
bracket experiment almost exactly, while MLIP C11 (39.0–78.1 GPa) all fall far below
the experimental 95.4 GPa — independently consistent with the manuscript's
"softening" thesis, and a free experimental anchor the panel could cite.

---

## Verdict on the Schottky h_S anchor set (manuscript line 24)

Anchors: LiF 2.42, LiCl 2.12, LiBr 1.80, LiI 1.34, NaCl 2.83 eV, presented as
"conductivity-derived experimental values h_S = 2(E_intrinsic − ΔH_m)".

| Anchor | Derivation inputs (per kinetics_targets.json) | Arithmetic | Audit status |
|---|---|---|---|
| LiF 2.42 | 2×(1.87 − 0.66), Stoebe & Huggins 1966 | ✓ | **SOUND** — matches the primary's own published h_S |
| LiCl 2.12 | 2×(1.47 − 0.41), Haven 1950 via Alt et al. 2025 | ✓ | Plausible, single-lineage; repo itself records a conflicting dataset (h_m 0.59, h_S 1.66) |
| LiBr 1.80 | 2×(1.29 − 0.39), Haven 1950 via Alt et al. 2025 | ✓ | Plausible, single-lineage (Haven 1950 not independently readable; secondary quotations concur) |
| LiI 1.34 | 2×(1.05 − 0.38), Haven 1950 via Alt et al. 2025 | ✓ | Plausible, single-lineage |
| NaCl 2.83 | 2×(2.10 − 0.685) implied | ✓ arithmetic, ✗ inputs | **WRONG / UNSUPPORTED** — no primary found with E_int = 2.10 eV; published experimental h_S: 2.12 ± 0.07 (Dreyfus & Nowick 1962) and ~2.44 (classic compilation, stored in the repo's own kinetics file) |

Overall: **4 of 5 anchors sound-to-plausible; the NaCl anchor is not defensible as
stated.** Recommended fix: re-anchor NaCl at 2.44 eV (matching
kinetics_targets.json, cited to the classic compilation) or 2.12 ± 0.07 eV (only
fetchable primary), recompute the NaCl deficit percentage, and reconcile the
kinetics file's internally inconsistent trio (h_m 0.69 / E_int "~2.10" / h_S 2.44).

## Red flags (summary)

1. **MAJOR — manuscript NaCl h_S = 2.83 eV** is 0.4–0.7 eV above every value
   supported by fetched primaries or by the repo's own targets file; it inflates the
   NaCl Schottky-deficit percentage and would invalidate any NaCl-vs-LiF ordering
   statement. (Li-halide-only ordering claims are unaffected.)
2. **MODERATE — internal inconsistency in kinetics_targets.json NaCl entry**: the
   stated intrinsic activation (~2.10 eV) contradicts the stored h_S (2.44 eV) under
   the file's own formula; 2.10 appears to be the seed of the manuscript's 2.83.
3. **MINOR — NaCl migration band understated**: stored 0.65–0.71 eV excludes
   Dreyfus & Nowick's 0.796 ± 0.02 eV; honest experimental spread is 0.65–0.85 eV.
4. **MINOR — Hooton & Jacobs 1988 is cited but not readable**: only the anion value
   (0.744 eV) is verifiable from open metadata; the cation migration and Δh_S
   attributed to it rest on secondary compilations. Flag in the data-provenance
   appendix rather than presenting as page-verified.
5. **NOTE — Li-halide anchors (LiCl/LiBr/LiI)** all descend from one 1950 study via
   one 2025 compilation; arithmetic is exact but the lineage is single-source, and
   the repo's own LiCl caveat records a 0.46 eV-lower alternative h_S. State the
   spread when these anchors carry quantitative weight.
6. **POSITIVE — KCl, CoCrNi, LiF, Li2S-a0 all check out exactly** against primaries
   fetched independently this session (Norwood & Briscoe Table II read page-level;
   CoCrNi confirmed via a second, independent secondary quotation of Laplanche;
   Stoebe & Huggins exact; Li2S experimental a0 and Cij now documented above for
   future use as anchors).
