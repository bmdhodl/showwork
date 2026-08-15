# showwork CI command/network policy case matrix r16

Date: 2026-08-15  
Scope: local static inspection and disposable loopback fixtures. No live GitHub
run was inferred; no public URL was contacted by the fixture; no workflow,
action ref/default, security copy, schema, verifier, or release change.

## Sources inspected

- `.github/workflows/clean-room-action.yml`: fork-shaped pull requests are
  excluded when the head repository differs from the base repository.
- `.github/workflows/ci.yml`: the same repository guard is present and the
  receipt job leaves `allow-commands` false and tolerates YELLOW unless strict.
- `actions/verify/action.yml`: command/network inputs default false; false
  inputs set `SHOWWORK_NO_COMMANDS` and `SHOWWORK_NO_NETWORK`; exit 3 fails only
  when strict is true, while other nonzero exits fail.
- `src/showwork/checks.py`: the two environment gates return explicit errors;
  the allowed command is locked to a Python script under the root and the
  allowed HTTP probe is bounded and redirect-free.
- `docs/ci.md`: the copy describes fork safety and limits it to the declared
  command/network defaults.

## Disposable fixture matrix

| case | local observation | classification |
|---|---|---|
| fork-like head repository mismatch | workflow `if` condition is false | job skipped before the bounded receipt check |
| same repository, no opt-ins | command returns `error` naming `SHOWWORK_NO_COMMANDS`; loopback probe returns `error` naming `SHOWWORK_NO_NETWORK`; record evaluation is YELLOW | bounded refusal; default non-strict action tolerates YELLOW |
| same repository, explicit local opt-ins | a root-local Python fixture returns 0 and a loopback-only HTTP fixture returns 200 with the expected body; record evaluation is GREEN | bounded check reached; not a live GitHub run |
| command refusal | locked command is not executed when the env gate is set | YELLOW input, not success evidence |
| explicit network refusal | no request is made when the env gate is set | YELLOW input, not network proof |
| strict escalation | action `gate` function treats exit 3 as failure when `strict=true`; exit 2/other nonzero always fails | policy mapping observed statically |

The loopback server was bound to `127.0.0.1` and shut down before cleanup. No
public URL or external network side effect was used.

## Copy ambiguity and recommendation

“Fork-safe” is accurate for these declared command/network refusal paths, but it
can be overread as a complete supply-chain or hostile-code guarantee. **Bounded
documentation recommendation:** keep the phrase adjacent to the exact limits:
fork-shaped jobs skip, command checks are refused by default, network probes are
refused by default, and explicit trusted opt-ins are required for a bounded
check. Do not add certification, compliance, adoption, or supply-chain claims.

Decision: **NO CHANGE.** The current local matrix supports the existing refusal
boundary; no workflow/action/public-copy change is justified by synthetic local
evidence.

Validation: `python -m pytest tests/ -q --basetemp=...` -> **239 passed**.
