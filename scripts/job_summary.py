#!/usr/bin/env python3
"""Emit a markdown KPI summary to stdout (for $GITHUB_STEP_SUMMARY)."""
import json
import sys

try:
    r = json.load(open(sys.argv[1] if len(sys.argv) > 1 else "out/report.json"))
except FileNotFoundError:
    print("_No report produced._")
    sys.exit(0)

ov = r["overall"]
overdue = sum(p["overdue_open"] for p in r["products"].values())
net = ov["opened_this_period"] - ov["closed_this_period"]
mttr = ov["mttr_all"]["median"]

print("## 🛡️ Product Security Newsletter\n")
print(f"**{len(r['products'])} products · window {r['window_days']}d**\n")
print(f"| Open | Critical | High | Past SLA | Median MTTR | Net backlog Δ |")
print(f"|---|---|---|---|---|---|")
print(f"| {ov['open']} | {ov['severity_open']['critical']} | "
      f"{ov['severity_open']['high']} | {overdue} | "
      f"{mttr if mttr is not None else '—'} d | {'+' if net > 0 else ''}{net} |\n")

print("### Risk leaderboard\n")
print("| Product | Risk | Crit | High | Overdue | MTTR |")
print("|---|---:|---:|---:|---:|---:|")
for b in r["leaderboard"]:
    m = f"{b['mttr_median']:g}d" if b["mttr_median"] is not None else "—"
    print(f"| {b['name']} | {b['risk_score']} | {b['open_critical']} | "
          f"{b['open_high']} | {b['overdue']} | {m} |")

if r.get("insights"):
    print("\n### Insights\n")
    for s in r["insights"]:
        print(f"- {s.replace('*', '')}")
