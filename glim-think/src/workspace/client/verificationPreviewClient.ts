import { canonicalComparisonJSON, comparisonContractSchema } from "../comparisonContracts";
import { assessVacancyEvidence } from "../vacancyEvidenceContracts";
import { RESEARCH_RUN_MAX_BYTES, sha256 } from "../researchRunContracts";

/** Only an explicit preview click sends the reviewed contract and optional attachment. */
export async function requestVerificationPreview(runId: string, text: string, vacancyText = ""): Promise<{
  blockers: string[]; contractSha256: string; vacancyAttachmentSha256?: string;
}> {
  const bytes = (value: string) => new TextEncoder().encode(value).length;
  if (bytes(text) > RESEARCH_RUN_MAX_BYTES / 2 || bytes(vacancyText) > RESEARCH_RUN_MAX_BYTES)
    throw new Error("Comparison is too large");
  const contract = comparisonContractSchema.parse(JSON.parse(text));
  const contractSha256 = await sha256(canonicalComparisonJSON(contract));
  const vacancyEvidence = vacancyText.trim()
    ? assessVacancyEvidence(JSON.parse(vacancyText), contract.arms.map(arm => arm.modelId)).evidence : undefined;
  if (vacancyEvidence && vacancyEvidence.comparisonContractSha256 !== contractSha256)
    throw new Error("Vacancy attachment binds another contract");
  const attachmentSha256 = vacancyEvidence ? await sha256(canonicalComparisonJSON(vacancyEvidence)) : undefined;
  const body = JSON.stringify({ runId, contract, ...(vacancyEvidence ? { vacancyEvidence } : {}) });
  if (bytes(body) > RESEARCH_RUN_MAX_BYTES) throw new Error("Comparison is too large");
  const init = { method: "POST", credentials: "same-origin" as const,
    headers: { "Content-Type": "application/json" }, body };
  const response = await fetch("/workspace/research-runs/verification-preview", init);
  if (!response.ok) throw new Error("Comparison preview unavailable");
  const result = await response.json() as Record<string, unknown>;
  if (!result || result.execution !== "not_started" || result.scheduled !== false || result.visibility !== "private" ||
      result.publication !== "held" || result.sourceVerification !== "not_performed" ||
      !Array.isArray(result.blockers) || result.blockers.some(item => typeof item !== "string") ||
      result.contractSha256 !== contractSha256) throw new Error("Invalid preview");
  const attachment = result.vacancyEvidence as Record<string, unknown> | undefined;
  if (vacancyEvidence ? !attachment || attachment.attachmentSha256 !== attachmentSha256 ||
      attachment.arithmeticConsistency !== "checked_on_declared_components" ||
      attachment.inputArtifactExecution !== "not_verified" || attachment.sourceVerification !== "not_performed" ||
      attachment.scientificSupport !== "not_asserted" : attachment !== undefined)
    throw new Error("Invalid vacancy attachment acknowledgement");
  return { blockers: result.blockers as string[], contractSha256,
    ...(attachmentSha256 ? { vacancyAttachmentSha256: attachmentSha256 } : {}) };
}

