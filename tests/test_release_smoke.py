"""Release smoke must reject broken evidence with Python optimization enabled."""

import os
from pathlib import Path
import subprocess
import sys

import pytest


@pytest.mark.parametrize("failure", ["exit", "verdict", "receipts", "none"])
def test_optimized_installed_smoke_preserves_fail_closed_checks(tmp_path, failure):
    root = Path(__file__).parents[1]
    runner = tmp_path / "smoke_control.py"
    runner.write_text(
        "import importlib.util,json,subprocess\n"
        "from pathlib import Path\n"
        "from types import SimpleNamespace\n"
        f"failure={failure!r}\n"
        "def controlled(argv,**kwargs):\n"
        "    code=0\n"
        "    if 'finish' in argv and not (Path(argv[argv.index('--root')+1])/'output.txt').exists(): code=2\n"
        "    if '--gate' in argv or '--max-seconds' in argv: code=2\n"
        "    if 'init' in argv and failure=='exit': code=42\n"
        "    data={'verdict':'RED' if failure=='verdict' else 'GREEN','outcome':{'verdict':'VERIFIED'}}\n"
        "    if 'receipts' in argv: data={'states':['unknown' if failure=='receipts' else 'verified']}\n"
        "    return SimpleNamespace(returncode=code,stdout=json.dumps(data),stderr='')\n"
        "subprocess.run=controlled\n"
        f"spec=importlib.util.spec_from_file_location('actual_smoke',{str(root/'scripts/smoke_release.py')!r})\n"
        "module=importlib.util.module_from_spec(spec)\n"
        "spec.loader.exec_module(module)\n"
        "print(json.dumps(module.smoke()))\n",
        encoding="utf-8",
    )
    env = {**os.environ, "PYTHONPATH": str(root / "src")}
    result = subprocess.run(
        [sys.executable, "-O", str(runner)], cwd=tmp_path, env=env,
        capture_output=True, text=True, timeout=30,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    if failure == "none":
        assert result.returncode == 0, result.stderr
        assert '"passed"' in result.stdout
    else:
        assert result.returncode != 0, "optimized smoke silently accepted broken evidence"
        assert "AssertionError" in result.stderr
