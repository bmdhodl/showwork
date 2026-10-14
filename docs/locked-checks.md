# Locked checks and weakened tests

An agent can make "all tests passing" true by moving the finish line:
deleting a failing test, marking it skipped, dropping an assertion, or
editing the script that runs the suite. Two features refuse that close
([#179](https://github.com/bmdhodl/showwork/issues/179)).

## Owner steps

Run these before the agent starts, from a committed tree:

```bash
showwork start --session fix-nav --agent cursor
showwork require --session fix-nav --id suite --scope behavior --description "the suite passes" --type command --command-arg python --command-arg scripts/run_tests.py --expect-exit 0 --stdout-contains passed
showwork require --session fix-nav --id intact --scope artifact --description "no test was weakened" --type tests_intact --path tests
showwork lock --session fix-nav --path tests/conftest.py --path pyproject.toml
```

`lock` prints each locked file and the requirements digest. Commit the
`.showwork/` receipt, or keep the digest, before you hand off.

The agent then works and records claims as usual. It cannot add requirements
to a locked session: `require` is refused, and a requirement record appended
by hand fails the lock digest.

## What refuses the close

| Agent action | Refusal reason | Finding |
| --- | --- | --- |
| Edits `scripts/run_tests.py`, even with a claim naming it | `locked_checks_changed` | `locked check file changed: scripts/run_tests.py` |
| Deletes or adds a file under a locked glob | `locked_checks_changed` | `locked check file deleted: ...` / `new file under a locked path: ...` |
| Adds a requirement after the lock | `locked_checks_changed` | `requirement declared after the lock: ...` |
| Deletes a test file | `tests_weakened` | `test file deleted: tests/test_calc.py (2 tests)` |
| Deletes or renames a test | `tests_weakened` | `test deleted: tests/test_calc.py::test_add_negative` |
| Adds `@pytest.mark.skip`, `xfail`, `pytestmark`, `unittest.skip`, `pytest.skip()` | `tests_weakened` | `test newly skipped or xfail: ...` |
| Removes an `assert`, `assert*` call or `pytest.raises` | `tests_weakened` | `assertions fell from 2 to 1: ...` |
| Drops literal parametrize cases | `tests_weakened` | `parametrize cases fell from 3 to 1: ...` |

`finish` exits `2`, prints `REFUSED ... (locked_checks_changed)` or
`(tests_weakened)`, and appends a `session.finish.refused` event with the
findings. A session that adds tests, adds assertions and leaves locked files
alone closes with `Outcome: VERIFIED`; its finish event carries
`lock_check.status: intact`.

`gate` reruns both comparisons, so a locked file changed after the close
still fails CI. A `--base` excuses no lock finding. If the base changed a
locked file, the finish line moved: start a new session and lock again.

## What it compares

`tests_intact` pins `base` to a full commit ID when the requirement is
declared (`--commit REV`, default `HEAD`). It reads test files at that
commit from Git objects, so uncommitted edits made before the declaration
are not part of the base. It parses each `test_*.py` or `*_test.py` file
with `ast` and compares every base test by name. Nothing is imported or run.
In CI, fetch enough history to contain the base commit.

The lock hashes the script of each `command` requirement and every file a
`--path` glob matches. Globs follow the [snapshot exclusion](snapshot-exclusions.md)
rules; a glob that matches nothing is refused.

## Limits

- Counts are not meaning. A test rewritten to assert something weaker with
  the same number of assertions passes, as does an assertion weakened in an
  unchanged helper or an early `return` before the assertions.
- Pytest and unittest naming conventions only. Custom `python_functions`,
  dynamic parametrization and `pytest_generate_tests` are counted as one case.
  Markers applied through an alias (`slow = pytest.mark.skip`) are missed;
  deselection through `-k`, `-m` or `addopts` is caught only when the runner
  and configuration are locked.
- A renamed or moved test reads as a deletion. Declare a new session with a
  new base after an intentional rename.
- Conftest hooks, fixtures and plugins are not test files. Lock them with
  `--path`.
- The lock is a record in the agent-writable ledger. It catches changes after
  the lock, and the hash chain catches edits to committed history. It does not
  stop an agent that never locks, or that rewrites a whole unanchored session
  file. Anchor the lock by committing it before handoff or by publishing the
  digest `lock` prints.
- Fails-on-base proof for a new regression test is not part of this feature.
