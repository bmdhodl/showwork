"""Smoke the installed distribution in a new temporary workspace."""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

import showwork


def smoke():
    checks = []
    with tempfile.TemporaryDirectory(prefix="showwork-smoke-") as directory:
        root = Path(directory)
        env = dict(os.environ)
        env.pop("PYTHONPATH", None)
        env.pop("SHOWWORK_ROOT", None)

        def run(name, args, expected=0):
            proc = subprocess.run([sys.executable, "-m", "showwork", "--root", str(root), *args],
                                  env=env, cwd=root, capture_output=True, text=True, timeout=30)
            assert proc.returncode == expected, (name, proc.returncode, proc.stdout, proc.stderr)
            checks.append(name)
            return proc.stdout

        run("init", ["init"])
        run("start", ["start", "--session", "smoke"])
        run("claim missing file", ["claim", "--session", "smoke", "--claim", "output exists",
                                   "--type", "file_exists", "--path", "output.txt"])
        run("refuse false done", ["finish", "--session", "smoke"], 2)
        (root / "output.txt").write_text("real output", encoding="utf-8")
        run("accept real outcome", ["finish", "--session", "smoke"])
        state = json.loads(run("verify", ["verify", "--session", "smoke", "--json", "--no-report"]))
        assert state["verdict"] == "GREEN"
        run("chain audit", ["audit"])
        payload = json.loads(run("receipts", ["receipts", "--session", "smoke", "--json"]))
        assert payload["states"] == ["verified"]
        run("status", ["status", "--session", "smoke"])
        run("report", ["report"])
        run("wrapper", ["run", "--session", "wrapped", "--keep", "passed", "--",
                        sys.executable, "-c", "print('passed')"])
        run("empty wrapper gate", ["run", "--session", "empty", "--gate", "--",
                                   sys.executable, "-c", "print('done')"], 2)
        run("timeout", ["run", "--session", "timeout", "--max-seconds", "0.2", "--",
                        sys.executable, "-c", "import time; time.sleep(10)"], 2)
        return {"version": showwork.__version__, "python": sys.version.split()[0],
                "installed_from": showwork.__file__, "passed": checks}


if __name__ == "__main__":
    print(json.dumps(smoke(), indent=2))
