---
name: z-item
description: Create, claim, advance, decide and close work items in the Zebedee records store. Use whenever you start, move or finish a piece of work (feature, bug, enhancement, refactor, chore).
---

# z-item — work items

Requires your agent UUID from `/z-ai-init`. All commands: `just z-item <sub> … --agent <uuid>`.

## Create

```
just z-item new --agent <uuid> --title "<title>" --type <type> --domains <d1,d2> [--stage N] [--intent "<1-2 sentences>"]
```

- Default entry stage is -2 (idea). Typical entry: feature/enhancement -2, bug 1, refactor/chore 2. Enter at the earliest stage that really happened. Don't invent stages to step through; `--entry-note` says why you entered late.
- Provenance: `--commit <sha|a..b>` and `--source <path@sha>`, both repeatable.
- Entering at stage ≥1 needs `--intent`: what it achieves and why, no *how*.
- You own new items automatically. Prints the item ID.

## Find

```
just z-item list [--stage N] [--type T] [--domain D] [--status S] [--owner UUID] [--all] [--json]
just z-item show <id>        # id prefix is fine
```

## Claim / release

```
just z-item claim <id> --agent <uuid>
just z-item release <id> --agent <uuid>
```

A claim held by a **stale** session (see `just sessions`) can be taken with a plain `claim`. `--force` overrides a *live* claim: use it only when you're sure that session is dead.

## Move through stages

```
just z-item stage <id> --agent <uuid> --to N [--reason "<why>"]
```

- Forward one step at a time. Backward needs `--reason`.
- Stage 0 is the gate. Leave it only with a decision:

```
just z-item decide <id> --agent <uuid> --verdict commit|reject|park --reason "<one line>" [--revisit "<trigger>"]
```

  commit → stage 1; reject → closed with a tombstone; park → needs `--revisit`. Reject and park release your claim.

When a parked item's revisit trigger fires:

```
just z-item reopen <id> --agent <uuid> --reason "<trigger fired>"
```

## Fix mistakes

```
just z-item edit <id> --agent <uuid> --reason "<why>" [--title "…"] [--type T] [--domains d1,d2] [--add-commit SHA] [--add-source PATH]
```

The ID never changes, so links stay valid. Every edit is logged.

## Documents

```
just z-item doc <id> spec --agent <uuid>     # prints path; then edit the body
```

Write a spec only when the intent isn't enough to write tests from. Keep it short.

## Finish

```
just z-item close <id> --agent <uuid>        # from stage 5 or 6
```

## Migrating past work

Add `--as-of <ISO date>` to `new`, `stage`, `decide`, `reopen` and `close` to record when something *actually* happened. Use it only when importing history, never for live work.

## Type rules

- **refactor:** existing tests are the spec and must not change. If they do, it isn't a refactor.
- **bug:** implementation doesn't match spec. If the spec is wrong, say so in Notes; fix the earliest wrong layer.
