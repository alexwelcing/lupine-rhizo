# Ontology snapshots: superseded records

`atlas.v1.json` and `atlas.v2.json` are hash-pinned snapshots of the Lupine
ontology as compiled on 2026-07-30. `snapshots/ontology.lock.json` points at v2,
and `tools/check_ontology_links.py` and the anti-laundering check
(`tools/check_status_evidence.py`) verify them byte for byte, so they are kept
unchanged as historical records.

They are superseded. On 2026-11-11 the source ontology
(`lupine-ledger/content/ontology/lupine-ontology.json`) was edited to remove
funding, partner and authorship fields. These snapshots predate that edit and no
longer match it.

Read them with these corrections:

- No organisation named in them is a Lupine partner. The `venture.partnersWith`
  relation and the joint-development entry in `roadmapPhases` do not describe
  any agreement.
- The NSF SBIR and other funding-programme dates in `roadmapPhases`,
  `timeGates` and `freshnessLayer` (also copied into
  `snapshots/ontology.lock.json`) are not current plans.
- The climate aggregate (5–12 GtCO₂/yr) is not a Lupine result, and mechanism
  entries such as corrected barriers are hypotheses to test. Theorem counts are
  not evidence.

Current statuses are in the [conjecture ledger](../../docs/conjectures/ledger.md)
and the corrections log at <https://lupine.science/corrections/>.
