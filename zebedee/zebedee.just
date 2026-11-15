# Zebedee — an agent-native work ledger. Recipes (v0.2).
#
# Imported by the project's root justfile:   import 'zebedee/zebedee.just'
# Don't edit in a project; update from the Zebedee repo instead.
#
# Naming:
#   z-ai-*      for AI agents to run directly
#   z-agents-*  for the human, to oversee agents
#   z-init*     for the human, once per project (setup)
#   other z-*   shared: agents and the human
#
# Agents: write records ONLY through these recipes.
#
# How the helper runs (Python ≥3.10, stdlib only; DuckDB optional for z-index):
#   1. $ZEBEDEE_CMD, if set
#   2. else the contents of .zebedee-cmd at the project root (commit it, so every agent uses it)
#   3. else the default for uv Python projects
# Non-Python projects: echo 'uv run --quiet --no-project --with duckdb python zebedee/zcli.py' > .zebedee-cmd

zebedee_cmd := env("ZEBEDEE_CMD", `c=$(grep -v '^[[:space:]]*#' .zebedee-cmd 2>/dev/null | grep . | head -1); echo "${c:-uv run --quiet python zebedee/zcli.py}"`)

# ── human: project setup ─────────────────────────────────────────────

# Create the records store (.records/) and its git repo. On a fresh seed clone, also keeps the manual as README-zebedee.md and moves Zebedee's own files into zebedee/. Run once per project.
[group('human: setup')]
z-init:
    @{{zebedee_cmd}} setup

# Install the launchd job that auto-commits .records/ every 5 min (macOS host)
[group('human: setup')]
z-init-launchctl-add:
    #!/usr/bin/env bash
    set -euo pipefail
    [ "$(uname)" = "Darwin" ] || { echo "z-init-launchctl-add: macOS host only" >&2; exit 1; }
    [ -d .records/.git ] || { echo "no .records/ git repo — run 'just z-init' first" >&2; exit 1; }
    # Label = folder name + hash of the full path, so same-named projects never collide.
    name="$(basename "$PWD" | tr -c 'A-Za-z0-9._\n-' '-')"
    hash="$(printf %s "$PWD" | shasum | cut -c1-6)"
    label="com.zebedee.records.${name}-${hash}"
    plist="$HOME/Library/LaunchAgents/${label}.plist"
    if [ -f "$plist" ] && ! grep -q "<string>${PWD}/.records</string>" "$plist"; then
      echo "refusing: ${plist} belongs to a different project path" >&2; exit 1
    fi
    mkdir -p "$HOME/Library/LaunchAgents"
    sed -e "s|com.zebedee.records.PROJECT|${label}|g" -e "s|/ABS/PATH/TO/PROJECT|${PWD}|g" \
        zebedee/launchd/com.zebedee.records.PROJECT.plist > "$plist"
    launchctl bootout "gui/$(id -u)/${label}" 2>/dev/null || true
    launchctl bootstrap "gui/$(id -u)" "$plist"
    echo "installed ${label}"
    echo "  plist: ${plist}"
    echo "  log:   /tmp/${label}.err"

# Remove the launchd auto-commit job for this project (macOS host)
[group('human: setup')]
z-init-launchctl-del:
    #!/usr/bin/env bash
    set -euo pipefail
    [ "$(uname)" = "Darwin" ] || { echo "z-init-launchctl-del: macOS host only" >&2; exit 1; }
    name="$(basename "$PWD" | tr -c 'A-Za-z0-9._\n-' '-')"
    hash="$(printf %s "$PWD" | shasum | cut -c1-6)"
    label="com.zebedee.records.${name}-${hash}"
    plist="$HOME/Library/LaunchAgents/${label}.plist"
    launchctl bootout "gui/$(id -u)/${label}" 2>/dev/null && echo "unloaded ${label}" || echo "${label} was not loaded"
    if [ -f "$plist" ]; then rm "$plist" && echo "removed ${plist}"; fi

# List every Zebedee auto-commit job on this Mac, its project, and whether that project still exists
[group('human: setup')]
z-init-launchctl-list:
    #!/usr/bin/env bash
    set -uo pipefail
    [ "$(uname)" = "Darwin" ] || { echo "z-init-launchctl-list: macOS host only" >&2; exit 1; }
    shopt -s nullglob
    found=0
    for plist in "$HOME"/Library/LaunchAgents/com.zebedee.records.*.plist; do
      found=1
      label="$(basename "$plist" .plist)"
      records="$(grep -o '<string>[^<]*/\.records</string>' "$plist" | sed 's|<string>||; s|</string>||')"
      loaded="not loaded"; launchctl print "gui/$(id -u)/${label}" >/dev/null 2>&1 && loaded="loaded"
      exists="ok"; [ -d "$records/.git" ] || exists="MISSING (project moved or deleted? run z-init-launchctl-del there, or remove the plist)"
      printf '%-48s %-10s %s  %s\n' "$label" "$loaded" "${records%/.records}" "$exists"
    done
    [ "$found" = 1 ] || echo "no Zebedee launchd jobs installed"

# ── human: oversee agents ────────────────────────────────────────────

# Active and stale agent sessions, with claims held
[group('human: agents')]
[positional-arguments]
z-agents-sessions *args:
    @{{zebedee_cmd}} sessions "$@"

alias sessions := z-agents-sessions

# ── AI agents ────────────────────────────────────────────────────────

# Register an agent session; prints its UUID. Usage: just z-ai-init --harness "Claude Code" --family Claude --model "Opus 5.5" [--session ID]
[group('ai')]
[positional-arguments]
z-ai-init *args:
    @{{zebedee_cmd}} init "$@"

# Recover a lost UUID from the harness session ID
[group('ai')]
[positional-arguments]
z-ai-whoami *args:
    @{{zebedee_cmd}} whoami "$@"

# ── shared ───────────────────────────────────────────────────────────

# The agent manifest: every registered session
[group('shared')]
z-agents:
    @{{zebedee_cmd}} agents

# Work items: new | list | show | claim | release | stage | decide | reopen | edit | close | doc
[group('shared')]
[positional-arguments]
z-item *args:
    @{{zebedee_cmd}} item "$@"

# Test/benchmark results: record | list | void
[group('shared')]
[positional-arguments]
z-run *args:
    @{{zebedee_cmd}} run "$@"

# Generated summary (add --write to also write .records/STATUS.md)
[group('shared')]
[positional-arguments]
z-status *args:
    @{{zebedee_cmd}} status "$@"

# Build .records/index.json and index.duckdb
[group('shared')]
z-index:
    @{{zebedee_cmd}} index
