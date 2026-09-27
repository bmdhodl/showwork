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
`session_id` or `sessionId`. The hook binds to a session in this order:

1. `SHOWWORK_SESSION`, when it is set in the environment Claude Code started
   with (`session_bound_from: SHOWWORK_SESSION`). An `export` inside a Bash
   tool call does not reach the hook.
2. The latest session that `showwork start` opened from this Claude Code
   session, while no explicit `showwork finish` has closed it
   (`session_bound_from: host_session`). `start` records Claude Code's
   `CLAUDE_CODE_SESSION_ID` as `host_session`; the Stop payload carries the
   same id.
3. Otherwise the host payload id, stamped `session_unbound: true` so orphan
   Claude UUID finishes stay visible in the ledger.

The observed `session.finish` always includes `claims_verdict` and
`claims_unverified`.

## Agent prompt

Add this project instruction:

```text
Start material work with `showwork start --session <id> --agent claude-code`.
The Stop hook binds to that session until `showwork finish` closes it.
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
