"""Same-slug concurrent appends must keep every record.

Issue #199: Windows ``open("a")`` is seek-to-end plus write. Two processes
that append to one session file at the same instant can overwrite a whole
record; the loser still prints success and audit stays GREEN. POSIX O_APPEND
is atomic for small writes, so Linux CI usually does not see the loss.

These tests pin the new contract on every platform: ``_append`` holds an
exclusive lock around one ``os.write`` of the full line, reads ``prev``
inside that lock, and fails loudly if the lock cannot be taken.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

from showwork.audit import audit_file, audit_root
from showwork.ledger import (
    _append,
    record_claim,
    session_claims_path,
    start_session,
)

SRC = Path(__file__).resolve().parents[1] / "src"
N_WORKERS = 8
CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def _child_env() -> dict[str, str]:
    env = os.environ.copy()
    inherited = env.get("PYTHONPATH")
    env["PYTHONPATH"] = os.pathsep.join(filter(None, [str(SRC), inherited]))
    env.pop("SHOWWORK_ROOT", None)
    env.pop("SHOWWORK_SESSION", None)
    env.pop("SHOWWORK_VERIFYING", None)
    return env


def test_append_holds_lock_around_prev_and_single_os_write(monkeypatch, tmp_path):
    """Would fail on current main on every OS: no lock, text-mode open("a")."""
    import showwork.ledger as ledger

    events: list[object] = []
    held = {"locked": False}
    real_acquire = ledger._acquire_exclusive_lock
    real_release = ledger._release_exclusive_lock
    real_prev = ledger._prev_hash
    real_write = os.write

    def acquire(fd, path, timeout=None):
        result = real_acquire(fd, path, timeout=timeout)
        held["locked"] = True
        events.append("lock")
        return result

    def release(fd):
        events.append("unlock")
        held["locked"] = False
        return real_release(fd)

    def prev(path):
        assert held["locked"], "chain head was read without the exclusive lock"
        events.append("prev")
        return real_prev(path)

    def write(fd, data):
        assert held["locked"], "os.write ran without the exclusive lock"
        events.append(("write", bytes(data)))
        return real_write(fd, data)

    monkeypatch.setattr(ledger, "_acquire_exclusive_lock", acquire)
    monkeypatch.setattr(ledger, "_release_exclusive_lock", release)
    monkeypatch.setattr(ledger, "_prev_hash", prev)
    monkeypatch.setattr(os, "write", write)

    record_claim(tmp_path, "s", "one")

    kinds = [e[0] if isinstance(e, tuple) else e for e in events]
    assert kinds == ["lock", "prev", "write", "unlock"]
    payload = events[2][1]
    assert payload.endswith(b"\n")
    assert payload.count(b"\n") == 1
    record = json.loads(payload.decode("utf-8"))
    assert record["claim"] == "one"
    assert "prev" in record


def test_append_fails_loudly_when_lock_unavailable(tmp_path, monkeypatch):
    """Would fail on current main on every OS: _append did not take a lock."""
    import showwork.ledger as ledger

    start_session(tmp_path, "held")
    record_claim(tmp_path, "held", "seed")
    path = session_claims_path(tmp_path, "held")
    ready = tmp_path / "holder-ready"
    holder = subprocess.Popen(
        [
            sys.executable,
            "-c",
            "import sys, time\n"
            "from pathlib import Path\n"
            "from showwork.ledger import _acquire_exclusive_lock, _open_append_fd\n"
            "path = Path(sys.argv[1])\n"
            "ready = Path(sys.argv[2])\n"
            "fd = _open_append_fd(path)\n"
            "_acquire_exclusive_lock(fd, path, timeout=5)\n"
            "ready.write_text('locked', encoding='utf-8')\n"
            "time.sleep(60)\n",
            str(path),
            str(ready),
        ],
        cwd=tmp_path,
        env=_child_env(),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        creationflags=CREATE_NO_WINDOW,
    )
    try:
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            if ready.is_file():
                break
            if holder.poll() is not None:
                out, err = holder.communicate()
                pytest.fail(f"lock holder exited {holder.returncode}: {out}{err}")
            time.sleep(0.01)
        else:
            pytest.fail("lock holder did not acquire the lock")
        monkeypatch.setattr(ledger, "_APPEND_LOCK_TIMEOUT_SECONDS", 0.3)
        with pytest.raises(TimeoutError, match="could not lock ledger file"):
            _append(path, {"session": "held", "ts": "t", "claim": "blocked"})
    finally:
        holder.kill()
        holder.wait(timeout=5)


def test_concurrent_record_claim_keeps_all_records(tmp_path):
    """N parallel record_claim processes, released by a barrier.

    On current main this fails on Windows (lost records, audit still GREEN).
    On Linux main, POSIX O_APPEND usually keeps the lines, so this test can
    pass there even without the lock. The lock/write unit test above is what
    fails on every OS before the fix.
    """
    session = "parallel"
    start_session(tmp_path, session)
    ready_dir = tmp_path / "ready"
    ready_dir.mkdir()
    barrier = tmp_path / "go"
    workers = []
    for index in range(N_WORKERS):
        script = (
            "import sys, time\n"
            "from pathlib import Path\n"
            "from showwork.ledger import record_claim\n"
            f"ready = Path({str(ready_dir / str(index))!r})\n"
            f"barrier = Path({str(barrier)!r})\n"
            "ready.write_text('ready', encoding='utf-8')\n"
            "for _ in range(1000):\n"
            "    if barrier.exists():\n"
            "        break\n"
            "    time.sleep(0.01)\n"
            "else:\n"
            "    raise SystemExit('barrier was not released')\n"
            f"record_claim(Path({str(tmp_path)!r}), {session!r}, "
            f"'parallel claim {index}')\n"
            "print('claim recorded')\n"
        )
        workers.append(
            subprocess.Popen(
                [sys.executable, "-c", script],
                cwd=tmp_path,
                env=_child_env(),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                creationflags=CREATE_NO_WINDOW,
            )
        )

    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        if all((ready_dir / str(i)).is_file() for i in range(N_WORKERS)):
            break
        time.sleep(0.01)
    else:
        pytest.fail("workers did not reach the barrier")
    barrier.write_text("go", encoding="utf-8")

    outputs = []
    for proc in workers:
        stdout, stderr = proc.communicate(timeout=30)
        outputs.append((proc.returncode, stdout, stderr))
    assert all(code == 0 for code, _out, _err in outputs), outputs
    recorded = sum(out.count("claim recorded") for _code, out, _err in outputs)
    assert recorded == N_WORKERS

    path = session_claims_path(tmp_path, session)
    records = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    claims = [rec["claim"] for rec in records]
    assert len(records) == N_WORKERS
    assert set(claims) == {f"parallel claim {i}" for i in range(N_WORKERS)}

    file_state = audit_file(path)
    assert file_state["verdict"] == "GREEN"
    assert file_state["records"] == N_WORKERS
    root_state = audit_root(tmp_path)
    assert root_state["verdict"] == "GREEN"
