# showwork r21: public proof snippet answerability

Date: 2026-08-15  
Scope: read-only GitHub, PyPI, raw documentation, repository metadata, and
dated public-query inspection. No publish, edit, metadata change, tracking,
traffic, or adoption claim.

## Surface-to-query matrix

| intent/query | inspected surface | directly visible | safe class | unsupported inference |
|---|---|---|---|---|
| install intent | [README](https://github.com/bmdhodl/showwork/blob/main/README.md), [PyPI](https://pypi.org/project/showwork/) | pip install showwork | answer: documented command | an install or successful use |
| documented proof | [GitHub README](https://raw.githubusercontent.com/bmdhodl/showwork/main/README.md) | deterministic showwork verify, falsifiable claims, no-LLM-judge wording | answer: documented behavior | independent proof of every public claim |
| proof limits | [CI documentation](https://raw.githubusercontent.com/bmdhodl/showwork/main/docs/ci.md) | pinned action guidance and warnings about main | qualify: context and ref matter | release or supply-chain assurance |
| package version | [PyPI JSON](https://pypi.org/pypi/showwork/json) | version 0.3.0, Python >=3.10, wheel and sdist names | answer: published metadata | local checkout parity or installation |
| source reachability | [GitHub repository](https://github.com/bmdhodl/showwork) | public page/API reachable; repository counters were 0 stars and 1 fork at inspection | answer: current public metadata | users, customers, or adoption |
| search presence | dated public query sample | returned noisy/unrelated results; direct target was checked separately | unknown | ranking, impressions, clicks, or traffic |
| external adoption | all inspected surfaces | no independent usage evidence | refuse | users, customers, traffic, or adoption |

The page and metadata observations were made read-only on 2026-08-15. A
snippet or page can answer what the project documents. It cannot answer
whether a person installed it, whether an AI retrieved it, whether a human
understood it, or whether anyone adopted it.

An owner-gated distribution follow-up could predeclare a query set and
separate direct answerability from measured traffic. This report does not
authorize public-copy, package, release, tracking, or adoption work.

Validation: python -m pytest tests/ -q --basetemp=<temp>\showwork-r21-full-20260815 -> **239 passed**
