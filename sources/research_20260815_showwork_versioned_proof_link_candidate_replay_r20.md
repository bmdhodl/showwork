# showwork r20: versioned proof-link candidate replay

Date: 2026-08-15  
Scope: read-only PyPI, sdist metadata/context, raw GitHub `main`, and raw GitHub `v0.3.0` inspection. No README, package, tag, release, or public link was edited.

## Artifact and link matrix

| candidate context | observed result | classification |
|---|---|---|
| PyPI project page 0.3.0 | 200 response; rendered description contains relative `SPEC.md`, docs, and `actions/verify@main` references | host-dependent rendering; action reference drifts |
| PyPI JSON 0.3.0 | version `0.3.0`; wheel and sdist URLs exposed; description matches the PyPI rendering | stable release metadata, not proof that relative docs resolve from a package |
| published wheel | wheel URL is available; it contains package/runtime content but not the README/docs proof targets | no portable relative-doc context |
| published sdist | sdist URL is available; README contains relative links, but the package artifact does not make every linked target a hosted page | artifact context is incomplete |
| GitHub `main` raw README | 200 response; action example uses `bmdhodl/showwork/actions/verify@v0.3.0` | version-pinned action target, current branch copy |
| GitHub `v0.3.0` raw README | 200 response; action example uses `bmdhodl/showwork/actions/verify@main` | tag content is historical/drifted relative to `main` |
| GitHub `main` and `v0.3.0` target paths | observed page responses for `SPEC.md`, docs, and action paths | reachability only; not a claim about rendered contents or package parity |

The same relative link text is portable only when a reader has a repository checkout at the expected root. A PyPI rendering may display the link, but its host-relative resolution and anti-bot/challenge behavior are not equivalent to a GitHub repository file. The versioned and branch-pinned action references also point in opposite directions between the current branch and the tag.

## Candidate policy

For a future documentation review, versioned GitHub URLs are the clearest replay candidate for a released artifact, while `main` links are mutable and relative links are context-dependent. That is a candidate policy, not a release decision. An **owner-gated** documentation or packaging review must choose whether link changes are acceptable and must recheck the published artifact after any owner-authorized release.

This readout does not prove package reproducibility, exact replay, adoption, supply-chain integrity, or release readiness. No signing, schema, verifier, packaging, or public-copy change is authorized.

Validation: `python -m pytest tests/ -q --basetemp=C:\Users\patri\AppData\Local\Temp\showwork-r20-full-20260815` -> **239 passed**
