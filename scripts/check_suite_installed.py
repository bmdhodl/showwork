"""Build isolated validation wheels and run the offline suite example.

Downloads only the pinned public AgentGuard source and build dependencies.
Provider calls are local stubs. Neither runtime installs the other package.
No release, BMD installation or persisted join is created.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
AGENTGUARD_COMMIT = "45c4d54824319888abe67e3e437c38294c92a306"
FLAGS = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def run(argv, *, cwd=None, input_text=None):
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    env.pop("SHOWWORK_VERIFYING", None)
    env.pop("SHOWWORK_NO_COMMANDS", None)
    env["GIT_TERMINAL_PROMPT"] = "0"
    result = subprocess.run([str(arg) for arg in argv], cwd=cwd, env=env,
                            input=input_text, capture_output=True, text=True, encoding="utf-8",
                            timeout=240, creationflags=FLAGS)
    if result.returncode:
        # These commands use public sources and synthetic data only.
        raise RuntimeError(f"{Path(str(argv[0])).name} failed ({result.returncode}): {result.stderr[-2000:]}")
    return result.stdout.strip()


def interpreter(folder):
    return folder / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def environment(folder):
    run([sys.executable, "-m", "venv", folder])
    return interpreter(folder)


SDK_PROBE = r'''
import importlib.metadata as metadata
import importlib.util
import json
from pathlib import Path
import sys
from agentguard import BudgetGuard, BudgetExceeded, Tracer, JsonlFileSink
from agentguard.receipt import build_receipt

def require(ok, message):
    if not ok: raise RuntimeError(message)

require(importlib.util.find_spec("showwork") is None, "SDK unexpectedly requires showwork")
require(metadata.version("agentguard47") == "1.4.1", "wrong SDK version")
require(all("extra ==" in row for row in (metadata.requires("agentguard47") or [])), "SDK runtime dependency growth")
root = Path(sys.argv[1])
observations = {}
for name, limit in (("within", 2), ("stopped", 1), ("corrected", 2)):
    guard = BudgetGuard(max_calls=limit, warn_at_pct=None)
    calls = []
    def provider_stub():
        calls.append("synthetic")
        return "synthetic"
    denied = False
    trace = root / ("runtime-" + name + ".jsonl")
    with Tracer(sink=JsonlFileSink(str(trace)), session_id=name, watermark=False) as tracer:
        with tracer.trace("offline.example") as span:
            guard.check()
            output = provider_stub()
            guard.consume(calls=1)
            span.event("llm.result", data={"output": output})
            if name == "stopped":
                try:
                    guard.check()
                except BudgetExceeded as error:
                    denied = True
                    span.event("guard.budget_exceeded", data={"message": str(error),
                               "calls_used": guard.state.calls_used, "calls_limit": limit})
                else:
                    provider_stub()
    require(len(calls) == 1 and denied == (name == "stopped"), "pre-dispatch denial failed")
    receipt = build_receipt(str(trace))
    require(receipt["llm_calls"] == 1 and bool(receipt["stops"]) == denied, "receipt diverged from guard")
    (root / ("runtime-" + name + "-receipt.json")).write_text(json.dumps(receipt), encoding="utf-8")
    observations[name] = {"provider_stub_calls": len(calls), "next_dispatch_checked": name == "stopped",
                          "next_dispatch_denied": denied if name == "stopped" else None,
                          "receipt_sha256": receipt["sha256"], "version": receipt["version"]}
print(json.dumps(observations))
'''


POST_RECEIPT_PROBE = r'''
import json
import sys
from agentguard import BudgetGuard, BudgetExceeded
guard = BudgetGuard(max_calls=1, warn_at_pct=None)
calls = []
def provider_stub():
    calls.append("synthetic")
    return "synthetic"
guard.check()
provider_stub()
guard.consume(calls=1)
view = json.loads(sys.stdin.read())
if view["acceptance"]["state"] != "recorded_verified":
    raise RuntimeError("matching acceptance input missing")
try:
    guard.check()
except BudgetExceeded:
    denied = True
else:
    denied = False
    provider_stub()
if not denied or len(calls) != 1 or guard.state.calls_used != 1:
    raise RuntimeError("acceptance receipt changed exhausted dispatch budget")
print(json.dumps({"receipt_loaded": True, "next_dispatch_denied": denied, "provider_stub_calls": len(calls)}))
'''


SHOWWORK_PROBE = r'''
import importlib.metadata as metadata
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from showwork.ledger import start_session, record_claim, finish_session
from showwork.outcomes import record_requirement
from showwork.checks import verify_claim

def require(ok, message):
    if not ok: raise RuntimeError(message)

root = Path(sys.argv[1])
require(importlib.util.find_spec("agentguard") is None, "showwork unexpectedly requires SDK")
require(metadata.version("showwork") == "0.6.5", "wrong showwork version")
require(not metadata.requires("showwork"), "showwork runtime dependency growth")
def git(*args):
    return subprocess.check_output(["git", *args], cwd=root, text=True,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)).strip()
def commit(message):
    git("add", "production.py", "check.py", "artifact.txt")
    git("-c", "user.name=fixture", "-c", "user.email=fixture@example.invalid", "commit", "-qm", message)
    return git("rev-parse", "HEAD")
def start(session):
    start_session(root, session, ignore=["runtime-*"])
    record_requirement(root, session, "run", "production add(2,2) returns 4", "behavior",
        {"type": "command", "argv": ["python", "check.py"], "expect_exit": 0, "stdout_contains": "passed"})
    record_requirement(root, session, "artifact", "artifact is ready", "artifact",
        {"type": "file_contains", "path": "artifact.txt", "pattern": "ready"})
    record_claim(root, session, "artifact exists", check={"type": "file_exists", "path": "artifact.txt"})

(root / "production.py").write_text("def add(a, b): return a + b + 1\n", encoding="utf-8")
(root / "check.py").write_text("from production import add\nif add(2, 2) != 4: raise SystemExit(1)\nprint('passed')\n", encoding="utf-8")
(root / "artifact.txt").write_text("ready\n", encoding="utf-8")
git("init", "-q")
broken = commit("broken production fixture")
start("within-failed")
require(finish_session(root, "within-failed", "blocked")[0] == 0, "failed attempt not retained")
start("stopped-unfinished")
artifact_observation = verify_claim({"session": "stopped-unfinished", "claim": "artifact is ready",
    "check": {"type": "file_contains", "path": "artifact.txt", "pattern": "ready"}}, root)
require(artifact_observation["status"] == "pass", "artifact observation did not pass")
print(json.dumps({"broken_revision": broken, "stopped_artifact_check": artifact_observation["status"]}))
'''


def build_and_check(base):
    builder = environment(base / "builder")
    run([builder, "-m", "pip", "install", "setuptools==82.0.1", "wheel==0.47.0"])
    sdk_repo = base / "agentguard-source"
    sdk_repo.mkdir()
    run(["git", "init", "-q"], cwd=sdk_repo)
    run(["git", "fetch", "--depth=1", "--filter=blob:none", "https://github.com/bmdhodl/agent47.git", AGENTGUARD_COMMIT], cwd=sdk_repo)
    run(["git", "sparse-checkout", "init", "--cone"], cwd=sdk_repo)
    run(["git", "sparse-checkout", "set", "sdk"], cwd=sdk_repo)
    run(["git", "checkout", "--detach", "FETCH_HEAD"], cwd=sdk_repo)
    require(run(["git", "rev-parse", "HEAD"], cwd=sdk_repo) == AGENTGUARD_COMMIT, "SDK source pin mismatch")
    showwork_revision = run(["git", "rev-parse", "HEAD"], cwd=ROOT)
    archive = base / "showwork-source.zip"
    run(["git", "archive", "--format=zip", f"--output={archive}", "HEAD", "src", "pyproject.toml", "README.md", "LICENSE"], cwd=ROOT)
    source = base / "showwork-source"
    source.mkdir()
    with zipfile.ZipFile(archive) as package:
        for item in package.infolist():
            target = (source / item.filename).resolve()
            require(target.is_relative_to(source.resolve()), "archive path escapes source")
        package.extractall(source)
    wheels = base / "wheels"
    wheels.mkdir()
    for directory in (source, sdk_repo / "sdk"):
        run([builder, "-m", "pip", "wheel", "--no-deps", "--no-build-isolation", "--wheel-dir", wheels, directory])
    showwork_wheel, = wheels.glob("showwork-*.whl")
    sdk_wheel, = wheels.glob("agentguard47-*.whl")
    showwork = environment(base / "showwork-only")
    sdk = environment(base / "agentguard-only")
    run([showwork, "-m", "pip", "install", "--no-index", "--no-deps", showwork_wheel])
    run([sdk, "-m", "pip", "install", "--no-index", "--no-deps", sdk_wheel])
    workspace = base / "workspace"
    workspace.mkdir()
    sdk_script, writer_script = base / "sdk_probe.py", base / "showwork_probe.py"
    sdk_script.write_text(SDK_PROBE, encoding="utf-8")
    writer_script.write_text(SHOWWORK_PROBE, encoding="utf-8")
    runtime = json.loads(run([sdk, "-I", sdk_script, workspace], cwd=base))
    revisions = json.loads(run([showwork, "-I", writer_script, workspace], cwd=base))
    reader = ROOT / "examples/suite/read_evidence.py"
    def read(session, requirement="run", revision=None, runtime_case="within", root=None, trace=None, receipt=None):
        return json.loads(run([showwork, "-I", reader, root or workspace, "--session", session,
            "--requirement", requirement, "--revision", revision or revisions["broken_revision"],
            "--trace", trace or f"runtime-{runtime_case}.jsonl", "--runtime-receipt", receipt or f"runtime-{runtime_case}-receipt.json"], cwd=base))
    failed = read("within-failed")
    require(failed["runtime"]["state"] == "no_recorded_stop" and failed["acceptance"]["state"] == "failed", "within budget hid failed work")
    require(failed["acceptance"]["requirement"]["claim"] == "production add(2,2) returns 4", "requirement text missing")
    stopped = read("stopped-unfinished", runtime_case="stopped")
    require(stopped["runtime"]["state"] == "stopped" and stopped["acceptance"]["state"] == "incomplete", "stopped work appeared complete")
    original = (workspace / ".showwork/sessions/within-failed.jsonl").read_bytes()
    correction = SHOWWORK_PROBE[:SHOWWORK_PROBE.index('(root / "production.py").write_text')] + '''
(root / "production.py").write_text("def add(a, b): return a + b\\n", encoding="utf-8")
fixed = commit("corrected production fixture")
start("corrected")
require(finish_session(root, "corrected", "ok")[0] == 0, "corrected acceptance failed")
start_session(root, "artifact-only", ignore=["runtime-*"])
record_requirement(root, "artifact-only", "artifact", "artifact is ready", "artifact",
    {"type": "file_contains", "path": "artifact.txt", "pattern": "ready"})
record_claim(root, "artifact-only", "artifact exists", check={"type": "file_exists", "path": "artifact.txt"})
require(finish_session(root, "artifact-only", "ok")[0] == 0, "artifact-only acceptance failed")
print(json.dumps({"corrected_revision": fixed}))
'''
    writer_script.write_text(correction, encoding="utf-8")
    revisions.update(json.loads(run([showwork, "-I", writer_script, workspace], cwd=base)))
    corrected = read("corrected", "artifact", revisions["corrected_revision"], "corrected")
    require(corrected["acceptance"]["state"] == "recorded_verified" and corrected["acceptance"]["requirement"]["scope"] == "artifact", "artifact scope lost")
    require(corrected["acceptance"]["requirement"]["claim"] == "artifact is ready", "artifact requirement text missing")
    post_receipt_script = base / "post_receipt_probe.py"
    post_receipt_script.write_text(POST_RECEIPT_PROBE, encoding="utf-8")
    post_receipt = json.loads(run([sdk, "-I", post_receipt_script], cwd=base, input_text=json.dumps(corrected)))
    require(original == (workspace / ".showwork/sessions/within-failed.jsonl").read_bytes(), "retry overwrote failed evidence")
    cases = {"within_failed": failed, "stopped_unfinished": stopped, "corrected_artifact": corrected,
             "old_revision": read("corrected", revision=revisions["broken_revision"]),
             "missing_session": read("missing"), "stale_original": read("within-failed")}
    copied = base / "wrong-root"
    shutil.copytree(workspace, copied)
    cases["wrong_root"] = read("corrected", revision=revisions["corrected_revision"], root=copied)
    for name in ("old_revision", "missing_session", "stale_original", "wrong_root"):
        require(cases[name]["acceptance"]["state"] == "unknown", f"{name} did not refuse")
    cases["missing_runtime"] = read("corrected", revision=revisions["corrected_revision"], trace="runtime-absent.jsonl")
    incompatible = json.loads((workspace / "runtime-corrected-receipt.json").read_text(encoding="utf-8"))
    incompatible["version"] = "999.0"
    (workspace / "runtime-incompatible-receipt.json").write_text(json.dumps(incompatible), encoding="utf-8")
    cases["incompatible_runtime"] = read("corrected", revision=revisions["corrected_revision"],
        runtime_case="corrected", receipt="runtime-incompatible-receipt.json")
    for name in ("missing_runtime", "incompatible_runtime"):
        require(cases[name]["runtime"]["state"] == "unknown" and cases[name]["reference_status"] == "unknown",
                f"{name} did not refuse")
    cases["artifact_only"] = read("artifact-only", "artifact", revisions["corrected_revision"], "corrected")
    cases["artifact_only_unbound_revision"] = read("artifact-only", "artifact", "f" * 40, "corrected")
    for name in ("artifact_only", "artifact_only_unbound_revision"):
        view = cases[name]
        require(view["acceptance"]["state"] == "recorded_verified"
                and view["acceptance"]["requirement"]["scope"] == "artifact"
                and view["acceptance"]["command_evidence"] is None
                and view["acceptance"]["reference_bound"] is False
                and view["reference_status"] == "unknown", f"{name} lost artifact scope or invented revision binding")
    for name, view in cases.items():
        require(view["current_execution"] == "not performed" and view["current_outcome"] == "UNVERIFIED"
                and view["dispatch_authorized"] is False, f"{name} inherited authority")
    report = {"build_kind": "source-built validation wheels; not published releases",
              "source_revisions": {"showwork": showwork_revision, "agentguard47": AGENTGUARD_COMMIT},
              "wheels": {wheel.name: hashlib.sha256(wheel.read_bytes()).hexdigest() for wheel in (showwork_wheel, sdk_wheel)},
              "runtime_proof": runtime, "cases": cases, "failed_attempt_retained": True,
              "post_acceptance_dispatch": post_receipt,
              "stopped_artifact_check": revisions["stopped_artifact_check"],
              "limits": ["synthetic local provider; no customer adoption or production BMD proof",
                         "hashes identify supplied bytes; origin authentication is not established"]}
    (base / "proof.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report))
    print("installed suite proof passed")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifacts", type=Path, help="retain artifacts in a new, caller-selected directory")
    args = parser.parse_args()
    if args.artifacts:
        base = args.artifacts.resolve()
        base.mkdir(exist_ok=False)
        build_and_check(base)
    else:
        with tempfile.TemporaryDirectory(prefix="sw-suite-") as scratch:
            build_and_check(Path(scratch))


if __name__ == "__main__":
    main()
