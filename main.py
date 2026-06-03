#!/usr/bin/env python3
"""
Aikido Product Security Newsletter.

Pulls issues for every Aikido team named `Product:<name>`, computes AppSec KPIs,
renders charts, and publishes a newsletter to Slack (or a local HTML preview).

Examples
--------
  # Dry run with synthetic data -> writes charts + HTML preview, posts nothing
  python -m main --mock --dry-run --out ./out

  # Real run against your workspace, publish to Slack
  export AIKIDO_CLIENT_ID=... AIKIDO_CLIENT_SECRET=... SLACK_BOT_TOKEN=xoxb-...
  python -m main --region eu --days 30 --slack-channel "#appsec-weekly"

  # Real run but preview locally first (no Slack post)
  python -m main --dry-run --out ./out
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

from aikido_newsletter import analytics, charts, mock_data, preview
from aikido_newsletter.aikido_client import AikidoClient
from aikido_newsletter.slack_report import (
    SlackBotPublisher,
    SlackWebhookPublisher,
    build_blocks,
)


def _env(name: str, fallback: str | None = None) -> str | None:
    return os.environ.get(name, fallback)


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="Aikido product security newsletter")
    p.add_argument("--region", default=_env("AIKIDO_REGION", "eu"),
                   choices=["eu", "us", "me"], help="Aikido data region")
    p.add_argument("--product-prefix", default="Product:",
                   help="Team-name prefix that marks a product")
    p.add_argument("--days", type=int, default=30, help="Reporting window (days)")
    p.add_argument("--trend-weeks", type=int, default=12,
                   help="Weeks of opened/closed/backlog trend")
    p.add_argument("--slack-webhook", default=_env("SLACK_WEBHOOK_URL"),
                   help="Incoming-webhook URL (simplest path; no token/channel)")
    p.add_argument("--slack-channel", default=_env("SLACK_CHANNEL"),
                   help="Channel for the bot-token path (id or #name)")
    p.add_argument("--chart-base-url", default=_env("SLACK_CHART_BASE_URL"),
                   help="Public base URL where chart PNGs are hosted, to embed "
                        "them as image blocks in webhook mode")
    p.add_argument("--dry-run", action="store_true",
                   help="Build charts + HTML preview, do not post to Slack")
    p.add_argument("--mock", action="store_true",
                   help="Use synthetic data instead of calling Aikido")
    p.add_argument("--out", default="./out", help="Output directory")
    p.add_argument("--save-json", action="store_true",
                   help="Also write the computed report as report.json")
    return p.parse_args(argv)


def fetch(args) -> dict[str, list[dict]]:
    if args.mock:
        print("• Using synthetic data (--mock)")
        return mock_data.generate()
    cid, secret = _env("AIKIDO_CLIENT_ID"), _env("AIKIDO_CLIENT_SECRET")
    if not (cid and secret):
        sys.exit("ERROR: set AIKIDO_CLIENT_ID and AIKIDO_CLIENT_SECRET "
                 "(or pass --mock).")
    client = AikidoClient(cid, secret, region=args.region)
    print(f"• Listing teams (prefix {args.product_prefix!r})…")
    by_product = client.issues_by_product(prefix=args.product_prefix, status="all")
    if not by_product:
        sys.exit(f"No teams matched prefix {args.product_prefix!r}. "
                 "Check the prefix and the teams:read scope.")
    for name, issues in by_product.items():
        print(f"    {name}: {len(issues)} issues")
    return by_product


def main(argv=None) -> int:
    args = parse_args(argv)
    os.makedirs(args.out, exist_ok=True)
    now = int(time.time())

    issues_by_product = fetch(args)
    print("• Computing KPIs…")
    report = analytics.build_report(
        issues_by_product, now=now, days=args.days, trend_weeks=args.trend_weeks)

    if args.save_json:
        with open(os.path.join(args.out, "report.json"), "w") as f:
            json.dump(report, f, indent=2, default=str)

    print("• Rendering charts…")
    chart_paths = charts.render_all(report, args.out)

    workspace = _env("WORKSPACE_NAME", "")
    blocks = build_blocks(report, workspace)

    have_target = bool(args.slack_webhook) or bool(args.slack_channel and _env("SLACK_BOT_TOKEN"))

    if args.dry_run or not have_target:
        path = preview.render(report, chart_paths, args.out, workspace=workspace)
        if not args.dry_run and not have_target:
            print("• No Slack target configured → preview only "
                  "(set SLACK_WEBHOOK_URL, or SLACK_BOT_TOKEN + --slack-channel).")
        print(f"✓ Preview written: {path}")
        with open(os.path.join(args.out, "slack_blocks.json"), "w") as f:
            json.dump(blocks, f, indent=2)
        print(f"✓ Slack Block Kit payload: {os.path.join(args.out, 'slack_blocks.json')}")
        return 0

    # Webhook path (preferred: URL only, no token/channel)
    if args.slack_webhook:
        mode = ("with hosted charts" if args.chart_base_url
                else "text-only (charts in artifact; set --chart-base-url to embed)")
        print(f"• Publishing via incoming webhook, {mode}…")
        SlackWebhookPublisher(args.slack_webhook, args.chart_base_url).publish(
            blocks, chart_paths)
        print("✓ Posted via webhook.")
        return 0

    # Bot-token path (uploads charts directly into the thread)
    token = _env("SLACK_BOT_TOKEN")
    print(f"• Publishing to Slack {args.slack_channel} (bot token)…")
    ts = SlackBotPublisher(token).publish(args.slack_channel, blocks, chart_paths)
    print(f"✓ Posted (ts={ts}) with {len(chart_paths)} charts in thread.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
