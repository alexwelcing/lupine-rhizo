# Y-matrix reference targets

Compiled 2026-07-01. Eight families of reference values (`lupine.y_matrix_targets.v1` schema), one JSON file
per family, for the 16-metal set (Ag, Al, Au, Ca, Cr, Cu, Fe, Mo, Nb, Ni, Pd, Pt, Sr, Ta, V, W) plus Si, MgO,
NaCl, NiAl, Ni3Al. Every entry carries a `source` record with citation, URL, and a `notes` field stating exactly
how and when the number was verified.

## Coverage per family

| Family | File | Entries resolved / sought | Notes |
|---|---|---|---|
| finite_t | `finite_t.json` | 34 / 34 | Melting points + linear thermal expansion (300 K), 16 metals + Si; CRC-attributed. Compiled in a previous run. |
| vacancy_formation | `vacancy_formation.json` | 28 / 32 | DFT-PBE: 16/16 (Angsten NJP 2014 for fcc; Ma & Dudarev PRM 2019 for bcc). Experiment: 12/16 (Ehrhart Landolt-Bornstein III/25 recommended values for fcc; positron/quench primaries for bcc). |
| surface_energies | `surface_energies.json` | 57 / 57 | DFT-PBE per-facet: 41/41, read programmatically from the actual Tran et al. Sci. Data 2016 Dryad dataset (`surfaces.json`); 4 facet entries are the reconstructed termination (flagged). Experiment: 16/16 Tyson & Miller 1977 polycrystalline values (de Boer 1988 companion values in notes), via the Vitos 1998 tabulation. |
| stacking_faults | `stacking_faults.json` | 14 / 14 | Intrinsic SFE for Ag, Al, Au, Cu, Ni, Pd, Pt; DFT-PBE (Li et al. 2015 EMTO-PBE; Linda et al. 2024 VASP-PBE for Pd) + experiment (weak-beam TEM primaries: Cockayne/Jenkins/Ray, Stobbs & Sworn, Jenkins; Murr 1973 for Al; Hirth & Lothe tabulation for Ni, Pt). Pd experiment is the weakest entry (unresolved primary attribution). |
| eos | `eos.json` | 26 / 16 B0 + B0' where available | Experimental B0 for all 16 metals: 15 precise (ultrasonic primaries, via Zhang et al. NJP 2018 SI tabulation; 0 K-extrapolated, property named accordingly) + Cr coarse (CRC, 2 s.f.). B0' (DAC, 300 K): 10 metals (Dewaele Minerals 2019 Rydberg-Vinet refits of Dewaele-group DAC data; Young et al. 2016 for Cr) + NaCl-B1 in beyond_metals. |
| beyond_metals | `beyond_metals.json` | 23 / ~29 | Si: a0, B0, C11/C12/C44 (Ioffe, 300 K), vacancy (PBE 3.63 eV + positron 3.6 eV flagged), Gamma LTO phonon 15.5 THz (Ioffe, primaries Dolling/Tubino). MgO: a0, adiabatic B0, C11/C12/C44 (Sinogeikin & Bass via Fan 2019), dKs/dP. NaCl: a0, isothermal B0 + B0' (Dewaele 2019 B1-phase DAC). PBE lattice constants and B0 for all three (Csonka PRB 2009, cross-checked against Zhang 2018). |
| intermetallics | `intermetallics.json` | 14 / ~16 | NiAl (B2): formation enthalpy (Nash & Kleppa 2001 calorimetry, -0.6405(115) eV/atom, from the Kim/Meschel/Nash/Chen Sci Data 2017 figshare dataset; MP/OQMD PBE), a0, B0 (Rusovic & Warlimont). Ni3Al (L12): formation enthalpy (Debski 2013 calorimetry; MP PBE), a0, B0 (Yoo 1987), APB(111) experiment ~195 mJ/m^2 + DFT-PBE 188 mJ/m^2 with idealized-vs-relaxed range documented. |
| lattice_constants | `lattice_constants.json` | 32 / 32 | a0 for all 16 metals, experiment + DFT-PBE. Experiment: 15 metals at three decimals from Zhang et al. NJP 2018 SI Table II 'Exp.' column (0 K unless noted, ZPE retained; primaries: Haas/Tran/Blaha 2009 for the bcc metals + Pt, Staroverov 2004 for Cu/Pd/Ag, Anderson 1990 for Ca/Sr, Touloukian for Au, Gaudoin & Foulkes + Kresch for Ni, Landolt-Bornstein for Al) + Cr coarse (Kittel 7th ed. 2.88 A via Ma & Dudarev Table I; Young DAC-fit conversion 2.885 A at 300 K noted). DFT-PBE: 15 from the same Zhang table (PBE Uncorr. column) + Cr 2.862 A from Ma & Dudarev Table I. |

Totals: 228 resolved entries across 8 files.

## Unresolved gaps (explicit)

Each item below is also recorded in the `unresolved` array of its family file.

**vacancy_formation**
- Ca, Sr - experimental vacancy formation energy: no verifiable equilibrium/positron measurement found.
- V - experiment: literature commonly quotes ~2.1-2.2 eV, but no fetchable source with checkable attribution was found; no number recorded.
- Cr - experiment: notoriously ill-determined; no recommended value verified.

**surface_energies**
- Ag, Au, Pt (110) and Sr (111): the Tran dataset stores the reconstructed lowest-energy termination (`is_reconstructed=true`, flagged per entry); unreconstructed (1x1) values not separately extractable.

**stacking_faults**
- Pd experiment: recorded 130 mJ/m^2 rests on Linda et al. (2024) Table 1 with an unresolved primary reference; the Murr-1975 compilation value for Pd was not independently verified.
- Al experiment: only the Murr (1973)-derived 166 mJ/m^2 was verifiable; later reassessments (~120-144 mJ/m^2) not verified and omitted.

**eos**
- Cr B0: only a coarse 2-s.f. CRC value (160 GPa) verifiable; LLNL DAC fit gives a conflicting 193.5 GPa (flagged, not resolved).
- B0' missing for Ca, Sr, V, Nb, and bcc Fe (alpha-Fe transforms to hcp at ~13 GPa; only epsilon-Fe DAC parameters exist).

**beyond_metals**
- Si vacancy experiment (Dannefaer 3.6 +/- 0.2 eV): verified only from the PRL abstract text surfaced in search results (APS blocked direct fetch); entry included but flagged.
- DFT-PBE elastic constants for Si and MgO: not verified this session.
- DFT-PBE Gamma phonon for Si: not verified this session.

**intermetallics**
- B2-NiAl DFT a0/B0 are GGA-PW91 (Ward et al.), not strictly PBE; a PBE-labelled pair was not separately verified.
- Ni3Al APB(111) experiment: only the "~195 mJ/m^2" consensus statement verified; per-study primaries (Baluc 1991, Hemker & Mills, Baither 2002, Douin 1986) not individually fetched. Treat as +/-10%.
- Ni3Al Kleppa-lab direct-synthesis formation enthalpy: absent from the Kim et al. dataset; not verified.

**lattice_constants**
- Cr experiment: only a 2-decimal Kittel-attributed value (2.88 A) was verifiable (Cr absent from the Zhang et al. set); the Young et al. DAC-fit conversion gives 2.885 A at 300 K. A precise 0 K-extrapolated diffraction value for Cr remains unresolved.

**finite_t** (from the earlier run)
- Si thermal expansion: no CRC-attributed value verifiable; entry uses Ioffe NSM / Okada & Tokumaru instead.

## No-fabrication statement

Every numeric value in these files was transcribed from a source document actually retrieved and read during the
compilation session (web fetch of an HTML page, download and text extraction of an open PDF/preprint, or
programmatic parse of a published dataset file such as the Tran et al. Dryad `surfaces.json` and the Kim et al.
figshare `enthalpy_formation.json`); the `notes` field of each entry records the retrieval route and date, and
where a value was derived arithmetically from a verified number (e.g., a lattice constant from a cell volume, or
a unit conversion) the derivation is stated explicitly. No value was written from memory, interpolated,
averaged across unverified sources, or estimated. Where a sought quantity could not be verified through an
accessible source - even when "well-known" values circulate in the literature - the gap is recorded in the
`unresolved` array of the family file and in the list above rather than filled, and entries resting on weaker
provenance (search-snippet verification, unresolved secondary attribution, coarse handbook rounding, or
reconstructed-surface caveats) are explicitly flagged in their notes so that downstream machine checks can
weight or exclude them.
