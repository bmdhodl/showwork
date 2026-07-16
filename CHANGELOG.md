# Changelog

All notable changes to showwork are recorded here.

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
