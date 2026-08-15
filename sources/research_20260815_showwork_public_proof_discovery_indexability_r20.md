# showwork r20: public proof discovery and indexability

Date: 2026-08-15  
Scope: read-only public search and page inspection. No outreach, tracking, public edit, traffic purchase, release, or adoption claim was made.

## Query-to-surface readout

| query | observed surface | match class | safe conclusion |
|---|---|---|---|
| `deterministic agent verification showwork` | [showwork GitHub](https://github.com/bmdhodl/showwork), [showwork PyPI 0.3.0](https://pypi.org/project/showwork/0.3.0/), first-party article at [bmdpat.com](https://bmdpat.com/blog/my-agents-have-to-prove-what-they-did-2026) | direct / first-party | the project and its proof vocabulary are publicly reachable |
| `false done rate AI agents showwork` | [Grolea false-success article](https://www.grolea.com/insights/agent-says-done-but-isnt), first-party showwork article | adjacent / first-party | false-success is a discoverable adjacent problem; this is not traffic evidence |
| `append-only agent receipts showwork` | [AgentReceipt](https://www.agentreceipt.co/), [Agent Receipts specification](https://agentreceipts.ai/specification/overview/), [Tycho](https://swail.dev/), [WorkProof](https://www.workproof.run/), first-party showwork surfaces | adjacent / first-party | receipt and verification vocabulary exists across several public surfaces |

The public GitHub and PyPI pages were reachable on the probe date. Search results also surfaced adjacent receipt and verification projects. The first-party article is direct evidence that the topic is publicly indexed, but ownership means it is not independent adoption evidence. Adjacent results show vocabulary overlap, not use of showwork.

## Crawler, human, and inference limits

Search-result presence does not establish ranking, impressions, clicks, qualified readers, conversion, or adoption. A crawler can discover a URL and extract text; it cannot establish that a human understood the proof boundary or that an organization used the package. Search results are time-, locale-, and index-dependent. No search-volume or traffic measurement was performed.

An **owner-gated** distribution experiment could compare one versioned proof landing surface against the current public artifact with predeclared query and reader checks. It would need explicit instrumentation and review. This report does not authorize that experiment or any public copy change.

Validation: `python -m pytest tests/ -q --basetemp=C:\Users\patri\AppData\Local\Temp\showwork-r20-full-20260815` -> **239 passed**
