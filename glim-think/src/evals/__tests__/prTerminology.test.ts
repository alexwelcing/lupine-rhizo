import { describe, expect, it } from "vitest";
import { evaluateParticipationRatioTerminology } from "../prTerminology";

describe("participation-ratio terminology evaluator", () => {
  it("passes the MLIP covariance-spectrum sense", () => {
    const result = evaluateParticipationRatioTerminology(
      "Explain PR for the MLIP elastic-constant manifold.",
      "Here PR is the effective dimension of the covariance eigenvalue spectrum over relative-error vectors: (sum lambda)^2 / sum lambda^2.",
    );

    expect(result).toMatchObject({ relevant: true, label: "pass", score: 1 });
  });

  it("fails the phonon/vibrational-mode sense in MLIP manifold answers", () => {
    const result = evaluateParticipationRatioTerminology(
      "Explain participation ratio for the MLIP elastic-constant manifold.",
      "Participation ratio measures phonon q-point supercell low-frequency acoustic mode localization.",
    );

    expect(result).toMatchObject({ relevant: true, label: "fail", score: 0 });
  });

  it("skips unrelated coordination answers", () => {
    const result = evaluateParticipationRatioTerminology(
      "Summarize today's agenda.",
      "Queue the next literature review and update the public report.",
    );

    expect(result).toMatchObject({ relevant: false, label: "skip" });
  });
});
