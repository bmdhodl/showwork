# Stale historical receipt claims: exact mapping and correction decision

## Scope

This report reconciles the 22 active command claims that made the remote
integrity check RED. It is a receipt-only repair. It changes no product
behavior, parser, schema, workflow, runner, package, public copy, or release
state.

The source records are the exact JSONL lines in
`.showwork/claims-2026-08-15.jsonl`. The direct current evidence is:

```text
python scripts/run_tests.py
242 passed in 18.19s
exit 0
```

The historical records were valid observations at their assertion times, but
their live `command` checks re-run the command against the current checkout.
Their exact `stdout_contains` values (`232 passed` or `234 passed`) are now
false because the suite has grown to 242 tests. That is receipt-check drift,
not evidence that the historical test runs never passed.

## Exact claim-to-source mapping

Every row below is one active record and one remote RED gap. The line number is
the source line before the append-only repair.

| source line | session | claim | stale check |
| ---: | --- | --- | --- |
| 36 | `git-state-2026-08-15` | `git_state full test suite passes` | `232 passed` |
| 40 | `release-packaging-metadata-2026-08-15` | `full test suite passes after packaging cleanup` | `232 passed` |
| 42 | `continuous-development-2026-08-15` | `full test suite passes` | `232 passed` |
| 44 | `receipt-refresh-2026-08-15` | `receipt refresh test suite passes` | `232 passed` |
| 46 | `http-probe-2026-08-15` | `HTTP probe full test suite passes` | `232 passed` |
| 50 | `research-next-adapter-2026-08-15` | `research documentation leaves the suite green` | `232 passed` |
| 56 | `clean-room-action-2026-08-15` | `full repository suite passes after clean-room fixture changes` | `232 passed` |
| 59 | `attestation-policy-2026-08-15` | `the repository test suite remains green` | `232 passed` |
| 62 | `fork-aware-receipt-export-2026-08-15` | `the full repository suite passes after the fork-aware export read-only audit` | `232 passed` |
| 65 | `evidence-pack-red-refusal-2026-08-15` | `the full repository suite passes after the evidence-pack read-only fixture audit` | `232 passed` |
| 68 | `evidence-pack-demand-recheck-2026-08-15` | `the repository suite remains green after the demand recheck` | `232 passed` |
| 71 | `public-proof-reader-matrix-2026-08-15` | `the repository suite passes after the reader matrix research` | `232 passed` |
| 76 | `ai-proof-query-coverage-2026-08-15` | `the repository suite passes after AI query coverage research` | `232 passed` |
| 79 | `fork-provenance-copy-contract-2026-08-15` | `the repository suite passes after provenance wording research` | `232 passed` |
| 88 | `governance-evidence-2026-08-15` | `full repository suite passes after governance reports` | `232 passed` |
| 98 | `integrity-follow-up-evidence-2026-08-15` | `full repository suite passes after integrity follow-up reports` | `232 passed` |
| 108 | `r8-refill-evidence-2026-08-15` | `full repository suite passes after r8 reports` | `232 passed` |
| 122 | `r9-queue-closeout-and-tests` | `full direct and wrapper test suites report 232 passed` | `232 passed` |
| 135 | `r10-queue-closeout-and-tests` | `full direct and wrapper test suites report 232 passed after r10 artifact creation` | `232 passed` |
| 138 | `benchmark-verification-overhead-20260815` | `full direct and wrapper suites pass after append-cache change` | `234 passed` |
| 153 | `package-proof-release-gate-r12-20260815` | `full suite remains green after report-only r12 work` | `234 passed` |
| 164 | `package-provenance-evidence-pack-crosswalk-r13-20260815` | `full suite remains green after report-only r13 work` | `234 passed` |

The failed remote receipt `31915190394` and its later sampled failure
`31918517487` both reported 22 gaps. Their failed rows are exactly this set,
not a second product or runner failure.

## Contract decision

Append-only correction is authorized and truthful here:

1. Preserve every original record and its historical count.
2. Append one retraction per original session/claim key, with the reason that
   the exact count is stale under the current verifier.
3. Append a corrected command claim in a new repair session using
   `expect_exit: 0` and `stdout_contains: "passed"`. This follows the
   command-check shape in `SPEC.md`; it proves a successful suite output
   without binding future receipt verification to a historical test count.
4. Keep the current exact observation (`242 passed`) in this report and in the
   test receipt; the flexible checker is not an adoption, performance, or
   release claim.

The retractions are not a history rewrite and do not turn the remote gate
green by assertion. The corrected claims must still execute under the CI
receipt verifier. The current local command passed, but remote CI remains
unverified while the sole matching self-hosted runner is offline.

## Explicit boundaries

- No source behavior, test, schema, parser, workflow, runner, or package code
  changed.
- No public URL, PyPI publish, tag, GitHub release, or adoption claim was
  made.
- The runner condition remains separate: six CI runs are queued behind the
  offline `fluarmn-wsl-showwork` runner.
- Release eligibility remains owner-gated and RED until a remote run actually
  completes with the repaired receipt set and all required release checks.
