# Contributing to showwork

showwork checks what an agent says it did. The same rule applies to anyone who
changes showwork itself. Every pull request carries its own proof.

## Every pull request carries a committed receipt

A pull request must include the committed `.showwork/` receipt for the session
that produced it. The receipt is one file per session under
`.showwork/sessions/`, plus that session's claims under `.showwork/claims/`.

**A pull request with no receipt is not reviewed.**

The receipt is the review marker. A reviewer reads it against the diff and asks
two questions. Does a check back every completed change the session claimed?
Does the diff match the files those checks name?

A pull request with no receipt was never verified. The diff alone does not say
whether anyone checked it, so a reviewer has nowhere to start.

Produce a receipt like this:

```bash
python -m showwork.cli start --session <agent>-<task-slug> --agent <claude-code|codex|cursor|gemini>

python -m showwork.cli require --session <agent>-<task-slug> \
  --id regression --scope behavior \
  --description "<the behavior your new test covers>" \
  --check-json '{"type":"command","argv":["python","scripts/run_tests.py"]}'

python -m showwork.cli claim --session <agent>-<task-slug> \
  --claim "<what changed>" --type file_contains \
  --path <file> --pattern "<regex>"

python -m showwork.cli finish --session <agent>-<task-slug> --status ok

git add .showwork/sessions/<agent>-<task-slug>.jsonl \
        .showwork/claims/<agent>-<task-slug>.jsonl
```

Check types are `file_exists`, `file_contains`, `path_moved`, `frontmatter`,
`glob_count`, `command`, `http_probe` and `git_state`. Pick one that can fail.

`finish` refuses with exit 2 when a claimed change is not real. Repair the code,
or retract the claim truthfully with `showwork retract`, then finish again. Do
not pass `--no-verify`. The bypass is stamped on the record and CI fails on it.
If you are truly stuck, close with `finish --status blocked` and say so in the
pull request.

Run the gate against the committed tree before you push:

```bash
python -m showwork.cli gate --session <agent>-<task-slug> --require-tracked
```

CI runs the same gate on the receipts your change ships.

## Agent-authored pull requests say so

An agent wrote much of this repository. That is the point, and hiding it is not.
Start the title with `agent:` when an agent produced the change. Then carry the
receipt like any other pull request.

showwork does not ban agent contributions. It asks them to show their work.

## Tests pass before the pull request opens

```bash
python scripts/run_tests.py
```

That script runs `pytest tests/ -q` and must exit 0. CI runs the same suite, the
receipt gate, and the integrity chain audit.

showwork has zero runtime dependencies and keeps it that way. Use the standard
library.

## One session, one receipt, one slug

A hash-chained ledger has exactly one writer. Two sessions that append the same
file fork the chain, and a fork costs real work to unwind.

- Give each session its own slug. Distinct slugs write distinct files.
- Stage only your own session's files.
- Never stage the rolling `.showwork/sessions.jsonl`. Every concurrent branch
  changes it, and it is the largest source of merge conflicts here.
- Never rewrite ledger history. A correction is a retraction record that points
  at the original claim.

Background: [docs/concurrency.md](docs/concurrency.md).

## SPEC.md is a contract

`SPEC.md` defines the ledger format. A format change needs a specification
update in the same commit. Treat it as a last resort, because it breaks every
existing reader until v1.

## Security

Report a security flaw privately. Do not open a public issue for one.

Use GitHub private vulnerability reporting on this repository: open the
**Security** tab, then **Report a vulnerability**. Give the version, the steps
to reproduce, and what an attacker gains. Wait for a reply before you make the
flaw public.

## Out of scope for a pull request

Publishing belongs to the owner. Do not publish to PyPI, tag a release, or
change repo visibility.

## License

Contributions ship under the [MIT License](LICENSE), the same license as the
rest of the repository.
