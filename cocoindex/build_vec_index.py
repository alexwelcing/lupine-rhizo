#!/usr/bin/env python3
"""
Build the search sidecars for ./evidence.db: the sqlite-vec ANN index and
the FTS5 BM25 index.

CocoIndex's SQLite connector writes `evidence_chunks` with a native
float[384] embedding column, but does not create a vec0 virtual table —
so `query.py --semantic` falls back to brute-force cosine over every row.
This script materializes:
  - the vec0 KNN index (`evidence_chunks_vec_row`) for the semantic fast path;
  - the FTS5 index (`evidence_chunks_fts`) that upgrades keyword search from
    SQL LIKE to real BM25 ranking, and provides the lexical leg of
    `query.py --hybrid` (reciprocal-rank fusion).

Idempotent: skips each rebuild when the sidecar row count already matches
`evidence_chunks` (use --force to rebuild anyway). Run it after every
`cocoindex update main.py`, or via `just evidence-index` which chains it.

Usage:
    python build_vec_index.py [--db ./evidence.db] [--force]
"""
from __future__ import annotations

import argparse
import pathlib
import sqlite3
import sys
import time

VEC_TABLE = "evidence_chunks_vec_row"  # the name query.py's fast path expects
FTS_TABLE = "evidence_chunks_fts"      # the name query.py's BM25 path expects
EMBED_DIM = 384


def build_fts(conn, n_rows: int, force: bool = False) -> None:
    """Materialize the FTS5 external-content index over evidence_chunks.text."""
    has_fts = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (FTS_TABLE,)
    ).fetchone()
    if has_fts and not force:
        n_fts = conn.execute(f"SELECT COUNT(*) FROM {FTS_TABLE}").fetchone()[0]
        if n_fts == n_rows:
            print(f"fts index up to date ({n_fts} rows); use --force to rebuild")
            return
    t0 = time.perf_counter()
    conn.execute(f"DROP TABLE IF EXISTS {FTS_TABLE}")
    conn.execute(
        f"CREATE VIRTUAL TABLE {FTS_TABLE} USING fts5("
        "text, content='evidence_chunks', content_rowid='rowid')"
    )
    conn.execute(f"INSERT INTO {FTS_TABLE}({FTS_TABLE}) VALUES('rebuild')")
    conn.commit()
    print(f"built {FTS_TABLE}: {n_rows} rows in {time.perf_counter() - t0:.2f}s")


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

        n_rows = conn.execute("SELECT COUNT(*) FROM evidence_chunks").fetchone()[0]
        has_vec = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (VEC_TABLE,)
        ).fetchone()
        if has_vec and not force:
            n_vec = conn.execute(f"SELECT COUNT(*) FROM {VEC_TABLE}").fetchone()[0]
            if n_vec == n_rows:
                print(f"vec index up to date ({n_vec} rows); use --force to rebuild")
                build_fts(conn, n_rows, force=force)
                return 0

        t0 = time.perf_counter()
        conn.execute(f"DROP TABLE IF EXISTS {VEC_TABLE}")
        conn.execute(
            f"CREATE VIRTUAL TABLE {VEC_TABLE} USING vec0(embedding float[{EMBED_DIM}])"
        )
        conn.execute(
            f"INSERT INTO {VEC_TABLE}(rowid, embedding) "
            "SELECT rowid, embedding FROM evidence_chunks"
        )
        conn.commit()
        dt = time.perf_counter() - t0
        print(f"built {VEC_TABLE}: {n_rows} vectors in {dt:.2f}s -> {db_path}")
        build_fts(conn, n_rows, force=force)
        return 0
    finally:
        conn.close()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", default=str(pathlib.Path(__file__).resolve().parent / "evidence.db"))
    ap.add_argument("--force", action="store_true", help="rebuild even if row counts match")
    args = ap.parse_args(argv)
    return build(pathlib.Path(args.db), force=args.force)


if __name__ == "__main__":
    sys.exit(main())
