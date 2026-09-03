# showwork trend-claim language boundary r10

Date: 2026-08-15  
Scope: wording derived from the r9 date-state matrix and existing local
verification outputs. This is an internal reader contract. It does not edit
README, CLI output, dashboards, public copy, status vocabulary, or release
behavior.

## Result

KEEP qualified date language only. Every trend sentence must name its date or
range, counts, and state. A few `GREEN` checks do not support a reliability,
compliance, security, or adoption claim. Missing, vacuous, skipped/retracted,
YELLOW, RED, gap, and command-error samples must be described as such or
excluded from a positive trend.

## Wording matrix

| Sample state | Allowed wording | Conditional wording | Forbidden wording |
|---|---|---|---|
| Qualified non-empty GREEN | “On 2026-08-14, bounded verification returned `GREEN` for 11/11 records.” | “This is one qualified point-in-time observation; include the date, range, check scope, and any skipped/retracted count.” | “showwork is 100% reliable,” “all work is verified,” or “the system is compliant.” |
| Multiple qualified points | “The sampled dates 2026-07-11 and 2026-08-14 were qualified non-empty GREEN observations: 1/1 and 11/11.” | “The sample shows these observed points; it is not a population reliability rate or adoption measure.” | “The trend proves reliability,” “zero false dones,” or “production adoption.” |
| GREEN 0/0 or missing/future date | “No records were selected for 2099-01-01; the result is `GREEN 0/0`.” | “This is empty/vacuous and is excluded from health interpretation.” | “The date was healthy,” “nothing failed,” or “verification was complete.” |
| Skipped/retracted-only | “The selected range contains a skipped/retracted record; the retraction remains visible.” | “Report the lifecycle state, but do not count it as current positive proof.” | “The skipped claim passed,” “the task was completed,” or “a human approved the retraction.” |
| YELLOW or gap | “The selected range is `YELLOW` and has an unresolved gap; no positive trend point is claimed.” | “A later rerun may explain the gap, but it does not rewrite this observation.” | “Mostly green,” “healthy despite the gap,” or “compliant.” |
| RED or tampered chain | “Verification refused: the selected evidence is `RED` and is not usable as a positive proof pack.” | “The failure is evidence about this fixture or range, not a product-wide rate.” | “The pack proves the event,” “the chain is authoritative,” or “the failure can be ignored.” |
| Command error | “The command check errored; the predicate is unverified.” | “The error may be a fixture or command issue; do not reinterpret it as success.” | “The command probably passed,” “the date is green,” or any inferred result. |

## Exact sample anchors

- `2026-07-11`: exit 0, `GREEN`, 1/1.
- `2026-08-07`: exit 2, `RED`, 3/5, one skipped record and one gap.
- `2026-08-10`: exit 3, `YELLOW`, two records, no passed records, one
  skipped/retracted record, one command error, and one gap.
- `2026-08-14`: exit 0, `GREEN`, 11/11.
- `2026-08-15`: exit 0, `GREEN`, 63/76, with 13 skipped/retracted records
  and no gaps at the time of the r9 snapshot.
- `2026-08-16` and `2099-01-01`: exit 0, `GREEN`, 0/0; both are excluded as
  empty/future ranges.

Evidence paths:

- `K:\showwork\sources\research_20260815_showwork_date_sample_selection_readout_r9.md`
- `K:\showwork\.showwork\claims-2026-08-07.jsonl`
- `K:\showwork\.showwork\claims-2026-08-10.jsonl`
- `K:\showwork\.showwork\claims-2026-08-14.jsonl`
- `K:\showwork\.showwork\claims-2026-08-15.jsonl`
- `<vault>\Reports\Research\showwork-date-sample-selection-readout-2026-08-15.md`

## Decision

KEEP this wording matrix as internal guidance. NO CHANGE to the public or AI
reader surfaces. The [NIST AI RMF](https://www.nist.gov/itl/ai-risk-management-framework)
is risk-management guidance, not a basis for turning local sample counts into
a compliance or reliability claim.
