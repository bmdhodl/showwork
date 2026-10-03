"""Three toy failure/repair paths using the selected Python's showwork install."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import showwork


BROKEN = "def add(a, b):\n    return a + b + 1\n"
REPAIRED = "def add(a, b):\n    return a + b\n"
PROBE = ("from add import add\n"
         "if add(2, 2) != 4:\n    raise RuntimeError('2 + 2 did not return 4')\n"
         "print('passed')\n")


def require(condition, detail):
    if not condition:
        raise RuntimeError(detail)


def environment():
    env = dict(os.environ)
    env.pop("SHOWWORK_ROOT", None)
    env.pop("SHOWWORK_SESSION", None)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


def run(root, args, expected=0):
    proc = subprocess.run([sys.executable, "-m", "showwork", "--root", str(root), *args],
                          cwd=root, env=environment(), capture_output=True, text=True,
                          timeout=60, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    require(proc.returncode == expected,
            f"{args[0]} expected exit {expected}, observed {proc.returncode}: {proc.stdout} {proc.stderr}")
    return proc


def seed(root, source=REPAIRED):
    root.mkdir()
    (root / "add.py").write_text(source, encoding="utf-8")
    (root / "probe.py").write_text(PROBE, encoding="utf-8")


def declare(root, session, agent="manual"):
    run(root, ["start", "--session", session, "--agent", agent])
    run(root, ["require", "--session", session, "--id", "add", "--scope", "behavior",
               "--description", "the real add(2,2) returns 4", "--type", "command",
               "--command-arg", "python", "--command-arg", "probe.py",
               "--expect-exit", "0", "--stdout-contains", "passed"])
    for path in ("add.py", "probe.py"):
        run(root, ["claim", "--session", session, "--claim", f"{path} exists",
                   "--type", "file_exists", "--path", path])


def failure(root):
    seed(root, BROKEN)
    declare(root, "declared-failure")
    refused = run(root, ["finish", "--session", "declared-failure"], 2)
    require("REFUSED" in refused.stderr, "broken production behavior did not refuse completion")
    (root / "add.py").write_text(REPAIRED, encoding="utf-8")
    run(root, ["finish", "--session", "declared-failure"])
    fresh = root.parent / "declared-fresh"
    shutil.copytree(root, fresh)
    result = json.loads(run(fresh, ["verify", "--session", "declared-failure", "--json", "--no-report"]).stdout)
    require(result["outcome"]["verdict"] == "VERIFIED", "fresh rerun was not verified")
    return {"example": "declared-failure", "broken_finish": 2, "repaired_finish": 0,
            "fresh_rerun": result["outcome"]["verdict"],
            "limits": "Only add(2,2) is tested; other inputs and requirement adequacy are unknown"}


def damage(root):
    seed(root)
    (root / "keep.txt").write_text("keep this existing input\n", encoding="utf-8")
    declare(root, "undeclared-damage")
    # Delete only this script's known toy input, after the start snapshot.
    (root / "keep.txt").unlink()
    run(root, ["finish", "--session", "undeclared-damage"], 2)
    failed = json.loads(run(root, ["verify", "--session", "undeclared-damage", "--json", "--no-report"], 2).stdout)
    require(any(row.get("type") == "undeclared_change" and row.get("status") == "fail"
                and row.get("claim") == "undeclared deletion: keep.txt" for row in failed["results"]),
            "refusal did not identify the undeclared deletion")
    (root / "keep.txt").write_text("keep this existing input\n", encoding="utf-8")
    run(root, ["finish", "--session", "undeclared-damage"])
    result = json.loads(run(root, ["verify", "--session", "undeclared-damage", "--json", "--no-report"]).stdout)
    require(result["outcome"]["verdict"] == "VERIFIED", "restored input did not verify")
    return {"example": "undeclared-damage", "damaged_finish": 2, "restored_finish": 0,
            "current_rerun": result["outcome"]["verdict"],
            "limits": "Existing snapshotted files only; no claim that every new file or external effect is covered"}


def receipt_bytes(root):
    return {p.relative_to(root).as_posix(): p.read_bytes()
            for p in (root / ".showwork").rglob("*") if p.is_file()}


def handoff(root):
    seed(root)
    declare(root, "producer", "codex")
    run(root, ["finish", "--session", "producer"])
    consumer = root.parent / "handoff-consumer"
    shutil.copytree(root, consumer)
    (consumer / "probe.py").write_text(
        "from pathlib import Path\nPath('command-ran.txt').write_text('yes')\n"
        "raise RuntimeError('broken after handoff')\n", encoding="utf-8")
    before = receipt_bytes(consumer)
    read = subprocess.run([sys.executable, "-c",
                           "import json,sys; from showwork.receipts import evidence_for_session; "
                           "print(json.dumps(evidence_for_session(sys.argv[1], 'producer')))", str(consumer)],
                          cwd=consumer, env=environment(), capture_output=True, text=True,
                          timeout=60, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    require(read.returncode == 0, f"fresh reader failed: {read.stderr}")
    payload = json.loads(read.stdout)
    require(payload["state"] != "verified", "reader inherited verified behavior without executing acceptance")
    require(not (consumer / "command-ran.txt").exists(), "reader executed an inherited command")
    require(receipt_bytes(consumer) == before, "reader changed receipt bytes")
    run(consumer, ["verify", "--session", "producer", "--json", "--no-report"], 2)
    require((consumer / "command-ran.txt").is_file(), "explicit rerun did not execute the real broken probe")
    (consumer / "command-ran.txt").unlink()  # Remove only the toy probe's own marker.
    (consumer / "probe.py").write_text(PROBE, encoding="utf-8")
    run(consumer, ["start", "--session", "consumer", "--agent", "claude-code"])
    run(consumer, ["require", "--session", "consumer", "--id", "add", "--scope", "behavior",
                   "--description", "consumer independently reruns the real add probe", "--type", "command",
                   "--command-arg", "python", "--command-arg", "probe.py", "--expect-exit", "0",
                   "--stdout-contains", "passed"])
    run(consumer, ["claim", "--session", "consumer", "--claim", "probe exists",
                   "--type", "file_exists", "--path", "probe.py"])
    run(consumer, ["finish", "--session", "consumer"])
    result = json.loads(run(consumer, ["verify", "--session", "consumer", "--json", "--no-report"]).stdout)
    require(result["outcome"]["verdict"] == "VERIFIED", "consumer did not independently verify repair")
    return {"example": "handoff", "read_only_state": payload["state"],
            "inherited_command_executed": False, "receipt_bytes_preserved": True,
            "broken_explicit_rerun": 2, "consumer_repaired_rerun": result["outcome"]["verdict"],
            "approval_inherited": False,
            "limits": "Driver labels two client sessions; no actual model task, trust change or permission transfer"}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path, help="new directory; existing directories are refused")
    parser.add_argument("--example", choices=("all", "failure", "damage", "handoff"), default="all")
    args = parser.parse_args(argv)
    root = args.root.resolve()
    require(not root.exists(), "choose a new toy directory; existing data is never overwritten")
    root.mkdir(parents=True)
    functions = {"failure": failure, "damage": damage, "handoff": handoff}
    selected = functions if args.example == "all" else {args.example: functions[args.example]}
    results = [function(root / name) for name, function in selected.items()]
    print(json.dumps({"version": showwork.__version__,
                      "python": sys.version.split()[0], "results": results}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
