# Zebedee — an agent-native work ledger

_...from ideas to shipped code, with every spike, decision and benchmark on the record._




<img align="right" src="zebedee/zebedee.png">

<sub>v0.1.2 - Sunday 15 Novermber 2026</sub>

For the human. Agents read `AGENTS.md`.

### Setup

```
git clone https://github.com/ianscrivener/zebedee my_project
cd my_project
uv venv
source .venv/bin/activate
uv sync

```




1. Copy this folder (or unzip / use as a git template repo).
2. Edit `z.toml`: set `domains`.
3. `just z-init` creates `.records/` with its own git repo and adds `/.records/` to the code repo's `.gitignore`.
4. Optional: `just z-init-launchctl-add` installs the launchd job that auto-commits `.records/` every 5 minutes. `just z-init-launchctl-del` removes it. Each project gets its own job (`com.zebedee.records.<folder>-<path hash>`), so same-named projects never collide; `just z-init-launchctl-list` shows them all.
5. DuckDB (for `just z-index` SQL queries) is installed by `uv sync`.

Requires `just` and `git`. Opinionated towards `uv`, but works without it:

**Python & how the helper runs.** The helper (`zebedee/zcli.py`) is a single stdlib-only script needing **Python ≥3.10**; DuckDB is optional (only `just z-index` uses it). The recipes find the command in this order: `$ZEBEDEE_CMD` → a committed `.zebedee-cmd` file at the project root → the default `uv run --quiet python zebedee/zcli.py`.

| Project | Put this in `.zebedee-cmd` | DuckDB |
|---|---|---|
| uv Python project | _(nothing: the default works)_ | `uv add duckdb` |
| pip / venv / Poetry Python project | `python zebedee/zcli.py` (run with the venv active) | `pip install duckdb` (+ requirements file) or `poetry add duckdb` |
| Not Python (Node, Rust, Go, …), uv installed | `uv run --quiet --no-project --with duckdb python zebedee/zcli.py` | included by `--with` |
| Not Python, no uv | `python3 zebedee/zcli.py` | optional: `python3 -m pip install --user duckdb` |

## Existing projects

Open an agent at the project root and say: *"Follow https://github.com/ianscrivener/zebedee/blob/main/RETROFIT_PROMPT.md"*. It installs Zebedee alongside the project (one `import` line in the existing justfile), backfills history from git and docs using `--as-of` dates, and posts a retrospective issue to the Zebedee repo.

## Improving Zebedee

Open an agent in this repo and give it `zebedee/prompts/triage-feedback.md`. It reads the feedback issues, tracks them as Zebedee items in this repo's own records, applies low-risk fixes in a PR (smoke test: `zebedee/tests/smoke.sh`), and replies on each issue. You decide the rest.

## Commands

`just --list` shows them grouped. The prefix says who runs it:

| Prefix | Who | Commands |
|---|---|---|
| `z-ai-*` | AI agents, directly | `z-ai-init` (register a session), `z-ai-whoami` (recover a lost UUID) |
| `z-agents-*` | the human, overseeing agents | `z-agents-sessions` (alias `sessions`): active / stale sessions and their claims |
| `z-init*` | the human, project setup | `z-init`, `z-init-launchctl-add`, `z-init-launchctl-del`, `z-init-launchctl-list` |
| other `z-*` | shared | `z-item`, `z-run`, `z-status`, `z-index`, `z-agents` (the manifest) |

## Containers and worktrees

Git worktrees don't contain `.records/`. Mount the project's `.records/` into every container at the same path and set `Z_RECORDS`:

```
-v /ABS/PATH/TO/PROJECT/.records:/records  -e Z_RECORDS=/records
```

## Layout

This is the seed's layout. In a new project, `just z-init` copies this README to `README-zebedee.md` and moves `LICENSE`, `CHANGELOG.md`, `Zebedde-Decision-Register.md` and `RETROFIT_PROMPT.md` into `zebedee/`, so the root is yours.

```
AGENTS.md          agent entry point (tiny); CLAUDE.md imports it
RETROFIT_PROMPT.md migrate an existing project into Zebedee
TEMPLATE.md        stages, types, domains
z.toml             project config
justfile           project recipes; imports zebedee/zebedee.just
zebedee/zebedee.just  all z-* recipes (the only write path for agents)
zebedee/zcli.py    helper behind the recipes
zebedee/templates/ item / spike / decision / spec skeletons
zebedee/launchd/   auto-commit for .records/
zebedee/prompts/   triage-feedback.md — maintainer prompt for processing feedback issues
zebedee/tests/     smoke.sh — end-to-end check of the helper
Zebedde-Decision-Register.md  design decisions for Zebedee itself (why it is the way it is)
CHANGELOG.md       versions; minor = additive, major = record-format change
.claude/skills/    z-ai-init, z-item, z-spike, z-run, z-status
.records/          (created by z-init; own git repo; ignored by the code repo)
  agents/<uuid>.json        one per session — the manifest
  events/<uuid>.jsonl       one append-only log per session
  work/<item-id>/           item.md (+ spike.md, decision.md, spec.md)
  results/runs/*.jsonl      one file per run
  STATUS.md, index.*        generated, never committed
```

Other harnesses: Claude Code reads `.claude/skills/`. For Copilot CLI or Hermes, symlink or copy the skill folders to wherever that harness looks.

## Not in v0.1

Write-blocking hooks · spike promote-vs-rewrite policy · per-project metric schemas · which types require `spec.md` · shared-template update mechanism.
