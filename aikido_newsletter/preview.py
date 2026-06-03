"""
HTML dry-run preview. Renders the same report + charts as a self-contained
page so the newsletter can be eyeballed before wiring up Slack (--dry-run).
"""

from __future__ import annotations

import base64
import datetime as dt
import os

from .analytics import TYPE_LABELS

SEV = {"critical": "#f85149", "high": "#fb8500", "medium": "#f5c518", "low": "#58a6ff"}


def _b64(path: str) -> str:
    with open(path, "rb") as f:
        return "data:image/png;base64," + base64.b64encode(f.read()).decode()


def _d(ts: int) -> str:
    return dt.datetime.utcfromtimestamp(ts).strftime("%b %d, %Y")


def render(report: dict, charts: dict[str, str], out_dir: str,
           workspace: str = "") -> str:
    ov = report["overall"]
    overdue = sum(p["overdue_open"] for p in report["products"].values())
    net = ov["opened_this_period"] - ov["closed_this_period"]

    def card(label, value, sub=""):
        return (f'<div class="kpi"><div class="kpi-l">{label}</div>'
                f'<div class="kpi-v">{value}</div>'
                f'<div class="kpi-s">{sub}</div></div>')

    kpis = "".join([
        card("Open issues", ov["open"]),
        card("Critical / High",
             f'<span style="color:{SEV["critical"]}">{ov["severity_open"]["critical"]}</span> / '
             f'<span style="color:{SEV["high"]}">{ov["severity_open"]["high"]}</span>'),
        card("Past SLA", f'<span style="color:{SEV["critical"]}">{overdue}</span>', "overdue"),
        card("Median MTTR",
             ov["mttr_all"]["median"] if ov["mttr_all"]["median"] is not None else "—", "days"),
        card("Opened / Closed", f'{ov["opened_this_period"]} / {ov["closed_this_period"]}',
             "this period"),
        card("Net backlog Δ", f'{"+" if net > 0 else ""}{net}',
             "growing" if net > 0 else "shrinking"),
    ])

    insights = "".join(
        f"<li>{s.replace('*', '')}</li>" for s in report["insights"])

    rows = ""
    for b in report["leaderboard"]:
        mttr = f"{b['mttr_median']:g}d" if b["mttr_median"] is not None else "—"
        arrow = "▲" if b["crit_delta"] > 0 else "▼" if b["crit_delta"] < 0 else "–"
        acol = SEV["critical"] if b["crit_delta"] > 0 else "#3fb950" if b["crit_delta"] < 0 else "#8b949e"
        rows += (f"<tr><td>{b['name']}</td><td class='n'>{b['risk_score']}</td>"
                 f"<td class='n' style='color:{SEV['critical']}'>{b['open_critical']}</td>"
                 f"<td class='n' style='color:{SEV['high']}'>{b['open_high']}</td>"
                 f"<td class='n'>{b['overdue']}</td><td class='n'>{mttr}</td>"
                 f"<td class='n' style='color:{acol}'>{arrow}</td></tr>")

    crit = ""
    for c in report["top_critical_issues"][:8]:
        ident = c["cve"] or c["package"] or TYPE_LABELS.get(c["type"], c["type"])
        od = ' <span class="badge">overdue</span>' if c["overdue"] else ""
        crit += (f'<div class="fb"><span class="dot" style="background:{SEV.get(c["severity"],"#888")}"></span>'
                 f'<div><b>{c["rule"]}</b> <span class="sev">{c["severity"]} · {c["score"]}</span>{od}'
                 f'<div class="meta">{c["product"]} · {c["repo"] or "—"} · {ident} · {c["age_days"]}d old</div>'
                 f'</div></div>')

    chart_order = ["risk_leaderboard", "severity_by_product", "opened_vs_closed_trend",
                   "mttr_by_severity", "issue_type_mix", "open_aging", "top_cwes"]
    imgs = "".join(
        f'<div class="chart"><img src="{_b64(charts[c])}" alt="{c}"></div>'
        for c in chart_order if c in charts)

    cwes = "".join(f'<span class="chip">{c} <em>×{n}</em></span>'
                   for c, n in report["top_cwes"][:8])

    html = f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Product Security Newsletter</title>
<style>
 :root{{--bg:#0d1117;--panel:#161b22;--line:#222b36;--text:#e6edf3;--muted:#8b949e;--accent:#2f81f7;}}
 *{{box-sizing:border-box}}
 body{{margin:0;background:var(--bg);color:var(--text);
   font-family:'IBM Plex Sans',-apple-system,Segoe UI,Roboto,sans-serif;line-height:1.5;}}
 .wrap{{max-width:860px;margin:0 auto;padding:32px 20px 64px;}}
 .top{{border-left:3px solid var(--accent);padding-left:16px;margin-bottom:28px;}}
 h1{{font-size:26px;margin:0 0 4px;letter-spacing:-.4px;}}
 .sub{{color:var(--muted);font-size:13px;font-family:'IBM Plex Mono',ui-monospace,monospace;}}
 h2{{font-size:13px;text-transform:uppercase;letter-spacing:1.4px;color:var(--muted);
   margin:34px 0 14px;border-bottom:1px solid var(--line);padding-bottom:8px;}}
 .kpis{{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;}}
 .kpi{{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:16px;}}
 .kpi-l{{font-size:11px;text-transform:uppercase;letter-spacing:.8px;color:var(--muted);}}
 .kpi-v{{font-size:28px;font-weight:700;margin:6px 0 2px;
   font-family:'IBM Plex Mono',ui-monospace,monospace;}}
 .kpi-s{{font-size:11px;color:var(--muted);}}
 ul.ins{{background:var(--panel);border:1px solid var(--line);border-radius:10px;
   padding:16px 16px 16px 34px;margin:0;}}
 ul.ins li{{margin:7px 0;}}
 table{{width:100%;border-collapse:collapse;background:var(--panel);
   border:1px solid var(--line);border-radius:10px;overflow:hidden;
   font-family:'IBM Plex Mono',ui-monospace,monospace;font-size:13px;}}
 th,td{{padding:10px 12px;text-align:left;border-bottom:1px solid var(--line);}}
 th{{font-size:11px;text-transform:uppercase;letter-spacing:.6px;color:var(--muted);}}
 td.n,th.n{{text-align:right;}}
 tr:last-child td{{border-bottom:none}}
 .fb{{display:flex;gap:12px;align-items:flex-start;background:var(--panel);
   border:1px solid var(--line);border-radius:10px;padding:12px 14px;margin-bottom:8px;}}
 .dot{{width:10px;height:10px;border-radius:50%;margin-top:6px;flex:0 0 auto;}}
 .sev{{font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.6px;}}
 .meta{{font-size:12px;color:var(--muted);margin-top:3px;
   font-family:'IBM Plex Mono',ui-monospace,monospace;}}
 .badge{{background:rgba(248,81,73,.15);color:#f85149;font-size:10px;padding:2px 6px;
   border-radius:4px;text-transform:uppercase;letter-spacing:.5px;}}
 .chart{{background:var(--panel);border:1px solid var(--line);border-radius:10px;
   padding:8px;margin-bottom:16px;}}
 .chart img{{width:100%;display:block;border-radius:6px;}}
 .chips{{display:flex;flex-wrap:wrap;gap:8px;}}
 .chip{{background:var(--panel);border:1px solid var(--line);border-radius:6px;
   padding:5px 10px;font-size:12px;font-family:'IBM Plex Mono',ui-monospace,monospace;}}
 .chip em{{color:var(--muted);font-style:normal;}}
 .foot{{color:var(--muted);font-size:12px;margin-top:40px;border-top:1px solid var(--line);
   padding-top:16px;}}
 @media(max-width:560px){{.kpis{{grid-template-columns:repeat(2,1fr)}}}}
</style></head><body><div class="wrap">
 <div class="top"><h1>🛡️ Product Security Newsletter</h1>
   <div class="sub">{_d(report['window_start'])} – {_d(report['generated_at'])}
     · {len(report['products'])} products{(' · ' + workspace) if workspace else ''}
     · data via Aikido</div></div>
 <h2>Executive summary</h2><div class="kpis">{kpis}</div>
 <h2>📌 Insights</h2><ul class="ins">{insights}</ul>
 <h2>🏆 Product risk leaderboard</h2>
 <table><tr><th>Product</th><th class="n">Risk</th><th class="n">Crit</th>
   <th class="n">High</th><th class="n">Overdue</th><th class="n">MTTR</th>
   <th class="n">Δcrit</th></tr>{rows}</table>
 <h2>🔥 Most critical open findings</h2>{crit}
 <h2>Top weakness classes (CWE)</h2><div class="chips">{cwes}</div>
 <h2>📊 Charts</h2>{imgs}
 <div class="foot">Generated by <b>aikido-product-newsletter</b> ·
   dry-run preview. In production this is posted to Slack as a Block Kit message
   with the charts uploaded in-thread.</div>
</div></body></html>"""

    path = os.path.join(out_dir, "newsletter_preview.html")
    with open(path, "w") as f:
        f.write(html)
    return path
