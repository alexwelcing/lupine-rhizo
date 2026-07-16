import type { ClaimRecord } from "../types";

export type RecurringClaimType =
  | "ManifoldAnalysis"
  | "DataPurge"
  | "CorpusAudit"
  | "MultiPropertySeed"
  | "StructurePropertyScreen"
  | "ScaleFreeStructureScreen"
  | "DataIntegrityScreen";

export interface RecurringClaimInput {
  agentId: string;
  claimType: RecurringClaimType;
  dimensions?: Readonly<Record<string, string>>;
  claimData: Readonly<Record<string, unknown>>;
  evidenceIds: readonly string[];
  confidence: number;
  description: string;
  evidenceRecordTimestamp: string | null;
  recomputedAt?: string;
}

export interface CurrentClaimRecord extends ClaimRecord {
  recurring_key: string;
  evidence_record_timestamp: string | null;
  recomputed_at: string;
}

export interface CurrentClaimFilters {
  status?: string | null;
  claimType?: string | null;
  agentId?: string | null;
  limit?: number;
}

function sortedDimensions(dimensions: Readonly<Record<string, string>> = {}): Array<[string, string]> {
  return Object.entries(dimensions).sort(([left], [right]) => left.localeCompare(right));
}

function recurringKey(dimensions: Readonly<Record<string, string>> = {}): string {
  const entries = sortedDimensions(dimensions);
  return entries.length > 0
    ? entries.map(([name, value]) => `${name}=${value}`).join("|")
    : "global";
}

export function canonicalRecurringClaimId(
  claimType: RecurringClaimType,
  dimensions: Readonly<Record<string, string>> = {},
): string {
  const entries = sortedDimensions(dimensions);
  const key = entries.length > 0
    ? entries.map(([name, value]) => `${encodeURIComponent(name)}=${encodeURIComponent(value)}`).join(":")
    : "global";
  return `current:${encodeURIComponent(claimType)}:${key}`;
}

export function latestEvidenceRecordTimestamp(
  timestamps: Iterable<string | null | undefined>,
): string | null {
  let latest: string | null = null;
  for (const timestamp of timestamps) {
    if (typeof timestamp === "string" && timestamp.length > 0 && (latest === null || timestamp > latest)) {
      latest = timestamp;
    }
  }
  return latest;
}

export async function upsertRecurringClaim(
  ledger: Pick<D1Database, "prepare">,
  input: RecurringClaimInput,
): Promise<string> {
  const recomputedAt = input.recomputedAt ?? new Date().toISOString();
  const dimensions = Object.fromEntries(sortedDimensions(input.dimensions));
  const claimId = canonicalRecurringClaimId(input.claimType, dimensions);
  const claimData = {
    ...input.claimData,
    current_state: {
      canonical: true,
      recurring_key: recurringKey(dimensions),
      dimensions,
      evidence_record_timestamp: input.evidenceRecordTimestamp,
      recomputed_at: recomputedAt,
      supersession: {
        mode: "canonical_upsert",
        scope: "same_claim_type_and_recurring_key",
        supersedes_legacy_append_only_rows: true,
        legacy_rows_preserved: true,
      },
    },
  };

  await ledger.prepare(
    `INSERT INTO claims
       (claim_id, agent_id, claim_type, claim_data, evidence_ids, confidence, status, description, created_at, timestamp)
     VALUES (?1, ?2, ?3, ?4, ?5, ?6, 'proposed', ?7, ?8, ?8)
     ON CONFLICT(claim_id) DO UPDATE SET
       agent_id = excluded.agent_id,
       claim_type = excluded.claim_type,
       claim_data = excluded.claim_data,
       evidence_ids = excluded.evidence_ids,
       confidence = excluded.confidence,
       description = excluded.description,
       timestamp = excluded.timestamp`,
  ).bind(
    claimId,
    input.agentId,
    input.claimType,
    JSON.stringify(claimData),
    JSON.stringify(input.evidenceIds),
    input.confidence,
    input.description,
    recomputedAt,
  ).run();

  return claimId;
}

export async function listRecurringCurrentClaims(
  ledger: Pick<D1Database, "prepare">,
  filters: CurrentClaimFilters = {},
): Promise<CurrentClaimRecord[]> {
  const where = [
    `claim_id LIKE 'current:%'`,
    `json_extract(claim_data, '$.current_state.canonical') = 1`,
  ];
  const bindings: unknown[] = [];
  if (filters.status) {
    bindings.push(filters.status);
    where.push(`status = ?${bindings.length}`);
  }
  if (filters.claimType) {
    bindings.push(filters.claimType);
    where.push(`claim_type = ?${bindings.length}`);
  }
  if (filters.agentId) {
    bindings.push(filters.agentId);
    where.push(`agent_id = ?${bindings.length}`);
  }
  const limit = Math.min(Math.max(filters.limit ?? 50, 1), 500);
  bindings.push(limit);

  const rows = await ledger.prepare(
    `SELECT claim_id, agent_id, claim_type, claim_data, evidence_ids, confidence, status,
            description, created_at,
            json_extract(claim_data, '$.current_state.recurring_key') AS recurring_key,
            json_extract(claim_data, '$.current_state.evidence_record_timestamp') AS evidence_record_timestamp,
            timestamp AS recomputed_at
       FROM claims
      WHERE ${where.join(" AND ")}
      ORDER BY timestamp DESC
      LIMIT ?${bindings.length}`,
  ).bind(...bindings).all<CurrentClaimRecord>();

  return rows.results;
}
