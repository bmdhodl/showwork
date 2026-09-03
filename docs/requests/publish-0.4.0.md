---
created: 2026-09-03 14:30
type: blocked:decision
priority: P0
originating_agent: cursor
originating_task: cursor-showwork-stranger-20260903
status: open
last_reviewed: 2026-09-03 14:30
decision_type: policy
question: Publish showwork 0.4.0 to PyPI, tag v0.4.0, and cut the GitHub release so PyPI matches the tree?
recommendation: yes
default_action: do nothing; PyPI stays on 0.3.0 and the README keeps stating the gap
expires: 2026-09-10
blast_radius: medium
decision: pending
---

# Request: Publish showwork 0.4.0

## Patrick's words (verbatim)
agent-initiated

## Ask
Publish, tag, and release showwork 0.4.0 so a stranger's `pip install showwork` matches this tree.

## Why
The tree is 0.4.0 / spec-v0.4. PyPI still serves 0.3.0 (2026-07-18). GitHub's last release is v0.2.0. Issue #58 named the gap at 0.3.1. A stranger who pastes the README installs the old package, which has no `__main__`, no undeclared-change check, and a quickstart that refuses on missing files for the wrong reason.

## What the agent tried
- Prepared CHANGELOG Unreleased notes for 0.4.0 / spec-v0.4.
- Did not tag, did not publish, did not touch `.github/workflows/publish.yml`.

## Unblocker
From a clean main after merge:

1. Confirm `pyproject.toml` version is `0.4.0`.
2. Move the Unreleased 0.4.0 notes under `## 0.4.0 - 2026-09-03` if you want the date on the published changelog.
3. Tag `v0.4.0` on the merged commit.
4. Run the owner-gated publish workflow.
5. Create the GitHub release for `v0.4.0`.
6. Close #58 after PyPI shows 0.4.0.

## Resume path
No agent follow-up. Patrick does this himself. After publish, the README line "PyPI still serves 0.3.0" should be deleted in a small follow-up commit.
