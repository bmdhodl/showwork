# Adopting showwork across a fleet of repos

How to roll showwork out when multiple repositories each run their own AI agent
sessions (nightly workers, queue sweeps, interactive coding agents) and you want
every repo's PRs to carry receipts. This is the pattern we used on our own
fleet; adapt freely.

## The target state, per repo

1. **The package is importable** in every environment agents run in (developer
   machine, CI runner, sandbox image): `pip install showwork`.
2. **A Stop-hook records verdicts** (`.claude/settings.json` for Claude Code —
   see [claude-code.md](claude-code.md)). Observe-only; it never blocks.
3. **The agent contract is in the repo's agent instructions** (AGENTS.md /
   CLAUDE.md): start → falsifiable claim per completed change → gated
   `finish --status ok` before reporting success. REFUSED means fix reality or
   retract truthfully; `--no-verify` is prohibited.
4. **`.showwork/` is committed with the work.** The receipt ships inside the
   PR, so reviewers see proof, not prose. The ledger is append-only.

## Rollout order that worked

- **One repo per day/night.** Small blast radius; each repo's wiring is its own
  reviewable PR whose diff is config + docs + the genesis receipt only.
- **Genesis receipt as the smoke test.** Have the wiring session verify itself:
  claim the hook file exists, claim the docs section landed, close through the
  gate. If `finish` returns GREEN, the wiring works — by construction.
- **Prove the hook separately:** `printf '{"session_id":"<sid>"}' | python -m
  showwork.cli stop-hook`, then check `.showwork/sessions.jsonl` for the
  durable verdict.

## Pitfalls we hit (check these first)

- **`.claude/` is often gitignored.** Your hook file will silently not ship.
  Add an explicit negation (`/.claude/*` + `!/.claude/settings.json`) so shared
  settings commit while `settings.local.json` stays local. Verify with
  `git status` that the hook file actually staged.
- **`python` vs `python3`.** Debian/Ubuntu images ship `python3` only; a hook
  command using `python` fails *silently* (hooks never block). Install
  `python-is-python3` or adjust the command. Detection: no
  `"observed_by": "stop-hook"` events appearing in `.showwork/sessions.jsonl`.
- **Working trees you must not disturb** (long-lived feature branches, crash
  recovery, running daemons): wire the repo through `git worktree add` off the
  default branch instead of switching branches in the live checkout.
- **Default branches differ** across old repos (`master` vs `main`); pass the
  base explicitly when scripting PR creation.

## What NOT to do

- Don't gitignore `.showwork/`. A receipt that never ships is prose.
- Don't rewrite ledger history to "clean it up". Corrections are retraction
  records; a messy-but-honest ledger is the point.
- Don't wire verification into runtime-critical paths (trading, deploys,
  medical anything). showwork is session bookkeeping; a claims verdict is
  evidence for humans and CI, not a control signal.
- Don't let agents close with `--no-verify` "just this once". That single
  bypass converts every future GREEN into a maybe. The bypass is stamped on the
  record for a reason.

## After adoption: make the receipts earn rent

- **CI gate:** a step that runs `showwork verify --session <id>` and fails RED
  turns the receipt into an enforced contract.
- **Harvest honestly.** Count sessions closed, GREEN vs RED verdicts, and every
  REFUSED with its false claim and fix. If the gate never refused anything,
  that's your report. Fabricated case studies are the exact failure mode this
  tool exists to end.
