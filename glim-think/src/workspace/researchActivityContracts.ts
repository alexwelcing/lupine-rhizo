import { z } from "zod";

export const PUBLIC_ACTIVITY_SCHEMA = "lupine.public_research_activity.v1" as const;
export const PUBLIC_ACTIVITY_FEED_SCHEMA = "lupine.public_research_activity_feed.v1" as const;
export const PUBLIC_ACTIVITY_MAX_BYTES = 16_384;
export const PUBLIC_ACTIVITY_DEFAULT_LIMIT = 20;
export const PUBLIC_ACTIVITY_MAX_LIMIT = 50;

// This is a reviewed publication boundary, not a sanitizer for private packets.
// Unknown fields are rejected. These additional checks prevent common accidental
// disclosures; an operator must still review every sentence before importing it.
const PRIVATE_TEXT = /(?:[\x00-\x1f\x7f<>]|[A-Za-z][A-Za-z0-9+.-]*:\/\/|(?:^|\s|["'(])(?:\/(?:Users|home|private|tmp|var|mnt|workspace)\/|~\/|[A-Za-z]:[\\/]|\\\\)|[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}|\b(?:awphone|aledev|hermitage)\b)/i;
const CREDENTIAL = /(?:\bBearer\s+\S+|\b(?:sk-(?:proj-)?|ghp_|gho_|github_pat_|AIza)[A-Za-z0-9_-]{12,}|-----BEGIN [A-Z ]*PRIVATE KEY-----|\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,})/i;
const SENSITIVE_QUERY = /(?:token|key|secret|signature|credential|authorization|password|session|email|auth|jwt)/i;
const REPOSITORIES = new Set(["lupine", "lupine-rhizo", "lupine-ledger"]);

export function isPublicText(value: string): boolean {
  return value === value.trim() && !PRIVATE_TEXT.test(value) && !CREDENTIAL.test(value) &&
    !/(?:\b\d{1,3}(?:\.\d{1,3}){3}\b|\b[A-Za-z0-9.-]+\.ts\.net\b|(?:^|\s|["'(])(?:\.{1,2}\/|\/(?:[^\s/]+\/)+|(?:outputs|work|data|evidence|tools)\/)|(?:[^\s/]+\/){2,}[^\s/]+)/i.test(value);
}

/** Public URLs only. No fetching, credentials, device addresses or signed links. */
export function isPublicSourceUrl(value: string): boolean {
  try {
    if (value !== value.trim() || /[\s\\\x00-\x1f\x7f]/.test(value) || CREDENTIAL.test(value)) return false;
    const url = new URL(value);
    const host = url.hostname.toLowerCase();
    if (url.protocol !== "https:" || url.username || url.password || url.port || !host.includes(".") ||
        /[\[\]:]/.test(host) || /^\d+(?:\.\d+)*$/.test(host) ||
        /(?:^|\.)(?:localhost|local|internal|test|invalid|example|onion)$/.test(host) ||
        /(?:^|\.)(?:nip\.io|sslip\.io|xip\.io|localtest\.me|lvh\.me)$/.test(host) ||
        /(?:^|\.)\d{1,3}(?:\.\d{1,3}){3}(?:\.|$)/.test(host) ||
        host.endsWith(".ts.net") || host.endsWith(".localdomain") || host.endsWith(".home.arpa") || host.endsWith(".")) return false;
    let decoded = value;
    for (let i = 0; i < 2; i++) decoded = decodeURIComponent(decoded);
    let decodedPath = url.pathname;
    for (let i = 0; i < 2; i++) decodedPath = decodeURIComponent(decodedPath);
    if (/[\\\x00-\x1f\x7f]/.test(decoded) || CREDENTIAL.test(decoded) || /(?:\/(?:Users|home|private|tmp|var|mnt|workspace)\/|[A-Za-z]:[\\/])/i.test(decodedPath) || /\b(?:awphone|aledev|hermitage)\b/i.test(decoded)) return false;
    for (const [key, content] of url.searchParams) {
      if (SENSITIVE_QUERY.test(key) || CREDENTIAL.test(content) || /(?:[a-z][a-z0-9+.-]*:\/\/|@)/i.test(content)) return false;
    }
    return !SENSITIVE_QUERY.test(url.hash) && !/@/.test(decoded);
  } catch { return false; }
}

export function isRepositoryUrl(value: string, release = false): boolean {
  if (!isPublicSourceUrl(value)) return false;
  const url = new URL(value);
  const pieces = url.pathname.split("/").filter(Boolean);
  return url.hostname === "github.com" && pieces[0] === "alexwelcing" && REPOSITORIES.has(pieces[1] ?? "") &&
    !url.search && (!release || pieces[2] === "releases");
}

const text = (max: number) => z.string().min(1).max(max).refine(isPublicText, "Use reviewed public text without private identifiers, paths or credentials");
export const publicActivityIdSchema = z.string().regex(/^[a-z0-9][a-z0-9._-]{0,95}$/).refine(isPublicText);
const timestamp = z.string().regex(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/)
  .refine(value => Number.isFinite(Date.parse(value)) && new Date(value).toISOString() === value, "Use an actual UTC timestamp with milliseconds");
const source = z.strictObject({ label: text(100), url: z.string().max(1024).refine(isPublicSourceUrl, "Use a public HTTPS source") });
const repository = source.extend({ url: z.string().max(1024).refine(value => isRepositoryUrl(value), "Use an approved public repository") });
const release = source.extend({ url: z.string().max(1024).refine(value => isRepositoryUrl(value, true), "Use an approved public release") });
const count = z.number().int().min(0).max(1_000_000_000);

export const publicResearchActivitySchema = z.strictObject({
  schema: z.literal(PUBLIC_ACTIVITY_SCHEMA),
  id: publicActivityIdSchema,
  activityId: publicActivityIdSchema,
  evidenceKind: z.enum(["archived_analysis", "research_cycle"]),
  state: z.enum(["planned", "running", "completed", "failed", "blocked"]),
  verification: z.enum(["pending", "arithmetic_checked", "source_checked"]),
  title: text(160),
  summary: text(1200),
  observedAt: timestamp,
  reviewedAt: timestamp,
  datasets: z.array(z.strictObject({ name: text(120), configurations: count, groups: count.optional(), atoms: count.optional() })).max(8),
  findings: z.array(text(600)).max(8),
  limitations: z.array(text(600)).min(1).max(8),
  nextStep: text(600),
  sources: z.array(source).max(12),
  hashes: z.array(z.strictObject({ label: text(100), sha256: z.string().regex(/^[a-f0-9]{64}$/) })).max(12),
  repositoryLinks: z.array(repository).max(3),
  releaseLinks: z.array(release).max(6),
  supersedes: publicActivityIdSchema.nullable(),
  correctionReason: text(600).nullable(),
}).superRefine((value, ctx) => {
  if (value.reviewedAt < value.observedAt) ctx.addIssue({ code: "custom", message: "Review cannot precede observation" });
  if (value.supersedes === value.id) ctx.addIssue({ code: "custom", message: "A record cannot supersede itself" });
  if (!value.supersedes && value.correctionReason !== null) ctx.addIssue({ code: "custom", message: "A correction requires a prior record" });
  if (value.verification !== "pending" && value.hashes.length === 0 && value.sources.length === 0) ctx.addIssue({ code: "custom", message: "Checked evidence requires a public reference" });
});
export type PublicResearchActivity = z.infer<typeof publicResearchActivitySchema>;
export interface PublicResearchActivityFeed {
  schema: typeof PUBLIC_ACTIVITY_FEED_SCHEMA;
  items: PublicResearchActivity[];
  truncated: boolean;
}

export function decodePublicResearchActivity(value: unknown, now = Date.now()): PublicResearchActivity {
  const record = publicResearchActivitySchema.parse(value);
  if (Date.parse(record.reviewedAt) > now + 60_000) throw new Error("Review time is in the future");
  if (new TextEncoder().encode(JSON.stringify(record)).length > PUBLIC_ACTIVITY_MAX_BYTES) throw new Error("Public activity is too large");
  return record;
}

export async function publicActivitySha256(value: string): Promise<string> {
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(value));
  return Array.from(new Uint8Array(digest), byte => byte.toString(16).padStart(2, "0")).join("");
}
