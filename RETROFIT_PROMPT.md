# Retrofit prompt: migrate an existing project into Zebedee

> **Usage:** open your agent at the root of the project to migrate and say:
>
> *"Follow https://github.com/ianscrivener/zebedee/blob/main/RETROFIT_PROMPT.md"*
>
> Settings (defaults apply unless the human says otherwise):
>
> - **Project:** the agent's current working directory
> - **Template repo:** `ianscrivener/zebedee`
> - **Checkpoint:** `ask` (stop for human approval after the plan). The human can say `auto` to proceed and report.

---

You are migrating the project in your current working directory from its current ad hoc state into **Zebedee, an agent-native work ledger** (template: `ianscrivener/zebedee`).

The goal is to **extract the project's history and knowledge** from git commits, docs, notes, logs and test/benchmark output into Zebedee's structured records. A future agent should be able to answer "what was tried, what was decided, why, and what did it measure?" by querying Zebedee instead of reading the old docs.

## Required deliverables

1. The migrated records in `.records/` (Phases 0–5).
2. A short report for the human (Phase 6).
3. **A retrospective, posted as a GitHub issue on the template repo `ianscrivener/zebedee`** (Phase 7). This is not optional. The template improves only through these issues: say honestly how hard or easy the migration was, what you struggled with, and your ideas and suggestions.

## Ground rules

1. **Non-destructive.** Never delete, move or rewrite existing project files or git history. Old docs stay where they are; you propose an archive plan, and the human decides.
2. **Work on a branch** of the code repo: `zebedee-migration`. Commit template files there; do not merge.
3. **Write records only through `just z-*` commands.** Never hand-edit frontmatter in `.records/`. Body text of `spike.md` / `spec.md` in items you own is fine.
4. **Token discipline.** Inventory before reading. Use `git log --stat`, `git log --format`, `ls`, `wc -l` and `grep` to find what matters, then read selectively. Do not read every file end to end.
5. **Provenance on everything.** Every migrated record says where it came from (file path, commit SHAs, original dates). If a fact is inferred rather than stated in a source, mark it `inferred`.
6. **Granularity: one item per meaningful unit of work** (a feature, a performance experiment, a bug fix worth remembering, a significant refactor). Not one per commit. Trivial commits (typos, formatting, version bumps) are not migrated unless they're part of a larger item.
7. **Agent history is optional.** If commits or docs reveal which agent or model did the work, note it in Provenance. Don't spend effort hunting for it.
8. **Keep a struggle log** as you go, in `.records/migration/struggles.md`: anything confusing, missing from Zebedee, awkward or slow. You'll need it for the retrospective. Write in it the moment something is hard, not at the end.

## Phase 0: Install Zebedee

1. Fetch the template outside the project: `git clone --depth 1 https://github.com/ianscrivener/zebedee "$(mktemp -d)/zebedee-seed"`. Read its `README.md` (the Zebedee manual), `AGENTS.md` and `TEMPLATE.md`, and nothing else from it yet.
2. Copy the template files into the project **without overwriting** anything:
   - `zebedee/` (helper, `zebedee.just` recipes, templates, launchd, prompts), `.claude/skills/z-*`, `TEMPLATE.md`, `z.toml`: copy if absent.
   - The seed's `LICENSE`, `CHANGELOG.md`, `Zebedde-Decision-Register.md` and `RETROFIT_PROMPT.md` → the project's `zebedee/` folder (never the project root). `zebedee/CHANGELOG.md` records which Zebedee version the project is on.
   - The seed's `README.md` → the project's `README-zebedee.md`. **Never touch the project's own `README.md`.** Add one line to it pointing at `README-zebedee.md`, if the project's conventions allow.
   - `justfile`: if the project has one, **add this line** near the top: `import 'zebedee/zebedee.just'`. Don't copy the recipes in. If there's no justfile, copy the template's root `justfile`. If a project recipe name clashes with a `z-*` recipe, keep the project's recipe and note the clash in the struggle log.
   - `AGENTS.md` / `CLAUDE.md`: if they exist, **append** a short Zebedee section pointing at the `z-*` skills. Don't replace their content.
   - **DuckDB:** install it the way this project already installs packages, e.g. `uv add duckdb` (uv), `pip install duckdb` plus adding it to `requirements*.txt` (pip), or `poetry add duckdb` (Poetry). Don't introduce a new package manager.
   - **How the helper runs:** the recipes default to `uv run python zebedee/zcli.py`. If the project isn't run via uv, set `ZEBEDEE_CMD` to the right invocation (e.g. `export ZEBEDEE_CMD="python zebedee/zcli.py"` inside the project's activated environment), document that in the project README, and note it in the struggle log.
   - The helper needs Python ≥3.10. If the project's Python is older, stop and tell the human.
3. Run `just z-init` to create `.records/`.
4. Register yourself: `/z-ai-init` (skill). Keep your UUID and pass `--agent <uuid>` on every write.
5. `mkdir -p .records/migration`. The struggle log, plan and report live there.

## Phase 1: Inventory (read little, list much)

Produce `.records/migration/inventory.md` containing:

- **Repo shape:** languages, top-level layout, size, first and last commit dates, commit count, branches and tags.
- **Docs:** every markdown/text doc with path, size, last-modified commit and a one-line guess at its purpose (design note, perf idea, results, TODO, changelog, README…). Get the guess from the filename, headings (`grep '^#'`) and first lines, not a full read.
- **Results sources:** test logs, benchmark outputs, CSV/JSON/JSONL results, CI logs and notebooks, with paths and formats.
- **Test harness history:** when the tests or benchmark harness changed significantly (`git log --stat -- tests/ bench*/`). Results from different harness versions aren't comparable, so you need these boundaries.
- **Work signals in git:** branches named `spike/`, `exp/`, `perf/` or `feature/`; reverted commits; commit messages mentioning try, experiment, revert, benchmark, faster, slower, regression, fix, refactor.
- **Existing trackers:** GitHub issues/PRs if accessible (`gh issue list`, `gh pr list --state all`), TODO files, `TODO:` comments.

## Phase 2: Domains and the migration plan

1. Propose the project's **domains** from the template list (`TEMPLATE.md`), plus any project-specific additions, and set them in `z.toml`.
2. Write `.records/migration/plan.md`: a **candidate item list** in a table, with one row per proposed item:

   | # | Title | Type | Domains | Final stage | Status | Sources (paths, SHAs) | Confidence |
   |---|---|---|---|---|---|---|---|

   - **Type:** feature, bug, enhancement, refactor or chore (definitions in `TEMPLATE.md`).
   - **Final stage:** where the work actually got to. Shipped and tested is 5. Shipped with observed or benchmarked behaviour is 6. An abandoned experiment ends at 0 with a reject or park decision. A written but unbuilt idea is -2.
   - **Status:** active, done, rejected or parked.
   - **Confidence:** high if the docs state it, medium if it's clear from commits, low if inferred.
   - Mark which items are **spikes** (feasibility or performance experiments). These are the highest-value records. Rejected spikes become tombstones that stop future agents repeating dead ends.
3. Include a **results migration plan**: which historical results you'll import, mapped to items and harness versions, and which you'll skip and why.
4. **If the checkpoint setting is `ask` (the default): stop here.** Summarise the plan for the human (item counts by type and status, key spikes, open questions) and wait for approval or edits.

## Phase 3: Create the items

Work through the plan **oldest first**, so the records read chronologically.

For each item:

1. **Create it at its entry stage** with an intent, **backdated** with `--as-of` to when the work started (the first relevant commit or doc date):
   ```
   just z-item new --agent <uuid> --title "…" --type … --domains … --stage <entry> \
     --intent "<what it achieved and why, 1–2 sentences>" --as-of 2026-03-02T10:00
   ```
   The item ID then carries the original date, so `ls .records/work/` reads as the real timeline.
   - **Entry stage:** -2 if it started as an idea, -1 if it was an experiment, otherwise the earliest stage the evidence supports (often 1).
2. **Advance it to its final stage** with `just z-item stage … --to N --as-of <date>`, one step at a time, each step dated from the evidence. A date that isn't in the evidence gets the nearest known date, noted as inferred. At stage 0, use `just z-item decide … --as-of <date>` with the historical verdict and reason (`park` needs `--revisit`). `--as-of` also works on `close` and `reopen`.
3. **Add provenance to the item body** (under Notes, via the item's files you own). Use exactly this shape:
   ```
   ### Provenance (migrated)
   - Sources: docs/perf-ideas.md@a1b2c3d, notes/kernel.md@e4f5g6h
   - Commits: a1b2c3d..9z8y7x6 (12 commits)
   - Original dates: 2026-03-02 → 2026-04-10
   - Agents/models: unknown | <if known>
   - Confidence: high | medium | low (inferred: <what>)
   ```
4. **Spikes:** create `spike.md` (`just z-item doc <id> spike`) and fill in Hypothesis, Success criterion, Results (numbers, briefly) and Verdict from the historical sources. Keep it to a page at most; link to the old doc for detail.
5. **Specs:** only create `spec.md` if a real specification existed. Summarise it and link the original. Don't invent specs.
6. **Close done items** with `just z-item close`.

**Timestamps:** `--as-of` records when something happened. Zebedee also stores `recorded_at` (now) and marks the record `migrated`, so imported history can always be told apart from live work. Dates can't be in the future or before the item's creation.

## Phase 4: Import historical results

For each result source in the plan:

- Record **representative runs**, not every line: baselines, before/after pairs for each spike, and regressions.
  ```
  just z-run record --agent <uuid> --kind bench|suite|unit --mode controlled|observed --name "…" \
    --harness-version "<sha or version at the time>" --item <id> \
    --as-of <original timestamp> --git-sha <commit the run was made at> \
    --metrics '{"…": …, "source": "<path>@<sha>"}'
  ```
- The environment snapshot is captured at import and labelled as such. Put any historical environment details you find (machine, OS, versions) into `metrics` under `historical_env`.
- If results can't be tied to a harness version, use `"harness-version": "unknown"` and log it.

## Phase 5: Verify

1. `just z-index`, then `just z-status`.
2. Check:
   - every plan row became an item (or is listed as skipped with a reason)
   - every spike has a verdict
   - every item has provenance
   - stage and status distributions match the plan
3. **Spot-check 5 items against their sources** with fresh eyes: does the record say what the source says? Fix any discrepancies.
4. Answer these from Zebedee alone (queries, not old docs). Note any you can't answer:
   - What performance experiments were tried, and which were kept?
   - What was rejected, and why?
   - What does the latest benchmark show, and against which baseline?
   - What's still open?

## Phase 6: Report to the human

Write `.records/migration/report.md`, kept short:

- Counts: items by type, stage and status; spikes kept vs rejected; runs imported.
- **Archive proposal:** which old docs are now fully captured and could move to `docs/archive/` or be deleted, and which still hold unique knowledge. Don't move anything yourself.
- Known gaps and low-confidence items.
- How to review: the 3–5 items most worth a human look.

## Phase 7: Retrospective and template issue

1. Write `.records/migration/retrospective.md`:
   - **Difficulty:** 1–5 overall, and per phase, with a sentence each.
   - **Effort:** rough time and token cost, and which phase dominated.
   - **What worked well** in Zebedee for this.
   - **What was hard:** from your struggle log, concrete, each with an example.
   - **Missing features:** commands, fields or conventions you needed but didn't have.
   - **Suggestions:** specific changes to the template, skills, prompt or taxonomy, each with the problem it solves.
   - **Taxonomy fit:** did the stages, types and domains fit this project's history? What didn't fit?
2. File an issue on the template repo:
   ```
   gh issue create --repo ianscrivener/zebedee \
     --title "Migration retrospective: <project name> (<date>)" \
     --body-file .records/migration/retrospective.md --label migration-feedback
   ```
   - If the label doesn't exist, file without it.
   - If `gh` isn't available or authenticated, leave the retrospective file in place and tell the human the issue still needs filing.
   - **Don't include secrets, private paths or proprietary code in the issue.** It may be public. Summarise rather than paste.
3. Release any claims you still hold.
4. Final message to the human: three lines covering what was migrated, the report path and the issue link.

## Done checklist

- [ ] Records migrated, verified, with provenance on every item
- [ ] `report.md` written, with the archive proposal
- [ ] `retrospective.md` written
- [ ] **Retrospective posted as an issue on `ianscrivener/zebedee`** (or the human told exactly why it couldn't be)
- [ ] Claims released
