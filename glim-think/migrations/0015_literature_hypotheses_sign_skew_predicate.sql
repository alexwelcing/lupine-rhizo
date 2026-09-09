-- Migration 0015: admit the T1 protocol-offset sign-skew typed predicate
-- (signed_error_positive_fraction>0.5) and its matching metric
-- (signed_error_positive). SQLite cannot alter a column CHECK constraint, so
-- the table is rebuilt with the extended predicate whitelist; the contract
-- validation trigger is replaced to admit the new metric; the 0012 contract
-- triggers, the 0014 freshness guard, and the indexes are recreated.

PRAGMA foreign_keys = OFF;

CREATE TABLE literature_hypotheses_new (
  -- TEXT PRIMARY KEY on a rowid table does not imply NOT NULL in SQLite/D1;
  -- declare it so the stable identifier can never be NULL.
  literature_hypothesis_id TEXT PRIMARY KEY NOT NULL,
  contract_json TEXT NOT NULL
    CHECK (json_valid(contract_json) AND json_type(contract_json) = 'object'),
  source_json TEXT GENERATED ALWAYS AS
    (json_extract(contract_json, '$.source')) STORED NOT NULL
    CHECK (json_type(contract_json, '$.source') = 'object'),
  claim_text TEXT GENERATED ALWAYS AS
    (json_extract(contract_json, '$.claim_text')) STORED NOT NULL
    CHECK (
      json_type(contract_json, '$.claim_text') = 'text'
      AND length(trim(
        claim_text,
        char(9) || char(10) || char(11) || char(12) || char(13)
        || char(28) || char(29) || char(30) || char(31) || char(32)
        || char(133) || char(160) || char(5760) || char(8192) || char(8193)
        || char(8194) || char(8195) || char(8196) || char(8197) || char(8198)
        || char(8199) || char(8200) || char(8201) || char(8202) || char(8232)
        || char(8233) || char(8239) || char(8287) || char(12288)
      )) > 0
    ),
  bindings_json TEXT GENERATED ALWAYS AS
    (json_extract(contract_json, '$.bindings')) STORED NOT NULL
    CHECK (
      json_type(contract_json, '$.bindings') = 'object'
      AND json_type(contract_json, '$.bindings.errorTypes') = 'array'
      AND json_array_length(contract_json, '$.bindings.errorTypes') > 0
      AND json_type(contract_json, '$.bindings.materialClasses') = 'array'
      AND json_array_length(contract_json, '$.bindings.materialClasses') > 0
      AND json_type(contract_json, '$.bindings.chains') = 'array'
      AND json_array_length(contract_json, '$.bindings.chains') > 0
      AND json_type(contract_json, '$.bindings.acceptanceTests') = 'array'
      AND json_array_length(contract_json, '$.bindings.acceptanceTests') > 0
    ),
  epistemic_marker TEXT GENERATED ALWAYS AS
    (json_extract(contract_json, '$.epistemicMarker')) STORED NOT NULL
    CHECK (epistemic_marker IN ('OBS', 'INF', 'TRN', 'PRP', 'FRC')),
  readiness TEXT GENERATED ALWAYS AS
    (json_extract(contract_json, '$.readiness')) STORED NOT NULL
    CHECK (
    readiness IN ('H', 'M', 'L')
    OR (
      readiness GLOB '[HML] (*)'
      AND length(readiness) > 4
      AND substr(readiness, 4, length(readiness) - 4) NOT GLOB '*[()]*'
      AND trim(
        substr(readiness, 4, length(readiness) - 4),
        char(9) || char(10) || char(11) || char(12) || char(13)
        || char(28) || char(29) || char(30) || char(31) || char(32)
        || char(133) || char(160) || char(5760) || char(8192) || char(8193)
        || char(8194) || char(8195) || char(8196) || char(8197) || char(8198)
        || char(8199) || char(8200) || char(8201) || char(8202) || char(8232)
        || char(8233) || char(8239) || char(8287) || char(12288)
      ) <> ''
    )
    ),
  confidence TEXT GENERATED ALWAYS AS
    (json_extract(contract_json, '$.confidence')) STORED NOT NULL
    CHECK (confidence IN ('High', 'Medium')),
  proposed_experiment_json TEXT GENERATED ALWAYS AS
    (json_extract(contract_json, '$.proposedExperiment')) STORED NOT NULL
    CHECK (json_type(contract_json, '$.proposedExperiment') = 'object'),
  proposed_experiment_predicate TEXT GENERATED ALWAYS AS
    (json_extract(contract_json, '$.proposedExperiment.predicate')) STORED NOT NULL
    CHECK (proposed_experiment_predicate IN ('barrier_mae_mev<=40', 'signed_error_positive_fraction>0.5')),
  status TEXT GENERATED ALWAYS AS
    (json_extract(contract_json, '$.status')) STORED NOT NULL
    CHECK (status IN ('proposed', 'accepted', 'rejected', 'superseded')),
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
  updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

INSERT INTO literature_hypotheses_new (literature_hypothesis_id, contract_json, created_at, updated_at)
  SELECT literature_hypothesis_id, contract_json, created_at, updated_at
    FROM literature_hypotheses;

DROP TABLE literature_hypotheses;
-- ALTER TABLE reparses all surviving triggers with extra expression depth.
-- Drop the 0012 validator before renaming; its shallow replacement is below.
DROP TRIGGER IF EXISTS literature_hypothesis_contract_validate;
ALTER TABLE literature_hypotheses_new RENAME TO literature_hypotheses;

CREATE TRIGGER literature_hypotheses_contract_insert
BEFORE INSERT ON literature_hypotheses
BEGIN
  INSERT INTO literature_hypothesis_contract_validation (contract_json)
  VALUES (NEW.contract_json);
END;

CREATE TRIGGER literature_hypotheses_contract_update
BEFORE UPDATE OF contract_json ON literature_hypotheses
BEGIN
  INSERT INTO literature_hypothesis_contract_validation (contract_json)
  VALUES (NEW.contract_json);
END;

CREATE TRIGGER literature_hypothesis_evidence_guard
BEFORE UPDATE OF contract_json ON literature_hypotheses
WHEN OLD.status <> json_extract(NEW.contract_json, '$.status')
  OR OLD.readiness <> json_extract(NEW.contract_json, '$.readiness')
BEGIN
  SELECT RAISE(ABORT, 'literature hypothesis status/readiness change requires a new EvidenceBundle event')
  WHERE NOT EXISTS (
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
  );
END;

CREATE INDEX idx_literature_hypotheses_status
  ON literature_hypotheses(status);
CREATE INDEX idx_literature_hypotheses_readiness
  ON literature_hypotheses(readiness);
CREATE INDEX idx_literature_hypotheses_predicate
  ON literature_hypotheses(proposed_experiment_predicate);

CREATE TRIGGER literature_hypothesis_contract_validate
INSTEAD OF INSERT ON literature_hypothesis_contract_validation
BEGIN
  -- Keep rejection clauses in separate statements for D1's expression-depth
  -- limit. Preserve clause order and nested AND conditions (including NULLs).
  SELECT RAISE(ABORT, 'invalid LiteratureHypothesis top-level contract')
  WHERE
    (SELECT count(*) FROM json_each(NEW.contract_json)) <> 8;

  SELECT RAISE(ABORT, 'invalid LiteratureHypothesis top-level contract')
  WHERE
    EXISTS (
      SELECT 1 FROM json_each(NEW.contract_json)
      WHERE key NOT IN (
        'source', 'claim_text', 'bindings', 'epistemicMarker', 'readiness',
        'confidence', 'proposedExperiment', 'status'
      )
    );

  SELECT RAISE(ABORT, 'invalid LiteratureHypothesis source')
  WHERE
    (SELECT count(*) FROM json_each(NEW.contract_json, '$.source')) <> 6;

  SELECT RAISE(ABORT, 'invalid LiteratureHypothesis source')
  WHERE
    EXISTS (
      SELECT 1 FROM json_each(NEW.contract_json, '$.source')
      WHERE key NOT IN ('arxiv_id', 'openalex_id', 'ss_id', 'doi', 'url', 'asOf')
    );

  SELECT RAISE(ABORT, 'invalid LiteratureHypothesis source')
  WHERE
    json_type(NEW.contract_json, '$.source.arxiv_id') NOT IN ('text', 'null');

  SELECT RAISE(ABORT, 'invalid LiteratureHypothesis source')
  WHERE
    json_type(NEW.contract_json, '$.source.openalex_id') NOT IN ('text', 'null');

  SELECT RAISE(ABORT, 'invalid LiteratureHypothesis source')
  WHERE
    json_type(NEW.contract_json, '$.source.ss_id') NOT IN ('text', 'null');

  SELECT RAISE(ABORT, 'invalid LiteratureHypothesis source')
  WHERE
    json_type(NEW.contract_json, '$.source.doi') NOT IN ('text', 'null');

  SELECT RAISE(ABORT, 'invalid LiteratureHypothesis source')
  WHERE
    json_type(NEW.contract_json, '$.source.url') <> 'text';

  SELECT RAISE(ABORT, 'invalid LiteratureHypothesis source')
  WHERE
    json_type(NEW.contract_json, '$.source.asOf') <> 'text';

  SELECT RAISE(ABORT, 'invalid LiteratureHypothesis source')
  WHERE
    (
      json_type(NEW.contract_json, '$.source.arxiv_id') = 'null'
      AND json_type(NEW.contract_json, '$.source.openalex_id') = 'null'
      AND json_type(NEW.contract_json, '$.source.ss_id') = 'null'
      AND json_type(NEW.contract_json, '$.source.doi') = 'null'
    );

  SELECT RAISE(ABORT, 'invalid LiteratureHypothesis source')
  WHERE
    EXISTS (
      SELECT 1 FROM json_each(NEW.contract_json, '$.source')
      WHERE type = 'text'
        AND length(trim(
          value,
          (char(9) || char(10) || char(11) || char(12) || char(13))
        || (char(28) || char(29) || char(30) || char(31) || char(32))
        || (char(133) || char(160) || char(5760) || char(8192) || char(8193))
        || (char(8194) || char(8195) || char(8196) || char(8197) || char(8198))
        || (char(8199) || char(8200) || char(8201) || char(8202) || char(8232))
        || (char(8233) || char(8239) || char(8287) || char(12288))
        )) = 0
    );

  SELECT RAISE(ABORT, 'invalid LiteratureHypothesis source')
  WHERE json_type(NEW.contract_json, '$.source.doi') = 'text'
    AND (substr(json_extract(NEW.contract_json, '$.source.doi'), 1, 3) <> '10.');

  SELECT RAISE(ABORT, 'invalid LiteratureHypothesis source')
  WHERE json_type(NEW.contract_json, '$.source.doi') = 'text'
    AND (instr(json_extract(NEW.contract_json, '$.source.doi'), '/') < 8);

  SELECT RAISE(ABORT, 'invalid LiteratureHypothesis source')
  WHERE json_type(NEW.contract_json, '$.source.doi') = 'text'
    AND (length(substr(
          json_extract(NEW.contract_json, '$.source.doi'), 4,
          instr(json_extract(NEW.contract_json, '$.source.doi'), '/') - 4
        )) NOT BETWEEN 4 AND 9);

  SELECT RAISE(ABORT, 'invalid LiteratureHypothesis source')
  WHERE json_type(NEW.contract_json, '$.source.doi') = 'text'
    AND (substr(
          json_extract(NEW.contract_json, '$.source.doi'), 4,
          instr(json_extract(NEW.contract_json, '$.source.doi'), '/') - 4
        ) GLOB '*[^0-9]*');

  SELECT RAISE(ABORT, 'invalid LiteratureHypothesis source')
  WHERE json_type(NEW.contract_json, '$.source.doi') = 'text'
    AND (length(substr(
          json_extract(NEW.contract_json, '$.source.doi'),
          instr(json_extract(NEW.contract_json, '$.source.doi'), '/') + 1
        )) = 0);

  SELECT RAISE(ABORT, 'invalid LiteratureHypothesis source')
  WHERE json_type(NEW.contract_json, '$.source.doi') = 'text'
    AND (instr(json_extract(NEW.contract_json, '$.source.doi'), char(9)) > 0);

  SELECT RAISE(ABORT, 'invalid LiteratureHypothesis source')
  WHERE json_type(NEW.contract_json, '$.source.doi') = 'text'
    AND (instr(json_extract(NEW.contract_json, '$.source.doi'), char(10)) > 0);

  SELECT RAISE(ABORT, 'invalid LiteratureHypothesis source')
  WHERE json_type(NEW.contract_json, '$.source.doi') = 'text'
    AND (instr(json_extract(NEW.contract_json, '$.source.doi'), char(11)) > 0);

  SELECT RAISE(ABORT, 'invalid LiteratureHypothesis source')
  WHERE json_type(NEW.contract_json, '$.source.doi') = 'text'
    AND (instr(json_extract(NEW.contract_json, '$.source.doi'), char(12)) > 0);

  SELECT RAISE(ABORT, 'invalid LiteratureHypothesis source')
  WHERE json_type(NEW.contract_json, '$.source.doi') = 'text'
    AND (instr(json_extract(NEW.contract_json, '$.source.doi'), char(13)) > 0);

  SELECT RAISE(ABORT, 'invalid LiteratureHypothesis source')
  WHERE json_type(NEW.contract_json, '$.source.doi') = 'text'
    AND (instr(json_extract(NEW.contract_json, '$.source.doi'), char(28)) > 0);

  SELECT RAISE(ABORT, 'invalid LiteratureHypothesis source')
  WHERE json_type(NEW.contract_json, '$.source.doi') = 'text'
    AND (instr(json_extract(NEW.contract_json, '$.source.doi'), char(29)) > 0);

  SELECT RAISE(ABORT, 'invalid LiteratureHypothesis source')
  WHERE json_type(NEW.contract_json, '$.source.doi') = 'text'
    AND (instr(json_extract(NEW.contract_json, '$.source.doi'), char(30)) > 0);

  SELECT RAISE(ABORT, 'invalid LiteratureHypothesis source')
  WHERE json_type(NEW.contract_json, '$.source.doi') = 'text'
    AND (instr(json_extract(NEW.contract_json, '$.source.doi'), char(31)) > 0);

  SELECT RAISE(ABORT, 'invalid LiteratureHypothesis source')
  WHERE json_type(NEW.contract_json, '$.source.doi') = 'text'
    AND (instr(json_extract(NEW.contract_json, '$.source.doi'), char(32)) > 0);

  SELECT RAISE(ABORT, 'invalid LiteratureHypothesis source')
  WHERE json_type(NEW.contract_json, '$.source.doi') = 'text'
    AND (instr(json_extract(NEW.contract_json, '$.source.doi'), char(133)) > 0);

  SELECT RAISE(ABORT, 'invalid LiteratureHypothesis source')
  WHERE json_type(NEW.contract_json, '$.source.doi') = 'text'
    AND (instr(json_extract(NEW.contract_json, '$.source.doi'), char(160)) > 0);

  SELECT RAISE(ABORT, 'invalid LiteratureHypothesis source')
  WHERE json_type(NEW.contract_json, '$.source.doi') = 'text'
    AND (instr(json_extract(NEW.contract_json, '$.source.doi'), char(5760)) > 0);

  SELECT RAISE(ABORT, 'invalid LiteratureHypothesis source')
  WHERE json_type(NEW.contract_json, '$.source.doi') = 'text'
    AND (instr(json_extract(NEW.contract_json, '$.source.doi'), char(8192)) > 0);

  SELECT RAISE(ABORT, 'invalid LiteratureHypothesis source')
  WHERE json_type(NEW.contract_json, '$.source.doi') = 'text'
    AND (instr(json_extract(NEW.contract_json, '$.source.doi'), char(8193)) > 0);

  SELECT RAISE(ABORT, 'invalid LiteratureHypothesis source')
  WHERE json_type(NEW.contract_json, '$.source.doi') = 'text'
    AND (instr(json_extract(NEW.contract_json, '$.source.doi'), char(8194)) > 0);

  SELECT RAISE(ABORT, 'invalid LiteratureHypothesis source')
  WHERE json_type(NEW.contract_json, '$.source.doi') = 'text'
    AND (instr(json_extract(NEW.contract_json, '$.source.doi'), char(8195)) > 0);

  SELECT RAISE(ABORT, 'invalid LiteratureHypothesis source')
  WHERE json_type(NEW.contract_json, '$.source.doi') = 'text'
    AND (instr(json_extract(NEW.contract_json, '$.source.doi'), char(8196)) > 0);

  SELECT RAISE(ABORT, 'invalid LiteratureHypothesis source')
  WHERE json_type(NEW.contract_json, '$.source.doi') = 'text'
    AND (instr(json_extract(NEW.contract_json, '$.source.doi'), char(8197)) > 0);

  SELECT RAISE(ABORT, 'invalid LiteratureHypothesis source')
  WHERE json_type(NEW.contract_json, '$.source.doi') = 'text'
    AND (instr(json_extract(NEW.contract_json, '$.source.doi'), char(8198)) > 0);

  SELECT RAISE(ABORT, 'invalid LiteratureHypothesis source')
  WHERE json_type(NEW.contract_json, '$.source.doi') = 'text'
    AND (instr(json_extract(NEW.contract_json, '$.source.doi'), char(8199)) > 0);

  SELECT RAISE(ABORT, 'invalid LiteratureHypothesis source')
  WHERE json_type(NEW.contract_json, '$.source.doi') = 'text'
    AND (instr(json_extract(NEW.contract_json, '$.source.doi'), char(8200)) > 0);

  SELECT RAISE(ABORT, 'invalid LiteratureHypothesis source')
  WHERE json_type(NEW.contract_json, '$.source.doi') = 'text'
    AND (instr(json_extract(NEW.contract_json, '$.source.doi'), char(8201)) > 0);

  SELECT RAISE(ABORT, 'invalid LiteratureHypothesis source')
  WHERE json_type(NEW.contract_json, '$.source.doi') = 'text'
    AND (instr(json_extract(NEW.contract_json, '$.source.doi'), char(8202)) > 0);

  SELECT RAISE(ABORT, 'invalid LiteratureHypothesis source')
  WHERE json_type(NEW.contract_json, '$.source.doi') = 'text'
    AND (instr(json_extract(NEW.contract_json, '$.source.doi'), char(8232)) > 0);

  SELECT RAISE(ABORT, 'invalid LiteratureHypothesis source')
  WHERE json_type(NEW.contract_json, '$.source.doi') = 'text'
    AND (instr(json_extract(NEW.contract_json, '$.source.doi'), char(8233)) > 0);

  SELECT RAISE(ABORT, 'invalid LiteratureHypothesis source')
  WHERE json_type(NEW.contract_json, '$.source.doi') = 'text'
    AND (instr(json_extract(NEW.contract_json, '$.source.doi'), char(8239)) > 0);

  SELECT RAISE(ABORT, 'invalid LiteratureHypothesis source')
  WHERE json_type(NEW.contract_json, '$.source.doi') = 'text'
    AND (instr(json_extract(NEW.contract_json, '$.source.doi'), char(8287)) > 0);

  SELECT RAISE(ABORT, 'invalid LiteratureHypothesis source')
  WHERE json_type(NEW.contract_json, '$.source.doi') = 'text'
    AND (instr(json_extract(NEW.contract_json, '$.source.doi'), char(12288)) > 0);

  -- The JSON Schema also constrains source.url with format "uri". D1 cannot
  -- parse URIs, so reject the malformed shapes that pass a bare prefix
  -- check: empty host, whitespace/control characters, and bracketed
  -- IP-literal hosts (out of scope for provenance links).

  SELECT RAISE(ABORT, 'invalid LiteratureHypothesis source')
  WHERE
    substr(json_extract(NEW.contract_json, '$.source.url'), 1, 8) <> 'https://';

  SELECT RAISE(ABORT, 'invalid LiteratureHypothesis source')
  WHERE
    length(json_extract(NEW.contract_json, '$.source.url')) = 8;

  SELECT RAISE(ABORT, 'invalid LiteratureHypothesis source')
  WHERE
    instr(json_extract(NEW.contract_json, '$.source.url'), char(9)) > 0;

  SELECT RAISE(ABORT, 'invalid LiteratureHypothesis source')
  WHERE
    instr(json_extract(NEW.contract_json, '$.source.url'), char(10)) > 0;

  SELECT RAISE(ABORT, 'invalid LiteratureHypothesis source')
  WHERE
    instr(json_extract(NEW.contract_json, '$.source.url'), char(11)) > 0;

  SELECT RAISE(ABORT, 'invalid LiteratureHypothesis source')
  WHERE
    instr(json_extract(NEW.contract_json, '$.source.url'), char(12)) > 0;

  SELECT RAISE(ABORT, 'invalid LiteratureHypothesis source')
  WHERE
    instr(json_extract(NEW.contract_json, '$.source.url'), char(13)) > 0;

  SELECT RAISE(ABORT, 'invalid LiteratureHypothesis source')
  WHERE
    instr(json_extract(NEW.contract_json, '$.source.url'), char(28)) > 0;

  SELECT RAISE(ABORT, 'invalid LiteratureHypothesis source')
  WHERE
    instr(json_extract(NEW.contract_json, '$.source.url'), char(29)) > 0;

  SELECT RAISE(ABORT, 'invalid LiteratureHypothesis source')
  WHERE
    instr(json_extract(NEW.contract_json, '$.source.url'), char(30)) > 0;

  SELECT RAISE(ABORT, 'invalid LiteratureHypothesis source')
  WHERE
    instr(json_extract(NEW.contract_json, '$.source.url'), char(31)) > 0;

  SELECT RAISE(ABORT, 'invalid LiteratureHypothesis source')
  WHERE
    instr(json_extract(NEW.contract_json, '$.source.url'), char(32)) > 0;

  SELECT RAISE(ABORT, 'invalid LiteratureHypothesis source')
  WHERE
    instr(json_extract(NEW.contract_json, '$.source.url'), char(133)) > 0;

  SELECT RAISE(ABORT, 'invalid LiteratureHypothesis source')
  WHERE
    instr(json_extract(NEW.contract_json, '$.source.url'), char(160)) > 0;

  SELECT RAISE(ABORT, 'invalid LiteratureHypothesis source')
  WHERE
    instr(json_extract(NEW.contract_json, '$.source.url'), char(5760)) > 0;

  SELECT RAISE(ABORT, 'invalid LiteratureHypothesis source')
  WHERE
    instr(json_extract(NEW.contract_json, '$.source.url'), char(8192)) > 0;

  SELECT RAISE(ABORT, 'invalid LiteratureHypothesis source')
  WHERE
    instr(json_extract(NEW.contract_json, '$.source.url'), char(8193)) > 0;

  SELECT RAISE(ABORT, 'invalid LiteratureHypothesis source')
  WHERE
    instr(json_extract(NEW.contract_json, '$.source.url'), char(8194)) > 0;

  SELECT RAISE(ABORT, 'invalid LiteratureHypothesis source')
  WHERE
    instr(json_extract(NEW.contract_json, '$.source.url'), char(8195)) > 0;

  SELECT RAISE(ABORT, 'invalid LiteratureHypothesis source')
  WHERE
    instr(json_extract(NEW.contract_json, '$.source.url'), char(8196)) > 0;

  SELECT RAISE(ABORT, 'invalid LiteratureHypothesis source')
  WHERE
    instr(json_extract(NEW.contract_json, '$.source.url'), char(8197)) > 0;

  SELECT RAISE(ABORT, 'invalid LiteratureHypothesis source')
  WHERE
    instr(json_extract(NEW.contract_json, '$.source.url'), char(8198)) > 0;

  SELECT RAISE(ABORT, 'invalid LiteratureHypothesis source')
  WHERE
    instr(json_extract(NEW.contract_json, '$.source.url'), char(8199)) > 0;

  SELECT RAISE(ABORT, 'invalid LiteratureHypothesis source')
  WHERE
    instr(json_extract(NEW.contract_json, '$.source.url'), char(8200)) > 0;

  SELECT RAISE(ABORT, 'invalid LiteratureHypothesis source')
  WHERE
    instr(json_extract(NEW.contract_json, '$.source.url'), char(8201)) > 0;

  SELECT RAISE(ABORT, 'invalid LiteratureHypothesis source')
  WHERE
    instr(json_extract(NEW.contract_json, '$.source.url'), char(8202)) > 0;

  SELECT RAISE(ABORT, 'invalid LiteratureHypothesis source')
  WHERE
    instr(json_extract(NEW.contract_json, '$.source.url'), char(8232)) > 0;

  SELECT RAISE(ABORT, 'invalid LiteratureHypothesis source')
  WHERE
    instr(json_extract(NEW.contract_json, '$.source.url'), char(8233)) > 0;

  SELECT RAISE(ABORT, 'invalid LiteratureHypothesis source')
  WHERE
    instr(json_extract(NEW.contract_json, '$.source.url'), char(8239)) > 0;

  SELECT RAISE(ABORT, 'invalid LiteratureHypothesis source')
  WHERE
    instr(json_extract(NEW.contract_json, '$.source.url'), char(8287)) > 0;

  SELECT RAISE(ABORT, 'invalid LiteratureHypothesis source')
  WHERE
    instr(json_extract(NEW.contract_json, '$.source.url'), char(12288)) > 0;

  SELECT RAISE(ABORT, 'invalid LiteratureHypothesis source')
  WHERE
    instr(json_extract(NEW.contract_json, '$.source.url'), '[') > 0;

  SELECT RAISE(ABORT, 'invalid LiteratureHypothesis source')
  WHERE
    instr(json_extract(NEW.contract_json, '$.source.url'), ']') > 0;

  SELECT RAISE(ABORT, 'invalid LiteratureHypothesis source')
  WHERE
    length(json_extract(NEW.contract_json, '$.source.asOf')) <> 10;

  SELECT RAISE(ABORT, 'invalid LiteratureHypothesis source')
  WHERE
    json_extract(NEW.contract_json, '$.source.asOf')
      GLOB '*[^0-9-]*';

  SELECT RAISE(ABORT, 'invalid LiteratureHypothesis source')
  WHERE
    substr(json_extract(NEW.contract_json, '$.source.asOf'), 5, 1) <> '-';

  SELECT RAISE(ABORT, 'invalid LiteratureHypothesis source')
  WHERE
    substr(json_extract(NEW.contract_json, '$.source.asOf'), 8, 1) <> '-';

  SELECT RAISE(ABORT, 'invalid LiteratureHypothesis source')
  WHERE
    CAST(substr(json_extract(NEW.contract_json, '$.source.asOf'), 1, 4) AS INTEGER) < 1;

  SELECT RAISE(ABORT, 'invalid LiteratureHypothesis source')
  WHERE
    CAST(substr(json_extract(NEW.contract_json, '$.source.asOf'), 6, 2) AS INTEGER)
      NOT BETWEEN 1 AND 12;

  SELECT RAISE(ABORT, 'invalid LiteratureHypothesis source')
  WHERE
    CAST(substr(json_extract(NEW.contract_json, '$.source.asOf'), 9, 2) AS INTEGER)
      NOT BETWEEN 1 AND 31;

  SELECT RAISE(ABORT, 'invalid LiteratureHypothesis source')
  WHERE
    CAST(substr(json_extract(NEW.contract_json, '$.source.asOf'), 9, 2) AS INTEGER) >
      (31
        - coalesce(CAST(substr(json_extract(NEW.contract_json, '$.source.asOf'), 6, 2) AS INTEGER) IN (4, 6, 9, 11), 0)
        - coalesce(CAST(substr(json_extract(NEW.contract_json, '$.source.asOf'), 6, 2) AS INTEGER) = 2, 0)
          * (3 - coalesce(
          CAST(substr(json_extract(NEW.contract_json, '$.source.asOf'), 1, 4) AS INTEGER) % 400 = 0
          OR (
            CAST(substr(json_extract(NEW.contract_json, '$.source.asOf'), 1, 4) AS INTEGER) % 4 = 0
            AND CAST(substr(json_extract(NEW.contract_json, '$.source.asOf'), 1, 4) AS INTEGER) % 100 <> 0
          )
          , 0))
      );

  SELECT RAISE(ABORT, 'invalid LiteratureHypothesis bindings')
  WHERE
    (SELECT count(*) FROM json_each(NEW.contract_json, '$.bindings')) <> 4;

  SELECT RAISE(ABORT, 'invalid LiteratureHypothesis bindings')
  WHERE
    EXISTS (
      SELECT 1 FROM json_each(NEW.contract_json, '$.bindings')
      WHERE key NOT IN ('errorTypes', 'materialClasses', 'chains', 'acceptanceTests')
    );

  SELECT RAISE(ABORT, 'invalid LiteratureHypothesis bindings')
  WHERE
    EXISTS (
      SELECT 1 FROM json_each(NEW.contract_json, '$.bindings.errorTypes')
      WHERE type <> 'text' OR length(value) <> 2 OR substr(value, 1, 1) <> 'T'
        OR CAST(substr(value, 2) AS INTEGER) NOT BETWEEN 1 AND 7
        OR value <> printf('T%d', CAST(substr(value, 2) AS INTEGER))
    );

  SELECT RAISE(ABORT, 'invalid LiteratureHypothesis bindings')
  WHERE
    EXISTS (
      SELECT 1 FROM json_each(NEW.contract_json, '$.bindings.materialClasses')
      WHERE type <> 'text' OR length(value) <> 3 OR substr(value, 1, 2) <> 'MC'
        OR CAST(substr(value, 3) AS INTEGER) NOT BETWEEN 1 AND 9
        OR value <> printf('MC%d', CAST(substr(value, 3) AS INTEGER))
    );

  SELECT RAISE(ABORT, 'invalid LiteratureHypothesis bindings')
  WHERE
    EXISTS (
      SELECT 1 FROM json_each(NEW.contract_json, '$.bindings.chains')
      WHERE type <> 'text' OR CAST(substr(value, 2) AS INTEGER) NOT BETWEEN 1 AND 11
        OR value <> printf('C%d', CAST(substr(value, 2) AS INTEGER))
    );

  SELECT RAISE(ABORT, 'invalid LiteratureHypothesis bindings')
  WHERE
    EXISTS (
      SELECT 1 FROM json_each(NEW.contract_json, '$.bindings.acceptanceTests')
      WHERE type <> 'text' OR CAST(substr(value, 2) AS INTEGER) NOT BETWEEN 1 AND 11
        OR value <> printf('Z%d', CAST(substr(value, 2) AS INTEGER))
    );

  SELECT RAISE(ABORT, 'invalid LiteratureHypothesis bindings')
  WHERE
    (SELECT count(*) FROM json_each(NEW.contract_json, '$.bindings.errorTypes'))
      <> (SELECT count(DISTINCT value) FROM json_each(NEW.contract_json, '$.bindings.errorTypes'));

  SELECT RAISE(ABORT, 'invalid LiteratureHypothesis bindings')
  WHERE
    (SELECT count(*) FROM json_each(NEW.contract_json, '$.bindings.materialClasses'))
      <> (SELECT count(DISTINCT value) FROM json_each(NEW.contract_json, '$.bindings.materialClasses'));

  SELECT RAISE(ABORT, 'invalid LiteratureHypothesis bindings')
  WHERE
    (SELECT count(*) FROM json_each(NEW.contract_json, '$.bindings.chains'))
      <> (SELECT count(DISTINCT value) FROM json_each(NEW.contract_json, '$.bindings.chains'));

  SELECT RAISE(ABORT, 'invalid LiteratureHypothesis bindings')
  WHERE
    (SELECT count(*) FROM json_each(NEW.contract_json, '$.bindings.acceptanceTests'))
      <> (SELECT count(DISTINCT value) FROM json_each(NEW.contract_json, '$.bindings.acceptanceTests'));

  SELECT RAISE(ABORT, 'invalid LiteratureHypothesis proposedExperiment')
  WHERE
    (SELECT count(*) FROM json_each(NEW.contract_json, '$.proposedExperiment')) NOT IN (4, 5);

  SELECT RAISE(ABORT, 'invalid LiteratureHypothesis proposedExperiment')
  WHERE
    EXISTS (
      SELECT 1 FROM json_each(NEW.contract_json, '$.proposedExperiment')
      WHERE key NOT IN (
        'metric', 'predicate', 'panel_ref', 'estimated_cells', 'estimated_gpu_hours'
      )
    );

  SELECT RAISE(ABORT, 'invalid LiteratureHypothesis proposedExperiment')
  WHERE
    json_type(NEW.contract_json, '$.proposedExperiment.metric') IS NOT 'text';

  SELECT RAISE(ABORT, 'invalid LiteratureHypothesis proposedExperiment')
  WHERE
    json_extract(NEW.contract_json, '$.proposedExperiment.metric') NOT IN ('barrier_mae', 'signed_error_positive');

  SELECT RAISE(ABORT, 'invalid LiteratureHypothesis proposedExperiment')
  WHERE
    json_type(NEW.contract_json, '$.proposedExperiment.predicate') IS NOT 'text';

  SELECT RAISE(ABORT, 'invalid LiteratureHypothesis proposedExperiment')
  WHERE
    json_type(NEW.contract_json, '$.proposedExperiment.estimated_cells') IS NULL;

  SELECT RAISE(ABORT, 'invalid LiteratureHypothesis proposedExperiment')
  WHERE
    (
      json_type(NEW.contract_json, '$.proposedExperiment.estimated_cells') <> 'integer'
      AND NOT (
        json_type(NEW.contract_json, '$.proposedExperiment.estimated_cells') = 'real'
        AND json_extract(NEW.contract_json, '$.proposedExperiment.estimated_cells')
          = CAST(json_extract(
            NEW.contract_json, '$.proposedExperiment.estimated_cells'
          ) AS INTEGER)
      )
    );

  SELECT RAISE(ABORT, 'invalid LiteratureHypothesis proposedExperiment')
  WHERE
    json_extract(NEW.contract_json, '$.proposedExperiment.estimated_cells') < 1;

  SELECT RAISE(ABORT, 'invalid LiteratureHypothesis proposedExperiment')
  WHERE
    json_extract(NEW.contract_json, '$.proposedExperiment.estimated_cells')
      > 9223372036854775807;

  SELECT RAISE(ABORT, 'invalid LiteratureHypothesis proposedExperiment')
  WHERE
    json_type(NEW.contract_json, '$.proposedExperiment.estimated_gpu_hours') IS NULL;

  SELECT RAISE(ABORT, 'invalid LiteratureHypothesis proposedExperiment')
  WHERE
    json_type(NEW.contract_json, '$.proposedExperiment.estimated_gpu_hours')
      NOT IN ('integer', 'real');

  SELECT RAISE(ABORT, 'invalid LiteratureHypothesis proposedExperiment')
  WHERE
    json_extract(NEW.contract_json, '$.proposedExperiment.estimated_gpu_hours') < 0;

  SELECT RAISE(ABORT, 'invalid LiteratureHypothesis proposedExperiment')
  WHERE
    (
      json_type(NEW.contract_json, '$.proposedExperiment.panel_ref') IS NOT NULL
      AND (
        json_type(NEW.contract_json, '$.proposedExperiment.panel_ref') <> 'text'
        OR length(trim(
          json_extract(NEW.contract_json, '$.proposedExperiment.panel_ref'),
          (char(9) || char(10) || char(11) || char(12) || char(13))
        || (char(28) || char(29) || char(30) || char(31) || char(32))
        || (char(133) || char(160) || char(5760) || char(8192) || char(8193))
        || (char(8194) || char(8195) || char(8196) || char(8197) || char(8198))
        || (char(8199) || char(8200) || char(8201) || char(8202) || char(8232))
        || (char(8233) || char(8239) || char(8287) || char(12288))
        )) = 0
      )
    );
END;

PRAGMA foreign_keys = ON;
