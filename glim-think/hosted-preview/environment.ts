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
    CLEF_ROUTER_MODE: "disabled",
  } as Env;
}
