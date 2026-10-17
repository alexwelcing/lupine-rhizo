-- One SQLite statement: all metrics share the same read snapshot; no payloads.
SELECT
 (SELECT COUNT(*) FROM public_research_activity) AS public_count,
 (SELECT COUNT(*) FROM public_activity_archive_sequence) AS archive_count,
 (SELECT COUNT(*) FROM public_research_activity a LEFT JOIN public_activity_archive_sequence s ON s.record_id=a.id WHERE s.record_id IS NULL) AS missing_sequence,
 (SELECT COUNT(*) FROM public_activity_archive_sequence s LEFT JOIN public_research_activity a ON a.id=s.record_id WHERE a.id IS NULL) AS orphan_sequence,
 (SELECT COUNT(*) FROM (SELECT record_id FROM public_activity_archive_sequence GROUP BY record_id HAVING COUNT(*)>1)) AS duplicate_records,
 (SELECT COUNT(*) FROM (SELECT sequence FROM public_activity_archive_sequence GROUP BY sequence HAVING COUNT(*)>1)) AS duplicate_sequences,
 (SELECT COUNT(*) FROM public_activity_archive_sequence WHERE sequence<=0 OR typeof(sequence)!='integer') AS invalid_sequences,
 (SELECT COUNT(*) FROM sqlite_master WHERE type='trigger' AND tbl_name='public_research_activity' AND name='public_activity_archive_append') AS append_trigger,
 (SELECT COUNT(*) FROM sqlite_master WHERE type='trigger' AND tbl_name='public_activity_archive_sequence' AND name IN ('public_activity_archive_no_update','public_activity_archive_no_delete')) AS immutable_triggers;
