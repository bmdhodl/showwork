# showwork r21: receipt projection exact-claim fidelity

Date: 2026-08-15  
Scope: disposable redacted receipt dictionaries and synthetic reader
projections. No packer, serializer, schema, dashboard, public-copy, or
performance change.

## Fidelity matrix

| state | full projection | field-separated projection | bounded projection | truncation visible |
|---|---|---|---|---|
| normal | all six decisive fields exact | all six exact | claim and scope lost | yes |
| RED | all six decisive fields exact | all six exact | claim, refusal reason, and scope lost | yes |
| refused | all six decisive fields exact | all six exact | claim, refusal reason, and scope lost | yes |
| blocked | all six decisive fields exact | all six exact | claim, refusal reason, and scope lost | yes |
| contradictory | all six decisive fields exact | all six exact | claim, refusal reason, and scope lost | yes |

The decisive fields were status, claims verdict, command exit, scope, exact
claim text, and refusal reason. The bounded projection used a 32-character
limit and appended [truncated]. It preserved short status, verdict, and exit
values, but exact claim and refusal context did not survive. The
field-separated projection retained all tested decisive values while making
truncation state explicit.

## Reader boundary

A bounded projection with a visible marker can answer that evidence was
shortened. It cannot support the original exact claim or refusal explanation.
Without a visible marker, a reader could mistake an excerpt for the complete
proof and produce a false-green or false-red interpretation. The projection
must not be treated as a complete receipt merely because its status field is
GREEN.

An owner-gated representation review may choose a projection contract that
preserves decisive fields and links to complete evidence. This report does not
authorize a packer, serializer, schema, dashboard, public-copy, performance,
or adoption change.

Validation: python -m pytest tests/ -q --basetemp=<temp>\showwork-r21-full-20260815 -> **239 passed**
