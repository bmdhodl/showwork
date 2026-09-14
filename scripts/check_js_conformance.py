"""Locked Python entry point for the existing JavaScript chain fixtures."""

import subprocess
import sys

raise SystemExit(subprocess.run(["node", "js/showwork-audit/test.mjs"], check=False).returncode)
