import { describe, expect, it } from "vitest";
import {
  canonicalRecurringClaimId,
  listRecurringCurrentClaims,
  upsertRecurringClaim,
} from "../recurringClaims";

interface StoredClaim {
  claim_id: string;
  agent_id: string;
  claim_type: string;
  claim_data: string;
  evidence_ids: string;
  confidence: number;
  status: string;
  description: string;
  created_at: string;
  timestamp: string;
}

class MemoryClaimsLedger {
  readonly claims = new Map<string, StoredClaim>();

  seed(claim: StoredClaim): void {
    this.claims.set(claim.claim_id, structuredClone(claim));
  }

  prepare(sql: string): D1PreparedStatement {
    let bindings: unknown[] = [];
    const statement = {
      bind: (...values: unknown[]) => {
        bindings = values;
        return statement;
      },
      run: async () => {
        if (!sql.includes("INSERT INTO claims")) throw new Error(`Unexpected run SQL: ${sql}`);
        const [
          claimId,
          agentId,
          claimType,
          claimData,
          evidenceIds,
          confidence,
          description,
          recomputedAt,
        ] = bindings as [string, string, string, string, string, number, string, string];
        const existing = this.claims.get(claimId);
        if (existing) {
          Object.assign(existing, {
            agent_id: agentId,
            claim_type: claimType,
            claim_data: claimData,
            evidence_ids: evidenceIds,
            confidence,
            description,
            timestamp: recomputedAt,
          });
        } else {
          this.claims.set(claimId, {
            claim_id: claimId,
            agent_id: agentId,
            claim_type: claimType,
            claim_data: claimData,
            evidence_ids: evidenceIds,
            confidence,
            status: "proposed",
            description,
            created_at: recomputedAt,
            timestamp: recomputedAt,
          });
        }
        return { success: true };
      },
      all: async <T>() => {
        if (!sql.includes("current_state.canonical")) throw new Error(`Unexpected all SQL: ${sql}`);
        const limit = Number(bindings.at(-1));
        const rows = [...this.claims.values()]
          .filter((claim) => {
            const data = JSON.parse(claim.claim_data) as { current_state?: { canonical?: boolean } };
            return claim.claim_id.startsWith("current:") && data.current_state?.canonical === true;
          })
          .sort((a, b) => b.timestamp.localeCompare(a.timestamp))
          .slice(0, limit)
          .map((claim) => {
            const data = JSON.parse(claim.claim_data) as {
              current_state: {
                recurring_key: string;
                evidence_record_timestamp: string | null;
              };
            };
            return {
              ...claim,
              recurring_key: data.current_state.recurring_key,
              evidence_record_timestamp: data.current_state.evidence_record_timestamp,
              recomputed_at: claim.timestamp,
            };
          });
        return { results: rows as T[] };
      },
    };
    return statement as unknown as D1PreparedStatement;
  }
}

function writeManifold(
  ledger: MemoryClaimsLedger,
  args: {
    element: string;
    family: string;
    pr: number;
    evidenceRecordTimestamp: string;
    recomputedAt: string;
  },
) {
  return upsertRecurringClaim(ledger, {
    agentId: "agent_alpha_manifold",
    claimType: "ManifoldAnalysis",
    dimensions: { element: args.element, family: args.family },
    claimData: { pr: args.pr },
    evidenceIds: [`record:${args.element}:${args.pr}`],
    confidence: 0.85,
    description: `${args.element}/${args.family} PR=${args.pr}`,
    evidenceRecordTimestamp: args.evidenceRecordTimestamp,
    recomputedAt: args.recomputedAt,
  });
}

describe("recurring claim current state", () => {
  it("keeps row cardinality stable while refreshing data and timestamps", async () => {
    const ledger = new MemoryClaimsLedger();
    const firstId = await writeManifold(ledger, {
      element: "Al",
      family: "all",
      pr: 1.2,
      evidenceRecordTimestamp: "2026-07-15T10:00:00.000Z",
      recomputedAt: "2026-07-15T11:00:00.000Z",
    });
    const firstCreatedAt = ledger.claims.get(firstId)?.created_at;
    ledger.claims.get(firstId)!.status = "confirmed";

    const secondId = await writeManifold(ledger, {
      element: "Al",
      family: "all",
      pr: 1.4,
      evidenceRecordTimestamp: "2026-07-15T11:30:00.000Z",
      recomputedAt: "2026-07-15T12:00:00.000Z",
    });

    expect(secondId).toBe(firstId);
    expect(ledger.claims.size).toBe(1);
    const current = ledger.claims.get(firstId)!;
    const data = JSON.parse(current.claim_data) as {
      pr: number;
      current_state: { evidence_record_timestamp: string; recomputed_at: string };
    };
    expect(data.pr).toBe(1.4);
    expect(data.current_state.evidence_record_timestamp).toBe("2026-07-15T11:30:00.000Z");
    expect(data.current_state.recomputed_at).toBe("2026-07-15T12:00:00.000Z");
    expect(current.created_at).toBe(firstCreatedAt);
    expect(current.timestamp).toBe("2026-07-15T12:00:00.000Z");
    expect(current.evidence_ids).toBe(JSON.stringify(["record:Al:1.4"]));
    expect(current.status).toBe("confirmed");
  });

  it("keeps the complete 21-claim hourly set stable across cycles", async () => {
    const ledger = new MemoryClaimsLedger();
    const elements = ["Al", "Cu", "Ni", "Ag", "Au", "Pt", "Pd", "Pb", "Fe", "Cr", "Mo", "W", "V", "Nb", "Ta"];
    const globalTypes = [
      "DataPurge",
      "CorpusAudit",
      "MultiPropertySeed",
      "StructurePropertyScreen",
      "ScaleFreeStructureScreen",
      "DataIntegrityScreen",
    ] as const;

    for (const recomputedAt of ["2026-07-15T11:00:00.000Z", "2026-07-15T12:00:00.000Z"]) {
      await Promise.all([
        ...elements.map((element, index) => writeManifold(ledger, {
          element,
          family: "all",
          pr: 1 + index / 100,
          evidenceRecordTimestamp: "2026-07-15T10:00:00.000Z",
          recomputedAt,
        })),
        ...globalTypes.map((claimType) => upsertRecurringClaim(ledger, {
          agentId: "agent_delta_causal",
          claimType,
          claimData: { cycle: recomputedAt },
          evidenceIds: [],
          confidence: 0.8,
          description: `${claimType} current state`,
          evidenceRecordTimestamp: "2026-07-15T10:00:00.000Z",
          recomputedAt,
        })),
      ]);
      expect(ledger.claims.size).toBe(21);
    }

    expect([...ledger.claims.values()].every((claim) => claim.timestamp === "2026-07-15T12:00:00.000Z")).toBe(true);
  });

  it("uses distinct canonical IDs for manifold element and family keys", async () => {
    const ledger = new MemoryClaimsLedger();
    const common = {
      pr: 1.1,
      evidenceRecordTimestamp: "2026-07-15T10:00:00.000Z",
      recomputedAt: "2026-07-15T11:00:00.000Z",
    };

    const ids = await Promise.all([
      writeManifold(ledger, { ...common, element: "Al", family: "all" }),
      writeManifold(ledger, { ...common, element: "Cu", family: "all" }),
      writeManifold(ledger, { ...common, element: "Al", family: "eam/alloy" }),
    ]);

    expect(new Set(ids).size).toBe(3);
    expect(ledger.claims.size).toBe(3);
    expect(ids[0]).toBe("current:ManifoldAnalysis:element=Al:family=all");
    expect(ids[2]).toBe("current:ManifoldAnalysis:element=Al:family=eam%2Falloy");
    expect(canonicalRecurringClaimId("ManifoldAnalysis", { family: "all", element: "Al" })).toBe(ids[0]);
  });

  it("preserves one-off history and excludes it from current-state reads", async () => {
    const ledger = new MemoryClaimsLedger();
    const reviewed: StoredClaim = {
      claim_id: "manifold_Al_all_1752570000000",
      agent_id: "agent_alpha_manifold",
      claim_type: "ManifoldAnalysis",
      claim_data: JSON.stringify({ pr: 1.05, reviewer_note: "accepted historical result" }),
      evidence_ids: "[]",
      confidence: 0.9,
      status: "confirmed",
      description: "Reviewed one-off manifold claim",
      created_at: "2026-07-14T10:00:00.000Z",
      timestamp: "2026-07-14T10:00:00.000Z",
    };
    ledger.seed(reviewed);

    await writeManifold(ledger, {
      element: "Al",
      family: "all",
      pr: 1.3,
      evidenceRecordTimestamp: "2026-07-15T10:00:00.000Z",
      recomputedAt: "2026-07-15T11:00:00.000Z",
    });
    const current = await listRecurringCurrentClaims(ledger, { limit: 50 });

    expect(ledger.claims.size).toBe(2);
    expect(ledger.claims.get(reviewed.claim_id)).toEqual(reviewed);
    expect(current).toHaveLength(1);
    expect(current[0]).toMatchObject({
      claim_id: "current:ManifoldAnalysis:element=Al:family=all",
      recurring_key: "element=Al|family=all",
      evidence_record_timestamp: "2026-07-15T10:00:00.000Z",
      recomputed_at: "2026-07-15T11:00:00.000Z",
      status: "proposed",
    });
  });
});
