"""Inputs come from the fixture; the application must produce the file."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from app import load, save


class PersistenceAcceptance(unittest.TestCase):
    def test_save_survives_a_fresh_reader(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "theme.txt"
            self.assertIsNone(load(path))
            save(path, "dark")
            self.assertEqual(load(path), "dark")
            fresh = subprocess.run(
                [sys.executable, "-B", "-c",
                 "from pathlib import Path; from app import load; "
                 "import sys; print(load(Path(sys.argv[1])))", str(path)],
                capture_output=True, text=True, timeout=10,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            self.assertEqual(fresh.returncode, 0, fresh.stderr)
            self.assertEqual(fresh.stdout.strip(), "dark")
