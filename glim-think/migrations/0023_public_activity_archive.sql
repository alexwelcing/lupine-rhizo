-- Append-only ingestion order for already reviewed public records only.
-- Observation/review dates remain evidence timestamps, not pagination cursors.
CREATE TABLE IF NOT EXISTS public_activity_archive_sequence (
  sequence INTEGER PRIMARY KEY AUTOINCREMENT,
  record_id TEXT NOT NULL UNIQUE REFERENCES public_research_activity(id)
);
INSERT INTO public_activity_archive_sequence(record_id)
  SELECT a.id FROM public_research_activity a
  WHERE NOT EXISTS (SELECT 1 FROM public_activity_archive_sequence s WHERE s.record_id = a.id)
  ORDER BY a.imported_at ASC, a.id ASC;
CREATE TRIGGER IF NOT EXISTS public_activity_archive_append
  AFTER INSERT ON public_research_activity BEGIN
    INSERT INTO public_activity_archive_sequence(record_id) VALUES (NEW.id);
  END;
CREATE TRIGGER IF NOT EXISTS public_activity_archive_no_update
  BEFORE UPDATE ON public_activity_archive_sequence BEGIN
    SELECT RAISE(ABORT, 'Public activity archive sequence is immutable');
  END;
CREATE TRIGGER IF NOT EXISTS public_activity_archive_no_delete
  BEFORE DELETE ON public_activity_archive_sequence BEGIN
    SELECT RAISE(ABORT, 'Public activity archive sequence is immutable');
  END;
