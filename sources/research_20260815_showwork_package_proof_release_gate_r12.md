# showwork package proof release gate r12

Date: 2026-08-15  
Scope: candidate local wheel, current source metadata, rendered public GitHub
and PyPI artifacts, and a future proof-path gate. No package edit, public-copy
edit, tag, PyPI upload, release, adoption, compliance, authority, signer, or
supply-chain claim.

## Result

The local candidate is `showwork 0.3.1`; the current public PyPI page reports
`0.3.0`, released 2026-07-18. The local wheel contains the Python package but
does not contain the repository-local `scripts/evidence_pack.py`. The rendered
GitHub README pins the verify action to `@v0.3.0`, while the rendered PyPI
description shows `@main`. These are release-gate observations, not evidence of
traffic, adoption, provenance, compliance, or release readiness.

Decision: **OWNER-GATED**. Keep the current package and public surfaces
unchanged. A future owner-approved release may resolve the parity assertions;
this report does not publish or edit anything.

## Artifact matrix

| artifact | observed result | gate implication |
|---|---|---|
| `pyproject.toml` | local version `0.3.1`, Python `>=3.10`, project URLs present | candidate metadata is internally inspectable |
| local wheel | `showwork-0.3.1-py3-none-any.whl`, 16 files, metadata version `0.3.1` | candidate wheel builds without dependency additions |
| wheel script contents | `HAS_EVIDENCE_PACK=False` | evidence pack is checkout-only for this candidate |
| local README | action ref `bmdhodl/showwork/actions/verify@v0.3.0`; points to `scripts/evidence_pack.py` | source docs have explicit pinned action and checkout path dependency |
| public GitHub README | action ref `@v0.3.0` | current public source is pinned to the published action |
| public PyPI description | action ref `@main`; package page reports latest `0.3.0` | rendered distribution copy differs from GitHub |
| minimal proof | install, start, claim, verify, audit, and finish work from the package; evidence pack needs an explicit checkout | future gate must distinguish package CLI from checkout script |

Public references inspected on 2026-08-15: [GitHub repository](https://github.com/bmdhodl/showwork), [PyPI project](https://pypi.org/project/showwork/), and [PyPI project metadata guidance](https://docs.pypi.org/project_metadata/).

## Future owner-approved gate

1. Build the wheel from the intended source revision and record name, version,
   Python requirement, project URLs, and complete file list.
2. Compare the wheel README metadata with the intended GitHub README and the
   rendered PyPI description. Require exact action-ref parity.
3. Run the clean proof: install the candidate, start a session, record one
   local predicate, verify GREEN, audit the chain, and finish through the gate.
4. Invoke the evidence pack from an explicit checkout path and label it
   checkout-only if the script is not packaged.
5. Stop on any version, action-ref, README, file-list, or command-path drift.

The gate is a candidate inspection contract. It does not establish package
provenance, supply-chain security, compliance, authority, or user adoption.

