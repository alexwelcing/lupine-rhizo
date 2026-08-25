import { describe, expect, it } from "vitest";
import { handleResearchWorkflowRoute } from "../workflows";
import { buildStubEnv, stubLedger, stubQueue } from "../../testing/envStub";

function canonicalJson(value: unknown): string {
  if (Array.isArray(value)) return `[${value.map(canonicalJson).join(",")}]`;
  if (value && typeof value === "object") {
    return `{${Object.entries(value as Record<string, unknown>)
      .sort(([left], [right]) => left.localeCompare(right))
      .map(([key, item]) => `${JSON.stringify(key)}:${canonicalJson(item)}`)
      .join(",")}}`;
  }
  return JSON.stringify(value);
}

const CAMPAIGN_ID = "screening.user.dcafaef77757232c.1.v1";

async function requestBody(): Promise<string> {
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
    created_at: new Date().toISOString(),
  };
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(canonicalJson(body)));
  const content_hash = "sha256:" + Array.from(
    new Uint8Array(digest),
    (byte) => byte.toString(16).padStart(2, "0"),
  ).join("");
  return JSON.stringify({ ...body, content_hash });
}

describe("lupine-app campaign route", () => {
  it("creates the locked campaign and enqueues its selected cells in one POST", async () => {
    const queue = stubQueue();
    const campaignId = CAMPAIGN_ID;
    const fixtureUrl = "https://raw.githubusercontent.com/alexwelcing/lupine-rhizo/efb8237f55940312ce0ad848a5e5cd9b4bdc9b0c/campaigns/v1/z1.campaign-manifest.v1.json";
    const env = buildStubEnv({
      LUPINE_APP_TOKEN: "app-secret",
      RESEARCH_QUEUE: queue,
      LEDGER: stubLedger({
        queries: [
          {
            match: "FROM mlip_campaigns",
            first: {
              campaign_id: campaignId,
              hypothesis_id: "h.z1.barrier-accuracy",
              title: "Z1 migration barrier campaign",
              status: "draft",
              rows_json: JSON.stringify([{ id: "barrier", label: "Migration barrier MAE" }]),
              mlips_json: JSON.stringify([{ id: "chgnet", label: "CHGNet" }]),
              variants_json: JSON.stringify([{ id: "baseline", label: "Baseline MLIP", strategy: "baseline" }]),
              fixture_url_template: fixtureUrl,
              model_pairs_json: "[]",
              top_k: 1,
              quality_gate: "accuracy",
              created_at: "now",
              updated_at: "now",
            },
          },
          {
            match: "FROM mlip_campaign_cells",
            all: [{
              cell_id: `${campaignId}:baseline:barrier:chgnet`,
              campaign_id: campaignId,
              row_id: "barrier",
              mlip_id: "chgnet",
              variant_id: "baseline",
              fixture_url: fixtureUrl,
              status: "queued",
              job_id: null,
              accuracy_score: null,
              accuracy_unit: null,
              speed_score: null,
              speed_unit: null,
              metrics_json: null,
              created_at: "now",
              updated_at: "now",
            }],
          },
          { match: "FROM mlip_campaign_triplet_evals", all: [] },
        ],
      }),
    });

    const response = await handleResearchWorkflowRoute(
      env,
      new URL("https://worker.test/research/workflows/mlip-5x5x3/campaigns"),
      "POST",
      await requestBody(),
      { authorization: "Bearer app-secret" },
    );
    const body = await response?.json() as {
      accepted: boolean;
      campaign_id: string;
      dispatched: Array<{ mlip_id: string }>;
    };

    expect(response?.status).toBe(200);
    expect(body).toMatchObject({ accepted: true, campaign_id: campaignId });
    expect(body.dispatched).toHaveLength(1);
    expect(queue.sent).toHaveLength(1);
    expect(queue.sent[0]).toMatchObject({
      kind: "mlip_cell_run",
      row_id: "barrier",
      mlip_id: "chgnet",
      variant_id: "baseline",
      manifest_url: fixtureUrl,
    });
  });

  it("binds the dedicated app credential to the exact dispatch contract", async () => {
    const dispatchWithoutCredential = await handleResearchWorkflowRoute(
      buildStubEnv({ LUPINE_APP_TOKEN: "app-secret" }),
      new URL("https://worker.test/research/workflows/mlip-5x5x3/campaigns"),
      "POST",
      await requestBody(),
    );
    expect(dispatchWithoutCredential?.status).toBe(403);

    const ordinaryBodyWithCredential = await handleResearchWorkflowRoute(
      buildStubEnv({ LUPINE_APP_TOKEN: "app-secret" }),
      new URL("https://worker.test/research/workflows/mlip-5x5x3/campaigns"),
      "POST",
      JSON.stringify({ hypothesis_id: "not-a-lupine-dispatch" }),
      { authorization: "Bearer app-secret" },
    );
    expect(ordinaryBodyWithCredential?.status).toBe(403);
  });
});
