#!/usr/bin/env python3
"""
Build the search sidecars for ./evidence.db: the sqlite-vec exact KNN index and
the FTS5 BM25 index.

CocoIndex's SQLite connector writes `evidence_chunks` with a native
float[384] embedding column, but does not create a vec0 virtual table —
so `query.py --semantic` falls back to brute-force cosine over every row.
This script materializes:
  - the vec0 KNN index (`evidence_chunks_vec_row`) for the semantic fast path;
  - the FTS5 index (`evidence_chunks_fts`) that upgrades keyword search from
    SQL LIKE to real BM25 ranking, and provides the lexical leg of
    `query.py --hybrid` (reciprocal-rank fusion).

Idempotent: skips only when a recorded content fingerprint and sidecar schema
match the source (use --force to rebuild anyway). External-content FTS row counts
are not index-freshness evidence. Fingerprinting is linear in source size. Run with the source writer quiescent;
this is an offline sidecar builder, not online change capture. Fingerprints do not
verify embedding quality, dimension/model identity or direct sidecar integrity. Run it after every
`cocoindex update main.py`, or via `just evidence-index` which chains it.

Usage:
    python build_vec_index.py [--db ./evidence.db] [--force]
"""
from __future__ import annotations

from contextlib import contextmanager
import hashlib
import argparse
import pathlib
import sqlite3
import sys
import time
from embedding_contract import common_space, TOKENIZER_VERSION

VEC_TABLE = "evidence_chunks_vec_row"  # the name query.py's fast path expects
FTS_TABLE = "evidence_chunks_fts"      # the name query.py's BM25 path expects
EMBED_DIM = 384


def source_fingerprint(conn, column: str) -> str:
    """Stream index-relevant values and row identities; do not trust row counts."""
    if column not in {"text", "embedding"}:
        raise ValueError("Unsupported fingerprint column")
    digest = hashlib.sha256(b"lupine-search-sidecar-v2")
    digest.update((TOKENIZER_VERSION if column == "text" else (common_space(conn) or "unknown-embedding-space")).encode())
    for row in conn.execute(f"SELECT rowid, {column} FROM evidence_chunks ORDER BY rowid"):
        for value in row:
            data = (b"null" if value is None else b"bytes:" + bytes(value)
                    if isinstance(value, (bytes, bytearray, memoryview))
                    else (type(value).__name__ + ":" + str(value)).encode("utf-8"))
            digest.update(len(data).to_bytes(8, "big")); digest.update(data)
    return digest.hexdigest()


def sidecar_current(conn, table: str, fingerprint: str, expected_sql: str) -> bool:
    conn.execute("CREATE TABLE IF NOT EXISTS lupine_sidecar_freshness "
                 "(sidecar TEXT PRIMARY KEY, fingerprint TEXT NOT NULL, schema_sql TEXT NOT NULL)")
    schema = conn.execute("SELECT sql FROM sqlite_master WHERE name=?", (table,)).fetchone()
    saved = conn.execute("SELECT fingerprint, schema_sql FROM lupine_sidecar_freshness "
                         "WHERE sidecar=?", (table,)).fetchone()
    return bool(schema and saved and saved == (fingerprint, expected_sql) and schema[0] == expected_sql)


def remember_sidecar(conn, table: str, fingerprint: str) -> None:
    schema = conn.execute("SELECT sql FROM sqlite_master WHERE name=?", (table,)).fetchone()[0]
    conn.execute("INSERT OR REPLACE INTO lupine_sidecar_freshness VALUES (?, ?, ?)",
                 (table, fingerprint, schema))


@contextmanager
def sidecar_transaction(conn):
    """Own one immediate transaction, or isolate work in a caller's transaction."""
    nested = conn.in_transaction
    conn.execute("SAVEPOINT lupine_sidecars" if nested else "BEGIN IMMEDIATE")
    try:
        yield
    except BaseException:
        if nested:
            conn.execute("ROLLBACK TO lupine_sidecars")
            conn.execute("RELEASE lupine_sidecars")
        else:
            conn.rollback()
        raise
    else:
        if nested:
            conn.execute("RELEASE lupine_sidecars")
        else:
            conn.commit()


def fts_ddl():
    return (f"CREATE VIRTUAL TABLE {FTS_TABLE} USING fts5("
            "text, content='evidence_chunks', content_rowid='rowid')")


def vector_ddl(embed_dim=None):
    dimension = EMBED_DIM if embed_dim is None else embed_dim
    if not isinstance(dimension, int) or isinstance(dimension, bool) or dimension < 1:
        raise ValueError("Embedding dimension must be a positive integer")
    return f"CREATE VIRTUAL TABLE {VEC_TABLE} USING vec0(embedding float[{dimension}])"


def _update_fts(conn, n_rows, force=False):
    fingerprint = source_fingerprint(conn, "text")
    current = sidecar_current(conn, FTS_TABLE, fingerprint, fts_ddl())
    if current and not force:
        print(f"fts index source fingerprint unchanged ({n_rows} source rows)")
        return
    t0 = time.perf_counter()
    conn.execute(f"DROP TABLE IF EXISTS {FTS_TABLE}")
    conn.execute(fts_ddl())
    conn.execute(f"INSERT INTO {FTS_TABLE}({FTS_TABLE}) VALUES('rebuild')")
    remember_sidecar(conn, FTS_TABLE, fingerprint)
    print(f"prepared {FTS_TABLE}: {n_rows} rows in {time.perf_counter() - t0:.2f}s")


def build_fts(conn, n_rows: int, force: bool = False) -> None:
    """Atomically replace postings and freshness; preserve caller transactions.

    Direct sidecar corruption still requires integrity checking or --force.
    """
    with sidecar_transaction(conn):
        _update_fts(conn, n_rows, force)


def build_sidecars(conn, force=False, embed_dim=None):
    """One coherent source snapshot and rollback boundary for BOTH sidecars."""
    with sidecar_transaction(conn):
        n_rows = conn.execute("SELECT COUNT(*) FROM evidence_chunks").fetchone()[0]
        space = common_space(conn)
        if space is None:
            print("vector generation unknown/mixed/test-only; refreshing lexical index only")
            _update_fts(conn, n_rows, force)
            return
        import json
        space_dimension = json.loads(space)["dimension"]
        ddl = vector_ddl(space_dimension if embed_dim is None else embed_dim)
        if embed_dim is not None and embed_dim != space_dimension:
            raise ValueError("Requested dimension differs from embedding generation")
        fingerprint = source_fingerprint(conn, "embedding")
        current = sidecar_current(conn, VEC_TABLE, fingerprint, ddl)
        if current and not force:
            print(f"vec index source fingerprint unchanged ({n_rows} source rows)")
        else:
            conn.execute(f"DROP TABLE IF EXISTS {VEC_TABLE}")
            conn.execute(ddl)
            conn.execute(f"INSERT INTO {VEC_TABLE}(rowid, embedding) "
                         "SELECT rowid, embedding FROM evidence_chunks")
            remember_sidecar(conn, VEC_TABLE, fingerprint)
        _update_fts(conn, n_rows, force)


def build(db_path: pathlib.Path, force: bool = False) -> int:
    if not db_path.exists():
        print(f"error: {db_path} not found — run `cocoindex update main.py` first", file=sys.stderr)
        return 2
    try:
        import sqlite_vec
    except ImportError:
        print("error: sqlite-vec not installed (pip install sqlite-vec)", file=sys.stderr)
        return 2

    conn = sqlite3.connect(str(db_path))
    try:
        conn.enable_load_extension(True)
        sqlite_vec.load(conn)
        conn.enable_load_extension(False)

        build_sidecars(conn, force=force)
        return 0
    finally:
        conn.close()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", default=str(pathlib.Path(__file__).resolve().parent / "evidence.db"))
    ap.add_argument("--force", action="store_true", help="rebuild even if source fingerprints and sidecar schemas match")
    args = ap.parse_args(argv)
    return build(pathlib.Path(args.db), force=args.force)



def sidecar_matches_source(conn, table, column):
    """Read-only freshness check. Unknown/legacy stamps never authorize postings."""
    if table not in {FTS_TABLE, VEC_TABLE} or column not in {"text", "embedding"}:
        return False
    try:
        row = conn.execute("SELECT fingerprint FROM lupine_sidecar_freshness WHERE sidecar=?", (table,)).fetchone()
        return bool(row and row[0] == source_fingerprint(conn, column))
    except sqlite3.OperationalError:
        return False


if __name__ == "__main__":
    sys.exit(main())
