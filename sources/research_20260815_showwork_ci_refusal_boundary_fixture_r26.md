# CI refusal-boundary fixture — r26

Date: 2026-08-15  
Scope: disposable/local replay of `actions/verify/action.yml`; no action, permission, GitHub, or release change  
Source checkout: `ef9cacd`

## Replay method

The Verify-receipts shell policy in `actions/verify/action.yml` was replayed
with local `showwork` CLI subprocesses and synthetic roots. The fixtures
covered valid proof, a RED claim, a missing ledger, a tampered ledger, and
valid command/http claims evaluated with the action's default
`allow-commands=false` and `allow-network=false` policy. Both `strict=false`
and `strict=true` were evaluated where YELLOW behavior mattered.

The replay inspected command exits, the `## showwork receipt` summary framing,
plain receipt lines, and the durable sessions ledger. It did not invoke GitHub,
open a PR, install an action, or contact a public endpoint.

## Input-to-outcome matrix

| fixture | audit exit | session verify exit | action exit, non-strict / strict | durable refusal |
|---|---:|---:|---:|---|
| valid proof | 0 GREEN | 0 GREEN | 0 / 0 | no; clean finish is recorded |
| RED claim / missing proof | 0 GREEN | 2 RED | 1 / 1 | yes; seed exit gate recorded `session.finish.refused` |
| missing ledger | 3 YELLOW | not run with empty session input | 0 / 1 | no ledger exists; strict mode converts YELLOW to failure |
| tampered chained ledger | 2 RED | 0 GREEN in this fixture | 1 / 1 | no action event; audit refusal is the evidence |
| network claim with `SHOWWORK_NO_NETWORK=1` | 0 GREEN | 3 YELLOW | 0 / 1 | no action event; policy error is visible in verify output |
| command claim with `SHOWWORK_NO_COMMANDS=1` | 0 GREEN | 3 YELLOW | 0 / 1 | no action event; policy error is visible in verify output |

The tampered case intentionally changed the first of two chained claim lines.
The session claim check still passed because its referenced file existed; the
chain audit independently returned RED. This is why the action runs both
audit and session verification.

Every replay wrote the `## showwork receipt` header and fenced summary. No
`::error` or `::warning` annotations were emitted by the action logic. The
action's `gate` function treats exit 3 as a tolerated YELLOW in non-strict
mode, and as a failure in strict mode; exit 2 or any other nonzero exit fails
both modes.

## Reader-safe boundary

This demonstrates a local action-policy contract, not GitHub workflow health,
marketplace adoption, user trust, compliance, or release compatibility. A
non-strict pass with YELLOW command/network checks means the configured policy
did not fail the job; it does not mean those checks ran or that the proof is
complete. Keep command and network opt-ins owner-reviewed for untrusted input.

## Verification

- Action-policy tests: `python -m pytest tests/test_ci_policy.py -q` -> `6 passed`.
- No `action.yml`, workflow, permission, GitHub state, production code, public
  copy, package, or release change.
