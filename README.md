# showwork

[![CI](https://github.com/bmdhodl/showwork/actions/workflows/ci.yml/badge.svg)](https://github.com/bmdhodl/showwork/actions/workflows/ci.yml)
[![PyPI version](https://img.shields.io/pypi/v/showwork.svg)](https://pypi.org/project/showwork/)

**Make your AI agents show their work.**

Observability tools log what an agent *did*. showwork verifies what an agent *claimed* it did, deterministically, against reality, and refuses to bless a "done" that isn't real.

Zero dependencies. Stdlib only. One append-only ledger.

[Read the portable `spec-v0.4` ledger specification](SPEC.md). Install the
[Claude Code Stop-hook adapter](docs/claude-code.md) or run
`showwork init` for Cursor, Claude, and a CI draft.

Surveyed 2026-09-03: 0 GitHub stars, 1 fork, 448 lifetime PyPI downloads.
Day-0 False Done Rate on the author's fleet: 21 sessions, 42.9% contained a
false done. Every one was caught by the gate. Source:
[docs/false-done-rate-day0.md](docs/false-done-rate-day0.md).
The published PyPI package is still 0.3.0. This tree is 0.4.0.

## The problem

An agent reports "done: I updated the config, logged the decision, and moved the task file." Two of those three things never happened. Your logs show the agent ran. Your traces show what tools it called. Nothing checks whether the *outcome it asserted* is true.

That gap is why agent pilots die before production, and it's what audit-trail requirements (EU AI Act, HIPAA, SOC 2) actually ask for: not "what did the agent do," but "prove the record is faithful."

## The model

1. **Claims are falsifiable or they're just prose.** When an agent (or its harness) reports a completed change, it appends a structured claim to the ledger: a file changed, a path moved, a metric holds, a command passes. Free-form prose is recorded but never counted as proof.
2. **Verification is deterministic.** `showwork verify` re-checks every claim against the filesystem and locked commands. No LLM judges an LLM.
3. **The exit gate refuses false dones.** `showwork finish --status ok` verifies the session's own claims first. If any is RED, the close is refused (exit 2). Fix it, retract it, or close as `blocked`. The bypass is stamped on the record either way.
4. **The ledger is append-only.** Corrections are retraction records that reference the original claim. History is never rewritten.
5. **Undeclared damage is not GREEN.** `session.start` snapshots the project tree. `verify` and `finish` go RED if a file that existed at start is deleted or changed and no active claim named that path. That is issue #64.

## Quickstart

Paste this into an empty directory. The first close is supposed to fail.
The refusal is the product.

```bash
pip install showwork
```

`python -m showwork` is the same CLI after install. Use it if `showwork` is not on PATH.

```bash
showwork start --session first-look --agent cursor
showwork claim --session first-look --claim "config/api.yaml exists" --type file_exists --path config/api.yaml
showwork finish --session first-look --status ok
```

```
claims: RED (0/1 verified)
REFUSED: a clean close requires this session's claims to verify.
```

Then make the claim true and close clean:

```bash
python -c "from pathlib import Path; p=Path('config'); p.mkdir(exist_ok=True); (p/'api.yaml').write_text('timeout: 30\n')"
showwork retract --session first-look --claim "config/api.yaml exists" --reason "file was not written yet"
showwork claim --session first-look --claim "config/api.yaml exists" --type file_exists --path config/api.yaml
showwork finish --session first-look --status ok
```

```
claims: GREEN (1/1 verified)
session.finish recorded: first-look
```

Put the same loop on your own repo in one command:

```bash
showwork init
```

That writes a Cursor rule, a Claude Code Stop hook, and `docs/ci/showwork-verify.yml`.
Copy the YAML into `.github/workflows/` when you are ready to gate CI.
A Cursor walk is in [docs/walks/cursor.md](docs/walks/cursor.md).

Audit any day or any session after the fact:

```bash
showwork verify --date 2026-07-09
showwork verify --session first-look --json
```

## Check types

| type | asserts |
|---|---|
| `file_exists` | a file is present |
| `file_contains` | a regex matches (or is absent from) a file |
| `path_moved` | source is gone, destination exists |
| `frontmatter` | a YAML frontmatter field equals a value |
| `glob_count` | a glob's match count satisfies `== >= <= > <` |
| `command` | a **locked** command exits as expected (`python <script under project root>` only; no shell, no metacharacters, no escape) |
| `http_probe` | an HTTP(S) endpoint returns an exact status and optional body substring, with redirects disabled |
| `git_state` | the local tree is clean/dirty, on an exact branch, or at a commit prefix |

Vacuous checks are rejected, not blessed: a regex that matches the empty string, or a glob count that's always true (`>= 0`), returns an error instead of a pass. A checker that lets an agent record a bogus "done" is worse than no checker.

`http_probe` uses a fixed timeout and response-size cap. Network checks are
disabled by default in the GitHub Action for fork safety; enable them only for
trusted same-repository workflows with `allow-network: true`.

`git_state` runs fixed, non-shell Git queries against the declared project root.
It accepts at least one of `clean`, `branch`, or a seven-plus-character commit
prefix, so an empty check cannot pass as proof.

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

**Concurrent sessions do not share a file.** Two agents with distinct session
slugs (`cursor-fix-nav`, `codex-fix-nav`) write `.showwork/sessions/<id>.jsonl`
and `.showwork/claims/<id>.jsonl`. Git then merges two paths, not one hash
chain. Worktree checkouts keep receipts in that worktree so the branch carries
them. Reuse of one slug is still one writer; `merge=union` remains only for
leftover shared files. The audit still accepts a fork inside one file as GREEN
and goes RED on modification, deletion, or reorder. Repos that forbid
concurrency can pass `showwork audit --strict`. Rationale:
[docs/concurrency.md](docs/concurrency.md).

## Gate your CI on receipts

```yaml
- uses: bmdhodl/showwork/actions/verify@v0.3.0
  with:
    session: my-agent-session
```

Fails the job on a chain break, failed claims, a missing exit-gate close, or
a `--no-verify` bypass stamp, and renders the receipt into the step summary.
Fork-safe by default ([docs/ci.md](docs/ci.md)).

## Wrap any agent, no integration

```bash
showwork run --session fix-123 --gate -- codex exec "fix the failing test"
```

Observe mode is exit-transparent; `--gate` exits 2 when the command reports
success but the receipts are RED ([docs/adapters.md](docs/adapters.md)).

Bound an unattended command by wall clock:

```bash
showwork run --session fix-123 --gate --max-seconds 1800 -- codex exec "fix the failing test"
```

The wrapper terminates the child and records `budget_exceeded` when the time
envelope trips. Tool-call ceilings remain an integration concern because a
generic subprocess wrapper cannot see an agent's internal tool stream; use the
`showwork.RunBudget` API or the live hook adapter for that dimension.

## The False Done Rate

Receipts make a new number measurable: **how often agents claim work that is
not backed by reality.** Day-0 on our own production fleet: **21 sessions,
42.9% contained a false done, every one caught by the gate.** Methodology
pre-registered, corpus honesty rules included:
[docs/false-done-rate.md](docs/false-done-rate.md).

## Evidence packs for auditors

`scripts/evidence_pack.py` maps a date range of chain-verified receipts to
EU AI Act Art. 12/26(6), SOC 2, and HIPAA record-keeping language, and
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

## Where this sits

The 2026 survey [*Code as Agent Harness*](https://arxiv.org/abs/2605.18747) (Ning et al., UIUC / Meta / Stanford) argues that code has become the runtime medium agents operate inside rather than the artifact they produce, and it names the layer showwork implements. Its §3.4.4, "Verification through Deterministic Sensors," states the rule plainly: deterministic sensors are "reproducible enough to serve as control signals," and agentic critics "should interpret sensor outputs rather than replace them." Same commitment as *no LLM judges an LLM*, reached from a literature review instead of from an incident.

Two of the survey's open problems are the ones this package exists for:

- **§5.2.1 Harness-Level Evaluation and Oracle Adequacy.** End-task success "conflates the capabilities of the base model, the quality of the harness, the reliability of tools, the informativeness of feedback, and the difficulty of the environment." The [False Done Rate](docs/false-done-rate.md) measures the substrate rather than the model.
- **§5.2.5 Human-in-the-Loop Safety and Accountability as Harness State.** Safety "cannot be delegated to the base model or encoded only as a natural-language instruction." An append-only ledger with a refusing exit gate makes accountability a piece of harness state instead of a sentence in a prompt.

The survey predates this package and does not cite it. It is context for the problem, not an endorsement of the solution.

## What showwork is not

- Not observability. Traces show what happened; showwork proves what was *claimed* to have happened.
- Not agent testing. Test frameworks check behavior pre-deployment; showwork verifies outcomes at runtime, every session.
- Not an LLM judge. Every check is deterministic and reproducible, which is what makes the record audit-grade.

## Roadmap

- More coding-agent adapters (OpenAI Agents SDK / LangGraph middleware)
- Event stream + point-in-time replay
- More check types as real outcome gaps emerge
- False Done Rate at study scale: controlled task sets, per-model corpora
- Detached signing of ledger heads (external timestamp anchoring)

## License

MIT
