-- Synthetic UI fixtures only, in an isolated local preview database.
CREATE TABLE IF NOT EXISTS hypotheses (id TEXT PRIMARY KEY, title TEXT, status TEXT, confidence REAL, evidence_ids TEXT, updated_at TEXT);
CREATE TABLE IF NOT EXISTS literature_papers (doi TEXT PRIMARY KEY, arxiv_id TEXT, title TEXT, abstract TEXT, year INTEGER, source TEXT, fetched_at TEXT);
CREATE TABLE IF NOT EXISTS lab_beats (beat_id TEXT PRIMARY KEY, agent TEXT, summary TEXT, ts TEXT);
INSERT OR IGNORE INTO hypotheses VALUES ('preview-hypothesis-1', 'Synthetic hypothesis: interface evidence readability', 'proposed', 0.2, '["preview-paper-1"]', '2026-10-05T12:00:00Z');
INSERT OR IGNORE INTO literature_papers VALUES ('preview-paper-1', NULL, 'Synthetic paper: conversation continuity fixture', 'This is invented test data for interface verification. It is not a real publication or scientific evidence.', 2026, 'local-preview', '2026-10-05T12:00:00Z');
INSERT OR IGNORE INTO lab_beats VALUES ('preview-activity-1', 'local-preview', 'Synthetic activity: no experiment was run; this row exists only to exercise evidence rendering.', '2026-10-05T12:00:00Z');
