/**
 * Proof provenance for Phoenix / OpenInference telemetry.
 *
 * Carries exact Meta ATLAS-Lean and Mathlib dependency revisions plus a bounded
 * theorem-inventory rollup. This module owns span attributes and export headers;
 * phoenix.ts owns transport. Helpers are pure except for the passed span's
 * attribute setters.
 */

import type { Span } from "@opentelemetry/api";
import {
  SemanticConventions,
  OpenInferenceSpanKind,
} from "@arizeai/openinference-semantic-conventions";
import type { TheoremStatus } from "../research/theorems";

export { OpenInferenceSpanKind };
export type OpenInferenceSpanKindValue =
  (typeof OpenInferenceSpanKind)[keyof typeof OpenInferenceSpanKind];

/** Classify a span using the canonical OpenInference convention. */
export function setSpanKind(span: Span, kind: OpenInferenceSpanKindValue): void {
  span.setAttribute(SemanticConventions.OPENINFERENCE_SPAN_KIND, kind);
}

export interface TheoremInventorySummary {
  readonly total_imported: number;
  readonly total_extended: number;
  readonly by_facet: Readonly<Record<string, number>>;
}

/** Dependency provenance for the formal foundations used by the running build. */
export interface ProofTelemetryConfig {
  readonly meta_atlas_revision: string;
  readonly mathlib_revision: string;
  readonly theorem_inventory_summary: TheoremInventorySummary;
}

export const META_ATLAS_REVISION_HEADER = "x-lupine-meta-atlas-revision";
export const MATHLIB_REVISION_HEADER = "x-lupine-mathlib-revision";
export const THEOREM_COUNT_HEADER = "x-lupine-theorem-count";

/** Return canonical proof-provenance headers, or no headers without a config. */
export function proofExportHeaders(
  config: ProofTelemetryConfig | undefined,
): Record<string, string> {
  if (!config) return {};
  const { total_imported, total_extended } = config.theorem_inventory_summary;
  return {
    [META_ATLAS_REVISION_HEADER]: config.meta_atlas_revision,
    [MATHLIB_REVISION_HEADER]: config.mathlib_revision,
    [THEOREM_COUNT_HEADER]: String(total_imported + total_extended),
  };
}

type ParsedProofConfig =
  | { state: "valid"; config: ProofTelemetryConfig }
  | { state: "invalid" | "conflict" };

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function revision(value: unknown): string | undefined {
  return typeof value === "string" ? value.trim() || undefined : undefined;
}

function isCount(value: unknown): value is number {
  return typeof value === "number" && Number.isSafeInteger(value) && value >= 0;
}

/** The historical config field is consumed only at this input boundary. */
function parseProofConfig(raw: string): ParsedProofConfig {
  let value: unknown;
  try {
    value = JSON.parse(raw);
  } catch {
    return { state: "invalid" };
  }
  if (!isRecord(value)) return { state: "invalid" };
  const canonical = revision(value.meta_atlas_revision);
  const legacy = revision(value.atlas_revision);
  if (canonical && legacy && canonical !== legacy) return { state: "conflict" };
  if (
    (value.meta_atlas_revision !== undefined && !canonical) ||
    (value.atlas_revision !== undefined && !legacy)
  ) return { state: "invalid" };
  const metaAtlas = canonical ?? legacy;
  const mathlib = revision(value.mathlib_revision);
  if (!metaAtlas || !mathlib) return { state: "invalid" };

  const rawSummary = value.theorem_inventory_summary ?? {};
  if (!isRecord(rawSummary)) return { state: "invalid" };
  const imported = rawSummary.total_imported ?? 0;
  const extended = rawSummary.total_extended ?? 0;
  const facets = rawSummary.by_facet ?? {};
  if (
    !isCount(imported) || !isCount(extended) ||
    !Number.isSafeInteger(imported + extended) || !isRecord(facets)
  ) return { state: "invalid" };
  const entries = Object.entries(facets);
  if (!entries.every(([, count]) => isCount(count))) return { state: "invalid" };
  entries.sort(([a], [b]) => a.localeCompare(b));
  return {
    state: "valid",
    config: {
      meta_atlas_revision: metaAtlas,
      mathlib_revision: mathlib,
      theorem_inventory_summary: {
        total_imported: imported,
        total_extended: extended,
        by_facet: Object.fromEntries(entries) as Record<string, number>,
      },
    },
  };
}

/**
 * Resolve PROOF_TELEMETRY_CONFIG or discrete META_ATLAS_REVISION /
 * MATHLIB_REVISION values. Historical environment keys and config fields are
 * accepted only here. Conflicting aliases return undefined. Malformed JSON can
 * fall back to discrete revisions, preserving the previous no-throw behavior.
 */
export function resolveProofTelemetryConfig(env: {
  PROOF_TELEMETRY_CONFIG?: string;
  META_ATLAS_REVISION?: string;
  MATHLIB_REVISION?: string;
  /** Legacy input aliases; never emitted. */
  ATLAS_TELEMETRY_CONFIG?: string;
  ATLAS_REVISION?: string;
}): ProofTelemetryConfig | undefined {
  try {
    const canonicalRaw = env.PROOF_TELEMETRY_CONFIG?.trim();
    const legacyRaw = env.ATLAS_TELEMETRY_CONFIG?.trim();
    const canonical = canonicalRaw ? parseProofConfig(canonicalRaw) : undefined;
    const legacy = legacyRaw ? parseProofConfig(legacyRaw) : undefined;
    if (canonical?.state === "conflict" || legacy?.state === "conflict") return undefined;
    if (canonicalRaw && legacyRaw) {
      if (
        canonical?.state !== "valid" || legacy?.state !== "valid" ||
        JSON.stringify(canonical.config) !== JSON.stringify(legacy.config)
      ) return undefined;
    }

    const metaAtlas = env.META_ATLAS_REVISION?.trim();
    const oldRevision = env.ATLAS_REVISION?.trim();
    if (metaAtlas && oldRevision && metaAtlas !== oldRevision) return undefined;
    const discreteMetaAtlas = metaAtlas || oldRevision;
    const mathlib = env.MATHLIB_REVISION?.trim();
    const config = canonical?.state === "valid" ? canonical.config
      : legacy?.state === "valid" ? legacy.config : undefined;
    if (config) {
      if (
        (discreteMetaAtlas && discreteMetaAtlas !== config.meta_atlas_revision) ||
        (mathlib && mathlib !== config.mathlib_revision)
      ) return undefined;
      return config;
    }
    if (discreteMetaAtlas && mathlib) {
      return {
        meta_atlas_revision: discreteMetaAtlas,
        mathlib_revision: mathlib,
        theorem_inventory_summary: { total_imported: 0, total_extended: 0, by_facet: {} },
      };
    }
    return undefined;
  } catch {
    return undefined;
  }
}

export const ProofSpanAttr = {
  BUILD_META_ATLAS_REVISION: "lupine.build.meta_atlas_revision",
  BUILD_MATHLIB_REVISION: "lupine.build.mathlib_revision",
  BUILD_THEOREM_COUNT: "lupine.build.theorem_count",
  THEOREM_NAME: "lupine.theorem.name",
  THEOREM_MODULE: "lupine.theorem.module",
  THEOREM_REVISION: "lupine.theorem.revision",
  PROOF_STATUS: "lupine.proof.status",
} as const;

/** Stamp build provenance; absent config leaves the span untouched. */
export function setBuildAttributes(span: Span, config: ProofTelemetryConfig | undefined): void {
  if (!config) return;
  const { total_imported, total_extended } = config.theorem_inventory_summary;
  span.setAttribute(ProofSpanAttr.BUILD_META_ATLAS_REVISION, config.meta_atlas_revision);
  span.setAttribute(ProofSpanAttr.BUILD_MATHLIB_REVISION, config.mathlib_revision);
  span.setAttribute(ProofSpanAttr.BUILD_THEOREM_COUNT, total_imported + total_extended);
}

/** Stamp the bounded theorem reference once, without a duplicate module key. */
export function setTheoremAttributes(
  span: Span,
  theorem: {
    readonly theorem: string;
    readonly module: string;
    readonly revision: string;
    readonly status: TheoremStatus;
  },
): void {
  span.setAttribute(ProofSpanAttr.THEOREM_NAME, theorem.theorem);
  span.setAttribute(ProofSpanAttr.THEOREM_MODULE, theorem.module);
  span.setAttribute(ProofSpanAttr.THEOREM_REVISION, theorem.revision);
  span.setAttribute(ProofSpanAttr.PROOF_STATUS, theorem.status);
}
