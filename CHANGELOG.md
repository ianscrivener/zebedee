# Changelog

Zebedee — an agent-native work ledger. Versions follow semver: a **minor** bump can add commands or fields; a **major** bump changes the record format (with a migration note).

## 0.1.0 — 2026-11-15

- Stages -2..6, types, domains; `z.toml` config.
- `zebedee/zcli.py` helper behind `zebedee/zebedee.just` recipes; root `justfile` imports it.
- Records store `.records/` (nested git repo): items, per-session agents and events, one file per run.
- Skills: z-ai-init, z-item, z-spike, z-run, z-status.
- `just z-init` on a fresh seed clone: keeps the manual as `README-zebedee.md` and moves `LICENSE`, `CHANGELOG.md`, `Zebedde-Decision-Register.md`, `RETROFIT_PROMPT.md` into `zebedee/`. Skipped in the maintainer checkout (`.zebedee-seed`) and in retrofits.
- MIT licence.
- `--as-of` backdating for migrating history; launchd auto-commit (one job per project, path-hashed labels; add / del / list); migration and triage prompts; smoke test.
