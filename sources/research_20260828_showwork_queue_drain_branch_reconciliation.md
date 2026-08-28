# Queue drain and branch reconciliation — 2026-08-28

Session: `drain-queue-merge-main-20260828`. Task: drain the showwork queue and
merge outstanding work to main. This readout records what was measured, with
the exact commands, so every statement below can be re-run.

## Main

Local `main` was 117 commits behind `origin/main` with 0 local commits ahead
(`git rev-list --left-right --count main...origin/main` returned `0 117`).
It was fast-forwarded to `a598ca0` (merge of PR #63). No merge commit was
created; nothing local was rewritten.

## Branch audit: nothing left to merge

Every branch that still existed was checked against `origin/main`. Two
methods: `git cherry origin/main <branch>` for patch equivalence, and
`git merge-tree --write-tree main <branch>` for residual code delta.

Already patch-equivalent in main (cherry `-`), safe to delete:

- `merge-work-11` through `merge-work-17`, `merge-work-19`, `merge-work-20`,
  `merge-work-22`, `merge-work-24`, `merge-work-26`, `merge-work-27`
- `land-10`, `land-18`, `land-21`, `land-23`, `land-25`
- `origin/docs/code-as-harness-citation` (its one commit `ac67474` landed as
  `59cb47237e357ba8fc127a6506f3e95d49628cca`, PR #30; test merge produced
  zero code delta vs main)

Superseded drafts (cherry `+`, but every fix has a landed twin in main):

- `merge-work-10/18/21/23/25` are earlier drafts of the same fixes their
  `land-N` twins carry. `git diff merge-work-N land-N -- src tests scripts`
  shows the land side is a strict superset in each pair, and each land tip is
  patch-equivalent in main.
- `grok/harden-utf8-ledger-decode` (`ead08a2`, 2026-07-17 11:25) is an
  alternative implementation of the non-UTF-8 ledger fix. The chosen
  implementation landed the same day as
  `1261aabdf4d7b227aa79e8a6144598a795b283d3` (PR #24, 23:38) and was hardened
  further afterward.
- `codex/showwork-origin-ledger-20260807` (`e73ef00`) is the first commit of
  PR #37, which landed as `0873ca32fbbae59ba718559328fc6104abb880aa` with
  three follow-up fixes on top.

Test merges of all seven superseded branches conflict against current main,
because main rewrote the same files afterward. Merging any of them would
regress landed work. The correct action was deletion, not merge.

## Stale receipt byproducts

Three untracked files in `.showwork/` each read "GREEN (0/0 verified), No
claims recorded":

- `audit-2026-08-16.md`
- `audit-session-ruff-cleanup-20260816.md`
- `audit-session-sanitize-replay-value-semantic-20260816.md`

The committed ledger contradicts them: `claims-2026-08-16.jsonl` holds claims
for both named sessions, and `sessions.jsonl` shows both closed GREEN. The
files were generated in a checkout that had no claims files. They were moved
out of the repo, not committed, because a receipt that misstates the ledger
is worse than no receipt. The repo tracks no date-labeled audit file, so
nothing was regenerated in their place.

## Queue state

`Queue/showwork/` holds one open card:
`record-integrity-closure-unmet-verifier-20260827.md`. It is marked
`agent_doable: false`, `do_not_auto: true`, `assignee: patrick`. Its whole
subject is that only Patrick can record or withdraw a decision attributed to
him, so this drain leaves it open and puts the two closure options in front
of him. The stale `_OPEN-INDEX.md` flagged by that card was refreshed to
match the real folder state.
