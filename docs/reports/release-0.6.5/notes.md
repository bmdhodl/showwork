---
title: showwork 0.6.5
excerpt: Your AI agent broke the fix. Did anything notice?
---

showwork 0.6.5 is on PyPI.

## The fix

An AI coding agent can break its own work and keep going as if nothing happened. showwork exists to catch that. You tell it what done looks like: this file must exist, this test must pass. The agent cannot call the work done while a check fails.

In Claude Code, showwork also checks the work after every step and keeps a running score. In 0.6.4 that score had a blind spot. It could stay on all good after the work broke.

My test:

1. Give an agent one task with one check: the fix file must exist.
2. Let it run for twenty steps.
3. Halfway through, delete the fix file.

0.6.4 said all good after every one of the twenty steps. The file was gone for the last seven.

0.6.5 caught it at the next check and marked the task as broken.

Both versions came from PyPI and ran in clean folders.

## Why it happened

The running score in Claude Code was going to the wrong place. It went under Claude's own session ID instead of under your task. That ID had no checks attached, so it could never fail. Your task got no score at all.

The only way around it was to set `SHOWWORK_SESSION` before you launched Claude Code. The docs told you to `export` it from inside the agent. That never worked, and that advice is gone.

## What changed

- **The score goes to your task.** `showwork start` now remembers which Claude Code session it ran in. After each step, showwork finds your open task from that session and scores it there.
- **Less noise.** showwork used to write the same score after every step. Now it writes only when the score changes. Twenty quiet steps give one line, and a failure stands out.
- **No guessing.** showwork uses only the latest task you started in this Claude Code session, and only until `finish` closes it. It ignores tasks from other sessions.

## CI

- **No more fake deletions in pull requests.** If other PRs added receipts to main after you branched, the receipt check counted them as files your PR deleted. It now compares against the point where your branch left main. A real deletion still fails.
- **The receipt check reads your branch as you pushed it,** not the merged result.
- **The GitHub Action has a warn-only mode.** It reports problems and keeps the build green. Blocking stays the default. The showwork repo runs its own receipt job in warn-only mode. Its tests still block.

## Small things

- Each test run gets its own temp folder and cleans it up.
- The CI docs had examples that disagreed with each other. They now show one setup and the steps to recover from a bad run.

## Upgrade

`pip install -U showwork`

The `finish` command, which blocks a false done, works the same as in 0.6.4.
