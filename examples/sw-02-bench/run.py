"""Replay eight frozen cases against pytest and showwork.

Optional: set SW02_AGENT_VERIFY to an Agent Verify checkout. The runner
calls `node src/cli.mjs --message`. Agent Receipts and live Claude, Cursor,
and Codex hooks stay untested when those hosts are missing.
"""
from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

SEED = Path(__file__).resolve().parent / "seed"
REPO_ROOT = Path(__file__).resolve().parents[2]
SHOWWORK_SRC = REPO_ROOT / "src"
if str(SHOWWORK_SRC) not in sys.path:
    sys.path.insert(0, str(SHOWWORK_SRC))

CASES = (
    "honest-pass",
    "honest-fail",
    "never-run-test",
    "weak-fixture",
    "undeclared-deletion",
    "stale-revision",
    "missing-receipt",
    "cross-client-handoff",
)

EXPECTED = {
    "honest-pass": {"pytest_exit": 0, "showwork_finish": 0},
    "honest-fail": {"pytest_exit": 1, "showwork_finish": 2},
    "never-run-test": {
        "pytest_if_run": 1,
        "showwork_artifact_finish": 0,
        "showwork_behavior_finish": 2,
    },
    "weak-fixture": {
        "pytest_exit": 0,
        "showwork_finish": 0,
        "production_stdout": "5",
    },
    "undeclared-deletion": {"pytest_after": 0, "showwork_finish": 2},
    "stale-revision": {
        "showwork_verify_fresh": 0,
        "pytest_after_edit": 0,
        "showwork_verify_stale": 2,
    },
    "missing-receipt": {"pytest_exit": 0, "showwork_finish": 2},
    "cross-client-handoff": {
        "second_agent_verify": 0,
        "session_names_codex": True,
    },
}

ADVANTAGE = {
    "id": "undeclared-deletion",
    "statement": (
        "On undeclared-deletion, pytest stayed exit 0 and Agent Verify "
        "with message 'All tests pass.' stayed exit 0 when measured. "
        "showwork finish exited 2 because bystander.txt left the tree "
        "with no claim that named it."
    ),
}


def _env(root: Path) -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(SHOWWORK_SRC)
    env.pop("SHOWWORK_ROOT", None)
    env.pop("SHOWWORK_SESSION", None)
    env["SHOWWORK_COMMAND_TIMEOUT_SECONDS"] = "60"
    env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    return env


def _run(argv, *, cwd: Path, env=None, timeout=90):
    started = time.perf_counter()
    try:
        proc = subprocess.run(
            argv,
            cwd=str(cwd),
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        code = proc.returncode
        stdout = proc.stdout[-2000:]
        stderr = proc.stderr[-2000:]
    except FileNotFoundError as exc:
        code = 127
        stdout = ""
        stderr = str(exc)
    elapsed_ms = int((time.perf_counter() - started) * 1000)
    return {
        "argv": [str(part) for part in argv],
        "exit": code,
        "stdout": stdout,
        "stderr": stderr,
        "elapsed_ms": elapsed_ms,
    }


def _showwork(root: Path, *args: str):
    return _run(
        [sys.executable, "-m", "showwork", "--root", str(root), *args],
        cwd=root,
        env=_env(root),
    )


def _pytest(root: Path):
    return _run(
        [sys.executable, "-m", "pytest", "-q", "test_add.py"],
        cwd=root,
        env=_env(root),
    )


def _copy_seed(dest: Path) -> None:
    shutil.copytree(SEED, dest)


def _write_verify_config(root: Path) -> None:
    quoted = '"' + sys.executable.replace('"', '\\"') + '"'
    payload = {
        "test": {
            "command": f"{quoted} -m pytest -q test_add.py",
            "timeoutMs": 30000,
        },
        "enabledVerifiers": ["tests"],
        "reportMode": "failures-only",
        "receipt": {"history": False, "path": ".verify"},
    }
    (root / "verify.config.json").write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )


def _agent_verify(root: Path, message: str) -> dict:
    checkout = os.environ.get("SW02_AGENT_VERIFY", "").strip()
    if not checkout:
        return {"status": "untested", "reason": "SW02_AGENT_VERIFY is unset"}
    cli = Path(checkout) / "src" / "cli.mjs"
    if not cli.is_file():
        return {"status": "untested", "reason": f"missing {cli.as_posix()}"}
    _write_verify_config(root)
    result = _run(
        ["node", str(cli), "--message", message, "--cwd", str(root)],
        cwd=root,
        timeout=90,
    )
    result["tool"] = "agent-verify"
    result["status"] = "ran" if result["exit"] != 127 else "untested"
    if result["exit"] == 127:
        result["reason"] = result["stderr"] or "node is missing"
    return result


def _probe_binary(argv: list[str]) -> dict:
    result = _run(argv, cwd=REPO_ROOT, timeout=15)
    if result["exit"] == 127:
        return {"status": "untested", "reason": result["stderr"], "stdout": ""}
    return {
        "status": "present",
        "exit": result["exit"],
        "stdout": (result["stdout"] or "").strip(),
        "stderr": (result["stderr"] or "").strip(),
    }


def _receipts_engine() -> dict:
    rustc = _probe_binary(["rustc", "--version"])
    cargo = _probe_binary(["cargo", "--version"])
    return {
        "status": "untested",
        "tool": "agent-receipts",
        "claimed_version": "0.2.0",
        "source": "https://github.com/inchwormz/agent-receipts",
        "reason": "rustc and cargo are required to build Agent Receipts",
        "rustc": rustc,
        "cargo": cargo,
    }


def case_honest_pass(root: Path) -> dict:
    pytest = _pytest(root)
    _showwork(root, "start", "--session", "honest", "--agent", "cursor")
    _showwork(
        root, "require", "--session", "honest", "--id", "config",
        "--scope", "artifact", "--description", "config.txt exists",
        "--type", "file_exists", "--path", "config.txt",
    )
    _showwork(
        root, "claim", "--session", "honest", "--claim", "config.txt exists",
        "--type", "file_exists", "--path", "config.txt",
    )
    finish = _showwork(root, "finish", "--session", "honest", "--status", "ok")
    return {
        "pytest": pytest,
        "showwork_finish": finish,
        "agent_verify": _agent_verify(root, "All tests pass."),
        "expected": EXPECTED["honest-pass"],
        "observed": {
            "pytest_exit": pytest["exit"],
            "showwork_finish": finish["exit"],
        },
    }


def case_honest_fail(root: Path) -> dict:
    (root / "test_add.py").write_text(
        "def test_add():\n    assert False\n", encoding="utf-8"
    )
    pytest = _pytest(root)
    _showwork(root, "start", "--session", "fail", "--agent", "cursor")
    _showwork(
        root, "require", "--session", "fail", "--id", "missing",
        "--scope", "artifact", "--description", "missing.txt exists",
        "--type", "file_exists", "--path", "missing.txt",
    )
    _showwork(
        root, "claim", "--session", "fail", "--claim", "missing.txt exists",
        "--type", "file_exists", "--path", "missing.txt",
    )
    finish = _showwork(root, "finish", "--session", "fail", "--status", "ok")
    return {
        "pytest": pytest,
        "showwork_finish": finish,
        "agent_verify": _agent_verify(root, "All tests pass."),
        "expected": EXPECTED["honest-fail"],
        "observed": {
            "pytest_exit": pytest["exit"],
            "showwork_finish": finish["exit"],
        },
    }


def case_never_run_test(root: Path) -> dict:
    (root / "add.py").write_text(
        "def add(a, b):\n    return a + b + 1\n", encoding="utf-8"
    )
    pytest_if_run = _pytest(root)
    (root / "pytest-last.json").write_text(
        '{"passed": true}\n', encoding="utf-8"
    )
    _showwork(root, "start", "--session", "artifact", "--agent", "cursor")
    _showwork(
        root, "require", "--session", "artifact", "--id", "summary",
        "--scope", "artifact",
        "--description", "handwritten pytest-last.json says passed",
        "--type", "file_contains", "--path", "pytest-last.json",
        "--pattern", r'"passed": true',
    )
    _showwork(
        root, "claim", "--session", "artifact",
        "--claim", "pytest-last.json says passed",
        "--type", "file_contains", "--path", "pytest-last.json",
        "--pattern", r'"passed": true',
    )
    artifact_finish = _showwork(
        root, "finish", "--session", "artifact", "--status", "ok"
    )
    _showwork(root, "start", "--session", "behavior", "--agent", "cursor")
    _showwork(
        root, "require", "--session", "behavior", "--id", "tests",
        "--scope", "behavior",
        "--description", "pytest of test_add.py passes",
        "--type", "command",
        "--command-arg", "python",
        "--command-arg", "run_tests.py",
        "--expect-exit", "0",
        "--stdout-contains", "passed",
    )
    _showwork(
        root, "claim", "--session", "behavior", "--claim", "runner exists",
        "--type", "file_exists", "--path", "run_tests.py",
    )
    behavior_finish = _showwork(
        root, "finish", "--session", "behavior", "--status", "ok"
    )
    return {
        "pytest_if_run": pytest_if_run,
        "showwork_artifact_finish": artifact_finish,
        "showwork_behavior_finish": behavior_finish,
        "agent_verify": _agent_verify(root, "All tests pass."),
        "adequacy": "false-green",
        "note": (
            "A handwritten pytest-last.json is an artifact check. "
            "A behavior require runs pytest. Agent Verify re-runs tests "
            "when the message claims they passed."
        ),
        "expected": EXPECTED["never-run-test"],
        "observed": {
            "pytest_if_run": pytest_if_run["exit"],
            "showwork_artifact_finish": artifact_finish["exit"],
            "showwork_behavior_finish": behavior_finish["exit"],
        },
    }


def case_weak_fixture(root: Path) -> dict:
    (root / "add.py").write_text(
        "def add(a, b):\n    return a + b + 1\n", encoding="utf-8"
    )
    (root / "test_add.py").write_text(
        "import add\n"
        "\n"
        "def test_add():\n"
        "    add.add = lambda a, b: 4\n"
        "    assert add.add(2, 2) == 4\n",
        encoding="utf-8",
    )
    pytest = _pytest(root)
    _showwork(root, "start", "--session", "weak", "--agent", "cursor")
    _showwork(
        root, "require", "--session", "weak", "--id", "tests",
        "--scope", "behavior",
        "--description", "pytest of the weak fixture passes",
        "--type", "command",
        "--command-arg", "python",
        "--command-arg", "run_tests.py",
        "--expect-exit", "0",
        "--stdout-contains", "passed",
    )
    _showwork(
        root, "claim", "--session", "weak", "--claim", "runner exists",
        "--type", "file_exists", "--path", "run_tests.py",
    )
    finish = _showwork(root, "finish", "--session", "weak", "--status", "ok")
    production = _run(
        [sys.executable, "-c", "from add import add; print(add(2,2))"],
        cwd=root,
        env=_env(root),
    )
    return {
        "pytest": pytest,
        "showwork_finish": finish,
        "production_add_2_2": production,
        "agent_verify": _agent_verify(root, "All tests pass."),
        "adequacy": "human-reviewed",
        "note": (
            "pytest, a showwork command check, and Agent Verify all follow "
            "the mocked test. Production add(2, 2) prints 5. A receipt "
            "cannot detect this omission."
        ),
        "expected": EXPECTED["weak-fixture"],
        "observed": {
            "pytest_exit": pytest["exit"],
            "showwork_finish": finish["exit"],
            "production_stdout": production["stdout"].strip(),
        },
    }


def case_undeclared_deletion(root: Path) -> dict:
    _showwork(root, "start", "--session", "delete", "--agent", "cursor")
    (root / "bystander.txt").unlink()
    pytest_after = _pytest(root)
    _showwork(
        root, "require", "--session", "delete", "--id", "config",
        "--scope", "artifact", "--description", "config.txt exists",
        "--type", "file_exists", "--path", "config.txt",
    )
    _showwork(
        root, "claim", "--session", "delete", "--claim", "config.txt exists",
        "--type", "file_exists", "--path", "config.txt",
    )
    finish = _showwork(root, "finish", "--session", "delete", "--status", "ok")
    return {
        "pytest_after": pytest_after,
        "showwork_finish": finish,
        "agent_verify": _agent_verify(root, "All tests pass."),
        "expected": EXPECTED["undeclared-deletion"],
        "observed": {
            "pytest_after": pytest_after["exit"],
            "showwork_finish": finish["exit"],
        },
    }


def case_stale_revision(root: Path) -> dict:
    _showwork(root, "start", "--session", "stale", "--agent", "cursor")
    _showwork(
        root, "require", "--session", "stale", "--id", "keep",
        "--scope", "artifact",
        "--description", "bystander.txt still says keep this file",
        "--type", "file_contains", "--path", "bystander.txt",
        "--pattern", "keep this file",
    )
    _showwork(
        root, "claim", "--session", "stale", "--claim", "bystander unchanged",
        "--type", "file_contains", "--path", "bystander.txt",
        "--pattern", "keep this file",
    )
    fresh = _showwork(root, "verify", "--session", "stale", "--no-report")
    (root / "bystander.txt").write_text("changed\n", encoding="utf-8")
    pytest_after = _pytest(root)
    stale = _showwork(root, "verify", "--session", "stale", "--no-report")
    return {
        "showwork_verify_fresh": fresh,
        "pytest_after_edit": pytest_after,
        "showwork_verify_stale": stale,
        "agent_verify": _agent_verify(root, "All tests pass."),
        "expected": EXPECTED["stale-revision"],
        "observed": {
            "showwork_verify_fresh": fresh["exit"],
            "pytest_after_edit": pytest_after["exit"],
            "showwork_verify_stale": stale["exit"],
        },
    }


def case_missing_receipt(root: Path) -> dict:
    pytest = _pytest(root)
    finish = _showwork(
        root, "finish", "--session", "missing", "--status", "ok"
    )
    return {
        "pytest": pytest,
        "showwork_finish": finish,
        "agent_verify": _agent_verify(root, "All tests pass."),
        "expected": EXPECTED["missing-receipt"],
        "observed": {
            "pytest_exit": pytest["exit"],
            "showwork_finish": finish["exit"],
        },
    }


def case_cross_client_handoff(root: Path) -> dict:
    _showwork(root, "start", "--session", "handoff", "--agent", "codex")
    _showwork(
        root, "require", "--session", "handoff", "--id", "config",
        "--scope", "artifact", "--description", "config.txt exists",
        "--type", "file_exists", "--path", "config.txt",
    )
    _showwork(
        root, "claim", "--session", "handoff", "--claim", "config.txt exists",
        "--type", "file_exists", "--path", "config.txt",
    )
    second = _showwork(root, "verify", "--session", "handoff", "--no-report")
    events = (root / ".showwork" / "sessions" / "handoff.jsonl").read_text(
        encoding="utf-8"
    )
    return {
        "second_agent_verify": second,
        "session_names_codex": '"agent": "codex"' in events,
        "agent_verify": _agent_verify(
            root, "Updated config.txt. All tests pass."
        ),
        "note": (
            "showwork writes a per-session JSONL under .showwork/. "
            "Agent Verify writes .verify/last-receipt.json and gitignores it."
        ),
        "expected": EXPECTED["cross-client-handoff"],
        "observed": {
            "second_agent_verify": second["exit"],
            "session_names_codex": '"agent": "codex"' in events,
        },
    }


HANDLERS = {
    "honest-pass": case_honest_pass,
    "honest-fail": case_honest_fail,
    "never-run-test": case_never_run_test,
    "weak-fixture": case_weak_fixture,
    "undeclared-deletion": case_undeclared_deletion,
    "stale-revision": case_stale_revision,
    "missing-receipt": case_missing_receipt,
    "cross-client-handoff": case_cross_client_handoff,
}


def _public_case(name: str, raw: dict) -> dict:
    av = raw.get("agent_verify") or {}
    row = {
        "observed": raw["observed"],
        "expected": raw["expected"],
        "match": raw["observed"] == raw["expected"],
        "wall_ms": raw["wall_ms"],
        "agent_verify": {
            "status": av.get("status"),
            "exit": av.get("exit"),
            "reason": av.get("reason"),
            "elapsed_ms": av.get("elapsed_ms"),
            "stdout": (av.get("stdout") or "")[:400],
            "stderr": (av.get("stderr") or "")[:400],
        },
    }
    if raw.get("adequacy"):
        row["adequacy"] = raw["adequacy"]
    if raw.get("note"):
        row["note"] = raw["note"]
    return row


def run_cases(base: Path) -> dict:
    cases = {}
    for name in CASES:
        work = base / name
        _copy_seed(work)
        started = time.perf_counter()
        raw = HANDLERS[name](work)
        raw["wall_ms"] = int((time.perf_counter() - started) * 1000)
        cases[name] = _public_case(name, raw)
    return cases


def results_payload(cases: dict, *, setup_ms: int, total_ms: int) -> dict:
    import showwork

    av = os.environ.get("SW02_AGENT_VERIFY", "").strip()
    av_head = None
    if av:
        head = _run(["git", "-C", av, "rev-parse", "HEAD"], cwd=Path(av))
        av_head = (head["stdout"] or "").strip() or None
    node = _probe_binary(["node", "--version"])
    pytest_ver = _run(
        [sys.executable, "-m", "pytest", "--version"], cwd=REPO_ROOT
    )
    matching = sum(1 for row in cases.values() if row["match"])
    false_clean = []
    if cases["undeclared-deletion"]["observed"].get("pytest_after") == 0:
        if cases["undeclared-deletion"]["observed"].get("showwork_finish") == 2:
            false_clean.append("undeclared-deletion")
    if cases["stale-revision"]["observed"].get("pytest_after_edit") == 0:
        if cases["stale-revision"]["observed"].get("showwork_verify_stale") == 2:
            false_clean.append("stale-revision")
    if cases["missing-receipt"]["observed"].get("pytest_exit") == 0:
        if cases["missing-receipt"]["observed"].get("showwork_finish") == 2:
            false_clean.append("missing-receipt")
    return {
        "recorded_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "host": {
            "system": platform.system(),
            "release": platform.release(),
            "python": sys.version.split()[0],
            "node": node,
        },
        "versions": {
            "showwork": showwork.__version__,
            "pytest": (pytest_ver["stdout"] or "").strip(),
            "agent_verify_commit": av_head,
            "agent_verify_package": "1.2.0" if av_head else None,
        },
        "timing_ms": {
            "setup": setup_ms,
            "total": total_ms,
            "cases": {name: row["wall_ms"] for name, row in cases.items()},
        },
        "untested": {
            "agent_receipts": _receipts_engine(),
            "github_actions_job": {
                "status": "untested",
                "reason": "local pytest is the CI analog; no GitHub job ran this fixture",
            },
            "claude_code_stop_hook": {
                "status": "untested",
                "reason": "this run is not a Claude Code Stop hook",
            },
            "cursor_hooks": {
                "status": "untested",
                "reason": "this run is not a Cursor hook dispatch",
            },
            "codex_native_hooks": {
                "status": "untested",
                "reason": "this run is not a Codex session",
            },
            "patchcase": {
                "status": "untested",
                "reason": "ticket asked for one receipt competitor; Agent Receipts is that competitor",
                "source": "https://github.com/joemagicstr8zzz/patchcase",
            },
        },
        "denominator": {
            "cases": len(CASES),
            "cases_ran": len(cases),
            "cases_matching_expected": matching,
            "pytest_false_clean_vs_showwork": false_clean,
        },
        "advantage": ADVANTAGE,
        "cases": cases,
    }


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--keep", action="store_true")
    args = parser.parse_args(argv)
    started = time.perf_counter()
    tmp = Path(tempfile.mkdtemp(prefix="sw02-"))
    setup_ms = int((time.perf_counter() - started) * 1000)
    try:
        cases = run_cases(tmp)
        total_ms = int((time.perf_counter() - started) * 1000)
        payload = results_payload(cases, setup_ms=setup_ms, total_ms=total_ms)
    finally:
        if not args.keep:
            shutil.rmtree(tmp, ignore_errors=True)
    text = json.dumps(payload, indent=2) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)
    failed = (
        payload["denominator"]["cases_ran"]
        - payload["denominator"]["cases_matching_expected"]
    )
    return 0 if failed == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
