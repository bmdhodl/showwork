#!/usr/bin/env python3
"""Replay recorded Claude Code sessions through the stuck detector.

Synthetic fixtures prove the detector does what it was written to do. They
cannot tell you whether the thresholds are right for real agents. This replays
actual session transcripts so both questions get answered against real data:

  1. How often would this have fired on real runs?  (recall)
  2. How often would it have fired on runs that finished fine?  (false positives)

Transcripts live at ~/.claude/projects/<slug>/<session>.jsonl. Each `assistant`
record carries message.content[] blocks; `tool_use` blocks are the stream we
care about.

Usage:
    python scripts/replay_transcripts.py [--root DIR] [--limit N] [--json OUT]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from showwork.control import call_from_payload  # noqa: E402
from showwork.guards import StuckDetector  # noqa: E402


def default_root() -> Path:
    return Path(os.path.expanduser("~")) / ".claude" / "projects"


def tool_calls(path: Path) -> list[dict]:
    """Extract the ordered tool_use stream from one transcript."""
    calls: list[dict] = []
    try:
        with path.open(encoding="utf-8", errors="replace") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except (ValueError, TypeError):
                    continue
                if record.get("type") != "assistant":
                    continue
                content = record.get("message", {}).get("content")
                if not isinstance(content, list):
                    continue
                for block in content:
                    if not isinstance(block, dict):
                        continue
                    if block.get("type") != "tool_use":
                        continue
                    calls.append(
                        {
                            "tool_name": block.get("name") or "",
                            "tool_input": block.get("input"),
                        }
                    )
    except OSError:
        return []
    return calls


def replay_one(path: Path, **thresholds) -> dict | None:
    calls = tool_calls(path)
    if not calls:
        return None
    detector = StuckDetector(**thresholds)
    verdict = None
    fired_at = None
    for index, payload in enumerate(calls, start=1):
        verdict = detector.observe(call_from_payload(payload))
        if verdict.stuck:
            fired_at = index
            break
    return {
        "session": path.stem,
        "project": path.parent.name,
        "total_calls": len(calls),
        "stuck": bool(verdict and verdict.stuck),
        "reason": verdict.reason if verdict and verdict.stuck else "",
        "detail": verdict.detail if verdict and verdict.stuck else "",
        "fired_at_call": fired_at,
        "calls_after_trip": (len(calls) - fired_at) if fired_at else 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=default_root())
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--json", type=Path)
    parser.add_argument("--repeat-threshold", type=int, default=3)
    parser.add_argument("--window", type=int, default=12)
    parser.add_argument("--no-progress-threshold", type=int, default=6)
    parser.add_argument("--alternation-threshold", type=int, default=3)
    args = parser.parse_args()

    if not args.root.exists():
        print(f"no transcript root at {args.root}", file=sys.stderr)
        return 1

    thresholds = dict(
        repeat_threshold=args.repeat_threshold,
        window=args.window,
        no_progress_threshold=args.no_progress_threshold,
        alternation_threshold=args.alternation_threshold,
    )

    files = sorted(args.root.rglob("*.jsonl"))
    if args.limit:
        files = files[: args.limit]

    results = []
    skipped = 0
    for path in files:
        outcome = replay_one(path, **thresholds)
        if outcome is None:
            skipped += 1
            continue
        results.append(outcome)

    stuck = [r for r in results if r["stuck"]]
    reasons = Counter(r["reason"] for r in stuck)
    with_calls = len(results)

    print(f"transcripts scanned      : {len(files)}")
    print(f"  with tool calls        : {with_calls}")
    print(f"  empty / unparseable    : {skipped}")
    print(f"thresholds               : {thresholds}")
    print()
    print(f"sessions flagged stuck   : {len(stuck)}"
          + (f"  ({100.0 * len(stuck) / with_calls:.1f}%)" if with_calls else ""))
    for reason, count in reasons.most_common():
        print(f"  {reason:<14} : {count}")

    if stuck:
        wasted = sum(r["calls_after_trip"] for r in stuck)
        print()
        print(f"tool calls that ran AFTER the detector would have fired: {wasted}")
        print(f"  median session length (flagged): "
              f"{sorted(r['total_calls'] for r in stuck)[len(stuck) // 2]}")
        print()
        print("top flagged sessions:")
        for row in sorted(stuck, key=lambda r: -r["calls_after_trip"])[:10]:
            print(f"  [{row['reason']:<12}] {row['session'][:8]} "
                  f"call {row['fired_at_call']}/{row['total_calls']} "
                  f"(+{row['calls_after_trip']} after) - {row['detail'][:70]}")

    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(
            json.dumps(
                {"thresholds": thresholds, "scanned": len(files),
                 "with_calls": with_calls, "results": results},
                indent=2,
            ),
            encoding="utf-8",
        )
        print(f"\nwrote {args.json}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
