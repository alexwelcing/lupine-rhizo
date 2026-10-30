import { z } from "zod";
import { decodePublicResearchActivity, isPublicSourceUrl, isPublicText, publicActivitySha256,
  publicResearchActivitySchema } from "./researchActivityContracts";

/** User-authorized automated publication policy. It validates the accepted
 * report's public projection, not scientific correctness or external review. */
export const DISCOVERY_PUBLICATION_POLICY = "accepted-discovery-public/v1" as const;
export const DISCOVERY_EVIDENCE_MAX_BYTES = 32_768;
export const DISCOVERY_ENVELOPE_MAX_BYTES = 65_536;
export const DISCOVERY_ROLES = ["evidence", "methods", "reviewer", "principal"] as const;
const sha = z.string().regex(/^[a-f0-9]{64}$/);
export const publicationIdSchema = z.string().regex(/^discovery-[a-f0-9]{64}$/);
const topicId = z.string().regex(/^topic-[a-f0-9]{64}$/);
const reference = z.string().regex(/^src-[a-f0-9]{64}$/);
const role = z.enum(DISCOVERY_ROLES);
/** One scientific package-family token, not a general path exception. Apply
 * only to discovery evidence checks; never change retained bytes or the older
 * activity-v1 publication contract. Prefix/suffix paths and extensions fail. */
export function isDiscoveryEvidenceText(value:string):boolean {
  return isPublicText(value.replace(/(?<![\p{L}\p{N}_.\/\\-])KOKKOS\/GPU\/OPENMP(?![\p{L}\p{N}_\/\\-]|\.[\p{L}\p{N}_])/gu,"KOKKOS_GPU_OPENMP"));
}
const text = (bytes: number) => z.string().min(1).max(bytes).refine(isDiscoveryEvidenceText)
  .refine(value => new TextEncoder().encode(value).length <= bytes);
const time = z.string().regex(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/)
  .refine(value => Number.isFinite(Date.parse(value)) && new Date(value).toISOString() === value);
const references = z.array(reference).min(1).max(3).refine(values => new Set(values).size === values.length);
export const publicDiscoveryReportSchema = z.strictObject({
  schema: z.literal("lupine-discovery-report/v1"), role, summary: text(1800),
  claims: z.array(z.strictObject({ statement: text(500), sourceReferences: references,
    kind: z.enum(["published-claim", "hypothesis"]) })).max(6),
  concepts: z.array(z.strictObject({ name: text(120), kind: z.enum(["material", "method", "property", "dataset", "software"]),
    sourceReferences: references })).max(6),
  assessments: z.array(z.strictObject({ targetRole: role, claimIndex: z.number().int().min(0).max(5),
    verdict: z.enum(["supports", "contradicts", "inconclusive"]), reason: text(350), sourceReferences: references })).max(3),
  questions: z.array(text(400)).max(3), queries: z.array(text(100)).max(3), disposition: z.enum(["advance", "wait", "reject"]),
});
export const discoveryEvidenceSchema = z.strictObject({
  schema: z.literal("lupine.public_discovery_report.v1"), policy: z.literal(DISCOVERY_PUBLICATION_POLICY),
  topic: z.strictObject({ id: topicId, question: text(800), parentTopicId: topicId.nullable(), parentPublicationId: publicationIdSchema.nullable(),
    parentQuestionIndex:z.number().int().min(0).max(2).nullable() }),
  report: publicDiscoveryReportSchema,
  sources: z.array(z.strictObject({ reference, title: text(500), url: z.string().max(1024).refine(isPublicSourceUrl), semanticSha256: sha })).min(1).max(3),
  priorReports: z.array(z.strictObject({ role, publicationId: publicationIdSchema })).max(3),
  provenance: z.strictObject({ provider: text(100), model: text(100), modelIdentity: z.literal("controller-reported"), completedAt: time,
    outputSha256: sha, receiptSha256: sha, archiveSha256: sha }),
  empiricalValidation: z.literal(false), externalPeerReviewed: z.literal(false), reviewBasis: z.literal("automated-contract-validation"),
});
export const discoveryPublicationSchema = z.strictObject({
  schema: z.literal("lupine.discovery_publication.v1"), policy: z.literal(DISCOVERY_PUBLICATION_POLICY),
  producer: z.literal("lupine-research-team-v02"), record: publicResearchActivitySchema, evidence: discoveryEvidenceSchema,
});
export type DiscoveryEvidence = z.infer<typeof discoveryEvidenceSchema>;
export type DiscoveryPublication = z.infer<typeof discoveryPublicationSchema>;
export interface DiscoveryPublicationAck {
  schema: "lupine.discovery_publication_ack.v1"; id: string; activityId: string;
  recordSha256: string; evidenceSha256: string; duplicate: boolean; knowledgeProjected: true;
}
export function canonicalPublicJson(value: unknown): string {
  if (value === null || typeof value !== "object") return JSON.stringify(value);
  if (Array.isArray(value)) return "[" + value.map(canonicalPublicJson).join(",") + "]";
  return "{" + Object.keys(value).sort().map(key => JSON.stringify(key) + ":" + canonicalPublicJson((value as Record<string, unknown>)[key])).join(",") + "}";
}
function plainData(value: unknown, depth = 0): void {
  if (depth > 20) throw Error("Invalid public data");
  if (typeof value === "string" && /(?:lev1:|\bdq-[a-f0-9]{40}\b|\brl-[a-f0-9]{40}\b|cc:rl-)/i.test(value)) throw Error("Private execution identity");
  if (value === null || typeof value === "boolean" || typeof value === "string" || typeof value === "number" && Number.isFinite(value)) return;
  if (typeof value !== "object" || !value || ![Object.prototype, Array.prototype].includes(Object.getPrototypeOf(value))) throw Error("Invalid public data");
  const entries = Object.entries(Object.getOwnPropertyDescriptors(value));
  if (entries.length > 100) throw Error("Invalid public data");
  for (const [key, descriptor] of entries) {
    if (!("value" in descriptor)) throw Error("Invalid public data");
    if (Array.isArray(value) && key === "length") continue;
    plainData(descriptor.value, depth + 1);
  }
}
export function decodeDiscoveryEvidence(value: unknown): DiscoveryEvidence {
  plainData(value);
  const evidence = discoveryEvidenceSchema.parse(value), report = evidence.report;
  const refs = new Set(evidence.sources.map(source => source.reference));
  const unique = (values: unknown[]) => new Set(values).size === values.length;
  if (evidence.sources.some(source => source.reference !== "src-" + source.semanticSha256) || refs.size !== evidence.sources.length ||
      [...report.claims, ...report.concepts, ...report.assessments].some(item => item.sourceReferences.some(ref => !refs.has(ref))) ||
      report.queries.length > report.questions.length || !unique(report.questions) || !unique(report.queries.map(query => query.toLowerCase())) ||
      !unique(report.concepts.map(concept => concept.kind + ":" + concept.name.replace(/\s+/g, " "))) ||
      !unique(report.assessments.map(item => item.targetRole + ":" + item.claimIndex)) ||
      report.queries.some(query => { const terms = query.split(/\s+/); return terms.length > 12 || terms.some(term => term.length > 40 || /^(and|or|not)$/i.test(term)); }) ||
      evidence.topic.parentTopicId === evidence.topic.id || evidence.topic.parentPublicationId && !evidence.topic.parentTopicId ||
      (evidence.topic.parentPublicationId===null)!==(evidence.topic.parentQuestionIndex===null)) throw Error("Invalid public report joins");
  const index = DISCOVERY_ROLES.indexOf(report.role);
  if (evidence.priorReports.length !== index || !unique(evidence.priorReports.map(item => item.publicationId)) ||
      evidence.priorReports.some((item, i) => item.role !== DISCOVERY_ROLES[i]) ||
      report.assessments.some(item => DISCOVERY_ROLES.indexOf(item.targetRole) >= index) ||
      new TextEncoder().encode(canonicalPublicJson(evidence)).length > DISCOVERY_EVIDENCE_MAX_BYTES) throw Error("Invalid public report lineage or size");
  return evidence;
}
export async function decodeDiscoveryPublication(value: unknown, now = Date.now()): Promise<DiscoveryPublication> {
  plainData(value);
  const parsed = discoveryPublicationSchema.parse(value);
  const record = decodePublicResearchActivity(parsed.record, now), evidence = decodeDiscoveryEvidence(parsed.evidence);
  const id = "discovery-" + evidence.provenance.archiveSha256;
  if (record.id !== id || record.activityId !== id || record.evidenceKind !== "research_cycle" || record.state !== "completed" ||
      record.verification !== "pending" || record.supersedes !== null || record.correctionReason !== null ||
      record.observedAt !== evidence.provenance.completedAt || evidence.priorReports.some(item => item.publicationId === id) || evidence.topic.parentPublicationId === id ||
      record.hashes.filter(item => item.label === "Public evidence").length !== 1 ||
      record.hashes.find(item => item.label === "Public evidence")?.sha256 !== await publicActivitySha256(canonicalPublicJson(evidence)) ||
      evidence.sources.some(source => !record.sources.some(item => item.url === source.url)) ||
      new TextEncoder().encode(canonicalPublicJson({ ...parsed, record, evidence })).length > DISCOVERY_ENVELOPE_MAX_BYTES) throw Error("Invalid publication join");
  return { ...parsed, record, evidence };
}
