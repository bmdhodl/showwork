"""Render a self-contained dashboard: runs, status, interventions, proof of work.

A static artifact, not a service. Same five things a hosted dashboard shows,
without the multi-tenant SaaS underneath: no signup, no database, no billing.
Open the file, or serve it on loopback with `showwork dashboard --serve`.

"Spend" is deliberately absent. Agent hooks carry no cost data, so a spend
column would be an invented number wearing a dashboard's clothes. Tool calls
are counted instead, because they are real.
"""

from __future__ import annotations

import html
import json

__all__ = ["render", "CSS"]


CSS = """
:root{--bg:#0d1117;--fg:#e6edf3;--dim:#8b949e;--line:#30363d;--card:#161b22;
--red:#f85149;--green:#3fb950;--amber:#d29922;--accent:#58a6ff}
@media(prefers-color-scheme:light){:root{--bg:#fff;--fg:#1f2328;--dim:#59636e;
--line:#d1d9e0;--card:#f6f8fa;--red:#cf222e;--green:#1a7f37;--amber:#9a6700;--accent:#0969da}}
*{box-sizing:border-box}
body{margin:0;padding:2rem 1.25rem;background:var(--bg);color:var(--fg);
font:15px/1.55 ui-sans-serif,-apple-system,Segoe UI,sans-serif}
.wrap{max-width:1080px;margin:0 auto}
h1{font-size:1.5rem;margin:0 0 .25rem}
.sub{color:var(--dim);margin:0 0 2rem;font-size:.9rem}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:.75rem;margin-bottom:2rem}
.stat{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:1rem}
.stat .n{font-size:1.7rem;font-weight:600;font-variant-numeric:tabular-nums}
.stat .l{color:var(--dim);font-size:.78rem;text-transform:uppercase;letter-spacing:.04em}
h2{font-size:1.05rem;margin:2rem 0 .75rem;padding-bottom:.4rem;border-bottom:1px solid var(--line)}
.scroll{overflow-x:auto;-webkit-overflow-scrolling:touch}
table{border-collapse:collapse;width:100%;font-size:.85rem;min-width:640px}
th,td{text-align:left;padding:.5rem .6rem;border-bottom:1px solid var(--line);vertical-align:top}
th{color:var(--dim);font-weight:500;font-size:.75rem;text-transform:uppercase;letter-spacing:.04em}
td.n{text-align:right;font-variant-numeric:tabular-nums}
code{background:var(--card);padding:.1rem .35rem;border-radius:4px;font-size:.85em}
.tag{display:inline-block;padding:.1rem .45rem;border-radius:4px;font-size:.72rem;font-weight:600}
.tag.stuck{background:color-mix(in srgb,var(--red) 18%,transparent);color:var(--red)}
.tag.ok{background:color-mix(in srgb,var(--green) 18%,transparent);color:var(--green)}
.note{background:var(--card);border-left:3px solid var(--amber);padding:.8rem 1rem;
border-radius:0 6px 6px 0;font-size:.85rem;color:var(--dim);margin:1rem 0}
footer{margin-top:3rem;padding-top:1rem;border-top:1px solid var(--line);
color:var(--dim);font-size:.78rem}
"""


def esc(value: object) -> str:
    return html.escape(str(value))


def render(data: dict) -> str:
    results = data.get("results", [])
    stuck = [r for r in results if r.get("stuck")]
    total_calls = sum(r.get("total_calls", 0) for r in results)
    wasted = sum(r.get("calls_after_trip", 0) for r in stuck)
    rate = (100.0 * len(stuck) / len(results)) if results else 0.0

    stats = [
        (f"{len(results):,}", "runs observed"),
        (f"{total_calls:,}", "tool calls"),
        (str(len(stuck)), "interventions"),
        (f"{rate:.1f}%", "stuck rate"),
        (f"{wasted:,}", "calls after trip"),
    ]
    stat_html = "".join(
        f'<div class="stat"><div class="n">{esc(n)}</div><div class="l">{esc(l)}</div></div>'
        for n, l in stats
    )

    rows = []
    for row in sorted(stuck, key=lambda r: -r.get("calls_after_trip", 0)):
        call = esc(row.get("detail", "").split(" called")[0])
        rows.append(
            "<tr>"
            f'<td><span class="tag stuck">{esc(row.get("reason","stuck"))}</span></td>'
            f"<td><code>{esc(row.get('session','')[:8])}</code></td>"
            f"<td>{esc(row.get('project','')[:34])}</td>"
            f"<td><code>{call}</code></td>"
            f'<td class="n">{esc(row.get("fired_at_call") or "-")}</td>'
            f'<td class="n">{esc(row.get("total_calls",0))}</td>'
            f'<td class="n">+{esc(row.get("calls_after_trip",0))}</td>'
            "</tr>"
        )
    table = "".join(rows) or '<tr><td colspan="7">No interventions.</td></tr>'

    thresholds = esc(json.dumps(data.get("thresholds", {})))

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>showwork - agent control</title><style>{CSS}</style></head>
<body><div class="wrap">
<h1>showwork &mdash; agent control</h1>
<p class="sub">Runs, status, interventions, and proof of work. Static file, no service behind it.</p>

<div class="grid">{stat_html}</div>

<h2>Interventions</h2>
<p class="sub">Where the stuck detector would have halted a run, and how far past that point it actually ran.</p>
<div class="scroll"><table>
<thead><tr><th>Signal</th><th>Session</th><th>Project</th><th>Repeated call</th>
<th class="n">Fired at</th><th class="n">Length</th><th class="n">Ran on</th></tr></thead>
<tbody>{table}</tbody></table></div>

<div class="note">
<strong>Read this correctly.</strong> Retroactive replay over recorded sessions, not live kills.
The detector did not exist when these ran, so the claim is &ldquo;this would have fired here&rdquo;,
not &ldquo;this saved money&rdquo;. Owned-fleet dogfooding data, not market evidence.
No spend column: agent hooks carry no cost data, so any dollar figure would be invented.
</div>

<footer>
Thresholds: <code>{thresholds}</code><br>
Generated by <code>scripts/render_dashboard.py</code> from
<code>scripts/replay_transcripts.py</code> output. Self-contained; works offline.
</footer>
</div></body></html>"""


