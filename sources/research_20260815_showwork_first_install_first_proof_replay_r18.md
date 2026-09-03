# showwork first-install first-proof replay readout r18

Date: 2026-08-15  
Status: observed / disposable single-machine replay  
Scope: published PyPI package only. No local checkout import, credentials,
network write, source edit, publish, or adoption inference.

## Public inputs

- PyPI project: https://pypi.org/project/showwork/
- Inspected release page: https://pypi.org/project/showwork/0.3.0/
- Source repository: https://github.com/bmdhodl/showwork
- Installed requirement: `showwork==0.3.0`, with `--only-binary=:all:`

## Environment

| item | observed value |
|---|---|
| Python | 3.13.2 |
| package | 0.3.0 |
| import path | disposable venv `...\\venv\\Lib\\site-packages\\showwork\\__init__.py` |
| checkout isolation | ran from a disposable temporary project; `PYTHONPATH` and `SHOWWORK_ROOT` removed |
| install | PyPI wheel, no local source build |

## Command matrix

| command/action | exit | observed result |
|---|---:|---|
| `pip install --no-cache-dir --only-binary=:all: showwork==0.3.0` | 0 | wheel downloaded and installed |
| package/version/path probe | 0 | version 0.3.0; import resolved to disposable venv site-packages |
| `showwork start --session first-install-first-proof-r18 --agent codex` | 0 | session start recorded |
| create disposable `config/api.yaml` with `timeout: 30` | 0 | fixture written outside the checkout |
| `showwork claim ... file_contains ... timeout: 30` | 0 | claim recorded |
| `showwork finish --status ok` | 0 | `claims: GREEN (1/1 verified)` and finish recorded |
| `showwork verify --session ... --no-report` | 0 | session GREEN, 1/1 verified |
| `showwork audit` | 0 | disposable claims and sessions files GREEN, 3/3 records chained |

The temporary venv and project root were removed after the replay. This proves
that the published wheel can reach the minimal deterministic proof path on
this machine. It does not prove adoption, traffic, human success rates, or
compatibility across environments.

## Missing context and distribution boundary

The wheel contains runtime modules but no README or repository proof docs. The
published sdist contains README and tests but not `SPEC.md`, `docs/`,
`scripts/`, `js/`, or `actions/`, so relative proof/context links cannot all
be followed from an unpacked artifact. The PyPI-rendered README currently
shows an `actions/verify@main` example, while the local versioned README uses
`actions/verify@v0.3.0`; this is a distribution-surface drift observation,
not an adoption or release claim.

## owner-gated recommendation

Before a future owner-controlled release, replay the public README from a
clean environment after reconciling versioned action references and stable
links for repository-only proof context. Keep this result as a reproducible
fixture, not as a traffic, citation, or adoption metric.

Validation: `python -m pytest tests/ -q --basetemp=<temp>\showwork-r18-full-20260815` -> **239 passed**.
