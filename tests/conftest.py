import pytest


@pytest.fixture(autouse=True)
def _clear_verifying_env(monkeypatch):
    # Tests must behave identically whether or not the suite is itself running
    # under a showwork `command` claim (dogfooding runs it exactly that way).
    # Recursion stays bounded: these tests spawn only tiny leaf scripts.
    monkeypatch.delenv("SHOWWORK_VERIFYING", raising=False)
