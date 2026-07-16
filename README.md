# showwork

[![CI](https://github.com/bmdhodl/showwork/actions/workflows/ci.yml/badge.svg)](https://github.com/bmdhodl/showwork/actions/workflows/ci.yml)

**Make your AI agents show their work.**

Observability tools log what an agent *did*. showwork verifies what an agent *claimed* it did — deterministically, against reality — and refuses to bless a "done" that isn't real.

Zero dependencies. Stdlib only. One append-only ledger.

[Read the portable `spec-v0.1` ledger specification](SPEC.md) or install the
[Claude Code Stop-hook adapter](docs/claude-code.md).

## The problem

An agent reports "done: I updated the config, logged the decision, and moved the task file." Two of those three things never happened. Your logs show the agent ran. Your traces show what tools it called. Nothing checks whether the *outcome it asserted* is true.

That gap is why agent pilots die before production, and it's what audit-trail requirements (EU AI Act, HIPAA, SOC 2) actually ask for: not "what did the agent do," but "prove the record is faithful."

## The model

1. **Claims are falsifiable or they're just prose.** When an agent (or its harness) reports a completed change, it appends a structured claim to the ledger: a file changed, a path moved, a metric holds, a command passes. Free-form prose is recorded but never counted as proof.
2. **Verification is deterministic.** `showwork verify` re-checks every claim against the filesystem and locked commands. No LLM judges an LLM.
3. **The exit gate refuses false dones.** `showwork finish --status ok` verifies the session's own claims first. If any is RED, the close is refused (exit 2). Fix it, retract it, or close as `blocked` — the bypass is stamped on the record either way.
4. **The ledger is append-only.** Corrections are retraction records that reference the original claim. History is never rewritten.

## Quickstart

```bash
pip install showwork
```

```bash
# an agent session starts
showwork start --session deploy-fix --agent claude-code

# the agent claims what it did, with a check that can fail
showwork claim --session deploy-fix \
  --claim "bumped the API timeout in config" \
  --type file_contains --path config/api.yaml --pattern "timeout: 30"

showwork claim --session deploy-fix \
  --claim "tests pass" \
  --type command --command-arg python --command-arg scripts/run_tests.py

# the close is gated: exit 0 only if every claim verifies
showwork finish --session deploy-fix --status ok
```

```
claims: GREEN (2/2 verified)
session.finish recorded: deploy-fix
```

If a claim doesn't hold:

```
claims: RED (1/2 verified)
REFUSED: a clean close requires this session's claims to verify.
```

Audit any day or any session after the fact:

```bash
showwork verify --date 2026-07-09        # exit 0 GREEN, 3 YELLOW, 2 RED
showwork verify --session deploy-fix --json
```

## Check types

| type | asserts |
|---|---|
| `file_exists` | a file is present |
| `file_contains` | a regex matches (or is absent from) a file |
| `path_moved` | source is gone, destination exists |
| `frontmatter` | a YAML frontmatter field equals a value |
| `glob_count` | a glob's match count satisfies `== >= <= > <` |
| `command` | a **locked** command exits as expected (`python <script under project root>` only — no shell, no metacharacters, no escape) |

Vacuous checks are rejected, not blessed: a regex that matches the empty string, or a glob count that's always true (`>= 0`), returns an error instead of a pass. A checker that lets an agent record a bogus "done" is worse than no checker.

## Tamper-evident by construction (v0.2)

Every appended record carries the SHA-256 of the record before it, so
"append-only" is provable, not promised:

```bash
showwork audit
# showwork audit  =>  GREEN  (34/34 records chained)
#   OK  claims-2026-07-16.jsonl  head ad93b1103b7bfc04
```

Alter, delete, or reorder one byte of chained history and the audit goes RED
at the exact line. Publishing a file's *head hash* anywhere out-of-band (a
commit message, a post) anchors the entire history behind it. Spec:
[SPEC.md](SPEC.md) § Integrity chain. A zero-dependency Node auditor
([js/showwork-audit](js/showwork-audit/)) is held to the same frozen
conformance fixtures as the Python reference.

## Gate your CI on receipts

```yaml
- uses: bmdhodl/showwork/actions/verify@main
  with:
    session: my-agent-session
```

Fails the job on a chain break, failed claims, a missing exit-gate close, or
a `--no-verify` bypass stamp — and renders the receipt into the step summary.
Fork-safe by default ([docs/ci.md](docs/ci.md)).

## Wrap any agent, no integration

```bash
showwork run --session fix-123 --gate -- codex exec "fix the failing test"
```

Observe mode is exit-transparent; `--gate` exits 2 when the command reports
success but the receipts are RED ([docs/adapters.md](docs/adapters.md)).

## The False Done Rate

Receipts make a new number measurable: **how often agents claim work that is
not backed by reality.** Day-0 on our own production fleet: **21 sessions,
42.9% contained a false done — every one caught by the gate.** Methodology
pre-registered, corpus honesty rules included:
[docs/false-done-rate.md](docs/false-done-rate.md).

## Evidence packs for auditors

`scripts/evidence_pack.py` maps a date range of chain-verified receipts to
EU AI Act Art. 12/26(6), SOC 2, and HIPAA record-keeping language — and
refuses to generate from a tampered ledger
([docs/compliance.md](docs/compliance.md)).

## Python API

```python
from showwork import record_claim, verify_session, resolve_root

root = resolve_root()
record_claim(root, session="nightly", claim="report written",
             check={"type": "file_exists", "path": "reports/2026-07-09.md"})
state = verify_session(root=root, session="nightly")
assert state["verdict"] == "GREEN"
```

## Provenance

This isn't a spec written on a whiteboard. It's extracted from the verification
layer that runs a real one-person, AI-operated company. The system began after
one agent confidently reported three completed actions and two were not real.
The resulting production ledger now supplies the receipts behind the package.

[Read the sanitized case study and reproduce its aggregate metrics.](docs/case-study.md)

The sanitized snapshot contains 2,158 claims from 842 sessions. Deterministic
checks back 2,152 claims. The ledger preserves 152 retractions and surfaced one
malformed line instead of dropping it. Its captured audit was RED at 54/60
verified, because failed proof remains visible rather than becoming a green
marketing number.

## What showwork is not

- Not observability. Traces show what happened; showwork proves what was *claimed* to have happened.
- Not agent testing. Test frameworks check behavior pre-deployment; showwork verifies outcomes at runtime, every session.
- Not an LLM judge. Every check is deterministic and reproducible — which is what makes the record audit-grade.

## Roadmap

- More coding-agent adapters (OpenAI Agents SDK / LangGraph middleware)
- Event stream + point-in-time replay
- More check types (HTTP probe, git state)
- False Done Rate at study scale: controlled task sets, per-model corpora
- Detached signing of ledger heads (external timestamp anchoring)

## License

MIT
