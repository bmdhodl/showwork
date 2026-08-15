# showwork evidence-pack parser-shape robustness r24

Date: 2026-08-15  
Source revision: 6f55b4a  
Scope: redacted in-memory shape fixtures only. No production parser,
serializer, pack format, dashboard, or threshold changed.

## Shape mutation matrix

The same semantic record was represented as JSON, Markdown, CLI text, and
field-separated records. Eight mutations were applied to each encoding, for
32 cells. The fixture classified exact claim fidelity as `answer`,
`qualify`, `unknown`, or `refuse`.

| mutation | fixture condition | classification | exact-claim fidelity |
|---|---|---|---|
| canonical | all decisive fields and disclosure present | answer | exact |
| field order | keys/fields reordered without value changes | answer | exact |
| whitespace | extra surrounding whitespace only | answer | exact |
| marker moved | disclosure marker retained but repositioned | qualify | visible but qualified |
| missing marker | bounded result has no disclosure marker | unknown | not safe |
| omitted decisive | verdict or exit omitted | refuse | not safe |
| malformed value | invalid JSON or invalid exit value | refuse | not safe |
| contradictory | GREEN paired with exit 2 | refuse | not safe |

Field order and whitespace are safe only under the explicit fixture assumption
that the reader is key-aware or trims the representation. They are not proof
that a production parser already has those properties. The missing-marker
cases are false-complete hazards: an intact-looking claim cannot establish
completeness without the disclosure contract. Contradictory decisive fields
refuse rather than allowing a status word to override the exit evidence.

## Boundary

This is a deterministic content/parser contract candidate, not a parser
implementation or compatibility guarantee. Any future parser or content
change remains owner-gated and must preserve refusal for omitted, malformed,
or contradictory decisive evidence. No human-comprehension or adoption claim
is made.

Validation: `python -m pytest tests/ -q` -> **240 passed**.
