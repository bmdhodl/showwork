# showwork action fork and network policy readout r15

Date: 2026-08-15  
Scope: static evaluation of the committed CI workflow, composite action, and
CI documentation. No workflow policy, verifier, schema, signer, authority,
compliance, adoption, public-copy, or release change. No fixture contacted a
public URL.

## Policy matrix

| shape | command checks | network checks | workflow/action state | safe interpretation |
|---|---|---|---|---|
| trusted same-repository, defaults | blocked by `SHOWWORK_NO_COMMANDS` | blocked by `SHOWWORK_NO_NETWORK` | non-strict action tolerates YELLOW | safe default; no repository code or URL is executed |
| trusted same-repository, explicit `allow-commands: true` | may execute locked Python checks | still blocked unless network is also enabled | explicit owner choice | same-repository execution only; not a security proof |
| trusted same-repository, explicit `allow-network: true` | still blocked unless commands are also enabled | bounded probe may run | explicit external dependency | response evidence is live and time-bound |
| fork-shaped pull request | clean-room job is skipped by its repository-equality `if` guard | no fixture runs | no untrusted workflow execution | refusal by workflow policy |
| fork-shaped ledger sent to action defaults | command checks report policy errors | network checks report policy errors | non-strict YELLOW can pass; strict fails | repository-controlled inputs are not executed by default |
| pinned ref | checkout uses SHA `9c091bb...` | local action resolves from checkout | deterministic action source | pinning narrows drift; it is not complete supply-chain proof |
| floating `@main` | not recommended by docs | not recommended by docs | testing only | refuse for a trusted gate |

The action's `strict: true` input converts YELLOW into a failing gate. With the
default `strict: false`, a policy refusal can be an honest partial-verification
state rather than a false GREEN claim.

## Safe and refusal paths

Safe path: a trusted same-repository workflow keeps both opt-ins false, audits
the chain, verifies the session, and accepts only the documented non-strict
YELLOW behavior for blocked command/network checks.

Explicit refusal path: a fork-shaped clean-room pull request does not enter the
job, and the action's default environment refuses any command or network claim
that reaches the verifier. Neither path proves GitHub supply-chain security.

## Recommendation

**NO CHANGE.** Keep a static regression check for the fork equality guard, the
two opt-in defaults, the pinned checkout SHA, and the strict/YELLOW gate
mapping. Do not enable either opt-in for fork-shaped input.

Canonical local evidence: `.github/workflows/clean-room-action.yml`,
`.github/workflows/ci.yml`, `actions/verify/action.yml`, and `docs/ci.md`.

Validation: `python -m pytest tests/ -q --basetemp=<temp>\showwork-r15-full-20260815` -> **234 passed in 13.27s**.
