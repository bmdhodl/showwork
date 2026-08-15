# showwork proof-question comprehension fixture r23

Date: 2026-08-15  
Source revision: 128eea9  
Scope: one redacted question and read-only public first-party surfaces. No
competitor score, human study, public edit, publication, or adoption claim.

## Predeclared question and rubric

Question: **What proves this run completed?**

The fixture records whether a reader can locate four distinct things:

1. proof state or verdict;
2. decisive evidence or command;
3. failure/refusal meaning;
4. stated limits or non-inferences.

Reachability and citation visibility are recorded separately from
comprehension. Install intent is only a visible installation instruction.
Adoption is not inferred from any of these surfaces.

## First-party evidence

| surface | reachability | visible proof-question evidence | comprehension result | citation visibility | install intent | adoption |
|---|---|---|---|---|---|---|
| [showwork GitHub](https://github.com/bmdhodl/showwork), [README](https://raw.githubusercontent.com/bmdhodl/showwork/main/README.md), [PyPI](https://pypi.org/project/showwork/), [docs](https://github.com/bmdhodl/showwork/tree/main/docs) | GitHub/README/package/docs returned HTTP 200 | README names deterministic `showwork verify`, claim checks, GREEN/RED, and `REFUSED` on a false close | The question is answerable from the visible contract: the run is supported by verified claims, with the refusal path shown | Public repository and README links are directly visible | README shows `pip install showwork` | No adoption evidence; no inference made |
| [Inspect AI GitHub](https://github.com/UKGovernmentBEIS/inspect_ai), [README](https://raw.githubusercontent.com/UKGovernmentBEIS/inspect_ai/main/README.md), [PyPI](https://pypi.org/project/inspect-ai/), [docs](https://inspect.aisi.org.uk/) | GitHub/README/package/docs returned HTTP 200 | README exposes evaluations, development install, linting, and tests, but not a run-completion proof/refusal contract | The specific question is not answered by the inspected README surface; this is a surface observation, not a product judgment | Public repository, package, and docs links are directly visible | README shows development install; package page is reachable | No adoption evidence; no inference made |
| [Evidently GitHub](https://github.com/evidentlyai/evidently), [README](https://raw.githubusercontent.com/evidentlyai/evidently/main/README.md), [PyPI](https://pypi.org/project/evidently/), [docs](https://docs.evidentlyai.com/) | GitHub/README/package/docs returned HTTP 200 | README exposes Reports, Test Suites, pass/fail conditions, and monitoring, but not a receipt-level completion/refusal contract | The question is only partially answered for evaluation outputs; the inspected surface does not establish receipt proof for a run | Public repository, package, and docs links are directly visible | README shows `pip install evidently` | No adoption evidence; no inference made |
| [QWED GitHub](https://github.com/QWED-AI/qwed-verification), [README](https://raw.githubusercontent.com/QWED-AI/qwed-verification/main/README.md), [PyPI](https://pypi.org/project/qwed/), [docs](https://docs.qwedai.com/) | GitHub/README/package/docs returned HTTP 200 | README names `VERIFIED`, `UNVERIFIABLE`, attached evidence, `proof_ref`, and execution != verification | The proof question is answerable at the vocabulary level: verdict and evidence are named, with an explicit unverifiable state | Public repository, package, and docs links are directly visible | README exposes an install/quick-start path | No adoption evidence; no inference made |

## Interpretation boundary

This fixture demonstrates a deterministic reader rubric, not human
comprehension, product quality, or market position. Reachability only means a
public surface responded. Citation visibility only means a source link or
source text was visible. A package command only establishes install intent.
None establishes traffic, repeat use, adoption, certification, or compliance.

Any future public content-contract experiment remains owner-gated and must
preserve these separations.

Validation: `python -m pytest tests/ -q` -> **240 passed**.
