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

## Phase 3 — Ubiquity: universal wrapper + second implementation  [status: DONE 2026-07-16]

- [x] `showwork run --session S [--gate] -- <any agent command>`: wraps any
      process in a session; observe mode is exit-transparent, gate mode
      exits 2 on "command says success, receipts say RED"; child inherits
      SHOWWORK_SESSION/SHOWWORK_ROOT (5 tests)
- [x] `js/showwork-audit`: zero-dep Node implementation of the spec-v0.2
      reading half (chain audit + verdicts; re-executes no checks; scope
      honestly narrowed from "TS + check re-execution" to reader-only
      conformance, which the spec explicitly blesses)
- [x] Cross-implementation conformance: 8 frozen fixture ledgers
      (tests/fixtures/chain/ + expected.json, regenerable via
      scripts/make_chain_fixtures.py); Python 8/8, JS 9/9, and both agree
      with each other on this repo's real ledger byte-for-byte on heads
- [x] `conformance-js` CI job; docs/adapters.md (Claude Code, Codex, Gemini,
      wrapper, write-your-own)

## Phase 4 — The False Done Rate  [status: DONE 2026-07-16]

- [x] `scripts/false_done_rate.py`: session- and event-level FDR from any
      labeled set of ledgers; durable evidence only (REFUSED events,
      retractions, RED closes, bypass stamps); 5 behavioral tests
- [x] docs/false-done-rate.md: pre-registered methodology + honesty rules
      (lower bound stated, low rates published too, no retro-editing)
- [x] docs/false-done-rate-day0.md + frozen .json: REAL day-0 numbers —
      **21 eligible sessions across the fleet, 9 false-done (42.9%), every
      one caught by the gate**, incl. the gate catching its own author
      during phase 1. One repo excluded (pre-adoption branch), stated.

## Phase 5 — Compliance evidence packs  [status: DONE 2026-07-16]

- [x] `scripts/evidence_pack.py`: date-range of receipts → auditor bundle
      (integrity heads, activity summary, control mapping, receipt
      inventory, `--redact`); REFUSES to generate from a RED ledger
      (4 behavioral tests)
- [x] docs/compliance.md: EU AI Act Art. 12 / Art. 26(6), SOC 2 CC8.1 +
      CC7.2/7.3, HIPAA 164.312(b) / 164.316(b); point-in-time vs
      at-export verification explained; not-legal-advice framing throughout
- [x] docs/evidence-pack-sample.md: real pack from this repo's own ledger
      (honestly shows 3 refusals + historical claims that no longer verify)

## Exit criteria (all phases)

- [x] Full suite green (75 tests); `showwork audit` on own ledger: today's
      files GREEN and anchored; pre-2026-07-16 files honestly YELLOW
      (pre-chain history cannot be retro-proven — that is the point)
- [x] Every phase's session closed GREEN through the exit gate
      (v02-phase-1 through v02-phase-5; phase 1 includes 2 genuine REFUSEDs)
- [x] CHANGELOG + version bump to 0.2.0; README v0.2 sections
- [ ] Marketing video of the new capabilities, real CLI output only
