# showwork r25 proof-receipt and OTel identity mapping

Date: 2026-08-15  
Scope: redacted conceptual mapping; report-only  
Card: `proof-receipt-otel-identity-mapping-20260815-r25`

## Reference context

The [OpenTelemetry GenAI observability article](https://opentelemetry.io/blog/2026/genai-observability/)
describes an `invoke_agent` span with child `chat` and `execute_tool` spans,
and shows that content-bearing attributes may contain sensitive data. The
[GenAI semantic-convention registry](https://opentelemetry.io/docs/specs/semconv/registry/attributes/gen-ai/)
defines concepts including `gen_ai.operation.name`,
`gen_ai.tool.call.id`, `gen_ai.tool.name`, and tool-call arguments/results.
These references describe observability concepts; they do not imply that
showwork emits OTel or that the two identity systems interoperate.

## Mapping

The local fixture used only redacted identifiers and coarse states. “Candidate”
means a possible conceptual correspondence, not a safe join.

| showwork concept | OTel concept | relation | join result |
|---|---|---|---|
| run (`session`, timestamp) | `trace_id` and root `invoke_agent` span | one-to-many | missing by default |
| proof claim (`claim`, session, timestamp) | span event or child event | one-to-many | no stable shared ID |
| proof packet/report artifact | no direct OTel primitive; spans/events may reference it | missing | not safe to join |
| tool invocation | `execute_tool` span plus `gen_ai.tool.call.id/name` | one-to-one candidate | candidate only; showwork does not emit it |
| retry | multiple child spans/events | one-to-many | retry identity missing in showwork |
| refusal (`session.finish.refused`) | span status or error event | one-to-one candidate | semantics can conflict; OTel status is not proof truth |
| timeout/budget observation | span duration/status | one-to-many | does not prove descendant termination |
| descendant/fork observation | child span or span link | one-to-many | reused or conflicting identity possible |

## Join and refusal cases

The synthetic redacted cases were:

| case | showwork ID | OTel IDs | disposition |
|---|---|---|---|
| one-to-many | `run-001` | `trace-001`, `trace-002` | cannot choose one without an owner correlation contract |
| missing | `packet-001` | none | no join; keep separate |
| reused | `tool-001` | `span-001`, `span-001` | refuse identity join until uniqueness is proven |
| conflicting | `packet-002` | `trace-003`, `trace-004` | refuse; do not infer provenance |

The mapping intentionally includes one-to-many, missing, reused, and
conflicting cases. A showwork `session` is not an OTel `trace_id`; a claim is
not automatically a span event; a refusal is not automatically an OTel error;
and a timeout measurement is not proof that descendants stopped. The safe
default for absent or conflicting correlation is “unjoined,” not a guessed
trace.

## Privacy and redaction

The fixture retained only synthetic IDs, state labels, and relation types. It
excluded prompt text, system instructions, tool arguments, tool results,
paths, content payloads, and user identifiers. That boundary matters because
the OTel reference material warns that GenAI messages, tool arguments, and
tool results can contain sensitive data. No telemetry was emitted, exported,
captured, or sent to a collector.

## Owner gate

Any future experiment needs an owner-defined correlation key, one-to-many
rules, uniqueness and lifecycle guarantees, privacy/redaction policy, and
explicit refusal behavior for reused or conflicting IDs. It would also need
to decide whether a local proof artifact is allowed to reference telemetry at
all. This report does not add an OTel dependency, fields, adapter, exporter,
schema, signer, verifier, or interoperability claim.

## Verification

- Eight mapping rows and four redacted join cases validated in memory.
- No telemetry integration or public/production change was made.
- Full repository gate for this cycle: `python -m pytest tests/ -q` -> 240 passed.
