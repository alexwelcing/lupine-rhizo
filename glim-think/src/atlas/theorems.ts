/**
 * ATLAS-Lean theorem inventory: shared-ledger access + bounded reference types.
 *
 * Per ATLAS_Lean_Integration_Review §8.4, each facet (specialist agent) depends
 * on a bounded set of formally-verified theorems from the ATLAS-Lean layer. The
 * full proofs live in the Lean project; glim-think only ever holds REFERENCES
 * (theorem name + module + revision + status) so Durable Object state stays
 * bounded — never proof bodies.
 *
 * The inventory lives in the shared D1 ledger (`env.LEDGER`) so the whole fleet
 * can query by facet. See migrations/0010_atlas_theorems.sql (base tables) and
 * migrations/0011_atlas_schema_reconciliation.sql (facet registry, statuses,
 * lifecycle states, proof revisions, hashes). Facet keys are canonical
 * lowercase — see ./facetRegistry for the agent-class mapping and the
 * extension-approval policy that gates which rows may ground an agent.
 */

import type { Env } from "../types";
import { isApprovedExtension, normalizeFacet } from "./facetRegistry";

/** Verification lifecycle of a theorem reference within a facet. */
export type AtlasTheoremStatus = "imported" | "verified" | "extended" | "failed";

/** Lifecycle state of a theorem row (migration 0011). */
export type AtlasTheoremLifecycle = "active" | "retired" | "superseded";

/**
 * Statuses allowed to ground an agent. `verified` rows ground unconditionally;
 * `extended` rows ground only when the registry extension policy approves the
 * facet+module pair (enforced in JS by {@link isGroundableRef}, since the
 * prefix rule is not expressible in D1 SQL). `imported` and `failed` rows must
 * never ground an agent.
 */
export const GROUNDABLE_STATUSES: ReadonlyArray<AtlasTheoremStatus> = ["verified", "extended"];

/** Default / hard cap for theorem-inventory reads — keeps DO state bounded (§8.4). */
export const DEFAULT_THEOREM_LIMIT = 128;
export const MAX_THEOREM_LIMIT = 512;

/**
 * A single theorem reference as stored in the shared `atlas_theorems` table.
 * This is a reference only — the proof itself is never carried here.
 */
export interface AtlasTheoremRef {
  readonly id: number;
  readonly facet: string;
  readonly theorem_name: string;
  readonly module: string;
  readonly revision: string;
  readonly status: AtlasTheoremStatus;
  readonly lifecycle_status?: AtlasTheoremLifecycle;
  readonly used_in_hypotheses: number;
  readonly created_at: string;
}

/**
 * Compact reference carried in facet-to-facet RPC payloads and DO-local state.
 * Drops the surrogate id / counters so the payload stays small (§8.4: bounded).
 */
export interface FormalBasis {
  /** Theorem name as it appears in the Lean source (e.g. `Atlas.Manifold.prCongr`). */
  readonly theorem: string;
  /** Lean module path the theorem is defined in (e.g. `Atlas/Manifold/Core.lean`). */
  readonly module: string;
  /** ATLAS revision the reference is pinned to (git sha or tag). */
  readonly revision: string;
  /** Verification status of the reference at the time it was attached. */
  readonly status: AtlasTheoremStatus;
  /**
   * Optional natural-language helper describing how the theorem grounds the
   * payload (e.g. "PR is invariant under basis change → manifold dims comparable").
   */
  readonly helper?: string;
}

/** A bounded, JSON-serializable inventory summary for one facet's theorems. */
export interface TheoremInventory {
  readonly facet: string;
  readonly total: number;
  readonly by_status: Readonly<Record<AtlasTheoremStatus, number>>;
  /** References only — capped by the caller to keep the document small. */
  readonly theorems: ReadonlyArray<FormalBasis>;
  /**
   * Non-null when the inventory query itself failed — distinguishes a load
   * error from a genuinely empty inventory (which serializes `load_error:
   * null`). Absent on inventories built from rows loaded by other means.
   */
  readonly load_error?: string | null;
}

const EMPTY_BY_STATUS: Record<AtlasTheoremStatus, number> = {
  imported: 0,
  verified: 0,
  extended: 0,
  failed: 0,
};

/**
 * Result of a theorem-inventory read. `error` is non-null when the query
 * failed (e.g. table absent, D1 outage) so callers can distinguish a load
 * error from a genuinely empty inventory — the two must never collapse into
 * the same "no theorems" state, because an agent grounded on a failed read
 * silently loses its formal basis.
 */
export interface FacetTheoremLoad {
  readonly facet: string;
  readonly rows: AtlasTheoremRef[];
  readonly error: string | null;
}

/**
 * True when a theorem reference is allowed to ground an agent payload:
 *   - `verified` rows always ground;
 *   - `extended` rows ground only when the registry extension policy
 *     explicitly approves the facet + module pair;
 *   - `imported` / `failed` rows never ground;
 *   - retired/superseded rows never ground (when the column is present).
 */
export function isGroundableRef(
  ref: Pick<AtlasTheoremRef, "status" | "facet" | "module" | "lifecycle_status">,
): boolean {
  if (ref.lifecycle_status && ref.lifecycle_status !== "active") return false;
  if (ref.status === "verified") return true;
  if (ref.status === "extended") return isApprovedExtension(ref.facet, ref.module);
  return false;
}

/**
 * Load theorem references for a facet from the shared ledger, newest first.
 *
 * Grounding-safe by default: unless the caller passes explicit `statuses`,
 * only `verified` / `extended` rows in the `active` lifecycle are read — an
 * `imported` or `failed` row can never reach an agent through this path. The
 * query is always bounded by a SQL `LIMIT` (default
 * {@link DEFAULT_THEOREM_LIMIT}, hard-capped at {@link MAX_THEOREM_LIMIT}) so
 * DO state stays bounded regardless of inventory size.
 *
 * Never throws: a failed read returns `{ rows: [], error }` so an
 * unprovisioned facet still boots cleanly, while the caller can surface the
 * error separately from an empty inventory.
 */
export async function loadFacetTheorems(
  env: Env,
  facet: string,
  opts?: {
    statuses?: ReadonlyArray<AtlasTheoremStatus>;
    lifecycleStatus?: AtlasTheoremLifecycle;
    limit?: number;
  },
): Promise<FacetTheoremLoad> {
  const canonical = normalizeFacet(facet);
  const statuses = opts?.statuses && opts.statuses.length > 0 ? opts.statuses : GROUNDABLE_STATUSES;
  const lifecycle = opts?.lifecycleStatus ?? "active";
  const limit = Math.min(Math.max(Math.trunc(opts?.limit ?? DEFAULT_THEOREM_LIMIT), 1), MAX_THEOREM_LIMIT);
  try {
    const { results } = await env.LEDGER.prepare(
      `SELECT id, facet, theorem_name, module, revision, status, lifecycle_status, used_in_hypotheses, created_at
         FROM atlas_theorems
        WHERE facet = ?
          AND status IN (${statuses.map(() => "?").join(",")})
          AND lifecycle_status = ?
        ORDER BY created_at DESC
        LIMIT ?`,
    )
      .bind(canonical, ...statuses, lifecycle, limit)
      .all<AtlasTheoremRef>();
    return { facet: canonical, rows: results ?? [], error: null };
  } catch (e) {
    return { facet: canonical, rows: [], error: e instanceof Error ? e.message : String(e) };
  }
}

/** Project a stored theorem reference into the compact RPC/state shape. */
export function toFormalBasis(ref: AtlasTheoremRef, helper?: string): FormalBasis {
  return {
    theorem: ref.theorem_name,
    module: ref.module,
    revision: ref.revision,
    status: ref.status,
    ...(helper ? { helper } : {}),
  };
}

/**
 * Project loaded theorem rows into a `formal_basis[]` payload, dropping every
 * row that is not allowed to ground an agent ({@link isGroundableRef}). This
 * is the JS-layer guarantee that `failed` / `imported` / unapproved-`extended`
 * rows never reach a dispatch payload even when the caller loaded rows with a
 * wider status filter. Pure + immutable.
 *
 * `theoremNames` scopes the basis to the theorems actually relied on
 * (recommended — keeps payloads minimal); `helpers` maps a theorem name to its
 * grounding note; `maxRefs` bounds the payload (default 64, hard cap 256).
 */
export function groundableFormalBasis(
  rows: ReadonlyArray<AtlasTheoremRef>,
  opts?: {
    theoremNames?: ReadonlyArray<string>;
    helpers?: Readonly<Record<string, string>>;
    maxRefs?: number;
  },
): FormalBasis[] {
  const wanted = opts?.theoremNames ? new Set(opts.theoremNames) : null;
  const helpers = opts?.helpers ?? {};
  const maxRefs = Math.min(Math.max(Math.trunc(opts?.maxRefs ?? 64), 1), 256);
  return rows
    .filter(isGroundableRef)
    .filter((t) => (wanted ? wanted.has(t.theorem_name) : true))
    .slice(0, maxRefs)
    .map((t) => toFormalBasis(t, helpers[t.theorem_name]));
}

/**
 * Summarize a facet's theorem references into a bounded inventory document.
 *
 * Pure + immutable: builds a fresh summary from the input rows. `maxRefs` caps
 * the embedded reference list so the JSON stored in `atlas_facet_state` and the
 * telemetry summary stays small regardless of how many theorems a facet imports.
 */
export function summarizeInventory(
  facet: string,
  refs: ReadonlyArray<AtlasTheoremRef>,
  maxRefs = 64,
): TheoremInventory {
  const by_status: Record<AtlasTheoremStatus, number> = { ...EMPTY_BY_STATUS };
  for (const r of refs) {
    if (r.status in by_status) by_status[r.status] += 1;
  }
  return {
    facet,
    total: refs.length,
    by_status,
    theorems: refs.slice(0, maxRefs).map((r) => toFormalBasis(r)),
  };
}

/** Per-facet ATLAS reference state row (§8.4). */
export interface AtlasFacetState {
  readonly facet: string;
  readonly atlas_revision: string | null;
  readonly mathlib_revision: string | null;
  /** Parsed `theorem_inventory` JSON, when present and well-formed. */
  readonly theorem_inventory: TheoremInventory | null;
  readonly updated_at: string;
}

/**
 * Load the per-facet ATLAS reference state, if any. Returns null (never throws)
 * when the table/row is absent or the inventory JSON is malformed.
 */
export async function loadFacetState(env: Env, facet: string): Promise<AtlasFacetState | null> {
  try {
    const row = await env.LEDGER.prepare(
      `SELECT facet, atlas_revision, mathlib_revision, theorem_inventory, updated_at
         FROM atlas_facet_state WHERE facet = ?`,
    )
      .bind(facet)
      .first<{
        facet: string;
        atlas_revision: string | null;
        mathlib_revision: string | null;
        theorem_inventory: string | null;
        updated_at: string;
      }>();
    if (!row) return null;
    let inventory: TheoremInventory | null = null;
    if (row.theorem_inventory) {
      try {
        inventory = JSON.parse(row.theorem_inventory) as TheoremInventory;
      } catch {
        inventory = null;
      }
    }
    return {
      facet: row.facet,
      atlas_revision: row.atlas_revision,
      mathlib_revision: row.mathlib_revision,
      theorem_inventory: inventory,
      updated_at: row.updated_at,
    };
  } catch {
    return null;
  }
}
