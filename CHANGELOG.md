# Changelog

Zebedee — an agent-native work ledger. Versions follow semver: a **minor** bump can add commands or fields; a **major** bump changes the record format (with a migration note).

## 0.2.0 — 2026-11-15

From the first migration retrospective (#1). Additive; no record-format changes.

- `z-item edit`: correct title, type or domains, or add provenance (`--add-commit`, `--add-source`). ID never changes; every edit is logged.
- `z-item new --commit / --source` (repeatable) store provenance as queryable fields; `--entry-note` records why an item entered at its stage.
- `z-run void <run_id> --reason`: runs are never edited or deleted. Voided runs are hidden from `list`/`status` and the `live_runs` DuckDB view, and kept in `runs` + `voids`. `z-run list --include-void` shows them.
- Helper command resolution: `$ZEBEDEE_CMD` → committed `.zebedee-cmd` file → uv default. README table covers uv, pip/Poetry and non-Python projects.
- Retrofit prompt: enter items at the earliest stage the evidence shows (no invented stages); ideas without outcome stay at -2; spikes with no recorded verdict are parked (`verdict not recorded`).

## 0.1.0 — 2026-11-15

- Stages -2..6, types, domains; `z.toml` config.
- `zebedee/zcli.py` helper behind `zebedee/zebedee.just` recipes; root `justfile` imports it.
- Records store `.records/` (nested git repo): items, per-session agents and events, one file per run.
- Skills: z-ai-init, z-item, z-spike, z-run, z-status.
- `just z-init` on a fresh seed clone: keeps the manual as `README-zebedee.md` and moves `LICENSE`, `CHANGELOG.md`, `Zebedde-Decision-Register.md`, `RETROFIT_PROMPT.md` into `zebedee/`. Skipped in the maintainer checkout (`.zebedee-seed`) and in retrofits.
- MIT licence.
- `--as-of` backdating for migrating history; launchd auto-commit (one job per project, path-hashed labels; add / del / list); migration and triage prompts; smoke test.
