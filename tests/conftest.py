import sys
from pathlib import Path

import pytest


# The test gate must exercise this checkout, even when another clone has been
# installed editable in the interpreter.  pytest's `pythonpath = ["src"]`
# setting does not guarantee precedence over an existing editable finder.
_LOCAL_SRC = str(Path(__file__).resolve().parents[1] / "src")
if _LOCAL_SRC in sys.path:
    sys.path.remove(_LOCAL_SRC)
sys.path.insert(0, _LOCAL_SRC)


@pytest.fixture(autouse=True)
def _clear_verifying_env(monkeypatch):
    # Tests must behave identically whether or not the suite is itself running
    # under a showwork `command` claim (dogfooding runs it exactly that way).
    # Recursion stays bounded: these tests spawn only tiny leaf scripts.
    monkeypatch.delenv("SHOWWORK_VERIFYING", raising=False)
    monkeypatch.delenv("SHOWWORK_SESSION", raising=False)
    monkeypatch.delenv("SHOWWORK_ROOT", raising=False)
