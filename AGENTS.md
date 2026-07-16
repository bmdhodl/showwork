# Agent Instructions — showwork

showwork is outcome verification for AI agents: falsifiable claims, deterministic
verification, an exit gate that refuses a false "done." Read `README.md` for the
model and `SPEC.md` for the ledger format before changing anything.

## Ground rules

- **Tests are the gate.** `python -m pytest tests/ -q` must be green before any
  commit. No exceptions. (If pytest crashes on a temp-dir permission error,
  pass `--basetemp` pointing at a fresh directory — do not skip the suite.)
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

1. Start material work: `python -m showwork.cli start --session <task-slug> --agent <claude-code|codex|gemini>`
2. After each completed change, record a claim with a check that can fail
   (types: `file_exists`, `file_contains`, `path_moved`, `frontmatter`,
   `glob_count`, `command`):
   `python -m showwork.cli claim --session <task-slug> --claim "<what changed>" --type file_contains --path <file> --pattern "<regex>"`
3. Before reporting success: `python -m showwork.cli finish --session <task-slug> --status ok`
   - REFUSED (exit 2) means a claimed "done" is not backed by reality. Fix the
     gap or retract the claim truthfully (`retract`), then finish again. NEVER
     pass `--no-verify` to manufacture a clean close; if genuinely stuck,
     `finish --status blocked`.
4. `git add .showwork/` and commit the ledger with your change — the receipt is
   part of the work. Do not gitignore it. The ledger is append-only; never
   rewrite history in it.
5. The Stop hook in `.claude/settings.json` records a claims verdict when a
   session stops. It observes; it never blocks. The explicit `finish` is the gate.

Rolling this pattern out across multiple repos: see `docs/fleet-adoption.md`.
