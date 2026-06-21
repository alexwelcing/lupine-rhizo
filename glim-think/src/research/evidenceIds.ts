export function stableEvidencePart(value: string): string {
  return value.trim().replace(/[^A-Za-z0-9_.:-]/g, "-").slice(0, 180);
}

export function recordEvidenceId(recordId: string | null | undefined): string | null {
  const clean = recordId?.trim();
  if (!clean) return null;
  return clean.startsWith("record:") ? clean : `record:${clean}`;
}

export function compactEvidenceIds(
  ids: Array<string | null | undefined>,
  limit = 240,
  overflowLabel = "evidence-set",
): string[] {
  const unique = [...new Set(ids.map((id) => id?.trim()).filter((id): id is string => Boolean(id)))];
  if (unique.length <= limit) return unique;
  return [
    ...unique.slice(0, limit),
    `evidence-set:${stableEvidencePart(overflowLabel)}:total=${unique.length}`,
  ];
}

export function parseEvidenceIds(value: unknown): string[] {
  if (Array.isArray(value)) return compactEvidenceIds(value.map(String));
  if (typeof value !== "string" || !value.trim()) return [];
  try {
    const parsed = JSON.parse(value);
    return Array.isArray(parsed) ? compactEvidenceIds(parsed.map(String)) : [];
  } catch {
    return [];
  }
}

export function inferEvidenceIdsFromClaimData(value: unknown): string[] {
  const root = typeof value === "string" ? safeJson(value) : value;
  const ids = new Set<string>();
  const visit = (node: unknown, key?: string) => {
    if (node === null || node === undefined) return;
    if (typeof node === "string" || typeof node === "number") {
      const text = String(node).trim();
      if (!text) return;
      if (key === "record_id" || key === "recordId") {
        const record = recordEvidenceId(text);
        if (record) ids.add(record);
      } else if (key === "claim_id" || key === "source_claim" || key === "source_claim_id") {
        ids.add(text.startsWith("claim:") ? text : `claim:${text}`);
      } else if (key === "github_run_id") {
        ids.add(`github-actions:${text}`);
      } else if (key === "discovery_campaign_id" || key === "campaign_id" || key === "run_id") {
        ids.add(`campaign:${text}`);
      }
      return;
    }
    if (Array.isArray(node)) {
      for (const item of node) visit(item, key);
      return;
    }
    if (typeof node === "object") {
      for (const [childKey, childValue] of Object.entries(node as Record<string, unknown>)) {
        visit(childValue, childKey);
      }
    }
  };
  visit(root);
  return compactEvidenceIds([...ids]);
}

function safeJson(value: string): unknown {
  try {
    return JSON.parse(value);
  } catch {
    return null;
  }
}
