---
name: z-run
description: Record a test or benchmark run (with git SHA, harness version and environment snapshot) in the Zebedee results store, or look up past runs. Use after running unit tests, the test suite or any benchmark.
---

# z-run — test & benchmark results

## Record

```
just z-run record --agent <uuid> --kind unit|suite|bench --name "<test or bench name>" \
  --harness-version "<version>" --metrics '<json>' [--item <id>] [--mode controlled|observed] [--pass|--fail]
```

- `--metrics` is a JSON object (or `@path/to/file.json`), e.g. `'{"passed":41,"failed":0}'` or `'{"s_per_image":2.1,"peak_gb":9.4}'`.
- `--harness-version`: the version of the test/bench harness (e.g. its git SHA or semver). Results from different harness versions aren't comparable, so always set it.
- `--mode controlled` (default) = quiet machine, fixed settings. `observed` = real-world conditions.
- The command adds the git SHA, dirty flag and an environment snapshot automatically.
- Inside a container the snapshot describes the container VM, not the Mac host. Run benchmarks on the host when host conditions (swap, thermals) matter.

Importing a historical result? Add `--as-of <original timestamp> --git-sha <commit>`. The record is marked `migrated`.

## Fix a wrong run

Runs are never edited or deleted. Void the wrong one, then record it again:

```
just z-run void <run_id> --agent <uuid> --reason "<what was wrong>"
```

`run_id`: the last 8 characters shown by `z-run list` are enough. Voided runs are hidden from `list`, `status` and the `live_runs` DuckDB view, but kept (`list --include-void`, `runs` table).

## Look up

```
just z-run list [--item <id>] [--name <name>] [--kind K] [--limit N] [--json]
```

Use this instead of reading log files.
