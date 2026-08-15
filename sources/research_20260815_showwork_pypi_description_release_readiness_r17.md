# showwork PyPI description release-readiness readout r17

Date: 2026-08-15  
Retrieval: read-only page and local checkout inspection on 2026-08-15. Exact
public URL: <https://pypi.org/project/showwork/>. No README edit, publish, tag,
action-ref change, install, traffic, citation, adoption, or compliance claim.

## Matrix

| item | local checkout `f802774` | published PyPI 0.3.0 | classification |
|---|---|---|---|
| package version | `src/showwork/__init__.py` = 0.3.1; `pyproject.toml` = 0.3.1 | JSON metadata and page = 0.3.0 | published snapshot stale/local ahead |
| Python support | `requires-python >=3.10`; classifiers 3.10-3.13 | `Requires-Python: >=3.10`; same classifiers | parity |
| install command | `pip install showwork` | rendered in the description | wording parity; not install evidence |
| first proof command | local README/docs use `actions/verify@v0.3.0` and explain `@main` as testing-only | rendered PyPI description uses `actions/verify@main` | drift |
| links and limits | local README links SPEC, CI, adapters, case study, and explicit limits | package description is a 0.3.0 snapshot | stale-link and snapshot risk; inspect artifact contents separately |
| release repair | local text can be corrected before a future package build | replacing rendered PyPI text requires an owner-approved publication path | owner-gated |

## Reproducible checks

```text
python -c "import showwork; print(showwork.__version__)" -> 0.3.1
git rev-parse HEAD -> f802774...
rg -n "@v0.3.0|@main|pip install|requires-python" README.md pyproject.toml docs/ci.md
```

The page's visible release is 0.3.0 and its description still contains the
floating action ref. Page visibility is only a discoverability observation; it
does not prove installation, successful verification, human traffic, AI
citation, adoption, compliance, or supply-chain status.

## Decision

**OWNER-GATED REPAIR-DESIGN-ONLY.** Decide whether to rebuild/release a package
whose description matches the versioned proof path and whether local 0.3.1 is
ready for publication. No release or public edit was performed.

Validation: `python -m pytest tests/ -q --basetemp=...` -> **239 passed**.
