"""Bound child execution and terminate its process tree on timeout.

Captured output uses files, so an inherited pipe cannot hold timeout cleanup
open. This contains ordinary descendants, not processes deliberately escaping
their process group or operating-system security boundary.
"""

from contextlib import ExitStack
import os
import signal
import subprocess
import tempfile


def _kill_tree(proc: subprocess.Popen) -> None:
    if os.name == "nt":
        taskkill = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32", "taskkill.exe")
        subprocess.run([taskkill, "/PID", str(proc.pid), "/T", "/F"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                       timeout=10, creationflags=subprocess.CREATE_NO_WINDOW)
    else:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    if proc.poll() is None:
        proc.kill()
    proc.wait(timeout=10)


def run_process(argv, *, cwd, env, timeout=None, capture_output=False):
    """Return a text CompletedProcess; TimeoutExpired carries partial output."""
    with ExitStack() as stack:
        stdout = stack.enter_context(tempfile.TemporaryFile()) if capture_output else None
        stderr = stack.enter_context(tempfile.TemporaryFile()) if capture_output else None
        options = {"start_new_session": True} if os.name != "nt" else {}
        proc = subprocess.Popen(argv, cwd=cwd, env=env, stdout=stdout, stderr=stderr, **options)
        timed_out = False
        try:
            proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            _kill_tree(proc)
        except BaseException:
            _kill_tree(proc)
            raise

        def read(handle):
            if handle is None:
                return None
            handle.seek(0)
            return handle.read().decode("utf-8", errors="replace")

        out, err = read(stdout), read(stderr)
        if timed_out:
            raise subprocess.TimeoutExpired(argv, timeout, output=out, stderr=err)
        return subprocess.CompletedProcess(argv, proc.returncode, out, err)
