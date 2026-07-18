# Live enforcement on Claude Code

Two hooks. Approval gates on risky actions, and a halt when the agent stops
making progress. Both run as ordinary processes; nothing is hosted.

Add to `.claude/settings.json` in the repo you want guarded:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "*",
        "hooks": [
          { "type": "command", "command": "showwork guard --event pre" }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "*",
        "hooks": [
          { "type": "command", "command": "showwork guard --event post" }
        ]
      }
    ]
  }
}
```

That is the whole install.

## What each does

`--event pre` reads the pending call and returns Claude Code's permission
contract. Six default rules: CI workflow edits, secrets and `.env` files, DB
migrations, force-push and hard reset, recursive force delete, and publishing.
Anything else is allowed.

```json
{"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "ask",
 "permissionDecisionReason": "[showwork:history-rewrite] force-push and hard reset destroy work that is not recoverable"}}
```

`--event post` feeds each completed call to the stuck detector and exits 2 when
the run stops progressing, which halts the loop before the next model call.

```json
{"continue": false, "stopReason": "[showwork:stuck:repeat] mcp__kraken__fetchBalance called with identical input 3 times within the last 3 calls. Halted before further spend."}
```

## Unattended runs

`--behavior deny` refuses outright instead of asking, for nightly jobs where
nobody is there to answer:

```json
{ "type": "command", "command": "showwork guard --event pre --behavior deny" }
```

## Calibration

Defaults come from replaying 2,757 real Claude Code sessions
(`scripts/replay_transcripts.py`). `repeat_threshold=3` flags 0.5% of real
sessions. `no_progress` is **off by default** — at its original threshold of 6
it flagged 82.7%, because reading a dozen files before an edit is ordinary work.

Measure before changing these. Point the replay script at your own transcripts:

```bash
python scripts/replay_transcripts.py --repeat-threshold 3
```

If it flags a large fraction of your sessions, the threshold is wrong for your
workload. A guard that kills real work gets switched off, and a switched-off
guard catches nothing.

## Failure behaviour

The guard fails **open** on its own internal errors: unreadable payload,
corrupt state file, unexpected exception all exit 0 and allow the call. A guard
that crashes the agent it protects is a worse outage than the loop it watched
for. It only ever refuses deliberately — a matched risk rule, or a stuck
verdict.

State lives at `.showwork/guard-state.json` (a PostToolUse hook is a fresh
process per call, so the rolling window has to persist). It is cleared whenever
a run trips, so a killed run starts clean. Safe to delete; safe to gitignore.

## What this does not do

No token or dollar budgets. Claude Code hooks receive no cost data
([claude-code#11008](https://github.com/anthropics/claude-code/issues/11008),
open since 2025-11-04), and Anthropic's gateway and Cloudflare AI Gateway both
enforce spend natively and for free. Use those for dollars. Use this for the
thing they cannot see: whether the agent is still getting anywhere.

For time and tool-call ceilings inside your own code, see `showwork.budgets.RunBudget`.
