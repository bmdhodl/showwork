# showwork Architecture

How the pieces actually fit. `README.md` is the pitch, `SPEC.md` is the
portable format contract, this file is the map of the implementation. When
this file and the spec disagree, the spec wins.

Scope: the Python reference package under `src/showwork/`, the Node reader
under `js/showwork-audit/`, the CI action under `actions/verify/`, and the
support scripts under `scripts/`.

## The model in one pass

An agent asserts it did something. showwork makes that assertion falsifiable,
then falsifies it or does not.

```
agent work
   |
   v
showwork start   ->  session.start event          .showwork/sessions.jsonl
   |
   v
showwork claim   ->  claim record + check spec    .showwork/claims-YYYY-MM-DD.jsonl
   |
   v
showwork verify  ->  run each check against the filesystem
   |                 -> GREEN / YELLOW / RED
   v
showwork finish  ->  verify this session's own claims first.
                     RED means the close is REFUSED (exit 2).
```

Every appended record carries the SHA-256 of an earlier record line, so the
file can prove it was only appended to. `showwork audit` walks that chain.

Three rules drive every design decision below:

1. A claim without a `check` is recorded but never counts as proof.
2. No model evaluates the record. Every checker is deterministic and
   re-executable by someone who does not trust the writer.
3. The gate refuses instead of warning.

## Module map

| File | Role |
|---|---|
| `src/showwork/ledger.py` | Append-only storage, record framing, hash chain writes, session lifecycle, the `finish` gate |
| `src/showwork/checks.py` | The six deterministic checkers, the verification driver, verdict algebra, retraction resolution |
| `src/showwork/audit.py` | Reads the hash chain back and proves append-only, including fork handling |
| `src/showwork/cli.py` | Argument parsing and the ten subcommands; exit codes |
| `src/showwork/hooks.py` | Stop-hook adapter. Observes, never gates |
| `src/showwork/control.py` | PreToolUse approval rules, PostToolUse payload plumbing, Claude Code hook JSON |
| `src/showwork/guards.py` | `StuckDetector`: repeat / alternation / no-progress signatures |
| `src/showwork/budgets.py` | `RunBudget`: wall clock, tool-call count, per-tool rate. Library only |
| `src/showwork/dashboard.py` | Static HTML render of replay data |
| `js/showwork-audit/index.mjs` | Zero-dependency Node implementation of the reading half of the spec |
| `actions/verify/action.yml` | Composite GitHub Action that gates a job on receipts |

`src/showwork/__init__.py` re-exports the public Python API and pins
`__version__ = "0.3.0"`, matching `pyproject.toml`.

## Data model

### Where it lives

`ledger_dir(root)` is always `<root>/.showwork/` (`ledger.py`). The root is
resolved once per invocation by `resolve_root()`, in this order: the `--root`
flag, then `$SHOWWORK_ROOT`, then the current working directory.

```text
.showwork/
  claims-YYYY-MM-DD.jsonl   one claim or retraction per line
  sessions.jsonl            session.start / session.finish events
  audit-<label>.md          human-readable report written by `verify`
  guard-state.json          rolling tool-call window for the post-tool guard
```

Day files are the only sharding. `claims_path()` rejects any date that is not
`YYYY-MM-DD` and then re-checks that the resolved path stays inside
`.showwork/`, because a hostile `--date` was otherwise a path escape.

`_audit_report_path()` in `cli.py` does the same job for report labels: session
ids reach it as attacker-controlled strings, so separators, colons, nulls and
`..` are collapsed before the join and containment is asserted after it.

### Claim record

```json
{"session":"deploy-fix","ts":"2026-07-10T14:30:00","claim":"config has the new timeout",
 "severity":"RED","artifact":"config/api.yaml",
 "check":{"type":"file_contains","path":"config/api.yaml","pattern":"timeout: 30"},
 "prev":"<sha256 of the previous record line>"}
```

`check` is optional. A claim without one is prose: it stays in the record and
shows as `skipped`, and it can never move the verdict. `artifact` is optional
metadata. `severity` is `RED` or `YELLOW`; `verify_claim()` coerces anything
else (empty, `GREEN`, a typo) back to `RED` so a bad severity cannot demote a
failing claim out of the gate.

### Retraction record

History is never edited. A correction is a new record that points at the old
one.

```json
{"session":"deploy-fix","ts":"...","retracted":true,
 "retracts":{"session":"deploy-fix","claim":"the configuration changed"},
 "retraction_reason":"the write failed"}
```

`apply_append_retractions()` in `checks.py` resolves these in file order, and
the ordering rule matters: a retraction suppresses only targets that appear
*before* it. Re-claiming the same session and claim text afterwards is a new
live claim, not something an old retraction kills forever. The referencing
records themselves are bookkeeping and are dropped from the listed claims by
`evaluate_records()`.

### Session event

```json
{"event":"session.start","session":"deploy-fix","ts":"...","agent":"claude-code"}
{"event":"session.finish","session":"deploy-fix","ts":"...","status":"ok","claims_verdict":"GREEN"}
{"event":"session.finish.refused","session":"deploy-fix","ts":"...","status":"ok","claims_verdict":"RED"}
```

`session.finish.refused` is the durable trace of a blocked close. It is also
the primary input to the False Done Rate measurement in
`scripts/false_done_rate.py`. A bypass writes `verify_bypassed: true` on the
finish event, and CI reads that field.

### The integrity chain

`_append()` computes `prev` at write time from the current last record line and
sets it on the record before serializing. Two helpers define the anchor:

- `line_hash(line)` is SHA-256 over `line.strip()`. Stripping is deliberate.
  A checkout or an editor that rewrites line endings must not break the chain,
  while any content change must.
- `genesis_hash(path)` is SHA-256 over `showwork:genesis:<filename>`, the
  anchor for the first record in a file.

`audit_file()` in `audit.py` walks the file and keeps three structures:

- `seen`: the genesis anchor plus the hash of every record line already read.
- `referenced`: every hash used as some record's `prev`.
- `record_hashes`: the hash of each record line, in file order.

A record's `prev` is valid when it is in `seen`. That is wider than "the
immediate predecessor" on purpose:

| Condition | Result |
|---|---|
| `prev` equals the immediate predecessor's hash | Linear step |
| `prev` is in `seen` but not the predecessor | Fork, counted, still GREEN |
| `prev` matches no earlier line | RED, reported at the exact line |
| No `prev` at all, after the chain started | RED, append-only is no longer provable |
| No `prev`, before any chained record | Pre-chain record, counted, file stays YELLOW until a chained append anchors it |

Forks are what a legitimate concurrent merge looks like. Two agents appending
in separate git worktrees, then merged with `merge=union` (this repo sets that
in `.gitattributes`), produce two blocks chaining off the same parent. Tamper
detection survives it: modification, deletion and reorder all still produce a
`prev` that matches no earlier line. `--strict` turns any fork RED for repos
that forbid concurrency.

`head` is the hash of the last record line. `heads` is every record hash that
nothing else anchored to, which is one per branch. Publishing a head anywhere
out of band anchors the history behind it, which is the only defense against
deleting a whole branch tip.

### Framing and JSON dialect

Three readers (Python verify, Python audit, the Node auditor) must agree
byte-for-byte on where one record ends. So the segmentation rule lives in
`ledger.py` and nowhere else.

- `read_record_text()` reads bytes and decodes `utf-8-sig`. It does not use
  `Path.read_text`, which opens in universal-newline mode and folds a lone CR
  into `\n` before any split runs. The Node side reads raw and never
  translates, so translating here would silently desynchronize the two.
- `split_record_lines()` splits on `\r?\n` only. Not `str.splitlines()`, which
  also breaks on U+2028, U+2029, U+0085, VT, FF and the FS/GS/RS/US controls.
  A `JSON.parse` reader treats none of those as boundaries, so splitting on
  them would cut a JSON string that legitimately contains one and the two
  implementations would disagree on record counts and head hashes.
- `strict_json_loads()` rejects the bare tokens `NaN`, `Infinity` and
  `-Infinity` via `parse_constant`. They are not valid JSON and `JSON.parse`
  rejects them, so both sides treat such a line as a parse error.

A parse error never disappears. `_read_jsonl()` turns an unparseable line into
a YELLOW pseudo-record carrying `_parse_error`, and invalid UTF-8 turns the
whole file into one YELLOW record instead of raising.

## Check types

All six live in `checks.py` and are registered in the `CHECKERS` dict. Each
returns `(status, detail)` where status is `pass`, `fail`, or `error`.

`error` is not a synonym for `fail`. A failed check means the claim is false. A
checker error means the claim could not be evaluated, which blocks GREEN but is
not proof of a lie.

### Shared confinement

`_resolve(root, path_str)` guards every path-taking checker. A non-string or
empty path raises `PathArgError` (reported as `error`). A path that resolves
outside the project root raises `PathEscapeError` (reported as `fail`, since a
claim reaching outside the root is a bad claim, not an unevaluable one).

### The six

| Type | Fields | Passes when |
|---|---|---|
| `file_exists` | `path` | `path` is a regular file. A directory at that path is a `fail`, not a pass |
| `file_contains` | `path`, `pattern`, `absent?` | The regex matches, or does not match when `absent` is set. Read with `utf-8-sig` so a BOM does not shift offsets |
| `path_moved` | `from`, `to` | Source is gone and destination exists |
| `frontmatter` | `path`, `field`, `equals` | The file opens with `---`, the field is present in the block, and the scalar matches after quote trimming |
| `glob_count` | `pattern`, `op`, `n` | `root.glob(pattern)` count satisfies `== >= <= > <` |
| `command` | `argv`, `expect_exit?`, `stdout_contains?` | The locked command exits as expected and optional stdout text is present |

`frontmatter` normalizes the expected value before comparing:
`_frontmatter_equals_str()` maps JSON `true`/`false`/`null` to their lowercase
YAML spellings, because `--check-json` can supply real booleans and
`str(True)` is `"True"`, which would never match YAML `true`.

### Anti-vacuous rules

A checker that lets an agent record a bogus done is worse than no checker.
Three checks are therefore rejected rather than passed:

- `file_contains` with a positive pattern that matches the empty string
  (`""`, `^`, `$`, `.*`) returns `error`. It would match any text.
- `glob_count` with `>= 0` or `> -1` returns `error`. A count is never
  negative, so the predicate is always true.
- `path_moved` with an empty `from` or `to` returns `error`. An empty string
  resolves to the project root under a path join, so `{"to": ""}` would pass
  whenever the root exists.

### The command lock

`chk_command()` is the only checker that executes anything, so it is locked
hard. A ledger is a data file, and a data file must never be able to run
arbitrary commands.

- `argv[0]` must be `python`, `python.exe`, or `python3`.
- `argv[1]` must resolve to an existing regular file under the project root.
- Any shell metacharacter from `;|&$<>` plus backtick, CR and LF in any token
  is rejected. There is no shell: `subprocess.run` gets a list.
- PowerShell, pwsh, and any `.ps1` argument are rejected explicitly.
- `expect_exit` must be an integer. `bool` is rejected even though it is an
  `int` subclass.
- The child runs with `cwd=root`, a 120 second timeout, and
  `SHOWWORK_VERIFYING=1` in its environment. If that child triggers
  verification in turn, nested `command` checks refuse instead of recursing.
- `SHOWWORK_NO_COMMANDS=1` disables the checker entirely. It reports an error
  and the verdict degrades honestly to YELLOW. This is the policy switch CI
  uses on fork PRs so untrusted repo code never executes.

## Verdict algebra and exit codes

`evaluate_records()` applies the algebra. `EXIT_BY_VERDICT` maps it to process
exits.

| Verdict | Condition | Exit |
|---|---|---|
| `RED` | At least one active failed claim has RED severity | 2 |
| `YELLOW` | No RED failure, but a YELLOW claim failed or a checker errored | 3 |
| `GREEN` | Nothing failed or errored | 0 |

Unchecked prose is `skipped`. It never contributes. A GREEN verdict on a
session of pure prose means nothing was proven, not that everything is fine,
which is why `passed/total` is always printed alongside the verdict.

`audit_root()` uses the same three-value algebra over files: any RED file makes
the root RED, any YELLOW file makes it YELLOW, and no ledger files at all is
YELLOW rather than GREEN.

## CLI surface

`showwork <subcommand>`, defined in `cli.py`. A global `--root` precedes the
subcommand.

| Subcommand | What it does | Exit |
|---|---|---|
| `start` | Appends `session.start` to `sessions.jsonl` | 0 |
| `claim` | Builds a check spec from the flags (or takes `--check-json`) and appends the claim | 0 |
| `retract` | Appends a referencing retraction | 0 |
| `verify` | Verifies a day (`--date`) or a session (`--session`), writes `audit-<label>.md` unless `--no-report` | 0/3/2 |
| `finish` | The exit gate. See below | 0 or 2 |
| `audit` | Walks the integrity chain of every ledger file. `--strict` forbids forks | 0/3/2 |
| `run` | Wraps any command in a session | wrapped code, or 2 under `--gate`, or 127 |
| `stop-hook` | Reads a Stop payload on stdin, records the verdict | always 0 |
| `dashboard` | Renders replay JSON to a static HTML file, optionally serves it on loopback | 0 or 2 |
| `guard` | PreToolUse approval gate or PostToolUse stuck detection | 0, or 2 when stuck |

`claim` builds the check dict in `_build_check()`. Each type has a required set
of flags and `_req()` fails loudly with the missing flag name rather than
writing a half-formed check.

## What can refuse, and what cannot

This is the distinction the whole package turns on. Four call sites see the
same verdict and only some of them are allowed to act on it.

### `finish` is the gate

`finish_session()` in `ledger.py`:

1. Normalizes `status` case-insensitively and rejects anything but `ok` or
   `blocked`. `OK` must not silently skip the gate.
2. If `status=ok` and `--no-verify` was not passed, it verifies this session's
   own claims.
3. On RED it appends `session.finish.refused` and returns exit 2. No
   `session.finish` is written. The session is not closed.
4. Otherwise it appends `session.finish` carrying `claims_verdict`, plus
   `verify_bypassed: true` when the gate was deliberately skipped.

The three legitimate ways past a refusal are: fix the gap, retract the claim
truthfully, or close as `--status blocked`. The fourth way, `--no-verify`,
leaves a permanent stamp on the record that CI reads.

### The Stop hook only observes

`hooks.observe_stop()` verifies the session and appends `session.finish` with
`observed_by: "stop-hook"`, `claims_verdict`, and the full
`claims_unverified` list. Then the CLI returns 0 no matter what.

Two reasons. A Stop hook runs after the agent has already stopped, so there is
nothing left to block. And breaking the host's shutdown path would turn an
evidence adapter into an availability problem. The `stop-hook` branch in
`cli.py` wraps everything in a bare `except` and still returns 0 for the same
reason.

So the telemetry path and the gate path write to the same ledger and produce
the same verdict, but only the explicit `finish` can refuse. Hook backfill is
liveness evidence, not proof of completion.

### `run --gate` refuses on disagreement

`showwork run --session s -- <cmd>` records `session.start`, executes the
command with `SHOWWORK_SESSION` and `SHOWWORK_ROOT` exported into its
environment (showwork itself reads the root variable; the session variable is
there for the wrapped process to pick up), then verifies and records
`session.finish` with `observed_by: "run-wrapper"` and `command_exit`.

Observe mode is exit-transparent: it returns the wrapped command's own code.
`--gate` returns 2 in exactly one case, when the command exited 0 but the
session's claims are RED. That is "the agent said done and the receipts
disagree" turned into a nonzero exit an orchestrator can act on. A command that
cannot be found records a finish with `status: "error"` and returns 127.

### The CI action refuses on four conditions

`actions/verify/action.yml` installs showwork from the action's own ref, then
gates on:

1. `showwork audit` (chain integrity),
2. `showwork verify --session <id>` when a session is given,
3. a missing `session.finish` for that session, meaning the exit gate never
   ran,
4. `verify_bypassed` on the last finish event.

`strict: true` escalates YELLOW to a failure. `allow-commands` defaults to
false and exports `SHOWWORK_NO_COMMANDS=1`, so a fork PR cannot get its own
code executed by the checker. Output is echoed into the step summary.

## Control plane

Separate from verification. Verification asks whether a finished claim is true.
This layer asks whether a running agent should keep going.

### Approval gate (`guard --event pre`)

`control.evaluate_pre_tool_use()` matches the pending call against
`DEFAULT_RULES`: CI workflow writes, secret and credential files, database
migrations, history rewrites (force push, hard reset, `branch -D`), recursive
force deletes, and publishing commands (PyPI, twine, npm publish,
`gh release create`).

A `RiskRule` matches on any combination of tool name, path glob, and command
regex. A rule carrying none of those three matches nothing, since a rule with
no discriminator would match everything and that is a misconfiguration rather
than a policy. `render_pre_tool_use()` emits Claude Code's
`hookSpecificOutput.permissionDecision` shape. The default behavior is `ask`,
not `deny`, because the point is a human in the loop. Unattended runs should
pass `--behavior deny`.

The rules are patterns, not model judgment, for the same reason `finish`
refuses on a failed check: a gate an agent can argue with is not a gate.

### Stuck detection (`guard --event post`)

`guards.StuckDetector` reads the tool-call stream and reports three
signatures:

- `repeat`: the same tool with identical input N times inside a window.
  Default threshold 3, window 12.
- `alternation`: A-B-A-B ping-pong that never converges. Default 3.
- `no_progress`: N consecutive calls that mutated nothing. **Off by default.**

That default is calibrated, not guessed. `scripts/replay_transcripts.py` was
run over 2,757 real Claude Code sessions and 4,674 transcripts on 2026-07-18.
`no_progress` at 6 flagged 82.7% of sessions. Raising it did not rescue it: by
the threshold where it stopped firing on healthy sessions it had stopped
catching anything `repeat` had not already caught. `repeat` at 3 flagged 0.5%.
Every synthetic test passed while the shipped default was wrong, which is the
lesson recorded in the module docstring: fixtures prove the code does what it
was written to do, only real transcripts say whether it was written to do the
right thing.

Any mutating call clears the window. This is what separates a retry loop from
convergent work: edit, test, edit, test runs the same test command every cycle,
but each cycle changed the world.

The detector latches. Once stuck, every later observation returns the same
verdict until `reset()`.

Because a PostToolUse hook is a fresh process per call, the rolling window
lives on disk. `_load_guard_window()` and `_save_guard_window()` in `cli.py`
read and write `.showwork/guard-state.json`, and the window is cleared once a
verdict trips so a killed run starts clean. Both fail soft: a read failure
yields an empty window, which under-detects for a few calls, and that is the
safe direction. The whole `guard` branch catches its own exceptions and returns
0, because a guard that crashes the agent it protects is a worse outage than
the loop it was watching for.

Exit 2 from the post event halts the loop before the next model call.

### Budgets

`budgets.RunBudget` caps wall-clock seconds, total tool calls, and per-tool
call counts. Limits left as `None` are not enforced, all limits are inclusive,
and the clock is injected so replays are deterministic. Like the detector, it
latches.

It is a library API exported from `showwork`, not wired into any CLI
subcommand. Callers embed it in their own loop.

Dollar and token budgets are deliberately absent from this whole layer.
Anthropic's gateway and Cloudflare AI Gateway enforce spend natively, Claude
Code hooks receive no usage data at all, and a stuck agent is detectable from
the tool stream alone, before the money is spent rather than after.

## Two implementations, one conformance suite

`js/showwork-audit/index.mjs` implements the **reading half** of `spec-v0.2`:
chain verification and verdicts, `node:crypto` and `node:fs` only. It
re-executes no checks. Per the spec's reader-only conformance clause it reports
what it does not verify rather than skipping it silently.

`tests/fixtures/chain/` is the contract between them. Fifteen frozen `.jsonl`
files cover intact chains, tampering, deletion, forks, two genesis roots,
unchained appends, CRLF and lone CR, comments, U+2028 inside a string, and
non-finite JSON constants. `expected.json` holds the verdict each one must
produce. `tests/test_chain_fixtures.py` holds the Python side to it and
`js/showwork-audit/test.mjs` holds the Node side to the same file. If the two
ever disagree on a verdict that is a conformance bug, not an opinion.

`scripts/make_chain_fixtures.py` regenerates the fixtures deterministically.
Rerun it only when chain semantics change, and commit the diff consciously.

## Supporting scripts

| Script | Purpose |
|---|---|
| `scripts/run_tests.py` | Runs pytest. Exists so the repo's own ledger can carry a locked `command` claim that the suite passes |
| `scripts/false_done_rate.py` | Computes the False Done Rate from durable ledger evidence only |
| `scripts/evidence_pack.py` | Maps a date range of chain-verified receipts to EU AI Act, SOC 2, and HIPAA record-keeping language. Refuses to generate from a RED ledger |
| `scripts/replay_transcripts.py` | Replays recorded sessions through the stuck detector. The calibration input |
| `scripts/sanitize_replay.py` | Strips session ids, repo paths, and tool arguments out of replay data before publication |
| `scripts/build_public_dashboard.py` | Publication view, leads with the calibration finding |
| `scripts/render_dashboard.py` | CLI wrapper over `showwork.dashboard`, equivalent to `showwork dashboard` |
| `scripts/derive_case_study.py` | Derives sanitized aggregate metrics from the production ledger. Copies no claim text, paths, or financial data |

## Public surface

- PyPI package `showwork`, version 0.3.0, `requires-python >= 3.10`, zero
  runtime dependencies, MIT licensed. The console script `showwork` maps to
  `showwork.cli:main` (`pyproject.toml`).
- The Python API re-exported from `showwork/__init__.py`. `record_claim`,
  `verify_session`, `verify_date`, `resolve_root`, `finish_session`,
  `audit_root`, plus the control-plane types.
- `SPEC.md`, the portable `spec-v0.2` ledger format. Every normative
  requirement names a behavioral test beside it, and reader-only conformance
  is defined there for auditors like `js/showwork-audit`.
- `actions/verify`, consumable as `bmdhodl/showwork/actions/verify@main`.
- `docs/`: adapters, CI gating, the Claude Code Stop hook, fleet adoption,
  concurrency rationale, compliance mapping, live enforcement, the False Done
  Rate methodology, and the sanitized case study with derived metrics.
- The repo's own `.showwork/` receipts, which ship with each PR.

## Extension points

### A new check type

Four steps, in this order:

1. Write `chk_<name>(c: dict, root: Path) -> tuple[str, str]` in `checks.py`.
   Resolve every path through `_resolve()` so root confinement is not
   reimplemented. Return `error`, not `fail`, when the check cannot be
   evaluated.
2. Ask what the vacuous form of the check is and reject it explicitly. Every
   existing checker has one. If you cannot name a way for the check to pass
   while proving nothing, look harder.
3. Register it in `CHECKERS`. The driver, verdict algebra, retraction handling,
   and reporting pick it up with no further change.
4. Add the flags to the `claim` parser in `cli.py` and the branch in
   `_build_check()`. `--check-json` works without this step, so the CLI flags
   are ergonomics rather than a gate.

Then update `SPEC.md` with the normative semantics and a named test beside each
MUST, and add the test in `tests/test_checks.py`. A check type that is not in
the spec is not portable, and `tests/test_spec_conformance.py` exists to keep
the two aligned.

### A new adapter

An adapter needs exactly three behaviors, and the ledger is the only interface:

1. Record `session.start` when material work begins.
2. Append falsifiable claims as outcomes land.
3. Close through the exit gate before reporting success.

If the target can run a CLI at all, `showwork run` needs no integration
whatsoever. If it exposes lifecycle hooks, model the adapter on `hooks.py`:
observe and record, do not block. Decide deliberately which side of the
observe/gate line the adapter sits on, and if it observes, make sure it cannot
break the host by failing.

### A new reader

Implement the reading half of `SPEC.md` and run against
`tests/fixtures/chain/expected.json`. That fixture set is the entry test. Match
`split_record_lines()` and the strict JSON dialect exactly, or the record
counts and head hashes will drift from the reference under adversarial input.

### A new risk rule

Append a `RiskRule` to `DEFAULT_RULES` in `control.py`, or pass a custom
`rules` sequence to `RiskPolicy`. Give it at least one of tool set, path globs,
or command pattern.

## Deliberate omissions

Things that are absent on purpose, so nobody adds them back by accident:

- **No LLM judging.** Every checker is deterministic and reproducible by a
  third party who does not trust the writer. A verdict that needs inference to
  reproduce is not audit-grade.
- **No runtime dependencies.** Stdlib only, Python 3.10+. The Node reader is
  `node:crypto` and `node:fs`. This is a feature, not an accident.
- **No cost or token data anywhere.** Agent hooks carry none, and inventing it
  from a side channel would be the weakest number in the system. The dashboard
  counts tool calls instead, because those are real.
- **No service.** The dashboard is a static file. `--serve` binds to
  `127.0.0.1` on purpose, since it renders real session ids and paths.
- **No history rewriting.** Corrections are appends. This is enforced by the
  chain, not by convention.

## Tests

`python -m pytest tests/ -q` is the gate. 203 tests as of v0.3.0, all
behavioral. `scripts/run_tests.py` wraps the same run so the ledger can carry a
locked `command` claim asserting the suite is green.

`tests/test_spec_conformance.py` ties `SPEC.md`'s normative MUST clauses to
named tests, so a spec change without a test is caught. CI
(`.github/workflows/ci.yml`) runs three jobs: the Python suite plus a
verification of the committed genesis receipt, the Node conformance run against
the frozen fixtures, and `actions/verify` gating on the repo's own receipts.

This repo eats its own dog food. Every session that changes it records claims
with the version of showwork in `src/`, closes through the exit gate, and
commits the `.showwork/` receipt with the change. If a change breaks the tool,
the author's own exit gate is the first thing that says so. See `AGENTS.md`.
