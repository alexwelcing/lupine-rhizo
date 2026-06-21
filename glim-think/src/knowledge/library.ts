import type { Env } from "../types";
import {
  inferEvidenceIdsFromClaimData,
  parseEvidenceIds,
} from "../research/evidenceIds";

const CORS_HEADERS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type, X-Internal-Token",
} as const;

export const OKF_VERSION = "0.1";

type SortKey = "timestamp" | "updated_at" | "created_at" | "title";
type SortOrder = "ASC" | "DESC";

export interface KnowledgeConceptInput {
  concept_id: string;
  type: string;
  title?: string | null;
  description?: string | null;
  resource?: string | null;
  tags?: string[] | null;
  timestamp?: string | null;
  body_md?: string | null;
  source_kind?: string | null;
  source_id?: string | null;
  okf_version?: string | null;
}

export interface KnowledgeConceptRow {
  concept_id: string;
  type: string;
  title: string | null;
  description: string | null;
  resource: string | null;
  tags_json: string | null;
  timestamp: string | null;
  body_md: string | null;
  source_kind: string | null;
  source_id: string | null;
  okf_version: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface KnowledgeConcept {
  concept_id: string;
  type: string;
  title: string;
  description: string | null;
  resource: string | null;
  tags: string[];
  timestamp: string | null;
  body_md: string;
  source_kind: string | null;
  source_id: string | null;
  okf_version: string;
  created_at: string | null;
  updated_at: string | null;
}

interface NormalizedKnowledgeConcept {
  concept_id: string;
  type: string;
  title: string;
  description: string | null;
  resource: string | null;
  tags: string[];
  timestamp: string | null;
  body_md: string;
  source_kind: string | null;
  source_id: string | null;
  okf_version: string;
  now: string;
}

interface UpsertKnowledgeConceptOptions {
  ensureSchema?: boolean;
  recordEvent?: boolean;
  readBack?: boolean;
  useBatch?: boolean;
}

interface KnowledgeEdgeRow {
  from_concept_id: string;
  to_concept_id: string;
  edge_kind: string;
  label: string | null;
  created_at: string | null;
}

interface SourceHypothesisRow {
  id: string;
  title: string;
  status: string | null;
  confidence: number | null;
  evidence_ids: string | null;
  agent_id: string | null;
  created_at: string | null;
  updated_at: string | null;
}

interface SourceClaimRow {
  claim_id: string;
  claim_type: string;
  claim_data: string | null;
  status: string | null;
  confidence: number | null;
  description: string | null;
  evidence_ids: string | null;
  created_at: string | null;
}

interface SourceRecordRow {
  record_id: string;
  element: string | null;
  potential_id: string | null;
  potential_label: string | null;
  pair_style: string | null;
  property: string | null;
  reference: number | null;
  predicted: number | null;
  unit: string | null;
  provenance: string | null;
  timestamp: string | null;
}

interface SourceQuestionRow {
  id: string;
  question: string;
  asked_by: string | null;
  status: string | null;
  answer_md: string | null;
  target_hypothesis_id: string | null;
  created_at: string | null;
  answered_at: string | null;
}

interface SourceAgendaTaskRow {
  task_id: string;
  title: string;
  domain: string | null;
  specialty: string | null;
  status: string | null;
  priority: number | null;
  payload: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export async function ensureKnowledgeLibrarySchema(env: Env): Promise<void> {
  await env.LEDGER.prepare(`
    CREATE TABLE IF NOT EXISTS knowledge_documents (
      concept_id TEXT PRIMARY KEY,
      type TEXT NOT NULL,
      title TEXT,
      description TEXT,
      resource TEXT,
      tags_json TEXT NOT NULL DEFAULT '[]',
      timestamp TEXT,
      body_md TEXT NOT NULL DEFAULT '',
      source_kind TEXT,
      source_id TEXT,
      okf_version TEXT NOT NULL DEFAULT '0.1',
      created_at TEXT NOT NULL DEFAULT (datetime('now')),
      updated_at TEXT NOT NULL DEFAULT (datetime('now'))
    )
  `).run();
  await env.LEDGER.prepare(`
    CREATE TABLE IF NOT EXISTS knowledge_edges (
      from_concept_id TEXT NOT NULL,
      to_concept_id TEXT NOT NULL,
      edge_kind TEXT NOT NULL DEFAULT 'markdown_link',
      label TEXT,
      created_at TEXT NOT NULL DEFAULT (datetime('now')),
      PRIMARY KEY (from_concept_id, to_concept_id, edge_kind)
    )
  `).run();
  await env.LEDGER.prepare(`
    CREATE TABLE IF NOT EXISTS knowledge_events (
      event_id TEXT PRIMARY KEY,
      event_kind TEXT NOT NULL,
      concept_id TEXT,
      summary TEXT NOT NULL,
      created_at TEXT NOT NULL DEFAULT (datetime('now'))
    )
  `).run();
  await env.LEDGER.prepare(`
    CREATE INDEX IF NOT EXISTS idx_knowledge_documents_timestamp
    ON knowledge_documents(timestamp DESC)
  `).run();
  await env.LEDGER.prepare(`
    CREATE INDEX IF NOT EXISTS idx_knowledge_documents_updated
    ON knowledge_documents(updated_at DESC)
  `).run();
  await env.LEDGER.prepare(`
    CREATE INDEX IF NOT EXISTS idx_knowledge_documents_created
    ON knowledge_documents(created_at DESC)
  `).run();
  await env.LEDGER.prepare(`
    CREATE INDEX IF NOT EXISTS idx_knowledge_documents_type
    ON knowledge_documents(type)
  `).run();
  await env.LEDGER.prepare(`
    CREATE INDEX IF NOT EXISTS idx_knowledge_documents_source
    ON knowledge_documents(source_kind, source_id)
  `).run();
  await env.LEDGER.prepare(`
    CREATE INDEX IF NOT EXISTS idx_knowledge_edges_from
    ON knowledge_edges(from_concept_id)
  `).run();
  await env.LEDGER.prepare(`
    CREATE INDEX IF NOT EXISTS idx_knowledge_edges_to
    ON knowledge_edges(to_concept_id)
  `).run();
}

export async function upsertKnowledgeConcept(
  env: Env,
  input: KnowledgeConceptInput,
  options: UpsertKnowledgeConceptOptions = {},
): Promise<KnowledgeConcept> {
  if (options.ensureSchema !== false) await ensureKnowledgeLibrarySchema(env);
  const concept = normalizeKnowledgeConceptInput(input);
  await runKnowledgeWriteStatements(
    env,
    buildKnowledgeWriteStatements(env, concept, { recordEvent: options.recordEvent !== false }),
    { useBatch: options.useBatch === true },
  );

  if (options.readBack === false) return normalizedToConcept(concept);
  const row = await getKnowledgeConceptRow(env, concept.concept_id, { ensureSchema: options.ensureSchema !== false });
  if (!row) throw new Error(`knowledge concept '${concept.concept_id}' did not persist`);
  return rowToConcept(row);
}

function normalizeKnowledgeConceptInput(input: KnowledgeConceptInput, now = new Date().toISOString()): NormalizedKnowledgeConcept {
  const concept_id = normalizeConceptId(input.concept_id);
  const type = cleanRequired(input.type);
  if (!concept_id) throw new Error("concept_id is required");
  if (!type) throw new Error("type is required");

  return {
    concept_id,
    type,
    title: clean(input.title) || titleFromConceptId(concept_id),
    description: clean(input.description),
    resource: clean(input.resource),
    tags: normalizeTags(input.tags),
    timestamp: normalizeTimestamp(input.timestamp),
    body_md: clean(input.body_md) ?? "",
    source_kind: clean(input.source_kind),
    source_id: clean(input.source_id),
    okf_version: clean(input.okf_version) || OKF_VERSION,
    now,
  };
}

function buildKnowledgeWriteStatements(
  env: Env,
  concept: NormalizedKnowledgeConcept,
  options: { recordEvent: boolean },
): D1PreparedStatement[] {
  const statements: D1PreparedStatement[] = [];
  statements.push(env.LEDGER.prepare(`
    INSERT INTO knowledge_documents
      (concept_id, type, title, description, resource, tags_json, timestamp, body_md, source_kind, source_id, okf_version, created_at, updated_at)
    VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12, ?12)
    ON CONFLICT(concept_id) DO UPDATE SET
      type = excluded.type,
      title = excluded.title,
      description = excluded.description,
      resource = excluded.resource,
      tags_json = excluded.tags_json,
      timestamp = excluded.timestamp,
      body_md = excluded.body_md,
      source_kind = excluded.source_kind,
      source_id = excluded.source_id,
      okf_version = excluded.okf_version,
      updated_at = excluded.updated_at
  `).bind(
    concept.concept_id,
    concept.type,
    concept.title,
    concept.description,
    concept.resource,
    JSON.stringify(concept.tags),
    concept.timestamp,
    concept.body_md,
    concept.source_kind,
    concept.source_id,
    concept.okf_version,
    concept.now,
  ));

  statements.push(env.LEDGER.prepare(
    `DELETE FROM knowledge_edges WHERE from_concept_id = ?1 AND edge_kind = 'markdown_link'`,
  ).bind(concept.concept_id));
  for (const target of extractInternalLinks(concept.body_md, concept.concept_id)) {
    statements.push(env.LEDGER.prepare(`
      INSERT OR IGNORE INTO knowledge_edges
        (from_concept_id, to_concept_id, edge_kind, label, created_at)
      VALUES (?1, ?2, 'markdown_link', NULL, ?3)
    `).bind(concept.concept_id, target, concept.now));
  }

  if (options.recordEvent) {
    statements.push(env.LEDGER.prepare(`
      INSERT OR REPLACE INTO knowledge_events
        (event_id, event_kind, concept_id, summary, created_at)
      VALUES (?1, 'upsert', ?2, ?3, ?4)
    `).bind(`knowledge:${concept.concept_id}:${concept.now}`, concept.concept_id, `Upserted ${concept.title}`, concept.now));
  }
  return statements;
}

async function runKnowledgeWriteStatements(
  env: Env,
  statements: D1PreparedStatement[],
  options: { useBatch: boolean },
): Promise<void> {
  if (!statements.length) return;
  if (options.useBatch) {
    for (let i = 0; i < statements.length; i += 100) {
      await env.LEDGER.batch(statements.slice(i, i + 100));
    }
    return;
  }
  for (const statement of statements) {
    await statement.run();
  }
}

function normalizedToConcept(concept: NormalizedKnowledgeConcept): KnowledgeConcept {
  return {
    concept_id: concept.concept_id,
    type: concept.type,
    title: concept.title,
    description: concept.description,
    resource: concept.resource,
    tags: concept.tags,
    timestamp: concept.timestamp,
    body_md: concept.body_md,
    source_kind: concept.source_kind,
    source_id: concept.source_id,
    okf_version: concept.okf_version,
    created_at: concept.now,
    updated_at: concept.now,
  };
}

export async function syncKnowledgeLibraryFromLedger(env: Env, limit = 100): Promise<{
  ok: true;
  upserted: number;
  by_type: Record<string, number>;
  generated_at: string;
}> {
  await ensureKnowledgeLibrarySchema(env);
  const capped = Math.min(Math.max(Math.trunc(limit), 1), 500);
  const inputs: KnowledgeConceptInput[] = [];

  const hypotheses = await env.LEDGER.prepare(`
    SELECT id, title, status, confidence, evidence_ids, agent_id, created_at, updated_at
    FROM hypotheses
    ORDER BY COALESCE(updated_at, created_at) DESC
    LIMIT ?1
  `).bind(capped).all<SourceHypothesisRow>().catch(() => ({ results: [] as SourceHypothesisRow[] }));
  for (const row of hypotheses.results ?? []) {
    const evidence = parseEvidenceIds(row.evidence_ids);
    inputs.push({
      concept_id: `hypotheses/${row.id}`,
      type: "Research Hypothesis",
      title: row.title,
      description: `Status ${row.status ?? "unknown"}; confidence ${row.confidence ?? "unknown"}.`,
      resource: `/hypotheses/${encodeURIComponent(row.id)}`,
      tags: ["hypothesis", row.status ?? "unknown", ...(row.agent_id ? [`agent:${row.agent_id}`] : [])],
      timestamp: row.updated_at ?? row.created_at,
      source_kind: "hypothesis",
      source_id: row.id,
      body_md: [
        `# ${row.title}`,
        "",
        `- Status: ${row.status ?? "unknown"}`,
        `- Confidence: ${row.confidence ?? "unknown"}`,
        ...(row.agent_id ? [`- Agent: ${row.agent_id}`] : []),
        ...(evidence.length ? ["", "# Evidence", ...evidence.map((id) => `- [${id}](/claims/${encodeURIComponent(id)}.md)`)] : []),
      ].join("\n"),
    });
  }

  const claims = await env.LEDGER.prepare(`
    SELECT claim_id, claim_type, claim_data, status, confidence, description, evidence_ids, created_at
    FROM claims
    ORDER BY created_at DESC
    LIMIT ?1
  `).bind(capped).all<SourceClaimRow>().catch(() => ({ results: [] as SourceClaimRow[] }));
  for (const row of claims.results ?? []) {
    const evidence = claimEvidenceIds(row);
    inputs.push({
      concept_id: `claims/${row.claim_id}`,
      type: "Discovery Claim",
      title: row.description?.slice(0, 120) || row.claim_id,
      description: `${row.claim_type}; status ${row.status ?? "unknown"}; confidence ${row.confidence ?? "unknown"}.`,
      resource: `/claims/${encodeURIComponent(row.claim_id)}`,
      tags: ["claim", row.claim_type, row.status ?? "unknown"],
      timestamp: row.created_at,
      source_kind: "claim",
      source_id: row.claim_id,
      body_md: [
        `# ${row.description || row.claim_id}`,
        "",
        `- Claim type: ${row.claim_type}`,
        `- Status: ${row.status ?? "unknown"}`,
        `- Confidence: ${row.confidence ?? "unknown"}`,
        "",
        "# Evidence IDs",
        formatEvidenceList(evidence),
      ].join("\n"),
    });
  }

  const records = await env.LEDGER.prepare(`
    SELECT record_id, element, potential_id, potential_label, pair_style, property,
           reference, predicted, unit, provenance, timestamp
    FROM records
    ORDER BY timestamp DESC
    LIMIT ?1
  `).bind(capped).all<SourceRecordRow>().catch(() => ({ results: [] as SourceRecordRow[] }));
  for (const row of records.results ?? []) {
    inputs.push({
      concept_id: `records/${row.record_id}`,
      type: "Benchmark Record",
      title: `${row.element ?? "unknown"}/${row.potential_id ?? row.potential_label ?? "unknown"}/${row.property ?? "property"}`,
      description: `Reference ${row.reference ?? "n/a"}; predicted ${row.predicted ?? "n/a"} ${row.unit ?? ""}`.trim(),
      resource: `/records/${encodeURIComponent(row.record_id)}`,
      tags: [
        "record",
        ...(row.element ? [`element:${row.element}`] : []),
        ...(row.potential_id ? [`potential:${row.potential_id}`] : []),
        ...(row.pair_style ? [`pair_style:${row.pair_style}`] : []),
      ],
      timestamp: row.timestamp,
      source_kind: "benchmark_record",
      source_id: row.record_id,
      body_md: [
        `# ${row.element ?? "unknown"} ${row.potential_id ?? row.potential_label ?? "unknown"} ${row.property ?? "property"}`,
        "",
        `- Record ID: ${row.record_id}`,
        `- Element: ${row.element ?? "unknown"}`,
        `- Potential: ${row.potential_id ?? row.potential_label ?? "unknown"}`,
        `- Pair style: ${row.pair_style ?? "unknown"}`,
        `- Property: ${row.property ?? "unknown"}`,
        `- Reference: ${row.reference ?? "unknown"} ${row.unit ?? ""}`.trim(),
        `- Predicted: ${row.predicted ?? "unknown"} ${row.unit ?? ""}`.trim(),
        ...(row.provenance ? ["", "# Provenance", "```json", row.provenance, "```"] : []),
      ].join("\n"),
    });
  }

  const questions = await env.LEDGER.prepare(`
    SELECT id, question, asked_by, status, answer_md, target_hypothesis_id, created_at, answered_at
    FROM research_questions
    ORDER BY COALESCE(answered_at, created_at) DESC
    LIMIT ?1
  `).bind(capped).all<SourceQuestionRow>().catch(() => ({ results: [] as SourceQuestionRow[] }));
  for (const row of questions.results ?? []) {
    inputs.push({
      concept_id: `questions/${row.id}`,
      type: "Research Question",
      title: row.question.slice(0, 120),
      description: `Status ${row.status ?? "unknown"}.`,
      resource: `/research/questions/${encodeURIComponent(row.id)}`,
      tags: ["question", row.status ?? "unknown", ...(row.asked_by ? [`asked_by:${row.asked_by}`] : [])],
      timestamp: row.answered_at ?? row.created_at,
      source_kind: "research_question",
      source_id: row.id,
      body_md: [
        `# ${row.question}`,
        "",
        `- Status: ${row.status ?? "unknown"}`,
        ...(row.target_hypothesis_id ? [`- Target hypothesis: [${row.target_hypothesis_id}](/hypotheses/${encodeURIComponent(row.target_hypothesis_id)}.md)`] : []),
        ...(row.answer_md ? ["", "# Answer", row.answer_md] : []),
      ].join("\n"),
    });
  }

  const tasks = await env.LEDGER.prepare(`
    SELECT task_id, title, domain, specialty, status, priority, payload, created_at, updated_at
    FROM intelligence_tasks
    ORDER BY COALESCE(updated_at, created_at) DESC
    LIMIT ?1
  `).bind(capped).all<SourceAgendaTaskRow>().catch(() => ({ results: [] as SourceAgendaTaskRow[] }));
  for (const row of tasks.results ?? []) {
    const payload = safeJson(row.payload);
    const workflowId = typeof payload?.workflow_id === "string" ? payload.workflow_id : null;
    const campaignId = typeof payload?.campaign_id === "string" ? payload.campaign_id : null;
    inputs.push({
      concept_id: `agenda/${stablePathPart(row.task_id)}`,
      type: "Agenda Task",
      title: row.title,
      description: `${row.status ?? "unknown"} ${row.specialty ?? "task"} priority ${row.priority ?? "unknown"}.`,
      resource: `/admin/agenda/tasks?status=${encodeURIComponent(row.status ?? "queued")}`,
      tags: ["agenda", row.status ?? "unknown", row.specialty ?? "general", ...(workflowId ? [`workflow:${workflowId}`] : [])],
      timestamp: row.updated_at ?? row.created_at,
      source_kind: "agenda_task",
      source_id: row.task_id,
      body_md: [
        `# ${row.title}`,
        "",
        `- Task ID: ${row.task_id}`,
        `- Domain: ${row.domain ?? "unknown"}`,
        `- Specialty: ${row.specialty ?? "unknown"}`,
        `- Status: ${row.status ?? "unknown"}`,
        `- Priority: ${row.priority ?? "unknown"}`,
        ...(workflowId && campaignId ? ["", `# Workflow`, `[${workflowId} campaign ${campaignId}](/workflows/${encodeURIComponent(workflowId)}.md)`] : []),
        ...(row.payload ? ["", "# Payload", "```json", row.payload, "```"] : []),
      ].join("\n"),
    });
  }

  inputs.push({
    concept_id: "systems/glim-think-ledger",
    type: "Knowledge System",
    title: "glim-think D1 ledger",
    description: "Durable Cloudflare D1 control-plane ledger for hypotheses, claims, questions, agenda tasks, and knowledge-library OKF concepts.",
    resource: "/knowledge/library",
    tags: ["system", "ledger", "okf", "knowledge-library"],
    timestamp: new Date().toISOString(),
    source_kind: "system",
    source_id: "glim-think-ledger",
    body_md: [
      "# glim-think D1 ledger",
      "",
      "This concept documents the ledger-backed knowledge library and its OKF export surface.",
      "",
      "# Links",
      "- [Hypotheses](/hypotheses/index.md)",
      "- [Claims](/claims/index.md)",
      "- [Research questions](/questions/index.md)",
      "- [Agenda tasks](/agenda/index.md)",
    ].join("\n"),
  });

  const generatedAt = new Date().toISOString();
  const concepts = inputs.map((input) => normalizeKnowledgeConceptInput(input, generatedAt));
  const counts: Record<string, number> = {};
  const statements: D1PreparedStatement[] = [];
  for (const concept of concepts) {
    counts[concept.type] = (counts[concept.type] ?? 0) + 1;
    statements.push(...buildKnowledgeWriteStatements(env, concept, { recordEvent: false }));
  }
  await runKnowledgeWriteStatements(env, statements, { useBatch: true });
  await env.LEDGER.prepare(`
    INSERT OR REPLACE INTO knowledge_events
      (event_id, event_kind, concept_id, summary, created_at)
    VALUES (?1, 'sync', ?2, ?3, ?4)
  `).bind(
    `knowledge:sync:${generatedAt}`,
    "systems/glim-think-ledger",
    `Synced ${concepts.length} concepts into the OKF knowledge library`,
    generatedAt,
  ).run();
  return { ok: true, upserted: concepts.length, by_type: counts, generated_at: generatedAt };
}

export async function listKnowledgeConcepts(env: Env, url: URL): Promise<{
  concepts: KnowledgeConcept[];
  count: number;
  limit: number;
  sort: string;
  order: "asc" | "desc";
}> {
  await ensureKnowledgeLibrarySchema(env);
  const limitRaw = Number.parseInt(url.searchParams.get("limit") ?? "50", 10);
  const limit = Number.isFinite(limitRaw) && limitRaw > 0 ? Math.min(limitRaw, 500) : 50;
  const sort = normalizeSort(url.searchParams.get("sort"));
  const order = normalizeOrder(url.searchParams.get("order"));
  const where: string[] = [];
  const binds: unknown[] = [];
  const type = clean(url.searchParams.get("type"));
  const tag = clean(url.searchParams.get("tag"));
  const q = clean(url.searchParams.get("q"));
  if (type) {
    where.push(`type = ?${binds.length + 1}`);
    binds.push(type);
  }
  if (tag) {
    where.push(`tags_json LIKE ?${binds.length + 1}`);
    binds.push(`%"${escapeLike(tag)}"%`);
  }
  if (q) {
    where.push(`(LOWER(title) LIKE ?${binds.length + 1} OR LOWER(description) LIKE ?${binds.length + 1} OR LOWER(body_md) LIKE ?${binds.length + 1})`);
    binds.push(`%${q.toLowerCase()}%`);
  }
  const whereSql = where.length ? `WHERE ${where.join(" AND ")}` : "";
  binds.push(limit);
  const rows = await env.LEDGER.prepare(`
    SELECT *
    FROM knowledge_documents
    ${whereSql}
    ORDER BY ${sortSql(sort)} ${order}, concept_id ASC
    LIMIT ?${binds.length}
  `).bind(...binds).all<KnowledgeConceptRow>();
  return {
    concepts: (rows.results ?? []).map(rowToConcept),
    count: rows.results?.length ?? 0,
    limit,
    sort,
    order: order.toLowerCase() as "asc" | "desc",
  };
}

export async function buildKnowledgeGraph(env: Env, limit = 250): Promise<{
  nodes: Array<{ id: string; type: string; label: string; timestamp: string | null; tags: string[]; source_kind: string | null }>;
  edges: Array<{ id: string; source: string; target: string; kind: string; label: string | null }>;
  stats: { nodes_total: number; edges_total: number; by_type: Record<string, number>; generated_at: string };
}> {
  await ensureKnowledgeLibrarySchema(env);
  const capped = Math.min(Math.max(Math.trunc(limit), 1), 500);
  const rows = await env.LEDGER.prepare(`
    SELECT *
    FROM knowledge_documents
    ORDER BY COALESCE(timestamp, updated_at, created_at) DESC, concept_id ASC
    LIMIT ?1
  `).bind(capped).all<KnowledgeConceptRow>();
  const concepts = (rows.results ?? []).map(rowToConcept);
  const ids = new Set(concepts.map((concept) => concept.concept_id));
  const edgesRows = await env.LEDGER.prepare(`
    SELECT from_concept_id, to_concept_id, edge_kind, label, created_at
    FROM knowledge_edges
    ORDER BY created_at DESC
    LIMIT ?1
  `).bind(capped * 4).all<KnowledgeEdgeRow>();
  const byType: Record<string, number> = {};
  const nodes = concepts.map((concept) => {
    byType[concept.type] = (byType[concept.type] ?? 0) + 1;
    return {
      id: concept.concept_id,
      type: concept.type,
      label: concept.title,
      timestamp: concept.timestamp,
      tags: concept.tags,
      source_kind: concept.source_kind,
    };
  });
  const edges = (edgesRows.results ?? [])
    .filter((edge) => ids.has(edge.from_concept_id) && ids.has(edge.to_concept_id))
    .map((edge) => ({
      id: `${edge.from_concept_id}->${edge.to_concept_id}:${edge.edge_kind}`,
      source: edge.from_concept_id,
      target: edge.to_concept_id,
      kind: edge.edge_kind,
      label: edge.label,
    }));
  return {
    nodes,
    edges,
    stats: {
      nodes_total: nodes.length,
      edges_total: edges.length,
      by_type: byType,
      generated_at: new Date().toISOString(),
    },
  };
}

export async function exportOkfBundle(env: Env, limit = 250): Promise<{
  okf_version: string;
  bundle: string;
  generated_at: string;
  files: Array<{ path: string; concept_id?: string; type?: string; title?: string; timestamp?: string | null; content: string }>;
}> {
  const listed = await listKnowledgeConcepts(
    env,
    new URL(`https://worker.test/knowledge/library?limit=${Math.min(Math.max(Math.trunc(limit), 1), 500)}&sort=timestamp&order=desc`),
  );
  const files: Array<{
    path: string;
    concept_id?: string;
    type?: string;
    title?: string;
    timestamp?: string | null;
    content: string;
  }> = listed.concepts.map((concept) => ({
    path: `${concept.concept_id}.md`,
    concept_id: concept.concept_id,
    type: concept.type,
    title: concept.title,
    timestamp: concept.timestamp,
    content: conceptToOkfMarkdown(concept),
  }));
  files.unshift({ path: "log.md", content: buildOkfLog(listed.concepts) });
  files.unshift({ path: "index.md", content: buildOkfIndex(listed.concepts) });
  return {
    okf_version: OKF_VERSION,
    bundle: "glim-think-ledger",
    generated_at: new Date().toISOString(),
    files,
  };
}

export async function handleKnowledgeLibraryRoute(
  env: Env,
  url: URL,
  method: string,
  bodyText: string,
): Promise<Response | null> {
  if (!url.pathname.startsWith("/knowledge/library")) return null;
  if (method === "OPTIONS") return new Response(null, { status: 204, headers: CORS_HEADERS });

  try {
    if (url.pathname === "/knowledge/library" && method === "GET") {
      return Response.json(await listKnowledgeConcepts(env, url), { headers: CORS_HEADERS });
    }
    if (url.pathname === "/knowledge/library/graph" && method === "GET") {
      const limit = Number.parseInt(url.searchParams.get("limit") ?? "250", 10);
      return Response.json(await buildKnowledgeGraph(env, limit), { headers: CORS_HEADERS });
    }
    if (url.pathname === "/knowledge/library/okf" && method === "GET") {
      const limit = Number.parseInt(url.searchParams.get("limit") ?? "250", 10);
      return Response.json(await exportOkfBundle(env, limit), { headers: CORS_HEADERS });
    }
    if (url.pathname === "/knowledge/library/okf/concept" && method === "GET") {
      const conceptId = normalizeConceptId(url.searchParams.get("concept_id") ?? "");
      const row = conceptId ? await getKnowledgeConceptRow(env, conceptId) : null;
      if (!row) return Response.json({ error: `Knowledge concept not found: ${conceptId}` }, { status: 404, headers: CORS_HEADERS });
      return new Response(conceptToOkfMarkdown(rowToConcept(row)), {
        headers: { ...CORS_HEADERS, "Content-Type": "text/markdown; charset=utf-8" },
      });
    }
    if (url.pathname === "/knowledge/library/sync" && method === "POST") {
      const body = safeJson(bodyText) ?? {};
      const limit = typeof body.limit === "number" ? body.limit : Number.parseInt(url.searchParams.get("limit") ?? "100", 10);
      return Response.json(await syncKnowledgeLibraryFromLedger(env, limit), { headers: CORS_HEADERS });
    }
    if (url.pathname === "/knowledge/library/concepts" && method === "POST") {
      const body = safeJson(bodyText);
      if (!body || typeof body !== "object") {
        return Response.json({ error: "JSON object body required" }, { status: 400, headers: CORS_HEADERS });
      }
      return Response.json(await upsertKnowledgeConcept(env, body as unknown as KnowledgeConceptInput), {
        status: 201,
        headers: CORS_HEADERS,
      });
    }
    return Response.json({ error: "Not found" }, { status: 404, headers: CORS_HEADERS });
  } catch (e) {
    return Response.json({ error: String(e) }, { status: 500, headers: CORS_HEADERS });
  }
}

async function getKnowledgeConceptRow(
  env: Env,
  conceptId: string,
  options: { ensureSchema?: boolean } = {},
): Promise<KnowledgeConceptRow | null> {
  if (options.ensureSchema !== false) await ensureKnowledgeLibrarySchema(env);
  return env.LEDGER.prepare(
    `SELECT * FROM knowledge_documents WHERE concept_id = ?1`,
  ).bind(conceptId).first<KnowledgeConceptRow>();
}

function rowToConcept(row: KnowledgeConceptRow): KnowledgeConcept {
  return {
    concept_id: row.concept_id,
    type: row.type,
    title: row.title || titleFromConceptId(row.concept_id),
    description: row.description,
    resource: row.resource,
    tags: parseJsonArray(row.tags_json),
    timestamp: row.timestamp,
    body_md: row.body_md ?? "",
    source_kind: row.source_kind,
    source_id: row.source_id,
    okf_version: row.okf_version || OKF_VERSION,
    created_at: row.created_at,
    updated_at: row.updated_at,
  };
}

function conceptToOkfMarkdown(concept: KnowledgeConcept): string {
  const frontmatter: Record<string, unknown> = {
    type: concept.type,
    title: concept.title,
    description: concept.description,
    resource: concept.resource,
    tags: concept.tags,
    timestamp: concept.timestamp,
    okf_version: concept.okf_version,
    source_kind: concept.source_kind,
    source_id: concept.source_id,
  };
  return `---\n${toYaml(frontmatter)}---\n\n${concept.body_md.trim()}\n`;
}

function buildOkfIndex(concepts: KnowledgeConcept[]): string {
  const grouped = new Map<string, KnowledgeConcept[]>();
  for (const concept of concepts) {
    const group = concept.concept_id.split("/")[0] || "root";
    grouped.set(group, [...(grouped.get(group) ?? []), concept]);
  }
  const lines = [
    "---",
    `okf_version: "${OKF_VERSION}"`,
    "---",
    "",
    "# glim-think ledger knowledge bundle",
    "",
    "Ledger-backed OKF export for hypotheses, claims, questions, agenda tasks, and curated system knowledge.",
  ];
  for (const [group, rows] of [...grouped.entries()].sort(([a], [b]) => a.localeCompare(b))) {
    lines.push("", `# ${titleFromConceptId(group)}`);
    for (const concept of rows.slice(0, 100)) {
      lines.push(`* [${escapeMarkdown(concept.title)}](/${concept.concept_id}.md) - ${escapeMarkdown(concept.description ?? concept.type)}`);
    }
  }
  return `${lines.join("\n")}\n`;
}

function buildOkfLog(concepts: KnowledgeConcept[]): string {
  const byDate = new Map<string, KnowledgeConcept[]>();
  for (const concept of concepts) {
    const date = (concept.timestamp ?? concept.updated_at ?? concept.created_at ?? new Date().toISOString()).slice(0, 10);
    byDate.set(date, [...(byDate.get(date) ?? []), concept]);
  }
  const lines = ["# Directory Update Log"];
  for (const [date, rows] of [...byDate.entries()].sort(([a], [b]) => b.localeCompare(a))) {
    lines.push("", `## ${date}`);
    for (const concept of rows.slice(0, 100)) {
      lines.push(`* **Update**: Synced [${escapeMarkdown(concept.title)}](/${concept.concept_id}.md).`);
    }
  }
  return `${lines.join("\n")}\n`;
}

function normalizeConceptId(value: string): string {
  return value.trim()
    .replace(/\\/g, "/")
    .replace(/^\//, "")
    .replace(/\.md$/, "")
    .replace(/\/+/g, "/")
    .replace(/[^A-Za-z0-9_./:-]/g, "-")
    .replace(/\/(index|log)$/i, "/reserved");
}

function stablePathPart(value: string): string {
  return value.trim().replace(/[^A-Za-z0-9_.:-]/g, "-").slice(0, 180);
}

function extractInternalLinks(markdown: string, fromConceptId: string): string[] {
  const targets = new Set<string>();
  const re = /\[[^\]]+\]\(([^)]+)\)/g;
  let match: RegExpExecArray | null;
  while ((match = re.exec(markdown)) !== null) {
    const href = match[1].split("#")[0].trim();
    if (!href || /^(https?:|mailto:|#)/i.test(href)) continue;
    const target = href.startsWith("/")
      ? href.slice(1)
      : resolveRelativeConcept(fromConceptId, href);
    const normalized = normalizeConceptId(target);
    if (normalized) targets.add(normalized);
  }
  return [...targets].sort();
}

function resolveRelativeConcept(fromConceptId: string, href: string): string {
  const parts = fromConceptId.split("/");
  parts.pop();
  for (const part of href.split("/")) {
    if (!part || part === ".") continue;
    if (part === "..") parts.pop();
    else parts.push(part);
  }
  return parts.join("/");
}

function titleFromConceptId(id: string): string {
  const last = id.split("/").filter(Boolean).pop() ?? id;
  return last.replace(/[-_]/g, " ").replace(/\b\w/g, (char) => char.toUpperCase());
}

function parseJsonArray(value: unknown): string[] {
  if (Array.isArray(value)) return value.map(String).filter(Boolean);
  if (typeof value !== "string" || !value.trim()) return [];
  try {
    const parsed = JSON.parse(value);
    return Array.isArray(parsed) ? parsed.map(String).filter(Boolean) : [];
  } catch {
    return [];
  }
}

function claimEvidenceIds(row: SourceClaimRow): string[] {
  const explicit = parseEvidenceIds(row.evidence_ids);
  if (explicit.length) return explicit;
  return inferEvidenceIdsFromClaimData(row.claim_data);
}

function formatEvidenceList(ids: string[]): string {
  return ids.length ? ids.map((id) => `- [${id}](/${evidenceConceptPath(id)}.md)`).join("\n") : "- None recorded";
}

function evidenceConceptPath(id: string): string {
  if (id.startsWith("record:")) return `records/${id.slice("record:".length)}`;
  if (id.startsWith("claim:")) return `claims/${id.slice("claim:".length)}`;
  if (id.startsWith("campaign:")) return `campaigns/${id.slice("campaign:".length)}`;
  if (id.startsWith("github-actions:")) return `evidence/github-actions/${id.slice("github-actions:".length)}`;
  return `claims/${id}`;
}

function safeJson(value: unknown): Record<string, unknown> | null {
  if (typeof value !== "string") return typeof value === "object" && value !== null ? value as Record<string, unknown> : null;
  if (!value.trim()) return {};
  try {
    const parsed = JSON.parse(value);
    return typeof parsed === "object" && parsed !== null ? parsed as Record<string, unknown> : null;
  } catch {
    return null;
  }
}

function formatJsonishList(value: string | null): string {
  const rows = parseJsonArray(value);
  return rows.length ? rows.map((id) => `- ${id}`).join("\n") : "- None recorded";
}

function normalizeTags(tags: string[] | null | undefined): string[] {
  const unique = new Set<string>();
  for (const tag of tags ?? []) {
    const cleanTag = String(tag).trim().toLowerCase().replace(/[^a-z0-9:._-]/g, "-");
    if (cleanTag) unique.add(cleanTag);
  }
  return [...unique].sort();
}

function normalizeTimestamp(value: string | null | undefined): string | null {
  const text = clean(value);
  if (!text) return null;
  const date = new Date(text);
  return Number.isNaN(date.valueOf()) ? text : date.toISOString();
}

function normalizeSort(value: string | null): SortKey {
  if (value === "updated_at" || value === "created_at" || value === "title") return value;
  return "timestamp";
}

function normalizeOrder(value: string | null): SortOrder {
  return value?.toLowerCase() === "asc" ? "ASC" : "DESC";
}

function sortSql(sort: SortKey): string {
  if (sort === "title") return "LOWER(title)";
  if (sort === "updated_at") return "COALESCE(updated_at, timestamp, created_at)";
  if (sort === "created_at") return "COALESCE(created_at, timestamp, updated_at)";
  return "COALESCE(timestamp, updated_at, created_at)";
}

function cleanRequired(value: unknown): string {
  return typeof value === "string" ? value.trim() : "";
}

function clean(value: unknown): string | null {
  return typeof value === "string" && value.trim() ? value.trim() : null;
}

function escapeLike(value: string): string {
  return value.replace(/[%_]/g, "");
}

function escapeMarkdown(value: string): string {
  return value.replace(/\[/g, "\\[").replace(/\]/g, "\\]");
}

function toYaml(values: Record<string, unknown>): string {
  const lines: string[] = [];
  for (const [key, value] of Object.entries(values)) {
    if (value === null || value === undefined || value === "") continue;
    if (Array.isArray(value)) {
      lines.push(`${key}: [${value.map((item) => JSON.stringify(String(item))).join(", ")}]`);
    } else {
      lines.push(`${key}: ${JSON.stringify(String(value))}`);
    }
  }
  return `${lines.join("\n")}\n`;
}
