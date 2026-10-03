# Cursor CLI availability follow-up, October 3, 2026

Prepared for [#99](https://github.com/bmdhodl/showwork/issues/99). This corrects
the earlier host inventory; it does not certify a completed Cursor task or close
the card's owner/date/host prerequisites.

## Observed launcher and startup

PowerShell's default `agent` resolves to Grok. Inspecting `Get-Command agent -All`
also found a separately installed Cursor Agent PowerShell/command launcher.
Its actual version output is `2026.09.15-d2fe57e`. The inspected launcher selects
its bundled Node runtime and CLI entrypoint; no install or update was performed.

The actual pinned-runtime probe used a new public toy workspace, `--print`,
`--mode ask` and JSON output. Its prompt requested only `CURSOR_TOY_READY`, with
no tools, file reads or changes. The process exited 1 in 1.812 seconds. Its
diagnostic was `Workspace Trust Required`, and the requested readiness token was
absent. The first harness incorrectly set `CURSOR_AGENT_PERSIST_SESSION=0`,
assuming it was a Boolean switch. Inspection of the pinned CLI showed that it
accepts a session name; `0` matches its marker grammar. The first report's
`persistent_terminal_session_enabled: false` field is therefore invalid as
evidence of the marker being disabled. The
[first observation](cursor-availability-20261003/first-observation.json) is
retained with that qualification.

The repeat explicitly removed that variable from the child environment. It
also exited 1 with the same trust diagnostic and no readiness token, in 0.744
seconds. This establishes a runnable launcher and a real host trust refusal.
It does not establish loaded rules, native Stop dispatch or an acceptance task.

The corrected child environment had no persistent-session marker. Local probe
data used a validated throwaway directory. This does not certify general history
retention, model-provider data handling or an account privacy change. Raw host
logs stay local; the public
[sanitized observation](cursor-availability-20261003/startup-observation.json)
contains no account or credential fields.

## Prepared trial and remaining gate

Two public toy workspaces are prepared separately from the product checkout.
One has incorrect `add(2, 2)` behavior; the other counts a blank line as nonempty.
Each has a real production probe that returns exit 2 under optimized Python,
native Cursor recipe files, and a distinct predeclared behavior requirement.
File hashes and broken-control output are retained locally for owner review.
Preparing these fixtures is not a Cursor-authored repair or customer activation.

Workspace trust is held for owner review under the existing security-settings
boundary. The proposed authorization applies only to those two throwaway public
toy folders and normally reviewed task execution. It grants no trust to another
repository and no unrestricted tool mode. No `--force`, `--yolo`, automatic MCP
approval or global trust change was used to get past the refusal.

After approval, retain the actual task/refusal/repair path, native Stop dispatch,
interruption, repeated independent slug and exact generated-file uninstall.
Record elapsed time and unexpected refusals with their actual denominators.
The installed version and a startup probe cannot substitute for those outcomes.
The existing #92/#97 dependencies and October 13 owner decision remain visible.

[Cursor CLI documentation](https://cursor.com/docs/cli/overview) distinguishes
headless operation and read-only modes. The
[native hook documentation](https://cursor.com/docs/hooks) requires project trust
before project hooks run. Those are current vendor documentation claims;
the observation above is the locally measured result.

Sign-off: OpenAI | GPT-6 | auto.
