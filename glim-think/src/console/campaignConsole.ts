/**
 * CampaignConsole: one Durable Object per campaign — the live operator surface.
 *
 * Why a DO and not D1: the console (lupine-console, GPUI desktop) wants
 * push-based cell updates while a campaign runs. A DO holds the campaign's
 * hot state in SQLite and fans beats out over a websocket the moment they
 * land; D1 remains the long-term record.
 *
 * Routes (via stub.fetch from server.ts, or direct from feed/beats.ts):
 *   POST /lock?campaign_id=... { manifest } — freeze the preregistered manifest; a
 *                                    second lock with a different hash 409s.
 *   POST /beat   { beat_id, metrics, summary, observedAt } — ingest a cell beat (from /feed/beats
 *                                    fan-in); upserts the cell row and
 *                                    broadcasts to live sockets.
 *   GET  /state                    — snapshot: meta + cells.
 *   GET  /live                     — websocket: snapshot on connect, then
 *                                    every beat as it lands.
 *   Alarm: sweeps cells stuck in `running` past CELL_TIMEOUT_MS into `failed`
 *   (recorded, never imputed — same doctrine as the rest of the stack).
 */
import type { Env } from "../types";

const CELL_TIMEOUT_MS = 6 * 60 * 60 * 1000; // matches the Cloud Run task timeout

interface CellRow {
  cell_id: string;
  path_id: string | null;
  mlip_id: string | null;
  status: string;
  artifact_uri: string | null;
  accuracy_score: number | null;
  wall_seconds: number | null;
  updated_at: string;
}

interface BeatMetrics {
  cell_id?: string;
  row_id?: string;
  path_id?: string;
  mlip_id?: string;
  status?: string;
  artifact_uri?: string;
  accuracy?: { score?: number };
  accuracy_score?: number;
  speed?: { warm_duration_ms?: number };
  campaign_id?: string;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function validMetrics(value: unknown): value is BeatMetrics {
  if (!isRecord(value)) return false;
  for (const key of ["cell_id", "row_id", "path_id", "mlip_id", "status", "artifact_uri", "campaign_id"]) {
    if (value[key] != null && typeof value[key] !== "string") return false;
  }
  for (const key of ["accuracy", "speed"]) {
    if (value[key] != null && !isRecord(value[key])) return false;
  }
  const numbers = [value.accuracy_score, (value.accuracy as Record<string, unknown> | null)?.score,
    (value.speed as Record<string, unknown> | null)?.warm_duration_ms];
  return numbers.every((n) => n == null || (typeof n === "number" && Number.isFinite(n)));
}

function sourceTimestamp(value: unknown): string | null {
  if (typeof value !== "string") return null;
  const match = /^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})(?:\.\d{1,3})?(?:Z|[+-]\d{2}:\d{2})$/.exec(value);
  if (!match) return null;
  const local = new Date(`${match[1]}Z`);
  const date = new Date(value);
  // Date.parse alone silently rolls invalid calendar dates into the next month.
  if (!Number.isFinite(local.getTime()) || !local.toISOString().startsWith(match[1])
    || !Number.isFinite(date.getTime())) return null;
  return date.toISOString();
}

export class CampaignConsole implements DurableObject {
  private state: DurableObjectState;
  private env: Env;
  private started = false;
  private sockets = new Set<WebSocket>();

  constructor(state: DurableObjectState, env: Env) {
    this.state = state;
    this.env = env;
  }

  private async ensureStarted() {
    if (this.started) return;
    this.state.storage.sql.exec(`
      CREATE TABLE IF NOT EXISTS meta (
        k TEXT PRIMARY KEY,
        v TEXT
      );
      CREATE TABLE IF NOT EXISTS cells (
        cell_id TEXT PRIMARY KEY,
        path_id TEXT,
        mlip_id TEXT,
        status TEXT,
        artifact_uri TEXT,
        accuracy_score REAL,
        wall_seconds REAL,
        updated_at TEXT
      );
    `);
    this.started = true;
  }

  private metaGet(k: string): string | null {
    const rows = this.state.storage.sql
      .exec(`SELECT v FROM meta WHERE k = ?`, k)
      .toArray();
    return rows.length ? (rows[0].v as string) : null;
  }

  private metaSet(k: string, v: string) {
    this.state.storage.sql.exec(
      `INSERT INTO meta (k, v) VALUES (?, ?)
       ON CONFLICT(k) DO UPDATE SET v = excluded.v`,
      k, v,
    );
  }

  private snapshot() {
    const cells = this.state.storage.sql
      .exec(`SELECT * FROM cells ORDER BY updated_at DESC`)
      .toArray() as unknown as CellRow[];
    return {
      campaign_id: this.metaGet("campaign_id"),
      manifest_hash: this.metaGet("manifest_hash"),
      locked_at: this.metaGet("locked_at"),
      status: this.metaGet("status") || "draft",
      cells,
    };
  }

  private broadcast(payload: unknown) {
    const text = JSON.stringify(payload);
    for (const ws of this.sockets) {
      try {
        ws.send(text);
      } catch {
        this.sockets.delete(ws);
      }
    }
  }

  private async sweepStaleCells() {
    const cutoff = new Date(Date.now() - CELL_TIMEOUT_MS).toISOString();
    // Keep updated_at as the producer observation watermark: a local timeout
    // must not suppress a delayed result that is newer than the last beat.
    const res = this.state.storage.sql.exec(
      `UPDATE cells SET status = 'failed'
       WHERE status = 'running' AND updated_at < ?`,
      cutoff,
    );
    const swept = res.rowsWritten ?? 0;
    if (swept > 0) {
      this.broadcast({ kind: "sweep", swept, at: new Date().toISOString() });
    }
  }

  async alarm() {
    await this.ensureStarted();
    await this.sweepStaleCells();
    const running = this.state.storage.sql
      .exec(`SELECT cell_id FROM cells WHERE status = 'running' LIMIT 1`).toArray();
    if (running.length > 0) {
      await this.state.storage.setAlarm(Date.now() + 15 * 60 * 1000);
    }
  }

  async fetch(request: Request): Promise<Response> {
    await this.ensureStarted();
    const url = new URL(request.url);

    if (url.pathname === "/lock" && request.method === "POST") {
      const body = await request.json().catch(() => null) as { manifest?: Record<string, unknown> } | null;
      const manifest = body?.manifest;
      const campaignId = url.searchParams.get("campaign_id");
      if (!manifest || typeof manifest.content_hash !== "string" || !manifest.content_hash.trim()
        || typeof manifest.campaign_id !== "string" || !manifest.campaign_id.trim()
        || !campaignId?.trim()) {
        return Response.json({ error: "nonempty manifest.content_hash and campaign_id required" }, { status: 400 });
      }
      const identity = this.metaGet("campaign_id");
      if (manifest.campaign_id !== campaignId || (identity !== null && identity !== campaignId)) {
        return Response.json({ error: "campaign identity conflict" }, { status: 409 });
      }
      const existing = this.metaGet("manifest_hash");
      if (existing !== null) {
        if (existing !== manifest.content_hash) {
          return Response.json({ error: "campaign locked under a different manifest hash", existing }, { status: 409 });
        }
        return Response.json({ ok: true, manifest_hash: existing });
      }
      this.metaSet("manifest_hash", manifest.content_hash);
      this.metaSet("campaign_id", campaignId);
      this.metaSet("locked_at", new Date().toISOString());
      this.metaSet("status", "locked");
      this.broadcast({ kind: "locked", manifest_hash: manifest.content_hash });
      return Response.json({ ok: true, manifest_hash: manifest.content_hash });
    }

    if (url.pathname === "/beat" && request.method === "POST") {
      const beat: unknown = await request.json().catch(() => null);
      if (!isRecord(beat) || !validMetrics(beat.metrics)) {
        return Response.json({ error: "valid beat metrics required" }, { status: 400 });
      }
      const m = beat.metrics;
      const cellId = m.cell_id ?? beat.beat_id;
      const updatedAt = sourceTimestamp(beat.observedAt);
      if (typeof cellId !== "string" || !cellId.trim()
        || typeof m.campaign_id !== "string" || !m.campaign_id.trim() || !updatedAt) {
        return Response.json({ error: "nonempty cell_id, campaign_id and ISO observedAt required" }, { status: 400 });
      }
      const identity = this.metaGet("campaign_id");
      if (identity !== null && identity !== m.campaign_id) {
        return Response.json({ error: "campaign identity conflict" }, { status: 409 });
      }
      const cell: CellRow = {
        cell_id: cellId,
        path_id: m.path_id || m.row_id || null,
        mlip_id: m.mlip_id || null,
        status: m.status === "failed" ? "failed" : m.status === "running" ? "running" : "completed",
        artifact_uri: m.artifact_uri || null,
        accuracy_score: m.accuracy?.score ?? m.accuracy_score ?? null,
        wall_seconds: m.speed?.warm_duration_ms != null ? m.speed.warm_duration_ms / 1000 : null,
        updated_at: updatedAt,
      };
      const result = this.state.storage.sql.exec(
        `INSERT INTO cells (cell_id, path_id, mlip_id, status, artifact_uri, accuracy_score, wall_seconds, updated_at)
         VALUES (?, ?, ?, ?, ?, ?, ?, ?)
         ON CONFLICT(cell_id) DO UPDATE SET
           path_id = excluded.path_id,
           mlip_id = excluded.mlip_id,
           status = excluded.status,
           artifact_uri = excluded.artifact_uri,
           accuracy_score = excluded.accuracy_score,
           wall_seconds = excluded.wall_seconds,
           updated_at = excluded.updated_at
         WHERE excluded.updated_at > cells.updated_at`,
        cell.cell_id, cell.path_id, cell.mlip_id, cell.status, cell.artifact_uri,
        cell.accuracy_score, cell.wall_seconds, cell.updated_at,
      );
      if (result.rowsWritten === 0) return Response.json({ ok: true, ignored: true });
      if (identity === null) this.metaSet("campaign_id", m.campaign_id);
      if (cell.status === "running") {
        // Ensure the sweeper alarm exists while work is in flight.
        const alarm = await this.state.storage.getAlarm();
        if (alarm === null) {
          await this.state.storage.setAlarm(Date.now() + 15 * 60 * 1000);
        }
      }
      this.broadcast({ kind: "cell", cell: { ...m, ...cell } });
      return Response.json({ ok: true });
    }

    if (url.pathname === "/state" && request.method === "GET") {
      return Response.json(this.snapshot());
    }

    if (url.pathname === "/live" && request.method === "GET") {
      if (request.headers.get("Upgrade") !== "websocket") {
        return new Response("expected websocket", { status: 426 });
      }
      const pair = new WebSocketPair();
      const [client, server] = Object.values(pair);
      server.accept();
      server.send(JSON.stringify({ kind: "snapshot", ...this.snapshot() }));
      this.sockets.add(server);
      server.addEventListener("close", () => this.sockets.delete(server));
      server.addEventListener("error", () => this.sockets.delete(server));
      return new Response(null, { status: 101, webSocket: client });
    }

    return new Response("not found", { status: 404 });
  }
}
