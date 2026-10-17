# Private fff source discovery

Implemented adapter: `cocoindex/discover_sources.py`. This is an optional source
path discovery stage before a human/source audit, not a new vector database,
scientific evidence import, full-text search or public Library export.

```sh
python3 -B cocoindex/discover_sources.py --root /absolute/project/path --query comparisonContracts --limit 3
python3 -B -m unittest discover -s cocoindex -p test_discover_sources.py
```

Install/provision fff separately. The adapter finds `fff-mcp` on PATH, or accepts
`FFF_BIN` / `--binary /absolute/path/to/fff-mcp`. Tested against installed v0.11.0.
It invokes an argument list (no shell interpolation), sends JSONL MCP initialize
and **find_files only**, and closes the child on success/failure. Only the exact
"Index is still building; retry shortly" response is retried within the original
deadline. All other protocol/tool failures reject the operation.

An explicit project root is required. Home, root and system trees are refused;
there is no laptop-wide fallback. Watchers, content indexing, mmap warmup, update
checks and persistent content mappings are disabled; no frecency/history database
is configured and logging is off. No persistent adapter cache is created.

Limits: 60 seconds for the session, 768 MiB sampled child RSS, at most 20 returned
paths and 2 MiB per UTF-8 regular source file, 256 KiB buffered protocol output.
RSS is checked with `ps`; unavailable/malformed output fails closed. RSS sampling
is not a kernel-enforced cap and cannot rule out short peaks between samples.
The bounded path set is filtered before reading: outside paths, traversal,
symlinks (including intermediate directories), hidden/private credential and
known generated directories, credential-like filenames, binary and oversized
files are excluded. Source reads use no-follow directory descriptors. This is
conservative filtering, not a general content-classification or secret detector;
the envelope is always private. The server's project scan still traverses its
ignore-filtered project path index; adapter filtering is not a scan exclusion
policy. Do not point it at a root whose path indexing is itself unauthorized.

Each accepted discovery record contains a root-relative path, actual SHA256 and
byte count. The envelope retains the query, `method=fff_fuzzy_path`,
`coverage=partial` and `evidenceStatus=discovery_only_not_evidence_or_support`.
Neither nonmatches nor filtered results establish absence; fuzzy paths do not
establish text matches. No evidence/support relationship, publication status,
scientific result or execution authorization is inferred. Content hashes identify
the bytes read, not source truth or statistical independence.

Focused tests cover exact bytes/hashes, private/generated/outside/symlink filters,
protocol counts, the find-only envelope, failure cleanup, deadline/RSS fail-closed
behavior, and a real JSONL transport with a fake server. A separate bounded local
smoke check against fff v0.11.0 returned three project sources, with 26,064 KiB peak
sampled RSS. No provider/model job, full-text indexing or publication occurred.
