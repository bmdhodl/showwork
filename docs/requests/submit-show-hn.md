---
created: 2026-09-03 14:30
type: blocked:external
priority: P1
originating_agent: cursor
originating_task: cursor-showwork-stranger-20260903
status: open
last_reviewed: 2026-09-03 14:30
decision_type: content
question: Submit the Show HN draft after 0.4.0 is on PyPI?
recommendation: yes, after publish, not before
default_action: do not submit; the draft stays in docs/launch/show-hn.md
expires: 2026-10-13
blast_radius: medium
decision: pending
---

# Request: Submit Show HN for showwork

## Patrick's words (verbatim)
agent-initiated

## Ask
After 0.4.0 is on PyPI, submit docs/launch/show-hn.md to Hacker News.

## Why
Show HN was drafted 2026-07-15 and never submitted. A stranger cannot install the current tree from PyPI until you publish. Submitting against 0.3.0 would send people to the broken quickstart.

## What the agent tried
- Wrote docs/launch/show-hn.md from repo files and the 2026-09-03 survey numbers.
- Did not submit, star, or comment.

## Unblocker
1. Merge and publish 0.4.0.
2. Confirm `pip install showwork` installs 0.4.0 in a fresh venv.
3. Paste the draft as a Show HN post.

## Resume path
No agent follow-up. The 2026-10-13 gate reads stars, integrations, and inbound issues.
