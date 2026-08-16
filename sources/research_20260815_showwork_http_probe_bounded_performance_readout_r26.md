# HTTP probe bounded performance readout — r26

Date: 2026-08-15  
Scope: disposable localhost evidence; no timeout, response-cap, or network-policy change  
Source checkout: `a0d1f3d`

## Fixture

The existing `http_probe` checker was exercised against a disposable
`127.0.0.1` HTTP server. The server returned small healthy content, a 404, a
302 redirect, a 503, a body one byte over the configured cap, and a response
that slept past the configured timeout. The fixture also set
`SHOWWORK_NO_NETWORK=1` for one local probe and then restored the environment.
No public URL was contacted.

The current constants were observed, not changed:

- request timeout: `10` seconds
- maximum response body read: `1,048,576` bytes
- redirects: not followed; the observed status is checked directly

## Matrix

| case | median elapsed | checker outcome | observed boundary |
|---|---:|---|---|
| healthy 200 with body text | 36.80 ms across 3 runs | pass | status and body assertion both passed |
| expected 404 | 32.33 ms | pass | deliberate HTTP error status can be asserted |
| redirect | 34.39 ms | pass | 302 observed; `/ok` was not followed |
| unexpected 503 while expecting 200 | 32.47 ms | fail | endpoint response is visible as a status mismatch |
| body over 1 MiB cap | 34.24 ms | error | response rejected at the fixed body bound |
| delayed response | 10,040.42 ms | error | request timed out at the fixed 10-second bound |
| `SHOWWORK_NO_NETWORK=1` | 0.01 ms | error | request was refused by policy before network I/O |

The slow case is a one-run boundary probe, not a latency distribution. The
small-response sample is a local process measurement on this machine. These
numbers are not availability, capacity, performance, or SLA claims.

## Interpretation limits

Endpoint health and network access policy are separate: a healthy local 200
can pass when probes are enabled, while the same shape becomes an explicit
policy error under `SHOWWORK_NO_NETWORK`. A 404 or 302 can be valid evidence
when the claim expects that exact status. A checker result says what this
bounded request observed; it does not prove uptime, reachability from another
network, adoption, or human/AI comprehension.

## Verification

- Existing checker tests: `python -m pytest tests/test_checks.py -q` -> `65 passed`.
- No timeout/cap constant, network policy, production code, public URL, or
  release state changed.
