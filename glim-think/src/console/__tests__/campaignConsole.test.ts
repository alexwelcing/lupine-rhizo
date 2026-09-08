import { afterEach, describe, expect, it, vi } from "vitest";
// @ts-expect-error Node 24 provides node:sqlite; Worker tsconfig excludes Node types.
import { DatabaseSync } from "node:sqlite";
import { CampaignConsole } from "../campaignConsole";
import type { Env } from "../../types";

const databases: InstanceType<typeof DatabaseSync>[] = [];
afterEach(() => { vi.useRealTimers(); for (const db of databases.splice(0)) db.close(); });

function harness() {
  const db = new DatabaseSync(":memory:");
  databases.push(db);
  const exec = vi.fn((sql: string, ...bindings: unknown[]) => {
    if (sql.includes("CREATE TABLE")) { db.exec(sql); return { toArray: () => [], rowsWritten: 0 }; }
    const statement = db.prepare(sql);
    if (statement.columns().length) return { toArray: () => statement.all(...bindings), rowsWritten: 0 };
    const result = statement.run(...bindings);
    return { toArray: () => [], rowsWritten: Number(result.changes) };
  });
  const storage = { sql: { exec }, getAlarm: vi.fn(async () => null), setAlarm: vi.fn(async (_time: number) => {}) };
  const console = new CampaignConsole({ storage } as unknown as DurableObjectState, {} as Env);
  const send = vi.fn();
  // A socket peer spy observes broadcasts; all persistence uses real SQLite.
  (console as unknown as { sockets: Set<unknown> }).sockets.add({ send });
  const request = (path: string, body?: unknown) => console.fetch(new Request(`https://console${path}`, body === undefined ? {} : {
    method: "POST", body: JSON.stringify(body), headers: { "Content-Type": "application/json" },
  }));
  const lock = (manifest: unknown, campaign = "campaign-1") => request(`/lock?campaign_id=${campaign}`, { manifest });
  const snapshot = async () => (await request("/state")).json() as Promise<any>;
  return { db, exec, storage, console, send, request, lock, snapshot };
}

const manifest = { campaign_id: "campaign-1", content_hash: "opaque-hash" };
const beat = (metrics: Record<string, unknown> = {}, observedAt = "2026-09-01T10:00:00.000Z") => ({
  beat_id: "beat-1", summary: "cell update", observedAt,
  metrics: { campaign_id: "campaign-1", cell_id: "cell-1", ...metrics },
});

describe("CampaignConsole beat projection", () => {
  it("normalizes projector defaults, flat/nested accuracy and milliseconds using source time", async () => {
    const h = harness();
    expect((await h.request("/beat", beat({ row_id: "row", mlip_id: "model", accuracy_score: 0.7, speed: { warm_duration_ms: 2500 } }))).status).toBe(200);
    expect(await h.snapshot()).toMatchObject({ campaign_id: "campaign-1", manifest_hash: null, cells: [{
      cell_id: "cell-1", path_id: "row", mlip_id: "model", accuracy_score: 0.7,
      wall_seconds: 2.5, status: "completed", updated_at: "2026-09-01T10:00:00.000Z",
    }] });
    expect(h.storage.setAlarm).not.toHaveBeenCalled();
    await h.request("/beat", beat({ status: "queued", path_id: "path", row_id: "row", accuracy_score: 0.7, accuracy: { score: 0.9 } }, "2026-09-01T11:00:00Z"));
    expect((await h.snapshot()).cells[0]).toMatchObject({ path_id: "path", accuracy_score: 0.9, status: "completed" });
    const last = JSON.parse(h.send.mock.calls.at(-1)![0]);
    expect(last.cell).toMatchObject({ status: "completed", accuracy_score: 0.9, updated_at: "2026-09-01T11:00:00.000Z" });
  });

  it("ignores duplicate and out-of-order timestamps without broadcasting or setting alarms", async () => {
    const h = harness();
    await h.request("/beat", beat({ status: "completed", accuracy_score: 0.9 }));
    const first = await h.snapshot();
    h.send.mockClear();
    for (const observedAt of ["2026-09-01T10:00:00.000Z", "2026-09-01T09:00:00.000Z", "2026-09-01T12:00:00+02:00"]) {
      expect((await h.request("/beat", beat({ status: "running", accuracy_score: 0.1 }, observedAt))).status).toBe(200);
      expect(await h.snapshot()).toEqual(first);
    }
    expect(h.send).not.toHaveBeenCalled();
    expect(h.storage.getAlarm).not.toHaveBeenCalled();
    expect(h.storage.setAlarm).not.toHaveBeenCalled();
    await h.request("/beat", beat({ status: "failed" }, "2026-09-01T10:00:00.001Z"));
    expect((await h.snapshot()).cells[0]).toMatchObject({ status: "failed", updated_at: "2026-09-01T10:00:00.001Z" });
    expect(h.send).toHaveBeenCalledTimes(1);
  });

  it("rejects invalid timestamps, JSON and SQL-bound metric types before writing", async () => {
    const h = harness();
    for (const observedAt of [undefined, null, 123, "", "not-time", "2026-09-01", "2026-09-01T10:00:00", "2026-02-30T10:00:00Z"]) {
      expect((await h.request("/beat", { ...beat(), observedAt })).status).toBe(400);
    }
    expect((await h.console.fetch(new Request("https://console/beat", { method: "POST", body: "{" }))).status).toBe(400);
    for (const body of [null, [], {}, { ...beat(), metrics: null }, { ...beat(), metrics: [] }]) {
      expect((await h.request("/beat", body)).status).toBe(400);
    }
    for (const field of ["cell_id", "row_id", "path_id", "mlip_id", "status", "artifact_uri", "campaign_id"]) {
      for (const value of [12, {}, [], true]) {
        expect((await h.request("/beat", beat({ [field]: value }))).status).toBe(400);
      }
    }
    for (const metrics of [{ accuracy_score: "1" }, { accuracy: { score: "1" } }, { speed: { warm_duration_ms: "1" } },
      { accuracy: [] }, { speed: "fast" }, { cell_id: " " }, { campaign_id: "" }, { campaign_id: undefined }]) {
      expect((await h.request("/beat", beat(metrics))).status).toBe(400);
    }
    expect((await h.snapshot()).cells).toEqual([]);
    expect((await h.snapshot()).campaign_id).toBeNull();
    expect(h.send).not.toHaveBeenCalled();
    expect(h.storage.setAlarm).not.toHaveBeenCalled();
  });

  it("retains beat identity before lock and rejects inconsistent subsequent beats and locks", async () => {
    const h = harness();
    await h.request("/beat", beat());
    expect((await h.snapshot()).campaign_id).toBe("campaign-1");
    expect((await h.request("/beat", beat({ campaign_id: "other" }))).status).toBe(409);
    expect((await h.lock({ ...manifest, campaign_id: "other" }, "other")).status).toBe(409);
    expect((await h.lock(manifest)).status).toBe(200);
    expect((await h.request("/beat", beat({ campaign_id: "other" }))).status).toBe(409);
    expect((await h.snapshot()).campaign_id).toBe("campaign-1");
  });
});

describe("CampaignConsole sweeper", () => {
  it("allows a delayed completion newer than the last running observation after timeout", async () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-09-01T18:00:00Z"));
    const h = harness();
    await h.request("/beat", beat({ status: "running" }));
    await h.console.alarm();
    expect((await h.snapshot()).cells[0].status).toBe("failed");
    await h.request("/beat", beat({ status: "completed", accuracy_score: 0.9 }, "2026-09-01T11:00:00Z"));
    expect((await h.snapshot()).cells[0]).toMatchObject({ status: "completed", accuracy_score: 0.9 });
  });

  it("does not arm an idle campaign alarm", async () => {
    const h = harness();
    await h.console.alarm();
    expect(h.storage.setAlarm).not.toHaveBeenCalled();
    expect(h.send).not.toHaveBeenCalled();
  });

  it("fails only expired running cells and rearms only while running cells remain", async () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-09-01T12:00:00Z"));
    const h = harness();
    await h.request("/beat", beat({ cell_id: "stale", status: "running" }, "2026-09-01T05:59:59Z"));
    expect(h.storage.setAlarm).toHaveBeenLastCalledWith(Date.now() + 15 * 60 * 1000);
    h.storage.getAlarm.mockResolvedValueOnce(Date.now() + 1000 as never);
    await h.request("/beat", beat({ cell_id: "boundary", status: "running" }, "2026-09-01T06:00:00Z"));
    expect(h.storage.setAlarm).toHaveBeenCalledTimes(1);
    await h.request("/beat", beat({ cell_id: "completed", status: "completed" }, "2026-09-01T01:00:00Z"));
    await h.request("/beat", beat({ cell_id: "failed", status: "failed" }, "2026-09-01T01:00:00Z"));
    h.send.mockClear();
    h.storage.setAlarm.mockClear();
    await h.console.alarm();
    const cells = (await h.snapshot()).cells;
    expect(cells.find((c: any) => c.cell_id === "stale")).toMatchObject({ status: "failed", updated_at: "2026-09-01T05:59:59.000Z" });
    expect(cells.find((c: any) => c.cell_id === "boundary").status).toBe("running");
    expect(cells.find((c: any) => c.cell_id === "completed").status).toBe("completed");
    expect(cells.find((c: any) => c.cell_id === "failed").updated_at).toBe("2026-09-01T01:00:00.000Z");
    expect(h.storage.setAlarm).toHaveBeenCalledTimes(1);
    expect(JSON.parse(h.send.mock.calls[0][0])).toEqual({ kind: "sweep", swept: 1, at: "2026-09-01T12:00:00.000Z" });
    vi.setSystemTime(new Date("2026-09-01T12:15:00Z"));
    h.storage.setAlarm.mockClear();
    await h.console.alarm();
    expect((await h.snapshot()).cells.some((c: any) => c.status === "running")).toBe(false);
    expect(h.storage.setAlarm).not.toHaveBeenCalled();
    h.send.mockClear();
    await h.console.alarm();
    expect(h.send).not.toHaveBeenCalled();
    expect(h.storage.setAlarm).not.toHaveBeenCalled();
  });
});

it("retries schema initialization after a storage failure", async () => {
  const h = harness();
  h.exec.mockImplementationOnce(() => { throw new Error("schema unavailable"); });
  await expect(h.request("/state")).rejects.toThrow("schema unavailable");
  expect((await h.request("/state")).status).toBe(200);
});

describe("CampaignConsole locks", () => {
  it("returns 426 for a live request without a websocket upgrade", async () => {
    expect((await harness().request("/live")).status).toBe(426);
  });

  it("rejects malformed JSON, nulls, empty identifiers and route mismatches without writing", async () => {
    const h = harness();
    expect((await h.console.fetch(new Request("https://console/lock?campaign_id=campaign-1", { method: "POST", body: "{" }))).status).toBe(400);
    for (const body of [null, [], {}, { manifest: null }, { manifest: [] }]) {
      expect((await h.request("/lock?campaign_id=campaign-1", body)).status).toBe(400);
    }
    for (const value of [undefined, null, "", "  ", 12, {}]) {
      expect((await h.lock({ ...manifest, content_hash: value })).status).toBe(400);
      expect((await h.lock({ ...manifest, campaign_id: value })).status).toBe(400);
    }
    expect((await h.request("/lock", { manifest })).status).toBe(400);
    expect((await h.lock(manifest, "other")).status).toBe(409);
    expect((await h.snapshot()).manifest_hash).toBeNull();
    expect(h.send).not.toHaveBeenCalled();
  });

  it("preserves locked_at on identical retries and conflicts on hash or identity changes", async () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-09-01T00:00:00Z"));
    const h = harness();
    expect((await h.lock(manifest)).status).toBe(200);
    const first = await h.snapshot();
    vi.setSystemTime(new Date("2026-09-02T00:00:00Z"));
    expect((await h.lock(manifest)).status).toBe(200);
    expect(await h.snapshot()).toEqual(first);
    expect(h.send).toHaveBeenCalledTimes(1);
    expect((await h.lock({ ...manifest, content_hash: "different" })).status).toBe(409);
    expect((await h.lock({ ...manifest, campaign_id: "other" }, "other")).status).toBe(409);
    expect(await h.snapshot()).toEqual(first);
  });
});
