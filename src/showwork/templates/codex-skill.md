---
name: showwork-receipts
description: Record falsifiable acceptance requirements and claims for code changes with showwork, close through its explicit finish gate, and inspect another agent's receipts without inheriting its verdict. Use when a user requests showwork evidence or the project requires showwork verification.
---

# Showwork receipts

Use the project's Python environment containing showwork. Run `python -m showwork
--help` first. If it is unavailable, report the missing prerequisite and keep the
work unverified; do not install into a global environment or change host trust.

Choose one unique task slug per writer. Start with `python -m showwork start
--session SLUG --agent codex`. Declare each named requirement with `require`
before recording completion claims. Artifact observations use artifact scope;
changed behavior needs behavior scope with a Python acceptance script exercising
the real path and a control that fails when it is broken. A test command returning
zero with no meaningful assertions does not establish adequate coverage.

Record actual changed outcomes with falsifiable `claim` checks. Run the project's
required tests, then `python -m showwork finish --session SLUG --status ok`.
Fix a refusal or retract an inaccurate claim truthfully. Never bypass verification
to manufacture success. Commit this writer's claims, events and snapshot with the
change, then run `python -m showwork gate --session SLUG --require-tracked`.
Keep other writers' files intact.

When reviewing another task, inspect `receipts --session SLUG --json` and the named
requirements, check scope, freshness and disabled checks. Reading a recorded close
does not execute its acceptance checks. Require explicit trusted execution and an
adequacy review before adopting a behavior result. Missing or unsupported evidence
stays unknown.

The optional native Stop hook observes an already completed stop. It cannot undo
execution or enforce pre-dispatch policy. Set SHOWWORK_SESSION in the Codex
launcher's environment to bind it to this task; a child shell export cannot change
the parent host. Review each project hook through Codex's native trust UI. Never
bypass hook trust. The explicit `finish` and committed `gate` commands are the
acceptance boundaries.
