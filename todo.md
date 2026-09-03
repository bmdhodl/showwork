# showwork build plan

## v0.2 five phases — DONE (2026-07-16)

See git history / CHANGELOG 0.2.0. Provable → enforced → ubiquitous → FDR →
compliance evidence packs all closed through the exit gate.

## PR #65 follow-up — CI + review  [status: in tree]

- [x] Restore SPEC Integrity chain heading (`spec-v0.2`) so session
      `v02-phase-1` still verifies
- [x] Clean-room tamper path uses `.showwork/sessions/<id>.jsonl`
- [x] Clean-room fork-safe claim uses locked `python scripts/ok.py`
- [x] Blocked finish stamps `claims_verdict` (Copilot review)
- [x] Stop-hook docstring matches `session_unbound` behavior (Copilot review)
- [x] Session stems stay injective after rewrite (Codex P1)
- [x] `run --gate` refuses empty/prose-only success (Codex P1)
- [x] `status` reopens after a later `session.start` (Codex P2)
- [x] Hash stems from the untrimmed session id (Codex P1 round 2)
- [x] Claim-time shape for every checker type (Codex P1 round 2)
- [x] FDR script inserts `src/` (Codex P2 round 2)
- [x] Status uses the latest close attempt (Codex P2 round 2)
- [x] Keep `lossy = cleaned != raw` as a one-line assignment (CI verify)
- [x] `record_claim` treats `check={}` as invalid, not prose (Codex P2 PR 66)

## v0.4.0 writer isolation — per-session files  [status: in tree, unreleased]

- [x] New writes: `.showwork/sessions/<id>.jsonl` and `.showwork/claims/<id>.jsonl`
- [x] Readers still load leftover `sessions.jsonl` and `claims-YYYY-MM-DD.jsonl`
- [x] Linked worktrees write receipts in that worktree
- [x] SPEC.md → `spec-v0.3`; package version 0.4.0 (publish is owner-gated)

## v0.3.x operator cut — ergonomics + continuous metrics

Goal: cut agent claim misuse and make FDR/usage visible in the CLI. Defer new
check types and external adapters until agents stop failing on shipped checks.

- [x] Claim-time shape validation + clearer command-lock remediation
      (`validate_check_shape`, prefer `stdout_contains=passed`)
- [x] Finish refuses empty / prose-only sessions; refused events stamp
      `claims_unverified` + `refuse_reason`
- [x] `showwork status` / `showwork report` (FDR + usage; `--exclude-campaign`)
- [x] Stop hook binds `SHOWWORK_SESSION`; stamps `session_unbound` otherwise
- [x] Docs: AGENTS.md, claude-code.md, agent-prompt, SPEC, ARCHITECTURE 0.3.1

### Explicit non-goals (this cut)

- New checkers, point-in-time verify, detached signing
- Cursor / OpenAI Agents adapters (trigger: ≥3 external repos)
- Full claims dashboard UI (report --json is enough for now)

## Exit criteria

- [x] Full suite green (287 tests)
- [x] Session `improve-ergonomics-metrics-20260828` closed GREEN through the gate
