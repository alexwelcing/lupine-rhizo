import { z } from "zod";
import { researchRunSchema, sha256, type ResearchRun } from "./researchRunContracts";

const text = z.string().trim().min(1).max(2000);
const id = z.string().regex(/^[A-Za-z0-9][A-Za-z0-9_.-]{0,95}$/);
const hash = z.string().regex(/^[a-f0-9]{64}$/);
/** Private, proposed task specification. A hash identifies supplied bytes, not verified science. */
export const comparisonContractSchema = z.strictObject({
  schemaVersion: z.literal(1), id, visibility: z.literal("private"), authorization: z.literal("proposed"),
  runId: id, proposalId: id, discoveryPacketSha256: hash,
  intent: z.enum(["confirmatory", "exploratory", "descriptive", "methodological"]),
  executionKind: z.enum(["source_audit", "exact_arithmetic", "simulation"]),
  findings: z.array(z.strictObject({ sourceId: text, sourceSha256: hash.nullable(), anchor: text,
    rowIds: z.array(id).max(24) })).min(1).max(8),
  evaluation: z.strictObject({ material: text, composition: text, phase: text, observable: text, unit: text,
    temperature: text.nullable(), referenceId: text.nullable(), protocol: text.nullable(), candidateSet: text }),
  arms: z.array(z.strictObject({ modelId: text, artifactSha256: hash.nullable(), intervention: text,
    fitExposure: text.nullable(), referenceId: text.nullable() })).min(2).max(8),
  unknowns: z.array(text).max(24), excludedScope: z.array(text).min(1).max(24),
  decisionRule: text, falsifier: text, stoppingRule: text,
});
export type ComparisonContract = z.infer<typeof comparisonContractSchema>;

export function canonicalComparisonJSON(value: unknown): string {
  if (Array.isArray(value)) return `[${value.map(canonicalComparisonJSON).join(",")}]`;
  if (value !== null && typeof value === "object") return "{" + Object.entries(value).sort(([a], [b]) => a < b ? -1 : a > b ? 1 : 0)
    .map(([key, item]) => `${JSON.stringify(key)}:${canonicalComparisonJSON(item)}`).join(",") + "}";
  return JSON.stringify(value);
}

/** Caller supplies a run already receipt-validated by getResearchRun/decodeResearchRun.
 * This pure preview has no environment, storage, provider or scheduling capability. */
export async function previewVerificationTask(savedRun: ResearchRun, input: unknown) {
  const run = researchRunSchema.parse(savedRun);
  const contract = comparisonContractSchema.parse(input);
  const discovery = run.stages[0];
  if (contract.runId !== run.id || discovery.result?.role !== "proposer" ||
      discovery.status !== "completed" || contract.discoveryPacketSha256 !== discovery.receipt?.resultSha256)
    throw new Error("Comparison does not bind to the saved discovery receipt");
  if (!discovery.result.proposals.some(proposal => proposal.id === contract.proposalId))
    throw new Error("Unknown proposal");
  const reference = contract.evaluation.referenceId;
  if (contract.arms.some(arm => arm.referenceId !== reference)) throw new Error("Mismatched task reference");
  if (new Set(contract.arms.map(arm => arm.modelId)).size !== contract.arms.length) throw new Error("Duplicate model identity");
  const blockers = [...contract.unknowns];
  for (const finding of contract.findings) {
    if (finding.sourceSha256 === null) blockers.push(`Missing source hash: ${finding.sourceId}`);
    if (!finding.rowIds.length) blockers.push(`Missing comparison row IDs: ${finding.sourceId}`);
  }
  for (const field of ["temperature", "referenceId", "protocol"] as const)
    if (contract.evaluation[field] === null) blockers.push(`Missing evaluation ${field}`);
  for (const arm of contract.arms) {
    if (arm.fitExposure === null) blockers.push(`Unknown fitting exposure: ${arm.modelId}`);
    if (contract.executionKind === "simulation" && arm.artifactSha256 === null) blockers.push(`Missing executable model hash: ${arm.modelId}`);
  }
  const decision = run.stages[2].result;
  if (decision?.role !== "adjudicator" || decision.selected_proposal_id !== contract.proposalId || decision.recommendation !== "investigate")
    blockers.push("No PI investigate recommendation for this proposal");
  const contractSha256 = await sha256(canonicalComparisonJSON(contract));
  return {
    schemaVersion: 1 as const, contract, contractSha256,
    status: blockers.length ? "needs_clarification" as const : "specified" as const,
    blockers: [...new Set(blockers)],
    taskPreview: { title: `Verify ${contract.evaluation.material}: ${contract.evaluation.observable}`,
      payload: { runId: run.id, proposalId: contract.proposalId, comparisonContractId: contract.id, comparisonContractSha256: contractSha256, comparisonContract: contract,
        executionKind: contract.executionKind, decisionRule: contract.decisionRule, falsifier: contract.falsifier,
        stoppingRule: contract.stoppingRule, excludedScope: contract.excludedScope } },
    execution: "not_started" as const, publication: "held" as const, visibility: "private" as const,
    scheduled: false as const, sourceVerification: "not_performed" as const,
    note: "Preview only. Contract completeness and receipt validity do not establish scientific accuracy or authorize execution. Claim updates require verified evidence through existing claim/publication gates.",
  };
}

/** Draft from saved proposal text only; unresolved fields are deliberately visible. */
export function draftComparisonContract(run: ResearchRun, proposalId: string): ComparisonContract {
  const discovery = run.stages[0];
  if (discovery.result?.role !== "proposer" || !discovery.receipt?.resultSha256) throw new Error("No saved discovery receipt");
  const proposal = discovery.result.proposals.find(item => item.id === proposalId);
  if (!proposal) throw new Error("Unknown proposal");
  return comparisonContractSchema.parse({ schemaVersion:1, id:"comparison-draft", visibility:"private", authorization:"proposed",
    runId:run.id, proposalId, discoveryPacketSha256:discovery.receipt.resultSha256,
    intent:"exploratory", executionKind:"source_audit",
    findings:[{sourceId:discovery.result.sources[0].id,sourceSha256:null,anchor:"Source anchor unresolved",rowIds:[]}],
    evaluation:{material:"Material unresolved",composition:"Composition unresolved",phase:"Phase unresolved",observable:proposal.cheap_discriminating_experiment.measurement,
      unit:"Unit unresolved",temperature:null,referenceId:null,protocol:null,candidateSet:"Candidate set unresolved"},
    arms:[{modelId:"Baseline model unresolved",artifactSha256:null,intervention:proposal.cheap_discriminating_experiment.baseline,fitExposure:null,referenceId:null},
      {modelId:"Candidate model unresolved",artifactSha256:null,intervention:proposal.cheap_discriminating_experiment.design,fitExposure:null,referenceId:null}],
    unknowns:["Draft only: resolve material, composition, phase, units, candidate set and model identities; replace this checklist only after review","Source anchors, row IDs, source hash, evaluation protocol and fitting exposure require verification"],
    excludedScope:["Draft is not source verification, an executed experiment or a public claim"],
    decisionRule:proposal.cheap_discriminating_experiment.decision_rule,falsifier:proposal.falsifier,
    stoppingRule:"Stop after source-contract reconciliation; execution requires a separate authorization and resource gate" });
}
