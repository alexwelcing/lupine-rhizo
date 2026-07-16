/**
 * Canonical ATLAS facet registry (runtime mirror).
 *
 * The durable facet identities are lowercase (`causal`, `experiment`,
 * `manifold`, `theorist`) — that is how rows are keyed in `atlas_theorems`,
 * `atlas_facet_registry`, and `config/atlas_theorem_registry.v1.json`. Agent
 * class names are class-cased (`Causal`, `Experiment`, …), so a naive
 * `constructor.name` lookup can never join to the theorem inventory. This
 * module is the single runtime source of truth for:
 *
 *   - agent-class → canonical facet mapping (mirrors the
 *     `atlas_facet_registry` seed rows and the v1 JSON registry),
 *   - facet normalization for any ad-hoc facet strings,
 *   - the extension-approval policy that decides which `extended` theorem
 *     rows are allowed to ground an agent (mirrors `extension_policy` in
 *     config/atlas_theorem_registry.v1.json).
 *
 * Keep this mirror in sync with the JSON registry and the migration seeds;
 * the synchronizer (tools/atlas_theorem_sync.py) is the authority that
 * writes rows, this module only governs how glim-think reads them.
 */

/** Facets the ATLAS inventory manages, in canonical lowercase form. */
export const MANAGED_FACETS = ["causal", "experiment", "manifold", "theorist"] as const;

export type ManagedFacet = (typeof MANAGED_FACETS)[number];

/**
 * Explicit agent-class → canonical facet mapping. Mirrors the
 * `atlas_facet_registry` seed rows (migration 0011) and
 * `config/atlas_theorem_registry.v1.json` `managed_facets`.
 */
const AGENT_CLASS_TO_FACET: Readonly<Record<string, ManagedFacet>> = {
  Causal: "causal",
  Experiment: "experiment",
  Manifold: "manifold",
  Theorist: "theorist",
};

/** Normalize any facet string to the canonical lowercase key form. */
export function normalizeFacet(value: string): string {
  return value.trim().toLowerCase();
}

/**
 * Resolve an agent class name (e.g. `Experiment`) to its canonical facet key
 * (`experiment`). Known ATLAS-managed agents use the explicit mapping;
 * anything else falls back to lowercase normalization so unmanaged agents get
 * a stable, empty inventory rather than a case-mismatched one.
 */
export function canonicalFacetForAgentClass(agentClass: string): string {
  return AGENT_CLASS_TO_FACET[agentClass] ?? normalizeFacet(agentClass);
}

/** True when `facet` is one of the ATLAS-managed facets (after normalization). */
export function isManagedFacet(facet: string): facet is ManagedFacet {
  return (MANAGED_FACETS as ReadonlyArray<string>).includes(normalizeFacet(facet));
}

/**
 * Extension-approval policy, mirrored from
 * `config/atlas_theorem_registry.v1.json` `extension_policy`. An `extended`
 * theorem row may ground an agent only when its owning facet is listed here
 * AND its module sits under one of the approved module prefixes — i.e. the
 * extension was proved locally under a namespace the registry explicitly
 * allows that facet to extend. `verified` rows are always groundable; this
 * policy only gates `extended` rows.
 */
export const EXTENSION_POLICY = {
  facets: ["experiment"],
  module_prefixes: [
    "OpenDistillationFactory.Materials.DistillAtlas.",
    "OpenDistillationFactory.Materials.RegimeGate.",
  ],
} as const;

/**
 * True when an `extended` theorem row is explicitly approved to ground the
 * given facet. Pure + side-effect-free.
 */
export function isApprovedExtension(facet: string, module: string): boolean {
  const canonical = normalizeFacet(facet);
  if (!(EXTENSION_POLICY.facets as ReadonlyArray<string>).includes(canonical)) return false;
  return EXTENSION_POLICY.module_prefixes.some((prefix) => module.startsWith(prefix));
}
