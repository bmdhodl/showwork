# showwork evidence-pack large-field scaling readout r18

Date: 2026-08-15  
Status: observed / synthetic-local only  
Scope: disposable temporary ledgers passed to the existing
`scripts/evidence_pack.py::build_pack`; 100 base claims per fixture, five
repetitions, no production receipts or packer changes.

## Method

Each valid fixture created a temporary `artifact.txt`, one session, and 100
file-exists claims dated 2026-08-15. Shapes varied claim text, retraction
reason text, a synthetic fork branch, and a date range with no matching claims.
The malformed control appended a non-JSON line after a valid chain. For each
shape, elapsed time, UTF-8 serialized output size, and `tracemalloc` peak were
measured around `build_pack(root, from, to, ["soc2"], [])`. Temporary roots
were removed after the run; the post-run cleanup check was false.

## Results

Values are median elapsed/peak over five runs; min-max is elapsed time.

| shape | claims | code | output bytes | elapsed ms (median, min-max) | peak KiB (median, max) |
|---|---:|---:|---:|---:|---:|
| small claim text (~32-byte target) | 100 | 0 | 12,231 | 30.72 (30.25-42.91) | 193.9, 218.3 |
| large claim text (~8 KiB each) | 100 | 0 | 828,531 | 41.35 (38.92-45.47) | 2,582.6, 2,583.0 |
| large retraction reason (~12 KiB) | 100 + 1 retraction | 0 | 12,229 | 31.10 (29.69-44.21) | 220.4, 221.0 |
| synthetic fork metadata/branch | 100 + 1 branch | 0 | 14,412 | 31.17 (30.88-36.01) | 199.2, 199.5 |
| large claims, date range with no matches | 100 | 0 | 2,225 | 14.36 (13.53-23.46) | 2,480.1, 2,480.4 |
| malformed ledger control | 100 + malformed line | 2 | 1,052 | 2.47 (2.41-9.00) | 100.0, 100.2 |

The large claim fixture increased serialized output by about 67.7x and peak
allocation by about 13.3x versus the small fixture, while median pack time was
about 1.35x. The date-empty fixture still had a large allocation peak because
the chain audit must inspect the underlying ledger even though the requested
date range exported no claims. The large retraction reason did not appear in
the rendered inventory and therefore did not expand the pack; this is a
behavioral observation, not a recommendation to hide retractions.

The synthetic fork remained code 0 and expanded output through the audit
metadata. The malformed control returned code 2, confirming refusal before a
normal pack is emitted. No malformed or refused result was treated as a
successful export.

## Interpretation and boundary

These are local Python measurements on synthetic ledgers, not a throughput
benchmark, public performance claim, SLA, or production capacity estimate.
They show that serialized claim text is the dominant output and allocation
driver in this fixed-count sample, while raw chain inspection remains a cost
even for an empty date range.

## owner-gated recommendation

No packer optimization is justified by this readout alone. If owner-controlled
work later needs a bounded performance investigation, profile raw-ledger
parsing and date filtering separately, then repeat with representative,
redacted receipts. Do not publish these numbers or promise a scaling/SLA
boundary from them.

Validation: `python -m pytest tests/ -q --basetemp=C:\Users\patri\AppData\Local\Temp\showwork-r18-full-20260815` -> **239 passed**.
