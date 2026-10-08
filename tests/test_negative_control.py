"""The same real tests must reject broken code and accept its repair."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "examples/acceptance-review/compare.py"
TEST = """import unittest
from app import add

class Acceptance(unittest.TestCase):
    def test_add(self):
        self.assertEqual(add(2, 2), 4)
"""


def prepare(tmp_path, test=TEST, broken="return a + b + 1"):
    for name, content in [("broken", broken), ("repaired", "return a + b")]:
        folder = tmp_path / name
        folder.mkdir()
        (folder / "app.py").write_text(f"def add(a, b):\n    {content}\n", encoding="utf-8")
    tests = tmp_path / "checks"
    tests.mkdir()
    (tests / "test_app.py").write_text(test, encoding="utf-8")
    return tmp_path


def run(root, *extra):
    output = root / "result.json"
    proc = subprocess.run(
        [sys.executable, str(RUNNER), "--broken", str(root / "broken"),
         "--repaired", str(root / "repaired"), "--tests", str(root / "checks"),
         "--output", str(output), *extra], capture_output=True, text=True,
        timeout=30, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    assert output.is_file(), proc.stderr
    return proc, json.loads(output.read_text(encoding="utf-8"))


def test_same_assertion_fails_before_repair_and_passes_after(tmp_path):
    """REGRESSION: a passing command alone cannot expose an always-pass check."""
    root = prepare(tmp_path)
    before = {p.relative_to(root): p.read_bytes() for p in root.rglob("*.py")}
    proc, result = run(root)
    assert proc.returncode == 0, proc.stderr
    assert result["verdict"] == "SENSITIVE"
    assert result["broken"]["failures"] == 1
    assert result["repaired"]["failures"] == 0
    assert result["broken"]["test_ids"] == result["repaired"]["test_ids"]
    assert result["independent_review"] == "not established"
    assert result["broken"]["source_sha256"] != result["repaired"]["source_sha256"]
    assert len(result["tests_sha256"]) == 64
    assert len(result["runner_sha256"]) == 64
    assert len(result["broken"]["stdout_sha256"]) == 64
    assert {p.relative_to(root): p.read_bytes() for p in root.rglob("*.py")} == before
    assert not list(root.rglob("__pycache__"))


def test_always_pass_test_is_insensitive(tmp_path):
    root = prepare(tmp_path, TEST.replace("self.assertEqual(add(2, 2), 4)", "self.assertTrue(True)"))
    proc, result = run(root)
    assert proc.returncode == 1
    assert result["verdict"] == "INSENSITIVE"


@pytest.mark.parametrize("test,broken", [
    (TEST, "raise RuntimeError('crash')"),
    (TEST, "return ("),
    (TEST.replace("from app import add", "from missing_dependency import add"), "return 5"),
    ("import unittest\n", "return 5"),
    (TEST.replace("    def test_add", "    @unittest.skip('skip')\n    def test_add"), "return 5"),
    (TEST.replace("    def test_add", "    @unittest.expectedFailure\n    def test_add"), "return 5"),
])
def test_errors_empty_and_skipped_suites_are_inconclusive(tmp_path, test, broken):
    root = prepare(tmp_path, test, broken)
    proc, result = run(root)
    assert proc.returncode == 2
    assert result["verdict"] == "INCONCLUSIVE"


def test_repair_that_still_fails_is_not_sensitive(tmp_path):
    root = prepare(tmp_path)
    (root / "repaired/app.py").write_text("def add(a, b):\n    return 6\n", encoding="utf-8")
    proc, result = run(root)
    assert proc.returncode == 1
    assert result["verdict"] == "REPAIR_FAILED"


def test_timeout_does_not_count_as_a_caught_defect(tmp_path):
    root = prepare(tmp_path, broken="__import__('time').sleep(60)")
    before = (root / "broken/app.py").read_bytes()
    proc, result = run(root, "--timeout", "0.5")
    assert proc.returncode == 2
    assert result["verdict"] == "INCONCLUSIVE"
    assert result["broken"]["timed_out"] is True
    assert (root / "broken/app.py").read_bytes() == before


def test_output_cannot_overwrite_fixture_or_tests(tmp_path):
    root = prepare(tmp_path)
    target = root / "broken/app.py"
    before = target.read_bytes()
    proc = subprocess.run(
        [sys.executable, str(RUNNER), "--broken", str(root / "broken"),
         "--repaired", str(root / "repaired"), "--tests", str(root / "checks"),
         "--output", str(target)], capture_output=True, text=True, timeout=15,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    assert proc.returncode == 2
    assert "output must be outside" in proc.stderr
    assert target.read_bytes() == before


def test_setup_assertion_is_not_a_caught_production_defect(tmp_path):
    test = TEST.replace("    def test_add", "    def setUp(self):\n        if add(2, 2) != 4:\n            self.fail('fixture setup failed')\n\n    def test_add")
    root = prepare(tmp_path, test)
    proc, result = run(root)
    assert proc.returncode == 2
    assert result["verdict"] == "INCONCLUSIVE"


@pytest.mark.parametrize("phase", ["setUp", "tearDown"])
def test_subtest_fixture_assertion_is_inconclusive(tmp_path, phase):
    test = TEST.replace("    def test_add", f"    def {phase}(self):\n        with self.subTest(phase='{phase}'):\n            self.assertEqual(add(2, 2), 4)\n\n    def test_add")
    root = prepare(tmp_path, test)
    proc, result = run(root)
    assert proc.returncode == 2
    assert result["verdict"] == "INCONCLUSIVE"
    assert result["broken"]["errors"] == 1


@pytest.mark.parametrize("subtest", [False, True])
def test_partialmethod_assertion_is_a_caught_defect(tmp_path, subtest):
    test = """import functools
import unittest
from app import add

class Acceptance(unittest.TestCase):
    def check_sum(self, expected):
        ASSERTION
    test_add = functools.partialmethod(check_sum, 4)
""".replace("ASSERTION", "with self.subTest():\n            self.assertEqual(add(2, 2), expected)" if subtest else "self.assertEqual(add(2, 2), expected)")
    root = prepare(tmp_path, test)
    proc, result = run(root)
    assert proc.returncode == 0, proc.stderr
    assert result["verdict"] == "SENSITIVE"
    assert result["broken"]["failures"] == 1


def test_bundled_persistence_example_is_sensitive(tmp_path):
    fixtures = RUNNER.parent / "fixtures"
    output = tmp_path / "report.json"
    proc = subprocess.run(
        [sys.executable, str(RUNNER), "--broken", str(fixtures / "broken"),
         "--repaired", str(fixtures / "repaired"), "--tests", str(fixtures / "checks"),
         "--output", str(output)], capture_output=True, text=True, timeout=30,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    assert proc.returncode == 0, proc.stderr
    result = json.loads(output.read_text(encoding="utf-8"))
    assert result["verdict"] == "SENSITIVE"
    assert result["broken"]["failures"] == 1
    assert result["repaired"]["tests_run"] == 1


def test_changed_test_inventory_is_inconclusive(tmp_path):
    test = TEST + "\nif add(2, 2) == 4:\n    del Acceptance.test_add\n"
    root = prepare(tmp_path, test)
    proc, result = run(root)
    assert proc.returncode == 2
    assert result["verdict"] == "INCONCLUSIVE"


@pytest.mark.parametrize("timeout", ["0", "-1", "nan", "inf"])
def test_invalid_timeout_never_qualifies(tmp_path, timeout):
    root = prepare(tmp_path)
    proc, result = run(root, "--timeout", timeout)
    assert proc.returncode == 2
    assert result["verdict"] == "INCONCLUSIVE"


def test_missing_fixture_is_inconclusive(tmp_path):
    root = prepare(tmp_path)
    (root / "broken/app.py").unlink()
    (root / "broken").rmdir()
    proc, result = run(root)
    assert proc.returncode == 2
    assert result["verdict"] == "INCONCLUSIVE"


def test_each_run_uses_new_scratch_and_cleans_it_on_timeout(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location("negative_control", RUNNER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    root = prepare(tmp_path)
    seen = []

    def timeout(argv, *, cwd, env, timeout, capture_output):
        seen.append(Path(cwd))
        (Path(cwd) / "app.py").write_text("damaged scratch", encoding="utf-8")
        raise subprocess.TimeoutExpired(argv, timeout)

    monkeypatch.setattr(module, "run_process", timeout)
    result = module.compare(root / "broken", root / "repaired", root / "checks", 1)
    assert result["verdict"] == "INCONCLUSIVE"
    assert len(seen) == 2 and seen[0] != seen[1]
    assert all(not path.exists() for path in seen)
    assert "damaged scratch" not in (root / "broken/app.py").read_text()
