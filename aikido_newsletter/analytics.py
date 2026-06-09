"""
AppSec / vuln-management KPI engine.

Consumes the raw issue export (one list per product) and produces a single
report dict consumed by the chart and email layers.

KPIs implemented (all derivable from the /issues/export schema):
  - Open severity mix (critical/high/medium/low)
  - Issue-type mix (sast, open_source/SCA, leaked_secret, iac, container, cloud, ...)
  - MTTR (mean & median, in days) overall and per severity  -> closed_at - first_detected_at
  - SLA adherence %  -> closed_at <= sla_remediate_by ; plus currently-overdue open issues
  - Open-backlog aging buckets (0-7 / 8-30 / 31-90 / 90+ days)
  - Opened-vs-closed + reconstructed open-backlog trend, per week
  - Top CWE classes, top vulnerable packages, top CVEs
  - Per-product risk score (severity-weighted) -> leaderboard
  - Period-over-period deltas for opened criticals
"""

from __future__ import annotations

import statistics
from collections import Counter, defaultdict
from typing import Any

DAY = 86400
SEVERITIES = ("critical", "high", "medium", "low")
# Severity weights for the per-product risk score (open issues only).
RISK_WEIGHTS = {"critical": 10, "high": 5, "medium": 2, "low": 1}

# Human labels for Aikido issue types.
TYPE_LABELS = {
    "open_source": "Open-source (SCA)",
    "sast": "SAST",
    "leaked_secret": "Secrets",
    "iac": "IaC",
    "docker_container": "Container",
    "cloud": "Cloud",
    "cloud_instance": "Cloud instance",
    "malware": "Malware",
    "eol": "End-of-life",
    "mobile": "Mobile",
    "scm_security": "SCM",
    "surface_monitoring": "Surface mon.",
    "ai_pentest": "AI pentest",
    "license": "License",
}

# Origin grouping: WHERE a finding comes from / what fixing it means.
#   Code (SAST)         -> insecure code we wrote          (fix: change code)
#   Dependencies (SCA)  -> vulnerable libraries we pulled  (fix: upgrade dep)
#   Container images    -> CVEs in base images / OS pkgs   (fix: rebuild/patch image)
#   Secrets             -> leaked credentials in repos     (fix: rotate + remove)
#   Infrastructure      -> IaC / cloud misconfiguration    (fix: config)
SOURCE_CATEGORIES = {
    "sast": "Code (SAST)",
    "open_source": "Dependencies (SCA)",
    "docker_container": "Container images",
    "leaked_secret": "Secrets",
    "iac": "Infrastructure",
    "cloud": "Infrastructure",
    "cloud_instance": "Infrastructure",
}
SOURCE_ORDER = ["Code (SAST)", "Dependencies (SCA)", "Container images",
                "Secrets", "Infrastructure", "Other"]


def source_category(issue_type: str) -> str:
    return SOURCE_CATEGORIES.get(issue_type or "", "Other")


def _is_open(i: dict) -> bool:
    return i.get("status") == "open"


def _mttr_days(i: dict) -> float | None:
    c, f = i.get("closed_at"), i.get("first_detected_at")
    if c and f and c >= f:
        return (c - f) / DAY
    return None


def _stat_block(values: list[float]) -> dict:
    if not values:
        return {"n": 0, "mean": None, "median": None}
    return {
        "n": len(values),
        "mean": round(statistics.mean(values), 1),
        "median": round(statistics.median(values), 1),
    }


def _product_stats(name: str, issues: list[dict], now: int, days: int) -> dict:
    window_start = now - days * DAY
    open_issues = [i for i in issues if _is_open(i)]
    closed_issues = [i for i in issues if i.get("status") == "closed"]

    severity_open = Counter(i.get("severity", "low") for i in open_issues)
    type_open = Counter(i.get("type", "unknown") for i in open_issues)
    source_open = Counter(source_category(i.get("type", "")) for i in open_issues)

    # MTTR overall + per severity (over ALL closed issues with valid timestamps)
    mttr_all = [d for i in closed_issues if (d := _mttr_days(i)) is not None]
    mttr_by_sev = {
        sev: _stat_block(
            [d for i in closed_issues
             if i.get("severity") == sev and (d := _mttr_days(i)) is not None]
        )
        for sev in SEVERITIES
    }

    # SLA: closed within sla_remediate_by; open & past due = currently breaching
    closed_with_sla = [i for i in closed_issues if i.get("sla_remediate_by")]
    closed_in_sla = [i for i in closed_with_sla if i["closed_at"] <= i["sla_remediate_by"]]
    overdue_open = [
        i for i in open_issues
        if i.get("sla_remediate_by") and now > i["sla_remediate_by"]
    ]

    # Aging of currently-open issues
    aging = {"0-7": 0, "8-30": 0, "31-90": 0, "90+": 0}
    for i in open_issues:
        f = i.get("first_detected_at")
        if not f:
            continue
        age = (now - f) / DAY
        if age <= 7:
            aging["0-7"] += 1
        elif age <= 30:
            aging["8-30"] += 1
        elif age <= 90:
            aging["31-90"] += 1
        else:
            aging["90+"] += 1

    opened_this = sum(1 for i in issues if (i.get("first_detected_at") or 0) >= window_start)
    closed_this = sum(1 for i in issues if (i.get("closed_at") or 0) >= window_start)
    crit_opened_this = sum(
        1 for i in issues
        if i.get("severity") == "critical" and (i.get("first_detected_at") or 0) >= window_start
    )
    crit_opened_prev = sum(
        1 for i in issues
        if i.get("severity") == "critical"
        and window_start - days * DAY <= (i.get("first_detected_at") or 0) < window_start
    )

    risk = sum(RISK_WEIGHTS.get(s, 0) * c for s, c in severity_open.items())

    top_critical = sorted(
        [i for i in open_issues if i.get("severity") in ("critical", "high")],
        key=lambda i: (i.get("severity_score", 0), i.get("severity") == "critical"),
        reverse=True,
    )[:5]

    return {
        "name": name,
        "total": len(issues),
        "open": len(open_issues),
        "closed": len(closed_issues),
        "ignored": sum(1 for i in issues if i.get("status") == "ignored"),
        "snoozed": sum(1 for i in issues if i.get("status") == "snoozed"),
        "severity_open": {s: severity_open.get(s, 0) for s in SEVERITIES},
        "type_open": dict(type_open),
        "source_open": dict(source_open),
        "risk_score": risk,
        "overdue_open": len(overdue_open),
        "mttr_all": _stat_block(mttr_all),
        "mttr_by_sev": mttr_by_sev,
        "sla": {
            "closed_with_sla": len(closed_with_sla),
            "closed_in_sla": len(closed_in_sla),
            "pct": round(100 * len(closed_in_sla) / len(closed_with_sla), 1)
            if closed_with_sla else None,
        },
        "aging": aging,
        "opened_this_period": opened_this,
        "closed_this_period": closed_this,
        "crit_opened_this_period": crit_opened_this,
        "crit_opened_prev_period": crit_opened_prev,
        "top_critical": [
            {
                "rule": i.get("rule") or i.get("rule_id") or "Unnamed finding",
                "severity": i.get("severity"),
                "score": i.get("severity_score"),
                "type": i.get("type"),
                "cve": i.get("cve_id"),
                "package": i.get("affected_package"),
                "repo": i.get("code_repo_name") or i.get("container_repo_name")
                or i.get("cloud_name") or i.get("domain_name"),
                "age_days": round((now - i["first_detected_at"]) / DAY)
                if i.get("first_detected_at") else None,
                "overdue": bool(i.get("sla_remediate_by") and now > i["sla_remediate_by"]),
                "product": name,
            }
            for i in top_critical
        ],
    }


def _weekly_trend(all_issues: list[dict], now: int, weeks: int) -> dict:
    """Opened, closed, and reconstructed open-backlog per week (point-in-time)."""
    labels, opened, closed, backlog = [], [], [], []
    for w in range(weeks - 1, -1, -1):
        w_end = now - w * 7 * DAY
        w_start = w_end - 7 * DAY
        labels.append(_week_label(w_end))
        opened.append(sum(1 for i in all_issues
                          if w_start <= (i.get("first_detected_at") or 0) < w_end))
        closed.append(sum(1 for i in all_issues
                          if w_start <= (i.get("closed_at") or 0) < w_end))
        # backlog = detected before w_end and not yet closed at w_end
        backlog.append(sum(
            1 for i in all_issues
            if (i.get("first_detected_at") or 0) <= w_end
            and (i.get("closed_at") is None or (i.get("closed_at") or 0) > w_end)
        ))
    return {"weeks": labels, "opened": opened, "closed": closed, "backlog": backlog}


def _week_label(ts: int) -> str:
    import datetime as _dt
    return _dt.datetime.utcfromtimestamp(ts).strftime("%b %d")


def _top_counter(items, n: int):
    return Counter(items).most_common(n)


def _insights(report: dict) -> list[str]:
    out: list[str] = []
    ov = report["overall"]
    board = report["leaderboard"]

    crit_now = ov["crit_opened_this_period"]
    crit_prev = ov["crit_opened_prev_period"]
    if crit_prev or crit_now:
        if crit_prev == 0:
            out.append(f"*{crit_now}* new critical findings this period (none in the prior period).")
        else:
            delta = round(100 * (crit_now - crit_prev) / crit_prev)
            arrow = "up" if delta > 0 else "down" if delta < 0 else "flat"
            out.append(
                f"New critical findings are *{arrow} {abs(delta)}%* vs the previous "
                f"period ({crit_now} vs {crit_prev})."
            )

    if board:
        top = board[0]
        out.append(
            f"*{top['name']}* carries the highest risk score "
            f"({top['risk_score']}) — {top['open_critical']} critical / "
            f"{top['open_high']} high open, {top['overdue']} past SLA."
        )

    if report["top_cwes"]:
        cwe, c = report["top_cwes"][0]
        out.append(f"Most common weakness class is *{cwe}*, seen in {c} open findings.")

    src = ov.get("source_open", {})
    if sum(src.values()):
        code = src.get("Code (SAST)", 0)
        cont = src.get("Container images", 0)
        dep = src.get("Dependencies (SCA)", 0)
        out.append(
            f"By origin: *{code}* from our own code (SAST), *{cont}* from container "
            f"images, *{dep}* from dependencies (SCA) — i.e. how much is insecure "
            f"code vs insecure images vs vulnerable libraries.")

    crit_mttr = ov["mttr_by_sev"]["critical"]["median"]
    if crit_mttr is not None:
        out.append(f"Median time-to-remediate for *critical* issues is *{crit_mttr} days*.")

    total_overdue = sum(p["overdue_open"] for p in report["products"].values())
    if total_overdue:
        out.append(f"*{total_overdue}* open issues are currently past their SLA remediation date.")

    net = ov["opened_this_period"] - ov["closed_this_period"]
    if net > 0:
        out.append(
            f"Backlog *grew by {net}* this period "
            f"(opened {ov['opened_this_period']}, closed {ov['closed_this_period']})."
        )
    elif net < 0:
        out.append(
            f"Backlog *shrank by {abs(net)}* this period "
            f"(closed {ov['closed_this_period']}, opened {ov['opened_this_period']}) — teams are gaining ground."
        )
    return out


def build_report(
    issues_by_product: dict[str, list[dict]],
    *,
    now: int,
    days: int = 30,
    trend_weeks: int = 12,
    top_n: int = 8,
) -> dict:
    products = {
        name: _product_stats(name, issues, now, days)
        for name, issues in issues_by_product.items()
    }
    all_issues = [i for lst in issues_by_product.values() for i in lst]
    overall = _product_stats("All products", all_issues, now, days)

    # Cross-product frequency tables (open issues only)
    open_all = [i for i in all_issues if _is_open(i)]
    cwes = [c for i in open_all for c in (i.get("cwe_classes") or [])]
    pkgs = [i["affected_package"] for i in open_all if i.get("affected_package")]
    cves = [i["cve_id"] for i in open_all if i.get("cve_id")]

    leaderboard = sorted(
        (
            {
                "name": p["name"],
                "risk_score": p["risk_score"],
                "open_total": p["open"],
                "open_critical": p["severity_open"]["critical"],
                "open_high": p["severity_open"]["high"],
                "overdue": p["overdue_open"],
                "mttr_median": p["mttr_all"]["median"],
                "crit_delta": p["crit_opened_this_period"] - p["crit_opened_prev_period"],
            }
            for p in products.values()
        ),
        key=lambda x: x["risk_score"],
        reverse=True,
    )

    top_critical_issues = sorted(
        [c for p in products.values() for c in p["top_critical"]],
        key=lambda c: (c["score"] or 0, c["severity"] == "critical"),
        reverse=True,
    )[:8]

    report = {
        "generated_at": now,
        "window_days": days,
        "window_start": now - days * DAY,
        "trend_weeks": trend_weeks,
        "overall": overall,
        "products": products,
        "leaderboard": leaderboard,
        "trend": _weekly_trend(all_issues, now, trend_weeks),
        "top_critical_issues": top_critical_issues,
        "top_cwes": _top_counter(cwes, top_n),
        "top_packages": _top_counter(pkgs, top_n),
        "top_cves": _top_counter(cves, top_n),
    }
    report["insights"] = _insights(report)
    return report
