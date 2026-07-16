import { describe, expect, it } from "vitest";
import {
  canonicalFacetForAgentClass,
  isApprovedExtension,
  isManagedFacet,
  normalizeFacet,
} from "../facetRegistry";

describe("canonical facet mapping", () => {
  it("maps each ATLAS-managed agent class to its canonical lowercase facet", () => {
    expect(canonicalFacetForAgentClass("Causal")).toBe("causal");
    expect(canonicalFacetForAgentClass("Experiment")).toBe("experiment");
    expect(canonicalFacetForAgentClass("Manifold")).toBe("manifold");
    expect(canonicalFacetForAgentClass("Theorist")).toBe("theorist");
  });

  it("never returns the raw class-cased constructor name for managed agents", () => {
    for (const cls of ["Causal", "Experiment", "Manifold", "Theorist"]) {
      const facet = canonicalFacetForAgentClass(cls);
      expect(facet).toBe(facet.toLowerCase());
      expect(facet).not.toBe(cls);
    }
  });

  it("falls back to lowercase normalization for unmanaged agents", () => {
    expect(canonicalFacetForAgentClass("Orchestrator")).toBe("orchestrator");
    expect(canonicalFacetForAgentClass("Literaturist")).toBe("literaturist");
  });

  it("normalizes ad-hoc facet strings", () => {
    expect(normalizeFacet("  Experiment ")).toBe("experiment");
    expect(normalizeFacet("CAUSAL")).toBe("causal");
  });

  it("recognizes managed facets case-insensitively", () => {
    expect(isManagedFacet("manifold")).toBe(true);
    expect(isManagedFacet("Manifold")).toBe(true);
    expect(isManagedFacet("orchestrator")).toBe(false);
  });
});

describe("extension approval policy", () => {
  it("approves experiment extensions under the registry module prefixes", () => {
    expect(
      isApprovedExtension("experiment", "OpenDistillationFactory.Materials.DistillAtlas.Foo"),
    ).toBe(true);
    expect(
      isApprovedExtension("experiment", "OpenDistillationFactory.Materials.RegimeGate.Bar"),
    ).toBe(true);
  });

  it("rejects experiment extensions outside the approved prefixes", () => {
    expect(
      isApprovedExtension("experiment", "OpenDistillationFactory.Materials.Validation.Experiment"),
    ).toBe(false);
    expect(
      isApprovedExtension("experiment", "Atlas.Manifold.Core"),
    ).toBe(false);
  });

  it("rejects extensions for facets the policy does not list", () => {
    expect(
      isApprovedExtension("manifold", "OpenDistillationFactory.Materials.DistillAtlas.Foo"),
    ).toBe(false);
    expect(
      isApprovedExtension("theorist", "OpenDistillationFactory.Materials.RegimeGate.Bar"),
    ).toBe(false);
  });

  it("normalizes the facet before checking", () => {
    expect(
      isApprovedExtension("Experiment", "OpenDistillationFactory.Materials.DistillAtlas.Foo"),
    ).toBe(true);
  });
});
