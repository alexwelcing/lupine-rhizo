import { describe, expect, it } from "vitest";
import { buildObservedManifoldMatrix, covarianceParticipationRatio } from "../observedManifoldMatrix";

describe("covariance participation ratio", () => {
  it("uses off-diagonal covariance for one perfectly correlated mode", () => {
    expect(covarianceParticipationRatio([[1, 1, 1], [1, 1, 1], [1, 1, 1]])).toBe(1);
  });
  it("retains three independent equal modes", () => {
    expect(covarianceParticipationRatio([[1, 0, 0], [0, 1, 0], [0, 0, 1]])).toBe(3);
  });
  it("preserves PR under an orthogonal rotation of modes with eigenvalues 1, 2, 3", () => {
    const diagonal = [[1, 0, 0], [0, 2, 0], [0, 0, 3]];
    // Rotation has cos=3/5 and sin=4/5. Eigenvalues remain 1, 2, 3.
    const rotated = [[41 / 25, -12 / 25, 0], [-12 / 25, 34 / 25, 0], [0, 0, 3]];
    expect(covarianceParticipationRatio(diagonal)).toBeCloseTo(18 / 7, 12);
    expect(covarianceParticipationRatio(rotated)).toBeCloseTo(18 / 7, 12);
  });
  it("is unchanged by finite common scales whose squares overflow or underflow", () => {
    for (const scale of [1e200, 1e-200]) {
      expect(covarianceParticipationRatio([[scale, scale], [scale, scale]])).toBe(1);
    }
  });
  it("abstains for zero, malformed or nonfinite covariance", () => {
    for (const cov of [[], [[0, 0], [0, 0]], [[1, 0], [1]], [[Infinity]], [[NaN]]]) {
      expect(covarianceParticipationRatio(cov)).toBeNull();
    }
  });
});

describe("fixed elastic basis", () => {
  const row = (element: string, id: string, property: string, predicted: number) => ({
    element, potential_id: id, potential_label: id, property, reference: 100, predicted, unit: "GPa",
  });
  it("does not shrink the basis when an entire elastic component is missing", () => {
    const records = ["a", "b", "c"].flatMap((id, i) =>
      ["C11", "C12"].map(property => row("Cu", id, property, 90 + 10 * i)));
    expect(buildObservedManifoldMatrix(records, ["C11", "C12", "C44"])).toMatchObject({
      ok: false, error: "insufficient_complete_observations",
      selection: { complete_row_count: 0, missing_cell_count: 3, properties: ["C11", "C12", "C44"] },
    });
  });
  it("does not assemble a tensor by taking different properties from different elements", () => {
    const records = ["a", "b", "c"].flatMap((id, i) => [
      row("Cu", id, "C11", 90 + 10 * i),
      row("Al", id, "C12", 90 + 10 * i),
      row("Fe", id, "C44", 90 + 10 * i),
    ]);
    expect(buildObservedManifoldMatrix(records, ["C11", "C12", "C44"])).toMatchObject({
      ok: false, error: "insufficient_complete_observations",
      selection: { input_row_count: 9, complete_row_count: 0, excluded_row_count: 9 },
    });
  });
  it("rejects duplicate or inconsistent declared property bases", () => {
    expect(buildObservedManifoldMatrix([], ["C11", "C11"])).toMatchObject({ ok: false });
    expect(buildObservedManifoldMatrix([row("Cu", "a", "C66", 110)], ["C11", "C12", "C44"])).toMatchObject({
      ok: false, error: "invalid_required_properties",
    });
  });
});
