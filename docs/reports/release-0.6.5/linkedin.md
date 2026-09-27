---
title: showwork 0.6.5
excerpt: Your AI agent broke the fix. Did anything notice?
---

An AI coding agent can break its own work and keep going as if nothing happened.

That is the problem showwork exists for. You tell it what done looks like: this file must exist, this test must pass. showwork checks. The agent cannot call the work done while a check fails.

showwork 0.6.5 fixes a blind spot in Claude Code. While the agent works, showwork checks the work after every step and keeps a running score. In older versions, that score was stuck on all good. It stayed on all good after the work broke.

My test: I gave an agent a task with one check. The fix file must exist. Halfway through, I deleted that file.

0.6.4 said all good. Twenty steps in a row. The file was gone for the last seven.

0.6.5 caught it at the next check and marked the task as broken.

If you run showwork with Claude Code, upgrade.

pip install -U showwork

github.com/bmdhodl/showwork
