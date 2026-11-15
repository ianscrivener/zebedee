---
name: z-status
description: Get a compact picture of the project's current state — active items by stage, parked items, stale claims, latest test/bench runs, active agent sessions. Use when starting work, choosing what to do next, or reporting progress.
---

# z-status — what's going on

```
just z-status              # summary (generated, never edit)
just sessions              # active / stale agent sessions and the claims they hold
just z-agents              # every registered session (the manifest)
just z-item list --stage -1     # e.g. open spikes
just z-run list --limit 10      # latest results
just z-index               # build .records/index.json (+ index.duckdb if duckdb installed)
```

For ad-hoc questions, run `just z-index` then query `.records/index.duckdb` (tables `items`, `runs`, `events`) rather than reading files:

```
uv run python -c "import duckdb; print(duckdb.connect('.records/index.duckdb').sql(\"SELECT name, metrics FROM runs WHERE kind='bench' ORDER BY ts DESC LIMIT 5\"))"
```

Read `TEMPLATE.md` only if you need a stage, type or domain definition.
