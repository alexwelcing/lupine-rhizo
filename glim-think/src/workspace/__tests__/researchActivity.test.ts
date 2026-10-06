import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";
// @ts-expect-error Test-only SQLite, excluded from Worker types.
import { DatabaseSync } from "node:sqlite";
// @ts-expect-error Test-only fixtures, excluded from Worker types.
import { readFileSync } from "node:fs";
import type { Env } from "../../types";
import {
  decodePublicResearchActivity, isPublicSourceUrl, PUBLIC_ACTIVITY_MAX_BYTES,
  publicActivitySha256, type PublicResearchActivity,
} from "../researchActivityContracts";
import { getPublicResearchActivity, importPublicResearchActivity, listPublicResearchActivity, researchActivityResponse } from "../researchActivity";

const base = (import.meta as ImportMeta & { url: string }).url;
const migration = readFileSync(new URL("../../../migrations/0021_public_research_activity.sql", base), "utf8");
const recordContract = JSON.parse(readFileSync(new URL("../../../../schemas/public-research-activity.v1.schema.json", base), "utf8"));
const feedContract = JSON.parse(readFileSync(new URL("../../../../schemas/public-research-activity-feed.v1.schema.json", base), "utf8"));
const databases: InstanceType<typeof DatabaseSync>[] = [];
let token: string;
let jwk: JsonWebKey;
const auth = { ADMIN_EMAIL: "reviewer@example.test", CF_ACCESS_TEAM_DOMAIN: "activity-test", CF_ACCESS_AUD: "activity-audience" };
beforeAll(async () => {
  const pair = await crypto.subtle.generateKey({ name: "RSASSA-PKCS1-v1_5", modulusLength: 2048, publicExponent: new Uint8Array([1, 0, 1]), hash: "SHA-256" }, true, ["sign", "verify"]) as CryptoKeyPair;
  jwk = await crypto.subtle.exportKey("jwk", pair.publicKey) as JsonWebKey;
  const encode = (value: unknown) => btoa(JSON.stringify(value)).replace(/=/g, "").replace(/\+/g, "-").replace(/\//g, "_");
  const data = `${encode({ alg: "RS256", kid: "activity-key" })}.${encode({ email: auth.ADMIN_EMAIL, aud: auth.CF_ACCESS_AUD,
    iss: "https://activity-test.cloudflareaccess.com", exp: Math.floor(Date.now() / 1000) + 300 })}`;
  const signature = await crypto.subtle.sign("RSASSA-PKCS1-v1_5", pair.privateKey, new TextEncoder().encode(data));
  token = `${data}.${btoa(String.fromCharCode(...new Uint8Array(signature))).replace(/=/g, "").replace(/\+/g, "-").replace(/\//g, "_")}`;
});
beforeEach(() => vi.stubGlobal("fetch", vi.fn(async (input: string) => {
  expect(input).toBe("https://activity-test.cloudflareaccess.com/cdn-cgi/access/certs");
  return Response.json({ keys: [{ ...jwk, kid: "activity-key" }] });
})));
afterEach(() => { for (const db of databases.splice(0)) db.close(); vi.unstubAllGlobals(); });

function record(id = "public-fixture-1", activityId = "public-fixture"): PublicResearchActivity {
  return {
    schema: "lupine.public_research_activity.v1", id, activityId, evidenceKind: "archived_analysis",
    state: "completed", verification: "arithmetic_checked", title: "Reviewed archive analysis", summary: "A synthetic fixture demonstrates the public projection.",
    observedAt: "2026-10-01T10:00:00.000Z", reviewedAt: "2026-10-01T11:00:00.000Z",
    datasets: [{ name: "Public fixture dataset", configurations: 8, groups: 2, atoms: 32 }],
    findings: ["The reported arithmetic was checked."], limitations: ["Synthetic fixture only; no scientific claim."], nextStep: "Review another independent panel.",
    sources: [{ label: "Primary paper", url: "https://arxiv.org/abs/2401.01234" }],
    hashes: [{ label: "Reviewed public summary", sha256: "a".repeat(64) }],
    repositoryLinks: [{ label: "Rhizo", url: "https://github.com/alexwelcing/lupine-rhizo" }],
    releaseLinks: [{ label: "Rhizo releases", url: "https://github.com/alexwelcing/lupine-rhizo/releases" }],
    supersedes: null, correctionReason: null,
  };
}

function harness() {
  const db = new DatabaseSync(":memory:"); databases.push(db); db.exec("PRAGMA foreign_keys=ON"); db.exec(migration);
  const queries: string[] = [];
  const hooks: { beforeRun?: () => void } = {};
  function statement(sql: string, values: unknown[] = []): D1PreparedStatement {
    return { bind: (...bound: unknown[]) => statement(sql, [...values, ...bound]),
      first: async () => db.prepare(sql).get(...values) ?? null,
      all: async () => ({ results: db.prepare(sql).all(...values), success: true, meta: {} }),
      run: async () => { hooks.beforeRun?.(); return { results: [], success: true, meta: { changes: Number(db.prepare(sql).run(...values).changes) } }; },
    } as unknown as D1PreparedStatement;
  }
  const env = { ...auth, LEDGER: { prepare: (sql: string) => { queries.push(sql); return statement(sql); } } } as unknown as Env;
  const request = (value: unknown, headers: Record<string, string> = {}) => new Request("https://worker.example.org/workspace/research-activity/import", {
    method: "POST", headers: { "Content-Type": "application/json", Origin: "https://worker.example.org", "Cf-Access-Jwt-Assertion": token, ...headers }, body: JSON.stringify(value),
  });
  return { db, env, queries, hooks, request };
}

describe("reviewed public activity contract", () => {
  it("shares a strict consumer contract without any private receipt fields", () => {
    const value = decodePublicResearchActivity(record());
    expect(Object.keys(value).sort()).toEqual([...recordContract.required].sort());
    expect(recordContract.additionalProperties).toBe(false);
    expect(feedContract.properties.items.maxItems).toBe(50);
    expect(feedContract.properties.schema.const).toBe("lupine.public_research_activity_feed.v1");
    for (const key of ["packetJson", "stages", "machineId", "operatorEmail", "sessionId", "privatePath", "receipt"]) {
      expect(() => decodePublicResearchActivity({ ...value, [key]: "private" })).toThrow();
    }
    expect(() => decodePublicResearchActivity({ ...value, datasets: [{ ...value.datasets[0], path: "private" }] })).toThrow();
  });
  it.each(["/Users/person/private.json", "work/private/result.json", "outputs/private.json", "gs://private-bucket/object", "user@example.org", "10.0.0.1", "device.tail000.ts.net", "awphone", "Bearer abcdefghijklmnop", "sk-proj-abcdefghijklmnop", "ghp_abcdefghijklmnop", "<script>unsafe</script>"])("rejects private text %s", text => {
    expect(() => decodePublicResearchActivity({ ...record(), summary: text })).toThrow();
  });
  it.each(["http://arxiv.org/a", "https://user:pass@arxiv.org/a", "https://localhost/a", "https://127.0.0.1/a", "https://10.0.0.1/a", "https://[::1]/a", "https://0x7f000001/a", "https://device.tail123.ts.net/a", "https://127.0.0.1.nip.io/a", "https://host.internal/a", "https://arxiv.org:444/a", "https://arxiv.org/a?token=secret", "https://arxiv.org/a?X-Amz-Credential=secret", "https://arxiv.org/a#access_token=secret", "https://arxiv.org/%55sers/person/private", "https://arxiv.org/a?next=http%3A%2F%2Flocalhost"])("rejects a nonpublic or credential-bearing source %s", url => {
    expect(isPublicSourceUrl(url)).toBe(false);
    expect(() => decodePublicResearchActivity({ ...record(), sources: [{ label: "Invalid source", url }] })).toThrow();
  });
  it("accepts primary HTTPS sources and restricts repository/release identities", () => {
    expect(isPublicSourceUrl("https://arxiv.org/%5c%5cdevice/file")).toBe(false);
    expect(isPublicSourceUrl("https://arxiv.org/%0asecret")).toBe(false);
    expect(isPublicSourceUrl("https://www.nature.com/articles/s41524-023-01123-3")).toBe(true);
    expect(isPublicSourceUrl("https://doi.org/10.1038/s41524-023-01123-3")).toBe(true);
    expect(() => decodePublicResearchActivity({ ...record(), repositoryLinks: [{ label: "Other", url: "https://github.com/other/lupine-rhizo" }] })).toThrow();
    expect(() => decodePublicResearchActivity({ ...record(), releaseLinks: [{ label: "Code", url: "https://github.com/alexwelcing/lupine-rhizo/tree/main" }] })).toThrow();
  });
  it("requires actual timestamp ordering, evidence references and bounded fields", () => {
    for (const patch of [{ observedAt: "2026-10-01T12:00:00.000Z" }, { reviewedAt: "2999-01-01T00:00:00.000Z" }, { observedAt: "2026-02-30T00:00:00.000Z" }, { observedAt: "2026-10-01T10:00:00Z" }, { limitations: [] }, { sources: [], hashes: [] }, { summary: "x".repeat(1201) }, { id: "user@device" }, { datasets: [{ name: "Bad", configurations: -1 }] }]) {
      expect(() => decodePublicResearchActivity({ ...record(), ...patch })).toThrow();
    }
  });
});

describe("public projection storage and immutable history", () => {
  it("is empty by default and never queries private data", async () => {
    const h = harness();
    h.db.exec("CREATE TABLE workspace_research_runs (payload TEXT); INSERT INTO workspace_research_runs VALUES ('private-packet')");
    expect(await listPublicResearchActivity(h.env)).toEqual({ schema: "lupine.public_research_activity_feed.v1", items: [], truncated: false });
    expect(h.queries.every(sql => !sql.includes("workspace_research_runs") && sql.includes("public_research_activity"))).toBe(true);
  });
  it("imports idempotently without changing evidence age on reads or duplicates", async () => {
    const h = harness(); const value = record();
    expect((await importPublicResearchActivity(h.env, value)).duplicate).toBe(false);
    expect((await importPublicResearchActivity(h.env, value)).duplicate).toBe(true);
    const before = await listPublicResearchActivity(h.env);
    expect(await listPublicResearchActivity(h.env)).toEqual(before);
    expect(before.items[0].observedAt).toBe(value.observedAt);
    await expect(importPublicResearchActivity(h.env, { ...value, summary: "Replaced" })).rejects.toThrow();
    expect(() => h.db.exec("UPDATE public_research_activity SET observed_at='changed'")).toThrow("immutable");
    expect(() => h.db.exec("DELETE FROM public_research_activity")).toThrow("immutable");
  });
  it("keeps terminal corrections explicit and failed states terminal", async () => {
    const h = harness(); const value = { ...record(), state: "failed" as const, verification: "pending" as const };
    await importPublicResearchActivity(h.env, value);
    const next = { ...value, id: "public-fixture-2", supersedes: value.id, reviewedAt: "2026-10-01T12:00:00.000Z", correctionReason: "Clarified the recorded failure." };
    for (const patch of [{ state: "completed" }, { state: "running" }, { evidenceKind: "research_cycle" }, { correctionReason: null }, { reviewedAt: value.reviewedAt }]) {
      await expect(importPublicResearchActivity(h.env, { ...next, ...patch })).rejects.toThrow();
    }
    await importPublicResearchActivity(h.env, next);
    expect((await listPublicResearchActivity(h.env)).items.map(x => x.id)).toEqual([next.id]);
    expect((await getPublicResearchActivity(h.env, value.id))!.state).toBe("failed");
    await expect(importPublicResearchActivity(h.env, { ...next, id: "public-fixture-3", reviewedAt: "2026-10-01T13:00:00.000Z" })).rejects.toThrow();
  });
  it("accepts reviewed progress successors and prevents duplicate roots and forks", async () => {
    const h = harness(); const first = { ...record(), state: "planned" as const, verification: "pending" as const };
    await importPublicResearchActivity(h.env, first);
    await expect(importPublicResearchActivity(h.env, { ...first, id: "duplicate-root" })).rejects.toThrow();
    const next = { ...first, id: "public-fixture-2", state: "running" as const, supersedes: first.id, reviewedAt: "2026-10-01T12:00:00.000Z" };
    await importPublicResearchActivity(h.env, next);
    await expect(importPublicResearchActivity(h.env, { ...next, id: "fork", reviewedAt: "2026-10-01T13:00:00.000Z" })).rejects.toThrow();
    await expect(importPublicResearchActivity(h.env, { ...next, id: "rewind", state: "planned", supersedes: next.id, reviewedAt: "2026-10-01T13:00:00.000Z" })).rejects.toThrow();
  });
  it("fails closed for a malformed selected row, including lookahead", async () => {
    const h = harness(); const good = record(); await importPublicResearchActivity(h.env, good);
    const malformed = JSON.stringify({ ...record("bad-record", "bad-activity"), observedAt: "2026-09-01T10:00:00.000Z", privatePath: "DO-NOT-ECHO" });
    h.db.prepare("INSERT INTO public_research_activity(id,activity_id,observed_at,reviewed_at,supersedes_id,payload_sha256,payload) VALUES(?,?,?,?,?,?,?)")
      .run("bad-record", "bad-activity", "2026-09-01T10:00:00.000Z", good.reviewedAt, null, await publicActivitySha256(malformed), malformed);
    const response = await researchActivityResponse(new Request("https://worker.example.org/research/activity?limit=1"), h.env);
    expect(response!.status).toBe(503); expect(await response!.text()).not.toContain("DO-NOT-ECHO");
  });
  it("bounds page size, sorts by observation rather than review time, and exposes history read-only", async () => {
    const h = harness(); await importPublicResearchActivity(h.env, record("older", "older-study"));
    await importPublicResearchActivity(h.env, { ...record("newer", "newer-study"), observedAt: "2026-10-02T10:00:00.000Z", reviewedAt: "2026-10-02T11:00:00.000Z" });
    expect(await listPublicResearchActivity(h.env, 1)).toMatchObject({ items: [{ id: "newer" }], truncated: true });
    const response = await researchActivityResponse(new Request("https://worker.example.org/research/activity/older"), h.env);
    expect(await response!.json()).toMatchObject({ items: [{ id: "older" }], truncated: false });
  });
});

describe("public read and operator import boundaries", () => {
  it("serves only GET/OPTIONS with public credential-free CORS", async () => {
    const h = harness(); const response = await researchActivityResponse(new Request("https://worker.example.org/research/activity", { headers: { Origin: "https://reader.example.org" } }), h.env);
    expect(response!.status).toBe(200); expect(response!.headers.get("Access-Control-Allow-Origin")).toBe("*");
    expect(response!.headers.has("Access-Control-Allow-Credentials")).toBe(false);
    expect((await researchActivityResponse(new Request("https://worker.example.org/research/activity", { method: "POST", body: "private" }), h.env))!.status).toBe(405);
    expect((await researchActivityResponse(new Request("https://worker.example.org/research/activity", { method: "OPTIONS" }), h.env))!.status).toBe(204);
  });
  it.each(["limit=0", "limit=51", "limit=-1", "limit=1.5", "limit=1&limit=2", "token=secret"])("rejects unbounded or unknown queries %s", async query => {
    const h = harness(); expect((await researchActivityResponse(new Request(`https://worker.example.org/research/activity?${query}`), h.env))!.status).toBe(400);
    expect(h.queries).toHaveLength(0);
  });
  it("requires same-origin operator JWT and rejects every legacy bypass before storage", async () => {
    const h = harness(); const bypassEnv = { ...h.env, DEV_MODE: "true", INTERNAL_TASK_TOKEN: "secret", HERDR_BRIDGE_TOKEN: "secret" } as Env;
    const rejectedHeaders: Record<string, string>[] = [{ "Cf-Access-Jwt-Assertion": "", "X-Internal-Token": "secret" }, { "Cf-Access-Jwt-Assertion": "", Authorization: "Bearer secret" }, { Origin: "https://other.example.org" }, { Origin: "" }];
    for (const headers of rejectedHeaders) {
      expect((await researchActivityResponse(h.request(record(), headers), bypassEnv))!.status).toBe(403);
    }
    expect(h.queries).toHaveLength(0);
    const accepted = await researchActivityResponse(h.request(record()), h.env);
    expect(accepted!.status).toBe(200); expect(accepted!.headers.get("Cache-Control")).toBe("private, no-store");
    expect(accepted!.headers.has("Access-Control-Allow-Origin")).toBe(false);
  });
  it("rejects invalid projection and excessive UTF-8 streams without database access", async () => {
    const h = harness();
    expect((await researchActivityResponse(h.request({ ...record(), packetJson: "private" }), h.env))!.status).toBe(400);
    expect((await researchActivityResponse(h.request(record(), { "Content-Type": "text/plain" }), h.env))!.status).toBe(415);
    expect((await researchActivityResponse(h.request({ summary: "é".repeat(PUBLIC_ACTIVITY_MAX_BYTES) }), h.env))!.status).toBe(413);
    expect(h.queries).toHaveLength(0);
  });
});
