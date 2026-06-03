#!/usr/bin/env python3
"""
Aikido Product Security Newsletter (email edition).

Pulls issues for every Aikido team named `Product:<name>` across one or more
workspaces, computes AppSec KPIs, renders charts, and emails the newsletter to
a set of recipients (HTML with charts inlined, plus a plain-text fallback).

Examples
--------
  # Dry run with synthetic data -> writes HTML + .eml, sends nothing
  python -m main --mock --dry-run --out ./out

  # Single workspace -> email
  export AIKIDO_CLIENT_ID=... AIKIDO_CLIENT_SECRET=...
  export SMTP_HOST=smtp.example.com SMTP_USERNAME=apikey SMTP_PASSWORD=... \
         EMAIL_FROM="Security <sec@example.com>" EMAIL_TO="appsec@example.com,cto@example.com"
  python -m main --region eu --days 30

  # Multiple workspaces, separate email per workspace
  python -m main --per-workspace
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time

from aikido_newsletter import analytics, charts, email_report, mock_data, workspaces
from aikido_newsletter.aikido_client import AikidoClient


def _env(name: str, fallback: str | None = None) -> str | None:
    return os.environ.get(name, fallback)


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-") or "workspace"


def _addrs(value: str | None) -> list[str]:
    if not value:
        return []
    return [a.strip() for a in re.split(r"[,\n;]+", value) if a.strip()]


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="Aikido product security newsletter (email)")
    p.add_argument("--region", default=_env("AIKIDO_REGION", "eu"),
                   choices=["eu", "us", "me"], help="Region for single-workspace fallback")
    p.add_argument("--product-prefix", default="Product:", help="Team-name prefix")
    p.add_argument("--days", type=int, default=30, help="Reporting window (days)")
    p.add_argument("--trend-weeks", type=int, default=12, help="Weeks in the trend chart")
    p.add_argument("--per-workspace", action="store_true",
                   help="One email per workspace instead of one combined")
    # email
    p.add_argument("--email-to", default=_env("EMAIL_TO"),
                   help="Recipients, comma-separated")
    p.add_argument("--email-cc", default=_env("EMAIL_CC"), help="Cc, comma-separated")
    p.add_argument("--email-bcc", default=_env("EMAIL_BCC"), help="Bcc, comma-separated")
    p.add_argument("--email-from", default=_env("EMAIL_FROM"), help="From address")
    p.add_argument("--email-subject", default=_env("EMAIL_SUBJECT"),
                   help="Override subject (default includes the date range)")
    # smtp
    p.add_argument("--smtp-host", default=_env("SMTP_HOST"))
    p.add_argument("--smtp-port", type=int, default=int(_env("SMTP_PORT", "587")))
    p.add_argument("--smtp-username", default=_env("SMTP_USERNAME"))
    p.add_argument("--smtp-password", default=_env("SMTP_PASSWORD"))
    p.add_argument("--smtp-security", default=_env("SMTP_SECURITY", "starttls"),
                   choices=["starttls", "ssl", "none"])
    # run
    p.add_argument("--dry-run", action="store_true",
                   help="Render HTML + .eml, do not send")
    p.add_argument("--mock", action="store_true", help="Use synthetic data")
    p.add_argument("--out", default="./out", help="Output directory")
    p.add_argument("--save-json", action="store_true", help="Also write report.json")
    return p.parse_args(argv)


def gather(args) -> list[tuple[str, dict]]:
    if args.mock:
        print("• Using synthetic data (--mock)")
        return [("", mock_data.generate())]

    wss = workspaces.load()
    if not wss:
        sys.exit("ERROR: configure credentials — AIKIDO_CLIENT_ID/SECRET, or "
                 "AIKIDO_WORKSPACES (JSON) for several (or --mock).")
    multi = len(wss) > 1
    per_ws: list[tuple[str, dict]] = []
    for ws in wss:
        print(f"• Workspace {ws.name!r} ({ws.region}): listing {args.product_prefix!r} teams…")
        client = AikidoClient(ws.client_id, ws.client_secret, region=ws.region)
        bp = client.issues_by_product(prefix=args.product_prefix, status="all")
        for name, issues in bp.items():
            print(f"    {name}: {len(issues)} issues")
        per_ws.append((ws.name, bp))

    if args.per_workspace:
        return per_ws
    merged: dict[str, list] = {}
    for ws_name, bp in per_ws:
        for prod, issues in bp.items():
            merged[f"{ws_name} · {prod}" if multi else prod] = issues
    if not merged:
        sys.exit(f"No teams matched prefix {args.product_prefix!r} in any workspace.")
    return [("", merged)]


def deliver(args, label, report, chart_paths, out_dir, dry_run):
    workspace = label or _env("WORKSPACE_NAME", "")
    to = _addrs(args.email_to)
    cc = _addrs(args.email_cc)
    bcc = _addrs(args.email_bcc)
    subject = args.email_subject or email_report.default_subject(report, workspace)
    sender = args.email_from or "newsletter@example.com"

    if dry_run:
        html = email_report.render_html(
            report, {n: email_report.data_uri(p) for n, p in chart_paths.items()}, workspace)
        html_path = os.path.join(out_dir, "newsletter_email.html")
        with open(html_path, "w") as f:
            f.write(html)
        msg = email_report.build_message(
            report, chart_paths, sender=sender,
            recipients=to or ["recipient@example.com"], subject=subject, cc=cc,
            workspace=workspace)
        with open(os.path.join(out_dir, "newsletter.eml"), "wb") as f:
            f.write(bytes(msg))
        print(f"  ✓ Preview: {html_path}  (+ newsletter.eml)")
        return

    if not args.smtp_host:
        sys.exit("ERROR: set SMTP_HOST (and EMAIL_TO) to send, or use --dry-run.")
    msg = email_report.build_message(
        report, chart_paths, sender=sender, recipients=to, subject=subject,
        cc=cc, workspace=workspace)
    pub = email_report.EmailPublisher(
        args.smtp_host, args.smtp_port, args.smtp_username, args.smtp_password,
        args.smtp_security)
    print(f"  • Sending to {len(to + cc + bcc)} recipient(s) via {args.smtp_host}…")
    pub.send(msg, to + cc + bcc)
    print("  ✓ Email sent.")


def main(argv=None) -> int:
    args = parse_args(argv)
    os.makedirs(args.out, exist_ok=True)
    now = int(time.time())

    segments = gather(args)
    dry_run = args.dry_run or not (args.email_to and args.smtp_host)
    if dry_run:
        print("• Preview only (no recipients/SMTP configured or --dry-run set).")

    for label, issues_by_product in segments:
        out_dir = args.out if len(segments) == 1 else os.path.join(args.out, _slug(label))
        os.makedirs(out_dir, exist_ok=True)
        print(f"• {label or 'Combined'}: computing KPIs & charts…")
        report = analytics.build_report(
            issues_by_product, now=now, days=args.days, trend_weeks=args.trend_weeks)
        if args.save_json:
            with open(os.path.join(out_dir, "report.json"), "w") as f:
                json.dump(report, f, indent=2, default=str)
        chart_paths = charts.render_all(report, out_dir)
        deliver(args, label, report, chart_paths, out_dir, dry_run)

    print("✓ Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
