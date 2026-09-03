# Adapters: wiring showwork into any harness

The ledger is the interface. Anything that can run a CLI can record claims
and close through the gate — the adapters below are just lifecycle glue.

## Cursor

`showwork init --cursor` writes `.cursor/rules/showwork.mdc`. The rule tells
the agent to start a session, record claims, and close through `finish`.
Walk: [walks/cursor.md](walks/cursor.md).

## pytest

If pytest is installed, `pip install showwork` registers a plugin. It is
silent unless you pass `--showwork-session`. Then a passing run records a
`file_contains` claim on `.showwork/pytest-last.json`.

```bash
pytest -q --showwork-session cursor-fix-nav
```

## Claude Code

Stop-hook + prompt contract: see [claude-code.md](claude-code.md).

## The universal wrapper: `showwork run`

No harness integration at all — wrap the agent process itself:

```bash
showwork run --session nightly-fix --agent codex -- codex exec "fix the failing test"
```

`run` records `session.start`, executes the command with `SHOWWORK_SESSION`
and `SHOWWORK_ROOT` exported (so anything inside can record claims without
plumbing), then records `session.finish` with the claims verdict and the
command's exit code stamped (`observed_by: run-wrapper`).

- **Observe mode (default):** the wrapper is transparent — it exits with the
  wrapped command's own exit code and simply records the verdict.
- **Gate mode (`--gate`):** exit 2 when the command *claims success* (exit 0)
  but this session's claims are RED. "The agent said done and the receipts
  disagree" becomes a nonzero exit any orchestrator can act on.

## Codex CLI

Two options, in order of preference:

1. Wrap the invocation: `showwork run --session <task> --agent codex -- codex exec ...`
2. Prompt contract only: add the Outcome Verification block (see any fleet
   repo's AGENTS.md) to the project's instructions; Codex records claims and
   runs `finish` itself. Codex-side hooks can additionally call
   `showwork stop-hook` with `{"session_id": "<id>"}` on stdin.

## Gemini CLI

Same shape: `showwork run --session <task> --agent gemini -- gemini ...`, or
the prompt contract if the harness executes shell commands. The stop-hook
adapter accepts any JSON payload carrying `session_id`/`sessionId`.

## BMD desktop (read-only supervisor)

BMD is a cockpit. It must not write the bmd-desktop git ledger. Receipts live
in the **user workspace**. The sidecar imports `showwork.receipts`:

- `overlay_record(run, workspace)` joins `task_id` to `bmd-<task_id>`.
- Missing `.showwork/` is `unknown` ("No receipts yet."), never green.
- Prose-only close is `claimed`. Failed checks are `failed`. Check-backed
  GREEN is `verified`.
- `agent_environ` / `agent_prompt_block` set `SHOWWORK_SESSION` and
  `SHOWWORK_ROOT` for a dispatched Claude/Codex child. Observe mode. No
  `--gate` on the first slice.
- `showwork receipts --json|--html` is the same overlay from the CLI.

Copy-paste for the private BMD repo: [examples/bmd/README.md](../examples/bmd/README.md).
Do not add `.showwork/` to `bmdhodl/bmd-desktop`.

## Reading the ledger from JavaScript

[`js/showwork-audit`](../js/showwork-audit/) is a zero-dependency Node
implementation of the spec-v0.4 **reading half**: it parses ledgers, verifies
the integrity chain, and reports verdicts (`node js/showwork-audit/index.mjs
<root>`, exit 0/3/2). It re-executes no checks — what it does not verify it
reports, never skips. Both implementations are held to the same frozen
fixtures (`tests/fixtures/chain/`); if they ever disagree on a verdict, that
is a conformance bug, not an opinion.

## Writing your own adapter

An adapter needs exactly three behaviors (SPEC.md is the contract):

1. Record `session.start` when material work begins.
2. Append falsifiable claims as outcomes land (each with a check that can
   fail — prose is recorded but never counts as proof).
3. Close through the exit gate before reporting success, and never bypass it
   to make a result look clean; the bypass stamp is durable and CI reads it.
