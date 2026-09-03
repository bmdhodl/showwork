# showwork r21: public proof traffic-signal separation

Date: 2026-08-15  
Scope: read-only public observations plus synthetic signal controls. No post,
public edit, tracking, traffic measurement, package change, release, or
adoption claim.

## Signal taxonomy

| signal | current safe class | evidence observed | what it does not prove |
|---|---|---|---|
| repository reachability | reachable | GitHub API/HTML response for the public repository | indexing, understanding, adoption |
| package indexability | indexed metadata | PyPI JSON exposed 0.3.0 release metadata | installation, active use, adoption |
| search presence | unknown | query sample was noisy; direct target inspection is separate | ranking, impressions, clicks, traffic |
| install intent | documented intent | public copy contains pip install showwork | an install occurred |
| human proof comprehension | unknown | no human task study; synthetic labels are controls | understanding, conversion |
| AI answerability | content answerable | public text states documented behavior and limits | AI retrieval, AI traffic, adoption |
| independent adoption | refuse | no independent usage/customer evidence inspected | users, customers, market adoption |

## Evidence gates

The minimum evidence should remain separate: a response proves reachability;
dated exact-target search evidence is needed for indexability; a command in
copy is only documented intent; human comprehension needs an observed task with
a predeclared rubric; AI answerability needs retrieved text plus a bounded
answer test; adoption needs independent or instrumented usage evidence with
attribution. Synthetic controls can test the taxonomy but cannot advance any
real-world signal.

An owner-gated measurement plan may repeat dated queries, record the exact
surface and retrieval context, and separately instrument a reviewed experiment.
No signal may be promoted from reachability or answerability to traffic or
adoption without its own evidence gate.

Validation: python -m pytest tests/ -q --basetemp=<temp>\showwork-r21-full-20260815 -> **239 passed**
