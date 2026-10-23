"""Static comparison of Python test files against a pinned base commit.

A `tests_intact` check fails when, relative to its base commit, a test file or
a test function was deleted, a test gained a skip or xfail marker, or a test's
assertion count or literal parametrize case count fell. Source is parsed with
`ast`; tests are never imported or run. The comparison covers pytest and
unittest naming conventions only, and a rewrite that keeps every count (for
example a weaker assertion in place of a stronger one) still passes this check
alone.

When a test file covered by a declared check is rewritten in the same session
as non-test code, `covered_edit_results` refuses and names the test file and
the check. Adding tests without rewriting existing assertions still passes.
"""

from __future__ import annotations

import ast
import re
import subprocess
from collections import Counter
from pathlib import Path

BASE_RE = re.compile(r"[0-9a-f]{40}|[0-9a-f]{64}")
MAX_TEST_FILES = 5000
MAX_TEST_FILE_BYTES = 4 * 1024 * 1024
MAX_FINDINGS_SHOWN = 5
GIT_TIMEOUT_S = 30
SKIP_NAMES = frozenset({"skip", "skipif", "xfail", "skipIf", "skipUnless",
                        "expectedFailure", "skipTest", "SkipTest", "importorskip"})
RAISES_NAMES = frozenset({"raises", "warns", "deprecated_call"})


def is_test_file(rel: str) -> bool:
    name = rel.rsplit("/", 1)[-1]
    return name.endswith(".py") and (name.startswith("test_") or name.endswith("_test.py"))


def shape_error(check: dict) -> str | None:
    path = check.get("path")
    if not isinstance(path, str) or not path.strip():
        return "tests_intact.path must be a non-empty string"
    parts = path.replace("\\", "/").split("/")
    if path.startswith(("/", "\\")) or re.match(r"[A-Za-z]:", path) or ".." in parts:
        return f"tests_intact.path must stay under the project root: {path}"
    base = check.get("base")
    if not isinstance(base, str) or BASE_RE.fullmatch(base) is None:
        return "tests_intact.base must be a full lowercase commit ID"
    return None


def _terminal(node: ast.AST) -> str | None:
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, ast.Name):
        return node.id
    return None


def _skip_marks(node: ast.AST) -> int:
    return sum(_terminal(n) in SKIP_NAMES for n in ast.walk(node))


def _assertions(function: ast.AST) -> int:
    return len(_assertion_prints(function))


def _assertion_prints(function: ast.AST) -> list[str]:
    prints = []
    for node in ast.walk(function):
        if isinstance(node, ast.Assert):
            prints.append(ast.dump(node, include_attributes=False))
        elif isinstance(node, ast.Call):
            name = _terminal(node.func) or ""
            if name.startswith("assert") or name in RAISES_NAMES:
                prints.append(ast.dump(node, include_attributes=False))
    return prints


def _cases(function: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    """Literal parametrize cases; a computed argument list counts as one."""
    total = 1
    for decorator in function.decorator_list:
        if not isinstance(decorator, ast.Call) or _terminal(decorator.func) != "parametrize":
            continue
        values = decorator.args[1] if len(decorator.args) > 1 else next(
            (k.value for k in decorator.keywords if k.arg == "argvalues"), None)
        if isinstance(values, (ast.List, ast.Tuple)):
            total *= len(values.elts)
    return total


def _is_test_class(node: ast.ClassDef) -> bool:
    return node.name.startswith("Test") or any(
        (_terminal(base) or "").endswith("TestCase") for base in node.bases)


def _non_definitions(body: list[ast.stmt]) -> list[ast.stmt]:
    return [s for s in body if not isinstance(s, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))]


def _collect(body: list[ast.stmt], prefix: str, inherited: int, out: dict) -> None:
    for stmt in body:
        if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)) and stmt.name.startswith("test"):
            out[prefix + stmt.name] = {
                "asserts": _assertions(stmt),
                "prints": _assertion_prints(stmt),
                "skips": inherited + sum(_skip_marks(d) for d in stmt.decorator_list)
                + sum(_skip_marks(s) for s in stmt.body),
                "cases": _cases(stmt),
            }
        elif isinstance(stmt, ast.ClassDef) and _is_test_class(stmt):
            own = (sum(_skip_marks(d) for d in stmt.decorator_list)
                   + sum(_skip_marks(s) for s in _non_definitions(stmt.body)))
            _collect(stmt.body, f"{prefix}{stmt.name}::", inherited + own, out)


def scan_source(source: str) -> dict[str, dict]:
    """Map each test id in one module to its assertion, skip and case counts."""
    tree = ast.parse(source)
    tests: dict[str, dict] = {}
    # Module-level pytestmark, pytest.skip(allow_module_level=True) and
    # importorskip apply to every test in the file.
    module_skips = sum(_skip_marks(s) for s in _non_definitions(tree.body))
    _collect(tree.body, "", module_skips, tests)
    return tests


def existing_tests_rewritten(before_src: str, after_src: str) -> bool:
    """True when an existing test dropped or replaced an assertion.

    New tests and extra assertions on an existing test do not count as a rewrite.
    """
    before = scan_source(before_src)
    after = scan_source(after_src)
    for test_id, old in before.items():
        new = after.get(test_id)
        if new is None:
            return True
        if Counter(old["prints"]) - Counter(new["prints"]):
            return True
    return False


def _git(root: Path, args: list[str], data: bytes | None = None) -> bytes:
    result = subprocess.run(["git", "--literal-pathspecs", "-C", str(root), *args],
                            input=data, capture_output=True, timeout=GIT_TIMEOUT_S)
    if result.returncode:
        detail = result.stderr.decode("utf-8", "replace").strip()[:300]
        raise ValueError(f"git {args[0]} failed: {detail}")
    return result.stdout


def base_test_files(root: Path, base: str, path: str) -> dict[str, bytes]:
    """Test files under `path` at `base`, read from Git objects, not the worktree."""
    _git(root, ["cat-file", "-e", f"{base}^{{commit}}"])
    listing = _git(root, ["ls-tree", "-r", "-z", "-l", base, "--", path])
    entries = []
    for entry in filter(None, listing.split(b"\0")):
        meta, _, name = entry.partition(b"\t")
        mode, kind, oid, size = meta.split()
        rel = name.decode("utf-8", "replace")
        if kind != b"blob" or mode not in (b"100644", b"100755") or not is_test_file(rel):
            continue
        if int(size) > MAX_TEST_FILE_BYTES:
            raise ValueError(f"{rel} at base exceeds the {MAX_TEST_FILE_BYTES} byte limit")
        entries.append((rel, oid.decode("ascii")))
    if len(entries) > MAX_TEST_FILES:
        raise ValueError(f"more than {MAX_TEST_FILES} test files under {path}")
    if not entries:
        return {}
    output = _git(root, ["cat-file", "--batch"],
                  data="".join(f"{oid}\n" for _, oid in entries).encode("ascii"))
    files, offset = {}, 0
    for rel, _ in entries:
        header_end = output.index(b"\n", offset)
        size = int(output[offset:header_end].split()[2])
        files[rel] = output[header_end + 1:header_end + 1 + size]
        offset = header_end + 1 + size + 1
    return files


def _current(root: Path, rel: str) -> tuple[str | None, str | None]:
    """(source, problem) for the working-tree copy of a base test file."""
    path = root / rel
    if path.is_symlink():
        return None, f"test file replaced by a symlink: {rel}"
    if not path.is_file():
        return None, None
    if path.stat().st_size > MAX_TEST_FILE_BYTES:
        return None, f"{rel} exceeds the {MAX_TEST_FILE_BYTES} byte limit"
    try:
        return path.read_bytes().decode("utf-8-sig"), None
    except UnicodeDecodeError:
        return None, f"{rel} is no longer UTF-8 text"


def compare(root: Path, base_files: dict[str, bytes]) -> tuple[list[str], dict]:
    findings: list[str] = []
    stats = {"files": len(base_files), "tests": 0, "asserts": 0}
    for rel in sorted(base_files):
        try:
            before = scan_source(base_files[rel].decode("utf-8-sig"))
        except (SyntaxError, UnicodeDecodeError, ValueError) as exc:
            raise ValueError(f"cannot parse {rel} at base: {exc}") from exc
        stats["tests"] += len(before)
        stats["asserts"] += sum(t["asserts"] for t in before.values())
        source, problem = _current(root, rel)
        if problem:
            findings.append(problem)
            continue
        if source is None:
            findings.append(f"test file deleted: {rel} ({len(before)} tests)")
            continue
        try:
            after = scan_source(source)
        except (SyntaxError, ValueError) as exc:
            findings.append(f"{rel} no longer parses: {exc}")
            continue
        for test_id, old in before.items():
            new = after.get(test_id)
            where = f"{rel}::{test_id}"
            if new is None:
                findings.append(f"test deleted: {where}")
                continue
            if new["skips"] > old["skips"]:
                findings.append(f"test newly skipped or xfail: {where}")
            if new["asserts"] < old["asserts"]:
                findings.append(f"assertions fell from {old['asserts']} to {new['asserts']}: {where}")
            if new["cases"] < old["cases"]:
                findings.append(f"parametrize cases fell from {old['cases']} to {new['cases']}: {where}")
    return findings, stats


def chk_tests_intact(c: dict, root: Path) -> tuple[str, str]:
    error = shape_error(c)
    if error:
        return ("error", error)
    root = root.resolve()
    try:
        (root / c["path"]).resolve().relative_to(root)
    except ValueError:
        return ("fail", f"path escapes project root: {c['path']}")
    base = c["base"]
    try:
        files = base_test_files(root, base, c["path"])
        if not files:
            return ("error", f"no Python test files under {c['path']} at base {base[:12]}; "
                             "the check would prove nothing")
        findings, stats = compare(root, files)
    except (ValueError, IndexError, OSError, subprocess.TimeoutExpired) as exc:
        return ("error", f"cannot compare tests with base {base[:12]}: {exc}")
    if stats["tests"] == 0:
        return ("error", f"no tests found under {c['path']} at base {base[:12]}; "
                         "the check would prove nothing")
    summary = (f"{stats['tests']} tests and {stats['asserts']} assertions in "
               f"{stats['files']} test file(s) at base {base[:12]}")
    if not findings:
        return ("pass", f"{summary}: none deleted, newly skipped or weakened")
    shown = "; ".join(findings[:MAX_FINDINGS_SHOWN])
    more = len(findings) - MAX_FINDINGS_SHOWN
    return ("fail", f"tests weakened since base {base[:12]}: {shown}"
                    + (f"; and {more} more" if more > 0 else ""))


def covering_requirement(requirements: list[dict], rel: str) -> dict | None:
    """Prefer the behavior check that covers this test file, else tests_intact."""
    command = None
    intact = None
    for row in requirements:
        check = row.get("check") or {}
        if not isinstance(row.get("requirement_id"), str):
            continue
        ctype = check.get("type")
        if ctype == "tests_intact":
            path = str(check.get("path") or "").replace("\\", "/").rstrip("/")
            if path and (rel == path or rel.startswith(path + "/")):
                intact = row
        elif ctype == "command":
            if row.get("scope") == "behavior":
                command = command or row
            elif command is None:
                command = row
    return command or intact


def _source_at_bases(root: Path, rel: str, bases: list[str]) -> str | None:
    seen: set[str] = set()
    for base in bases:
        if not base or base in seen:
            continue
        seen.add(base)
        try:
            data = _git(root, ["cat-file", "-p", f"{base}:{rel}"])
        except ValueError:
            continue
        try:
            return data.decode("utf-8-sig")
        except UnicodeDecodeError:
            continue
    return None


def _bases_for_session(root: Path, requirements: list[dict]) -> list[str]:
    bases = []
    for row in requirements:
        check = row.get("check") or {}
        if check.get("type") == "tests_intact" and isinstance(check.get("base"), str):
            bases.append(check["base"])
    try:
        head = _git(root, ["rev-parse", "HEAD"]).decode("ascii", "replace").strip()
    except ValueError:
        head = ""
    if head:
        bases.append(head)
    return bases


def covered_edit_results(root: Path, requirements: list[dict],
                         start: dict | None, snapshot_path: Path) -> list[dict]:
    """Refuse when a covered test was rewritten in the same session as the code."""
    if not requirements or not isinstance(start, dict):
        return []
    from .snapshot import capture_tree, exclusion_scope, read_snapshot
    meta = start.get("tree_snapshot")
    if not isinstance(meta, dict) or not isinstance(meta.get("sha256"), str):
        return []
    try:
        before = read_snapshot(snapshot_path, meta)
        scope = exclusion_scope(meta)
    except (OSError, ValueError):
        return []
    current = capture_tree(root, ignore=scope.get("ignore_patterns"))
    changed = [rel for rel, digest in before.items() if current.get(rel) != digest]
    changed += [rel for rel in current if rel not in before]
    test_changed = [rel for rel in changed if is_test_file(rel) and rel in before]
    code_changed = [rel for rel in changed if not is_test_file(rel)]
    if not test_changed or not code_changed:
        return []
    bases = _bases_for_session(root, requirements)
    rows = []
    seen: set[tuple[str, str]] = set()
    for rel in sorted(test_changed):
        covering = covering_requirement(requirements, rel)
        if covering is None:
            continue
        source, problem = _current(root, rel)
        if problem or source is None:
            continue
        old_src = _source_at_bases(root, rel, bases)
        try:
            rewritten = True if old_src is None else existing_tests_rewritten(old_src, source)
        except (SyntaxError, ValueError):
            rewritten = True
        if not rewritten:
            continue
        rid = covering["requirement_id"]
        key = (rel, rid)
        if key in seen:
            continue
        seen.add(key)
        rows.append({
            "claim": covering.get("claim") or rid,
            "session": covering.get("session") or "",
            "severity": "RED",
            "type": "covered_test",
            "status": "fail",
            "detail": (f"test file {rel} covered by check {rid!r} was edited "
                       f"in the same session as the code"),
            "synthetic": True,
        })
    return rows
