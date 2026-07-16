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

from .audit import audit_root, render_audit
from .checks import EXIT_BY_VERDICT, render_report
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
        check = json.loads(args.check_json)
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

    p = sub.add_parser("run", help="wrap any command in a session: start, run, record the verdict")
    p.add_argument("--session", required=True)
    p.add_argument("--agent")
    p.add_argument("--gate", action="store_true",
                   help="exit 2 when the command succeeds but this session's claims are RED")
    p.add_argument("command", nargs=argparse.REMAINDER,
                   help="the command to wrap, after --")

    p = sub.add_parser("stop-hook", help="observe a coding-agent Stop hook; never gates")
    p.add_argument("--status", default="ok")

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
            state = verify_date(root, args.date)
        if not args.no_report:
            report = ledger_dir(root) / f"audit-{state['label'].replace(' ', '-')}.md"
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
        state = audit_root(root)
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
        start_session(root, args.session, agent=args.agent,
                      note="wrapped: " + " ".join(cmd))
        # The wrapped process inherits the session and root, so anything it
        # runs can record claims without extra plumbing.
        env = {**os.environ, SESSION_ENV: args.session, ROOT_ENV: str(root)}
        try:
            proc_code = subprocess.run(cmd, cwd=str(root), env=env).returncode
        except FileNotFoundError as exc:
            record_event(root, "session.finish", args.session, status="error",
                         observed_by="run-wrapper", note=f"command not found: {exc}")
            print(f"showwork run: command not found: {cmd[0]}", file=sys.stderr)
            return 127
        state = verify_session(root, args.session)
        record_event(root, "session.finish", args.session,
                     status=("ok" if proc_code == 0 else "error"),
                     claims_verdict=state["verdict"], command_exit=proc_code,
                     observed_by="run-wrapper")
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

    return 2  # unreachable


if __name__ == "__main__":
    raise SystemExit(main())
