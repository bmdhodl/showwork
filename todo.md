# showwork v0.2 build plan — five phases, in order

Each phase makes the next one possible: **provable → enforced → ubiquitous →
famous → paid.** One phase at a time; tests green before every commit; every
phase closes through showwork's own exit gate (session `v02-phase-N`).

## Phase 1 — Tamper-evident receipts (`spec-v0.2`)  [status: DONE 2026-07-16]

Hash-chain the ledger so "append-only" is provable, not promised.

- [x] `prev` field on every appended record: sha256 of the previous record's
      line content (EOL-agnostic; genesis anchor for empty files)
- [x] `showwork audit [--json]`: walks every ledger file, verifies the chain,
      names the exact line of any break, prints per-file head hashes
      (publish a head hash anywhere = external anchor for the whole history)
- [x] Pre-chain era handled: existing v0.1 records are anchored the moment the
      first chained record lands after them
- [x] `.gitattributes` so ledgers never get EOL-rewritten
- [x] SPEC.md → `spec-v0.2` "Integrity chain" section, test anchors beside
      every normative requirement (house style)
- [x] tests/test_audit.py (10 tests) — tamper/delete/unchained detection,
      EOL survival, pre-chain anchoring, CLI exit codes
- Session `v02-phase-1` closed GREEN (4/6; 2 honest retractions in history —
  the gate REFUSED a bash-mangled regex claim mid-development. Dogfood works.)

## Phase 2 — Receipts as CI gates  [status: DONE 2026-07-16]

- [x] `actions/verify/action.yml`: composite GitHub Action — fails a job when
      the receipt is missing, RED, chain-broken, or bypass-stamped; renders
      the receipt into the job step summary; installs from its own ref (no
      PyPI dependency)
- [x] Fork-PR safety: `SHOWWORK_NO_COMMANDS` policy env — command checks
      refuse to execute repo code, verdict degrades honestly to YELLOW
- [x] Dogfood: `receipts` job in ci.yml gates on the chain audit + the real
      `v02-phase-1` session (fork-safe mode live-demonstrated)
- [x] docs/ci.md: inputs, failure modes, fork-safety, session→PR mapping
- Gate script validated locally by rendering the composite step and running
  it against this repo's real ledger (exit 0; honest YELLOWs displayed)

## Phase 3 — Ubiquity: universal wrapper + second implementation  [status: pending]

- [ ] `showwork run --session S -- <any agent command>`: wraps any process in
      a session (start → run → finish observe-mode with verdict stamped)
- [ ] `js/`: TypeScript auditor (`showwork-audit-js`) — parses the ledger,
      verifies the hash chain, computes verdict algebra; filesystem checks
      re-verified where dialect-safe, `command` reported as unsupported
      (YELLOW), never silently skipped
- [ ] Cross-implementation conformance: fixture ledgers verified by both
      implementations must agree verdict-for-verdict
- [ ] docs/adapters.md: Codex CLI, Gemini CLI, generic wrapper lifecycles

## Phase 4 — The False Done Rate  [status: pending]

- [ ] `scripts/false_done_rate.py`: computes FDR from any set of ledgers —
      sessions whose clean close was REFUSED (or closed RED/bypassed) over
      total closed sessions with checked claims; per-agent breakdown
- [ ] docs/false-done-rate.md: pre-registered methodology (claim taxonomy,
      what counts, what does not, honesty rules — a low rate gets published
      too)
- [ ] Day-0 report from the real fleet ledgers, numbers traceable to claim IDs

## Phase 5 — Compliance evidence packs  [status: pending]

- [ ] `scripts/evidence_pack.py`: date-range of chain-verified receipts →
      auditor-readable bundle (control ↔ receipt ↔ chain proof)
- [ ] docs/compliance.md: mapping tables — EU AI Act Art. 12 record-keeping /
      Art. 26 deployer obligations, SOC 2 CC-series, HIPAA audit controls —
      framed as supporting evidence, explicitly not legal advice
- [ ] One real pack generated from this repo's own ledger

## Exit criteria (all phases)

- [ ] Full suite green, `showwork audit` GREEN on own ledger
- [ ] Every phase's session closed GREEN through the exit gate
- [ ] CHANGELOG + version bump to 0.2.0
- [ ] Marketing video of the new capabilities, real CLI output only
