"""Run against either release: restarting must not erase a deleted file.

python examples/restart_demo.py
Only a temporary directory is modified. No model or network call is needed.
"""

import json
from pathlib import Path
import tempfile

import showwork
from showwork.ledger import start_session, record_claim, finish_session


def demo():
    with tempfile.TemporaryDirectory(prefix="showwork-demo-") as folder:
        root = Path(folder)
        (root / "config.txt").write_text("keep this", encoding="utf-8")
        (root / "result.txt").write_text("done", encoding="utf-8")
        start_session(root, "demo")
        (root / "config.txt").unlink()
        record_claim(root, "demo", "result exists", check={
            "type": "file_exists", "path": "result.txt",
        })
        start_session(root, "demo")
        exit_code, state = finish_session(root, "demo")
        return {
            "version": showwork.__version__,
            "scenario": "delete config.txt, reopen the same session, claim result.txt",
            "config_exists": (root / "config.txt").exists(),
            "finish_exit": exit_code,
            "verdict": state["verdict"],
            "gaps": [r["claim"] for r in state["results"] if r["status"] == "fail"],
        }


if __name__ == "__main__":
    print(json.dumps(demo(), indent=2))
