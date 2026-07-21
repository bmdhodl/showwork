"""showwork CLI: record falsifiable claims, verify them, gate session exits.

    showwork start  --session S [--agent A] [--note N]
    showwork claim  --session S --claim TEXT --type file_contains --path F --pattern P
    showwork retract --session S --claim TEXT --reason R
    showwork verify [--date YYYY-MM-DD | --session S] [--json] [--no-report]
    showwork finish --session S [--status ok|blocked] [--no-verify] [--note N]

Exit codes: 0 GREEN, 3 YELLOW, 2 RED (and `finish --status ok` exits 2 when
this session's own claims do not verify).
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

from .audit import audit_root, render_audit
from .budgets import RunBudget
from .checks import EXIT_BY_VERDICT, render_report
from .dashboard import render as render_dashboard
from .control import (
    RiskPolicy,
    call_from_payload,
    evaluate_pre_tool_use,
    render_post_tool_use,
    render_pre_tool_use,
)
from .guards import StuckDetector, ToolCall
from .hooks import observe_stop, read_stop_payload
from .ledger import (
    ROOT_ENV,
    finish_session,
    ledger_dir,
    record_claim,
    record_event,
    record_retraction,
    resolve_root,
    start_session,
    verify_date,
    verify_session,
)

SESSION_ENV = "SHOWWORK_SESSION"

CHECK_TYPES = ["file_exists", "file_contains", "path_moved", "frontmatter",
               "glob_count", "command"]


def _build_check(args: argparse.Namespace) -> dict | None:
    if args.check_json:
        try:
            check = json.loads(args.check_json)
        except json.JSONDecodeError as e:
            raise SystemExit(f"--check-json is not valid JSON: {e}") from e
        if not isinstance(check, dict):
            raise SystemExit("--check-json must be a JSON object")
        return check
    t = args.type
    if not t:
        return None
    if t == "file_exists":
        return {"type": t, "path": _req(args, "path")}
    if t == "file_contains":
        c = {"type": t, "path": _req(args, "path"), "pattern": _req(args, "pattern")}
        if args.absent:
            c["absent"] = True
        return c
    if t == "path_moved":
        return {"type": t, "from": _req(args, "from_path"), "to": _req(args, "to_path")}
    if t == "frontmatter":
        return {"type": t, "path": _req(args, "path"), "field": _req(args, "field"),
                "equals": _req(args, "equals")}
    if t == "glob_count":
        return {"type": t, "pattern": _req(args, "pattern"), "op": _req(args, "op"),
                "n": _req(args, "n")}
    if t == "command":
        c = {"type": t, "argv": _req(args, "command_arg")}
        if args.expect_exit is not None:
            c["expect_exit"] = args.expect_exit
        if args.stdout_contains:
            c["stdout_contains"] = args.stdout_contains
        return c
    raise SystemExit(f"unknown check type {t!r}")


def _req(args: argparse.Namespace, name: str):
    val = getattr(args, name, None)
    if val is None or val == [] or val == "":
        flag = "--" + name.replace("_", "-")
        raise SystemExit(f"check type {args.type!r} requires {flag}")
    return val


def _audit_report_path(ledger: Path, label: str) -> Path:
    """Build audit-<label>.md as a single path segment under the ledger dir.

    Session ids and date labels are attacker-controlled strings in some
    workflows. Replacing only spaces left '/', '\\\\', and '..' intact, so
    joining the label into the report path could resolve outside `.showwork/`.
    """
    stem = str(label).replace(" ", "-")
    for bad in ("/", "\\", "\0", ":"):
        stem = stem.replace(bad, "_")
    while ".." in stem:
        stem = stem.replace("..", "_")
    if not stem or stem in (".", "_"):
        stem = "unknown"
    report = (ledger / f"audit-{stem}.md").resolve()
    try:
        report.relative_to(ledger.resolve())
    except ValueError as exc:
        raise SystemExit(
            f"refusing to write audit report outside ledger dir: {report}"
        ) from exc
    return report


def _print_state(state: dict, as_json: bool) -> None:
    if as_json:
        print(json.dumps(state, indent=2))
        return
    print(f"showwork verify - {state['label']}  =>  {state['verdict']}  "
          f"({state['passed']}/{state['total']} verified)")
    marks = {"pass": "OK ", "fail": "XX ", "error": "!! ", "skipped": ".. "}
    for r in state["results"]:
        print(f"  {marks.get(r['status'], '?? ')} {r['claim']}")
        print(f"       {r['detail']}")
    if state["gaps"]:
        print(f"\n{len(state['gaps'])} gap(s): a claimed 'done' is not backed by reality.")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="showwork",
                                 description="falsifiable claims + deterministic verification for AI agents")
    ap.add_argument("--root", default=None,
                    help="project root (default: $SHOWWORK_ROOT or cwd)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("start", help="record session.start")
    p.add_argument("--session", required=True)
    p.add_argument("--agent")
    p.add_argument("--note")

    p = sub.add_parser("claim", help="append a falsifiable claim")
    p.add_argument("--session", required=True)
    p.add_argument("--claim", required=True)
    p.add_argument("--severity", default="RED", choices=["RED", "YELLOW"])
    p.add_argument("--artifact")
    p.add_argument("--check-json")
    p.add_argument("--type", choices=CHECK_TYPES)
    p.add_argument("--path")
    p.add_argument("--pattern")
    p.add_argument("--absent", action="store_true")
    p.add_argument("--from-path", dest="from_path")
    p.add_argument("--to-path", dest="to_path")
    p.add_argument("--field")
    p.add_argument("--equals")
    p.add_argument("--op", choices=["==", ">=", "<=", ">", "<"])
    p.add_argument("--n", type=int)
    p.add_argument("--command-arg", dest="command_arg", action="append",
                   help="repeat per argv token, e.g. --command-arg python --command-arg scripts/check.py")
    p.add_argument("--expect-exit", dest="expect_exit", type=int)
    p.add_argument("--stdout-contains", dest="stdout_contains")

    p = sub.add_parser("retract", help="append-only retraction of an earlier claim")
    p.add_argument("--session", required=True)
    p.add_argument("--claim", required=True, help="exact text of the claim being retracted")
    p.add_argument("--reason", required=True)

    p = sub.add_parser("verify", help="verify claims; exit 0 GREEN, 3 YELLOW, 2 RED")
    p.add_argument("--date", help="verify one day's ledger (default: today)")
    p.add_argument("--session", help="verify one session's claims across all days")
    p.add_argument("--json", action="store_true")
    p.add_argument("--no-report", action="store_true",
                   help="do not write the markdown audit report")

    p = sub.add_parser("finish", help="record session.finish; a clean close verifies own claims first")
    p.add_argument("--session", required=True)
    p.add_argument("--status", default="ok", choices=["ok", "blocked"])
    p.add_argument("--no-verify", action="store_true",
                   help="deliberately bypass the exit gate (stamped on the event)")
    p.add_argument("--note")

    p = sub.add_parser("audit", help="verify the ledger's integrity chain; exit 0 GREEN, 3 YELLOW, 2 RED")
    p.add_argument("--json", action="store_true")
    p.add_argument("--strict", action="store_true",
                   help="forbid forks: a concurrent branch is RED, not an accepted merge")

    p = sub.add_parser("run", help="wrap any command in a session: start, run, record the verdict")
    p.add_argument("--session", required=True)
    p.add_argument("--agent")
    p.add_argument("--gate", action="store_true",
                   help="exit 2 when the command succeeds but this session's claims are RED")
    p.add_argument("--max-seconds", type=float,
                   help="halt the wrapped command after this wall-clock budget")
    p.add_argument("command", nargs=argparse.REMAINDER,
                   help="the command to wrap, after --")

    p = sub.add_parser("stop-hook", help="observe a coding-agent Stop hook; never gates")
    p.add_argument("--status", default="ok")

    p = sub.add_parser(
        "dashboard",
        help="render runs/status/interventions/proof-of-work; optionally serve it",
    )
    p.add_argument("--replay", type=Path, required=True,
                   help="replay_transcripts.py --json output")
    p.add_argument("--out", type=Path, default=Path("showwork-dashboard.html"))
    p.add_argument("--serve", type=int, metavar="PORT", nargs="?", const=8787,
                   help="serve on localhost after rendering (default port 8787)")

    p = sub.add_parser(
        "guard",
        help="PreToolUse/PostToolUse hook: gate risky actions, halt stuck runs",
    )
    p.add_argument("--event", choices=["pre", "post"], required=True,
                   help="pre = approval gate; post = stuck detection")
    p.add_argument("--behavior", choices=["ask", "deny"], default="ask",
                   help="what a matched risk rule does (deny suits unattended runs)")
    p.add_argument("--repeat-threshold", type=int, default=3)
    p.add_argument("--state", default=".showwork/guard-state.json",
                   help="where PostToolUse keeps its rolling call window")

    args = ap.parse_args(argv)
    root = resolve_root(args.root)

    if args.cmd == "start":
        start_session(root, args.session, agent=args.agent, note=args.note)
        print(f"session.start recorded: {args.session}")
        return 0

    if args.cmd == "claim":
        check = _build_check(args)
        record_claim(root, args.session, args.claim, check=check,
                     severity=args.severity, artifact=args.artifact)
        print("claim recorded" + ("" if check else " (no check: recorded, not verifiable)"))
        return 0

    if args.cmd == "retract":
        record_retraction(root, args.session, args.claim, args.reason)
        print("retraction recorded")
        return 0

    if args.cmd == "verify":
        if args.session:
            state = verify_session(root, args.session)
        else:
            try:
                state = verify_date(root, args.date)
            except ValueError as e:
                raise SystemExit(str(e)) from e
        if not args.no_report:
            report = _audit_report_path(ledger_dir(root), state["label"])
            report.parent.mkdir(parents=True, exist_ok=True)
            report.write_text(render_report(state), encoding="utf-8")
        _print_state(state, args.json)
        return EXIT_BY_VERDICT[state["verdict"]]

    if args.cmd == "finish":
        code, state = finish_session(root, args.session, status=args.status,
                                     no_verify=args.no_verify, note=args.note)
        if state is not None:
            print(f"claims: {state['verdict']} ({state['passed']}/{state['total']} verified)")
        if code != 0:
            print("REFUSED: a clean close requires this session's claims to verify. "
                  "Fix the gap, retract the claim, or finish --status blocked.",
                  file=sys.stderr)
        else:
            print(f"session.finish recorded: {args.session}")
        return code

    if args.cmd == "audit":
        state = audit_root(root, strict=args.strict)
        if args.json:
            print(json.dumps(state, indent=2))
        else:
            print(render_audit(state))
        return EXIT_BY_VERDICT[state["verdict"]]

    if args.cmd == "run":
        cmd = list(args.command)
        if cmd and cmd[0] == "--":
            cmd = cmd[1:]
        if not cmd:
            raise SystemExit("run requires a command after --")
        if args.max_seconds is not None and args.max_seconds <= 0:
            raise SystemExit("--max-seconds must be > 0")
        budget = RunBudget(max_seconds=args.max_seconds)
        budget.start()
        start_session(root, args.session, agent=args.agent,
                      note="wrapped: " + " ".join(cmd) +
                           (f"; max_seconds={args.max_seconds:g}" if args.max_seconds else ""))
        # The wrapped process inherits the session and root, so anything it
        # runs can record claims without extra plumbing.
        env = {**os.environ, SESSION_ENV: args.session, ROOT_ENV: str(root)}
        try:
            proc_code = subprocess.run(
                cmd, cwd=str(root), env=env, timeout=args.max_seconds
            ).returncode
        except subprocess.TimeoutExpired:
            verdict = budget.check()
            state = verify_session(root, args.session)
            record_event(
                root, "session.finish", args.session,
                status="budget_exceeded", claims_verdict=state["verdict"],
                command_exit=124, observed_by="run-wrapper",
                budget_max_seconds=args.max_seconds,
                budget_elapsed_seconds=round(budget.elapsed, 3),
                budget_exceeded=True, budget_reason="time",
            )
            print(
                f"BUDGET: wrapped command exceeded {args.max_seconds:g}s wall clock "
                f"({budget.elapsed:.1f}s elapsed).",
                file=sys.stderr,
            )
            return 2
        except FileNotFoundError as exc:
            record_event(root, "session.finish", args.session, status="error",
                         observed_by="run-wrapper", note=f"command not found: {exc}")
            print(f"showwork run: command not found: {cmd[0]}", file=sys.stderr)
            return 127
        state = verify_session(root, args.session)
        verdict = budget.check()
        record_event(root, "session.finish", args.session,
                     status=("ok" if proc_code == 0 else "error"),
                     claims_verdict=state["verdict"], command_exit=proc_code,
                     observed_by="run-wrapper",
                     budget_max_seconds=args.max_seconds,
                     budget_elapsed_seconds=round(budget.elapsed, 3),
                     budget_exceeded=verdict.exceeded,
                     budget_reason=verdict.reason)
        print(f"wrapped command exit {proc_code}; claims: {state['verdict']} "
              f"({state['passed']}/{state['total']} verified)")
        if args.gate and proc_code == 0 and state["verdict"] == "RED":
            print("GATE: the command reported success but this session's "
                  "claims do not verify.", file=sys.stderr)
            return 2
        return proc_code

    if args.cmd == "stop-hook":
        try:
            payload = read_stop_payload(sys.stdin)
            _event, state = observe_stop(root, payload, status=args.status)
            print(f"stop observed: {state['verdict']} "
                  f"({state['passed']}/{state['total']} verified)")
        except Exception as exc:  # noqa: BLE001
            # A Stop hook is post-hoc telemetry. Breaking the host's shutdown
            # path would turn an evidence adapter into an availability risk.
            print(f"showwork stop-hook: {exc}", file=sys.stderr)
        return 0

    if args.cmd == "dashboard":
        if not args.replay.exists():
            print(f"no replay data at {args.replay}", file=sys.stderr)
            return 2
        data = json.loads(args.replay.read_text(encoding="utf-8"))
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(render_dashboard(data), encoding="utf-8")
        print(f"wrote {args.out} ({args.out.stat().st_size:,} bytes)")

        if args.serve:
            # Bound to loopback on purpose. This renders real session ids,
            # project paths, and tool arguments; it is not something to expose
            # on a network interface by accident.
            import http.server
            import socketserver

            directory = str(args.out.parent.resolve())
            name = args.out.name

            class Handler(http.server.SimpleHTTPRequestHandler):
                def __init__(self, *a, **kw):
                    super().__init__(*a, directory=directory, **kw)

                def log_message(self, *a):  # quiet
                    pass

            with socketserver.TCPServer(("127.0.0.1", args.serve), Handler) as httpd:
                print(f"serving http://127.0.0.1:{args.serve}/{name}  (ctrl-c to stop)")
                try:
                    httpd.serve_forever()
                except KeyboardInterrupt:
                    print("\nstopped")
        return 0

    if args.cmd == "guard":
        # Unlike stop-hook, this one CAN refuse. It still fails open on its own
        # internal errors: a guard that crashes the agent it protects is a
        # worse outage than the loop it was watching for.
        try:
            payload = json.load(sys.stdin)
            if not isinstance(payload, dict):
                raise ValueError("hook payload must be a JSON object")
        except Exception as exc:  # noqa: BLE001
            print(f"showwork guard: unreadable payload: {exc}", file=sys.stderr)
            return 0

        try:
            if args.event == "pre":
                decision = evaluate_pre_tool_use(
                    payload, RiskPolicy(behavior=args.behavior)
                )
                print(render_pre_tool_use(decision))
                return 0

            state_path = Path(args.state)
            window = _load_guard_window(state_path)
            detector = StuckDetector(repeat_threshold=args.repeat_threshold)
            call = call_from_payload(payload)
            verdict = detector.observe_all(
                [ToolCall(**item) for item in window] + [call]
            )
            _save_guard_window(state_path, window, call, verdict.stuck)
            print(render_post_tool_use(verdict))
            # Exit 2 halts the agentic loop before the next model call.
            return 2 if verdict.stuck else 0
        except Exception as exc:  # noqa: BLE001
            print(f"showwork guard: {exc}", file=sys.stderr)
            return 0

    return 2  # unreachable


def _load_guard_window(path: Path, limit: int = 24) -> list[dict]:
    """Read the rolling tool-call window.

    A PostToolUse hook is a fresh process per call, so the window has to live on
    disk or every call looks like the first one. Any read failure yields an
    empty window: the guard then under-detects for a few calls, which is the
    safe direction to fail.
    """
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        calls = data.get("calls", [])
        if not isinstance(calls, list):
            return []
        return [c for c in calls if isinstance(c, dict)][-limit:]
    except (OSError, ValueError, TypeError):
        return []


def _save_guard_window(
    path: Path, window: list[dict], call: ToolCall, tripped: bool, limit: int = 24
) -> None:
    """Persist the window. Clears once tripped so a killed run starts clean."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        calls = [] if tripped else (window + [
            {
                "tool_name": call.tool_name,
                "tool_input": call.tool_input,
                "mutated": call.mutated,
            }
        ])[-limit:]
        path.write_text(json.dumps({"calls": calls}), encoding="utf-8")
    except (OSError, TypeError, ValueError):
        # Losing the window degrades detection; it must never break the agent.
        pass


if __name__ == "__main__":
    raise SystemExit(main())
