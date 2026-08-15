# showwork date-sample selection readout r9

Date: 2026-08-15  
Scope: existing date-bounded verification commands and disposable synthetic
fixtures. This is an interpretation readout only. It adds no dashboard,
filter, status vocabulary, reliability claim, adoption claim, schema, or
release behavior.

## Result

KEEP the existing date command, but exclude missing, empty, and otherwise
vacuous points from a health trend. A `GREEN 0/0` result proves that the
selected range contained no checkable records; it is not a positive health
observation. A non-green date is also not a trend point until its gap or
retraction state is explained.

## Evidence

The readout used `python -m showwork.cli verify --date <date> --json
--no-report` against the repository ledger, plus the existing disposable
human-authority fixture for an isolated retracted-only session.

| Sample | Observed command result | Safe interpretation |
|---|---|---|
| 2026-07-11 | Exit 0; `GREEN`; 1/1 | Valid non-empty point; one verified claim is present. |
| 2026-08-07 | Exit 2; `RED`; 3/5, one skipped record, one gap | Exclude from a positive trend; the missing workflow assertion must remain visible. |
| 2026-08-10 | Exit 3; `YELLOW`; 2 records, 0 passed; one skipped/retracted record and one command error; one gap | Exclude; this is an unresolved mixed state, not a health score. |
| 2026-08-14 | Exit 0; `GREEN`; 11/11 | Valid non-empty point. |
| 2026-08-15 | Exit 0; `GREEN`; 63/76, with 13 skipped/retracted records and no gaps | Usable only as a qualified point: report the verified and skipped/retracted counts together. |
| 2026-08-16 | Exit 0; `GREEN`; 0/0 | Missing/future range in this corpus; exclude as vacuous. |
| 2099-01-01 | Exit 0; `GREEN`; 0/0 | Future empty range; exclude as vacuous. |
| Isolated `retracted-run` fixture | Exit 0; `GREEN`; 1 record, 0 passed, status `skipped`, detail `retracted: fixture claim was not true` | Lifecycle behavior is observable, but it is not a positive reliability observation. |

Evidence paths:

- `K:\showwork\.showwork\claims-2026-08-07.jsonl`
- `K:\showwork\.showwork\claims-2026-08-10.jsonl`
- `K:\showwork\.showwork\claims-2026-08-14.jsonl`
- `K:\showwork\.showwork\claims-2026-08-15.jsonl`
- `C:\Users\patri\AppData\Local\Temp\showwork-governance-human-authority-20260815-r1`
- `C:\Users\patri\Documents\Obsidian Vault\Reports\Research\showwork-rolling-health-trend-readout-2026-08-15.md`

## Interpretation rule

For a trend readout, retain the date and exact command result, then classify
the sample before comparing it:

1. `GREEN` with at least one verified, non-retracted claim is a qualified
   observation.
2. `GREEN 0/0`, an out-of-range date, or a date containing only skipped or
   retracted records is a missing/vacuous observation.
3. `YELLOW` or `RED`, a gap, or a command error is an unresolved observation.

This rule is for report interpretation. It does not change the CLI's existing
status or invent a new status category.

## Decision

KEEP the current verifier and report-only classification. Do not turn missing
or vacuous points into a reliability, compliance, or adoption signal. No
dashboard, date filter, schema change, migration, re-chain, public copy, or
release follows from this sample.
