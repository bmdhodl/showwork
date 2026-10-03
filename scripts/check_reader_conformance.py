"""Run the existing JavaScript auditor and reader against frozen fixtures."""

import os
from pathlib import Path
import shutil
import subprocess
import sys


def main():
    node = shutil.which("node")
    if not node:
        print("Node is required for reader conformance; no checks ran", file=sys.stderr)
        return 2
    root = Path(__file__).resolve().parents[1]
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    result = subprocess.run([node, str(root / "js/showwork-audit/test.mjs")],
                            cwd=root, timeout=120, creationflags=flags,
                            capture_output=True, text=True)
    print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)
    if result.returncode:
        return result.returncode
    print("reader conformance passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
