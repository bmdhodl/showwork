# Research source: showwork next adapter demand

Date: 2026-08-15

## Question

Which official agent integration surface should showwork target next, if any,
after its CLI, GitHub Action, and Claude Code Stop-hook surfaces?

## Sources consulted

- Claude Code Hooks reference: https://code.claude.com/docs/en/hooks
- OpenAI Agents SDK Agents guide: https://openai.github.io/openai-agents-python/agents/
- OpenAI Agents SDK lifecycle reference: https://openai.github.io/openai-agents-python/ref/lifecycle/
- OpenAI Agents SDK quickstart: https://openai.github.io/openai-agents-python/quickstart/
- LangGraph interrupts: https://langchain-ai.github.io/langgraph/concepts/breakpoints/

## Findings

Claude Code exposes session, turn, tool, subagent, task, and stop lifecycle
events. Hook handlers can be commands, HTTP endpoints, MCP tools, prompts, or
agents, and command hooks receive JSON context on stdin. This is a broad,
useful surface, but showwork already has a Claude Stop-hook adapter and the
generic `run` and GitHub Action paths. A second Claude-specific adapter would
mostly duplicate existing coverage.

The OpenAI Agents SDK exposes two useful Python hook scopes: `RunHooks` for an
entire `Runner.run(...)` invocation and `AgentHooks` for one agent. The official
surface includes agent start/end, LLM start/end, tool start/end, handoff, and
usage context. Installation is `pip install openai-agents`. This gives a thin
integration seam where a hook can start a showwork session, record tool/run
events, and close through the existing exit gate without making model calls in
the adapter tests.

LangGraph's official integration seam is persistence plus interrupts. A graph
uses a checkpointer and `thread_id`; calling `interrupt()` saves graph state
and resumes with `Command`. That is valuable for durable human-in-the-loop
workflows, but it is a graph-state integration rather than a generic lifecycle
observer. The adapter would need to define where a graph run starts and ends
and how node-level outcomes map to claims, making it a larger and less
falsifiable first slice.

## Decision

Select the OpenAI Agents SDK Python hook surface for the next adapter candidate.
Do not implement it from this research card. The follow-up should remain
optional until demand is demonstrated and should preserve showwork's zero
runtime-dependency core by keeping the adapter integration optional.

## Adoption trigger

Track the number of independent external repositories that use the OpenAI
Agents SDK and either request outcome receipts or have a repeated need for
post-run proof. Start implementation when the count reaches three external
repositories, or when one external maintainer/customer explicitly requests the
adapter. Owner-fleet dogfood and showwork's own repository do not count as
external adoption.

## Limits

This is an official-document integration comparison, not an adoption census.
No external usage or customer demand is inferred from the existence of an SDK
hook API. The selected adapter is a research priority, not a release claim.
