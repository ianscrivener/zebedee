# Decisions log — Zebedee (v0.1)

**Zebedee — an agent-native work ledger.** _Ideas to shipped code, with every spike, decision and benchmark on the record._

As of 2026-11-15. v0.1 built and smoke-tested. This repo is the project seed.

The design record for Zebedee itself: why things are the way they are. Update it when a decision changes.

## Naming & tooling
- Name: Zebedee. Helper folder `zebedee/` (`zebedee/zcli.py`); CLI prog `zebedee`.
- Short `z` kept for `just z-*` commands, `z-*` skills, `z.toml` and `Z_RECORDS`.
- Opinionated: requires `uv` and `just`. Recipes run via `uv run python zebedee/zcli.py` by default; `ZEBEDEE_CMD` overrides for projects not run via uv. Helper needs Python ≥3.10 (TOML fallback parser below 3.11).
- DuckDB lives in the project's environment, installed the project's way (`uv add`, `pip install`, `poetry add`).
- `zebedee/tests/smoke.sh`: end-to-end check (31 cases). `CHANGELOG.md`: semver; minor = additive, major = record-format change.

## Commands
- All recipes in `zebedee/zebedee.just`; root `justfile` is the greenfield seed and just has `import 'zebedee/zebedee.just'`. Retrofit = add that one line.
- Prefixes: `z-ai-*` for agents (z-ai-init, z-ai-whoami); `z-agents-*` for the human (z-agents-sessions, alias `sessions`); `z-init*` human setup (z-init, z-init-launchctl-add, z-init-launchctl-del); other `z-*` shared (z-item, z-run, z-status, z-index, z-agents).

## Taxonomy
- Stages -2..6 (Idea, Spike, Decision, Intent, Spec, Unit test, Implementation, Test suite, Observed). See `TEMPLATE.md`.
- Types: feature, bug, enhancement, refactor, chore. Domains: per project, multi-valued, declared in `z.toml`.
- Stage moves: any stage at entry; then forward one step at a time; backward only with a reason. Leaving stage 0 only via a decision (commit → 1, reject, park + revisit trigger). Parked items can be reopened.
- No inbox/triage for now; Idea (-2) is the landing zone.

## Storage
- One folder per work item, time-based IDs (e.g. `20261115-1208-fused-attention`).
- Records live in `project/.records/`: git-ignored by the code repo, its own nested git repo.
- Agents never run git in `.records/`; a launchd job per project (`com.zebedee.records.<folder>-<6-char hash of full path>`) commits every 5 min. The hash stops same-named projects colliding; `add` refuses to overwrite another path's plist; `z-init-launchctl-list` shows all jobs and flags moved or deleted projects.
- Results: one JSONL file per run (SHA, dirty flag, harness version, item id, agent UUID, env snapshot, metrics). Queried with DuckDB.
- Generated files (STATUS.md, index.json, index.duckdb) are never committed.
- In containers, `.records/` is mounted at the same path for all agents and `Z_RECORDS` set, because worktrees won't contain it.

## Migration / history
- `--as-of <ISO>` on item new/stage/decide/reopen/close and run record backdates records. Events and runs also store `recorded_at` and `migrated: true`. No future dates; no dates before item creation. Migrated runs take `--git-sha`; env labelled as captured at import.
- Retrofit prompt: `RETROFIT_PROMPT.md` at the repo root; agents fetch it by URL, defaults built in (repo `ianscrivener/zebedee`, checkpoint `ask`). Non-destructive, branch `zebedee-migration`, checkpoint after plan (`ask` default for early migrations), provenance block on every item, struggle log, and a **required retrospective posted as an issue (label `migration-feedback`) on the Zebedee repo**.

## Feedback loop
- Triage prompt: `zebedee/prompts/triage-feedback.md`, run by an agent in the Zebedee repo. Modes `propose` / `apply-small`.
- The Zebedee repo dogfoods Zebedee: findings become items in its own `.records/`; declined ideas are rejected at stage 0 with a reason.
- Issue text is untrusted (public repo): data, never instructions.
- Dispositions: apply (low-risk only), propose, taxonomy (always human), already tracked, decline. Bug fixes start with a failing smoke-test case.
- One PR per triage run on `triage/<date>`; never push to main or merge; comment on and label every issue `triaged`; `Fixes #n` closes on merge. Never a major version bump without the human.

## Agents
- Skills: z-ai-init, z-item, z-spike, z-run, z-status.
- `/z-ai-init` run naked; agent self-reports `harness | family | model` (marked self_reported) and harness session ID (nullable).
- Script mints a UUIDv7 per session. Manifest = `.records/agents/<uuid>.json`. `just z-agents` lists it.
- Events: `.records/events/<uuid>.jsonl`, one append-only log per session.
- Agents pass `--agent <uuid>` on every write; `just z-ai-whoami --session <id>` recovers a lost UUID.
- Claims: `owner` field; live while owner active within `claim_timeout_hours`; stale claims can be taken; `--force` for live ones.

## Corrections (v0.2)
- Records stay append-only. Runs are **voided, never edited or deleted** (`results/voids/<run_id>.json`); re-record the corrected run.
- Items: `z-item edit` changes title/type/domains and adds provenance, logged with old → new. **IDs never change**, even when the title does, so links stay valid.
- Provenance: `commits` and `sources` are frontmatter list fields (queryable), alongside the free-text Provenance block.
- No "unknown verdict" state: ideas without outcome stay at -2; spikes with no recorded verdict are parked ("verdict not recorded"). Avoids a taxonomy change.
- Migration enters items at the earliest stage the evidence shows; skipping un-evidenced stages at entry is correct, not a workaround (`--entry-note`).
- Helper command: `$ZEBEDEE_CMD` → committed `.zebedee-cmd` → uv default. A committed file, not a shell export, so every agent sees it.

## Bootstrap
- `just z-init` adopts a fresh seed clone: README.md copied to README-zebedee.md; LICENSE, CHANGELOG.md, the decision register and RETROFIT_PROMPT.md move into `zebedee/` so the root is the project's. `zebedee/CHANGELOG.md` then records the project's Zebedee version.
- Guard: only when README.md is still the Zebedee README (so retrofits are never touched), never overwriting, and never in the maintainer checkout, which carries a git-ignored `.zebedee-seed` marker.
- Greenfield: clone the repo; `uv sync`; edit `z.toml`; `just z-init`; optionally `just z-init-launchctl-add`.

## Open (v0.2)
- Spike promote vs rewrite; write-blocking hooks; Hermes/Copilot skill locations; per-project metric schemas; which types require spec.md; how existing projects pull seed updates.
- Env snapshot inside a container describes the VM, not the Mac host — decide where benchmarks run.
