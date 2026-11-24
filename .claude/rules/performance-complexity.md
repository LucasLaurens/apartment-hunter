---
paths:
  - "src/**/*.py"
  - "tests/**/*.py"
---

## Performance
- TTL cache on geocoding (expensive Nominatim calls) — 24h TTL
- Cache deduplication by URL hash before DB insert (skip known IDs); same-home
  grouping is a separate, display-only pass — see `duplicates.py`
- Crawlers run concurrently via `asyncio.gather` with semaphore(5)
- No N+1: batch DB inserts with `executemany`

## Algorithmic Complexity
- Reason about time & space (Big O) for any non-trivial function (loops, recursion, collection work). Annotate when not obvious: `# O(n log n) time, O(n) space`, stating what `n` is.
- Flag any O(n²)-or-worse on potentially large data **before** writing it; propose a better approach.
- Anti-patterns to hunt: `x in list` inside a loop → `set`/`dict` (O(1)); nested loops over the same data → single pass with an auxiliary structure; `str +=` in a loop → `"".join(...)`; repeated `list.insert(0, x)` → `collections.deque`; re-sorting a mutated list → `heapq` or a sorted structure; recomputed subproblems → memoize (`functools.cache`).
- Pick the structure by dominant op: key lookup → `dict`; membership/dedupe → `set`; queue/stack → `deque`; recurring min/max → `heapq`; sorted order maintained → `SortedList`/`bisect`.
- State memory trade-offs (cache, memoization): "O(n²)→O(n) time, O(n) extra space".
- Don't over-optimize: on small/bounded n (< ~100) or one-shot code, prefer readability — but say so.
- Pedagogical mode: when writing/refactoring DSA-heavy code, add a short "Analyse" note explaining the complexity chosen and alternatives rejected.
