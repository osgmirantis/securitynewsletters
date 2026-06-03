"""
Chart rendering (matplotlib, headless). Each function writes a PNG and returns
its path. Palette is a cohesive dark "security-ops" theme; severity colours
follow the conventional critical=red / high=orange / medium=amber / low=blue.
"""

from __future__ import annotations

import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager  # noqa: F401

# ---- theme ------------------------------------------------------------------
BG = "#0d1117"
PANEL = "#161b22"
GRID = "#2b3340"
TEXT = "#e6edf3"
MUTED = "#8b949e"
ACCENT = "#2f81f7"
SEV_COLORS = {"critical": "#f85149", "high": "#fb8500", "medium": "#f5c518", "low": "#58a6ff"}
SERIES = ["#2f81f7", "#3fb950", "#f85149", "#a371f7", "#fb8500", "#56d4dd"]

plt.rcParams.update({
    "figure.facecolor": BG, "axes.facecolor": PANEL, "savefig.facecolor": BG,
    "text.color": TEXT, "axes.labelcolor": TEXT, "axes.edgecolor": GRID,
    "xtick.color": MUTED, "ytick.color": MUTED, "grid.color": GRID,
    "font.family": "DejaVu Sans", "font.size": 11, "axes.titlecolor": TEXT,
    "axes.titlesize": 13, "axes.titleweight": "bold", "figure.dpi": 150,
})


def _style(ax):
    ax.grid(axis="x", linestyle="-", linewidth=0.6, alpha=0.4)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(GRID)


def _save(fig, out_dir: str, name: str) -> str:
    path = os.path.join(out_dir, name)
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight", pad_inches=0.25)
    plt.close(fig)
    return path


def severity_by_product(report: dict, out_dir: str) -> str:
    products = list(report["products"].values())
    products.sort(key=lambda p: p["risk_score"])
    names = [p["name"] for p in products]
    fig, ax = plt.subplots(figsize=(8, max(2.4, 0.55 * len(names) + 1.4)))
    left = [0] * len(names)
    for sev in ("critical", "high", "medium", "low"):
        vals = [p["severity_open"][sev] for p in products]
        ax.barh(names, vals, left=left, color=SEV_COLORS[sev], label=sev.capitalize(),
                height=0.62, edgecolor=BG, linewidth=1)
        left = [l + v for l, v in zip(left, vals)]
    for i, total in enumerate(left):
        if total:
            ax.text(total + max(left) * 0.01, i, str(int(total)), va="center",
                    color=MUTED, fontsize=10)
    _style(ax)
    ax.set_title("Open issues by severity, per product", pad=14)
    ax.set_xlabel("Open issues")
    ax.legend(ncol=4, frameon=False, loc="upper center", fontsize=9,
              bbox_to_anchor=(0.5, -0.22))
    return _save(fig, out_dir, "severity_by_product.png")


def risk_leaderboard(report: dict, out_dir: str) -> str:
    board = list(reversed(report["leaderboard"]))
    names = [b["name"] for b in board]
    scores = [b["risk_score"] for b in board]
    colors = [SEV_COLORS["critical"] if b["open_critical"] else
              SEV_COLORS["high"] if b["open_high"] else ACCENT for b in board]
    fig, ax = plt.subplots(figsize=(8, max(2.2, 0.5 * len(names) + 1.2)))
    ax.barh(names, scores, color=colors, height=0.6)
    for i, b in enumerate(board):
        ax.text(b["risk_score"] + max(scores + [1]) * 0.012, i,
                f"{b['risk_score']}  ({b['open_critical']}C/{b['open_high']}H)",
                va="center", color=MUTED, fontsize=9)
    _style(ax)
    ax.set_title("Product risk leaderboard  (10·C + 5·H + 2·M + 1·L, open issues)")
    ax.set_xlabel("Risk score")
    return _save(fig, out_dir, "risk_leaderboard.png")


def issue_type_mix(report: dict, out_dir: str) -> str:
    from .analytics import TYPE_LABELS
    agg: dict[str, int] = {}
    for p in report["products"].values():
        for t, c in p["type_open"].items():
            agg[t] = agg.get(t, 0) + c
    items = sorted(agg.items(), key=lambda x: x[1], reverse=True)
    labels = [TYPE_LABELS.get(t, t) for t, _ in items]
    vals = [v for _, v in items]
    fig, ax = plt.subplots(figsize=(7.5, max(2.2, 0.5 * len(labels) + 1)))
    ax.barh(list(reversed(labels)), list(reversed(vals)),
            color=[SERIES[i % len(SERIES)] for i in range(len(vals))][::-1], height=0.62)
    for i, v in enumerate(reversed(vals)):
        ax.text(v + max(vals + [1]) * 0.012, i, str(v), va="center", color=MUTED, fontsize=9)
    _style(ax)
    ax.set_title("Open issues by type (AppSec category)")
    ax.set_xlabel("Open issues")
    return _save(fig, out_dir, "issue_type_mix.png")


def mttr_by_severity(report: dict, out_dir: str) -> str:
    sevs = ["critical", "high", "medium", "low"]
    med = [report["overall"]["mttr_by_sev"][s]["median"] or 0 for s in sevs]
    fig, ax = plt.subplots(figsize=(7, 3.4))
    bars = ax.bar(sevs, med, color=[SEV_COLORS[s] for s in sevs], width=0.6)
    for b, v in zip(bars, med):
        ax.text(b.get_x() + b.get_width() / 2, v + max(med + [1]) * 0.02,
                f"{v:g}d", ha="center", color=TEXT, fontsize=10, fontweight="bold")
    ax.grid(axis="y", linestyle="-", linewidth=0.6, alpha=0.4)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.set_title("Median time-to-remediate by severity")
    ax.set_ylabel("Days")
    return _save(fig, out_dir, "mttr_by_severity.png")


def opened_vs_closed_trend(report: dict, out_dir: str) -> str:
    t = report["trend"]
    x = range(len(t["weeks"]))
    fig, ax = plt.subplots(figsize=(9, 3.8))
    w = 0.4
    ax.bar([i - w / 2 for i in x], t["opened"], width=w, color=SEV_COLORS["high"],
           label="Opened", alpha=0.9)
    ax.bar([i + w / 2 for i in x], t["closed"], width=w, color=SERIES[1],
           label="Closed", alpha=0.9)
    ax2 = ax.twinx()
    ax2.plot(list(x), t["backlog"], color=ACCENT, marker="o", markersize=4,
             linewidth=2, label="Open backlog")
    ax2.set_ylabel("Open backlog", color=ACCENT)
    ax2.tick_params(axis="y", colors=ACCENT)
    ax2.spines["top"].set_visible(False)
    ax.set_xticks(list(x))
    ax.set_xticklabels(t["weeks"], rotation=45, ha="right", fontsize=8)
    ax.grid(axis="y", linestyle="-", linewidth=0.6, alpha=0.3)
    for s in ("top",):
        ax.spines[s].set_visible(False)
    ax.set_title("Weekly opened vs closed, with open backlog")
    ax.set_ylabel("Issues / week")
    lines, labels = ax.get_legend_handles_labels()
    l2, lab2 = ax2.get_legend_handles_labels()
    ax.legend(lines + l2, labels + lab2, frameon=False, ncol=3, fontsize=9,
              loc="upper left")
    return _save(fig, out_dir, "opened_vs_closed_trend.png")


def open_aging(report: dict, out_dir: str) -> str:
    buckets = ["0-7", "8-30", "31-90", "90+"]
    agg = {b: 0 for b in buckets}
    for p in report["products"].values():
        for b in buckets:
            agg[b] += p["aging"][b]
    vals = [agg[b] for b in buckets]
    colors = [SERIES[1], "#f5c518", SEV_COLORS["high"], SEV_COLORS["critical"]]
    fig, ax = plt.subplots(figsize=(7, 3.2))
    bars = ax.bar([f"{b} d" for b in buckets], vals, color=colors, width=0.62)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + max(vals + [1]) * 0.02, str(v),
                ha="center", color=TEXT, fontsize=10, fontweight="bold")
    ax.grid(axis="y", linestyle="-", linewidth=0.6, alpha=0.4)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.set_title("Open-issue aging (how long findings stay open)")
    ax.set_ylabel("Open issues")
    return _save(fig, out_dir, "open_aging.png")


def top_cwes(report: dict, out_dir: str) -> str:
    data = report["top_cwes"]
    if not data:
        return ""
    labels = [c for c, _ in data][::-1]
    vals = [n for _, n in data][::-1]
    fig, ax = plt.subplots(figsize=(7.5, max(2.2, 0.45 * len(labels) + 1)))
    ax.barh(labels, vals, color=SERIES[3], height=0.6)
    for i, v in enumerate(vals):
        ax.text(v + max(vals + [1]) * 0.012, i, str(v), va="center", color=MUTED, fontsize=9)
    _style(ax)
    ax.set_title("Most common weakness classes (CWE)")
    ax.set_xlabel("Open findings")
    return _save(fig, out_dir, "top_cwes.png")


CHARTS = [
    ("risk_leaderboard", risk_leaderboard),
    ("severity_by_product", severity_by_product),
    ("opened_vs_closed_trend", opened_vs_closed_trend),
    ("mttr_by_severity", mttr_by_severity),
    ("issue_type_mix", issue_type_mix),
    ("open_aging", open_aging),
    ("top_cwes", top_cwes),
]


def render_all(report: dict, out_dir: str) -> dict[str, str]:
    os.makedirs(out_dir, exist_ok=True)
    out: dict[str, str] = {}
    for name, fn in CHARTS:
        path = fn(report, out_dir)
        if path:
            out[name] = path
    return out
