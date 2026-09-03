---
created: 2026-09-03 22:15
type: work
priority: P1
originating_agent: cursor
originating_task: cursor-bmd-vault-card
status: open
last_reviewed: 2026-09-03 22:15
tracker: vault
github_project: none
decision_type: none
question: Overlay showwork receipts on BMD Home/Activity badges from the local vault card, not a GitHub Project.
recommendation: copy this file into the vault Requests folder and implement against bmd-desktop locally
default_action: leave the engine in showwork PR #68; do not board GitHub Projects
expires: 2026-10-03
blast_radius: low
decision: n/a
---

# Request: BMD overlay receipts (vault card)

## Patrick's words (verbatim)

ok just use like fucking the vault locally or something else i dont ffel like dicking around in github

## Ask

Track this work as a local vault request. Do not put it on GitHub Projects.
GitHub user boards (`/users/bmdhodl/projects/5`) are invisible to the cloud
box. Drop this file into the vault `Requests/` folder on the desktop machine
and implement the overlay in private `bmd-desktop` from there.

## Why

BMD already reads vault claims and ticket frontmatter for
`verified` / `claimed` / `failed` / `unknown`. That is the board this box
can actually participate in: markdown in the vault, not a GitHub ProjectV2
node. The engine for the overlay already landed in showwork
(`showwork.receipts`, examples/bmd/). The remaining work is local.

## What the agent tried

- Engine + copy-paste: showwork PR #68, `examples/bmd/README.md`.
- GitHub issue #70 as a scoped card. Could not add it to project 5
  (`Could not resolve to a ProjectV2 with the number 5`).
- Confirmed this token can read public project 4 only. Project 5 is private.

## Done when (local, in bmd-desktop + vault)

1. This request exists in the vault `Requests/` folder (same frontmatter).
2. Pin `showwork==0.4.0` in BMD `requirements.txt`. PyInstaller
   `hiddenimports` collect showwork (skip `showwork.pytest_plugin`).
   `/api/ping` stays zero-work. Boot with no `.showwork/` still pings.
3. `lab/verification_badges.py` calls `overlay_record` after the existing
   vault/frontmatter resolution. Overlay never writes the ledger. Vault
   claims stay the fallback when overlay is `unknown`.
4. Dispatch sets `SHOWWORK_SESSION=bmd-<task_id>` and `SHOWWORK_ROOT=<workspace>`.
   Prompt uses the sidecar interpreter. No `showwork run --gate` on this slice.
5. Empty workspace Home is UNKNOWN. GREEN fixture is VERIFIED. Prose-only
   is CLAIMED. Activity uses the same four states.

Copy-paste for the private repo: `examples/bmd/README.md`.

## Guardrails

- Two engines stay split. Do not migrate vault `config/claims` to showwork.
- Do not add `.showwork/` to `bmdhodl/bmd-desktop` git.
- Do not use GitHub Projects as the tracker for this card.

## Unblocker

On the desktop machine, copy this file into the vault:

```
Requests/bmd-overlay-receipts.md
```

Then implement against `bmd-desktop`. No GitHub board step.

## Resume path

Next agent on bmd-desktop (local, with the vault mounted) implements the
five done-when items. This public repo does not write the vault and does
not write the private BMD tree.
