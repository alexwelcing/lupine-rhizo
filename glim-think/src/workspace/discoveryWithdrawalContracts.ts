import { canonicalPublicJson } from "./discoveryPublicationContracts";
import { publicActivitySha256 } from "./researchActivityContracts";

export const DISCOVERY_WITHDRAWAL_MAX_BYTES = 2048;
export interface DiscoveryWithdrawal {
  schema: "lupine.discovery_source_withdrawal.v1"; producer: "lupine-research-team-v02";
  id: string; publicationId: string; recordSha256: string; evidenceSha256: string;
  sourceSemanticSha256: string; observedAt: string;
}
export interface DiscoveryWithdrawalAck {
  schema: "lupine.discovery_source_withdrawal_ack.v1"; id: string;
  payloadSha256: string; duplicate: boolean; knowledgeProjected: true;
}
export async function decodeDiscoveryWithdrawal(input: unknown, now = Date.now()): Promise<DiscoveryWithdrawal> {
  const keys = ["schema", "producer", "id", "publicationId", "recordSha256", "evidenceSha256", "sourceSemanticSha256", "observedAt"];
  if (!input || typeof input !== "object" || Object.getPrototypeOf(input) !== Object.prototype
    || Reflect.ownKeys(input).length !== keys.length) throw Error("Invalid source availability notice");
  const data: Record<string, string> = {};
  for (const key of keys) {
    const descriptor = Object.getOwnPropertyDescriptor(input, key);
    if (!descriptor || !("value" in descriptor) || typeof descriptor.value !== "string") throw Error("Invalid source availability notice");
    data[key] = descriptor.value;
  }
  if (data.schema !== "lupine.discovery_source_withdrawal.v1" || data.producer !== "lupine-research-team-v02"
    || !/^withdrawal-[a-f0-9]{64}$/.test(data.id) || !/^discovery-[a-f0-9]{64}$/.test(data.publicationId)
    || [data.recordSha256, data.evidenceSha256, data.sourceSemanticSha256].some(value => !/^[a-f0-9]{64}$/.test(value))
    || !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/.test(data.observedAt)
    || !Number.isFinite(Date.parse(data.observedAt)) || new Date(data.observedAt).toISOString() !== data.observedAt
    || Date.parse(data.observedAt) > now + 60000 || new TextEncoder().encode(canonicalPublicJson(data)).length > DISCOVERY_WITHDRAWAL_MAX_BYTES)
    throw Error("Invalid source availability notice");
  const { id, ...core } = data;
  if (id !== "withdrawal-" + await publicActivitySha256(canonicalPublicJson(core))) throw Error("Source availability identity differs");
  return data as unknown as DiscoveryWithdrawal;
}
