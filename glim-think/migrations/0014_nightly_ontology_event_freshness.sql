-- Migration 0014: replace the 0013 transition guard so already-migrated D1
-- databases require the event appended immediately before each ontology update.
-- Editing 0013 alone would not update a trigger on databases that recorded it.

DROP TRIGGER IF EXISTS literature_hypothesis_evidence_guard;

CREATE TRIGGER literature_hypothesis_evidence_guard
BEFORE UPDATE OF contract_json ON literature_hypotheses
WHEN OLD.status <> json_extract(NEW.contract_json, '$.status')
  OR OLD.readiness <> json_extract(NEW.contract_json, '$.readiness')
BEGIN
  SELECT CASE WHEN NOT EXISTS (
    SELECT 1
      FROM status_event AS event
     WHERE event.entity_type = 'literature_hypothesis'
       AND event.entity_id = OLD.literature_hypothesis_id
       AND event.from_status = OLD.status
       AND event.to_status = json_extract(NEW.contract_json, '$.status')
       AND event.evidence_bundle_id IS NOT NULL
       AND json_extract(event.metadata_json, '$.from_readiness') = OLD.readiness
       AND json_extract(event.metadata_json, '$.to_readiness') = json_extract(NEW.contract_json, '$.readiness')
       AND event.rowid = (
         SELECT max(latest.rowid)
           FROM status_event AS latest
          WHERE latest.entity_type = 'literature_hypothesis'
            AND latest.entity_id = OLD.literature_hypothesis_id
       )
  ) THEN RAISE(ABORT, 'literature hypothesis status/readiness change requires a new EvidenceBundle event') END;
END;
