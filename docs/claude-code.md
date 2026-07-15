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
`session_id` or `sessionId`, verifies that session's claims, and appends a
`session.finish` event containing `claims_verdict` and `claims_unverified`.

## Agent prompt

Add this project instruction:

```text
Start material work with `showwork start --session <id> --agent claude-code`.
After each completed change, record a falsifiable claim with `showwork claim`.
Before reporting success, run `showwork finish --session <id> --status ok`.
If the finish command refuses, fix the failed claim or retract it truthfully.
Never use `--no-verify` to manufacture a clean result.
```

## Manual proof

```bash
printf '{"session_id":"demo"}' | python -m showwork.cli stop-hook
```

The command returns zero even if the verdict is RED. Inspect
`.showwork/sessions.jsonl` for the durable observed verdict.
