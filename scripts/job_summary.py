#!/usr/bin/env python3
"""Emit a markdown KPI summary to stdout (for $GITHUB_STEP_SUMMARY).

Usage: job_summary.py <path>
  <path> may be a report.json FILE, or a DIRECTORY searched recursively for
  report.json files (one per workspace in --per-workspace runs).

This output is cosmetic, so the script never fails the job: any problem prints
a note and exits 0.
"""
import glob
import json
import os
import sys


def summarize(path: str, title_suffix: str = "") -> None:
    r = json.load(open(path))
    ov = r["overall"]
    overdue = sum(p["overdue_open"] for p in r.get("products", {}).values())
    net = ov["opened_this_period"] - ov["closed_this_period"]
    mttr = ov["mttr_all"]["median"]

    print(f"## 🛡️ Product Security Newsletter{title_suffix}\n")
    print(f"**{len(r.get('products', {}))} products · window {r['window_days']}d**\n")
    print("| Open | Critical | High | Past SLA | Median MTTR | Net backlog Δ |")
    print("|---|---|---|---|---|---|")
    print(f"| {ov['open']} | {ov['severity_open']['critical']} | "
          f"{ov['severity_open']['high']} | {overdue} | "
          f"{mttr if mttr is not None else '—'} d | {'+' if net > 0 else ''}{net} |\n")

    print("### Risk leaderboard\n")
    print("| Product | Risk | Crit | High | Overdue | MTTR |")
    print("|---|---:|---:|---:|---:|---:|")
    for b in r.get("leaderboard", []):
        m = f"{b['mttr_median']:g}d" if b["mttr_median"] is not None else "—"
        print(f"| {b['name']} | {b['risk_score']} | {b['open_critical']} | "
              f"{b['open_high']} | {b['overdue']} | {m} |")

    if r.get("insights"):
        print("\n### Insights\n")
        for s in r["insights"]:
            print(f"- {s.replace('*', '')}")
    print("\n---\n")


def find_reports(path: str) -> list[str]:
    if os.path.isfile(path):
        return [path]
    if os.path.isdir(path):
        # recursive '**' also matches the top-level out/report.json
        files = sorted(set(
            glob.glob(os.path.join(path, "**", "report.json"), recursive=True)
        ))
        return files
    return []


def main() -> int:
    path = sys.argv[1] if len(sys.argv) > 1 else "out"
    try:
        reports = find_reports(path)
        if not reports:
            print("_No report produced (nothing to summarize)._")
            return 0
        for f in reports:
            sub = os.path.basename(os.path.dirname(f))
            base = os.path.basename(path.rstrip("/")) if os.path.isdir(path) else ""
            suffix = f" — {sub}" if sub and sub not in ("out", base) else ""
            summarize(f, suffix)
    except Exception as e:  # never fail the job over a cosmetic summary
        print(f"_Summary unavailable: {e}_")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
