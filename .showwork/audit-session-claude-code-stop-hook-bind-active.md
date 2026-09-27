# Claims audit - session claude-code-stop-hook-bind-active

**Check verdict: RED**  (8/9 checks passed)

**Outcome: UNVERIFIED**. Some acceptance checks or session checks did not pass.

Claim descriptions are author supplied. Results establish only the stated check.

- OK Check for claim: **stop hook binds by host session** (`file_contains`)
    - /def open_session_for_host/ found in src/showwork/hooks.py
- OK Check for claim: **start passes the host session id** (`file_contains`)
    - /host_session=os.environ.get\(HOST_SESSION_ENV/ found in src/showwork/cli.py
- OK Check for claim: **session.start records host_session** (`file_contains`)
    - /host_session=host_session/ found in src/showwork/ledger.py
- OK Check for claim: **tests cover other-host isolation** (`file_contains`)
    - /def test_stop_hook_ignores_other_hosts_open_session/ found in tests/test_hooks.py
- OK Check for claim: **SPEC states host-session binding** (`file_contains`)
    - /session_bound_from: host_session/ found in SPEC.md
- OK Check for claim: **Claude Code doc explains host binding** (`file_contains`)
    - /CLAUDE_CODE_SESSION_ID/ found in docs/claude-code.md
- XX Check for claim: **AGENTS.md drops the export advice** (`file_contains`, RED)
    - /an .export.\s*$/ NOT in AGENTS.md
- OK Check for claim: **agent prompt drops the export line** (`file_contains`)
    - /binds to the session started from the same Claude Code/ found in docs/examples/agent-prompt.md
- OK Check for claim: **stop-hook binds to the open latest-started session when SHOWWORK_SESSION is unset, and falls back to unbound after an explicit finish or a tied start (tests/test_hooks.py fails without the fix)** (`command`)
    - exit 0, stdout has 'passed'

## 1 gap(s) - a claimed 'done' is not real

- [RED/fail] AGENTS.md drops the export advice - /an .export.\s*$/ NOT in AGENTS.md

## Explanation

Observation: current_rerun. Historical finish: absent.
Check verdict: RED. Outcome: UNVERIFIED. Integrity: unknown.
Limitations: undeclared requirements: unknown; test adequacy: not assessed; formatting does not change the verdict.
Recovery: Repair the failed check, then rerun verify. This text does not authorize a merge or a clean close.
  requirement:absent check:file_contains scope:individual_check result:pass evidence:claim:0 revision:absent
       /def open_session_for_host/ found in src/showwork/hooks.py
  requirement:absent check:file_contains scope:individual_check result:pass evidence:claim:1 revision:absent
       /host_session=os.environ.get\(HOST_SESSION_ENV/ found in src/showwork/cli.py
  requirement:absent check:file_contains scope:individual_check result:pass evidence:claim:2 revision:absent
       /host_session=host_session/ found in src/showwork/ledger.py
  requirement:absent check:file_contains scope:individual_check result:pass evidence:claim:3 revision:absent
       /def test_stop_hook_ignores_other_hosts_open_session/ found in tests/test_hooks.py
  requirement:absent check:file_contains scope:individual_check result:pass evidence:claim:4 revision:absent
       /session_bound_from: host_session/ found in SPEC.md
  requirement:absent check:file_contains scope:individual_check result:pass evidence:claim:5 revision:absent
       /CLAUDE_CODE_SESSION_ID/ found in docs/claude-code.md
  requirement:absent check:file_contains scope:individual_check result:fail evidence:claim:6 revision:absent
       /an .export.\s*$/ NOT in AGENTS.md
  requirement:absent check:file_contains scope:individual_check result:pass evidence:claim:7 revision:absent
       /binds to the session started from the same Claude Code/ found in docs/examples/agent-prompt.md
  requirement:stop-hook binds to the open latest-started session when SHOWWORK_SESSION is unset, and falls back to unbound after an explicit finish or a tied start (tests/test_hooks.py fails without the fix) check:command scope:behavior result:pass evidence:requirement:regression revision:a6374c4af74f
       exit 0, stdout has 'passed'
