import type { Span } from "@opentelemetry/api";
import { describe, expect, it } from "vitest";
import {
  META_ATLAS_REVISION_HEADER,
  MATHLIB_REVISION_HEADER,
  OpenInferenceSpanKind,
  ProofSpanAttr,
  THEOREM_COUNT_HEADER,
  proofExportHeaders,
  resolveProofTelemetryConfig,
  setBuildAttributes,
  setSpanKind,
  setTheoremAttributes,
  type ProofTelemetryConfig,
} from "../proofs";

const config: ProofTelemetryConfig = {
  meta_atlas_revision: "meta-revision",
  mathlib_revision: "mathlib-revision",
  theorem_inventory_summary: {
    total_imported: 3,
    total_extended: 2,
    by_facet: { analysis: 4, algebra: 1 },
  },
};
const legacyConfig = {
  atlas_revision: config.meta_atlas_revision,
  mathlib_revision: config.mathlib_revision,
  theorem_inventory_summary: config.theorem_inventory_summary,
};
type ConfigEnv = Parameters<typeof resolveProofTelemetryConfig>[0];

function recordingSpan(): { span: Span; attributes: Record<string, unknown> } {
  const attributes: Record<string, unknown> = {};
  const span = {
    setAttribute(key: string, value: unknown) {
      attributes[key] = value;
      return this;
    },
  } as unknown as Span;
  return { span, attributes };
}

describe("proof telemetry configuration", () => {
  it("resolves canonical JSON and exports only canonical provenance headers", () => {
    const resolved = resolveProofTelemetryConfig({
      PROOF_TELEMETRY_CONFIG: JSON.stringify(config),
    });
    expect(resolved).toEqual(config);
    expect(proofExportHeaders(resolved)).toEqual({
      [META_ATLAS_REVISION_HEADER]: "meta-revision",
      [MATHLIB_REVISION_HEADER]: "mathlib-revision",
      [THEOREM_COUNT_HEADER]: "5",
    });
    expect(proofExportHeaders(resolved)).not.toHaveProperty("x-lupine-atlas-revision");
  });

  it("consumes legacy environment and config keys without retaining them", () => {
    const resolved = resolveProofTelemetryConfig({
      ATLAS_TELEMETRY_CONFIG: JSON.stringify(legacyConfig),
    });
    expect(resolved).toEqual(config);
    expect(resolved).not.toHaveProperty("atlas_revision");
  });

  it("accepts matching JSON aliases independently of facet key order", () => {
    const legacy = {
      ...legacyConfig,
      theorem_inventory_summary: {
        ...config.theorem_inventory_summary,
        by_facet: { algebra: 1, analysis: 4 },
      },
    };
    expect(resolveProofTelemetryConfig({
      PROOF_TELEMETRY_CONFIG: JSON.stringify(config),
      ATLAS_TELEMETRY_CONFIG: JSON.stringify(legacy),
    })).toEqual(config);
    expect(resolveProofTelemetryConfig({
      PROOF_TELEMETRY_CONFIG: JSON.stringify({
        ...config, atlas_revision: "meta-revision",
      }),
    })).toEqual(config);
  });

  it.each([
    { META_ATLAS_REVISION: "meta-revision" },
    { ATLAS_REVISION: "meta-revision" },
    { META_ATLAS_REVISION: "meta-revision", ATLAS_REVISION: "meta-revision" },
  ])("normalizes discrete revision inputs: %j", (revisions) => {
    expect(resolveProofTelemetryConfig({
      ...revisions, MATHLIB_REVISION: "mathlib-revision",
    })).toEqual({
      meta_atlas_revision: "meta-revision",
      mathlib_revision: "mathlib-revision",
      theorem_inventory_summary: { total_imported: 0, total_extended: 0, by_facet: {} },
    });
  });

  it.each<ConfigEnv>([
    {
      META_ATLAS_REVISION: "new",
      ATLAS_REVISION: "old",
      MATHLIB_REVISION: "mathlib",
    },
    {
      PROOF_TELEMETRY_CONFIG: JSON.stringify({ ...config, atlas_revision: "different" }),
      META_ATLAS_REVISION: "meta-revision",
      MATHLIB_REVISION: "mathlib-revision",
    },
    {
      PROOF_TELEMETRY_CONFIG: JSON.stringify(config),
      ATLAS_TELEMETRY_CONFIG: JSON.stringify({ ...legacyConfig, atlas_revision: "different" }),
    },
    {
      PROOF_TELEMETRY_CONFIG: JSON.stringify(config),
      ATLAS_TELEMETRY_CONFIG: JSON.stringify({
        ...legacyConfig,
        theorem_inventory_summary: { total_imported: 4, total_extended: 2, by_facet: {} },
      }),
    },
    {
      PROOF_TELEMETRY_CONFIG: JSON.stringify(config),
      ATLAS_REVISION: "different",
    },
    {
      PROOF_TELEMETRY_CONFIG: JSON.stringify(config),
      MATHLIB_REVISION: "different",
    },
  ])("returns undefined for conflicting provenance without fallback: %j", (env) => {
    expect(resolveProofTelemetryConfig(env)).toBeUndefined();
  });

  it("preserves malformed-JSON fallback to discrete revisions", () => {
    expect(resolveProofTelemetryConfig({
      PROOF_TELEMETRY_CONFIG: "{malformed",
      META_ATLAS_REVISION: "meta-revision",
      MATHLIB_REVISION: "mathlib-revision",
    })).toEqual({
      meta_atlas_revision: "meta-revision",
      mathlib_revision: "mathlib-revision",
      theorem_inventory_summary: { total_imported: 0, total_extended: 0, by_facet: {} },
    });
  });

  it.each([
    null,
    [],
    { meta_atlas_revision: 42, mathlib_revision: "mathlib" },
    { ...config, theorem_inventory_summary: { total_imported: "3" } },
    { ...config, theorem_inventory_summary: { total_extended: -1 } },
    { ...config, theorem_inventory_summary: { by_facet: { analysis: "4" } } },
    {
      ...config,
      theorem_inventory_summary: {
        total_imported: Number.MAX_SAFE_INTEGER, total_extended: 1,
      },
    },
  ])("does not export malformed config: %j", (value) => {
    expect(resolveProofTelemetryConfig({
      PROOF_TELEMETRY_CONFIG: JSON.stringify(value),
    })).toBeUndefined();
  });

  it("never throws for malformed runtime environment values", () => {
    const malformed = { PROOF_TELEMETRY_CONFIG: 42 } as unknown as ConfigEnv;
    expect(() => resolveProofTelemetryConfig(malformed)).not.toThrow();
    expect(resolveProofTelemetryConfig(malformed)).toBeUndefined();
    expect(resolveProofTelemetryConfig({})).toBeUndefined();
    expect(proofExportHeaders(undefined)).toEqual({});
  });
});

describe("proof span attributes", () => {
  it("preserves OpenInference classification and emits explicit Meta build provenance", () => {
    const { span, attributes } = recordingSpan();
    setSpanKind(span, OpenInferenceSpanKind.TOOL);
    setBuildAttributes(span, config);
    expect(attributes).toMatchObject({
      [ProofSpanAttr.BUILD_META_ATLAS_REVISION]: "meta-revision",
      [ProofSpanAttr.BUILD_MATHLIB_REVISION]: "mathlib-revision",
      [ProofSpanAttr.BUILD_THEOREM_COUNT]: 5,
    });
    expect(attributes).not.toHaveProperty("lupine.build.atlas_revision");
  });

  it("leaves the span untouched when build provenance is absent", () => {
    const { span, attributes } = recordingSpan();
    setBuildAttributes(span, undefined);
    expect(attributes).toEqual({});
  });

  it("stamps each theorem field once without the old duplicate module attribute", () => {
    const { span, attributes } = recordingSpan();
    setTheoremAttributes(span, {
      theorem: "Atlas.Analysis.example",
      module: "Atlas.Analysis",
      revision: "proof-revision",
      status: "verified",
    });
    expect(attributes).toEqual({
      [ProofSpanAttr.THEOREM_NAME]: "Atlas.Analysis.example",
      [ProofSpanAttr.THEOREM_MODULE]: "Atlas.Analysis",
      [ProofSpanAttr.THEOREM_REVISION]: "proof-revision",
      [ProofSpanAttr.PROOF_STATUS]: "verified",
    });
    expect(attributes).not.toHaveProperty("lupine.atlas.module");
    expect(Object.values(ProofSpanAttr)).not.toContain("lupine.atlas.module");
  });
});
