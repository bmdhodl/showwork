# showwork evidence-pack parse/filter profile readout r19

Date: 2026-08-15  
Status: observed / synthetic-local only  
Scope: disposable redacted ledgers, 100 claims per fixture, five repetitions;
stage proxies around the existing packer, no parser/cache/output change and no
public performance or SLA claim.

## Method

The fixtures measured JSONL claim/session parsing, chain audit, date selection,
an inventory/evaluation proxy, and full `build_pack` output separately. Shapes
were small, large claim fields, a synthetic fork, an empty date range over the
large fixture, and a malformed line. Claim text was redacted in the full pack.
Temporary roots were removed; the post-run cleanup check was false.

## Stage results

Median milliseconds and median `tracemalloc` peak are shown. All valid shapes
used 100 base claims; the fork had one extra branch record.

| shape | parse claims ms / KiB | audit ms / KiB | date filter claims | inventory proxy ms | full pack ms / KiB | code / bytes |
|---|---:|---:|---:|---:|---:|---:|
| small | 1.03 / 143 | 2.70 / 101 | 100 | 33.36 | 43.32 / 192 | 0 / 10,031 |
| large claim fields | 3.36 / 2,541 | 11.01 / 1,753 | 100 | 36.67 | 55.73 / 2,545 | 0 / 10,031 |
| fork | 1.04 / 144 | 2.73 / 101 | 101 | 35.14 | 41.94 / 189 | 0 / 10,096 |
| large, empty date range | 4.11 / 2,541 | 11.17 / 1,753 | 0 | 0.04 | 18.66 / 2,544 | 0 / 2,225 |
| malformed line | 0.98 / 143 | 2.72 / 101, verdict RED | 100 | 33.27* | 3.18 / 103 | 2 / 1,055 |

`*` The malformed inventory proxy is only a comparison of the evaluation
stage; `build_pack` refuses after the RED chain audit and does not render a
normal inventory. Date selection itself is sub-millisecond in these fixtures;
the empty-range cost is in reading and auditing the underlying ledger.

## Interpretation

Large fields expand parse and audit allocation substantially while selection is
cheap. The full-pack output is redacted and stable for the small/large shapes,
so output size alone does not expose the raw input size. A malformed record
returns code 2 and is not treated as an export. These numbers are local
diagnostics, not a throughput benchmark or capacity promise.

## owner-gated recommendation

No optimization is justified yet. If an owner later needs a bounded profile,
measure raw ledger decoding and chain audit with representative redacted
receipts, then separately evaluate caching or pagination. Do not change the
packer or publish an SLA from this sample.

Validation: `python -m pytest tests/ -q --basetemp=C:\Users\patri\AppData\Local\Temp\showwork-r19-full-20260815` -> **239 passed**.
