# Project commands. `just --list` shows everything, grouped.
#
# Zebedee (agent-native work ledger) recipes come from the import below.
# Don't copy them here; update zebedee/ from the Zebedee repo instead.

import 'zebedee/zebedee.just'

# Show available recipes
default:
    @just --list

# ── project recipes ──────────────────────────────────────────────────
