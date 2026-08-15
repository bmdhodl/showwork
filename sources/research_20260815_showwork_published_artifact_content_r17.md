# showwork published-artifact content readout r17

Date: 2026-08-15  
Retrieval: read-only download and inspection of the published 0.3.0 wheel and
sdist. Exact page: <https://pypi.org/project/showwork/0.3.0/>. Downloads were
stored in a disposable temp directory, hashed, listed, and not installed or
modified. No artifact-trust, install, adoption, or release claim.

## Artifact matrix

| surface | observed content | reader classification |
|---|---|---|
| wheel `showwork-0.3.0-py3-none-any.whl` | runtime `showwork/*.py`, `LICENSE`, dist-info metadata/RECORD; no README, SPEC, docs, actions, scripts, or tests | installable runtime snapshot; proof documentation is not in the wheel |
| sdist `showwork-0.3.0.tar.gz` | `README.md`, `LICENSE`, `pyproject.toml`, `setup.cfg`, `src/showwork`, and tests | source snapshot includes README/tests but omits SPEC, docs, `actions/`, `scripts/`, and `js/` paths linked or described by the repository README |
| metadata | Version 0.3.0, `Requires-Python >=3.10`, MIT license, no runtime dependencies | parity with the published release metadata; stale versus local 0.3.1 |
| rendered description | quickstart is present; action example renders `@main`; relative links name SPEC/docs paths | first proof path is readable but version drift and relative-link gaps remain |

The observed SHA-256 values match the PyPI JSON metadata: wheel
`20a4a8a535bee0523c504dcea4f57992abb6bb5bbf74404b5a0ac8cc46ff23d3` and sdist
`dde783d6b1f9c2aede6c60f7f2ca57adc088c4799847dde8a2a0db5ac3f916ad`. These
identify the downloaded bytes only; they do not prove that an install or
verification succeeded.

## Reproducible local checks

```text
Invoke-WebRequest <wheel-url> / <sdist-url> into a disposable temp directory
Get-FileHash -Algorithm SHA256 <each-file>
python -c "zipfile.ZipFile(...).namelist()"
tar -tzf <sdist>
```

The local README references `SPEC.md`, `docs/claude-code.md`,
`docs/concurrency.md`, `docs/ci.md`, `docs/adapters.md`,
`docs/false-done-rate.md`, `docs/compliance.md`, `docs/case-study.md`, and
`js/showwork-audit/`; those paths were absent from the published sdist listing.

## Owner-gated recommendation

Before any future publication, an owner should choose whether the package
artifact should carry the proof documents or whether the description should use
stable public URLs instead of relative repository paths. Align the first proof
command with the versioned action guidance at the same time. No package,
metadata, README, or release change is authorized by this readout.

Validation: `python -m pytest tests/ -q --basetemp=...` -> **239 passed**.
