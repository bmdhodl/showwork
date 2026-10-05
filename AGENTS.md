# Agent Instructions — showwork

showwork is outcome verification for AI agents: falsifiable claims, deterministic
checks, and an exit gate for declared acceptance requirements. It cannot judge
whether those requirements cover the user's request. Read `README.md` for the
model and `SPEC.md` for the ledger format before changing anything.

## Ground rules

- **Tests are the gate.** `python scripts/run_tests.py` must be green before any
  commit. No exceptions. It runs `pytest tests/ -q` in a fresh system temp dir.
  If you run pytest directly, pass `--basetemp=.showwork/pytest-tmp/<slug>`.
  Keep temp dirs under that folder, because step 5 commits the rest of
  `.showwork/`. Do not skip the suite.
- **UI changes need the browser check.** After a change to the rendered
  receipts, run `python scripts/check_receipts_ui.py` (needs
  `requirements-ui.txt`). CI runs it too.
- **Zero dependencies is a feature.** stdlib only. Do not add runtime deps.
- **Publishing is owner-gated.** Never publish to PyPI, tag a release, or
  change repo visibility. Those steps belong to the owner.
- **SPEC.md is a contract.** Ledger-format changes require a spec update in the
  same commit and are breaking until v1 — treat them as last resort.

## Outcome Verification (showwork) — this repo eats its own dog food

Every agent session that changes this repo records falsifiable claims **with
the version of showwork in `src/`** and closes through the exit gate. Receipts
live in `.showwork/` and ship with the commit. If your change breaks the tool,
your own exit gate is the first thing that will tell you.

1. Start material work: `python -m showwork.cli start --session <agent>-<task-slug> --agent <claude-code|codex|gemini|cursor>`
   The Claude Stop hook binds to the session you started from the same Claude
   Code session until you finish it. `SHOWWORK_SESSION` overrides that only
   when set in the environment the agent host started with; an `export`
   inside a tool call does not reach it.
   Distinct slugs write distinct files under `.showwork/sessions/` and `.showwork/claims/`.
2. Before recording completion claims, declare acceptance requirements. A behavior
   requirement needs a Python test of the actual changed path, including a case
   that fails when the behavior is broken:
   `python -m showwork.cli require --session <slug> --id regression --scope behavior --description "<tested behavior>" --type command --command-arg python --command-arg scripts/run_tests.py --expect-exit 0 --stdout-contains passed`
   Use artifact scope only for artifact observations. Never use a text match on
   a handwritten summary to certify tests, behavior, or a video encoding.
   After each completed change, record a claim with a check that can fail
   (types: `file_exists`, `file_contains`, `path_moved`, `frontmatter`,
   `glob_count`, `command`, `http_probe`, `git_state`):
   `python -m showwork.cli claim --session <agent>-<task-slug> --claim "<what changed>" --type file_contains --path <file> --pattern "<regex>"`
   Prefer `git_state` / `glob_count` when they fit. For tests use
   `command` with `scripts/run_tests.py`, `expect_exit=0`, and
   `stdout_contains=passed` — not exact `"N passed"` counts. Invalid check
   shapes are rejected at claim time.
3. Before reporting success: `SHOWWORK_COMMAND_TIMEOUT_SECONDS=1800 python -m showwork.cli finish --session <agent>-<task-slug> --status ok`
   - `finish` reruns the `regression` command, and the full suite takes
     several minutes. Without the variable, the 120 s default stops the
     suite and the check fails. 1800 is the limit in seconds (maximum 3600).
   - REFUSED (exit 2) means a claimed "done" is not backed by reality, or the
     session has no check-backed claims. Fix the gap or retract the claim
     truthfully (`retract`), then finish again. NEVER pass `--no-verify` to
     manufacture a clean close; if genuinely stuck, `finish --status blocked`.
4. Operator helpers: `showwork status [--session S]` and
   `showwork report [--since YYYY-MM-DD] [--exclude-campaign]`.
5. `git add .showwork/` and commit the ledger with your change — the receipt is
   part of the work. Do not gitignore it. The ledger is append-only; never
   rewrite history in it. Run
   `SHOWWORK_COMMAND_TIMEOUT_SECONDS=1800 showwork gate --session <slug> --require-tracked`
   against the committed tree. The gate also reruns the suite, so it needs the
   same limit as `finish`. If you merged `main` after `start`, run
   `git fetch origin` and add `--base origin/main` to the gate. If you then
   finish again (for example after you add a claim), add the same
   `--base origin/main` to `finish`. Both then excuse files that equal
   `origin/main` exactly; an edit of your own or inside the merge stays RED.
   Do not add a claim for each file `main` changed. Check the required GitHub
   receipt job too.
6. The Stop hook in `.claude/settings.json` records a claims verdict when a
   session stops. It observes; it never blocks. The explicit `finish` is the gate.

Rolling this pattern out across multiple repos: see `docs/fleet-adoption.md`.
