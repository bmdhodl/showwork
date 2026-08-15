# showwork rolling health-trend readout

Date: 2026-08-15
Scope: read-only comparison of existing audit and verify commands. No
dashboard, status vocabulary, trend claim, production code, public copy,
legal, release, or adoption change.

## Result

KEEP the existing commands. The sampled dates are useful for operations, but
this self-generated history is not a reliability or adoption trend. The
commands expose enough detail to keep chain health, current claim health, and
empty-date behavior separate.

## Date matrix

Commands:

```text
python -m showwork.cli verify --date YYYY-MM-DD --json --no-report
python -m showwork.cli audit --json
python -m showwork.cli audit --strict
```

| Date/scope | Claim records | Chain state from audit | Verify exit | Verify result | Safe interpretation |
|---|---:|---|---:|---|---|
| 2026-07-11 | 1 | YELLOW, 1 pre-chain | 0 | GREEN 1/1 | One old claim checks now; chain integrity is not established for that file |
| 2026-08-07 | 6 | GREEN, 6/6 chained, no forks | 2 | RED 3/5, 1 skipped, 1 gap | Chain is intact but one historical workflow-copy claim fails now |
| 2026-08-14 | 11 | GREEN, 11/11 chained, no forks | 0 | GREEN 11/11 | Bounded day is chained and currently verifies |
| 2026-08-15 | 99 | GREEN, 99/99 chained, 1 accepted fork | 0 | GREEN 63/76, 13 skipped/retracted, 0 gaps | Current claims recheck green after preserving retractions |
| 2026-08-16 | 0 selected | No date file | 0 | GREEN 0/0 | Missing date is empty, not evidence |
| Whole corpus | 414 | YELLOW, 382/414 chained, 43 forks | n/a | n/a | Legacy pre-chain history and accepted branches remain visible |

The 2026-08-07 gap is `/runs-on:.ubuntu-latest/ NOT in .github/workflows/ci.yml`;
the file is not chain-tampered. Strict whole audit exits 2 because it forbids
forks, while ordinary audit exposes the forks and remains the operational
integrity view.

## Missing-date behavior

`verify --date 2026-08-16 --json --no-report` returns exit 0 with
`GREEN (0/0)`. That is the same vacuous shape as an empty evidence pack and
must not be placed on a positive health trend.

## Decision

NO CHANGE. Keep date-scoped matrices as internal readouts. Do not add a
dashboard, new status, or reliability/adoption trend claim from these counts.

Reference framing: [NIST AI RMF](https://www.nist.gov/itl/ai-risk-management-framework)
is voluntary risk-management guidance, not a health metric or certification.
