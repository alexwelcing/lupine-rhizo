import { afterAll, beforeAll, describe, expect, it } from "vitest";
// @ts-expect-error Node 24 provides node:sqlite; the Worker test tsconfig intentionally excludes Node types.
import { DatabaseSync } from "node:sqlite";
import { handleBeatsPost } from "../../feed/beats";
import { buildStubEnv } from "../../testing/envStub";
import type { Env } from "../../types";
import {
  ensureMlipBaselineSchema,
  recordMlipBaselineBeat,
  type MlipBaselineCellRecord,
  type MlipBaselineRunRecord,
} from "../mlipBaselineGrid";
import {
  ensureMlipCampaignSchema,
  recordMlipCampaignBeat,
  type MlipCampaignCell,
  type MlipCampaignRecord,
} from "../mlipCampaign";

function sqliteLedger(db: InstanceType<typeof DatabaseSync>): D1Database {
  function statement(sql: string, bindings: unknown[] = []): D1PreparedStatement {
    return {
      bind: (...values: unknown[]) => statement(sql, [...bindings, ...values]),
      first: async <T>() => (db.prepare(sql).get(...bindings) as T | undefined) ?? null,
      all: async <T>() => ({
        results: db.prepare(sql).all(...bindings) as T[],
        success: true,
        meta: {},
      }),
      run: async () => {
        const result = db.prepare(sql).run(...bindings);
        return {
          results: [],
          success: true,
          meta: { changes: Number(result.changes) },
        };
      },
    } as unknown as D1PreparedStatement;
  }

  return {
    prepare: (sql: string) => statement(sql),
    batch: async (statements: D1PreparedStatement[]) => Promise.all(statements.map((item) => item.run())),
    exec: async (sql: string) => {
      db.exec(sql);
      return { count: 0, duration: 0 };
    },
    dump: async () => new ArrayBuffer(0),
    withSession: () => ({}) as never,
  } as unknown as D1Database;
}

function seedBaselineRun(db: InstanceType<typeof DatabaseSync>, runId: string): void {
  const stamp = "2026-07-13T10:00:00.000Z";
  db.prepare(
    `INSERT INTO mlip_baseline_runs
      (run_id, workflow_instance_id, hypothesis_id, title, status, profile, fixture_id,
       manifest_url, artifact_prefix, max_dollars_per_hour, requested_max_active_gpu_cells,
       max_active_gpu_cells, max_poll_waves, rows_json, mlips_json, cost_estimate_json,
       report_r2_key, error, created_at, updated_at, started_at, finished_at)
     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
  ).run(
    runId,
    "workflow-1",
    "hypothesis-1",
    "Orchestrated baseline",
    "awaiting_results",
    "lab-gcp-gpu",
    "canonical-structures-v2",
    "gs://inputs/canonical-structures-v2/manifest.json",
    `gs://outputs/${runId}`,
    20,
    2,
    2,
    72,
    "[]",
    "[]",
    JSON.stringify({ estimated_hourly_usd: 1 }),
    null,
    null,
    stamp,
    stamp,
    stamp,
    null,
  );
  for (const [rowId, mlipId] of [["elastic_constants", "sevennet"], ["relaxation_stability", "sevennet"]]) {
    const cellId = `${runId}:baseline:${rowId}:${mlipId}`;
    db.prepare(
      `INSERT INTO mlip_baseline_cells
        (cell_id, run_id, row_id, mlip_id, status, target_job, manifest_url, retry_count, created_at, updated_at)
       VALUES (?, ?, ?, ?, 'queued', 'mlip-cell-sevennet', ?, 0, ?, ?)`,
    ).run(cellId, runId, rowId, mlipId, "gs://inputs/canonical-structures-v2/manifest.json", stamp, stamp);
  }
}

function seedCampaign(db: InstanceType<typeof DatabaseSync>, campaignId: string): void {
  const stamp = "2026-07-13T10:00:00.000Z";
  db.prepare(
    `INSERT INTO mlip_campaigns
      (campaign_id, hypothesis_id, title, status, rows_json, mlips_json, variants_json,
       fixture_url_template, model_pairs_json, top_k, quality_gate, created_at, updated_at)
     VALUES (?, 'hypothesis-1', 'Campaign', 'queued', '[]', '[]', ?, NULL, '[]', 5, 'accuracy', ?, ?)`,
  ).run(campaignId, JSON.stringify([{ id: "baseline" }, { id: "distill_accuracy" }]), stamp, stamp);
  for (const variantId of ["baseline", "distill_accuracy"]) {
    db.prepare(
      `INSERT INTO mlip_campaign_cells
        (cell_id, campaign_id, row_id, mlip_id, variant_id, fixture_url, status, created_at, updated_at)
       VALUES (?, ?, 'forces', 'chgnet', ?, 'gs://inputs/manifest.json', 'queued', ?, ?)`,
    ).run(`${campaignId}:${variantId}:forces:chgnet`, campaignId, variantId, stamp, stamp);
  }
}

function cellMetrics(
  runId: string,
  rowId: string,
  mlipId: string,
  status: "completed" | "failed",
  score: number,
): Record<string, unknown> {
  return {
    schema: "lupine.mlip.cell_result.v1",
    run_id: runId,
    campaign_id: runId,
    cell_id: `${runId}:baseline:${rowId}:${mlipId}`,
    row_id: rowId,
    mlip_id: mlipId,
    variant_id: "baseline",
    status,
    profile: "lab-gcp-gpu",
    fixture_id: "round1-candidates-v1",
    manifest_url: "gs://inputs/mlip-campaigns/round1-candidates-v1/manifest.json",
    accuracy: { score, unit: status === "completed" ? "row_native_physical_score" : "failed" },
    speed: { score: status === "completed" ? 1.5 : 0, unit: "structures_per_second" },
    artifact_uri: status === "completed" ? `gs://outputs/${rowId}/${mlipId}/cell_result.json` : undefined,
    error: status === "failed" ? "gated model access denied" : undefined,
  };
}

describe("MLIP beat ingress reconciliation", () => {
  let db: InstanceType<typeof DatabaseSync>;
  let env: Env;

  beforeAll(async () => {
    db = new DatabaseSync(":memory:");
    env = buildStubEnv({ LEDGER: sqliteLedger(db), DEV_MODE: "true" });
    db.exec(`
      CREATE TABLE lab_beats (
        beat_id TEXT PRIMARY KEY,
        agent TEXT NOT NULL,
        summary TEXT NOT NULL,
        metrics TEXT,
        ts INTEGER NOT NULL
      )
    `);
    await ensureMlipBaselineSchema(env);
    await ensureMlipCampaignSchema(env);
  });

  afterAll(() => db.close());

  async function postBeat(beatId: string, ts: number, metrics: Record<string, unknown>): Promise<Response> {
    return handleBeatsPost(
      new Request("https://worker.test/feed/beats", { method: "POST" }),
      env,
      JSON.stringify({
        beat_id: beatId,
        agent: "gcp-mlip-runner",
        summary: `result for ${String(metrics.cell_id)}`,
        metrics,
        ts,
      }),
    );
  }

  it("recovers the July six-cell parent and replays duplicate beats idempotently", async () => {
    const runId = "mlip-cloud-20260713-cand-r1";
    const baseTs = 1_752_400_000;
    const fixtures = [
      ["elastic_constants", "sevennet", "completed", 0.81],
      ["relaxation_stability", "sevennet", "completed", 0.93],
      ["elastic_constants", "orb-v3", "completed", 0.79],
      ["relaxation_stability", "orb-v3", "completed", 0.91],
      ["elastic_constants", "uma-s-1p1", "failed", 0],
      ["relaxation_stability", "uma-s-1p1", "failed", 0],
    ] as const;

    for (const [index, [rowId, mlipId, status, score]] of fixtures.entries()) {
      const response = await postBeat(
        `${runId}:beat:${index}`,
        baseTs + index,
        cellMetrics(runId, rowId, mlipId, status, score),
      );
      expect(response.status).toBe(200);
    }
    for (const [index, [rowId, mlipId, status, score]] of fixtures.entries()) {
      const response = await postBeat(
        `${runId}:beat:${index}`,
        baseTs + index,
        cellMetrics(runId, rowId, mlipId, status, score),
      );
      expect(response.status).toBe(200);
    }

    const parent = db.prepare(
      "SELECT * FROM mlip_baseline_runs WHERE run_id = ?",
    ).get(runId) as MlipBaselineRunRecord;
    const cells = db.prepare(
      "SELECT * FROM mlip_baseline_cells WHERE run_id = ? ORDER BY cell_id",
    ).all(runId) as MlipBaselineCellRecord[];
    expect(db.prepare("SELECT COUNT(*) AS count FROM mlip_baseline_runs WHERE run_id = ?").get(runId)).toEqual({ count: 1 });
    expect(db.prepare("SELECT COUNT(*) AS count FROM lab_beats WHERE beat_id LIKE ?").get(`${runId}:%`)).toEqual({ count: 6 });
    expect(cells).toHaveLength(6);
    expect(new Set(cells.map((item) => item.cell_id)).size).toBe(6);
    expect(cells.filter((item) => item.status === "completed")).toHaveLength(4);
    expect(cells.filter((item) => item.status === "failed")).toHaveLength(2);
    expect(parent).toMatchObject({
      status: "partial",
      profile: "recovered-ingress",
      fixture_id: "recovered-ingress",
      workflow_instance_id: null,
    });
    expect(parent.title).toContain("Recovered MLIP ingress run");
    expect(parent.error).toContain("original run configuration unavailable");

    const newest = cellMetrics(runId, "elastic_constants", "sevennet", "completed", 0.97);
    await postBeat(`${runId}:beat:newer`, baseTs + 100, newest);
    await postBeat(
      `${runId}:beat:stale-retry`,
      baseTs - 100,
      cellMetrics(runId, "elastic_constants", "sevennet", "completed", 0.25),
    );
    const reconciled = db.prepare(
      "SELECT accuracy_score, metrics_json FROM mlip_baseline_cells WHERE cell_id = ?",
    ).get(`${runId}:baseline:elastic_constants:sevennet`) as { accuracy_score: number; metrics_json: string };
    expect(reconciled.accuracy_score).toBe(0.97);
    expect(JSON.parse(reconciled.metrics_json)).toMatchObject({ accuracy: { score: 0.97 } });
  });

  it("keeps normal orchestrated configuration and terminalizes only after every cell finishes", async () => {
    const runId = "orchestrated-baseline-run";
    seedBaselineRun(db, runId);

    await recordMlipBaselineBeat(
      env,
      cellMetrics(runId, "elastic_constants", "sevennet", "completed", 0.88),
      "2026-07-13T10:01:00.000Z",
    );
    expect(db.prepare("SELECT status FROM mlip_baseline_runs WHERE run_id = ?").get(runId)).toEqual({
      status: "awaiting_results",
    });

    await recordMlipBaselineBeat(
      env,
      cellMetrics(runId, "relaxation_stability", "sevennet", "completed", 0.92),
      "2026-07-13T10:02:00.000Z",
    );
    const parent = db.prepare("SELECT * FROM mlip_baseline_runs WHERE run_id = ?").get(runId) as MlipBaselineRunRecord;
    expect(parent).toMatchObject({ status: "completed", profile: "lab-gcp-gpu", fixture_id: "canonical-structures-v2" });
    expect(parent.workflow_instance_id).toBe("workflow-1");
    expect(parent.finished_at).toBe("2026-07-13T10:02:00.000Z");
  });

  it("rolls campaign parents up from terminal cells and rejects stale metric retries", async () => {
    const completedId = "campaign-rollup-completed";
    seedCampaign(db, completedId);
    await recordMlipCampaignBeat(env, {
      campaign_id: completedId,
      cell_id: `${completedId}:baseline:forces:chgnet`,
      status: "completed",
      accuracy: { score: 0.7, unit: "score" },
    }, "2026-07-13T10:01:00.000Z");
    expect(db.prepare("SELECT status FROM mlip_campaigns WHERE campaign_id = ?").get(completedId)).toEqual({ status: "queued" });
    await recordMlipCampaignBeat(env, {
      campaign_id: completedId,
      cell_id: `${completedId}:distill_accuracy:forces:chgnet`,
      status: "completed",
      accuracy: { score: 0.85, unit: "score" },
    }, "2026-07-13T10:02:00.000Z");
    expect(db.prepare("SELECT status FROM mlip_campaigns WHERE campaign_id = ?").get(completedId)).toEqual({ status: "completed" });

    await recordMlipCampaignBeat(env, {
      campaign_id: completedId,
      cell_id: `${completedId}:distill_accuracy:forces:chgnet`,
      status: "completed",
      accuracy: { score: 0.91, unit: "score" },
    }, "2026-07-13T10:03:00.000Z");
    await recordMlipCampaignBeat(env, {
      campaign_id: completedId,
      cell_id: `${completedId}:distill_accuracy:forces:chgnet`,
      status: "completed",
      accuracy: { score: 0.2, unit: "score" },
    }, "2026-07-13T10:01:30.000Z");
    const latest = db.prepare(
      "SELECT accuracy_score FROM mlip_campaign_cells WHERE cell_id = ?",
    ).get(`${completedId}:distill_accuracy:forces:chgnet`) as { accuracy_score: number };
    expect(latest.accuracy_score).toBe(0.91);

    const failedId = "campaign-rollup-failed";
    seedCampaign(db, failedId);
    await recordMlipCampaignBeat(env, {
      campaign_id: failedId,
      cell_id: `${failedId}:baseline:forces:chgnet`,
      status: "completed",
    }, "2026-07-13T10:01:00.000Z");
    await recordMlipCampaignBeat(env, {
      campaign_id: failedId,
      cell_id: `${failedId}:distill_accuracy:forces:chgnet`,
      status: "failed",
    }, "2026-07-13T10:02:00.000Z");
    const failedParent = db.prepare("SELECT * FROM mlip_campaigns WHERE campaign_id = ?").get(failedId) as MlipCampaignRecord;
    const failedCells = db.prepare("SELECT * FROM mlip_campaign_cells WHERE campaign_id = ?").all(failedId) as MlipCampaignCell[];
    expect(failedCells.map((item) => item.status).sort()).toEqual(["completed", "failed"]);
    expect(failedParent.status).toBe("failed");
  });
});
