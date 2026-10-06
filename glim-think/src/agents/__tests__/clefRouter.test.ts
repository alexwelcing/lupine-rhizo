import { afterEach, describe, expect, it, vi } from "vitest";
import type { Env } from "../../types";
import { CLEF_DECISION_MODEL } from "../modelProfiles";
import { CLEF_ROUTER_CONTEXT_LIMIT, resolveClefRoute } from "../clefRouter";
import offlineCases from "../../../evals/__datasets__/clef-routing.json";

const mapping = JSON.stringify({ fast: "fast", deep: "workers-deep", code: "openai", research: "workers-deep" });
function response(overrides: Record<string, unknown> = {}) {
  return { model: "clef-flash", usage: { input_tokens: 100, output_tokens: 0 }, answers: { route: {
    type: "choice", choice: "code", probabilities: { fast: 0.05, deep: 0.1, code: 0.8, research: 0.05 }, confidence: 0.9,
    ...overrides,
  } } };
}
function setup(overrides: Partial<Env> = {}) {
  const run = vi.fn<(model: string, input: unknown, options: { signal: AbortSignal }) => Promise<unknown>>()
    .mockResolvedValue(response());
  const env = { AI: { run }, OPENAI_API_KEY: "test-configured", CLEF_ROUTER_MODE: "auto",
    CLEF_ROUTER_TASK_PROFILES: mapping, ...overrides } as unknown as Env;
  return { env, run };
}
afterEach(() => { vi.useRealTimers(); vi.restoreAllMocks(); });

describe("optional Clef routing", () => {
  it("defaults disabled with no classifier call and supports the workspace default", async () => {
    const { env, run } = setup({ CLEF_ROUTER_MODE: undefined });
    expect(await resolveClefRoute(env, { prompt: "Fix a bug", defaultProfileId: "workers-flash" }))
      .toEqual({ mode: "disabled", profileId: "workers-flash", reason: "router-disabled", source: "configured-default" });
    expect(run).not.toHaveBeenCalled();
  });

  it("lets a manual configured generation profile win before classifier or fallback configuration", async () => {
    const { env, run } = setup({ CLEF_ROUTER_TASK_PROFILES: "invalid", CLEF_ROUTER_MIN_CONFIDENCE: "NaN" });
    expect(await resolveClefRoute(env, { profileId: "openai", prompt: "Research this", defaultProfileId: "invalid" }))
      .toEqual({ mode: "manual", profileId: "openai", reason: "manual-profile", source: "manual" });
    expect(run).not.toHaveBeenCalled();
  });

  it.each(["clef", "unknown", "minimax", "@cf/cloudflare/clef-flash"])("rejects manual %s without classifying", async (profileId) => {
    const { env, run } = setup();
    await expect(resolveClefRoute(env, { profileId, prompt: "Hello" })).rejects.toThrow("manual profile is unavailable");
    expect(run).not.toHaveBeenCalled();
  });

  it("rejects decision models hidden by generation profile overrides", async () => {
    const { env, run } = setup({ WORKERS_AI_MODEL: CLEF_DECISION_MODEL });
    await expect(resolveClefRoute(env, { profileId: "fast", prompt: "Hello" })).rejects.toThrow();
    await expect(resolveClefRoute(env, { prompt: "Hello" })).rejects.toThrow("default generation profile is unavailable");
    expect(run).not.toHaveBeenCalled();
  });

  it("excludes a Clef override from an otherwise allowlisted deep profile", async () => {
    const { env, run } = setup({ WORKERS_AI_DEEP_MODEL: "@cf/cloudflare/clef" });
    expect(await resolveClefRoute(env, { prompt: "Compare evidence" }))
      .toMatchObject({ profileId: "fast", reason: "task-profiles-unavailable" });
    expect(run).not.toHaveBeenCalled();
  });

  it("keeps an explicit configured fallback when the classifier binding is absent", async () => {
    const { env } = setup({ AI: undefined, CLEF_ROUTER_TASK_PROFILES: '{"code":"openai"}' });
    expect(await resolveClefRoute(env, { prompt: "Debug", defaultProfileId: "openai" }))
      .toMatchObject({ profileId: "openai", reason: "classifier-unavailable" });
  });

  it("uses the official choice probabilities schema to select only an allowlisted profile", async () => {
    const { env, run } = setup();
    const decision = await resolveClefRoute(env, { profileId: "auto", prompt: "Debug my code" });
    expect(decision).toMatchObject({ mode: "auto", profileId: "openai", task: "code", confidence: 0.9,
      reason: "classified-task", source: "clef-flash", classifierModel: CLEF_DECISION_MODEL,
      probabilities: { fast: 0.05, deep: 0.1, code: 0.8, research: 0.05 } });
    expect(decision.margin).toBeCloseTo(0.7);
    expect(run).toHaveBeenCalledTimes(1);
    expect(run.mock.calls[0][0]).toBe(CLEF_DECISION_MODEL);
    expect(run.mock.calls[0][1]).toMatchObject({ model: "clef-flash", state: { user_request: "Debug my code" },
      questions: { route: { type: "choice", criteria: { fast: expect.any(String), deep: expect.any(String),
        code: expect.any(String), research: expect.any(String) } } } });
  });

  it("keeps the default in shadow mode while returning bounded evaluation evidence", async () => {
    const { env } = setup({ CLEF_ROUTER_MODE: "shadow" });
    expect(await resolveClefRoute(env, { prompt: "Debug", defaultProfileId: "workers-flash" }))
      .toMatchObject({ mode: "shadow", profileId: "workers-flash", suggestedProfileId: "openai",
        source: "configured-default", task: "code", confidence: 0.9 });
  });

  it("sends only bounded supplied text and never returns or logs raw text or provider errors", async () => {
    const { env, run } = setup();
    const log = vi.spyOn(console, "log");
    const warn = vi.spyOn(console, "warn");
    const error = vi.spyOn(console, "error");
    const prompt = "x".repeat(CLEF_ROUTER_CONTEXT_LIMIT) + "PRIVATE_TAIL";
    const decision = await resolveClefRoute(env, { prompt });
    expect(decision.contextTruncated).toBe(true);
    expect((run.mock.calls[0][1] as { state: { user_request: string } }).state.user_request)
      .toBe("x".repeat(CLEF_ROUTER_CONTEXT_LIMIT));
    expect(JSON.stringify(run.mock.calls[0][1])).not.toContain("test-configured");
    expect(JSON.stringify(decision)).not.toContain("PRIVATE_TAIL");
    run.mockRejectedValueOnce(new Error("PRIVATE_PROVIDER_ERROR"));
    expect(await resolveClefRoute(env, { prompt: "Hello" })).toMatchObject({ reason: "classifier-unavailable", profileId: "fast" });
    expect(log).not.toHaveBeenCalled();
    expect(warn).not.toHaveBeenCalled();
    expect(error).not.toHaveBeenCalled();
  });

  it.each([
    undefined, "{}", "not json", '{"fast":"openai"}', '{"code":"workers-flash"}',
    '{"code":"clef"}', '{"code":"unknown"}', '{"code":"minimax"}', '{"jobs":"openai"}',
  ])("does not call the classifier for absent or invalid task allowlist %s", async (raw) => {
    const { env, run } = setup({ CLEF_ROUTER_TASK_PROFILES: raw });
    expect(await resolveClefRoute(env, { prompt: "Debug" })).toMatchObject({ reason: "task-profiles-unavailable", profileId: "fast" });
    expect(run).not.toHaveBeenCalled();
  });

  it("falls back when a valid classification has no mapped profile", async () => {
    const { env } = setup({ CLEF_ROUTER_TASK_PROFILES: '{"fast":"fast"}' });
    expect(await resolveClefRoute(env, { prompt: "Debug" })).toMatchObject({ reason: "task-profile-unmapped", profileId: "fast", task: "code" });
  });

  it.each([
    { CLEF_ROUTER_MIN_CONFIDENCE: "NaN" }, { CLEF_ROUTER_MIN_CONFIDENCE: "Infinity" },
    { CLEF_ROUTER_MIN_CONFIDENCE: "1.1" }, { CLEF_ROUTER_MIN_MARGIN: "-1" },
    { CLEF_ROUTER_TIMEOUT_MS: "99" }, { CLEF_ROUTER_TIMEOUT_MS: "3001" },
  ])("fails closed on non-finite or out-of-range limits %j", async (config) => {
    const { env, run } = setup(config);
    expect(await resolveClefRoute(env, { prompt: "Debug" })).toMatchObject({ reason: "invalid-router-limits" });
    expect(run).not.toHaveBeenCalled();
  });

  it.each([
    { type: "noul" }, { choice: "run-job" }, { choice: "fast" }, { confidence: NaN },
    { confidence: Infinity }, { confidence: -0.1 }, { confidence: 1.1 }, { confidence: "0.9" },
    { probabilities: { fast: 0.05, deep: 0.1, code: Infinity, research: 0.05 } },
    { probabilities: { fast: 0.05, deep: 0.1, code: NaN, research: 0.05 } },
    { probabilities: { fast: 0.05, deep: 0.1, code: 1.1, research: 0.05 } },
    { probabilities: { fast: -0.05, deep: 0.1, code: 0.9, research: 0.05 } },
    { probabilities: { fast: 0.05, deep: 0.1, code: 0.8 } },
    { probabilities: { fast: 0.05, deep: 0.1, code: 0.8, research: 0.05, shell: 0 } },
    { probabilities: { fast: 0.1, deep: 0.1, code: 0.9, research: 0.1 } },
  ])("rejects malformed, inconsistent, or non-finite choice evidence %j", async (override) => {
    const { env, run } = setup();
    run.mockResolvedValueOnce(response(override));
    expect(await resolveClefRoute(env, { prompt: "Debug" })).toMatchObject({ reason: "invalid-classifier-response", profileId: "fast" });
  });

  it("requires confidence and a positive separation between the first two options", async () => {
    const { env, run } = setup();
    run.mockResolvedValueOnce(response({ confidence: 0.69 }));
    expect(await resolveClefRoute(env, { prompt: "Debug" })).toMatchObject({ reason: "low-confidence" });
    run.mockResolvedValueOnce(response({ probabilities: { fast: 0.1, deep: 0.39, code: 0.41, research: 0.1 } }));
    expect(await resolveClefRoute(env, { prompt: "Debug" })).toMatchObject({ reason: "ambiguous-task" });
    env.CLEF_ROUTER_MIN_MARGIN = "0";
    run.mockResolvedValueOnce(response({ probabilities: { fast: 0.1, deep: 0.4, code: 0.4, research: 0.1 } }));
    expect(await resolveClefRoute(env, { prompt: "Debug" })).toMatchObject({ reason: "ambiguous-task" });
  });

  it.each([null, {}, { ...response(), model: ["clef-flash"] }, { ...response(), model: "some-other-model" }])(
    "rejects missing or wrongly typed top-level response identity %j", async (value) => {
      const { env, run } = setup();
      run.mockResolvedValueOnce(value);
      expect(await resolveClefRoute(env, { prompt: "Debug" })).toMatchObject({ reason: "invalid-classifier-response" });
    },
  );

  it.each(["response", "stream"])("cancels an unexpected %s body without waiting for cancellation", async (kind) => {
    vi.useFakeTimers();
    const { env, run } = setup();
    const cancel = vi.fn(() => new Promise<void>(() => {}));
    const stream = new ReadableStream<Uint8Array>({ cancel });
    run.mockResolvedValueOnce(kind === "response" ? new Response(stream) : stream);
    expect(await resolveClefRoute(env, { prompt: "Debug" })).toMatchObject({ reason: "invalid-classifier-response", profileId: "fast" });
    expect(cancel).toHaveBeenCalledTimes(1);
    expect(run.mock.calls[0][2].signal.aborted).toBe(true);
    expect(vi.getTimerCount()).toBe(0);
  });

  it("cancels a late response body after the deadline and handles cancellation rejection", async () => {
    vi.useFakeTimers();
    const { env, run } = setup({ CLEF_ROUTER_TIMEOUT_MS: "100" });
    let resolveLate!: (value: unknown) => void;
    run.mockImplementationOnce(() => new Promise((resolve) => { resolveLate = resolve; }));
    const pending = resolveClefRoute(env, { prompt: "Debug" });
    await vi.advanceTimersByTimeAsync(100);
    expect(await pending).toMatchObject({ reason: "classifier-timeout" });
    const cancel = vi.fn(() => Promise.reject(new Error("cancellation failed")));
    resolveLate(new Response(new ReadableStream<Uint8Array>({ cancel })));
    await vi.advanceTimersByTimeAsync(0);
    expect(cancel).toHaveBeenCalledTimes(1);
    expect(run).toHaveBeenCalledTimes(1);
  });

  it("bounds the wait, aborts once, never retries, and safely ignores a late rejection", async () => {
    vi.useFakeTimers();
    const { env, run } = setup({ CLEF_ROUTER_TIMEOUT_MS: "100" });
    let rejectLate!: (error: Error) => void;
    run.mockImplementationOnce(() => new Promise((_, reject) => { rejectLate = reject; }));
    const pending = resolveClefRoute(env, { prompt: "Debug", defaultProfileId: "workers-flash" });
    await vi.advanceTimersByTimeAsync(100);
    expect(await pending).toMatchObject({ mode: "fallback", reason: "classifier-timeout", profileId: "workers-flash" });
    expect(run.mock.calls[0][2].signal.aborted).toBe(true);
    rejectLate(new Error("late provider response"));
    await vi.advanceTimersByTimeAsync(5_000);
    expect(run).toHaveBeenCalledTimes(1);
    expect(vi.getTimerCount()).toBe(0);
  });

  it("clears the deadline on success and avoids calls for empty input", async () => {
    vi.useFakeTimers();
    const { env, run } = setup();
    expect(await resolveClefRoute(env, { prompt: " " })).toMatchObject({ reason: "empty-request" });
    expect(run).not.toHaveBeenCalled();
    await resolveClefRoute(env, { prompt: "Debug" });
    expect(vi.getTimerCount()).toBe(0);
    expect(run.mock.calls[0][2].signal.aborted).toBe(false);
  });

  it("keeps the offline review cases uniquely named, bounded, and balanced across tasks", () => {
    expect(new Set(offlineCases.cases.map((item) => item.id)).size).toBe(12);
    for (const task of ["fast", "deep", "code", "research"]) {
      expect(offlineCases.cases.filter((item) => item.expectedTask === task)).toHaveLength(3);
    }
    for (const item of offlineCases.cases) {
      expect(item.prompt.length).toBeGreaterThan(0);
      expect(item.prompt.length).toBeLessThanOrEqual(CLEF_ROUTER_CONTEXT_LIMIT);
      expect(item.rationale.length).toBeGreaterThan(0);
    }
    // This validates fixture shape only; it makes no claim about live accuracy.
  });
});
