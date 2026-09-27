# Claims audit - session claude-code-stop-hook-bind-active

**Check verdict: RED**  (10/11 checks passed)

**Outcome: UNVERIFIED**. Some acceptance checks or session checks did not pass.

Claim descriptions are author supplied. Results establish only the stated check.

- OK Check for claim: **stop hook binds by host session** (`file_contains`)
    - /def open_session_for_host/ found in src/showwork/hooks.py
- .. Check for claim: **start passes the host session id** (`None`)
    - retracted: host id now comes from _host_session(), shared by start and run (Codex P2)
- OK Check for claim: **session.start records host_session** (`file_contains`)
    - /host_session=host_session/ found in src/showwork/ledger.py
- OK Check for claim: **tests cover other-host isolation** (`file_contains`)
    - /def test_stop_hook_ignores_other_hosts_open_session/ found in tests/test_hooks.py
- OK Check for claim: **SPEC states host-session binding** (`file_contains`)
    - /session_bound_from: host_session/ found in SPEC.md
- OK Check for claim: **Claude Code doc explains host binding** (`file_contains`)
    - /CLAUDE_CODE_SESSION_ID/ found in docs/claude-code.md
- .. Check for claim: **AGENTS.md drops the export advice** (`None`)
    - retracted: regex used a line anchor the checker does not apply per line; replaced with a literal match
- OK Check for claim: **agent prompt drops the export line** (`file_contains`)
    - /binds to the session started from the same Claude Code/ found in docs/examples/agent-prompt.md
- OK Check for claim: **AGENTS.md says an export inside a tool call does not reach the hook** (`file_contains`)
    - /inside a tool call does not reach it/ found in AGENTS.md
- OK Check for claim: **start and run both pass the host session id** (`command`)
    - exit 0, stdout has 'passed'
- XX Check for claim: **run records host_session** (`file_contains`, RED)
    - /host_session=_host_session\(\)\)\s*$/ NOT in src/showwork/cli.py
- OK Check for claim: **same-second host starts bind nothing** (`file_contains`)
    - /def test_stop_hook_same_second_host_starts_bind_nothing/ found in tests/test_hooks.py
- OK Check for claim: **stop-hook binds to the open latest-started session when SHOWWORK_SESSION is unset, and falls back to unbound after an explicit finish or a tied start (tests/test_hooks.py fails without the fix)** (`command`)
    - exit 0, stdout has 'passed'

## 1 gap(s) - a claimed 'done' is not real

- [RED/fail] run records host_session - /host_session=_host_session\(\)\)\s*$/ NOT in src/showwork/cli.py

## Explanation

Observation: current_rerun. Historical finish: absent.
Check verdict: RED. Outcome: UNVERIFIED. Integrity: unknown.
Limitations: undeclared requirements: unknown; test adequacy: not assessed; formatting does not change the verdict.
Recovery: Repair the failed check, then rerun verify. This text does not authorize a merge or a clean close.
  requirement:absent check:file_contains scope:individual_check result:pass evidence:claim:0 revision:absent
       /def open_session_for_host/ found in src/showwork/hooks.py
  requirement:absent check:absent scope:individual_check result:skipped evidence:claim:1 revision:absent
       retracted: host id now comes from _host_session(), shared by start and run (Codex P2)
  requirement:absent check:file_contains scope:individual_check result:pass evidence:claim:2 revision:absent
       /host_session=host_session/ found in src/showwork/ledger.py
  requirement:absent check:file_contains scope:individual_check result:pass evidence:claim:3 revision:absent
       /def test_stop_hook_ignores_other_hosts_open_session/ found in tests/test_hooks.py
  requirement:absent check:file_contains scope:individual_check result:pass evidence:claim:4 revision:absent
       /session_bound_from: host_session/ found in SPEC.md
  requirement:absent check:file_contains scope:individual_check result:pass evidence:claim:5 revision:absent
       /CLAUDE_CODE_SESSION_ID/ found in docs/claude-code.md
  requirement:absent check:absent scope:individual_check result:skipped evidence:claim:6 revision:absent
       retracted: regex used a line anchor the checker does not apply per line; replaced with a literal match
  requirement:absent check:file_contains scope:individual_check result:pass evidence:claim:7 revision:absent
       /binds to the session started from the same Claude Code/ found in docs/examples/agent-prompt.md
  requirement:absent check:file_contains scope:individual_check result:pass evidence:claim:8 revision:absent
       /inside a tool call does not reach it/ found in AGENTS.md
  requirement:absent check:command scope:individual_check result:pass evidence:claim:9 revision:absent
       exit 0, stdout has 'passed'
  requirement:absent check:file_contains scope:individual_check result:fail evidence:claim:10 revision:absent
       /host_session=_host_session\(\)\)\s*$/ NOT in src/showwork/cli.py
  requirement:absent check:file_contains scope:individual_check result:pass evidence:claim:11 revision:absent
       /def test_stop_hook_same_second_host_starts_bind_nothing/ found in tests/test_hooks.py
  requirement:stop-hook binds to the open latest-started session when SHOWWORK_SESSION is unset, and falls back to unbound after an explicit finish or a tied start (tests/test_hooks.py fails without the fix) check:command scope:behavior result:pass evidence:requirement:regression revision:5ca8e11fd8c9
       exit 0, stdout has 'passed'
