-- 0004_claims.sql
-- Bring the existing `claims` table up to parity with the archived lupine-distill Rust crate's
-- claims schema so the worker can be the canonical home for adjudicated
-- research verdicts (CrossStyleAlignment, DimensionalityRanking,
-- ManifoldEvolution, HyperRibbonConfirmed, ...).
--
-- The bootstrap `schema.sql` created `claims` with columns:
--   claim_id, agent_id, claim_type, evidence_ids, confidence, status,
--   timestamp, description
--
-- the archived lupine-distill Rust crate wrote via columns:
--   claim_id, agent_id, claim_type, claim_data, evidence_ids, confidence,
--   status, description, created_at
--
-- This migration rebuilds the table to add the two missing columns (claim_data, created_at),
-- backfills created_at from the existing `timestamp`, and adds indexes.
-- Distill is the producer (write side); the worker is the consumer (read
-- side, via /claims, /lab dashboard, Theorist, Critique-drain cron).
--
-- The rebuild is idempotent: running it twice simply re-copies rows into the
-- new table. The legacy `timestamp` column is retained as nullable so the
-- backfill expression remains valid on re-runs.

-- Ensure a claims table exists so the SELECT below has a source on fresh DBs.
CREATE TABLE IF NOT EXISTS claims (
  claim_id TEXT PRIMARY KEY,
  agent_id TEXT,
  claim_type TEXT,
  evidence_ids TEXT,
  confidence REAL,
  status TEXT,
  timestamp TEXT,
  description TEXT
);

CREATE TABLE IF NOT EXISTS claims_migrated (
  claim_id TEXT PRIMARY KEY,
  agent_id TEXT,
  claim_type TEXT,
  claim_data TEXT NOT NULL DEFAULT '{}',
  evidence_ids TEXT,
  confidence REAL,
  status TEXT,
  description TEXT,
  timestamp TEXT,
  created_at TEXT
);

INSERT OR IGNORE INTO claims_migrated
  (claim_id, agent_id, claim_type, claim_data, evidence_ids, confidence, status, description, timestamp, created_at)
SELECT
  claim_id,
  agent_id,
  claim_type,
  '{}',
  evidence_ids,
  confidence,
  status,
  description,
  timestamp,
  COALESCE(timestamp, strftime('%Y-%m-%dT%H:%M:%SZ','now'))
FROM claims;

DROP TABLE IF EXISTS claims;
ALTER TABLE claims_migrated RENAME TO claims;

CREATE INDEX IF NOT EXISTS idx_claims_status     ON claims(status);
CREATE INDEX IF NOT EXISTS idx_claims_type       ON claims(claim_type);
CREATE INDEX IF NOT EXISTS idx_claims_agent      ON claims(agent_id);
CREATE INDEX IF NOT EXISTS idx_claims_created_at ON claims(created_at DESC);
