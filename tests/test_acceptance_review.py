"""Acceptance fixtures supply inputs; the application must produce the output."""

import importlib.util
from pathlib import Path
import subprocess
import sys

import pytest

EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "acceptance-review"


def load_example():
    spec = importlib.util.spec_from_file_location("acceptance_review", EXAMPLE / "acceptance.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_real_store_survives_fresh_process_reopen(tmp_path):
    """REGRESSION: no test exercised persisted production writes and reopen."""
    module = load_example()
    module.accept_store(module.SettingsStore, tmp_path)
    proc = subprocess.run([sys.executable, str(EXAMPLE / "acceptance.py"),
                           "--read-existing", str(tmp_path)], capture_output=True,
                          text=True, timeout=15,
                          creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    assert proc.returncode == 0, proc.stderr
    assert "persisted values read" in proc.stdout


@pytest.mark.parametrize("mutant", ["EmptyStore", "CacheOnlyStore"])
def test_application_mutations_fail_the_same_acceptance(tmp_path, mutant):
    module = load_example()
    with pytest.raises(AssertionError):
        module.accept_store(getattr(module, mutant), tmp_path)


def test_read_existing_cannot_seed_a_missing_output(tmp_path):
    proc = subprocess.run([sys.executable, str(EXAMPLE / "acceptance.py"),
                           "--read-existing", str(tmp_path)], capture_output=True,
                          text=True, timeout=15,
                          creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    assert proc.returncode != 0
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("arguments", [["--mutation", "empty-write"], ["--mutation", "cache-only"], ["--read-existing"]])
def test_optimized_python_cannot_disable_the_acceptance_gate(tmp_path, arguments):
    """REGRESSION: -O silently removed acceptance assertions and returned pass."""
    proc = subprocess.run([sys.executable, "-O", str(EXAMPLE / "acceptance.py"),
                           *arguments, str(tmp_path)], capture_output=True, text=True,
                          timeout=15, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    assert proc.returncode == 1
    assert "acceptance failed" in proc.stdout
