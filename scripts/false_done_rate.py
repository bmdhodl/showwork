"""False Done Rate (FDR): how often agents claim work that is not backed by
reality - measured ONLY from durable ledger evidence.

    python scripts/false_done_rate.py [--json] [--label NAME=PATH ...] [ROOT ...]

Definition (pre-registered in docs/false-done-rate.md - read it before
quoting numbers). Implementation lives in ``showwork.report.analyze_fdr``;
this script remains the documented reproduce path.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from showwork.report import analyze_fdr  # noqa: E402


def analyze_root(root: Path) -> dict:
    """Backward-compatible alias used by tests and docs."""
    return analyze_fdr(root)


def _pct(x: float | None) -> str:
    return "n/a" if x is None else f"{100 * x:.1f}%"


def render(reports: list[tuple[str, dict]]) -> str:
    lines = ["# False Done Rate", "",
             "Durable-evidence lower bound; methodology: docs/false-done-rate.md", "",
             "| corpus | eligible sessions | false-done sessions | FDR (session) | FDR (event) | checked claims |",
             "|---|---:|---:|---:|---:|---:|"]
    te = tf = 0
    ee = ef = 0
    for label, r in reports:
        lines.append(f"| {label} | {r['eligible_sessions']} | {r['false_done_sessions']} "
                     f"| {_pct(r['fdr_session'])} | {_pct(r['fdr_event'])} "
                     f"| {r['checked_claims']} |")
        te += r["eligible_sessions"]
        tf += r["false_done_sessions"]
        ee += r["false_done_events"]
        ef += r["clean_closes"]
    lines.append(f"| **all** | **{te}** | **{tf}** "
                 f"| **{_pct(tf / te if te else None)}** "
                 f"| **{_pct(ee / (ee + ef) if (ee + ef) else None)}** |  |")
    lines.append("")
    for label, r in reports:
        if r["false_done_session_ids"]:
            lines.append(f"False-done sessions in {label}: "
                         + ", ".join(f"`{s}`" for s in r["false_done_session_ids"]))
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="False Done Rate from showwork ledgers")
    ap.add_argument("roots", nargs="*", default=["."],
                    help="project roots containing .showwork/")
    ap.add_argument("--label", action="append", default=[],
                    help="NAME=PATH labeled corpus (repeatable)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    corpora: list[tuple[str, Path]] = []
    for item in args.label:
        name, _, path = item.partition("=")
        corpora.append((name, Path(path)))
    for r in (args.roots if not corpora or args.roots != ["."] else []):
        corpora.append((Path(r).name or str(r), Path(r)))
    if not corpora:
        corpora = [(".", Path("."))]

    reports = [(label, analyze_root(root)) for label, root in corpora]
    if args.json:
        print(json.dumps({label: r for label, r in reports}, indent=2))
    else:
        print(render(reports))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
