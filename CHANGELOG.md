# Changelog

All notable changes to showwork are recorded here.

## Unreleased

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
