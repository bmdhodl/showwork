# Project-local host recipes

Use the project Python environment with showwork 0.6.6 or later. Version 0.6.5
and earlier lack `host-stop-hook`, previews and uninstall.

```text
python -m showwork init --codex --preview
python -m showwork init --codex
python -m showwork init --claude --preview
python -m showwork init --cursor --preview
python -m showwork init --codex --uninstall --preview
python -m showwork init --codex --uninstall
```

Select a host explicitly. Preview lists paths and creates nothing, including for
a nonexistent root. Installation merges native hook entries, preserving foreign
hooks and unknown configuration keys. Uninstall removes only unchanged generated
files and hook entries. User-edited skill/rule files and edited commands stay in
place for review. Malformed host JSON fails clearly and is never overwritten,
including with `--force`. No global configuration or trust entry is changed.

| Host | Project files | Stop response | Binding |
| --- | --- | --- | --- |
| Codex | `.codex/hooks.json`, `.agents/skills/showwork-receipts/SKILL.md` | `{"continue":true}` on stdout | `SHOWWORK_SESSION` in launcher environment |
| Claude Code | `.claude/settings.json` | `{}` on stdout | Same explicit launcher environment |
| Cursor | `.cursor/hooks.json`, `.cursor/rules/showwork.mdc` | `{}` on stdout; no follow-up message | Same explicit launcher environment |

Choose a unique showwork task slug, then set `SHOWWORK_SESSION` before launching
the host. An export in a child tool shell cannot change the parent's environment.
The observer does not create a writer from an unbound host UUID, conversation ID,
message or transcript path. A missing binding stays UNVERIFIED. Host IDs are not
used as execution authorization. Start and declare requirements before claims;
run explicit `finish --status ok` and the committed `gate --require-tracked`.

The native Stop command accepts at most 32 KiB of UTF-8 payload and reads receipts
with the bounded process-free reader. It writes no events, launches no acceptance
command and makes no network request. Its stderr reports recorded scope,
integrity, freshness and limitations. It returns zero and host-valid JSON even
for malformed input, missing evidence or a failed recorded outcome. Repeated Stop
events leave explicit closes and other writers' bytes intact. It does not request
another agent turn. Post-stop observation cannot undo work or enforce pre-dispatch
policy. Behavior acceptance belongs to explicit trusted verification.

An existing legacy `stop-hook` command is recognized during installation and kept
to avoid changing an edited hook or installing a duplicate. That legacy observer
can execute checks and append an observation. To adopt the new bounded recipe,
review and remove the old showwork entry yourself, then preview/install the new
one. Uninstall does not delete an edited or legacy entry it did not generate.

Codex's [native hook documentation](https://learn.chatgpt.com/docs/hooks) requires
project trust and review of the exact command via `/hooks`. Installation does not
grant that trust, and this recipe never bypasses it. Claude's
[Stop lifecycle documentation](https://code.claude.com/docs/en/hooks) distinguishes
normal Stop from interruption/error events. Cursor's
[hook documentation](https://cursor.com/docs/hooks) uses the lowercase `stop`
event. This observer emits no Cursor continuation request.

## Compatibility and proof boundaries

Versions inspected on October 3, 2026: Codex CLI 0.154.0, Claude Code 2.1.238,
Cursor 3.22.7 (Windows x64 desktop), and Cursor Agent CLI
`2026.09.15-d2fe57e`. Presence and version output do not establish host activation.
The initial inspection missed the separately installed Cursor Agent launcher:
the default `agent` command resolved to Grok. In PowerShell, inspect
`Get-Command agent -All` and select the actual Cursor launcher explicitly.

The pinned Cursor CLI's tool-free startup probe exited 1 with `Workspace Trust
Required` for the isolated public toy workspace. No readiness response or task
activation was observed. Installation does not grant workspace trust; review the
workspace and exact hook command through the host's normal trust flow. Native
desktop automation remains unavailable. The
[CLI availability follow-up](reports/cursor-availability-20261003.md) records the
corrected discovery and remaining trust/task evidence boundary.

Deterministic tests cover preview, repeated installation, removal, edited file
preservation, foreign hooks, invalid JSON, bound/unbound payloads, malformed and
oversized payloads, no process execution and byte-preserved explicit closes for
all three response protocols. The Codex skill passes the skill validator. These
tests exercise the command protocol; they are not three real-host agent runs.

The [actual host probe report](reports/native-hosts-20261003.md) retains the
observed Claude Stop dispatch and the Codex/Cursor availability limits.

A real-host smoke must retain the actual launched version, binding, loaded rule
or skill, tool/check evidence, host Stop dispatch and final explicit gate. Run a
lying claim first and retain its refusal, repair the real artifact, then retain a
successful close. A second independent task needs a different slug. Record absent
trust, unavailable UI/CLI, provider limits and missing dispatch as untested or
unavailable; do not count a synthetic payload as activation. The report retains
two driver-controlled Claude behavior sessions proving its Stop boundary and
uninstall, without claiming host-authored task completion. Codex and Cursor's
required actual task runs remain outstanding on #97/#99.
