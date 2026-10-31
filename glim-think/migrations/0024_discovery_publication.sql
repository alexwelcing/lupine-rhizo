-- Additive public projection. No private data are selected or exported.
CREATE TABLE IF NOT EXISTS knowledge_documents (
 concept_id TEXT PRIMARY KEY, type TEXT NOT NULL, title TEXT, description TEXT, resource TEXT,
 tags_json TEXT NOT NULL DEFAULT '[]', timestamp TEXT, body_md TEXT NOT NULL DEFAULT '',
 source_kind TEXT, source_id TEXT, okf_version TEXT NOT NULL DEFAULT '0.1',
 created_at TEXT NOT NULL DEFAULT (datetime('now')), updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS knowledge_edges (
 from_concept_id TEXT NOT NULL, to_concept_id TEXT NOT NULL, edge_kind TEXT NOT NULL DEFAULT 'markdown_link',
 label TEXT, created_at TEXT NOT NULL DEFAULT (datetime('now')),
 PRIMARY KEY (from_concept_id,to_concept_id,edge_kind)
);
CREATE TABLE IF NOT EXISTS knowledge_events (
 event_id TEXT PRIMARY KEY,event_kind TEXT NOT NULL,concept_id TEXT,summary TEXT NOT NULL,
 created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS public_discovery_evidence (
 publication_id TEXT PRIMARY KEY REFERENCES public_research_activity(id),
 evidence_sha256 TEXT NOT NULL CHECK(length(evidence_sha256)=64),
 record_sha256 TEXT NOT NULL CHECK(length(record_sha256)=64),
 projection_sha256 TEXT NOT NULL CHECK(length(projection_sha256)=64),
 payload TEXT NOT NULL CHECK(json_valid(payload) AND length(CAST(payload AS BLOB))<=32768)
);
-- Membership identifies the public subset of the existing knowledge store.
CREATE TABLE IF NOT EXISTS public_discovery_nodes (
 publication_id TEXT NOT NULL REFERENCES public_discovery_evidence(publication_id),
 concept_id TEXT NOT NULL REFERENCES knowledge_documents(concept_id),
 PRIMARY KEY(publication_id,concept_id)
);
CREATE INDEX IF NOT EXISTS public_discovery_nodes_concept ON public_discovery_nodes(concept_id);
CREATE TRIGGER IF NOT EXISTS public_discovery_evidence_insert BEFORE INSERT ON public_discovery_evidence BEGIN
 SELECT CASE WHEN EXISTS(SELECT 1 FROM public_discovery_evidence WHERE publication_id=NEW.publication_id AND
 (evidence_sha256<>NEW.evidence_sha256 OR record_sha256<>NEW.record_sha256 OR projection_sha256<>NEW.projection_sha256 OR payload<>NEW.payload))
 THEN RAISE(ABORT,'Public discovery evidence is immutable') END;
 SELECT CASE WHEN EXISTS(SELECT 1 FROM public_discovery_evidence WHERE publication_id=NEW.publication_id) THEN RAISE(IGNORE) END;
 SELECT CASE WHEN json_extract(NEW.payload,'$.schema') IS NOT 'lupine.public_discovery_report.v1'
 OR json_extract(NEW.payload,'$.policy') IS NOT 'accepted-discovery-public/v1'
 OR 'discovery-' || json_extract(NEW.payload,'$.provenance.archiveSha256') IS NOT NEW.publication_id
 THEN RAISE(ABORT,'Public discovery evidence identity mismatch') END;
END;
CREATE TRIGGER IF NOT EXISTS public_discovery_evidence_update BEFORE UPDATE ON public_discovery_evidence BEGIN SELECT RAISE(ABORT,'Public discovery evidence is immutable'); END;
CREATE TRIGGER IF NOT EXISTS public_discovery_evidence_delete BEFORE DELETE ON public_discovery_evidence BEGIN SELECT RAISE(ABORT,'Public discovery evidence is immutable'); END;
CREATE TRIGGER IF NOT EXISTS public_discovery_nodes_update BEFORE UPDATE ON public_discovery_nodes BEGIN SELECT RAISE(ABORT,'Public discovery membership is immutable'); END;
CREATE TRIGGER IF NOT EXISTS public_discovery_nodes_delete BEFORE DELETE ON public_discovery_nodes BEGIN SELECT RAISE(ABORT,'Public discovery membership is immutable'); END;
CREATE TRIGGER IF NOT EXISTS publication_knowledge_insert BEFORE INSERT ON knowledge_documents
 WHEN NEW.source_kind='public_discovery' OR NEW.concept_id GLOB 'publications/*' OR NEW.concept_id GLOB 'publication-topics/*' OR NEW.concept_id GLOB 'publication-sources/*' BEGIN
 SELECT CASE WHEN NEW.source_kind IS NOT 'public_discovery' THEN RAISE(ABORT,'Reserved publication namespace') END;
 SELECT CASE WHEN EXISTS(SELECT 1 FROM knowledge_documents old WHERE old.concept_id=NEW.concept_id AND
 (old.type IS NOT NEW.type OR old.title IS NOT NEW.title OR old.description IS NOT NEW.description OR old.resource IS NOT NEW.resource
 OR old.tags_json IS NOT NEW.tags_json OR old.timestamp IS NOT NEW.timestamp OR old.body_md IS NOT NEW.body_md
 OR old.source_kind IS NOT NEW.source_kind OR old.source_id IS NOT NEW.source_id OR old.okf_version IS NOT NEW.okf_version))
 THEN RAISE(ABORT,'Published knowledge is immutable') END;
 SELECT CASE WHEN EXISTS(SELECT 1 FROM knowledge_documents WHERE concept_id=NEW.concept_id) THEN RAISE(IGNORE) END;
END;
CREATE TRIGGER IF NOT EXISTS publication_knowledge_update BEFORE UPDATE ON knowledge_documents
 WHEN OLD.source_kind='public_discovery' OR NEW.source_kind='public_discovery'
 BEGIN SELECT RAISE(ABORT,'Published knowledge is immutable'); END;
CREATE TRIGGER IF NOT EXISTS publication_knowledge_delete BEFORE DELETE ON knowledge_documents WHEN OLD.source_kind='public_discovery'
 BEGIN SELECT RAISE(ABORT,'Published knowledge is immutable'); END;
CREATE TRIGGER IF NOT EXISTS publication_edges_insert BEFORE INSERT ON knowledge_edges WHEN NEW.edge_kind GLOB 'publication:*' BEGIN
 SELECT CASE WHEN NOT EXISTS(SELECT 1 FROM knowledge_documents WHERE concept_id=NEW.from_concept_id AND source_kind='public_discovery')
 OR NOT EXISTS(SELECT 1 FROM knowledge_documents WHERE concept_id=NEW.to_concept_id AND source_kind='public_discovery')
 THEN RAISE(ABORT,'Publication edge endpoints must be public') END;
 SELECT CASE WHEN EXISTS(SELECT 1 FROM knowledge_edges old WHERE old.from_concept_id=NEW.from_concept_id AND old.to_concept_id=NEW.to_concept_id
 AND old.edge_kind=NEW.edge_kind AND old.label IS NOT NEW.label) THEN RAISE(ABORT,'Published edge is immutable') END;
END;
CREATE TRIGGER IF NOT EXISTS publication_edges_update BEFORE UPDATE ON knowledge_edges WHEN OLD.edge_kind GLOB 'publication:*' OR NEW.edge_kind GLOB 'publication:*'
 BEGIN SELECT RAISE(ABORT,'Published edge is immutable'); END;
CREATE TRIGGER IF NOT EXISTS publication_edges_delete BEFORE DELETE ON knowledge_edges WHEN OLD.edge_kind GLOB 'publication:*'
 BEGIN SELECT RAISE(ABORT,'Published edge is immutable'); END;
CREATE TRIGGER IF NOT EXISTS publication_event_insert BEFORE INSERT ON knowledge_events WHEN NEW.event_id GLOB 'publication:*' BEGIN
 SELECT CASE WHEN EXISTS(SELECT 1 FROM knowledge_events old WHERE old.event_id=NEW.event_id AND
 (old.event_kind IS NOT NEW.event_kind OR old.concept_id IS NOT NEW.concept_id OR old.summary IS NOT NEW.summary OR old.created_at IS NOT NEW.created_at))
 THEN RAISE(ABORT,'Published event is immutable') END;
 SELECT CASE WHEN EXISTS(SELECT 1 FROM knowledge_events WHERE event_id=NEW.event_id) THEN RAISE(IGNORE) END;
END;
CREATE TRIGGER IF NOT EXISTS publication_event_update BEFORE UPDATE ON knowledge_events WHEN OLD.event_id GLOB 'publication:*' OR NEW.event_id GLOB 'publication:*'
 BEGIN SELECT RAISE(ABORT,'Published event is immutable'); END;
CREATE TRIGGER IF NOT EXISTS publication_event_delete BEFORE DELETE ON knowledge_events WHEN OLD.event_id GLOB 'publication:*'
 BEGIN SELECT RAISE(ABORT,'Published event is immutable'); END;
