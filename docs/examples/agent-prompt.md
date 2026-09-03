# Example: Agent prompt for showwork integration

Add this to your project instructions (e.g., `.claude/instructions.md`, `AGENTS.md`,
or your agent harness config):

```text
## Outcome Verification (showwork)

Start material work with:

    showwork start --session <agent>-<task-slug> --agent claude-code
    export SHOWWORK_SESSION=<agent>-<task-slug>

Use a distinct slug per agent (`cursor-fix-nav`, `codex-fix-nav`). Two agents
that share a slug share one ledger file.

After each completed change, record a falsifiable claim with a check that can fail:

    showwork claim --session <agent>-<task-slug> \
      --claim "bumped the API timeout in config" \
      --type file_contains --path config/api.yaml --pattern "timeout: 30"

Prefer git_state or glob_count when they fit. For test runs:

    showwork claim --session <agent>-<task-slug> \
      --claim "tests pass" --type command \
      --command-arg python --command-arg scripts/run_tests.py \
      --expect-exit 0 --stdout-contains passed

Do not claim exact "N passed" counts (they go stale). Check types:
file_exists, file_contains, path_moved, frontmatter, glob_count, command,
http_probe, git_state.

Before reporting success, close through the exit gate:

    showwork finish --session <agent>-<task-slug> --status ok

A clean close needs at least one check-backed claim. If the finish command
refuses (exit 2), fix the failed claim or retract it truthfully:

    showwork retract --session <agent>-<task-slug> --claim "<exact claim text>" --reason "<why>"

NEVER use --no-verify to manufacture a clean result. A bypassed gate is stamped on
the record and CI will reject it.

Operator helpers: `showwork status`, `showwork report [--since YYYY-MM-DD]`.

Commit .showwork/ receipts with your change - the ledger is part of the work.
```

## Claude Code users

If you installed the Stop hook (see `claude-stop-hook.json`), the hook observes
the verdict when the session stops. It does not block - the explicit `finish`
is the gate.
