# showwork artifact proof-context link replay readout r19

Date: 2026-08-15  
Status: observed / read-only public and disposable artifact inspection  
Scope: published 0.3.0 wheel/sdist, PyPI rendering, GitHub main/tag pages;
no packaging, metadata, release, public-copy, or artifact edit.

## Surface-by-link matrix

| surface | proof context result | classification |
|---|---|---|
| published wheel | no README or repository proof links in the payload | runtime-only; context is outside the wheel |
| unpacked published sdist | README links are present, but `SPEC.md`, `docs/`, `js/`, `scripts/`, and `actions/` targets are absent | repository-only links are broken inside this artifact |
| PyPI 0.3.0 rendering | relative hrefs such as `SPEC.md` and `docs/ci.md` are preserved as relative hrefs | host-dependent; not a stable GitHub link contract |
| GitHub `main` README | relative links resolve to repository files; inspected proof paths responded 200 | reachable repository context |
| GitHub `v0.3.0` README | relative links resolve to tag files; inspected proof paths responded 200 | reachable versioned repository context |

The inspected GitHub paths were `SPEC.md`, the Claude adapter, concurrency,
CI, adapters, false-done-rate, compliance, and case-study docs, plus the
JavaScript auditor and Action directory. The public repository surfaces had
those paths at both `main` and `v0.3.0`; this does not make them part of a
wheel/sdist artifact.

## Version and provenance context

The current GitHub `main` README uses `actions/verify@v0.3.0`, while the
`v0.3.0` tag README and the PyPI-rendered 0.3.0 description use
`actions/verify@main`. This is a version-drift observation. It does not prove
which reference an owner intends, and it is not an adoption or release claim.

The PyPI JSON/page identifies the 0.3.0 files and hashes and displays release
provenance details. This readout records the page content only; it does not
evaluate signing, attestations, trust, or supply-chain claims.

## owner-gated stable-link candidates

For owner review, versioned GitHub URLs such as
`https://github.com/bmdhodl/showwork/blob/v0.3.0/SPEC.md` are more explicit
than artifact-relative paths. A future decision must choose whether to link to
tagged repository context or carry selected docs in an artifact. No link or
packaging change was made.

Sources: https://pypi.org/project/showwork/0.3.0/, https://pypi.org/pypi/showwork/0.3.0/json, https://github.com/bmdhodl/showwork/blob/main/README.md, and https://github.com/bmdhodl/showwork/tree/v0.3.0.

Validation: `python -m pytest tests/ -q --basetemp=C:\Users\patri\AppData\Local\Temp\showwork-r19-full-20260815` -> **239 passed**.
