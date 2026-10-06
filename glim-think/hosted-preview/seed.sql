-- Apply only to the new lupine-workspace-preview-ledger database.
-- Synthetic interface fixtures; these are not scientific claims or publications.
CREATE TABLE IF NOT EXISTS hypotheses (id TEXT PRIMARY KEY, title TEXT, status TEXT, confidence REAL, evidence_ids TEXT, updated_at TEXT);
CREATE TABLE IF NOT EXISTS literature_papers (doi TEXT PRIMARY KEY, arxiv_id TEXT, title TEXT, abstract TEXT, year INTEGER, source TEXT, fetched_at TEXT);
CREATE TABLE IF NOT EXISTS lab_beats (beat_id TEXT PRIMARY KEY, agent TEXT, summary TEXT, ts TEXT);
INSERT OR IGNORE INTO hypotheses VALUES ('preview-hypothesis-1', 'Synthetic hypothesis: interface evidence readability', 'proposed', 0.2, '["preview-paper-1"]', '2026-10-05T12:00:00Z');
INSERT OR IGNORE INTO literature_papers VALUES ('preview-paper-1', NULL, 'Synthetic paper: conversation continuity fixture', 'Invented test data for interface verification. Not a real publication or scientific evidence.', 2026, 'hosted-preview', '2026-10-05T12:00:00Z');
INSERT OR IGNORE INTO lab_beats VALUES ('preview-activity-1', 'hosted-preview', 'Synthetic activity: no experiment was run. This row only exercises evidence rendering.', '2026-10-05T12:00:00Z');
