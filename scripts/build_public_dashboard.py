#!/usr/bin/env python3
"""Build the public (sanitized) dashboard page from replay data.

Separate from `showwork.dashboard`, which renders the local operator view. This
one is for publication: it leads with the calibration finding rather than the
intervention list, because the honest false-positive number is what makes the
0.5% believable to a stranger.

Emits a body fragment (style + markup, no doctype/head/body) suitable for the
artifact host.
"""

from __future__ import annotations

import argparse
import html
import json
from pathlib import Path

CALIBRATION = [
    ("repeat", "3, window 12", 14, 0.5, "plausible true positives", "ok"),
    ("no_progress", "6", 2281, 82.7, "noise", "bad"),
    ("no_progress", "20", 248, 9.0, "still mostly noise", "warn"),
    ("no_progress", "40", 33, 1.2, "adds nothing repeat missed", "warn"),
    ("alternation", "3", 0, 0.0, "never fired on real data", "off"),
]

CSS = """
:root{
  --ground:#FBFAF8; --panel:#FFFFFF; --ink:#14181D; --ink-dim:#5A6472;
  --rule:#E2E0DB; --rule-strong:#C9C6BF;
  --signal:#B06E14; --signal-soft:rgba(176,110,20,.10);
  --ok:#2F7D4F; --bad:#C0342B; --warn:#B06E14;
  --shadow:0 1px 2px rgba(20,24,29,.05), 0 8px 24px -12px rgba(20,24,29,.12);
}
@media (prefers-color-scheme: dark){
  :root{
    --ground:#0B0F14; --panel:#131920; --ink:#E7EBF0; --ink-dim:#8A94A3;
    --rule:#212932; --rule-strong:#2E3844;
    --signal:#E8A33D; --signal-soft:rgba(232,163,61,.12);
    --ok:#4BA36A; --bad:#E56159; --warn:#E8A33D;
    --shadow:0 1px 2px rgba(0,0,0,.4), 0 8px 24px -12px rgba(0,0,0,.6);
  }
}
:root[data-theme="light"]{
  --ground:#FBFAF8; --panel:#FFFFFF; --ink:#14181D; --ink-dim:#5A6472;
  --rule:#E2E0DB; --rule-strong:#C9C6BF;
  --signal:#B06E14; --signal-soft:rgba(176,110,20,.10);
  --ok:#2F7D4F; --bad:#C0342B; --warn:#B06E14;
  --shadow:0 1px 2px rgba(20,24,29,.05), 0 8px 24px -12px rgba(20,24,29,.12);
}
:root[data-theme="dark"]{
  --ground:#0B0F14; --panel:#131920; --ink:#E7EBF0; --ink-dim:#8A94A3;
  --rule:#212932; --rule-strong:#2E3844;
  --signal:#E8A33D; --signal-soft:rgba(232,163,61,.12);
  --ok:#4BA36A; --bad:#E56159; --warn:#E8A33D;
  --shadow:0 1px 2px rgba(0,0,0,.4), 0 8px 24px -12px rgba(0,0,0,.6);
}

*{box-sizing:border-box}
body{
  margin:0; background:var(--ground); color:var(--ink);
  font:15px/1.6 ui-sans-serif,-apple-system,"Segoe UI",Roboto,sans-serif;
  -webkit-font-smoothing:antialiased;
}
.mono{font-family:ui-monospace,SFMono-Regular,"Cascadia Mono",Menlo,Consolas,monospace}
.wrap{max-width:960px;margin:0 auto;padding:3rem 1.25rem 5rem}

.eyebrow{
  font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
  font-size:.7rem;letter-spacing:.14em;text-transform:uppercase;
  color:var(--signal);margin:0 0 .9rem;
}
h1{
  font-size:clamp(1.9rem,4.4vw,2.9rem);line-height:1.08;letter-spacing:-.022em;
  font-weight:660;margin:0 0 .85rem;text-wrap:balance;max-width:20ch;
}
.lede{font-size:1.06rem;color:var(--ink-dim);margin:0;max-width:62ch}
.lede strong{color:var(--ink);font-weight:600}

.rule{height:1px;background:var(--rule);border:0;margin:2.75rem 0}

h2{
  font-size:.95rem;font-weight:640;letter-spacing:-.005em;
  margin:0 0 .35rem;
}
.sub{color:var(--ink-dim);font-size:.87rem;margin:0 0 1.1rem;max-width:64ch}

.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:1px;
  background:var(--rule);border:1px solid var(--rule);border-radius:10px;overflow:hidden;
  box-shadow:var(--shadow)}
.stat{background:var(--panel);padding:1.05rem 1.1rem}
.stat .n{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
  font-size:1.55rem;font-weight:600;letter-spacing:-.02em;font-variant-numeric:tabular-nums;
  display:block;line-height:1.1}
.stat .l{font-size:.7rem;letter-spacing:.1em;text-transform:uppercase;color:var(--ink-dim);
  margin-top:.4rem;display:block}
.stat.flag .n{color:var(--signal)}

.scroll{overflow-x:auto;border:1px solid var(--rule);border-radius:10px;background:var(--panel);
  box-shadow:var(--shadow)}
table{border-collapse:collapse;width:100%;min-width:600px;font-size:.845rem}
th,td{text-align:left;padding:.6rem .8rem;border-bottom:1px solid var(--rule)}
tbody tr:last-child td{border-bottom:0}
th{font-size:.68rem;letter-spacing:.1em;text-transform:uppercase;color:var(--ink-dim);
  font-weight:600;background:var(--ground)}
td.n,th.n{text-align:right;font-variant-numeric:tabular-nums;
  font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}

/* Severity as form, not just number: a stripe you can scan without reading. */
tr.sev-bad td:first-child{box-shadow:inset 3px 0 0 var(--bad)}
tr.sev-warn td:first-child{box-shadow:inset 3px 0 0 var(--warn)}
tr.sev-ok td:first-child{box-shadow:inset 3px 0 0 var(--ok)}
tr.sev-off td:first-child{box-shadow:inset 3px 0 0 var(--rule-strong)}

.pill{display:inline-block;padding:.1rem .45rem;border-radius:4px;font-size:.72rem;
  font-weight:600;font-family:ui-monospace,Menlo,monospace}
.pill.bad{background:color-mix(in srgb,var(--bad) 16%,transparent);color:var(--bad)}
.pill.ok{background:color-mix(in srgb,var(--ok) 16%,transparent);color:var(--ok)}

.callout{border-left:3px solid var(--signal);background:var(--signal-soft);
  padding:1rem 1.15rem;border-radius:0 8px 8px 0;margin:1.4rem 0}
.callout p{margin:0;font-size:.9rem;color:var(--ink)}
.callout p + p{margin-top:.6rem;color:var(--ink-dim)}

code{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
  font-size:.86em;background:var(--ground);border:1px solid var(--rule);
  padding:.05rem .32rem;border-radius:4px}

.install{background:var(--panel);border:1px solid var(--rule);border-radius:10px;
  padding:1rem 1.15rem;box-shadow:var(--shadow)}
.install code{background:transparent;border:0;padding:0;font-size:.95rem;color:var(--signal)}

footer{margin-top:3.5rem;padding-top:1.25rem;border-top:1px solid var(--rule);
  color:var(--ink-dim);font-size:.8rem}
footer a{color:var(--signal)}
a{color:var(--signal)}
a:focus-visible,summary:focus-visible{outline:2px solid var(--signal);outline-offset:2px;border-radius:3px}
@media (prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}
"""


def esc(v: object) -> str:
    return html.escape(str(v))


def build(data: dict) -> str:
    results = data.get("results", [])
    stuck = [r for r in results if r.get("stuck")]
    wasted = sum(r.get("calls_after_trip", 0) for r in stuck)
    scanned = data.get("scanned", 0)
    with_calls = data.get("with_calls", len(results))
    rate = (100.0 * len(stuck) / with_calls) if with_calls else 0.0

    stats = "".join(
        f'<div class="stat{cls}"><span class="n">{esc(n)}</span>'
        f'<span class="l">{esc(l)}</span></div>'
        for n, l, cls in [
            (f"{scanned:,}", "sessions replayed", ""),
            (f"{with_calls:,}", "with tool calls", ""),
            (str(len(stuck)), "flagged stuck", ""),
            (f"{rate:.1f}%", "flag rate", ""),
            (f"{wasted:,}", "calls after trip", " flag"),
        ]
    )

    cal_rows = "".join(
        f'<tr class="sev-{sev}"><td class="mono">{esc(sig)}</td>'
        f'<td class="mono">{esc(thr)}</td>'
        f'<td class="n">{cnt:,}</td>'
        f'<td class="n">{pct:.1f}%</td>'
        f"<td>{esc(read)}</td></tr>"
        for sig, thr, cnt, pct, read, sev in CALIBRATION
    )

    int_rows = "".join(
        f'<tr class="sev-bad"><td><span class="pill bad">{esc(r.get("reason",""))}</span></td>'
        f'<td class="mono">{esc(r.get("session",""))}</td>'
        f'<td class="mono">{esc(r.get("project",""))}</td>'
        f'<td class="mono">{esc(r.get("detail","").split(" called")[0])}</td>'
        f'<td class="n">{esc(r.get("fired_at_call") or "-")}</td>'
        f'<td class="n">{esc(r.get("total_calls",0)):}</td>'
        f'<td class="n">+{esc(r.get("calls_after_trip",0))}</td></tr>'
        for r in sorted(stuck, key=lambda r: -r.get("calls_after_trip", 0))
    )

    worst = max((r.get("calls_after_trip", 0) for r in stuck), default=0)

    return f"""<style>{CSS}</style>
<div class="wrap">

  <p class="eyebrow">showwork &middot; calibration report</p>
  <h1>One agent ran 813 tool calls past the point it stopped making progress.</h1>
  <p class="lede">A stuck detector is only worth having if it fires on real loops and stays quiet
  on real work. So it was calibrated against <strong>{scanned:,} recorded Claude&nbsp;Code sessions</strong>
  rather than fixtures &mdash; which is how the first version was caught flagging
  <strong>four out of five healthy runs</strong>.</p>

  <hr class="rule">

  <h2>What the replay found</h2>
  <p class="sub">Every session's tool-call stream replayed through the detector, start to finish.</p>
  <div class="stats">{stats}</div>

  <hr class="rule">

  <h2>Calibration</h2>
  <p class="sub">The number that mattered was not the hit rate. It was the false-positive rate,
  and it only appeared against real data.</p>
  <div class="scroll"><table>
    <thead><tr>
      <th>Signature</th><th>Threshold</th><th class="n">Flagged</th>
      <th class="n">Rate</th><th>Read</th>
    </tr></thead>
    <tbody>{cal_rows}</tbody>
  </table></div>

  <div class="callout">
    <p><strong>no_progress shipped at 6 and would have killed 82.7% of real sessions.</strong>
    Reading a dozen files before an edit is ordinary work, not a stall. Raising the threshold
    did not rescue it: by the point it stopped flagging healthy runs, it had stopped catching
    anything <code>repeat</code> had not already found. It is off by default.</p>
    <p>Every synthetic test passed while that default was wrong. Fixtures prove the code does
    what it was written to do; only real transcripts say whether it was written to do the right thing.</p>
  </div>

  <hr class="rule">

  <h2>Interventions</h2>
  <p class="sub">Where the detector would have halted a run, and how far past that point the
  agent actually kept going. Session ids are hashed and repo names generalised.</p>
  <div class="scroll"><table>
    <thead><tr>
      <th>Signal</th><th>Session</th><th>Repo</th><th>Repeated call</th>
      <th class="n">Fired</th><th class="n">Length</th><th class="n">Ran on</th>
    </tr></thead>
    <tbody>{int_rows}</tbody>
  </table></div>

  <div class="callout">
    <p>Three shapes, all the same underneath &mdash; an identical call with unchanged arguments,
    three times, with nothing mutating in between: browser automation re-clicking dead
    coordinates, market-data polling waiting for a state change that was not coming, and the
    same file read three times in five calls.</p>
    <p>A mutation clears the detector's window, so <code>edit &rarr; test &rarr; edit &rarr; test</code>
    is never killed. Repeating a command after a real change is convergent work. Repeating it
    with nothing changed in between is a loop. That distinction is what a dollar-metering
    gateway structurally cannot see &mdash; it observes spend, not whether the world changed.</p>
  </div>

  <hr class="rule">

  <h2>Try it</h2>
  <p class="sub">Stdlib only, no dependencies. One entry in <code>.claude/settings.json</code>
  turns on live enforcement.</p>
  <div class="install"><code>pip install showwork</code></div>

  <footer>
    Worst observed overrun: <strong>{worst:,}</strong> tool calls after the trip point.
    Sanitized replay &mdash; retroactive, not live kills; the detector did not exist when these ran.
    Owned-fleet dogfooding data, not market evidence. No spend column: agent hooks carry no cost
    data, so any dollar figure would be invented.<br><br>
    <a href="https://github.com/bmdhodl/showwork">github.com/bmdhodl/showwork</a> &middot;
    <a href="https://pypi.org/project/showwork/">pypi.org/project/showwork</a>
  </footer>

</div>"""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--replay", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    data = json.loads(args.replay.read_text(encoding="utf-8"))
    if not data.get("sanitized"):
        print("refusing: input is not marked sanitized; run sanitize_replay.py first")
        return 2

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(build(data), encoding="utf-8")
    print(f"wrote {args.out} ({args.out.stat().st_size:,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
