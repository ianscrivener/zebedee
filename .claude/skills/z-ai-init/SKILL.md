---
name: z-ai-init
description: Register this agent session with the project's Zebedee records store and load the core rules. Run once at the start of every session, before any other z- skill or any work on the project.
---

# z-ai-init — register this session

1. Identify yourself as `harness | family | model`, e.g. `Claude Code | Claude | Opus 5.5`. Give your best knowledge; it is recorded as self-reported.
2. If your harness exposes a session ID, include it (it lets you recover your UUID later).
3. Run:

   ```
   just z-ai-init --harness "<harness>" --family "<family>" --model "<model>" [--session "<harness-session-id>"]
   ```

4. The command prints your **agent UUID**. Keep it. Pass `--agent <uuid>` on every Zebedee write for the rest of this session.
5. Lost it (e.g. after context compaction)? Run `just z-ai-whoami --session <harness-session-id>`.

If the command reports the records store is missing, tell the user: it needs `just z-init`, or `Z_RECORDS` set to the mounted path.

## Core rules

- Write records **only** through `just z-*`. Never hand-edit frontmatter in `.records/`, never run git there.
- Every work item has one **stage** (-2 idea … 6 observed), one **type** (feature, bug, enhancement, refactor, chore) and one or more **domains** declared in `z.toml`. Full definitions: `TEMPLATE.md`. Read it only if you need a definition.
- Claim an item before changing it; release it when you stop. In a claimed item you may edit body text (below the frontmatter) of `item.md`, `spike.md` and `spec.md`.
- Query rather than browse: `just z-item list`, `just z-item show <id>`, `just z-status`.

Next skills: `z-item` (work items), `z-spike` (experiments), `z-run` (test/bench results), `z-status` (what's going on).
