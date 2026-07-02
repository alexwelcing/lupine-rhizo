/**
 * Property-aware range gate (research/recordValidation.ts).
 *
 * The original elastic-era gate hard-rejected predicted <= 0 and
 * |predicted| > 1500 everywhere. That is wrong for the Y-matrix
 * property families: formation enthalpies (ΔH_f) are negative for every
 * stable compound, stacking-fault energies and B0′ legitimately cross
 * zero (Fe has B0′ < 0), and melting points exceed 1500 K. We assert:
 *
 *   1. sign-flexible properties admit negative predicted/reference;
 *   2. per-unit ceilings admit T_m up to 4000 K but still reject unit
 *      errors / non-converged sentinels (NaN, Inf, absurd magnitudes);
 *   3. on the legacy corpus shape (C11/C12/C44 in GPa) the gate reduces
 *      EXACTLY to the old predicate — positivity, 1500 ceiling, >500%
 *      scale-free relative rule — so a redeployed purge deletes nothing
 *      it would not have deleted before;
 *   4. the SQL twins (purge delete criterion, Manifold CLEAN filter)
 *      carry the same property/unit awareness so the lanes cannot drift.
 */
import { describe, it, expect } from "vitest";
import {
  allowsNegative,
  cleanRecordSqlPredicate,
  corruptRecordSqlPredicate,
  DEFAULT_MAGNITUDE_CEILING,
  isContaminatedRecord,
  magnitudeCeiling,
  recordContaminationReason,
} from "../recordValidation";

describe("allowsNegative — sign-convention classes", () => {
  it("admits negative-convention properties (case-insensitive)", () => {
    for (const property of [
      "formation_enthalpy",
      "dh_f",
      "stacking_fault_energy",
      "gamma_sfe",
      "B0_prime",
      "bulk_modulus_pressure_derivative",
      "binding_energy",
    ]) {
      expect(allowsNegative(property), property).toBe(true);
    }
  });

  it("keeps sign-fixed properties positive-only", () => {
    for (const property of ["C11", "C12", "C44", "a0", "B0", "e_vac", "gamma_100", "melting_point"]) {
      expect(allowsNegative(property), property).toBe(false);
    }
    // vacancy_formation_energy contains "formation" but is positive-definite.
    expect(allowsNegative("vacancy_formation_energy")).toBe(false);
    expect(allowsNegative(null)).toBe(false);
    expect(allowsNegative("")).toBe(false);
  });
});

describe("magnitudeCeiling — per-unit physical ceilings", () => {
  it("maps unit classes to their ceilings, case-insensitively", () => {
    expect(magnitudeCeiling("GPa")).toBe(1500);
    expect(magnitudeCeiling("K")).toBe(4000);
    expect(magnitudeCeiling("eV")).toBe(50);
    expect(magnitudeCeiling("eV/atom")).toBe(50);
    expect(magnitudeCeiling("Angstrom")).toBe(100);
    expect(magnitudeCeiling("J/m^2")).toBe(50);
    expect(magnitudeCeiling("mJ/m^2")).toBe(50000);
    expect(magnitudeCeiling("dimensionless")).toBe(1000);
  });

  it("falls back to the legacy 1500 backstop for unknown units", () => {
    expect(magnitudeCeiling("furlongs")).toBe(DEFAULT_MAGNITUDE_CEILING);
    expect(magnitudeCeiling("")).toBe(DEFAULT_MAGNITUDE_CEILING);
    expect(magnitudeCeiling(null)).toBe(DEFAULT_MAGNITUDE_CEILING);
  });
});

describe("recordContaminationReason — Y-matrix lanes the old gate broke", () => {
  it("admits negative formation enthalpy (NiAl ΔH_f, both sides negative)", () => {
    expect(
      recordContaminationReason({
        property: "formation_enthalpy",
        unit: "eV/atom",
        predicted: -0.7051,
        reference: -0.6586,
      }),
    ).toBeNull();
  });

  it("admits a genuinely negative predicted stacking-fault energy", () => {
    // Real Al/mace-mp-small failure: pred -7.62 vs ref 117.54 mJ/m^2 —
    // a large, informative model error, not corruption.
    expect(
      recordContaminationReason({
        property: "stacking_fault_energy",
        unit: "mJ/m^2",
        predicted: -7.62,
        reference: 117.54,
      }),
    ).toBeNull();
  });

  it("admits melting points above the old 1500 bound (W: 3695 K)", () => {
    expect(
      recordContaminationReason({
        property: "melting_point",
        unit: "K",
        predicted: 3400,
        reference: 3695,
      }),
    ).toBeNull();
  });

  it("still rejects absurd magnitudes per unit class", () => {
    expect(
      recordContaminationReason({ property: "melting_point", unit: "K", predicted: 5200, reference: 3695 }),
    ).toMatch(/ceiling/);
    expect(
      recordContaminationReason({ property: "C11", unit: "GPa", predicted: 51234, reference: 168 }),
    ).toMatch(/ceiling/);
    expect(
      recordContaminationReason({ property: "a0", unit: "Angstrom", predicted: 4100, reference: 4.05 }),
    ).toMatch(/ceiling/);
  });

  it("always rejects non-finite values", () => {
    expect(
      recordContaminationReason({ property: "dh_f", unit: "eV/atom", predicted: Number.NaN, reference: -0.5 }),
    ).toMatch(/non-finite/);
    expect(
      recordContaminationReason({
        property: "dh_f",
        unit: "eV/atom",
        predicted: Number.POSITIVE_INFINITY,
        reference: -0.5,
      }),
    ).toMatch(/non-finite/);
  });
});

describe("recordContaminationReason — legacy elastic corpus unchanged", () => {
  const legacy = (predicted: number, reference: number) =>
    recordContaminationReason({ property: "C11", unit: "GPa", predicted, reference });

  it("accepts a normal elastic record", () => {
    expect(legacy(102.1, 108.2)).toBeNull();
  });

  it("rejects non-positive predicted/reference (Born stability)", () => {
    expect(legacy(-5, 108.2)).toMatch(/sign-fixed/);
    expect(legacy(0, 108.2)).toMatch(/sign-fixed/);
    expect(legacy(102.1, 0)).toMatch(/sign-fixed/);
  });

  it("rejects >500% scale-free relative error (subtle unit slips)", () => {
    expect(legacy(1200, 150)).toMatch(/500%/);
    // exactly 5x is allowed, matching the old <= boundary
    expect(legacy(900, 150)).toBeNull();
  });

  it("rejects |predicted| beyond the 1500 GPa elastic ceiling", () => {
    expect(legacy(1501, 1400)).toMatch(/ceiling/);
  });
});

describe("SQL twins — purge criterion and CLEAN filter", () => {
  it("corrupt predicate carries the unit-ceiling CASE and sign exemptions", () => {
    const sql = corruptRecordSqlPredicate();
    expect(sql).toContain("predicted IS NULL OR reference IS NULL");
    expect(sql).toContain("WHEN 'gpa' THEN 1500");
    expect(sql).toContain("WHEN 'k' THEN 4000");
    expect(sql).toContain(`ELSE ${DEFAULT_MAGNITUDE_CEILING} END`);
    expect(sql).toContain("'formation_enthalpy'");
    expect(sql).toContain("'gamma_sfe'");
    expect(sql).toContain("'b0_prime'");
    // sign + relative rules are scoped to the NOT IN branch
    expect(sql).toMatch(/NOT IN \([^)]*\)\s*AND \(predicted <= 0/);
    expect(sql).toContain("5 * ABS(reference)");
  });

  it("clean predicate is the guarded negation of the corrupt predicate", () => {
    const clean = cleanRecordSqlPredicate();
    expect(clean).toContain("predicted IS NOT NULL AND reference IS NOT NULL");
    expect(clean).toContain(`NOT (${corruptRecordSqlPredicate()})`);
  });
});

describe("isContaminatedRecord — boolean wrapper", () => {
  it("mirrors recordContaminationReason", () => {
    expect(
      isContaminatedRecord({ property: "dh_f", unit: "eV/atom", predicted: -0.47, reference: -0.43 }),
    ).toBe(false);
    expect(
      isContaminatedRecord({ property: "C11", unit: "GPa", predicted: -0.47, reference: 108 }),
    ).toBe(true);
  });
});
