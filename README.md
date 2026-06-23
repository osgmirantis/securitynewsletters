# Aikido Product Security Newsletter

Generates a recurring AppSec newsletter from your **Aikido** workspace(s) and
**emails** it to a set of recipients. Products are defined as Aikido teams named
`Product:<name>` — the tool discovers them automatically and reports on each.

The email is HTML (with the charts **inlined**, no hosting needed) plus a
plain-text fallback. It contains an executive summary, a product **risk
leaderboard**, the most critical open findings, AppSec KPIs (severity mix,
issue-type mix, **MTTR by severity**, **SLA adherence / overdue**, **open-issue
aging**, **opened-vs-closed trend with reconstructed backlog**), top
**CWE / CVE / package** frequencies, and auto-generated narrative **insights**.

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

### Multiple Aikido workspaces

Aikido API credentials are **workspace-scoped** — there is no cross-workspace
token — so create one Client ID/Secret **per workspace** (in each workspace's
Settings → Integrations → API). Declare the workspaces in `AIKIDO_WORKSPACES`, a
JSON array with one object per workspace. Two ways to provide the credentials:

**(a) Inline — recommended for several workspaces.** Put the whole JSON, with
inline `client_id`/`client_secret`, in a single value. Because it contains
secrets, store it as a **GitHub Actions Secret** named `AIKIDO_WORKSPACES`
(locally, an env var). One value, nothing else to wire:

```json
[
  {"name":"k0rdent","region":"eu","client_id":"AIK_CLIENT_aaa","client_secret":"sec_aaa"},
  {"name":"workspace2","region":"eu","client_id":"AIK_CLIENT_bbb","client_secret":"sec_bbb"},
  {"name":"workspace3","region":"us","client_id":"AIK_CLIENT_ccc","client_secret":"sec_ccc"},
  {"name":"MOSK","region":"eu","client_id":"AIK_CLIENT_ddd","client_secret":"sec_ddd","all_teams":true}
]
```

Per-workspace team filtering:
- By default a workspace reports only teams whose name starts with the global
  `--product-prefix` (`Product:`).
- `"all_teams": true` — report **every** team in that workspace (e.g. **MOSK**,
  whose teams don't follow the `Product:` convention). Team names are used as-is.
- `"prefix": "Service:"` — override the prefix for just that workspace.

**(b) By reference — keeps each secret separate.** The JSON holds no secrets,
only `id_env`/`secret_env` pointing at other env vars, so it can be a
**Variable**; store each Client ID/Secret as its own Secret and map them in the
workflow `env:` block:

```json
[
  {"name":"k0rdent","region":"eu","id_env":"AIK_ID_K0RDENT","secret_env":"AIK_SECRET_K0RDENT"},
  {"name":"workspace2","region":"eu","id_env":"AIK_ID_WS2","secret_env":"AIK_SECRET_WS2"}
]
```

Notes:
- `region` is per workspace (`eu`/`us`/`me`) — set each to match where that
  workspace lives.
- **Default**: one *combined* email; product names are namespaced as
  `Workspace · Product` across all workspaces. Use `--per-workspace` for a
  *separate* email per workspace (outputs to `out/<workspace>/`).
- If `AIKIDO_WORKSPACES` is unset/empty, the tool falls back to a single
  workspace via `AIKIDO_CLIENT_ID` / `AIKIDO_CLIENT_SECRET` / `AIKIDO_REGION`.
- In the shipped workflow, `AIKIDO_WORKSPACES` is read from a Secret if present,
  otherwise a Variable: `${{ secrets.AIKIDO_WORKSPACES || vars.AIKIDO_WORKSPACES }}`.

## 2. Email / SMTP setup (one-time)

Delivery is plain **SMTP** (stdlib — no extra dependencies), so any provider
works: Gmail, AWS SES SMTP, Mailgun/SendGrid SMTP, or a corporate relay.

- **Recipients**: `EMAIL_TO` (comma-separated). `EMAIL_CC` / `EMAIL_BCC` optional.
- **Sender**: `EMAIL_FROM` (e.g. `Security Newsletter <security@example.com>`);
  must be an address your SMTP server is allowed to send as.
- **Server**: `SMTP_HOST`, `SMTP_PORT` (587 STARTTLS / 465 SSL / 25 none),
  `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_SECURITY` (`starttls` | `ssl` | `none`).
- **Subject**: defaults to include the date range; override with `EMAIL_SUBJECT`.

Charts are embedded inline via CID attachments, so they render in the email body
with no external hosting.

## 3. Configure

```bash
cp .env.example .env      # fill in the values, then:
set -a; source .env; set +a
pip install -r requirements.txt
```

## 4. Run

```bash
# Preview locally first — renders the HTML email + a .eml, sends nothing:
python -m main --dry-run --out ./out

# Send the email (needs SMTP_* and EMAIL_TO set):
python -m main --region eu --days 30

# One email per workspace (multi-workspace setups):
python -m main --per-workspace

# Try it with synthetic data (no credentials needed):
python -m main --mock --dry-run --out ./out
```

### Options

| Flag | Default | Meaning |
|------|---------|---------|
| `--region` | `eu` | Aikido region (single-workspace fallback) |
| `--product-prefix` | `Product:` | Team-name prefix marking a product |
| `--days` | `30` | Reporting window for period KPIs / deltas |
| `--trend-weeks` | `12` | Weeks in the opened/closed/backlog trend |
| `--per-workspace` | off | One email per workspace (else combined) |
| `--email-to` | env `EMAIL_TO` | Recipients, comma-separated |
| `--email-cc` / `--email-bcc` | env | Cc / Bcc recipients |
| `--email-from` | env `EMAIL_FROM` | Sender address |
| `--email-subject` | env `EMAIL_SUBJECT` | Subject override |
| `--smtp-host` / `--smtp-port` | env | SMTP server (`587`) |
| `--smtp-username` / `--smtp-password` | env | SMTP auth |
| `--smtp-security` | `starttls` | `starttls` / `ssl` / `none` |
| `--dry-run` | off | Render HTML + `.eml`, don't send |
| `--mock` | off | Use synthetic data instead of calling Aikido |
| `--save-json` | off | Also write the raw computed report |
| `--out` | `./out` | Output directory |

## 5. Schedule (weekly)

**cron**
```cron
0 9 * * 1  cd /opt/aikido-newsletter && set -a && . ./.env && set +a && \
           /usr/bin/python3 -m main >> run.log 2>&1
```

**GitHub Actions** — a ready workflow ships at
`.github/workflows/security-newsletter.yml` (weekly Monday 07:00 UTC + manual
trigger). To enable it:

1. Push this project to a repo (workflow expects the files at repo root).
2. **Settings → Secrets and variables → Actions → Secrets**, add:
   `AIKIDO_CLIENT_ID`, `AIKIDO_CLIENT_SECRET`, `SMTP_USERNAME`, `SMTP_PASSWORD`
   (and per-workspace `AIK_ID_*` / `AIK_SECRET_*` if using several).
3. Same screen → **Variables** (not secret): `EMAIL_TO`, `EMAIL_FROM`,
   `SMTP_HOST`, optionally `EMAIL_CC`, `SMTP_PORT`, `SMTP_SECURITY`,
   `AIKIDO_REGION`, `AIKIDO_WORKSPACES`, `WORKSPACE_NAME`.
4. The scheduled run sends the email. A **manual run** (Actions → Run workflow)
   can override `days`, tick **dry_run** (render without sending), or
   **per_workspace**. Every run uploads `out/` (charts, HTML, `.eml`,
   `report.json`) as an artifact and prints the KPIs to the run summary.

> GitHub cron is UTC-only; `0 7 * * 1` ≈ 09:00 in Barcelona. Adjust as needed.

---

## Attachment & Google Drive

**Attachment.** Every email carries an attachment with **the same content as the
email body** (executive summary, insights, leaderboards, charts). Pick the
format with `--attach-format` (env `ATTACH_FORMAT`):

- `html` *(default)* — a **self-contained HTML file**: it's the email body
  itself, with charts inlined, so it renders identically in any browser and in
  Google Drive's preview. No PDF engine, no fonts, no system libraries — the
  most reliable option.
- `pdf` — a PDF rendered from the same HTML via WeasyPrint. Needs system libs on
  the runner (`apt-get install -y libpango-1.0-0 libpangocairo-1.0-0
  libgdk-pixbuf-2.0-0 libffi-dev libcairo2`); emoji are stripped from the PDF
  since the print fonts can't draw them. Use this only if a PDF is required.
- `both` — attach the HTML and the PDF.
- `none` — body only.

The file is also written to the output dir (and the CI artifact).

**Google Drive.** Apart from emailing, the attachment is pushed to a Drive
folder. Set up once:

1. In Google Cloud, create a **service account**, enable the **Drive API**, and
   download its JSON key.
2. In Drive, **share the destination folder** with the service account's
   `client_email` (Editor). (For a Shared Drive folder, also pass
   `--gdrive-shared-drive` / `GDRIVE_SHARED_DRIVE=true`.)
3. Provide to the tool:
   - `GDRIVE_FOLDER_ID` — the folder's ID (from its URL), and
   - `GDRIVE_SERVICE_ACCOUNT_JSON` — the key JSON inline (a GitHub **Secret**),
     or `--gdrive-credentials /path/to/key.json` locally.

When a folder and credentials are present, the file uploads after the email
sends (skipped on `--dry-run`). Upload failures are logged but never block the
email. Scope used is `drive.file`. Note: service accounts can write to a folder
shared with them or to a Shared Drive — not to a human's personal My Drive root.

```bash
# local: email + attach the self-contained HTML + upload it to Drive
GDRIVE_SERVICE_ACCOUNT_JSON="$(cat sa.json)" GDRIVE_FOLDER_ID=1AbC… \
  python -m main --email-to team@corp.com --smtp-host smtp.gmail.com …
```

---

## How the KPIs are computed

All KPIs derive from the `/issues/export` fields, scoped per product team.

- **Open severity mix** — open issues grouped by `severity`.
- **Issue-type mix** — open issues grouped by `type` (SAST, open-source/SCA,
  secrets, IaC, container, cloud, …).
- **Findings by source (origin)** — open issues grouped into where they come
  from / what fixing them means: *Code (SAST)* = insecure code we wrote,
  *Container images* = CVEs in base images we run, *Dependencies (SCA)* =
  vulnerable libraries we pulled in, plus *Secrets* and *Infrastructure*. Edit
  the mapping in `analytics.py:SOURCE_CATEGORIES`.
- **MTTR** — `closed_at − first_detected_at`, mean & median in days, overall and
  per severity.
- **SLA adherence** — closed issues where `closed_at ≤ sla_remediate_by`;
  *overdue* = open issues where `now > sla_remediate_by`.
- **Aging** — open issues bucketed by age (0-7 / 8-30 / 31-90 / 90+ days).
- **Trend** — per week: opened (`first_detected_at`), closed (`closed_at`), and
  **reconstructed open backlog** = detected on/before the week end and not yet
  closed at that point. A true point-in-time series, not a snapshot.
- **Risk score** (leaderboard) — `10·critical + 5·high + 2·medium + 1·low` over
  open issues. Adjust the weights in `analytics.py:RISK_WEIGHTS`.
- **Security Champions** (hygiene score, 0–100, higher is better) — a friendly
  "best product" ranking that rewards remediation *effort*: remediation speed
  (MTTR, 30%, scored relative to peers), on-time fixes (SLA adherence, 30%),
  backlog control (closed ÷ opened+closed, 20%), and low open risk (severity-
  weighted, 20%, relative to peers). Effort is weighted above raw vuln count so
  any team can win regardless of size. Also surfaces a "best momentum / most
  improved" product. Tune in `analytics.py:HYGIENE_WEIGHTS`.
- **Top CWE / CVE / package** — frequency over open issues.
- **Insights** — narrative lines derived from period-over-period critical delta,
  highest-risk product, dominant CWE, critical MTTR, total overdue, and net
  backlog change. Edit `analytics.py:_insights`.

## 6. PowerPoint decks (optional)

Two decks are available:

**Overview / methodology deck** — explains what the report is, what data it's
based on, how findings are classified, and the KPI catalog with definitions (no
live numbers). Data-independent:

```bash
cd pptx && npm install && cd ..
node pptx/build_overview_deck.js out/newsletter-overview.pptx
```

**Data deck** — the current period's metrics as native, editable PowerPoint
charts (built from `report.json`, so run the tool once with `--save-json`):

```bash
python -m main --mock --dry-run --out ./out --save-json   # produces out/report.json
node pptx/build_deck.js out/report.json out/newsletter.pptx
```

The data deck has ten slides: title, executive summary, risk leaderboard,
severity by product, findings-by-source (origin), OWASP Top 10 risk,
remediation (MTTR/SLA/aging), persistence & recurrence, opened-vs-closed trend,
most-critical findings, top CWEs/packages/CVEs, and key takeaways. To produce in
CI, add a Node step after the Python run (`actions/setup-node`, `npm ci` in
`pptx/`, then the `node` command) and include the `.pptx` in the artifact.

## Layout

```
main.py                       CLI orchestrator
aikido_newsletter/
  aikido_client.py            OAuth2 + /teams + /issues/export
  workspaces.py               multi-workspace credential loader
  analytics.py                KPI engine + insights
  charts.py                   matplotlib chart rendering
  email_report.py             HTML+text email builder + SMTP publisher
  mock_data.py                synthetic data for --mock
scripts/job_summary.py        GitHub Actions run-summary
```

## Notes / security

- Secrets are read from env vars only; nothing is written to disk except the
  report/charts you ask for. Keep `.env` out of version control.
- The tool only needs **read** scopes on Aikido. It never mutates Aikido state.
- Validate the OAuth token endpoint for your region; this client uses
  `https://app.<region>.aikido.dev/api/oauth/token` per Aikido's auth docs.
