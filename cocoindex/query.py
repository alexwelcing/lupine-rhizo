#!/usr/bin/env python3
"""
Semantic + keyword search over the cocoindex evidence index (./evidence.db).

Two modes:
  --semantic "<q>"   embed the query and return nearest-neighbor chunks
                     (needs sqlite-vec; falls back to keyword if unavailable)
  --keyword "<q>"    plain SQL LIKE over text (always works)

Both rank by relevance and join back the source kind/ref_id so results are
actionable. Designed to be called from the command line AND programmatically
(`python query.py --semantic "..." --json`).

Examples:
    python query.py --semantic "which coordination strategies beat the baseline"
    python query.py --keyword "aluminium cohesive" --limit 5
    python query.py --semantic "hyper-ribbon error manifold" --kind hypothesis
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import pathlib

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

# Reuse the pipeline's embedder (real model with offline fallback) so query
# embeddings match index embeddings.
import main as pipeline  # noqa: E402

_QUERY_MODEL = None

# The manifest of whichever bundle main.py is actually indexing (deployed
# ledger cache when synced, else the local export bundle) — twin mapping must
# match the article source or the refs won't line up.
MANIFEST = pipeline.LIBRARY_ROOT / "manifest.json"
_TWIN_MAP: dict[str, str] | None = None


def twin_map() -> dict[str, str]:
    """Published-article ref → repo source path, from the library-content.v1
    manifest (e.g. "library:GLOSSARY.md" → "GLOSSARY.md"). A published article
    is another view of its source doc; for dedup they are the same content."""
    global _TWIN_MAP
    if _TWIN_MAP is None:
        mapping: dict[str, str] = {}
        try:
            for f in json.loads(MANIFEST.read_text(encoding="utf-8")).get("files", []):
                src, bundle = f.get("source"), f.get("bundleSource") or ""
                if src and bundle.startswith("articles/"):
                    mapping[f"library:{bundle[len('articles/'):]}"] = src
        except (OSError, json.JSONDecodeError):
            pass  # no bundle checked out → nothing to collapse
        _TWIN_MAP = mapping
    return _TWIN_MAP


def canonical_ref(ref_id: str) -> str:
    """Collapse a published article onto its repo source doc."""
    return twin_map().get(ref_id, ref_id)


def dedupe_results(results: list[dict], limit: int) -> list[dict]:
    """Keep only the best-ranked chunk per canonical source, preserving order."""
    seen: set[str] = set()
    out = []
    for r in results:
        key = canonical_ref(r["ref_id"])
        if key in seen:
            continue
        seen.add(key)
        out.append(r)
        if len(out) >= limit:
            break
    return out


def _load_vec(conn: sqlite3.Connection) -> bool:
    """Try to load sqlite-vec. Returns False (→ keyword fallback) if absent."""
    try:
        import sqlite_vec  # type: ignore
        conn.enable_load_extension(True)
        sqlite_vec.load(conn)
        conn.enable_load_extension(False)
        return True
    except Exception:
        return False


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone()
    return row is not None


def semantic_search(conn: sqlite3.Connection, query: str, limit: int,
                    kind_filter: str | None) -> list[dict]:
    vec_ok = _load_vec(conn)
    if not vec_ok:
        print("[query] sqlite-vec unavailable; falling back to keyword search",
              file=sys.stderr)
        return keyword_search(conn, query, limit, kind_filter)
    if not _table_exists(conn, "evidence_chunks"):
        return []
    # Embed the query through the same path the indexer used (real model or
    # hash-vector fallback), so query/index vector spaces match.
    qvec = pipeline._fallback_vector(query) if pipeline._FALLBACK_ACTIVE \
        else np.asarray(_safe_embed(query), dtype=np.float32)
    blob = np.asarray(qvec, dtype=np.float32).tobytes()
    # Unfiltered queries use the vec0 KNN sidecar (built by build_vec_index.py).
    # Kind-filtered queries deliberately do NOT: vec0 ranks globally and a
    # post-KNN kind filter silently drops rare kinds (a 2-chunk kind is never
    # in the global top-k). The exact cosine scan restricted to the kind is
    # both correct and fast (it only touches that kind's rows).
    rows = None
    if not kind_filter:
        rows = _try_vec0_query(conn, blob, limit)
    if rows is None:
        rows = _manual_cosine(conn, blob, limit, kind_filter)
    return rows


# BGE retrieval models are trained with an instruction prefix on the QUERY
# side only (documents embed bare). Harmless no-op for other model families.
_BGE_QUERY_PREFIX = "Represent this sentence for searching relevant passages: "


def _safe_embed(text: str):
    """Embed a query outside CocoIndex's component context.

    The indexer uses CocoIndex's SentenceTransformerEmbedder inside an active
    component context. The standalone query CLI has no such context, so load the
    same sentence-transformers model directly and keep the pipeline fallback for
    offline use.
    """
    global _QUERY_MODEL
    try:
        from sentence_transformers import SentenceTransformer
        if _QUERY_MODEL is None:
            _QUERY_MODEL = SentenceTransformer(pipeline.EMBED_MODEL)
        if "bge" in pipeline.EMBED_MODEL.lower():
            text = _BGE_QUERY_PREFIX + text
        vec = _QUERY_MODEL.encode(text, normalize_embeddings=True)
        vec = np.asarray(vec, dtype=np.float32)
        if int(vec.shape[-1]) == pipeline.EMBED_DIM:
            return vec
        raise ValueError(f"unexpected embedding dim {vec.shape[-1]}")
    except Exception as e:  # noqa: BLE001
        print(f"[query] embed failed ({e}); using fallback", file=sys.stderr)
        return pipeline._fallback_vector(text)


def _try_vec0_query(conn, blob: bytes, limit: int):
    """Unfiltered KNN via the vec0 virtual table (built by build_vec_index.py).
    Returns None if the virtual table isn't present (caller falls back to
    manual cosine)."""
    has_vec0 = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'evidence_chunks_vec%'"
    ).fetchone()
    if not has_vec0:
        return None
    try:
        sql = (
            "SELECT e.id, e.source_file, e.kind, e.ref_id, e.text, "
            "e.chunk_start, e.chunk_end, v.distance "
            "FROM evidence_chunks_vec_row v "
            "JOIN evidence_chunks e ON e.rowid = v.rowid "
            "WHERE v.embedding MATCH ? AND k = ? "
            "ORDER BY v.distance"
        )
        cur = conn.execute(sql, [blob, limit])
        return [_row(r, score=-float(r[7])) for r in cur.fetchall()]
    except sqlite3.OperationalError:
        return None


def _manual_cosine(conn, qblob: bytes, limit: int, kind_filter: str | None) -> list[dict]:
    """Brute-force cosine similarity over the embedding BLOB column. Slower but
    always correct; used when the vec0 virtual table isn't available."""
    q = np.frombuffer(qblob, dtype=np.float32)
    qn = np.linalg.norm(q) or 1.0
    sql = "SELECT id, source_file, kind, ref_id, text, chunk_start, chunk_end, embedding FROM evidence_chunks"
    if kind_filter:
        sql += " WHERE kind = ?"
    scored = []
    for r in conn.execute(sql, ([kind_filter] if kind_filter else [])).fetchall():
        v = np.frombuffer(r[7], dtype=np.float32)
        vn = np.linalg.norm(v) or 1.0
        sim = float(np.dot(q, v) / (qn * vn))
        scored.append(_row(r[:7], score=sim))
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:limit]


def keyword_search(conn: sqlite3.Connection, query: str, limit: int,
                   kind_filter: str | None) -> list[dict]:
    """Lexical search: FTS5/BM25 when the sidecar exists (build_vec_index.py),
    else the original LIKE scan."""
    if not _table_exists(conn, "evidence_chunks"):
        return []
    if _table_exists(conn, "evidence_chunks_fts"):
        rows = _bm25_search(conn, query, limit, kind_filter)
        if rows is not None:
            return rows
    return _like_search(conn, query, limit, kind_filter)


def _bm25_search(conn, query: str, limit: int, kind_filter: str | None):
    """BM25 over the FTS5 sidecar. Tokens are quoted so user text can't break
    the MATCH syntax. Returns None on FTS error (caller falls back to LIKE)."""
    # Keep single-char tokens: element symbols (C, N, O, H) are meaningful
    # here, and FTS5/BM25 handles short terms via IDF (unlike the LIKE path).
    terms = [t for t in query.split() if t.strip()]
    if not terms:
        return []
    match = " OR ".join('"' + t.replace('"', "") + '"' for t in terms)
    # The kind filter applies after MATCH ranking, so over-fetch to keep
    # rare kinds reachable (same reasoning as the semantic path).
    k = limit * 20 if kind_filter else limit
    sql = (
        "SELECT e.id, e.source_file, e.kind, e.ref_id, e.text, "
        "e.chunk_start, e.chunk_end, bm25(evidence_chunks_fts) AS score "
        "FROM evidence_chunks_fts f JOIN evidence_chunks e ON e.rowid = f.rowid "
        "WHERE evidence_chunks_fts MATCH ? "
        + ("AND e.kind = ? " if kind_filter else "")
        + "ORDER BY score LIMIT ?"
    )
    params = [match] + ([kind_filter] if kind_filter else []) + [k]
    try:
        rows = conn.execute(sql, params).fetchall()
    except sqlite3.OperationalError:
        return None
    # bm25() returns lower-is-better; expose as negative score like distance.
    return [_row(r[:7], score=-float(r[7])) for r in rows[:limit]]


def _like_search(conn, query: str, limit: int, kind_filter: str | None) -> list[dict]:
    # Simple subsequence-ish match: each whitespace token as LIKE OR.
    terms = [t for t in query.lower().split() if len(t) >= 3]
    if not terms:
        return []
    clauses = " OR ".join(["LOWER(text) LIKE ?" for _ in terms])
    sql = (
        "SELECT id, source_file, kind, ref_id, text, chunk_start, chunk_end FROM evidence_chunks "
        "WHERE (" + clauses + ") " + ("AND kind = ? " if kind_filter else "")
        + "ORDER BY LENGTH(text) ASC LIMIT ?"
    )
    params = [f"%{t}%" for t in terms] + ([kind_filter] if kind_filter else []) + [limit]
    return [_row(r) for r in conn.execute(sql, params).fetchall()]


RRF_K = 60  # standard reciprocal-rank-fusion constant


def hybrid_search(conn: sqlite3.Connection, query: str, limit: int,
                  kind_filter: str | None) -> list[dict]:
    """Reciprocal-rank fusion of the semantic and BM25 legs. Robust where
    either leg alone is weak: lexical anchors exact terms (element names,
    property symbols), semantic covers paraphrase."""
    depth = max(limit * 3, 15)
    sem = semantic_search(conn, query, depth, kind_filter)
    lex = keyword_search(conn, query, depth, kind_filter)
    fused: dict[str, dict] = {}
    for results in (sem, lex):
        for rank, r in enumerate(results, 1):
            entry = fused.setdefault(r["id"], {"row": r, "rrf": 0.0})
            entry["rrf"] += 1.0 / (RRF_K + rank)
    ranked = sorted(fused.values(), key=lambda e: e["rrf"], reverse=True)[:limit]
    out = []
    for e in ranked:
        row = dict(e["row"])
        row["score"] = round(e["rrf"], 4)
        out.append(row)
    return out


def _row(r, score: float | None = None) -> dict:
    out = {
        "id": r[0], "source_file": r[1], "kind": r[2], "ref_id": r[3],
        "text": r[4], "chunk_start": r[5], "chunk_end": r[6],
    }
    if score is not None:
        out["score"] = round(score, 4)
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--semantic", metavar="Q", help="semantic nearest-neighbor search")
    g.add_argument("--keyword", metavar="Q", help="keyword search (BM25 via FTS5, LIKE fallback)")
    g.add_argument("--hybrid", metavar="Q",
                   help="semantic + BM25 fused by reciprocal rank (best default)")
    ap.add_argument("--kind", default=None,
                    help="filter by kind: coordination_trace|hypothesis|claim|"
                         "research_question|document|published_article|site_guide|"
                         "publication_drift|agent_trace")
    ap.add_argument("--limit", type=int, default=5)
    ap.add_argument("--dedupe", action="store_true",
                    help="one result per source; collapses a published Library "
                         "article onto its repo source doc (twin-aware)")
    ap.add_argument("--json", action="store_true", help="emit JSON output")
    ap.add_argument("--db", default=str(HERE / "evidence.db"))
    args = ap.parse_args(argv)

    db = pathlib.Path(args.db)
    if not db.exists():
        msg = (f"evidence index not found at {db}. "
               f"Run `python seed_data.py && cocoindex update main.py` first.")
        print(json.dumps({"error": msg}) if args.json else msg, file=sys.stderr)
        return 2

    conn = sqlite3.connect(str(db))
    try:
        # With dedup, over-fetch so collapsing twins/extra chunks still fills `limit`.
        fetch = args.limit * 5 if args.dedupe else args.limit
        if args.semantic:
            mode, results = "semantic", semantic_search(conn, args.semantic, fetch, args.kind)
        elif args.hybrid:
            mode, results = "hybrid", hybrid_search(conn, args.hybrid, fetch, args.kind)
        else:
            mode, results = "keyword", keyword_search(conn, args.keyword, fetch, args.kind)
        if args.dedupe:
            results = dedupe_results(results, args.limit)
    finally:
        conn.close()

    if args.json:
        print(json.dumps({"query": args.semantic or args.hybrid or args.keyword,
                          "mode": mode,
                          "kind": args.kind, "count": len(results),
                          "results": results}, ensure_ascii=False, indent=2))
    else:
        if not results:
            print("(no matches)")
        for i, r in enumerate(results, 1):
            sc = r.get("score")
            head = f"[{i}] {r['kind']}/{r['ref_id']}"
            if sc is not None:
                head += f"  (score {sc:+.3f})" if sc < 0 else f"  (sim {sc:.3f})"
            print(head)
            print(f"    {r['text'][:280].replace(chr(10), ' ')}{'…' if len(r['text'])>280 else ''}")
            print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
