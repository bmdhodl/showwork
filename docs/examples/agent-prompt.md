# Example: Agent prompt for showwork integration

Add this to your project instructions (e.g., `.claude/instructions.md`, `AGENTS.md`,
or your agent harness config):

```text
## Outcome Verification (showwork)

Start material work with:

    showwork start --session <task-slug> --agent claude-code

After each completed change, record a falsifiable claim with a check that can fail:

    showwork claim --session <task-slug> \
      --claim "bumped the API timeout in config" \
      --type file_contains --path config/api.yaml --pattern "timeout: 30"

Check types: file_exists, file_contains, path_moved, frontmatter, glob_count, command, http_probe

Before reporting success, close through the exit gate:

    showwork finish --session <task-slug> --status ok

If the finish command refuses (exit 2), fix the failed claim or retract it truthfully:

    showwork retract --session <task-slug> --claim "<exact claim text>" --reason "<why>"

NEVER use --no-verify to manufacture a clean result. A bypassed gate is stamped on
the record and CI will reject it.

Commit .showwork/ receipts with your change - the ledger is part of the work.
```

## Claude Code users

If you installed the Stop hook (see `claude-stop-hook.json`), the hook observes
the verdict when the session stops. It does not block - the explicit `finish`
is the gate.
