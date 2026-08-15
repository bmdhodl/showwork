# showwork GitHub/PyPI proof-path parity readout r16

Date: 2026-08-15  
Retrieval: read-only page fetches on 2026-08-15. Live pages can change after
this snapshot. Exact live URLs: <https://github.com/bmdhodl/showwork> and
<https://pypi.org/project/showwork/>.

## Side-by-side matrix

| item | local checkout (`6be11ae`) | GitHub page | PyPI page | classification |
|---|---|---|---|---|
| package version | `src/showwork/__init__.py` = `0.3.1` | page does not establish a newer package version | rendered release = `0.3.0` | local-ahead drift |
| Python support | `pyproject.toml` = `>=3.10`; classifiers 3.10-3.13 | README is compatible with the same command path | metadata says Python `>=3.10` | parity |
| install command | `pip install showwork` in README | same repository quickstart is visible | project page presents the package install path | parity of wording; not install proof |
| first proof command | README `showwork start/claim/finish`; CI uses `showwork verify` | README renders the versioned action `bmdhodl/showwork/actions/verify@v0.3.0` | rendered description shows `bmdhodl/showwork/actions/verify@main` | description drift |
| action pin guidance | README/docs default to `@v0.3.0`; docs also show the release SHA and explain `@main` is testing-only | `@v0.3.0` is visible in the rendered README | `@main` is visible in the rendered package description | drift in the package copy; not an action or workflow change |
| proof/report links | local README links SPEC, CI docs, and evidence-pack docs | repository is the proof/report source | package description points back to the project but does not prove a successful verification | parity/unknown by surface |
| issue link | `pyproject.toml` declares `https://github.com/bmdhodl/showwork/issues` | repository issue path is the natural owner surface | no independent issue workflow was inferred from the package page | parity/unknown |
| roadmap language | local README/docs describe current features and deliberate limits | repository page is the source of current project text | package description is a release snapshot | snapshot drift possible |

The PyPI page also identifies the current published files as 0.3.0 and shows
source/wheel hashes and provenance metadata for that release. Those are page
observations, not evidence of local installation success, first verification,
traffic, AI citation, adoption, compliance, or supply-chain assurance.

## Reproducible local checks

The comparison used these read-only checks in `K:\showwork`:

```text
python -c "import showwork; print(showwork.__version__)"  -> 0.3.1
git rev-parse HEAD                                      -> 6be11ae...
git ls-remote origin refs/heads/main                    -> 6be11ae...
rg -n "pip install|requires-python|@v0.3.0|@main|Issues" README.md pyproject.toml docs/ci.md
```

The live page fetches used no login, write, publish, or public-URL fixture
operation. Page visibility is a discoverability observation only. It does not
establish that a reader installed the package, ran a successful verifier, or
adopted the project.

## Owner-gated recommendation

**REPAIR-DESIGN-ONLY:** an owner should decide whether the PyPI description
should be rebuilt/released so its first proof path matches the versioned
`@v0.3.0` guidance, and whether the local 0.3.1 version is ready for any future
publication. No README edit, package release, action-ref change, or public copy
change is authorized by this readout.

Validation: `python -m pytest tests/ -q --basetemp=...` -> **239 passed**.
