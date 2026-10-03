"""Dated exploratory adapter; four unchanged SW-02 seeds, not a new corpus."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--patchcase-checkout", type=Path, required=True)
parser.add_argument("--out", type=Path, required=True)
args = parser.parse_args()
source = args.patchcase_checkout.resolve() / "src"
if not (source / "patchcase/engine.py").is_file():
    parser.error("a reviewed PatchCase source checkout is required")
sys.path.insert(0, str(source))
from patchcase.engine import run_manifest
import patchcase

original_run = subprocess.run
def hidden_run(*args, **kwargs):
    kwargs.setdefault("creationflags", getattr(subprocess, "CREATE_NO_WINDOW", 0))
    return original_run(*args, **kwargs)
subprocess.run = hidden_run

seed = Path(__file__).resolve().parents[3] / "examples/sw-02-bench/seed"
cases = {}
expected = {"honest-pass": "verified", "honest-fail": "falsified",
            "weak-fixture": "verified", "undeclared-deletion": "verified"}
with tempfile.TemporaryDirectory(prefix="sw24-patchcase-") as temporary:
    for name in expected:
        root = Path(temporary) / name
        shutil.copytree(seed, root)
        if name == "honest-fail":
            (root / "test_add.py").write_text("def test_add():\n    assert False\n", encoding="utf-8")
        if name == "weak-fixture":
            (root / "add.py").write_text("def add(a,b):\n    return a+b+1\n", encoding="utf-8")
            (root / "test_add.py").write_text("import add\ndef test_add():\n    add.add = lambda a,b: 4\n    assert add.add(2,2) == 4\n", encoding="utf-8")
        if name == "undeclared-deletion":
            (root / "bystander.txt").unlink()
        manifest = {"title": "Frozen SW-02 comparison: " + name, "claims": [{
            "id": "tests", "statement": "The supplied pytest suite passes",
            "falsification": "A failing actual test produces a nonzero exit",
            "checks": [{"id": "pytest", "name": "Run the supplied test", "type": "command",
                        "command": [sys.executable, "-m", "pytest", "-q", "test_add.py"],
                        "expect": {"exit_code": 0}, "timeout_seconds": 30}]}]}
        manifest_path = root / "comparison.json"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        evidence = run_manifest(root, manifest_path)
        production = None
        if name == "weak-fixture":
            production = hidden_run([sys.executable, "-c", "from add import add; print(add(2,2))"],
                                    cwd=root, capture_output=True, text=True, check=True).stdout.strip()
        observed = evidence["overall_status"]
        cases[name] = {"observed": observed, "expected": expected[name],
                       "match": observed == expected[name], "production_stdout": production,
                       "manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
                       "evidence": evidence}
out = args.out.resolve()
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps({"package_version": patchcase.__version__, "cases": cases}, indent=2), encoding="utf-8")
print(json.dumps({"version": patchcase.__version__, "cases": {
    name: {key: value for key, value in row.items() if key != "evidence"}
    for name, row in cases.items()}}))
if not all(row["match"] for row in cases.values()):
    raise SystemExit(1)
