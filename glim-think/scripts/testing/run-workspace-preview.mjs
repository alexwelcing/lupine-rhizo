import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";
import { resolve } from "node:path";

const root = fileURLToPath(new URL("../../", import.meta.url));
const env = { ...process.env, WRANGLER_SEND_METRICS: "false", CLOUDFLARE_LOAD_DEV_VARS_FROM_DOT_ENV: "false", WRANGLER_LOG_PATH: resolve(root, ".wrangler/workspace-preview/logs") };
for (const key of Object.keys(env)) if (/^(CLOUDFLARE_(API|ACCOUNT)|CF_)/.test(key)) delete env[key];
const config = resolve(root, "scripts/testing/wrangler.workspace-preview.toml");
const state = resolve(root, ".wrangler/workspace-preview");
function run(args) {
  return new Promise((resolve, reject) => {
    const child = spawn(process.execPath, args, { cwd: root, env, stdio: "inherit" });
    const stop = () => child.kill("SIGTERM");
    process.once("SIGINT", stop); process.once("SIGTERM", stop);
    child.once("error", reject);
    child.once("exit", (code) => { process.off("SIGINT", stop); process.off("SIGTERM", stop); code === 0 ? resolve() : reject(new Error(`Preview subprocess exited ${code}`)); });
  });
}
await run(["scripts/build-workspace.mjs"]);
const wrangler = resolve(root, "node_modules/wrangler/bin/wrangler.js");
await run([wrangler, "d1", "execute", "LEDGER", "--config", config, "--local", "--persist-to", state, "--file", resolve(root, "scripts/testing/workspace-preview.sql")]);
await run([wrangler, "dev", "--config", config, "--local", "--persist-to", state]);
