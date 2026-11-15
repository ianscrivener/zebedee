# Agents: read this first

This project uses **Zebedee**, an agent-native work ledger. Work is tracked in a records store (`.records/`, or `$Z_RECORDS` in containers).

1. **Register first.** Run `/z-ai-init` (skill). Keep the UUID it gives you and pass `--agent <uuid>` on every write.
2. **Write records only through `just z-*` commands.** Never create, move or edit frontmatter in `.records/` by hand, and never run git there.
3. **You may edit the body text** (below the frontmatter) of `item.md`, `spike.md` and `spec.md` in an item you have claimed.
4. **Read only what your task needs.** Use `just z-item list`, `just z-item show <id>`, `just z-run list`, `just z-status`. Don't browse `.records/`.
5. **The taxonomy** (stages, types, domains) is in `TEMPLATE.md`. Use only declared values (`z.toml`).

Skills: `z-ai-init`, `z-item`, `z-spike`, `z-run`, `z-status`.

Commands: `z-ai-*` are yours. `z-agents-*` and `z-init*` are for the human — don't run them. Other `z-*` are shared.
