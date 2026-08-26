#!/usr/bin/env python3
import collections

import pyarrow.parquet as pq

p = pq.ParquetFile("inputs/mptrj-test.parquet")
print("rows", p.metadata.num_rows, "row_groups", p.metadata.num_row_groups)
print("schema", p.schema_arrow)
cols = ["task_id", "num_atoms", "numbers", "forces", "energy"]
counts = collections.Counter()
valid = collections.Counter()
reasons = collections.Counter()
for batch in p.iter_batches(columns=cols):
    for row in batch.to_pylist():
        task = str(row.get("task_id"))
        counts[task] += 1
        nums = row.get("numbers") or []
        force_rows = row.get("forces") or []
        if not nums:
            reasons["missing_numbers"] += 1
            continue
        if int(row.get("num_atoms") or 0) != len(nums):
            reasons["atom_count"] += 1
            continue
        if len(nums) > 80 or min(nums) < 1 or max(nums) > 83:
            reasons["element_or_size"] += 1
            continue
        if not force_rows or max(abs(float(x)) for vector in force_rows for x in vector) <= 1e-8:
            reasons["force_values"] += 1
            continue
        if row.get("energy") is None:
            reasons["energy"] += 1
            continue
        valid[task] += 1
print("unique_tasks", len(counts), "max_rows_per_task", max(counts.values()), "task_count_ge8", sum(v >= 8 for v in counts.values()))
print("valid_rows", sum(valid.values()), "valid_tasks", len(valid), "max_valid_per_task", max(valid.values()) if valid else 0, "eligible_ge8", sum(v >= 8 for v in valid.values()))
print("count_hist", sorted(collections.Counter(counts.values()).items()))
print("valid_hist", sorted(collections.Counter(valid.values()).items()))
print("filter_reasons", dict(reasons))
print("top_tasks", counts.most_common(10))
