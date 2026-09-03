# Changelog

All notable changes to showwork are recorded here.

## Unreleased

- **Per-session ledger files (`spec-v0.3`)** - new writes go to
  `.showwork/sessions/<id>.jsonl` and `.showwork/claims/<id>.jsonl`. Two agents
  with distinct slugs no longer share a hash-chained file. Leftover
  `sessions.jsonl` and `claims-YYYY-MM-DD.jsonl` stay readable. Package 0.4.0.
- **Worktree-local receipts** - linked worktrees write `.showwork/` in that
  worktree so the receipt ships with the branch. This reverses the 0.3.1 origin
  remap (commit 0873ca3).
- **Claim-time shape validation** - `validate_check_shape` rejects invalid
  `command` / `glob_count` checks before append; command lock errors point at
  `scripts/run_tests.py` + `stdout_contains=passed`.
- **Minimum-proof finish** - `finish --status ok` refuses empty or prose-only
  sessions; refused events stamp `claims_unverified` and `refuse_reason`.
- **`showwork status` / `showwork report`** - open-session view and FDR/usage
  window (`--since`, `--exclude-campaign`); FDR core lives in `showwork.report`.
- **Stop-hook session binding** - prefers `SHOWWORK_SESSION`; stamps
  `session_unbound` when falling back to the host payload id.
- **PyPI publish workflow pinning** - pinned checkout, Python setup, and PyPI
  publishing actions to audited commit SHAs; the owner-gated release path keeps
  the same behavior while avoiding floating action refs.

## 0.3.1 - 2026-08-14

Correctness and security hardening, plus production hygiene on the self-hosted CI runner.

- **`showwork run --max-seconds N`** - wall-clock ceiling for the run wrapper; the
  child is terminated and `budget_exceeded` is recorded when the envelope trips
  (commit e8fa3fc).
- **ReDoS defense in `file_contains`** - regex evaluation is bounded against
  catastrophic backtracking; patterns exceeding the safety limit are rejected
  upfront (commit f8000bb).
- **Audit-report coloring** - a GREEN session no longer paints RED in the report
  header when the file also contains other sessions' retractions (commit d09027a).
- **Worktree receipt persistence** - claims recorded from a git linked worktree now
  persist correctly to the canonical `.showwork/` directory instead of the
  worktree-local path (commit 0873ca3).
- **CI runner optimization** - self-hosted WSL runner hygiene: cached workflow
  directories are pruned, lightweight checks run outside the machine build slot,
  and the local runner setup is optimized (commits 7e54596, a7013ea, 2d12d08).
- **Documentation** - added ARCHITECTURE.md situating showwork's layers (commit
  94a8348); pinned the verify action example to `@v0.3.0` instead of `@main`
  (commit ae4fe94); and positioned showwork against the "Code as Agent Harness"
  survey's verification problem (commit 59cb472).
- **Public calibration dashboard** - sanitized aggregate metrics page (commit
  5d6cb19).
- **Adoption example correction** - the retraction workflow now uses the
  shipped `--claim` flag instead of an unsupported `--claim-index` flag.
- **Frontmatter boundary hardening** - frontmatter checks require exact opening
  and closing delimiter lines, preventing malformed blocks from becoming proof.
- **Packaging metadata cleanup** - use the SPDX `MIT` license expression and
  explicit license file metadata, removing deprecated packaging warnings ahead
  of the 0.3.1 distribution build.
- **HTTP probe checker** - verify bounded HTTP(S) status and optional body
  evidence without following redirects; network checks are disabled by default
  in the GitHub Action.
- **Git state checker** - verify local clean/dirty status, exact branch, or a
  non-vacuous commit prefix using fixed Git queries.

All changes are backward-compatible. The ledger format (spec-v0.2) is unchanged.

## 0.3.0 - 2026-07-18

Adds the enforcement half. The ledger proved what an agent claimed; this stops
the agent before it does damage worth proving.

- **`showwork.guards`** - stuck detection over the tool-call stream. Three
  signatures: `repeat` (identical call, unchanged args), `alternation` (A-B-A-B
  that never converges), `no_progress` (consecutive calls that mutate nothing).
  Every trip returns a `StuckVerdict` carrying the evidence that justified it.
- **`showwork.control`** - Claude Code adapters. `PreToolUse` approval gates for
  risky actions (CI workflows, secrets, migrations, force-push, recursive force
  delete, publishing) and `PostToolUse` stuck-halt. Deterministic patterns, not
  a model judging a model.
- **`showwork.budgets`** - `RunBudget`: wall-clock, total tool-call, and
  per-tool rate ceilings, with an injectable clock so budgets are testable
  without sleeping.
- **`showwork.dashboard`** + `showwork dashboard [--serve]` - static runs /
  status / interventions / proof-of-work view. No service, no signup, no
  database. Serving binds loopback only; it renders real session ids and tool
  arguments.
- **`showwork guard --event pre|post`** - the hook entry point. One
  `settings.json` entry enables live enforcement; see `docs/live-enforcement.md`.
- **`scripts/replay_transcripts.py`** - replay recorded sessions through the
  detector to calibrate thresholds against your own workload.

### Calibration

Defaults come from replaying **4,674 recorded Claude Code sessions** (2,757 with
tool calls), not from fixtures:

| signature | flagged | read |
|---|---|---|
| `repeat` (3, window 12) | 14 (0.5%) | plausible true positives |
| `no_progress` (6) | 2,281 (82.7%) | noise |
| `alternation` (3) | 0 | never fired |

`no_progress` was written with a default of 6 and would have killed four out of
five real sessions - reading a dozen files before an edit is ordinary work, not
a stall. It is **off by default**, pinned by `test_no_progress_is_off_by_default`.
Every synthetic test passed while that default was wrong.

A mutation clears the detector window, so `edit -> test -> edit -> test` is never
killed: repeating a command after a real change is convergent work, repeating it
with nothing changed in between is a loop. That distinction is what a
dollar-metering gateway structurally cannot see.

### Deliberately absent

No token or cost budgets. Claude Code hooks receive no usage data
(anthropics/claude-code#11008), and Anthropic's gateway and Cloudflare AI Gateway
both enforce spend natively and for free.

The guard fails open on its own internal errors. A guard that crashes the agent
it protects is a worse outage than the loop it watched for.

- **Cross-implementation dialect freeze**: the Python reference auditor and
  `js/showwork-audit` diverged on hostile/degenerate input because they used
  different JSON and line-segmentation dialects. Python `json.loads` accepted
  the bare tokens `NaN`/`Infinity`/`-Infinity` (which `JSON.parse` rejects), and
  `str.splitlines()` split on U+2028/U+2029/U+0085/VT/FF/FS-RS and a lone CR
  (which a `JSON.parse`-based reader never treats as a line boundary). A record
  with a raw U+2028 inside a JSON string, or non-strict number literals, audited
  to different verdicts in each implementation. Both now split on `\r?\n` only
  and reject non-standard JSON constants as parse errors (`audit.py` and
  `ledger.py` share `split_record_lines`/`strict_json_loads`). Four new frozen
  conformance fixtures (`nonfinite-constant`, `u2028-in-string`, `lone-cr`,
  `nlcr-break-numbering`) bind both implementations verdict-for-verdict; SPEC.md
  "Storage and framing" now specifies the split rule and the strict dialect. No
  record-format change; well-formed linear ledgers audit identically.
- **Fork-tolerant audit**: concurrent sessions appending in separate git
  worktrees and merging produce a *fork* — two record blocks chaining off the
  same parent line — which a linear walk mis-read as a chain break (RED). The
  audit now accepts a `prev` that re-anchors to any earlier line as a fork
  (GREEN), reports the fork count and every branch head, and still goes RED on
  real tampering, deletion, reorder, or an unchained append. `showwork audit
  --strict` forbids forks for repos that want single-history. A `.gitattributes`
  `merge=union` stanza makes concurrent appends concatenate instead of writing
  conflict markers. No record format change; existing linear ledgers audit
  identically. Mirrored in `js/showwork-audit`; two new conformance fixtures
  (`forked`, `forked-tampered`) bind both implementations. Rationale and the
  2026-07-16 bmdpat incident: docs/concurrency.md.

## 0.2.0 (2026-07-16)

Five moves, one arc: provable -> enforced -> ubiquitous -> famous -> paid.

- **Integrity chain (`spec-v0.2`)**: every appended record carries `prev`
  (SHA-256 of the previous record line; EOL-agnostic; per-file genesis
  anchor). New `showwork audit` re-derives every chain: tampering, deletion,
  or unchained appends RED at the exact line; per-file head hashes let one
  published hash anchor all history behind it. Pre-chain (v0.1) records are
  anchored by the first chained append.
- **CI gate**: `actions/verify` composite GitHub Action - fails a job on
  chain break, failed session claims, missing exit-gate close, or a
  `--no-verify` bypass stamp. Installs from its own ref. Fork-PR safety via
  `SHOWWORK_NO_COMMANDS` (command checks refuse to execute repo code and the
  verdict degrades honestly to YELLOW). Own CI dogfoods it.
- **Universal wrapper**: `showwork run --session S [--gate] -- <cmd>` wraps
  any agent process in a session; gate mode exits 2 on "command says
  success, receipts say RED".
- **Second implementation**: `js/showwork-audit`, a zero-dependency Node
  auditor for the spec's reading half; 8 frozen conformance fixtures bind
  both implementations verdict-for-verdict.
- **False Done Rate**: `scripts/false_done_rate.py` + pre-registered
  methodology (docs/false-done-rate.md) + real day-0 fleet report: 21
  eligible sessions, 42.9% contained a false done - every one caught by the
  gate (docs/false-done-rate-day0.md).
- **Evidence packs**: `scripts/evidence_pack.py` maps date-ranged,
  chain-verified receipts to EU AI Act Art. 12/26(6), SOC 2 CC8.1/CC7.x,
  HIPAA 164.312(b)/164.316(b); refuses tampered ledgers; `--redact`
  (docs/compliance.md + a real sample pack).

Suite: 75 tests. Every phase closed through the exit gate; the ledger's own
history now includes the gate refusing its author's mangled claim twice
during phase 1 - dogfood at its most literal.

## 0.1.0

- Add six deterministic claim checkers with anti-vacuous validation.
- Add append-only claims, retractions, and session lifecycle records.
- Add a clean-finish exit gate that refuses failed RED claims.
- Add a Claude Code/Codex-compatible Stop-hook observer.
- Publish the portable `spec-v0.1` ledger specification and conformance map.
- Publish a sanitized, reproducible production case study.
- Add self-hosted GitHub Actions CI that verifies the committed genesis receipt.
