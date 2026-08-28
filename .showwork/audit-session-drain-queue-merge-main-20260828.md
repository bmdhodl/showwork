# Claims audit - session drain-queue-merge-main-20260828

**Verdict: GREEN**  (6/6 verified)

- .. **local main tree matches origin/main after fast-forward to a598ca0** (`None`)
    - retracted: Check shape invalid under the locked check policy: command checks run only python scripts under the root, and glob_count needs op '=='. The claim text was not wrong; the check could never run. Re-claimed with valid checks.
- .. **UTF-8 ledger hardening (#24) is on main; grok/harden-utf8-ledger-decode is superseded** (`None`)
    - retracted: Check shape invalid under the locked check policy: command checks run only python scripts under the root, and glob_count needs op '=='. The claim text was not wrong; the check could never run. Re-claimed with valid checks.
- .. **linked-worktree receipt persistence (#37) is on main; codex/showwork-origin-ledger-20260807 is superseded** (`None`)
    - retracted: Check shape invalid under the locked check policy: command checks run only python scripts under the root, and glob_count needs op '=='. The claim text was not wrong; the check could never run. Re-claimed with valid checks.
- .. **harness-survey citation (#30) is on main; docs/code-as-harness-citation is superseded** (`None`)
    - retracted: Check shape invalid under the locked check policy: command checks run only python scripts under the root, and glob_count needs op '=='. The claim text was not wrong; the check could never run. Re-claimed with valid checks.
- .. **full pytest suite passes on merged main** (`None`)
    - retracted: Check shape invalid under the locked check policy: command checks run only python scripts under the root, and glob_count needs op '=='. The claim text was not wrong; the check could never run. Re-claimed with valid checks.
- .. **stale false day-audit byproduct is out of .showwork** (`None`)
    - retracted: Check shape invalid under the locked check policy: command checks run only python scripts under the root, and glob_count needs op '=='. The claim text was not wrong; the check could never run. Re-claimed with valid checks.
- .. **stale false ruff-cleanup session audit byproduct is out of .showwork** (`None`)
    - retracted: Check shape invalid under the locked check policy: command checks run only python scripts under the root, and glob_count needs op '=='. The claim text was not wrong; the check could never run. Re-claimed with valid checks.
- .. **stale false sanitize-replay session audit byproduct is out of .showwork** (`None`)
    - retracted: Check shape invalid under the locked check policy: command checks run only python scripts under the root, and glob_count needs op '=='. The claim text was not wrong; the check could never run. Re-claimed with valid checks.
- OK **full test suite passes on merged main** (`command`)
    - exit 0
- OK **stale false day-audit byproduct is out of .showwork** (`glob_count`)
    - count 0 == 0
- OK **stale false ruff-cleanup session audit byproduct is out of .showwork** (`glob_count`)
    - count 0 == 0
- OK **stale false sanitize-replay session audit byproduct is out of .showwork** (`glob_count`)
    - count 0 == 0
- OK **drain readout records branch supersession evidence with landed commit hashes** (`file_contains`)
    - /1261aabdf4d7b227aa79e8a6144598a795b283d3/ found in sources/research_20260828_showwork_queue_drain_branch_reconciliation.md
- OK **drain readout records that main was fast-forwarded, not rewritten** (`file_contains`)
    - /fast-forwarded to `a598ca0`/ found in sources/research_20260828_showwork_queue_drain_branch_reconciliation.md
