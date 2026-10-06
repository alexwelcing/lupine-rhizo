export const PREVIEW_WORKER_NAME = "lupine-workspace-preview";

/** Only explicit preview inputs enter the build; never load production settings. */
export function readPreviewSettings(input: Record<string, string | undefined>) {
  const required = (key: string, pattern: RegExp) => {
    const value = input[key]?.trim();
    if (!value || !pattern.test(value)) throw new Error(`Set a valid ${key} for the isolated workspace preview.`);
    return value;
  };
  const team = required("PREVIEW_ACCESS_TEAM_DOMAIN", /^[a-z0-9-]+(?:\.cloudflareaccess\.com)?$/)
    .replace(/\.cloudflareaccess\.com$/, "");
  return {
    accountId: required("CLOUDFLARE_ACCOUNT_ID", /^[a-f0-9]{32}$/i),
    kvId: required("PREVIEW_CONFIG_KV_ID", /^[a-f0-9]{32}$/i),
    d1Id: required("PREVIEW_LEDGER_D1_ID", /^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/i),
    team,
    audience: required("PREVIEW_ACCESS_AUD", /^[a-zA-Z0-9_-]{16,256}$/),
    adminEmail: required("PREVIEW_ADMIN_EMAIL", /^[^\s@]+@[^\s@]+\.[^\s@]+$/).toLowerCase(),
  };
}
