# showwork r22: public install intent versus adoption

Date: 2026-08-15  
Scope: read-only GitHub, PyPI, README, package metadata, and public-query
surfaces. No telemetry, metadata, package, publish, traffic, or adoption
change.

## Signal matrix

| signal | observed evidence | safe class | not established |
|---|---|---|---|
| install instructions | README and PyPI description each expose pip install showwork | documented intent | an install occurred |
| proof instructions | README exposes showwork verify and deterministic proof wording | documented behavior | successful use by a reader |
| package reachability | PyPI JSON/page returned version 0.3.0 and Python >=3.10 | indexed metadata | local checkout parity or installation |
| repository reachability | GitHub API/page reachable; counters were 0 stars and 1 fork | public metadata | users, customers, or adoption |
| repeat use | no independent repeat-use evidence in inspected surfaces | unknown | recurring use |
| downloads | PyPI metadata returned -1 sentinels for inspected download fields | unavailable | download volume or users |
| independent adoption | no independent usage evidence observed | refuse | traffic, users, customers, adoption |

The same visible install command can support an answer about documentation for
a human or AI reader. It cannot be promoted to intent, execution, repeat use,
or adoption without separate evidence. Repository counters are public metadata,
not a user count.

An owner-gated measurement plan may predeclare install-intent and repeat-use
evidence separately, with explicit attribution. No telemetry, tracking,
metadata, package, release, public-copy, ranking, traffic, or adoption claim
was made.

Validation: python -m pytest tests/ -q --basetemp=<temp>\showwork-r22-full-20260815 -> **240 passed**
