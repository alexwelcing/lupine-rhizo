import { describe, expect, it, vi, beforeEach } from "vitest";
import { conversationIdSchema, settingsSchema, safeEvidenceHref, validateChatProfile, validateWorkspaceStateChange } from "../contracts";
import { EVIDENCE_SQL, readWorkspaceEvidence } from "../evidence";
import { listWorkspaceConversations } from "../registry";
import type { Env } from "../../types";

const doubles = vi.hoisted(() => ({
  select: vi.fn(), decide: vi.fn(), catalog: vi.fn(),
}));
vi.mock("@cloudflare/think", () => ({
  Think: class {
    env: unknown; state: unknown; config: unknown; name = "research";
    ctx = { waitUntil: (_promise: Promise<unknown>) => {} };
    constructor(_ctx: unknown, env: unknown) { this.env = env; }
    getConfig() { return this.config; }
    configure(value: unknown) { this.config = value; }
    setState(value: unknown) { this.state = value; }
  },
}));
vi.mock("agents", () => ({ callable: () => () => {} }));
vi.mock("../../agents/models", () => ({ fastModel: () => ({ modelId: "placeholder" }), selectModelProfile: doubles.select }));
vi.mock("../../agents/modelProfiles", () => ({ getModelCatalog: doubles.catalog }));
vi.mock("../../agents/clefRouter", () => ({ resolveClefRoute: doubles.decide }));

import { ResearchWorkspace } from "../ResearchWorkspace";

const profiles = [
  { id: "workers-flash", role: "fast", provider: "workers-ai", modelId: "flash-test", configured: true, label: "Flash", availability: "configured-unverified" },
  { id: "clef", role: "decision", provider: "workers-ai", modelId: "clef-test", configured: true, label: "Clef", availability: "configured-unverified" },
  { id: "unavailable", role: "deep", provider: "test", modelId: "no-key", configured: false, label: "Unavailable", availability: "not-configured" },
];
function environment(records: unknown[] = []) {
  const all = vi.fn().mockResolvedValue({ results: records });
  const bind = vi.fn(() => ({ all }));
  const prepare = vi.fn(() => ({ bind }));
  const put = vi.fn().mockResolvedValue(undefined);
  const list = vi.fn().mockResolvedValue({ keys: [], list_complete: true });
  return { env: { LEDGER: { prepare }, CONFIG: { put, list } } as unknown as Env, prepare, bind, all, put, list };
}

beforeEach(() => {
  vi.clearAllMocks();
  doubles.catalog.mockReturnValue({ profiles });
  doubles.select.mockResolvedValue({ model: { modelId: "flash-test" }, provider: "workers-ai", modelId: "flash-test" });
  doubles.decide.mockImplementation(async (_env, input) => ({ mode: "manual", reason: "explicit-profile", profileId: input.profileId === "auto" ? input.defaultProfileId : input.profileId }));
});

describe("workspace boundaries", () => {
  it("bounds names and rejects namespace/path traversal", () => {
    for (const id of ["../other", "Research", "a/b", "a%2fb", "x".repeat(65), ""]) expect(conversationIdSchema.safeParse(id).success).toBe(false);
    expect(conversationIdSchema.parse("research-123")).toBe("research-123");
    expect(settingsSchema.safeParse({ title: "name\nsecond", profile: "workers-flash" }).success).toBe(false);
    expect(settingsSchema.safeParse({ title: "x".repeat(81), profile: "workers-flash" }).success).toBe(false);
  });
  it("rejects model discovery, decision models, and unconfigured providers as chat choices", () => {
    for (const id of ["clef", "unavailable", "arbitrary-provider"]) expect(() => validateChatProfile(profiles, id)).toThrow();
    expect(validateChatProfile(profiles, "workers-flash").modelId).toBe("flash-test");
  });
  it("rejects direct client state changes", () => {
    expect(() => validateWorkspaceStateChange({ id: "browser" })).toThrow();
    expect(() => validateWorkspaceStateChange("server")).not.toThrow();
  });
  it("blocks executable, data, protocol-relative, and backslash URLs", () => {
    for (const href of ["javascript:alert(1)", "data:text/html,hi", "//evil.test", "/\\evil.test", "http://example.com"]) expect(safeEvidenceHref(href)).toBeNull();
    expect(safeEvidenceHref("/live")).toBe("/live");
    expect(safeEvidenceHref("https://library.lupine.science/#/read/research-index")).toContain("library.lupine.science");
  });
});

describe("bounded read-only evidence", () => {
  it("uses allowlisted SELECTs and escapes literal search wildcards", async () => {
    const db = environment([{ id: "saved-1" }]);
    const result = await readWorkspaceEvidence(db.env, { collection: "hypotheses", query: "50%_' OR 1=1 --", limit: 3 });
    expect(db.prepare).toHaveBeenCalledWith(EVIDENCE_SQL.hypotheses);
    expect(db.bind).toHaveBeenCalledWith("%50\\%\\_' OR 1=1 --%", 3);
    expect(result.records).toHaveLength(1);
    expect(result.note).toContain("does not prove");
    for (const sql of Object.values(EVIDENCE_SQL)) { expect(sql.startsWith("SELECT ")).toBe(true); expect(sql).toContain("LIMIT ?"); expect(sql).toContain("substr("); }
  });
  it("rejects oversized reads, unknown sources and arbitrary SQL before touching D1", async () => {
    const db = environment();
    for (const input of [
      { collection: "papers", limit: 100 }, { collection: "secrets" },
      { collection: "activity", query: "x".repeat(161) }, { collection: "papers", sql: "DELETE FROM papers" },
    ]) await expect(readWorkspaceEvidence(db.env, input)).rejects.toThrow();
    expect(db.prepare).not.toHaveBeenCalled();
  });
  it("caps rows even if a binding returns too many and uses the canonical Library", async () => {
    const db = environment(Array.from({ length: 20 }, (_, i) => ({ doi: String(i) })));
    const result = await readWorkspaceEvidence(db.env, { collection: "papers", limit: 2 });
    expect(result.records).toHaveLength(2);
    expect(result.source).toBe("https://library.lupine.science/#/read/research-index");
  });
});

describe("ResearchWorkspace", () => {
  it("loads metadata and changes settings without model calls", async () => {
    const { env, put } = environment();
    const workspace = new ResearchWorkspace({} as DurableObjectState, env);
    const initial = await workspace.getWorkspace();
    expect(initial.state.profile).toBe("workers-flash");
    expect(initial.state.modelId).toBe("flash-test");
    expect(put).not.toHaveBeenCalled();
    await workspace.updateWorkspace({ title: "OMol evidence", profile: "workers-flash" });
    expect((await workspace.getWorkspace()).state.title).toBe("OMol evidence");
    expect(put).toHaveBeenCalledWith("workspace:conversation:research", expect.any(String), expect.objectContaining({ metadata: expect.objectContaining({ title: "OMol evidence" }) }));
    expect(doubles.select).not.toHaveBeenCalled();
    expect(doubles.decide).not.toHaveBeenCalled();
  });
  it("keeps decision models out of the generation setting", async () => {
    const { env } = environment();
    const workspace = new ResearchWorkspace({} as DurableObjectState, env);
    await expect(workspace.updateWorkspace({ title: "Bad profile", profile: "clef" })).rejects.toThrow();
    expect(workspace.getConfig()).toBeUndefined();
  });
  it("keeps metadata and model choices readable after the selected provider becomes unavailable", async () => {
    const { env } = environment();
    const workspace = new ResearchWorkspace({} as DurableObjectState, env);
    await workspace.updateWorkspace({ title: "Recoverable", profile: "workers-flash" });
    doubles.catalog.mockReturnValue({ profiles: profiles.map((profile) => ({ ...profile, configured: false })) });
    const info = await workspace.getWorkspace();
    expect(info.state.title).toBe("Recoverable");
    expect(info.catalog.profiles[0].configured).toBe(false);
    await expect(workspace.updateWorkspace({ title: "Recoverable", profile: "workers-flash" })).rejects.toThrow();
    doubles.catalog.mockReturnValue({ profiles: [] });
    expect((await workspace.getWorkspace()).state.profile).toBe("workers-flash");
    expect((await workspace.getWorkspace()).state.modelId).toBeNull();
  });
  it("overrides spoofed evidence tools and exposes only bounded reads", async () => {
    const { env, prepare } = environment();
    const workspace = new ResearchWorkspace({} as DurableObjectState, env);
    const malicious = vi.fn();
    const cfg = await workspace.beforeTurn({ messages: [{ role: "user", content: "Review my evidence" }], tools: { read_evidence: { execute: malicious } } } as never);
    expect(cfg.activeTools).toEqual(["read_evidence"]);
    expect(cfg.maxSteps).toBe(6);
    await cfg.tools.read_evidence.execute!({ collection: "papers", query: "", limit: 1 }, {} as never);
    expect(prepare).toHaveBeenCalled(); expect(malicious).not.toHaveBeenCalled();
    for (const toolName of ["write", "bash", "execute", "delete", "dispatch", "update_context"]) expect(workspace.beforeToolCall({ toolName } as never).action).toBe("block");
  });
  it("passes only the final bounded user prompt into optional routing and exposes provenance", async () => {
    const { env } = environment();
    const workspace = new ResearchWorkspace({} as DurableObjectState, env);
    await workspace.updateWorkspace({ title: "Routed", profile: "auto" });
    await workspace.beforeTurn({ messages: [{ role: "system", content: "private system context" }, { role: "user", content: "x".repeat(5000) }] } as never);
    // The leaf owns truncation, so its provenance can accurately report it.
    expect(doubles.decide).toHaveBeenCalledWith(env, { profileId: "auto", prompt: "x".repeat(5000), defaultProfileId: "workers-flash" });
    expect(doubles.select).toHaveBeenCalledWith(env, "workers-flash");
    expect((await workspace.getWorkspace()).state.routing?.profileId).toBe("workers-flash");
  });
  it("coalesces directory writes and preserves settings when the later KV write fails", async () => {
    vi.useFakeTimers();
    const warning = vi.spyOn(console, "warn").mockImplementation(() => {});
    try {
      const { env, put } = environment();
      put.mockResolvedValueOnce(undefined).mockRejectedValueOnce(new Error("429 limited"));
      const workspace = new ResearchWorkspace({} as DurableObjectState, env);
      await workspace.updateWorkspace({ title: "First", profile: "workers-flash" });
      await workspace.updateWorkspace({ title: "Second", profile: "workers-flash" });
      await workspace.updateWorkspace({ title: "Latest", profile: "workers-flash" });
      expect(put).toHaveBeenCalledTimes(1);
      expect((await workspace.getWorkspace()).state.title).toBe("Latest");
      await vi.runAllTimersAsync();
      expect(put).toHaveBeenCalledTimes(2);
      expect((await workspace.getWorkspace()).state.title).toBe("Latest");
      expect(warning).toHaveBeenCalledOnce();
    } finally { warning.mockRestore(); vi.useRealTimers(); }
  });
});

describe("cross-device directory", () => {
  it("lists bounded safe metadata and preserves the truncation signal", async () => {
    const { env, list } = environment();
    list.mockResolvedValue({ list_complete: false, keys: [
      { metadata: { id: "a", title: "Older", updatedAt: "2026-10-01" } },
      { metadata: { id: "b", title: "Newer", updatedAt: "2026-10-05" } },
      { metadata: { id: "../other", title: "Invalid", updatedAt: "2026-10-05" } },
    ] });
    const result = await listWorkspaceConversations(env);
    expect(list).toHaveBeenCalledWith({ prefix: "workspace:conversation:", limit: 100 });
    expect(result.conversations.map((c) => c.id)).toEqual(["b", "a"]);
    expect(result.truncated).toBe(true);
  });
});
