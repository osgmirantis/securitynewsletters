# Aikido Product Security Newsletter

Generates a recurring AppSec newsletter from your **Aikido** workspace and
publishes it to **Slack**. Products are defined as Aikido teams named
`Product:<name>` — the tool discovers them automatically and reports on each.

It produces an executive summary, a product **risk leaderboard**, the most
critical open findings, AppSec KPIs (severity mix, issue-type mix, **MTTR by
severity**, **SLA adherence / overdue**, **open-issue aging**, **opened-vs-closed
trend with reconstructed backlog**), top **CWE / CVE / package** frequencies, and
auto-generated narrative **insights** — as charts plus a Slack Block Kit message.

---

## 1. Aikido setup (one-time)

Aikido's public API uses **OAuth2 client credentials** (a Client ID + Secret,
not a single API key).

1. Aikido → **Settings → Integrations → API → REST API** → create credentials.
2. Grant the read scopes: **`teams:read`** and **`issues:read`**.
3. Note your data **region**: `eu` (`app.aikido.dev`), `us` (`app.us.aikido.dev`),
   or `me` (`app.me.aikido.dev`). This must match your workspace.
4. Make sure each product has a team named exactly `Product:<name>` with its
   repos/containers/clouds linked as the team's *responsibilities* (issues are
   scoped to the team via `filter_team_id`).

## 2. Slack setup (one-time)

Create a Slack app with a **bot token** (`xoxb-…`) and these scopes:
**`chat:write`** and **`files:write`**. Invite the bot to the target channel.
(The tool uploads charts with `files_upload_v2`; the legacy `files.upload` was
retired by Slack in Nov 2025.)

## 3. Configure

```bash
cp .env.example .env      # fill in the values, then:
set -a; source .env; set +a
pip install -r requirements.txt
```

## 4. Run

```bash
# Preview locally first — builds charts + an HTML preview, posts nothing:
python -m main --dry-run --out ./out

# Publish to Slack:
python -m main --region eu --days 30 --slack-channel "#appsec-weekly"

# Try it with synthetic data (no credentials needed):
python -m main --mock --dry-run --out ./out
```

### Options

| Flag | Default | Meaning |
|------|---------|---------|
| `--region` | `eu` | Aikido region: `eu` / `us` / `me` |
| `--product-prefix` | `Product:` | Team-name prefix marking a product |
| `--days` | `30` | Reporting window for period KPIs / deltas |
| `--trend-weeks` | `12` | Weeks in the opened/closed/backlog trend |
| `--slack-channel` | env `SLACK_CHANNEL` | Channel to post to (omit ⇒ preview only) |
| `--dry-run` | off | Build charts + HTML preview, don't post |
| `--mock` | off | Use synthetic data instead of calling Aikido |
| `--save-json` | off | Also write the raw computed report |
| `--out` | `./out` | Output directory |

## 5. Schedule (weekly)

**cron**
```cron
0 9 * * 1  cd /opt/aikido-newsletter && set -a && . ./.env && set +a && \
           /usr/bin/python3 -m main --slack-channel "#appsec-weekly" >> run.log 2>&1
```

**GitHub Actions** — store `AIKIDO_CLIENT_ID`, `AIKIDO_CLIENT_SECRET`,
`SLACK_BOT_TOKEN` as repo secrets and run `python -m main --slack-channel …`
on a `schedule:` cron trigger.

---

## How the KPIs are computed

All KPIs derive from the `/issues/export` fields, scoped per product team.

- **Open severity mix** — open issues grouped by `severity`.
- **Issue-type mix** — open issues grouped by `type` (SAST, open-source/SCA,
  secrets, IaC, container, cloud, …).
- **MTTR** — `closed_at − first_detected_at`, mean & median in days, overall and
  per severity.
- **SLA adherence** — closed issues where `closed_at ≤ sla_remediate_by`;
  *overdue* = open issues where `now > sla_remediate_by`.
- **Aging** — open issues bucketed by age (0-7 / 8-30 / 31-90 / 90+ days).
- **Trend** — per week: opened (`first_detected_at`), closed (`closed_at`), and
  **reconstructed open backlog** = detected on/before the week end and not yet
  closed at that point. This is a true point-in-time series, not a snapshot.
- **Risk score** (leaderboard) — `10·critical + 5·high + 2·medium + 1·low` over
  open issues. Adjust the weights in `analytics.py:RISK_WEIGHTS`.
- **Top CWE / CVE / package** — frequency over open issues.
- **Insights** — narrative lines derived from period-over-period critical delta,
  highest-risk product, dominant CWE, critical MTTR, total overdue, and net
  backlog change. Edit `analytics.py:_insights`.

## Layout

```
main.py                       CLI orchestrator
aikido_newsletter/
  aikido_client.py            OAuth2 + /teams + /issues/export
  analytics.py                KPI engine + insights
  charts.py                   matplotlib chart rendering
  slack_report.py             Block Kit builder + files_upload_v2 publisher
  preview.py                  HTML dry-run preview
  mock_data.py                synthetic data for --mock
```

## Notes / security

- Secrets are read from env vars only; nothing is written to disk except the
  report/charts you ask for. Keep `.env` out of version control.
- The tool only needs **read** scopes. It never mutates Aikido state.
- Validate the OAuth token endpoint for your region; this client uses
  `https://app.<region>.aikido.dev/api/oauth/token` per Aikido's auth docs.
```
