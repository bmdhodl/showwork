---
title: showwork 0.6.6
excerpt: Merging main no longer fails your agent's check.
---

showwork 0.6.6 is on PyPI.

## The fix

Many repos make a branch merge main before it can merge. That merge brings in files that other people changed. The showwork check in CI counted those files against the agent's session, so the pull request went RED for work the agent never did.

My test is a short script in a clean repo:

1. An agent session fixes login on a branch. Both of its checks pass.
2. A teammate edits README.md on main.
3. The branch merges main.
4. CI runs `showwork gate --changed-since <base SHA> --require-tracked`.

0.6.5 said RED: `undeclared change: README.md`.

0.6.6 said GREEN. README.md on the branch has the same bytes as README.md on main, so the gate counts the change as main's and lists the file in a note.

Then the agent edited README.md inside the merge commit. 0.6.6 said RED. Only a file that equals the base byte for byte is excused.

Both versions came from PyPI and ran the same script.

## Why it happened

The gate compares each file with the snapshot from the start of the session. After a merge from main, a file that main changed no longer matches that snapshot, and no claim names it. The gate could not tell main's change from the agent's.

## What changed

- **The gate takes a trusted base.** `gate --base REV` sets it, and `--changed-since` sets it too. A file that changed since the session started but now equals the base counts as the base's change. The gate lists it as a note.
- **Only exact matches count.** An edit by the session, an edit inside the merge, a revert to an older version, and the deletion of a file the base never tracked all stay RED. A base that already contains HEAD is refused.
- **No base, no change.** Without a base, `gate` and `finish` work as before.

## CI

- **Pin the Action to v0.6.6.** `actions/verify` runs the showwork code at its own pin. A workflow pinned to v0.6.5 or older keeps the old behavior after you upgrade the package.
- **`showwork init --ci` writes the new pin.** It used to write a commit from before this fix. If you made your workflow with an older `init --ci`, change its `actions/verify` line by hand.
- **The gate summary is Markdown.** Each session shows its requirements, results, observed revision, exit code and a receipt link. The first line still reads `showwork outcome gate: <verdict>`, and `--json` is unchanged.

## Also new

- `start --ignore GLOB` freezes an exclusion for a file that a background writer changes, such as a dashboard data file.
- `showwork --version` prints the version.
- `host-stop-hook --host codex|claude|cursor` is a read-only Stop hook. It reports, writes nothing and always exits 0. `init --codex` is new, and `init --claude` and `init --cursor` now use this hook. `init --preview` and `init --uninstall` are new.
- `showwork receipts` and the new Python reader read receipts without starting a process.
- A failed command check shows the Python version, the interpreter and the last lines of its output.

## Small things

- The snapshot skips `next-env.d.ts` and `*.tsbuildinfo`, which Next and TypeScript rewrite on every build.
- The pytest plugin keeps one record per run. It marks the latest run as running at start, so a killed run cannot leave an old pass in place.
- `run --keep` and `file_contains` start their time limits after the child process is up. A slow start no longer reads as a failed pattern.
- A second `init --claude` no longer adds a duplicate Stop hook.

## Upgrade

`pip install -U showwork`

GitHub Action: `bmdhodl/showwork/actions/verify@v0.6.6`
