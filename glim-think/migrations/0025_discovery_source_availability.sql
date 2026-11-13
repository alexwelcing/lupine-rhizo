-- Additive source availability notices. Original reports and projections stay immutable.
CREATE TABLE IF NOT EXISTS public_discovery_withdrawals (
 id TEXT PRIMARY KEY REFERENCES public_research_activity(id),
 publication_id TEXT NOT NULL REFERENCES public_discovery_evidence(publication_id),
 source_semantic_sha256 TEXT NOT NULL CHECK(length(source_semantic_sha256)=64),
 payload_sha256 TEXT NOT NULL CHECK(length(payload_sha256)=64),
 record_sha256 TEXT NOT NULL CHECK(length(record_sha256)=64),
 projection_sha256 TEXT NOT NULL CHECK(length(projection_sha256)=64),
 payload TEXT NOT NULL CHECK(json_valid(payload) AND length(CAST(payload AS BLOB))<=2048)
);
CREATE TABLE IF NOT EXISTS public_discovery_withdrawal_nodes (
 notice_id TEXT NOT NULL REFERENCES public_discovery_withdrawals(id),
 concept_id TEXT NOT NULL REFERENCES knowledge_documents(concept_id),
 PRIMARY KEY(notice_id,concept_id)
);
CREATE TRIGGER IF NOT EXISTS public_discovery_withdrawal_insert BEFORE INSERT ON public_discovery_withdrawals BEGIN
 SELECT CASE WHEN EXISTS(SELECT 1 FROM public_discovery_withdrawals old WHERE old.id=NEW.id AND
 (old.publication_id<>NEW.publication_id OR old.source_semantic_sha256<>NEW.source_semantic_sha256 OR old.payload_sha256<>NEW.payload_sha256
 OR old.record_sha256<>NEW.record_sha256 OR old.projection_sha256<>NEW.projection_sha256 OR old.payload<>NEW.payload))
 THEN RAISE(ABORT,'Source availability notice is immutable') END;
 SELECT CASE WHEN EXISTS(SELECT 1 FROM public_discovery_withdrawals WHERE id=NEW.id) THEN RAISE(IGNORE) END;
 SELECT CASE WHEN json_extract(NEW.payload,'$.schema') IS NOT 'lupine.discovery_source_withdrawal.v1'
 OR json_extract(NEW.payload,'$.producer') IS NOT 'lupine-research-team-v02'
 OR json_extract(NEW.payload,'$.id') IS NOT NEW.id
 OR json_extract(NEW.payload,'$.publicationId') IS NOT NEW.publication_id
 OR json_extract(NEW.payload,'$.sourceSemanticSha256') IS NOT NEW.source_semantic_sha256
 OR NOT EXISTS(SELECT 1 FROM public_discovery_evidence e WHERE e.publication_id=NEW.publication_id
 AND e.record_sha256=json_extract(NEW.payload,'$.recordSha256') AND e.evidence_sha256=json_extract(NEW.payload,'$.evidenceSha256')
 AND EXISTS(SELECT 1 FROM json_each(e.payload,'$.sources') s WHERE json_extract(s.value,'$.semanticSha256')=NEW.source_semantic_sha256))
 THEN RAISE(ABORT,'Source availability evidence mismatch') END;
END;
CREATE TRIGGER IF NOT EXISTS public_discovery_withdrawal_update BEFORE UPDATE ON public_discovery_withdrawals BEGIN SELECT RAISE(ABORT,'Source availability notice is immutable'); END;
CREATE TRIGGER IF NOT EXISTS public_discovery_withdrawal_delete BEFORE DELETE ON public_discovery_withdrawals BEGIN SELECT RAISE(ABORT,'Source availability notice is immutable'); END;
CREATE TRIGGER IF NOT EXISTS public_discovery_withdrawal_nodes_update BEFORE UPDATE ON public_discovery_withdrawal_nodes BEGIN SELECT RAISE(ABORT,'Source availability membership is immutable'); END;
CREATE TRIGGER IF NOT EXISTS public_discovery_withdrawal_nodes_delete BEFORE DELETE ON public_discovery_withdrawal_nodes BEGIN SELECT RAISE(ABORT,'Source availability membership is immutable'); END;
