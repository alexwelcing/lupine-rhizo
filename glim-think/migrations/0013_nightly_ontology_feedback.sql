-- Migration 0013: nightly evidence-to-ontology feedback in the existing D1 ledger.

-- Every supersession edge is durable: the 0011 single-column FK keeps the
-- first predecessor for compatibility, while the full unique predecessor set
-- (the EvidenceBundle v1 schema permits an array) lands here.
ALTER TABLE evidence_bundle ADD COLUMN supersedes_bundle_ids_json TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(supersedes_bundle_ids_json));

CREATE TABLE IF NOT EXISTS literature_reprioritization_queue (
  cycle_date TEXT NOT NULL,
  literature_hypothesis_id TEXT NOT NULL
    REFERENCES literature_hypotheses(literature_hypothesis_id) ON DELETE CASCADE,
  chain_id TEXT NOT NULL CHECK (chain_id GLOB 'C[1-9]' OR chain_id GLOB 'C1[01]'),
  chain_priority INTEGER NOT NULL CHECK (chain_priority BETWEEN 1 AND 11),
  query TEXT NOT NULL,
  reason TEXT NOT NULL,
  evidence_gap_json TEXT NOT NULL CHECK (json_valid(evidence_gap_json)),
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
  PRIMARY KEY (cycle_date, literature_hypothesis_id, chain_id)
);

CREATE INDEX IF NOT EXISTS literature_reprioritization_priority_idx
  ON literature_reprioritization_queue(cycle_date, chain_priority, literature_hypothesis_id);

-- One immutable bundle may authorize at most one lifecycle/readiness transition
-- for a hypothesis. Reusing a receipt would launder a second status change.
CREATE UNIQUE INDEX IF NOT EXISTS literature_hypothesis_status_bundle_once
  ON status_event(entity_id, evidence_bundle_id)
  WHERE entity_type = 'literature_hypothesis' AND evidence_bundle_id IS NOT NULL;

CREATE TRIGGER IF NOT EXISTS literature_hypothesis_evidence_guard
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
  ) THEN RAISE(ABORT, 'literature hypothesis status/readiness change requires a new EvidenceBundle event') END;
END;
