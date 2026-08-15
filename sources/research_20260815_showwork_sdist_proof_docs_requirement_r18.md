# showwork published sdist proof-docs requirement readout r18

Date: 2026-08-15  
Status: observed / owner-gated recommendation  
Scope: disposable downloads and unpacking of the published 0.3.0 artifacts,
local repository inspection, and a no-build first-reader replay. No package
metadata, build, release, or publish change was made.

## Result

The published wheel is a runtime distribution. The published sdist includes
the README, build metadata, runtime source, tests, and license, but not the
repository specification, documentation tree, JavaScript auditor, scripts, or
GitHub Action. That is a coherent library-artifact split, but the relative
proof-document links in README.md cannot be resolved from an unpacked sdist.
The first proof itself does not need those repository-only files: an installed
0.3.0 wheel can start a session, record a deterministic file claim, finish, and
verify in a disposable project.

## Public artifact evidence

Observed from the PyPI 0.3.0 JSON and files on 2026-08-15:

| artifact | SHA-256 | size | observed top-level content |
|---|---|---:|---|
| `showwork-0.3.0-py3-none-any.whl` | `20a4a8a535bee0523c504dcea4f57992abb6bb5bbf74404b5a0ac8cc46ff23d3` | 39,957 bytes | `showwork/` runtime modules plus `.dist-info/` metadata and license |
| `showwork-0.3.0.tar.gz` | `dde783d6b1f9c2aede6c60f7f2ca57adc088c4799847dde8a2a0db5ac3f916ad` | 57,699 bytes | `LICENSE`, `PKG-INFO`, `pyproject.toml`, `README.md`, `setup.cfg`, `src/`, `tests/` |

The PyPI page reports version 0.3.0, Python >=3.10, and the same hashes. It
also displays release provenance metadata. This readout treats those as
published-page observations only; it does not evaluate signing, attestations,
trust, or supply-chain claims.

## Artifact-content matrix

| asset or path | wheel | sdist | classification for a first reader |
|---|---:|---:|---|
| `showwork/` runtime modules | yes | yes, under `src/` | required runtime surface; present |
| `README.md` / `PKG-INFO` | no README file | yes | reader aid; present in sdist and rendered by PyPI, not a wheel payload |
| `LICENSE` | dist-info license | yes | distribution metadata; present |
| `tests/` | no | yes | source validation aid; not required for an installed first proof |
| `SPEC.md` | no | no | repository-only contract; linked by README, unresolved inside the unpacked sdist |
| `docs/claude-code.md`, `docs/ci.md`, `docs/adapters.md`, `docs/concurrency.md` | no | no | repository-only integration/context docs; linked but absent from sdist |
| `docs/false-done-rate.md`, `docs/compliance.md`, `docs/case-study.md` | no | no | repository-only methodology/context docs; linked but absent from sdist |
| `docs/examples/` | no | no | repository-only examples; absent from sdist |
| `js/showwork-audit/` | no | no | repository-only companion auditor; absent from sdist |
| `scripts/evidence_pack.py` and other `scripts/` | no | no | repository-only tooling; absent from sdist |
| `actions/verify/action.yml` | no | no | repository Action source; absent from sdist |

The local checkout is version 0.3.1 while the inspected public artifact is
0.3.0. Local files were used only to classify links and build configuration;
they were not substituted for the published artifact.

## Disposable unpacked-artifact replay

The sdist was downloaded to a temporary directory, listed, and removed. A
fresh unpacked tree showed the runtime, README, tests, and metadata rows above,
but no `SPEC.md`, `docs/`, `js/`, `scripts/`, or `actions/` targets for the
README's relative proof links. No build or installation was performed during
this artifact-only check.

The actual first-proof replay was performed separately from a PyPI-installed
wheel and is recorded in the r18 first-install report. It confirms that the
missing repository context is not a runtime prerequisite for the minimal
start/claim/finish/verify path.

## Owner-gated recommendation

Keep the wheel as runtime-only and keep repository-only docs out of the wheel.
Before a future owner-controlled release, decide whether the sdist should
carry a small stable proof-context subset or whether README links should point
to versioned repository URLs. Do not copy the current repository tree into a
published artifact without an explicit release policy: doing so would turn
the missing-file classification into a stale-copy risk.

Sources: https://pypi.org/pypi/showwork/0.3.0/json, https://pypi.org/project/showwork/0.3.0/, and the local `pyproject.toml`, `README.md`, `SPEC.md`, `docs/`, `scripts/`, and `actions/` paths.

Validation: `python -m pytest tests/ -q --basetemp=C:\Users\patri\AppData\Local\Temp\showwork-r18-full-20260815` -> **239 passed**.
