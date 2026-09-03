# showwork published-surface AI query readout r19

Date: 2026-08-15  
Status: observed / read-only public text  
Scope: current public GitHub and PyPI pages only; no README/PyPI edit,
outreach, tracking, release, traffic, citation, or adoption claim.

## Query matrix

| query | PyPI 0.3.0 | GitHub `main` | safe answer class |
|---|---|---|---|
| How do I install it? | `pip install showwork` is shown | same quickstart | directly supported, but not a cross-environment success rate |
| What is the first proof? | start, deterministic file/command claims, finish, verify are shown | same | documented path; one-machine replay evidence is separate |
| What version/runtime? | 0.3.0 and Python >=3.10 are shown | README does not establish the current package version by itself | PyPI-supported; GitHub answer needs tag/metadata context |
| Which Action ref? | rendered description says `actions/verify@main` | current `main` README says `@v0.3.0` | drift; do not silently merge the answers |
| What are the limits? | not observability, not agent testing, not an LLM judge; no spend column in current dashboard context | same limits plus wall-clock wording | directly supported with timeout/descendant qualification |
| What surfaces exist? | CLI/API/Action/docs are described, but docs are repository-only from the artifact | README links to repository docs and Action | mixed: public description, source context, and artifact content differ |
| Has it been adopted or is it getting traffic? | no supported adoption measure; PyPI download fields are not a user-count proof | GitHub page presence/stats are not adoption proof | unknown/unsafe to infer |

The GitHub `v0.3.0` tag README also uses `actions/verify@main`, reinforcing the
version-drift finding. Public page visibility establishes crawler-readable
text, not crawler traffic, human use, retention, or adoption. The PyPI page's
repository statistics explicitly carry maintainer-supplied/derived context;
they were not treated as independently verified traction.

## Safe answer boundary

An AI can answer the install syntax, documented first-proof commands, PyPI
version/runtime requirement, and stated product limits with source links. It
should qualify repository-only proof context, version-drifting Action refs,
descendant termination uncertainty, and the absence of adoption evidence. It
should refuse to turn citations, page presence, package provenance display, or
one local replay into claims of traffic, certification, compliance, authority,
or market adoption.

## owner-gated recommendation

Run a future owner-controlled distribution experiment only after reconciling
the Action reference and proof-context links. Measure actual referrals or
replays separately from page readability and citations; no public surface or
traffic instrumentation is warranted by this readout.

Sources: https://pypi.org/project/showwork/0.3.0/, https://pypi.org/pypi/showwork/0.3.0/json, https://github.com/bmdhodl/showwork, https://raw.githubusercontent.com/bmdhodl/showwork/main/README.md, and https://raw.githubusercontent.com/bmdhodl/showwork/v0.3.0/README.md.

Validation: `python -m pytest tests/ -q --basetemp=<temp>\showwork-r19-full-20260815` -> **239 passed**.
