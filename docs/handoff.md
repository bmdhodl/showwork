# Codex to Claude handoff

A later session can read a receipt. It cannot inherit a close. The writer
and the reader are two processes. They share files, not memory.

This walk uses showwork 0.6.4. Check that pin before you trust a checkout:

```bash
python -m showwork doctor
```

```powershell
python -m showwork doctor
```

## Record, then read

The writer is the Codex step. It declares a file check and a command check.
The command limit is the timeout stored on the finish event. The writer
saves `decision.json` after that receipt. A later supersede edits the
pointer. It does not rewrite the code snapshot. The reader is the fresh
process. Claude can run that same command. The reader calls `receipts`
only. It does not run `verify` or `gate`, and it does not execute the
recorded command.

```bash
python examples/sw-06-handoff/write_codex.py demo-handoff
python examples/sw-06-handoff/read_claude.py demo-handoff --session handoff
```

```powershell
python examples/sw-06-handoff/write_codex.py demo-handoff
python examples/sw-06-handoff/read_claude.py demo-handoff --session handoff
```

The reader prints one JSON object. `approval` is false. A passing file check
on that read still does not authorize a merge or a clean close.

The writer also records session `fileonly`. That session has the file check
only. A green read of `fileonly` still has `approval` false.

A human can open the same files with no agent client:

- `demo-handoff/DECISION.md`
- `demo-handoff/decision.json`
- `demo-handoff/.showwork/sessions/handoff.jsonl`
- `demo-handoff/.showwork/claims/handoff.jsonl`

`DECISION.md` is the governing decision. A model summary is not a decision.

This command is the same read the script uses:

```bash
python -m showwork receipts --root demo-handoff --session handoff --json
```

```powershell
python -m showwork receipts --root demo-handoff --session handoff --json
```

Run `gate` only when you intend to execute the command check. The reader
does not do that for you.

## What a later session must see

Change one thing, then run the reader again.

- Change `check.py`. The view is stale. The old command does not run.
- Change `note.txt`. The file check fails on the read.
- Delete `.showwork`. The view is unknown.
- Set `superseded_by` in `decision.json`. The old close is not approval.
- Ask for a session id the decision does not name. The other session is not reused.

[Return to the documentation index](README.md).
