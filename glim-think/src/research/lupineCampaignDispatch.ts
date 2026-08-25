import type { CreateMlipCampaignInput } from "./mlipCampaign";

export const Z1_PANEL_ID = "z1-nebdft2k-chemistry-held-out-v1";
export const Z1_PANEL_CONTENT_HASH =
  "sha256:192fe54a5579cc421f6644d5d76fb442c6dfb985f014dc4741549e29052efb68";
export const Z1_CAMPAIGN_MANIFEST_URL =
  "https://raw.githubusercontent.com/alexwelcing/lupine-rhizo/efb8237f55940312ce0ad848a5e5cd9b4bdc9b0c/campaigns/v1/z1.campaign-manifest.v1.json";

const Z1_MODELS = new Map([
  ["chgnet", "CHGNet"],
  ["mace-mp-small", "MACE-MP small"],
  ["mace-mp-medium", "MACE-MP medium"],
  ["mace-mpa-0-medium", "MACE-MPA-0 medium"],
]);

interface LupineCampaignDispatch {
  schema: "lupine.campaign_dispatch.v1";
  campaign_id: string;
  owner_uid: string;
  panel: { panel_id: string; content_hash: string };
  models: string[];
  anchor_policy: "union-sparse";
  acceptance_test: {
    metric: "barrier_mae";
    operator: "lte";
    threshold: 40;
    unit: "meV";
  };
  created_at: string;
  content_hash: string;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function canonicalJson(value: unknown): string {
  if (Array.isArray(value)) return `[${value.map(canonicalJson).join(",")}]`;
  if (isRecord(value)) {
    return `{${Object.keys(value).sort().map((key) =>
      `${JSON.stringify(key)}:${canonicalJson(value[key])}`).join(",")}}`;
  }
  const encoded = JSON.stringify(value);
  if (encoded === undefined) throw new Error("campaign dispatch contains a non-JSON value");
  return encoded;
}

async function sha256(value: string): Promise<string> {
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(value));
  return "sha256:" + Array.from(
    new Uint8Array(digest),
    (byte) => byte.toString(16).padStart(2, "0"),
  ).join("");
}

function expectString(record: Record<string, unknown>, key: string): string {
  const value = record[key];
  if (typeof value !== "string" || !value.trim()) throw new Error(`${key} is required`);
  return value;
}

const DISPATCH_KEYS = [
  "schema",
  "campaign_id",
  "owner_uid",
  "panel",
  "models",
  "anchor_policy",
  "acceptance_test",
  "created_at",
  "content_hash",
] as const;
const PANEL_KEYS = ["panel_id", "content_hash"] as const;
const ACCEPTANCE_KEYS = ["metric", "operator", "threshold", "unit"] as const;
const DISPATCH_FRESHNESS_MS = 5 * 60 * 1000;

function assertExactKeys(
  record: Record<string, unknown>,
  allowed: readonly string[],
  label: string,
): void {
  const allowedKeys = new Set(allowed);
  const unexpected = Object.keys(record).filter((key) => !allowedKeys.has(key));
  if (unexpected.length) throw new Error(`${label} contains unexpected key ${unexpected[0]}`);
}

async function parseDispatch(
  value: unknown,
  receivedAtMs: number,
): Promise<LupineCampaignDispatch> {
  if (!isRecord(value) || value.schema !== "lupine.campaign_dispatch.v1") {
    throw new Error("schema must be lupine.campaign_dispatch.v1");
  }
  assertExactKeys(value, DISPATCH_KEYS, "campaign dispatch");

  const campaignId = expectString(value, "campaign_id");
  const campaignMatch = campaignId.match(/^screening\.user\.([a-f0-9]{16})\.(\d+)\.v1$/);
  if (!campaignMatch) {
    throw new Error("campaign_id format must be screening.user.<ownerkey>.<timestamp>.v1");
  }
  const ownerUid = expectString(value, "owner_uid");
  const expectedOwnerKey = (await sha256(ownerUid)).slice("sha256:".length, "sha256:".length + 16);
  if (campaignMatch[1] !== expectedOwnerKey) {
    throw new Error("campaign_id owner key does not match SHA-256(owner_uid)");
  }

  const createdAt = expectString(value, "created_at");
  if (!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/.test(createdAt)) {
    throw new Error("created_at must be a canonical ISO date-time");
  }
  const createdAtMs = Date.parse(createdAt);
  if (!Number.isFinite(createdAtMs) || Math.abs(receivedAtMs - createdAtMs) > DISPATCH_FRESHNESS_MS) {
    throw new Error("created_at must be fresh within five minutes of receipt");
  }
  const contentHash = expectString(value, "content_hash");
  if (!/^sha256:[a-f0-9]{64}$/.test(contentHash)) {
    throw new Error("content_hash must be a sha256:<64 lowercase hex> lock");
  }
  if (!isRecord(value.panel)) throw new Error("panel lock is required");
  assertExactKeys(value.panel, PANEL_KEYS, "panel");
  if (
    value.panel.panel_id !== Z1_PANEL_ID ||
    value.panel.content_hash !== Z1_PANEL_CONTENT_HASH
  ) {
    throw new Error("only the reviewed Z1 panel lock is dispatchable");
  }
  if (!Array.isArray(value.models) || value.models.length < 1) {
    throw new Error("models must contain at least one reviewed model id");
  }
  const models = value.models.map((model) => {
    if (typeof model !== "string" || !Z1_MODELS.has(model)) {
      throw new Error(`model ${String(model)} is not registered in the reviewed Z1 campaign`);
    }
    return model;
  });
  if (new Set(models).size !== models.length) throw new Error("models must not contain duplicates");
  if (value.anchor_policy !== "union-sparse") {
    throw new Error("anchor_policy must be the frozen union-sparse preset");
  }
  const acceptance = value.acceptance_test;
  if (!isRecord(acceptance)) {
    throw new Error("acceptance_test must be the reviewed barrier_mae <= 40 meV gate");
  }
  assertExactKeys(acceptance, ACCEPTANCE_KEYS, "acceptance_test");
  if (
    acceptance.metric !== "barrier_mae" ||
    acceptance.operator !== "lte" ||
    acceptance.threshold !== 40 ||
    acceptance.unit !== "meV"
  ) {
    throw new Error("acceptance_test must be the reviewed barrier_mae <= 40 meV gate");
  }
  return value as unknown as LupineCampaignDispatch;
}

export function isLupineCampaignDispatch(value: unknown): boolean {
  return isRecord(value) && value.schema === "lupine.campaign_dispatch.v1";
}

export async function translateLupineCampaignDispatch(
  value: unknown,
  receivedAtMs = Date.now(),
): Promise<{ create: CreateMlipCampaignInput; enqueue: { limit: number } }> {
  const dispatch = await parseDispatch(value, receivedAtMs);
  const { content_hash: presentedHash, ...unhashed } = dispatch;
  const actualHash = await sha256(canonicalJson(unhashed));
  if (actualHash !== presentedHash) {
    throw new Error(`campaign dispatch content_hash mismatch: expected ${presentedHash}, got ${actualHash}`);
  }

  return {
    create: {
      campaign_id: dispatch.campaign_id,
      hypothesis_id: "h.z1.barrier-accuracy",
      title: "Z1 migration barrier campaign",
      workflow_profile: "z1_barrier",
      rows: [{ id: "barrier", label: "Migration barrier MAE" }],
      mlips: dispatch.models.map((id) => ({ id, label: Z1_MODELS.get(id)! })),
      variant_scope: "baseline",
      fixture_url_template: Z1_CAMPAIGN_MANIFEST_URL,
      top_k: 1,
      quality_gate: "accuracy",
    },
    enqueue: { limit: dispatch.models.length },
  };
}
