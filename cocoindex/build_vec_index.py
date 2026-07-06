#!/usr/bin/env python3
"""
Build the sqlite-vec ANN sidecar for ./evidence.db.

CocoIndex's SQLite connector writes `evidence_chunks` with a native
float[384] embedding column, but does not create a vec0 virtual table —
so `query.py --semantic` falls back to brute-force cosine over every row.
This script materializes the vec0 KNN index (`evidence_chunks_vec_row`)
that query.py's fast path expects, keyed by rowid.

Idempotent: skips the rebuild when the sidecar row count already matches
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
EMBED_DIM = 384


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
