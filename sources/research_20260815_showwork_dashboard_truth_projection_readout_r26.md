# Dashboard truth-projection readout — r26

Date: 2026-08-15  
Scope: disposable/local HTML projection evidence; no dashboard, accessibility, or public-copy change  
Source checkout: `ac47b44`

## Input boundary

The current `showwork.dashboard.render` path consumes replay-summary JSON with
`thresholds` and `results`. It does not read `.showwork` ledgers, receipt
verdicts, timestamps, stale markers, or a redacted-source field. The fixture
therefore supplied synthetic replay rows representing those states and
recorded what the existing HTML actually projected. The extra
`redacted_source` marker was ignored by the renderer.

## State-to-rendered-text matrix

All seven disposable cases rendered through `scripts/render_dashboard.py` with
exit 0. The generated HTML was inspected as visible text after removing tags
and styles.

| synthetic state | visible projection | source/proof boundary |
|---|---|---|
| verified run (`stuck=false`) | `1 runs observed`, `0 interventions`, `No interventions.` | session and receipt identity were omitted; no `verified` label was rendered |
| RED/refused | intervention tag `refused` plus the supplied detail | shows a replay reason, not a chain verdict or durable refusal receipt |
| timeout | intervention tag `timeout` plus the supplied detail | does not say whether this was an HTTP timeout, process timeout, or proof timeout |
| missing | intervention tag `missing` plus the supplied detail | missingness is visible only because the fixture supplied an arbitrary reason |
| stale | intervention tag `stale` plus the supplied detail | no source age, revision, or freshness check is performed |
| empty | `0 runs observed`, `0 interventions`, `No interventions.` | an empty projection is not evidence that proof is verified or absent |
| contradictory detail | both `proof_state=RED` and `claims_verdict=GREEN` remain visible | arbitrary detail is escaped/rendered; no cross-field contradiction gate exists |

Rows marked `stuck=false` are omitted from the table even though they affect
the aggregate counts. Rendered intervention rows truncate session identity to
the first eight characters and do not display receipt paths, chain heads,
claim checks, or timestamps. The static note correctly says the view is
retroactive replay and not live kills, but that note does not establish proof
for any individual row.

## Ambiguity and safe follow-up

The current projection can improve readability of replay/intervention data,
but it is not a proof-state reader. Human or AI extraction must treat the
aggregate counters and intervention labels as replay metadata only. Any future
truth projection would need an owner-defined source-to-state contract,
identity and freshness fields, contradiction handling, and tests before UI or
public-copy work is authorized. This report proposes no such implementation.

The card names `tests/test_dashboard.py` as a secondary source, but that file
is absent in this checkout. The full repository test suite remains the
available gate; no dashboard-specific test file was invented for this
report-only readout.

## Verification

- Disposable dashboard CLI render: 7/7 states exited 0.
- Full repository gate: `python -m pytest tests/ -q` -> `240 passed`.
- No HTML, accessibility attribute, source schema, public copy, release, or
  adoption claim changed.
