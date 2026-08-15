# showwork AI-search proof query set r23

Date: 2026-08-15  
Source revision: 128eea9  
Scope: six predeclared questions and one bounded read-only public snapshot.
No AI-search monitoring campaign, SEO/public-copy change, tracking, traffic,
citation-share, install, or adoption claim was made.

## Evidence snapshot

The following first-party surfaces were fetched once with read-only HTTP
requests on 2026-08-15:

| surface | result |
|---|---|
| [showwork README](https://raw.githubusercontent.com/bmdhodl/showwork/main/README.md) | HTTP 200; `pip install showwork` once; `showwork verify` three times; `REFUSED` once |
| [showwork SPEC](https://raw.githubusercontent.com/bmdhodl/showwork/main/SPEC.md) | HTTP 200 |
| [showwork GitHub](https://github.com/bmdhodl/showwork) | HTTP 200; repository reachable |
| [showwork PyPI JSON](https://pypi.org/pypi/showwork/json) | HTTP 200; public version `0.3.0`; Python `>=3.10`; download fields were `-1` sentinels |
| [showwork CI docs](https://raw.githubusercontent.com/bmdhodl/showwork/main/docs/ci.md) | HTTP 200 |
| [showwork adapter docs](https://raw.githubusercontent.com/bmdhodl/showwork/main/docs/adapters.md) | HTTP 200 |

Reachability means a surface responded. Indexability means a crawler can
locate and read a public source, not that it was cited. Comprehension means a
direct answer can be supported by visible source text. Citation visibility
means a source URL is shown. Install intent means an install instruction is
visible. Adoption requires independent usage evidence and is not inferred.

## Predeclared query set

| query | acceptable evidence | source URL | answer class | disallowed inference |
|---|---|---|---|---|
| How does showwork prove a run completed? | README text naming `showwork verify`, GREEN claims, and the refusal path | [README](https://raw.githubusercontent.com/bmdhodl/showwork/main/README.md) | supported from direct text | search snippets, stars, or reachability prove a completed run |
| How do I install showwork? | visible `pip install showwork` plus a reachable package page | [PyPI](https://pypi.org/project/showwork/) and [README](https://raw.githubusercontent.com/bmdhodl/showwork/main/README.md) | install intent only | install text proves use or adoption |
| What public version is available? | PyPI JSON `info.version` at the fetch time | [PyPI JSON](https://pypi.org/pypi/showwork/json) | time-bound public snapshot | local checkout version is already public or released |
| What happens when proof fails or is incomplete? | README RED/REFUSED/exit-2 language and the linked contract | [README](https://raw.githubusercontent.com/bmdhodl/showwork/main/README.md) and [SPEC](https://github.com/bmdhodl/showwork/blob/main/SPEC.md) | supported limit boundary | an incomplete page supports a success claim |
| Where are the source and ledger contracts? | reachable GitHub repository, README, and SPEC links | [GitHub](https://github.com/bmdhodl/showwork), [README](https://raw.githubusercontent.com/bmdhodl/showwork/main/README.md), [SPEC](https://github.com/bmdhodl/showwork/blob/main/SPEC.md) | citation-visible source | citation alone proves verification |
| Is showwork adopted? | independent usage evidence; otherwise an explicit unknown | [GitHub](https://github.com/bmdhodl/showwork) and [PyPI](https://pypi.org/project/showwork/) | unknown unless independent evidence exists | stars, forks, reachability, citations, install text, or `-1` download sentinels prove adoption |

## Reader-mode boundary

The practitioner article [Designing Websites for AI Agents](https://hidekazu-konishi.com/entry/designing_websites_for_ai_agents.html)
was used only as secondary context for three hypothetical reader modes:
bulk crawler, answer synthesis, and user-triggered fetch. Its suggestions
about stable URLs, server-rendered semantic HTML, truthful sitemap dates, and
the lack of guaranteed citation from `llms.txt` are not first-party showwork
evidence and are not treated as adoption or ranking proof.

The first-party comparison is narrower:

| reader mode | what the fixture may measure | what it cannot establish |
|---|---|---|
| bulk crawler | reachability and indexable source text | citation, traffic, or adoption |
| answer synthesis | comprehension of a question from visible text and citation visibility | human comprehension, install, or repeat use |
| user-triggered fetch | whether a stable URL returns readable source evidence | traffic, citation share, or adoption |

Google's [Search Generative AI performance report announcement](https://developers.google.com/search/blog/2026/06/gen-ai-performance-reports)
is the primary measurement context: it describes reports for impressions,
pages, countries, devices, and dates. Those measurements are distinct from
this local query rubric and were not queried or enabled here.

Any future measurement plan remains owner-gated. It must preserve the six
answer classes and the separation between reachability, comprehension,
citation visibility, install intent, and adoption.

Validation: `python -m pytest tests/ -q` -> **240 passed**.
