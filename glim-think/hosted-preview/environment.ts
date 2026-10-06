import type { Env } from "../src/types";

export type PreviewEnv = Pick<Env, "AI" | "CONFIG" | "LEDGER" | "RESEARCH_WORKSPACE" |
  "CF_ACCESS_TEAM_DOMAIN" | "CF_ACCESS_AUD" | "ADMIN_EMAIL">;

/** Discard accidental extra bindings, auth bypass flags, keys and telemetry. */
export function workspacePreviewEnv(env: PreviewEnv): Env {
  return {
    AI: env.AI, CONFIG: env.CONFIG, LEDGER: env.LEDGER, RESEARCH_WORKSPACE: env.RESEARCH_WORKSPACE,
    CF_ACCESS_TEAM_DOMAIN: env.CF_ACCESS_TEAM_DOMAIN,
    CF_ACCESS_AUD: env.CF_ACCESS_AUD,
    ADMIN_EMAIL: env.ADMIN_EMAIL,
    // Reviewed private-preview policy; no caller-supplied provider or routing overrides.
    CLEF_ROUTER_MODE: "auto",
    CLEF_ROUTER_TASK_PROFILES: JSON.stringify({ fast: "workers-flash", deep: "workers-deep", code: "workers-deep", research: "workers-deep" }),
    CLEF_ROUTER_MIN_CONFIDENCE: "0.7",
    CLEF_ROUTER_MIN_MARGIN: "0.15",
    CLEF_ROUTER_TIMEOUT_MS: "1500",
  } as Env;
}
