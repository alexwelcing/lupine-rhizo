#!/usr/bin/env python3
"""
Retrieval evaluation for the evidence index: does semantic search actually
find the right evidence, and what does a query cost?

A fixed gold set of natural-language questions, each with the known-correct
target (a document path or evidence ref_id). Every query is deliberately
paraphrased — not a keyword copy of the target text — so it measures semantic
retrieval, not string matching. For each mode (semantic / keyword) we report:

  hit@1, hit@3, hit@5   — was the target the 1st / in the top-3 / top-5
                          distinct source returned?
  MRR                   — mean reciprocal rank of the target source
  latency               — query embed time + search time (semantic), and a
                          vec0-vs-brute-force search-only comparison

Requires the REAL embedding model (results with the offline hash-vector
fallback are meaningless for semantic mode and are flagged as such).

Usage:
    python eval_retrieval.py            # human-readable report
    python eval_retrieval.py --json     # machine-readable (for the write-up)
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sqlite3
import statistics
import sys
import time

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import query  # noqa: E402  (reuses the CLI's search + embed paths)

# (question, expected ref_id, kind of the expected record)
# Documents are referenced by repo-relative path; ledger evidence by its id.
GOLD: list[tuple[str, str, str]] = [
    ("how do vibrational frequencies test the curvature of a potential energy surface",
     "docs/phonon_benchmarking_report.md", "document"),
    ("does simulation cell size change predicted elastic constants for copper and nickel",
     "docs/layer2_research_paper.md", "document"),
    ("choosing which interatomic potential to evaluate next using uncertainty estimates",
     "docs/bayesian_active_learning_report.md", "document"),
    ("what does EAM stand for and other force-field terminology",
     "GLOSSARY.md", "document"),
    ("government grants available for computational materials research infrastructure",
     "docs/funding_landscape_report.md", "document"),
    ("design for multi-model strategy selection with an embedded evidence store",
     "docs/rfc-omnigents-cocoindex.md", "document"),
    ("why did the aluminium potential come out four percent low on cohesive energy",
     "hyp-al-1", "hypothesis"),
    ("racing several language models on an easy question wastes tokens",
     "coord-0002", "coordination_trace"),
    ("copper C11 stiffness prediction error compared to the reference value",
     "claim-C11-001", "claim"),
    ("a critic caught a units mistake before the final answer was integrated",
     "coord-0003", "coordination_trace"),
    # Published Library corpus (deployed lupine-ledger content, per sync_ledger.py)
    # The environment-error-field paper is PENDING publication — findable as
    # the internal source doc (paper/ is part of the document corpus).
    ("paper on a smooth environment-resolved error field beneath universal potential errors",
     "paper/environment-error-field-2026-07-02.md", "document"),
    ("diagnosis of the global projection operator failing on the elastic benchmark metals",
     "library:mlip-elastic-benchmark/operator-failure-diagnosis-2026-06-27.md", "published_article"),
    ("final round-two verdict on the projection law",
     "library:docs/projection-law-round2-final.md", "published_article"),
    ("guide for crawlers and AI agents to the public lupine websites and viewers",
     "https://library.lupine.science/llms-full.txt", "site_guide"),
    ("which articles are awaiting publication to the public library",
     "publication-drift", "publication_drift"),
]

SEARCH_LIMIT = 10  # distinct-source ranks are computed within this window


def _distinct_source_rank(results: list[dict], expected: str) -> int | None:
    """Rank of `expected` among DISTINCT sources, 1-based. Multiple chunks of
    one document collapse into that document's best rank, and a published
    Library article collapses onto its repo source doc (twin-aware, via the
    bundle manifest) — retrieving either identity of the same content counts."""
    expected = query.canonical_ref(expected)
    seen: list[str] = []
    for r in results:
        rid = query.canonical_ref(r["ref_id"])
        if rid not in seen:
            seen.append(rid)
        if rid == expected:
            return seen.index(rid) + 1
    return None


def run_eval(conn: sqlite3.Connection) -> dict:
    modes: dict[str, dict] = {}
    for mode in ("semantic", "semantic+kind", "keyword"):
        ranks: list[int | None] = []
        latencies: list[float] = []
        for q, expected, kind in GOLD:
            t0 = time.perf_counter()
            if mode == "semantic":
                res = query.semantic_search(conn, q, SEARCH_LIMIT, None)
            elif mode == "semantic+kind":
                # What an agent that knows the evidence kind gets (--kind flag).
                res = query.semantic_search(conn, q, SEARCH_LIMIT, kind)
            else:
                res = query.keyword_search(conn, q, SEARCH_LIMIT, None)
            latencies.append(time.perf_counter() - t0)
            ranks.append(_distinct_source_rank(res, expected))
        n = len(GOLD)
        modes[mode] = {
            "hit@1": sum(1 for r in ranks if r == 1) / n,
            "hit@3": sum(1 for r in ranks if r is not None and r <= 3) / n,
            "hit@5": sum(1 for r in ranks if r is not None and r <= 5) / n,
            "mrr": sum(1.0 / r for r in ranks if r is not None) / n,
            "median_latency_s": round(statistics.median(latencies), 4),
            "ranks": ranks,
        }
    return modes


def time_search_backends(conn: sqlite3.Connection, reps: int = 25) -> dict:
    """Search-only latency (excludes query embedding): vec0 KNN vs brute force."""
    if not query._load_vec(conn):
        return {"error": "sqlite-vec unavailable"}
    blob = np.asarray(query._safe_embed("elastic constants benchmark"),
                      dtype=np.float32).tobytes()
    out: dict = {"rows": conn.execute("SELECT COUNT(*) FROM evidence_chunks").fetchone()[0]}

    for name, fn in (("vec0_knn", lambda c, b, n, _k: query._try_vec0_query(c, b, n)),
                     ("brute_force_cosine", query._manual_cosine)):
        times = []
        for _ in range(reps):
            t0 = time.perf_counter()
            res = fn(conn, blob, 5, None)
            times.append(time.perf_counter() - t0)
        out[name] = {
            "available": res is not None,
            "median_ms": round(statistics.median(times) * 1e3, 2),
        }
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", default=str(HERE / "evidence.db"))
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    db = pathlib.Path(args.db)
    if not db.exists():
        print(f"error: {db} not found — build the index first", file=sys.stderr)
        return 2

    conn = sqlite3.connect(str(db))
    try:
        # Warm the embedder once so the model download/load doesn't pollute
        # per-query latency, and detect fallback mode.
        t0 = time.perf_counter()
        query._safe_embed("warmup")
        model_load_s = round(time.perf_counter() - t0, 2)
        import main as pipeline
        real_model = not pipeline._FALLBACK_ACTIVE and query._QUERY_MODEL is not None

        report = {
            "gold_queries": len(GOLD),
            "real_embedding_model": real_model,
            "model_load_s": model_load_s,
            "modes": run_eval(conn),
            "search_backend_timing": time_search_backends(conn),
        }
    finally:
        conn.close()

    if not report["real_embedding_model"]:
        report["warning"] = ("hash-vector fallback active — semantic metrics "
                             "are NOT meaningful in this environment")

    if args.json:
        print(json.dumps(report, indent=2))
        return 0

    print(f"gold queries: {report['gold_queries']}   "
          f"real model: {report['real_embedding_model']}   "
          f"(model load {report['model_load_s']}s, one-time)")
    if "warning" in report:
        print(f"!! {report['warning']}")
    print()
    print(f"{'mode':<10} {'hit@1':>6} {'hit@3':>6} {'hit@5':>6} {'MRR':>6} {'median s/query':>15}")
    for mode, m in report["modes"].items():
        print(f"{mode:<10} {m['hit@1']:>6.2f} {m['hit@3']:>6.2f} {m['hit@5']:>6.2f} "
              f"{m['mrr']:>6.2f} {m['median_latency_s']:>15}")
    print()
    bt = report["search_backend_timing"]
    if "error" not in bt:
        print(f"search-only latency over {bt['rows']} chunks (excl. embedding): "
              f"vec0 {bt['vec0_knn']['median_ms']}ms vs "
              f"brute-force {bt['brute_force_cosine']['median_ms']}ms")
    # Per-query detail for the misses
    for mode, m in report["modes"].items():
        misses = [(GOLD[i][0], GOLD[i][1], m["ranks"][i])
                  for i in range(len(GOLD)) if m["ranks"][i] != 1]
        if misses:
            print(f"\n[{mode}] queries not ranked #1:")
            for q, exp, rank in misses:
                print(f"  rank {rank or '—':>2}  {exp}  <- \"{q}\"")
    return 0


if __name__ == "__main__":
    sys.exit(main())
