"""Claude Code control-plane adapters: approval gates and stuck kills.

Two hook surfaces, one job — keep a long-running agent inside its lane without
the operator watching it.

``PreToolUse``
    Risky actions stop and ask a human. The model does not get to talk its way
    past this: the decision is made outside the model, by pattern, before the
    call executes.

``PostToolUse`` / ``PostToolBatch``
    Every completed call feeds the stuck detector. When the agent stops making
    progress the run is halted, before the next model call rather than after
    the bill arrives.

Why the pattern layer is deterministic and not an LLM judgement: a gate an
agent can argue with is not a gate. Same reason ``showwork finish`` refuses on
a failed check instead of asking a model whether the work looked done.

Cost and token budgets are deliberately absent. Claude Code hooks receive no
usage data (claude-code#11008, open since 2025-11-04), and both Anthropic's
gateway and Cloudflare AI Gateway enforce spend natively and for free. Guessing
at cost from a side channel would be the weakest part of this file, so it does
not exist.
"""

from __future__ import annotations

import fnmatch
import json
import re
from dataclasses import dataclass, field
from typing import Any, Iterable, Sequence

from .guards import StuckDetector, StuckVerdict, ToolCall

__all__ = [
    "ApprovalDecision",
    "RiskPolicy",
    "RiskRule",
    "DEFAULT_RULES",
    "evaluate_pre_tool_use",
    "evaluate_post_tool_use",
    "render_pre_tool_use",
    "render_post_tool_use",
    "MUTATING_TOOLS",
]

# Tools whose successful use means the world changed. Used to tell a retry
# after a real fix apart from a loop that changes nothing.
MUTATING_TOOLS = frozenset(
    {"Write", "Edit", "MultiEdit", "NotebookEdit", "Bash", "PowerShell"}
)

# Bash/PowerShell are in MUTATING_TOOLS because most commands have side effects,
# but plenty are pure reads. Treating `ls` as progress would let an agent spin
# on directory listings forever without ever tripping no_progress.
_READONLY_COMMAND = re.compile(
    r"^\s*(ls|dir|cat|type|head|tail|grep|rg|find|pwd|echo|which|whoami|"
    r"git\s+(status|log|diff|show|branch)|"
    r"python\s+-m\s+pytest|pytest|npm\s+test|cargo\s+test)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class RiskRule:
    """One class of action that must not proceed unattended."""

    name: str
    reason: str
    tools: frozenset[str] = field(default_factory=frozenset)
    path_globs: tuple[str, ...] = ()
    command_pattern: str | None = None

    def matches(self, tool_name: str, tool_input: Any) -> bool:
        if self.tools and tool_name not in self.tools:
            return False

        if self.path_globs:
            path = _extract_path(tool_input)
            if path is None:
                return False
            normalised = path.replace("\\", "/")
            if not any(
                fnmatch.fnmatch(normalised, glob) for glob in self.path_globs
            ):
                return False

        if self.command_pattern:
            command = _extract_command(tool_input)
            if command is None:
                return False
            if not re.search(self.command_pattern, command, re.IGNORECASE):
                return False

        # A rule with no discriminator would match everything; that is a
        # misconfiguration, not a policy.
        return bool(self.path_globs or self.command_pattern or self.tools)


DEFAULT_RULES: tuple[RiskRule, ...] = (
    RiskRule(
        name="ci-workflow",
        reason="CI workflow changes can disable the checks that catch bad work",
        tools=frozenset({"Write", "Edit", "MultiEdit"}),
        path_globs=("*/.github/workflows/*", ".github/workflows/*"),
    ),
    RiskRule(
        name="secrets",
        reason="secret and credential files must never be written unattended",
        tools=frozenset({"Write", "Edit", "MultiEdit"}),
        path_globs=("*.env", "*.env.*", "*/.env*", "*secrets*", "*credentials*"),
    ),
    RiskRule(
        name="db-migration",
        reason="migrations are hard to reverse once applied",
        tools=frozenset({"Write", "Edit", "MultiEdit"}),
        path_globs=("*/migrations/*", "*/supabase/migrations/*"),
    ),
    RiskRule(
        name="history-rewrite",
        reason="force-push and hard reset destroy work that is not recoverable",
        command_pattern=r"(push\s+(-f|--force)|reset\s+--hard|branch\s+-D|clean\s+-[a-z]*f)",
    ),
    RiskRule(
        name="destructive-delete",
        reason="recursive force delete is unrecoverable",
        command_pattern=r"(rm\s+-[a-z]*[rf][a-z]*\s+/|Remove-Item.*-Recurse.*-Force)",
    ),
    RiskRule(
        name="publish",
        reason="publishing is public and cannot be taken back",
        command_pattern=r"(pypi|twine\s+upload|npm\s+publish|gh\s+release\s+create)",
    ),
)


@dataclass(frozen=True)
class ApprovalDecision:
    """Outcome of a PreToolUse evaluation."""

    behavior: str  # "allow" | "deny" | "ask"
    rule: str = ""
    reason: str = ""

    @property
    def blocked(self) -> bool:
        return self.behavior in {"deny", "ask"}


_ALLOW = ApprovalDecision(behavior="allow")


def _extract_path(tool_input: Any) -> str | None:
    if not isinstance(tool_input, dict):
        return None
    for key in ("file_path", "path", "notebook_path", "filePath"):
        value = tool_input.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def _extract_command(tool_input: Any) -> str | None:
    if not isinstance(tool_input, dict):
        return None
    for key in ("command", "cmd", "script"):
        value = tool_input.get(key)
        if isinstance(value, str) and value:
            return value
    return None


@dataclass
class RiskPolicy:
    """A set of rules plus the decision they produce when matched.

    ``behavior`` defaults to ``"ask"`` rather than ``"deny"`` because the point
    is a human in the loop, not a wall. Set it to ``"deny"`` for unattended
    runs where nobody is there to answer.
    """

    rules: Sequence[RiskRule] = DEFAULT_RULES
    behavior: str = "ask"

    def evaluate(self, tool_name: str, tool_input: Any) -> ApprovalDecision:
        for rule in self.rules:
            if rule.matches(tool_name, tool_input):
                return ApprovalDecision(
                    behavior=self.behavior, rule=rule.name, reason=rule.reason
                )
        return _ALLOW


def evaluate_pre_tool_use(payload: dict, policy: RiskPolicy | None = None) -> ApprovalDecision:
    """Decide whether a pending tool call needs a human."""
    policy = policy or RiskPolicy()
    tool_name = payload.get("tool_name") or payload.get("toolName") or ""
    tool_input = payload.get("tool_input") or payload.get("toolInput")
    if not isinstance(tool_name, str):
        return _ALLOW
    return policy.evaluate(tool_name, tool_input)


def render_pre_tool_use(decision: ApprovalDecision) -> str:
    """Serialise a decision into Claude Code's PreToolUse hook contract."""
    payload = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": decision.behavior,
        }
    }
    if decision.blocked:
        payload["hookSpecificOutput"]["permissionDecisionReason"] = (
            f"[showwork:{decision.rule}] {decision.reason}"
        )
    return json.dumps(payload)


def call_from_payload(payload: dict) -> ToolCall:
    """Build a :class:`ToolCall` from a PostToolUse payload.

    ``mutated`` is inferred conservatively: a tool in :data:`MUTATING_TOOLS`
    counts as progress unless it is a recognisably read-only shell command.
    """
    tool_name = payload.get("tool_name") or payload.get("toolName") or ""
    tool_input = payload.get("tool_input") or payload.get("toolInput")
    mutated = tool_name in MUTATING_TOOLS
    if mutated:
        command = _extract_command(tool_input)
        if command and _READONLY_COMMAND.match(command):
            mutated = False
    return ToolCall(tool_name=str(tool_name), tool_input=tool_input, mutated=mutated)


def evaluate_post_tool_use(payload: dict, detector: StuckDetector) -> StuckVerdict:
    """Feed one completed call to the detector and return the verdict."""
    return detector.observe(call_from_payload(payload))


def render_post_tool_use(verdict: StuckVerdict) -> str:
    """Serialise a stuck verdict into a Stop-style halt instruction."""
    if not verdict.stuck:
        return json.dumps({"continue": True})
    return json.dumps(
        {
            "continue": False,
            "stopReason": (
                f"[showwork:stuck:{verdict.reason}] {verdict.detail}. "
                "Halted before further spend."
            ),
        }
    )


def replay(payloads: Iterable[dict], detector: StuckDetector | None = None) -> StuckVerdict:
    """Run a recorded PostToolUse stream through the detector.

    Useful for testing a policy against a real session transcript before
    enabling the hook on live runs.
    """
    detector = detector or StuckDetector()
    verdict = StuckVerdict(stuck=False)
    for payload in payloads:
        verdict = evaluate_post_tool_use(payload, detector)
        if verdict.stuck:
            break
    return verdict
