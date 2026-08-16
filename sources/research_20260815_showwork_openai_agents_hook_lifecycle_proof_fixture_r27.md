# OpenAI Agents hook lifecycle proof fixture — r27

Date: 2026-08-15  
Scope: report-only fake event stream and disposable local ledger; no SDK
installation, provider call, adapter, receipt-schema change, public copy, or
release.  
Source card: `openai-agents-hook-lifecycle-proof-fixture-20260815-r27.md`

## Reference context

The supplied [OpenAI Agents SDK Agents guide](https://openai.github.io/openai-agents-python/agents/)
describes `RunHooks` as observing a whole `Runner.run(...)`, including
handoffs, and `AgentHooks` as scoped to one agent. It describes agent start/end,
LLM start/end, tool start/end, and handoff callbacks, with tool contexts able
to expose a tool-call identifier. This is reference context, not a claim that
showwork currently supports the SDK.

## Fake stream and current receipt mapping

The disposable stream contained: run start; triage agent start; model start and
end; tool start and end; handoff to a specialist; specialist start/end; triage
end; and run end. Every event carried a fake `run-1` join key and was labeled
observation-only.

| fake event | possible current concept | proof boundary |
|---|---|---|
| run start | `session.start` | identifies a candidate session; proves no outcome |
| agent/model/tool start/end | session context or a future observation record | timing and IDs do not prove a filesystem or command outcome |
| handoff and nested agent events | same run candidate plus agent/event sequence | one run can contain many agents; a tool or handoff ID is not a receipt join policy |
| checked artifact materialized | `claim` with an existing deterministic check | only the check can verify the claimed outcome |
| successful run end | `session.finish` after verification | clean close is gated by claim verdict |
| exception or refusal | possible failed-run input | does not itself prove a false outcome or authorize a new ledger event |
| failed clean close | `session.finish.refused` | existing gate evidence, not hook observation alone |

The same local fixture then used the existing ledger API for one success and
one failing claim. The success closed with code 0 and GREEN. The failing claim
closed with code 2 and RED refusal. No fake hook was allowed to write a new
schema or adapter record.

## Lossiness and privacy boundaries

The lifecycle stream can lose ordering if callbacks are delivered concurrently
or retried, and a handoff can create multiple agent-local sequences under one
run. A candidate join key therefore needs run identity plus an event sequence
or provider-issued event identity; neither was selected here. A hook's model
name, tool arguments, outputs, prompts, context, usage, exception text, and
user data can contain sensitive content. A future integration would need an
explicit minimization/redaction policy and retention boundary before storing
any of those fields. Timing or `tool_call_id` alone is observation, not proof.

## Threshold for future adapter work

Do not build an adapter from this fixture alone. A future adapter would need a
documented provider contract for callback ordering/retry behavior, stable run
and event identity, a privacy/redaction decision, a deterministic mapping from
observed outcomes to existing checkable claims, and a refusal test proving that
an exception or hook callback cannot manufacture a GREEN close. It would also
need a disposable integration fixture or first-party test surface; this report
does not supply that evidence.

## External-standard and evidence gaps

The OpenAI guide is documentation evidence about the named hook surfaces, not
a version-pinned compatibility guarantee, and no SDK package or real provider
was exercised. The fake stream cannot establish callback behavior under
streaming, retries, cancellation, parallel tools, nested handoffs, or SDK
version drift. No external adoption, performance, reliability, privacy,
compliance, or compatibility claim follows.

## Boundary

No adapter, hook integration, signer, timestamp, schema, checker, public copy,
provider call, package release, or real Git state changed.
