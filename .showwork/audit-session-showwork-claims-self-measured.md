# Claims audit - session showwork-claims-self-measured

**Verdict: GREEN**  (4/4 verified)

- OK **README.md labels the day-0 rate as measured by showwork on the author's own fleet, not independently measured** (`file_contains`)
    - /measured by showwork on the author's own fleet/ found in README.md
- OK **The Show HN draft marks the rate self-measured on a self-selected sample** (`file_contains`)
    - /Self-measured on a self-selected sample, not independently measured/ found in docs/launch/show-hn.md
- OK **The stranger report's figures table carries the provenance label in the row** (`file_contains`)
    - /not independently measured/ found in docs/reports/2026-09-03-stranger.md
- .. **The frozen machine-readable snapshot is unchanged by this session** (`None`)
    - retracted: I asserted the snapshot contains the aggregate 0.429 without reading it. It records per-corpus rates only (0.375 / 0.625 / 0.2); the aggregate lives in the method doc table. The claim was unverifiable as written.
- OK **The frozen per-corpus snapshot is untouched: it still reports the showwork corpus session rate 0.375** (`file_contains`)
    - /"fdr_session": 0.375/ found in docs/false-done-rate-day0.json
