# showwork bounded HTTP proof boundary readout r15

Date: 2026-08-15  
Scope: a temporary `127.0.0.1` HTTP server and the existing `http_probe`
checker. No public URL was contacted. No network cap, timeout, verifier,
schema, signer, workflow, public-copy, authority, compliance, adoption, or
release change.

## Local fixture matrix

| case | checker result | reader exit | observed behavior |
|---|---|---:|---|
| `200` plus body substring `healthy` | pass / GREEN | 0 | exact status and body match |
| expected `201`, received `200` | fail / RED | 2 | status mismatch |
| expected `404` plus `not found` | pass / GREEN | 0 | expected HTTP error is representable |
| redirect expected `302` | pass / GREEN | 0 | redirect was not followed |
| expected body `absent` | fail / RED | 2 | body mismatch |
| response larger than 1,048,576 bytes | error / YELLOW | 3 | hard response-size cap refused the read |
| delayed response | error / YELLOW | 3 | existing 10-second request timeout elapsed |
| `SHOWWORK_NO_NETWORK=1` | error / YELLOW | 3 | policy refused before making the request |

The temporary server, root, and fixture files were removed after the run;
cleanup verified true. The local server was bound only to loopback.

## Reader limitation

A GREEN local probe means that one bounded request observed the expected status
and optional body at that moment. It does not prove that an external service is
healthy, trustworthy, available later, or safe to depend on. A YELLOW refusal
must remain visible rather than being converted into a missing-success claim.

## Decision

**NO CHANGE.** Keep network disabled by default in CI and require an explicit
trusted-context opt-in for bounded probes. Do not contact public URLs from
synthetic fixtures or turn a local response into adoption, reliability, or
availability evidence.

Canonical local evidence: `src/showwork/checks.py`, `tests/test_checks.py`, and
`docs/ci.md`.

Validation: `python -m pytest tests/ -q --basetemp=<temp>\showwork-r15-full-20260815` -> **234 passed in 13.27s**.
