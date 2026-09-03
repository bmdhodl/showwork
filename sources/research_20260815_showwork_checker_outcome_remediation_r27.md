# Checker outcome remediation readout — r27

Date: 2026-08-15  
Scope: report-only disposable fixtures; no checker implementation, status
vocabulary, renderer, SPEC, schema, or public prose change.  
Source card: `checker-outcome-remediation-readout-20260815-r27.md`

## Harness finding preserved before correction

The first inline fixture was not valid product evidence. The default Python
process imported the editable package at
`<showwork-checkout>\src\showwork`, not this checkout's
`K:\showwork\src\showwork`. The two `checks.py` files had different SHA-256
hashes. That process reported `http_probe` and `git_state` as
`unknown check type`, even though the K checkout maps both types in
`CHECKERS`. The same first run also failed to remove its disposable Git
repository: Windows denied unlinking a read-only `.git/objects` file during
`shutil.rmtree`. These are harness/import and cleanup findings, not checker
behavior findings. The failed fixture was discarded only after exact-path
permission normalization and removal.

## Corrected fixture boundary

The corrected process set `PYTHONPATH=K:\showwork\src` and confirmed that the
imported package was `K:\showwork\src\showwork\__init__.py` with all eight
current checkers: `file_exists`, `file_contains`, `path_moved`, `frontmatter`,
`glob_count`, `command`, `http_probe`, and `git_state`. It used temporary roots,
a loopback HTTP server, and a temporary Git repository. The repository was
removed after normalizing temporary file permissions. No public URL or real
checkout state was used.

## Checker-outcome matrix

`rendered` is the existing `render_report` session header for the single-case
fixture. `RED` means the claim was proved false. `YELLOW` means the claim was
not fully verified because the input was malformed, vacuous, or blocked by
policy. `skipped` is recorded prose without a falsifiable check and does not
prove an outcome.

| checker case | raw status | detail class | session verdict | safe remediation |
|---|---|---|---|---|
| file exists, present | pass | path exists | GREEN | retain the checked path |
| file exists, missing | fail | missing file | RED | create/locate the artifact, then re-run |
| file exists, `../` escape | fail | unsafe path | RED | keep evidence inside the project root |
| file contains, match | pass | regex found | GREEN | retain a specific non-vacuous pattern |
| file contains, mismatch | fail | regex absent | RED | inspect the artifact or retract the claim |
| file contains, `.*` | error | vacuous regex | YELLOW | replace with a specific pattern |
| path moved, source gone/destination present | pass | move proven | GREEN | retain both path assertions |
| path moved, source remains | fail | source still exists | RED | complete the move or retract |
| frontmatter, field equals | pass | scalar matches | GREEN | retain field/value check |
| frontmatter, field absent | fail | field missing | RED | add/correct frontmatter or retract |
| glob count, exact count | pass | count matches | GREEN | retain bounded count |
| glob count, `>= 0` | error | vacuous count | YELLOW | use a meaningful bound |
| command, locked Python script | pass | exit/stdout match | GREEN | retain the locked command |
| command, `SHOWWORK_NO_COMMANDS` | error | policy blocked | YELLOW | run only in an allowed trusted context; do not treat as pass |
| command, shell metacharacter | error | unsafe command | YELLOW | use a locked Python script, not a shell expression |
| HTTP probe, loopback 200/body match | pass | response match | GREEN | retain exact local endpoint evidence |
| HTTP probe, body mismatch | fail | expected body absent | RED | inspect endpoint or retract |
| HTTP probe, `SHOWWORK_NO_NETWORK` | error | policy blocked | YELLOW | do not infer network proof from a blocked check |
| Git state, disposable repo clean/main | pass | state matches | GREEN | retain exact state assertions |
| Git state, disposable repo dirty | fail | clean assertion false | RED | clean/commit the intended state or retract |
| Git state, no assertions | error | empty/non-vacuous input | YELLOW | provide clean, branch, or commit |
| record with no check | skipped | non-falsifiable prose | GREEN header, no proof | add a deterministic check before claiming completion |
| malformed non-object check | error | check shape invalid | YELLOW | correct the JSON object shape |

The corrected run compared each raw result with the existing rendered header;
it did not modify the renderer. The distinction that matters for a reader is
“proved false” (`fail`/RED) versus “not verified” (`error`/YELLOW or skipped
prose). Policy-blocked command and HTTP checks are not failures of the claimed
artifact; they are unavailable evidence and must not be silently promoted to
GREEN.

## Remediation and evidence gaps

The matrix supports safe next actions only. It does not justify renaming
statuses, adding a blocked state, changing checker semantics, or claiming
human/AI comprehension. The first-run import path is an environment setup gap
that must be controlled in future test commands; the Windows ACL behavior is a
fixture-cleanup gap. Neither is evidence of public package compatibility or
adoption. Network and Git observations were local/disposable only.

## Boundary

No checker, schema, report formatter, SPEC, adapter, signer, timestamp,
public copy, release, or real Git state changed.
