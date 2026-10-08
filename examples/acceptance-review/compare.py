"""Compare trusted unittest checks against copied broken and repaired fixtures.

This is an optional example runner, not a sandbox or a test-adequacy verdict.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from showwork.process import run_process


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_fixture(root: Path) -> dict[str, bytes]:
    """Take an exact input copy; reject links rather than copy their targets."""
    if (not root.is_dir() or root.is_symlink()
            or getattr(root.lstat(), "st_file_attributes", 0) & 0x400):
        raise ValueError(f"fixture must be a regular directory: {root}")
    files = {}
    def unreadable(error):
        raise error

    for directory, folders, names in os.walk(root, followlinks=False, onerror=unreadable):
        folders[:] = sorted(n for n in folders if n not in {".git", "__pycache__"})
        for name in folders + sorted(names):
            path = Path(directory) / name
            if path.is_symlink() or getattr(path.lstat(), "st_file_attributes", 0) & 0x400:
                raise ValueError(f"fixture links are unsupported: {path}")
            if path.is_file() and path.suffix not in {".pyc", ".pyo"}:
                files[path.relative_to(root).as_posix()] = path.read_bytes()
    return files


def tree_digest(files: dict[str, bytes]) -> str:
    manifest = {name: digest(data) for name, data in sorted(files.items())}
    return digest(json.dumps(manifest, sort_keys=True).encode("utf-8"))


def write_copy(root: Path, files: dict[str, bytes]) -> None:
    root.mkdir(parents=True, exist_ok=True)
    for name, data in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)


class ObservedResult(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.test_ids = []

    def startTest(self, test):
        self.test_ids.append(test.id())
        super().startTest(test)

    def in_test_method(self, test, err):
        # unittest dispatches any callable test through this hook, including
        # partialmethod and async tests. Fixture callbacks use different hooks.
        code = getattr(test._callTestMethod, "__code__", None)
        traceback = err[2]
        while traceback is not None:
            if traceback.tb_frame.f_code is code and traceback.tb_frame.f_locals.get("self") is test:
                return True
            traceback = traceback.tb_next
        # A subtest catches the exception before the dispatch hook unwinds,
        # so that frame is on the live stack instead of the error traceback.
        frame = sys._getframe()
        try:
            while frame is not None:
                if frame.f_code is code and frame.f_locals.get("self") is test:
                    return True
                frame = frame.f_back
        finally:
            del frame
        return False

    def addFailure(self, test, err):
        if self.in_test_method(test, err):
            return super().addFailure(test, err)
        return super().addError(test, err)

    def addSubTest(self, test, subtest, err):
        if err is not None and not self.in_test_method(test, err):
            return super().addError(subtest, err)
        return super().addSubTest(test, subtest, err)


def worker(result_path: Path) -> int:
    sys.path.insert(0, str(Path.cwd()))
    suite = unittest.defaultTestLoader.discover("_checks", pattern="test*.py")
    result = unittest.TextTestRunner(resultclass=ObservedResult, verbosity=2).run(suite)
    observation = {
        "tests_run": result.testsRun, "test_ids": result.test_ids,
        "failures": len(result.failures), "errors": len(result.errors),
        "skipped": len(result.skipped), "expected_failures": len(result.expectedFailures),
        "unexpected_successes": len(result.unexpectedSuccesses),
    }
    result_path.write_text(json.dumps(observation), encoding="utf-8")
    return 0 if result.wasSuccessful() else 1


def observe(source: dict[str, bytes], tests: dict[str, bytes], timeout: float) -> dict:
    observation = {"source_sha256": tree_digest(source), "timed_out": False}
    with tempfile.TemporaryDirectory(prefix="showwork-control-") as scratch:
        root = Path(scratch)
        workspace = root / "workspace"
        write_copy(workspace, source)
        if (workspace / "_checks").exists():
            raise ValueError("fixture reserves the _checks directory for shared tests")
        write_copy(workspace / "_checks", tests)
        output = root / "observation.json"
        argv = [sys.executable, "-I", "-B", str(Path(__file__).resolve()), "--worker", str(output)]
        observation["argv"] = argv
        try:
            proc = run_process(argv, cwd=workspace, env=dict(os.environ),
                               timeout=timeout, capture_output=True)
            observation["exit_code"] = proc.returncode
            stdout, stderr = proc.stdout, proc.stderr
            try:
                observation.update(json.loads(output.read_text(encoding="utf-8")))
            except (OSError, ValueError):
                observation["error"] = "test process did not produce a valid observation"
        except subprocess.TimeoutExpired as exc:
            observation.update(timed_out=True, exit_code=None, error="test process timed out")
            stdout, stderr = exc.stdout or "", exc.stderr or ""
        except OSError as exc:
            observation.update(exit_code=None, error=str(exc))
            stdout, stderr = "", ""
        observation.update(
            stdout_sha256=digest(stdout.encode("utf-8")),
            stderr_sha256=digest(stderr.encode("utf-8")),
            stdout_tail=stdout[-2000:], stderr_tail=stderr[-2000:],
        )
    return observation


def conclusive(row: dict) -> bool:
    counts = ("tests_run", "failures", "errors", "skipped", "expected_failures", "unexpected_successes")
    if row.get("error") or row.get("timed_out"):
        return False
    if any(type(row.get(key)) is not int or row[key] < 0 for key in counts):
        return False
    return (
        row["tests_run"] > 0
        and isinstance(row.get("test_ids"), list)
        and len(row["test_ids"]) == row["tests_run"]
        and all(isinstance(item, str) for item in row["test_ids"])
        and not any(row[key] for key in ("errors", "skipped", "expected_failures", "unexpected_successes"))
        and row.get("exit_code") == (1 if row["failures"] else 0)
    )


def compare(broken: Path, repaired: Path, tests: Path, timeout: float = 30) -> dict:
    if not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("timeout must be positive and finite")
    shared = read_fixture(tests)
    bad_source, good_source = read_fixture(broken), read_fixture(repaired)
    before = observe(bad_source, shared, timeout)
    after = observe(good_source, shared, timeout)
    if not conclusive(before) or not conclusive(after) or before["test_ids"] != after["test_ids"]:
        verdict = "INCONCLUSIVE"
    elif after["failures"]:
        verdict = "REPAIR_FAILED"
    elif not before["failures"]:
        verdict = "INSENSITIVE"
    else:
        verdict = "SENSITIVE"
    return {
        "verdict": verdict, "broken": before, "repaired": after,
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "tests_sha256": tree_digest(shared), "runner_sha256": digest(Path(__file__).read_bytes()),
        "python": sys.version, "timeout_seconds": timeout,
        "independent_review": "not established",
        "scope": "sensitivity to this supplied defect only; test adequacy and requirement coverage not assessed",
    }


def main() -> int:
    if len(sys.argv) == 3 and sys.argv[1] == "--worker":
        return worker(Path(sys.argv[2]))
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("broken", "repaired", "tests", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--timeout", type=float, default=30, help="seconds per test process")
    args = parser.parse_args()
    output = args.output.resolve()
    inputs = [args.broken, args.repaired, args.tests]
    if any(output == path.resolve() or path.resolve() in output.parents for path in inputs):
        parser.error("output must be outside the input fixtures and tests")
    try:
        result = compare(*inputs, args.timeout)
    except (OSError, ValueError) as exc:
        result = {"verdict": "INCONCLUSIVE", "error": str(exc)}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print("negative control: " + result["verdict"])
    return {"SENSITIVE": 0, "INSENSITIVE": 1, "REPAIR_FAILED": 1, "INCONCLUSIVE": 2}[result["verdict"]]


if __name__ == "__main__":
    raise SystemExit(main())
