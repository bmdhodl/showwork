# Review whether acceptance tests cover the application

A passing declared check does not prove that the requirement inventory covers
the request. A fixture can quietly do the application's missing work. Review
that boundary before using a successful showwork close to make a delivery claim.

The [runnable persistence example](../examples/acceptance-review/acceptance.py)
uses a small settings application, its public write/read API, fresh instances and
a second process. It needs only Python and a new empty folder. No BMD account,
provider, database service or model is needed.

```text
python examples/acceptance-review/acceptance.py NEW_EMPTY_FOLDER
python examples/acceptance-review/acceptance.py --read-existing NEW_EMPTY_FOLDER
python examples/acceptance-review/acceptance.py --mutation empty-write OTHER_EMPTY_FOLDER
python examples/acceptance-review/acceptance.py --mutation cache-only THIRD_EMPTY_FOLDER
```

The correct implementation passes and leaves settings written by the application.
The no-op write mutation fails on the immediate read. The cache-only mutation
passes that read but fails when a new instance reopens the store. A fresh process
reading absent or incorrect output fails and writes nothing. Use a new empty
folder for each run: reopening is an explicit acceptance phase, not silently
resetting output until it happens to pass.

| Scenario | Application behavior | Fixture supplies | Counterexample | Expected label before runs |
| --- | --- | --- | --- | --- |
| Correct store | Write/read/reopen/update through public API | Empty root and input strings | Removing write breaks the same assertion | Pass for this declared behavior |
| Empty write | Write body removed | Same inputs; no output seeding | Immediate read is absent | Fail |
| Cache-only write | In-memory value only | Same inputs; new instance | Reopened read is absent | Fail |
| Read existing in a new process | Read application-produced persisted output | Root path only | Empty or incorrect output | Fail without writes |

The example's test author reviewed these expected labels before executing them.
They are authored controls, not independent customer failures. Review status:
**self-authored; independent fixture/test adequacy review not performed**. A
maintainer or independent reviewer must inspect the production path, fixture
inputs and mutations before marking that boundary reviewed. An automated code
review or a GREEN ledger does not silently change this status.

For a real contribution, put the requested behavior and its acceptance check in
named requirements before claims. Identify which dependency inputs are mocked,
which API produces the output, and which fresh reader consumes it. Run the same
assertion after replacing the relevant production behavior with an empty or
broken implementation. Retain the observed failure, repair and successful rerun.
Record who authored and independently reviewed the requirement and test, what
they reviewed, and what remains unreviewed in the existing PR/report. Do not add
an automatic coverage score or a second truth store.

Review effort for this task is **unmeasured**; there was no observed human review
session to time. The recipe covers this small string-settings contract only.
It does not cover concurrency, crash recovery, schema migration, hostile input,
all product requirements or real-user adequacy. Its explicit acceptance predicates
also execute under Python optimization; `-O` cannot turn a broken implementation
or missing output into success.

## Compare one shared test suite against a broken fixture and its repair

The optional [comparison runner](../examples/acceptance-review/compare.py)
automates this narrow check for stdlib `unittest.TestCase` suites. Run it from
a source checkout; it imports that checkout's process runner. It adds no
runtime dependency and changes no ledger format or default gate.

```text
python examples/acceptance-review/compare.py --broken examples/acceptance-review/fixtures/broken --repaired examples/acceptance-review/fixtures/repaired --tests examples/acceptance-review/fixtures/checks --output control-result.json
```

The supplied example calls the application's save/load functions and reads
the persisted value in a fresh process. The broken implementation's save is
empty. The repaired implementation writes the value. The test fixture supplies
an empty temporary directory and an input string, never the expected file.

Both implementations run against copies of the same tests in separate fresh
temporary directories, which are cleaned after each run. Inputs stay in place;
there is no in-place mutation/restore cycle. Fixture directories must contain
only the small inputs you intend to execute. Symlinks and Windows reparse
points are refused; `.git`, bytecode and `__pycache__` are excluded. `_checks`
is reserved for the shared suite. Output must be outside the input directories.

| Result | Exit | Meaning |
| --- | --- | --- |
| `SENSITIVE` | 0 | At least one test assertion rejected the broken fixture; the same test inventory passed on the repair. |
| `INSENSITIVE` | 1 | Both fixtures passed. The checks did not expose this supplied defect. |
| `REPAIR_FAILED` | 1 | The repair still has an ordinary assertion failure. |
| `INCONCLUSIVE` | 2 | Setup/teardown error, import/syntax error, timeout, missing observation, no tests, skips, expected failures or differing test inventories prevented the comparison. |

`--timeout` is a positive finite number of seconds per child, default 30.
Timeout cleanup uses showwork's existing process-tree handling. This bounds
ordinary children, not processes that deliberately escape that boundary.
The report keeps the actual child exit codes, input/test/runner hashes,
interpreter version, output hashes and bounded diagnostic tails.

These are trusted project tests running with your privileges, **not sandboxed
code**. A child can still access paths outside its copied directory. Test code
can forge its own observations. The shared test source is fixed between runs,
but it can branch on the fixture. An assertion failure can be unrelated to the
intended defect. A useful result therefore remains a signal about one chosen
counterexample, not proof of test quality, independence or full requirements.
The report always leaves independent review unestablished; keep the named
reviewer and scope in the existing PR/report rather than infer them from exit 0.

For showwork acceptance, declare a behavior `command` that runs this script
with `expect_exit=0` and `stdout_contains=SENSITIVE` before claiming completion.
Use an output beneath your session's artifact directory and explicitly claim
that file too. A `file_exists` claim on the report alone is only an artifact
observation; it must not replace rerunning the comparison. A project test
runner remains responsible for all other declared behavior requirements.
