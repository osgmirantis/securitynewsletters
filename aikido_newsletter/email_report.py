"""
Email delivery.

  render_html(report, img_src, workspace)  -> HTML body (img_src maps chart
                                              name -> a src string: 'cid:…' for a
                                              real email, or a data: URI for a
                                              browser-viewable preview)
  render_text(report, workspace)           -> plain-text fallback
  build_message(...)                       -> a multipart/alternative EmailMessage
                                              with charts inlined as related images
  EmailPublisher(...).send(msg, to_addrs)  -> sends via SMTP (STARTTLS/SSL/plain)

Stdlib only (smtplib, email) — works with any SMTP server: Gmail, AWS SES SMTP,
Mailgun/SendGrid SMTP, or a corporate relay.
"""

from __future__ import annotations

import base64
import datetime as dt
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formatdate, make_msgid

from .analytics import TYPE_LABELS

SEV = {"critical": "#f85149", "high": "#fb8500", "medium": "#d4a200", "low": "#2f6df6"}
INK = "#1a1d24"
MUTED = "#5b6470"
LINE = "#e4e7ec"
DARK = "#0d1117"
ACCENT = "#2f6df6"

CHART_ORDER = ["risk_leaderboard", "severity_by_product", "opened_vs_closed_trend",
               "mttr_by_severity", "issue_type_mix", "open_aging", "top_cwes"]


def _d(ts: int) -> str:
    return dt.datetime.utcfromtimestamp(ts).strftime("%b %d, %Y")


def data_uri(path: str) -> str:
    with open(path, "rb") as f:
        return "data:image/png;base64," + base64.b64encode(f.read()).decode()


def default_subject(report: dict, workspace: str = "") -> str:
    rng = f"{_d(report['window_start'])} - {_d(report['generated_at'])}"
    ws = f" - {workspace}" if workspace else ""
    return f"Product Security Newsletter{ws} ({rng})"


# --------------------------------------------------------------------------- #
# HTML
# --------------------------------------------------------------------------- #
def render_html(report: dict, img_src: dict[str, str], workspace: str = "") -> str:
    ov = report["overall"]
    overdue = sum(p["overdue_open"] for p in report["products"].values())
    net = ov["opened_this_period"] - ov["closed_this_period"]
    mttr = ov["mttr_all"]["median"]

    def kpi(label, value, sub=""):
        return (
            f'<td width="33%" valign="top" style="padding:6px;">'
            f'<table width="100%" cellpadding="0" cellspacing="0" role="presentation" '
            f'style="background:#f7f8fa;border:1px solid {LINE};border-radius:10px;">'
            f'<tr><td style="padding:14px 16px;font-family:Helvetica,Arial,sans-serif;">'
            f'<div style="font-size:11px;letter-spacing:.6px;text-transform:uppercase;color:{MUTED};">{label}</div>'
            f'<div style="font-size:26px;font-weight:700;color:{INK};margin:4px 0 1px;font-family:Georgia,serif;">{value}</div>'
            f'<div style="font-size:11px;color:{MUTED};">{sub}</div>'
            f'</td></tr></table></td>')

    kpi_table = (
        '<table width="100%" cellpadding="0" cellspacing="0" role="presentation"><tr>'
        + kpi("Open issues", ov["open"])
        + kpi("Critical / High",
              f'<span style="color:{SEV["critical"]}">{ov["severity_open"]["critical"]}</span>'
              f' / <span style="color:{SEV["high"]}">{ov["severity_open"]["high"]}</span>')
        + kpi("Past SLA", f'<span style="color:{SEV["critical"]}">{overdue}</span>', "overdue")
        + "</tr><tr>"
        + kpi("Median MTTR", mttr if mttr is not None else "—", "days")
        + kpi("Opened / Closed", f'{ov["opened_this_period"]} / {ov["closed_this_period"]}', "this period")
        + kpi("Net backlog Δ", f'{"+" if net > 0 else ""}{net}', "growing" if net > 0 else "shrinking")
        + "</tr></table>")

    insights = "".join(
        f'<li style="margin:7px 0;">{s.replace("*", "")}</li>' for s in report["insights"])

    lb_rows = ""
    for i, b in enumerate(report["leaderboard"]):
        m = f"{b['mttr_median']:g}d" if b["mttr_median"] is not None else "—"
        arrow = "▲" if b["crit_delta"] > 0 else "▼" if b["crit_delta"] < 0 else "–"
        acol = SEV["critical"] if b["crit_delta"] > 0 else "#1a7f37" if b["crit_delta"] < 0 else MUTED
        bg = "#ffffff" if i % 2 == 0 else "#fafbfc"
        lb_rows += (
            f'<tr style="background:{bg};">'
            f'<td style="padding:9px 12px;border-bottom:1px solid {LINE};">{b["name"]}</td>'
            f'<td align="right" style="padding:9px 12px;border-bottom:1px solid {LINE};font-weight:700;">{b["risk_score"]}</td>'
            f'<td align="right" style="padding:9px 12px;border-bottom:1px solid {LINE};color:{SEV["critical"]};">{b["open_critical"]}</td>'
            f'<td align="right" style="padding:9px 12px;border-bottom:1px solid {LINE};color:{SEV["high"]};">{b["open_high"]}</td>'
            f'<td align="right" style="padding:9px 12px;border-bottom:1px solid {LINE};">{b["overdue"]}</td>'
            f'<td align="right" style="padding:9px 12px;border-bottom:1px solid {LINE};">{m}</td>'
            f'<td align="right" style="padding:9px 12px;border-bottom:1px solid {LINE};color:{acol};">{arrow}</td>'
            f'</tr>')

    crit = ""
    for c in report["top_critical_issues"][:8]:
        ident = c["cve"] or c["package"] or TYPE_LABELS.get(c["type"], c["type"])
        od = (f'<span style="background:#fdeceb;color:{SEV["critical"]};font-size:10px;'
              f'padding:2px 6px;border-radius:4px;margin-left:6px;">OVERDUE</span>') if c["overdue"] else ""
        crit += (
            f'<tr><td style="padding:10px 0;border-bottom:1px solid {LINE};font-family:Helvetica,Arial,sans-serif;">'
            f'<span style="display:inline-block;width:9px;height:9px;border-radius:50%;'
            f'background:{SEV.get(c["severity"], "#888")};margin-right:8px;"></span>'
            f'<b style="color:{INK};">{c["rule"]}</b> '
            f'<span style="color:{MUTED};font-size:11px;text-transform:uppercase;">{c["severity"]} · {c["score"]}</span>{od}'
            f'<div style="color:{MUTED};font-size:12px;margin:3px 0 0 17px;font-family:Consolas,Menlo,monospace;">'
            f'{c["product"]} · {c["repo"] or "—"} · {ident} · {c["age_days"]}d old</div>'
            f'</td></tr>')

    cwes = "".join(
        f'<span style="display:inline-block;background:#f1f3f6;border:1px solid {LINE};'
        f'border-radius:6px;padding:4px 9px;margin:0 6px 6px 0;font-family:Consolas,Menlo,monospace;'
        f'font-size:12px;color:{INK};">{c} <span style="color:{MUTED};">×{n}</span></span>'
        for c, n in report["top_cwes"][:8])

    charts_html = ""
    for name in CHART_ORDER:
        if name in img_src:
            charts_html += (
                f'<tr><td style="padding:8px 0;">'
                f'<table width="100%" cellpadding="0" cellspacing="0" role="presentation" '
                f'style="background:{DARK};border:1px solid {LINE};border-radius:10px;">'
                f'<tr><td style="padding:8px;">'
                f'<img src="{img_src[name]}" width="100%" alt="{name.replace("_", " ")}" '
                f'style="display:block;width:100%;max-width:620px;border-radius:6px;"></td></tr>'
                f'</table></td></tr>')

    def section_title(t):
        return (f'<tr><td style="padding:26px 0 10px;font-family:Helvetica,Arial,sans-serif;'
                f'font-size:12px;letter-spacing:1.2px;text-transform:uppercase;color:{MUTED};'
                f'border-bottom:1px solid {LINE};">{t}</td></tr>')

    head = f"{_d(report['window_start'])} – {_d(report['generated_at'])} · {len(report['products'])} products"
    if workspace:
        head += f" · {workspace}"

    return f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="light"><title>Product Security Newsletter</title></head>
<body style="margin:0;padding:0;background:#eef0f3;">
<table width="100%" cellpadding="0" cellspacing="0" role="presentation" style="background:#eef0f3;">
<tr><td align="center" style="padding:24px 12px;">
  <table width="680" cellpadding="0" cellspacing="0" role="presentation"
    style="max-width:680px;width:100%;background:#ffffff;border-radius:14px;overflow:hidden;
    box-shadow:0 1px 3px rgba(16,24,40,.08);">
    <tr><td style="background:{DARK};padding:26px 28px;">
      <div style="font-family:Georgia,serif;font-size:23px;color:#ffffff;font-weight:700;">
        🛡️ Product Security Newsletter</div>
      <div style="font-family:Consolas,Menlo,monospace;font-size:12px;color:#9aa4b2;margin-top:6px;">{head}</div>
    </td></tr>
    <tr><td style="padding:26px 28px;font-family:Helvetica,Arial,sans-serif;color:{INK};">
      <table width="100%" cellpadding="0" cellspacing="0" role="presentation">
        {section_title("Executive summary")}
      </table>
      <div style="height:12px;"></div>
      {kpi_table}
      <table width="100%" cellpadding="0" cellspacing="0" role="presentation">
        {section_title("📌 Insights")}
        <tr><td style="padding-top:10px;">
          <ul style="margin:0;padding-left:20px;color:{INK};font-size:14px;line-height:1.55;">{insights}</ul>
        </td></tr>
        {section_title("🏆 Product risk leaderboard")}
        <tr><td style="padding-top:12px;">
          <table width="100%" cellpadding="0" cellspacing="0" role="presentation"
            style="border:1px solid {LINE};border-radius:8px;overflow:hidden;font-size:13px;color:{INK};">
            <tr style="background:#f4f5f7;font-size:11px;letter-spacing:.5px;text-transform:uppercase;color:{MUTED};">
              <td style="padding:9px 12px;">Product</td><td align="right" style="padding:9px 12px;">Risk</td>
              <td align="right" style="padding:9px 12px;">Crit</td><td align="right" style="padding:9px 12px;">High</td>
              <td align="right" style="padding:9px 12px;">Overdue</td><td align="right" style="padding:9px 12px;">MTTR</td>
              <td align="right" style="padding:9px 12px;">Δ</td></tr>
            {lb_rows}
          </table></td></tr>
        {section_title("🔥 Most critical open findings")}
        <tr><td style="padding-top:6px;"><table width="100%" cellpadding="0" cellspacing="0" role="presentation">{crit}</table></td></tr>
        {section_title("Top weakness classes (CWE)")}
        <tr><td style="padding-top:12px;">{cwes}</td></tr>
        {section_title("📊 Charts")}
        {charts_html}
      </table>
    </td></tr>
    <tr><td style="background:#f7f8fa;padding:16px 28px;border-top:1px solid {LINE};
      font-family:Helvetica,Arial,sans-serif;font-size:11px;color:{MUTED};">
      Generated by aikido-product-newsletter · data via the Aikido API.
    </td></tr>
  </table>
</td></tr></table></body></html>"""


# --------------------------------------------------------------------------- #
# Plain text
# --------------------------------------------------------------------------- #
def render_text(report: dict, workspace: str = "") -> str:
    ov = report["overall"]
    overdue = sum(p["overdue_open"] for p in report["products"].values())
    net = ov["opened_this_period"] - ov["closed_this_period"]
    mttr = ov["mttr_all"]["median"]
    L = [f"PRODUCT SECURITY NEWSLETTER{(' — ' + workspace) if workspace else ''}",
         f"{_d(report['window_start'])} – {_d(report['generated_at'])} · {len(report['products'])} products",
         "",
         f"Open: {ov['open']}   Critical/High: {ov['severity_open']['critical']}/{ov['severity_open']['high']}"
         f"   Past SLA: {overdue}   Median MTTR: {mttr if mttr is not None else '-'}d"
         f"   Net backlog: {'+' if net > 0 else ''}{net}",
         "", "INSIGHTS"]
    L += [f"  - {s.replace('*', '')}" for s in report["insights"]]
    L += ["", "RISK LEADERBOARD",
          f"  {'Product':<18}{'Risk':>5}{'Crit':>5}{'High':>5}{'Late':>6}"]
    for b in report["leaderboard"]:
        L.append(f"  {b['name'][:17]:<18}{b['risk_score']:>5}{b['open_critical']:>5}"
                 f"{b['open_high']:>5}{b['overdue']:>6}")
    L += ["", "TOP CRITICAL FINDINGS"]
    for c in report["top_critical_issues"][:8]:
        ident = c["cve"] or c["package"] or ""
        L.append(f"  [{c['severity']}] {c['rule']} ({c['score']}) — {c['product']} · "
                 f"{c['repo'] or '-'}{(' · ' + ident) if ident else ''} · {c['age_days']}d"
                 f"{' OVERDUE' if c['overdue'] else ''}")
    if report["top_cwes"]:
        L += ["", "Top CWE: " + ", ".join(f"{c}×{n}" for c, n in report["top_cwes"][:8])]
    L += ["", "Generated by aikido-product-newsletter · data via the Aikido API."]
    return "\n".join(L)


# --------------------------------------------------------------------------- #
# Message + SMTP
# --------------------------------------------------------------------------- #
def build_message(report: dict, charts: dict[str, str], *, sender: str,
                  recipients: list[str], subject: str, cc: list[str] | None = None,
                  workspace: str = "") -> EmailMessage:
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = ", ".join(recipients)
    if cc:
        msg["Cc"] = ", ".join(cc)
    msg["Date"] = formatdate(localtime=True)

    cids = {name: make_msgid(domain="aikido-newsletter") for name in charts}
    html = render_html(report, {n: f"cid:{cid[1:-1]}" for n, cid in cids.items()}, workspace)

    msg.set_content(render_text(report, workspace))
    msg.add_alternative(html, subtype="html")
    html_part = msg.get_payload()[1]
    for name, path in charts.items():
        with open(path, "rb") as f:
            html_part.add_related(f.read(), maintype="image", subtype="png",
                                  cid=cids[name], filename=f"{name}.png",
                                  disposition="inline")
    return msg


class EmailPublisher:
    def __init__(self, host: str, port: int = 587, username: str | None = None,
                 password: str | None = None, security: str = "starttls"):
        self.host, self.port = host, port
        self.username, self.password = username, password
        self.security = security  # starttls | ssl | none

    def send(self, msg: EmailMessage, to_addrs: list[str]) -> None:
        ctx = ssl.create_default_context()
        try:
            if self.security == "ssl":
                smtp = smtplib.SMTP_SSL(self.host, self.port, context=ctx, timeout=30)
            else:
                smtp = smtplib.SMTP(self.host, self.port, timeout=30)
        except OSError as e:
            raise RuntimeError(
                f"Could not connect to SMTP {self.host}:{self.port} ({e}). "
                f"Check SMTP_HOST (Gmail is 'smtp.gmail.com', not 'smtp.google.com'), "
                f"the port (587=starttls, 465=ssl), and that the host is reachable "
                f"(GitHub runners allow 587/465 but block 25)."
            ) from e
        try:
            smtp.ehlo()
            if self.security == "starttls":
                smtp.starttls(context=ctx)
                smtp.ehlo()
            if self.username:
                try:
                    smtp.login(self.username, self.password or "")
                except smtplib.SMTPAuthenticationError as e:
                    raise RuntimeError(
                        f"SMTP auth failed for {self.username} ({e.smtp_code}). "
                        f"For Gmail/Workspace use a 16-char App Password (2-Step "
                        f"Verification required), not the account password."
                    ) from e
            smtp.send_message(msg, to_addrs=to_addrs)
        finally:
            smtp.quit()
