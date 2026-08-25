import { describe, expect, it } from "vitest";
import {
  Z1_CAMPAIGN_MANIFEST_URL,
  translateLupineCampaignDispatch,
} from "../lupineCampaignDispatch";

function canonicalJson(value: unknown): string {
  if (Array.isArray(value)) return `[${value.map(canonicalJson).join(",")}]`;
  if (value && typeof value === "object") {
    const entries = Object.entries(value as Record<string, unknown>)
      .sort(([left], [right]) => left.localeCompare(right));
    return `{${entries.map(([key, item]) => `${JSON.stringify(key)}:${canonicalJson(item)}`).join(",")}}`;
  }
  return JSON.stringify(value);
}

async function sha256(value: string): Promise<string> {
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(value));
  return "sha256:" + Array.from(
    new Uint8Array(digest),
    (byte) => byte.toString(16).padStart(2, "0"),
  ).join("");
}

const FIXED_NOW = Date.parse("2026-08-25T12:02:00.000Z");
const CAMPAIGN_ID = "screening.user.dcafaef77757232c.1.v1";

async function dispatch(overrides: Record<string, unknown> = {}) {
  const body = {
    schema: "lupine.campaign_dispatch.v1",
    campaign_id: CAMPAIGN_ID,
    owner_uid: "uid-abc",
    panel: {
      panel_id: "z1-nebdft2k-chemistry-held-out-v1",
      content_hash: "sha256:192fe54a5579cc421f6644d5d76fb442c6dfb985f014dc4741549e29052efb68",
    },
    models: ["chgnet"],
    anchor_policy: "union-sparse",
    acceptance_test: { metric: "barrier_mae", operator: "lte", threshold: 40, unit: "meV" },
    created_at: "2026-08-25T12:00:00.000Z",
    ...overrides,
  };
  const contentHash = await sha256(canonicalJson(body));
  return { ...body, content_hash: contentHash };
}

describe("lupine-app campaign dispatch adapter", () => {
  it("maps the locked Z1 panel to one barrier cell and requests immediate enqueue", async () => {
    const translated = await translateLupineCampaignDispatch(await dispatch(), FIXED_NOW);

    expect(translated.create).toMatchObject({
      campaign_id: CAMPAIGN_ID,
      hypothesis_id: "h.z1.barrier-accuracy",
      workflow_profile: "z1_barrier",
      rows: [{ id: "barrier", label: "Migration barrier MAE" }],
      mlips: [{ id: "chgnet", label: "CHGNet" }],
      variant_scope: "baseline",
      fixture_url_template: Z1_CAMPAIGN_MANIFEST_URL,
    });
    expect(translated.enqueue).toEqual({ limit: 1 });
  });

  it("accepts the fixed canonical dispatch hash vector", async () => {
    const vector = {
      schema: "lupine.campaign_dispatch.v1",
      campaign_id: CAMPAIGN_ID,
      owner_uid: "uid-abc",
      panel: {
        panel_id: "z1-nebdft2k-chemistry-held-out-v1",
        content_hash: "sha256:192fe54a5579cc421f6644d5d76fb442c6dfb985f014dc4741549e29052efb68",
      },
      models: ["chgnet"],
      anchor_policy: "union-sparse",
      acceptance_test: { metric: "barrier_mae", operator: "lte", threshold: 40, unit: "meV" },
      created_at: "2026-08-25T12:00:00.000Z",
      content_hash: "sha256:de9c4997e43a72ea765eeaa0c962b08ef9a144c12afe50bd4957664e670ff34d",
    };

    await expect(translateLupineCampaignDispatch(vector, FIXED_NOW)).resolves.toMatchObject({
      create: { campaign_id: CAMPAIGN_ID },
    });
  });

  it.each([
    ["chgnet", "CHGNet"],
    ["mace-mp-small", "MACE-MP small"],
    ["mace-mp-medium", "MACE-MP medium"],
    ["mace-mpa-0-medium", "MACE-MPA-0 medium"],
  ])("maps reviewed model %s to runner label %s", async (id, label) => {
    const translated = await translateLupineCampaignDispatch(await dispatch({ models: [id] }), FIXED_NOW);
    expect(translated.create.mlips).toEqual([{ id, label }]);
  });

  it("fails closed on unreviewed panel locks and models", async () => {
    await expect(translateLupineCampaignDispatch(await dispatch({
      panel: { panel_id: "uploaded", content_hash: "sha256:" + "1".repeat(64) },
    }), FIXED_NOW)).rejects.toThrow(/reviewed Z1 panel/);

    await expect(translateLupineCampaignDispatch(await dispatch({ models: ["orb-v3"] }), FIXED_NOW))
      .rejects.toThrow(/not registered in the reviewed Z1 campaign/);
  });

  it("rejects unknown top-level and nested keys", async () => {
    await expect(translateLupineCampaignDispatch(await dispatch({ unexpected: true }), FIXED_NOW))
      .rejects.toThrow(/unexpected key/);
    await expect(translateLupineCampaignDispatch(await dispatch({
      panel: {
        panel_id: "z1-nebdft2k-chemistry-held-out-v1",
        content_hash: "sha256:192fe54a5579cc421f6644d5d76fb442c6dfb985f014dc4741549e29052efb68",
        unexpected: true,
      },
    }), FIXED_NOW)).rejects.toThrow(/panel.*unexpected key/);
    await expect(translateLupineCampaignDispatch(await dispatch({
      acceptance_test: {
        metric: "barrier_mae",
        operator: "lte",
        threshold: 40,
        unit: "meV",
        unexpected: true,
      },
    }), FIXED_NOW)).rejects.toThrow(/acceptance_test.*unexpected key/);
  });

  it("requires canonical ISO created_at within five minutes of receipt", async () => {
    await expect(translateLupineCampaignDispatch(await dispatch({
      created_at: "2026-08-25 12:00:00Z",
    }), FIXED_NOW)).rejects.toThrow(/canonical ISO/);
    await expect(translateLupineCampaignDispatch(await dispatch({
      created_at: "2026-08-25T11:56:59.999Z",
    }), FIXED_NOW)).rejects.toThrow(/fresh/);
    await expect(translateLupineCampaignDispatch(await dispatch({
      created_at: "2026-08-25T12:07:00.001Z",
    }), FIXED_NOW)).rejects.toThrow(/fresh/);
  });

  it("binds the campaign id owner key to SHA-256(owner_uid)", async () => {
    await expect(translateLupineCampaignDispatch(await dispatch({
      campaign_id: "screening.user.0000000000000000.1.v1",
    }), FIXED_NOW)).rejects.toThrow(/owner key/);
    await expect(translateLupineCampaignDispatch(await dispatch({
      campaign_id: "screening.user.dcafaef77757232c.not-a-timestamp.v1",
    }), FIXED_NOW)).rejects.toThrow(/campaign_id format/);
  });

  it("rejects a digest mismatch before campaign creation", async () => {
    await expect(translateLupineCampaignDispatch({
      ...await dispatch(),
      content_hash: "sha256:" + "0".repeat(64),
    }, FIXED_NOW)).rejects.toThrow(/content_hash mismatch/);
  });
});
