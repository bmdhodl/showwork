# showwork verification scale/memory follow-up readout r17

Date: 2026-08-15  
Scope: disposable local ledgers with 400 valid claims each; five repetitions
per operation. Measurements used Python `tracemalloc` allocation peaks, not
process RSS. No production receipt, implementation change, benchmark,
throughput, SLA, or compliance claim.

## Fixture shapes and observations

| shape | records / ledger bytes | audit median ms (range) | verify-date median ms (range) | pack median ms (range) | peak allocation audit / verify / pack KiB |
|---|---:|---:|---:|---:|---:|
| small claims | 401 / 93,383 | 7.459 (7.223-19.275) | 108.288 (105.368-109.592) | 117.239 (116.031-118.117) | 381 / 1,610 / 741 |
| large evidence strings | 401 / 4,067,392 | 40.590 (40.359-50.367) | 141.107 (138.430-145.781) | 163.322 (161.747-164.878) | 8,155 / 12,389 / 11,948 |
| many retractions | 801 / 207,794 | 14.656 (14.446-26.932) | 19.780 (19.368-19.979) | 32.281 (31.997-32.988) | 692 / 1,443 / 1,246 |
| fork-heavy history | 442 / 101,497 | 7.977 (7.742-21.243) | 112.759 (108.044-114.361) | 117.700 (116.242-123.079) | 361 / 722 / 1,707 |
| pack-heavy metadata | 601 / 952,487 | 18.233 (17.826-31.304) | 112.774 (112.595-115.045) | 131.569 (130.202-133.062) | 1,331 / 2,198 / 2,092 |

The small, fork-heavy, retraction-heavy, and metadata-heavy fixtures remained
GREEN/code 0 for the measured operations. Large claim/evidence strings were the
dominant allocation and audit cost. Retractions increased record count but did
not dominate verification time in this sample. The follow-up did not add a
malformed case; the r16 malformed control remains the refusal boundary (audit
RED and evidence-pack refusal code 2).

Memory values are Python allocation observations in one process. They are not
machine capacity, process RSS, or a service limit. The five synthetic shapes do
not support a public benchmark.

## Decision

**NO CHANGE.** Keep the current implementation and reserve any optimization for
an owner-reviewed workload with real receipt shapes. Do not publish a
throughput/SLA statement.

Validation: `python -m pytest tests/ -q --basetemp=...` -> **239 passed**.
