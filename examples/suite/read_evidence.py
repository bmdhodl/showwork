"""Offline example, not a supported SDK API or persisted join contract.

Requires the pinned source-built showwork reader described in the README.
AgentGuard remains independent: its existing JSON receipt and trace are inputs.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re

from showwork.reader import inspect_loaded, load_receipt, read_bytes
from showwork.snapshot import capture_tree


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def invalid_number(value):
    raise ValueError("nonfinite JSON value")


def local_bytes(root, relative):
    if not isinstance(relative, str) or not relative or Path(relative).is_absolute() or ".." in Path(relative).parts:
        raise ValueError("reference must be workspace-relative")
    return read_bytes(root, root / relative)


def decode_json(raw):
    return json.loads(raw.decode("utf-8"), object_pairs_hook=unique_object, parse_constant=invalid_number)


def runtime_observation(root, trace, receipt):
    unknown = {"state": "unknown", "reason": "runtime reference missing, incompatible or changed"}
    try:
        raw = local_bytes(root, trace)
        data = decode_json(local_bytes(root, receipt))
        if not isinstance(data, dict) or data.get("version") != "1.4.1":
            return unknown
        events = [decode_json(line.encode()) for line in raw.decode("utf-8").splitlines() if line.strip()]
        if not events or any(not isinstance(event, dict) for event in events):
            return unknown
        if data.get("trace") != Path(trace).name or data.get("sha256") != hashlib.sha256(raw).hexdigest():
            return unknown
        for key in ("events", "llm_calls", "tool_calls", "budget_warnings"):
            if type(data.get(key)) is not int or data[key] < 0:
                return unknown
        if data["events"] != len(events) or not isinstance(data.get("stops"), list):
            return unknown
        if any(not isinstance(stop, dict) or stop.get("kind") not in {"budget", "loop", "retry"}
               or not isinstance(stop.get("detail"), str) for stop in data["stops"]):
            return unknown
        return {"state": "stopped" if data["stops"] else "no_recorded_stop",
                "trace": trace, "receipt": receipt, "sha256": data["sha256"],
                "events": data["events"], "llm_calls": data["llm_calls"],
                "tool_calls": data["tool_calls"], "stop_kinds": [stop["kind"] for stop in data["stops"]],
                "version": data["version"], "origin_authentication": "not established"}
    except (OSError, ValueError, TypeError, UnicodeError):
        return unknown


def bound_command(root, command, requirement, revision, frozen_scope):
    """Reuse source identity calculation, without executing a recorded check."""
    evidence = command.get("evidence")
    check = requirement.get("check")
    if not isinstance(evidence, dict) or not isinstance(check, dict):
        return False
    argv = check.get("argv")
    recorded_argv = evidence.get("argv")
    if (check.get("type") != "command" or not isinstance(argv, list) or len(argv) < 2
            or not isinstance(recorded_argv, list) or len(recorded_argv) < 2
            or evidence.get("git_commit") != revision or evidence.get("showwork_version") != "0.6.5"):
        return False
    script = (root / argv[1]).resolve()
    if not script.is_relative_to(root) or Path(recorded_argv[1]).resolve() != script:
        return False
    if hashlib.sha256(read_bytes(root, script)).hexdigest() != evidence.get("script_sha256"):
        return False
    scope = evidence.get("source_exclusions") or {}
    if scope and scope != frozen_scope or not scope and frozen_scope.get("ignore_patterns"):
        return False
    files = capture_tree(root, ignore=scope.get("ignore_patterns"))
    source = {"files": files, **scope} if scope else files
    return hashlib.sha256(json.dumps(source, sort_keys=True).encode()).hexdigest() == evidence.get("source_sha256")


def acceptance_observation(root, session, requirement_id, revision):
    result = {"state": "unknown", "reference_bound": False, "claim_state": "unknown",
              "requirement": None, "command_evidence": None,
              "reason": "acceptance reference missing, incompatible, stale or mismatched"}
    try:
        receipt = load_receipt(root, session)
        inspection = inspect_loaded(receipt)
        result["reader"] = inspection
        if receipt["claims"]:
            result["claim_state"] = "checked_claims" if any(row.get("check") for row in receipt["claims"]) else "claimed"
        requirements = [row for row in receipt["events"] if row.get("event") == "session.requirement"]
        selected = [row for row in requirements if row.get("requirement_id") == requirement_id]
        if len(selected) != 1:
            return result
        requirement = selected[0]
        result["requirement"] = {key: requirement.get(key) for key in ("requirement_id", "claim", "scope", "check")}
        if (not isinstance(revision, str) or not re.fullmatch(r"(?:[0-9a-f]{40}|[0-9a-f]{64})", revision)
                or inspection["integrity"] != "GREEN" or inspection["spec_coverage"] != "supported_reading_fields"):
            return result
        lifecycle = [row for row in receipt["events"] if row.get("event") in
                     {"session.start", "session.finish", "session.finish.refused"}]
        if not lifecycle or lifecycle[-1].get("event") != "session.finish":
            if lifecycle and lifecycle[-1].get("event") == "session.start":
                result.update(state="incomplete", reason="requirements are declared but execution and completion are unverified")
            return result
        close = lifecycle[-1]
        if inspection["manifest"] != "matches" or inspection["freshness"] != "recorded_close":
            return result
        commands = close.get("command_evidence")
        if not isinstance(commands, list) or not commands:
            return result
        definitions = {row["requirement_id"]: row for row in requirements}
        for command in commands:
            if not isinstance(command, dict) or command.get("requirement_id") not in definitions:
                return result
            if not bound_command(root, command, definitions[command["requirement_id"]], revision,
                                 receipt["snapshot_scope"]):
                return result
        matching = [row for row in commands if row["requirement_id"] == requirement_id]
        if matching:
            if len(matching) != 1:
                return result
            evidence = matching[0]["evidence"]
            result["command_evidence"] = evidence
            if type(evidence.get("exit_code")) is int and evidence["exit_code"] != requirement["check"].get("expect_exit", 0):
                result.update(state="failed", reference_bound=True, reason="recorded command failed its declared exit check")
                return result
        if inspection["recorded_outcome"] == "VERIFIED":
            result.update(state="recorded_verified", reason="declared scope at the recorded execution only")
        else:
            outcome = close.get("outcome") or {}
            failed = type(outcome.get("passed")) is int and type(outcome.get("total")) is int and outcome["passed"] < outcome["total"]
            result.update(state="failed" if failed else "incomplete", reason="recorded close does not establish declared completion")
        result["reference_bound"] = True
        return result
    except (OSError, ValueError, TypeError, KeyError, AttributeError):
        result.update(state="unknown", reference_bound=False, command_evidence=None)
        return result


def read_evidence(root, session, requirement, revision, *, trace="runtime.jsonl", runtime_receipt="runtime-receipt.json"):
    root = Path(root).resolve()
    runtime = runtime_observation(root, trace, runtime_receipt)
    acceptance = acceptance_observation(root, session, requirement, revision)
    return {"selection": {"session": session, "requirement": requirement, "revision": revision},
            "runtime": runtime, "acceptance": acceptance,
            "reference_status": "loaded" if runtime["state"] != "unknown" and acceptance["reference_bound"] else "unknown",
            "correlation": "caller-supplied references; origin not authenticated",
            "current_execution": "not performed", "current_outcome": "UNVERIFIED", "dispatch_authorized": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workspace", type=Path)
    parser.add_argument("--session", required=True)
    parser.add_argument("--requirement", required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--trace", default="runtime.jsonl")
    parser.add_argument("--runtime-receipt", default="runtime-receipt.json")
    args = parser.parse_args()
    print(json.dumps(read_evidence(args.workspace, args.session, args.requirement, args.revision,
                                 trace=args.trace, runtime_receipt=args.runtime_receipt), indent=2))


if __name__ == "__main__":
    main()
