# showwork r22: proof-surface market comparison

Date: 2026-08-15  
Scope: direct visible evidence from a small read-only set of adjacent
developer tools. No competitor scoring, showwork copy change, publication,
traffic, or adoption claim.

## Direct surface comparison

| project | public repository/package/docs | visible proof or evaluation surface | visible install/version context | limits of comparison |
|---|---|---|---|---|
| showwork | [GitHub](https://github.com/bmdhodl/showwork), [PyPI](https://pypi.org/project/showwork/), [README](https://raw.githubusercontent.com/bmdhodl/showwork/main/README.md) | falsifiable claims, deterministic verification, append-only receipts, refused false done | pip install showwork; PyPI 0.3.0, Python >=3.10 | public reachability and copy only |
| Inspect AI | [GitHub](https://github.com/UKGovernmentBEIS/inspect_ai), [PyPI](https://pypi.org/project/inspect-ai/), [docs](https://inspect.aisi.org.uk/) | LLM evaluation framework with built-in evaluations and model-graded evaluation | PyPI 0.3.258, Python >=3.10; repository README shows editable development install | evaluation surface is not an append-only outcome receipt |
| Evidently | [GitHub](https://github.com/evidentlyai/evidently), [PyPI](https://pypi.org/project/evidently/), [docs](https://docs.evidentlyai.com/) | reports, test suites, offline evaluation, and monitoring for ML/LLM systems | pip install evidently; PyPI 0.7.21, Python >=3.10 | monitoring/evaluation surface is not proof of agent completion |
| QWED | [GitHub](https://github.com/QWED-AI/qwed-verification), [PyPI](https://pypi.org/project/qwed/), [docs](https://docs.qwedai.com/) | deterministic verification, DiagnosticResult, proof_ref, and explicit UNVERIFIABLE state | pip install qwed; PyPI 7.0.0, Python >=3.10 | direct copy is product documentation, not independent adoption evidence |

## Evidence classes

All four repository/API and package/docs surfaces were reachable during the
read-only inspection. Package-page visibility is indexability/metadata
evidence, not ranking. Visible commands and proof vocabulary support a
comprehension candidate, not a human comprehension result. No independent
adoption evidence was collected for any project; repository stars and forks
were not treated as adoption.

An owner-gated distribution experiment could compare one predeclared proof
question across these public surfaces, recording reachability, indexability,
comprehension, and adoption as separate gates. It must not copy positioning or
promote a visible command into an adoption claim.

Validation: python -m pytest tests/ -q --basetemp=C:\Users\patri\AppData\Local\Temp\showwork-r22-full-20260815 -> **240 passed**
