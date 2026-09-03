# Claude Code Stop-hook adapter

The explicit `showwork finish` command is the exit gate. It can refuse a clean
close when a claim is false. A Claude Code Stop hook runs after the agent stops,
so it records the verdict but always exits successfully.

## Install the hook

Add this to the project's `.claude/settings.json`:

```json
{
  "hooks": {
    "Stop": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "python -m showwork.cli stop-hook"
          }
        ]
      }
    ]
  }
}
```

Claude Code sends the hook payload on standard input. showwork accepts either
`session_id` or `sessionId`. Prefer binding the Stop hook to the same task
slug you passed to `showwork start`:

```bash
# In the agent shell (or wrapper) before Claude runs:
export SHOWWORK_SESSION=<task-slug>
```

When `SHOWWORK_SESSION` is set, the hook verifies and stamps that session
(`session_bound_from: SHOWWORK_SESSION`). When it is unset, the hook falls
back to the host payload id and stamps `session_unbound: true` so orphan
Claude UUID finishes stay visible in the ledger.

The observed `session.finish` always includes `claims_verdict` and
`claims_unverified`.

## Agent prompt

Add this project instruction:

```text
Start material work with `showwork start --session <id> --agent claude-code`.
Export SHOWWORK_SESSION=<id> in the same shell so the Stop hook binds to it.
After each completed change, record a falsifiable claim with `showwork claim`.
Before reporting success, run `showwork finish --session <id> --status ok`.
If the finish command refuses, fix the failed claim or retract it truthfully.
Never use `--no-verify` to manufacture a clean result.
```

## Manual proof

```bash
export SHOWWORK_SESSION=demo
printf '{"session_id":"host-uuid-ignored-when-env-set"}' | python -m showwork.cli stop-hook
```

The command returns zero even if the verdict is RED. Inspect
`.showwork/sessions/<id>.jsonl` for the durable observed verdict.
