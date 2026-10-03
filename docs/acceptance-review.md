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
