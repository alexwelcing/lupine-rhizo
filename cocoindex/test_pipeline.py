"""
Tests for the cocoindex evidence pipeline.

These avoid the heavy cocoindex engine (which needs COCOINDEX_DB + the CLI)
and instead unit-test the pure-Python pieces: the record format produced by
seed_data/export_evidence, and the deterministic fallback embedder. The full
engine run is exercised manually via `cocoindex update main.py` (see README).

Run: python -m pytest test_pipeline.py -q   (from the cocoindex/ dir, with .venv)
"""
import json
import pathlib
import sys

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

# Import the pure helpers from main.py without triggering cocoindex App
# registration side-effects: main.py builds the App at import time, which is
# fine because App construction is lazy (no engine start until update()).
import main as pipeline  # noqa: E402


def test_fallback_vector_is_deterministic_and_dim():
    a = pipeline._fallback_vector("hyper-ribbon error manifold")
    b = pipeline._fallback_vector("hyper-ribbon error manifold")
    c = pipeline._fallback_vector("completely different content")
    assert a.shape == (pipeline.EMBED_DIM,)
    assert np.array_equal(a, b), "same text must produce the same vector"
    assert not np.allclose(a, c, atol=1e-6), "different text should differ"
    assert abs(float(np.linalg.norm(a)) - 1.0) < 1e-5, "fallback vector must be unit-norm"


def test_seed_records_are_valid_jsonl_with_text():
    """Every seeded record is parseable JSONL with a non-empty `text` field —
    the contract process_file relies on."""
    data = HERE / "data"
    assert data.exists(), "run `python seed_data.py` first to create ./data"
    files = list(data.glob("*.jsonl"))
    assert len(files) >= 3, f"expected >=3 seed jsonl files, got {len(files)}"
    total = 0
    for f in files:
        with f.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                assert "text" in rec and rec["text"].strip(), f"{f.name}: missing text"
                assert "kind" in rec, f"{f.name}: missing kind"
                total += 1
    assert total >= 5, f"expected >=5 total seeded records, got {total}"


def test_evidence_chunk_dataclass_shape():
    """EvidenceChunk must carry the fields the index query layer relies on."""
    from dataclasses import fields
    names = {f.name for f in fields(pipeline.EvidenceChunk)}
    assert {"id", "source_file", "kind", "ref_id", "text", "embedding"}.issubset(names)


def test_export_evidence_arg_parser_does_not_require_d1():
    """export_evidence.py with no --from-d1 should be a no-op (prints a hint),
    so importing/calling it in CI never hits wrangler."""
    import export_evidence
    rc = export_evidence.main([])  # explicit empty argv — never reads pytest's args
    assert rc == 0


def test_query_keyword_search_returns_results():
    """query.py --keyword is pure SQL and does not depend on local index state."""
    import sqlite3
    import query
    conn = sqlite3.connect(":memory:")
    try:
        conn.execute(
            """
            CREATE TABLE evidence_chunks (
                id TEXT,
                source_file TEXT,
                kind TEXT,
                ref_id TEXT,
                text TEXT,
                chunk_start INTEGER,
                chunk_end INTEGER
            )
            """
        )
        conn.executemany(
            "INSERT INTO evidence_chunks VALUES (?, ?, ?, ?, ?, ?, ?)",
            [
                (
                    "trace-1",
                    "coordination_traces.jsonl",
                    "coordination_trace",
                    "trace-1",
                    "Fan-out/Merge selected a better synthesis route.",
                    0,
                    48,
                ),
                (
                    "hyp-1",
                    "hypotheses.jsonl",
                    "hypothesis",
                    "hyp-1",
                    "The manifold boundary explains the observed error mode.",
                    0,
                    57,
                ),
            ],
        )
        res = query.keyword_search(conn, "fan out merge", limit=5, kind_filter=None)
        assert len(res) >= 1
        assert any("fan" in r["text"].lower() for r in res)
        # kind filter narrows correctly
        only_hyp = query.keyword_search(conn, "manifold", limit=10, kind_filter="hypothesis")
        assert all(r["kind"] == "hypothesis" for r in only_hyp)
    finally:
        conn.close()


def test_query_missing_db_returns_clean_error():
    """query.py against a nonexistent db exits 2, not a traceback."""
    import query
    rc = query.main(["--keyword", "x", "--db", str(HERE / "nonexistent_test.db")])
    assert rc == 2


def _make_synthetic_db(path: pathlib.Path, n: int = 8) -> None:
    """A minimal evidence.db: n rows with deterministic fallback embeddings."""
    import sqlite3
    conn = sqlite3.connect(str(path))
    try:
        conn.execute(
            "CREATE TABLE evidence_chunks (id TEXT PRIMARY KEY, source_file TEXT, "
            "kind TEXT, ref_id TEXT, text TEXT, embedding BLOB, "
            "chunk_start INTEGER, chunk_end INTEGER)"
        )
        for i in range(n):
            text = f"synthetic evidence record number {i} about topic {i % 3}"
            vec = pipeline._fallback_vector(text).tobytes()
            conn.execute(
                "INSERT INTO evidence_chunks VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (f"row-{i}", "synthetic.jsonl", "claim", f"ref-{i}", text, vec, 0, len(text)),
            )
        conn.commit()
    finally:
        conn.close()


def test_build_vec_index_creates_knn_sidecar(tmp_path):
    """build_vec_index materializes the vec0 table query.py's fast path uses,
    is idempotent, and the KNN returns the exact-match row first."""
    import sqlite3
    import build_vec_index
    import query

    db = tmp_path / "evidence.db"
    _make_synthetic_db(db)
    assert build_vec_index.build(db) == 0
    assert build_vec_index.build(db) == 0  # second run: up-to-date no-op

    conn = sqlite3.connect(str(db))
    try:
        assert query._load_vec(conn), "sqlite-vec must load for the fast path"
        n_vec = conn.execute(
            f"SELECT COUNT(*) FROM {build_vec_index.VEC_TABLE}").fetchone()[0]
        assert n_vec == 8
        # Query with row 3's own embedding: KNN must rank row 3 first.
        target = "synthetic evidence record number 3 about topic 0"
        blob = pipeline._fallback_vector(target).tobytes()
        rows = query._try_vec0_query(conn, blob, 3)
        assert rows is not None, "vec0 fast path should be available"
        assert rows[0]["id"] == "row-3"
    finally:
        conn.close()


def test_build_vec_index_detects_content_changes(tmp_path):
    """Changing a row's text or embedding without changing row count must
    invalidate the sidecars and trigger an automatic rebuild."""
    import sqlite3
    import build_vec_index

    db = tmp_path / "evidence.db"
    _make_synthetic_db(db)
    assert build_vec_index.build(db) == 0

    # Mutate one row in place: same row count, different content.
    conn = sqlite3.connect(str(db))
    try:
        new_text = "synthetic evidence record number 0 about topic 0 MODIFIED"
        new_vec = pipeline._fallback_vector(new_text).tobytes()
        conn.execute(
            "UPDATE evidence_chunks SET text=?, embedding=? WHERE id=?",
            (new_text, new_vec, "row-0"),
        )
        conn.commit()
    finally:
        conn.close()

    # A second build must detect the fingerprint change and rebuild.
    assert build_vec_index.build(db) == 0

    import query

    conn = sqlite3.connect(str(db))
    try:
        assert query._load_vec(conn), "sqlite-vec must load for sidecar inspection"
        stored_fp = conn.execute(
            f"SELECT value FROM {build_vec_index.META_TABLE} WHERE key='content_fingerprint'"
        ).fetchone()[0]
        n_vec = conn.execute(
            f"SELECT COUNT(*) FROM {build_vec_index.VEC_TABLE}").fetchone()[0]
        assert n_vec == 8
        # The new embedding for row 0 should now be in the sidecar.
        row0_vec = conn.execute(
            "SELECT embedding FROM evidence_chunks_vec_row WHERE rowid=(SELECT rowid FROM evidence_chunks WHERE id='row-0')"
        ).fetchone()[0]
        assert row0_vec == new_vec
    finally:
        conn.close()


def test_fetch_site_content_record_shape_and_write_if_changed(tmp_path):
    """Site-guide records follow the pipeline contract, and an unchanged
    fetch must NOT rewrite the file (that would dirty the content
    fingerprint and force a pointless re-embed)."""
    import fetch_site_content as fsc

    rec = fsc._record("https://library.lupine.science/llms.txt", "  # Lupine Science\ncontent  ")
    assert rec["kind"] == "site_guide"
    assert rec["ref_id"] == "https://library.lupine.science/llms.txt"
    assert rec["text"] == "# Lupine Science\ncontent"  # stripped
    assert "text" in rec and rec["text"].strip()       # process_file contract
    json.dumps(rec)                                    # JSONL-serializable

    out = tmp_path / "site_guides.jsonl"
    assert fsc.write_if_changed([rec], out) is True    # first write
    assert fsc.write_if_changed([rec], out) is False   # identical -> no rewrite
    rec2 = fsc._record(rec["ref_id"], "different content now")
    assert fsc.write_if_changed([rec2], out) is True   # changed -> rewrite


def test_article_ref_ids_use_library_namespace():
    """Published-article refs live under the `library:` prefix, and the
    article source is whichever library-content bundle LIBRARY_ROOT resolved
    to (deployed ledger cache when synced, else the local export bundle)."""
    assert pipeline.LIBRARY_REF_PREFIX == "library:"
    assert pipeline.ARTICLES_DIR.name == "articles"
    assert pipeline.ARTICLES_DIR.parent == pipeline.LIBRARY_ROOT
    assert pipeline.LIBRARY_ROOT.name == "latest"


def test_manifest_diff_and_drift_record():
    """manifest_diff classifies pending/deployed-only/changed/in-sync, and
    the drift record is a valid, deterministic evidence record."""
    import sync_ledger as sl
    local = {"articles/a.md": "s1", "articles/b.md": "s2", "articles/new.md": "s9"}
    deployed = {"articles/a.md": "s1", "articles/b.md": "sX", "articles/gone.md": "s3"}
    diff = sl.manifest_diff(local, deployed)
    assert diff["pending_publication"] == ["articles/new.md"]
    assert diff["deployed_only"] == ["articles/gone.md"]
    assert diff["changed"] == ["articles/b.md"]
    assert diff["in_sync"] == ["articles/a.md"]

    info = {"generatedAt": "2026-07-02T00:00:00Z", "source": {"commit": "abcdef1234"}}
    rec = sl.drift_record(info, info, diff)
    assert rec["kind"] == "publication_drift"
    assert "new.md" in rec["text"] and "gone.md" in rec["text"]
    assert rec["metadata"]["pending_publication"] == 1
    assert rec == sl.drift_record(info, info, diff)  # deterministic
    json.dumps(rec)


def test_twin_map_and_dedupe_collapse_published_articles():
    """A published Library article and its repo source doc are the same
    content: canonical_ref maps library:X onto the manifest's source path,
    and dedupe_results keeps only the best-ranked of the pair."""
    import query
    tm = query.twin_map()
    if not tm:  # bundle not checked out in this environment
        import pytest
        pytest.skip("exports/library-content bundle not present")
    assert tm.get("library:GLOSSARY.md") == "GLOSSARY.md"
    assert query.canonical_ref("library:GLOSSARY.md") == "GLOSSARY.md"
    assert query.canonical_ref("docs/unrelated.md") == "docs/unrelated.md"

    results = [
        {"ref_id": "library:GLOSSARY.md", "score": 0.9},
        {"ref_id": "GLOSSARY.md", "score": 0.8},          # twin -> dropped
        {"ref_id": "docs/other.md", "score": 0.7},
    ]
    deduped = query.dedupe_results(results, limit=5)
    assert [r["ref_id"] for r in deduped] == ["library:GLOSSARY.md", "docs/other.md"]


def test_fts_bm25_and_hybrid_search(tmp_path):
    """build_vec_index also materializes the FTS5 sidecar; keyword_search
    then ranks by BM25, and hybrid_search fuses both legs by RRF."""
    import sqlite3
    import build_vec_index
    import query

    db = tmp_path / "evidence.db"
    _make_synthetic_db(db)
    assert build_vec_index.build(db) == 0
    conn = sqlite3.connect(str(db))
    try:
        assert conn.execute(
            "SELECT COUNT(*) FROM evidence_chunks_fts").fetchone()[0] == 8
        # "number 7" — the digit 7 appears only in row 7's text, so BM25's
        # IDF weighting must rank row 7 first over the shared common terms.
        res = query.keyword_search(conn, "record number 7", limit=3, kind_filter=None)
        assert res and res[0]["id"] == "row-7"           # BM25 puts rare-term match first
        assert res[0].get("score") is not None           # scored (LIKE path isn't)
        # Hybrid runs both legs and fuses by RRF. On synthetic hash-vector
        # embeddings the semantic leg is noise, so we assert structure (fused,
        # scored, RRF descending) not ordering — real ranking is the eval's job.
        assert query._load_vec(conn)
        fused = query.hybrid_search(conn, "record number 7", limit=3, kind_filter=None)
        assert fused and all(r.get("score") is not None for r in fused)
        scores = [r["score"] for r in fused]
        assert scores == sorted(scores, reverse=True)
    finally:
        conn.close()


def test_phoenix_span_record_shapes():
    """Root-span summarization: tolerant to flat/nested attributes, skips
    spans with no trace id, and only roots become records."""
    import fetch_phoenix_traces as fpt

    span = {
        "context": {"trace_id": "t-1", "span_id": "s-1"},
        "name": "coordinate",
        "parent_id": None,
        "span_kind": "AGENT",
        "status_code": "ERROR",
        "status_message": "provider timeout",
        "start_time": "2026-07-07T01:00:00Z",
        "end_time": "2026-07-07T01:00:04.200Z",
        "attributes": {"llm": {"model_name": "gpt-5.5", "token_count": {"total": 670}},
                       "input": {"value": "test prompt"}},
    }
    rec = fpt.span_record(span, "glim-think")
    assert rec["kind"] == "agent_trace" and rec["ref_id"] == "t-1"
    assert "ERROR" in rec["text"] and "provider timeout" in rec["text"]
    assert "gpt-5.5" in rec["text"] and "670" in rec["text"]
    assert "4200 ms" in rec["text"]
    assert rec == fpt.span_record(span, "glim-think")  # deterministic
    json.dumps(rec)

    flat = dict(span, attributes={"llm.model_name": "m", "input.value": "x"})
    assert "Model: m." in fpt.span_record(flat, "p")["text"]
    assert fpt.span_record({"name": "no-trace-id"}, "p") is None
    assert fpt.is_root(span) and not fpt.is_root(dict(span, parent_id="s-0"))


def test_phoenix_skips_cleanly_without_credentials(monkeypatch):
    """No Phoenix config → exit 0 (offline-tolerant), exit 1 with --strict."""
    import fetch_phoenix_traces as fpt
    monkeypatch.delenv("PHOENIX_COLLECTOR_ENDPOINT", raising=False)
    monkeypatch.delenv("PHOENIX_API_KEY", raising=False)
    assert fpt.main([]) == 0
    assert fpt.main(["--strict"]) == 1


def test_eval_distinct_source_rank():
    """Chunks of one document collapse to that document's best rank."""
    import eval_retrieval as ev
    results = [
        {"ref_id": "docs/a.md"}, {"ref_id": "docs/a.md"},
        {"ref_id": "docs/b.md"}, {"ref_id": "hyp-1"},
    ]
    assert ev._distinct_source_rank(results, "docs/a.md") == 1
    assert ev._distinct_source_rank(results, "docs/b.md") == 2
    assert ev._distinct_source_rank(results, "hyp-1") == 3
    assert ev._distinct_source_rank(results, "missing") is None
