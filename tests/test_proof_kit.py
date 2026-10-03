"""The same example probes exercise real broken paths and a repair."""

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest


ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "examples/proof-kit/run.py"


@pytest.mark.parametrize("example", ["failure", "damage", "handoff"])
def test_proof_kit_actual_failure_repair_and_rerun(tmp_path, example):
    env = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
    proc = subprocess.run([sys.executable, "-O", str(SCRIPT), str(tmp_path / "toy"),
                           "--example", example], env=env, capture_output=True, text=True,
                          timeout=90, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    result = json.loads(proc.stdout)["results"][0]
    if example == "handoff":
        assert result["broken_explicit_rerun"] == 2
        assert result["receipt_bytes_preserved"] is True
        assert result["approval_inherited"] is False
    else:
        assert 2 in result.values()
    assert "VERIFIED" in result.values()


def test_proof_kit_refuses_an_existing_workspace(tmp_path):
    marker = tmp_path / "owned.txt"
    marker.write_text("keep")
    proc = subprocess.run([sys.executable, str(SCRIPT), str(tmp_path)],
                          capture_output=True, text=True, timeout=30,
                          creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    assert proc.returncode != 0
    assert "existing data" in proc.stderr
    assert marker.read_text() == "keep"
