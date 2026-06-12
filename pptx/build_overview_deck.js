/*
 * Build the "about this report" deck — what the Product Security Newsletter is,
 * what data it's based on, how findings are classified, and the KPI catalog
 * with definitions. No live numbers; this explains the report itself.
 *
 *   node pptx/build_overview_deck.js <out.pptx>
 */
const pptxgen = require("pptxgenjs");
const outPath = process.argv[2] || "out/newsletter-overview.pptx";

const DARK = "0E1726", PANEL = "F4F6F9", INK = "1A1D24", MUTED = "5B6470";
const LINE = "E4E7EC", ACCENT = "2F6DF6", WHITE = "FFFFFF";
const SEV = { critical: "F85149", high: "FB8500", medium: "D4A200", low: "58A6FF" };
const SRC = { code: "2F6DF6", dep: "8957E5", img: "1F9AA8", sec: "F85149", infra: "D4760A" };
const HEAD = "Cambria", BODY = "Calibri", MONO = "Consolas";

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";
pres.author = "aikido-product-newsletter";
pres.title = "Product Security Newsletter — Overview & KPIs";
const W = 13.33, H = 7.5, M = 0.6;
const shadow = () => ({ type: "outer", color: "20304A", blur: 8, offset: 2, angle: 90, opacity: 0.16 });

let _pg = 1;
function kicker(s, t) { s.addText(t.toUpperCase(), { x: M, y: 0.42, w: W - 2 * M, h: 0.3, fontFace: BODY, fontSize: 12, color: ACCENT, bold: true, charSpacing: 3, margin: 0 }); }
function title(s, t) { s.addText(t, { x: M, y: 0.72, w: W - 2 * M, h: 0.7, fontFace: HEAD, fontSize: 30, color: INK, bold: true, margin: 0 }); }
function footer(s) { _pg++; s.addText("Product Security Newsletter  ·  methodology & KPI reference", { x: M, y: H - 0.45, w: 9, h: 0.3, fontFace: BODY, fontSize: 9, color: MUTED, margin: 0 }); s.addText(String(_pg), { x: W - 1.1, y: H - 0.45, w: 0.5, h: 0.3, fontFace: BODY, fontSize: 9, color: MUTED, align: "right" }); }

// card with a small colored dot motif (top-left)
function card(s, x, y, w, h, dot) {
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.08, fill: { color: PANEL }, line: { color: LINE, width: 1 }, shadow: shadow() });
  if (dot) s.addShape(pres.shapes.OVAL, { x: x + 0.28, y: y + 0.3, w: 0.16, h: 0.16, fill: { color: dot } });
}
function defCard(s, x, y, w, h, name, def, dot) {
  card(s, x, y, w, h, dot);
  s.addText(name, { x: x + (dot ? 0.58 : 0.3), y: y + 0.22, w: w - (dot ? 0.88 : 0.6), h: 0.4, fontFace: BODY, fontSize: 15, bold: true, color: INK, margin: 0, valign: "middle" });
  s.addText(def, { x: x + 0.3, y: y + 0.72, w: w - 0.6, h: h - 0.95, fontFace: BODY, fontSize: 12.5, color: MUTED, margin: 0, valign: "top", lineSpacingMultiple: 1.05 });
}

// =================================================================== 1 TITLE
let s = pres.addSlide(); s.background = { color: DARK };
s.addText("PRODUCT SECURITY NEWSLETTER", { x: M, y: 2.35, w: W - 2 * M, h: 0.5, fontFace: BODY, fontSize: 16, color: "7FA8FF", bold: true, charSpacing: 4, margin: 0 });
s.addText("How it works & what it measures", { x: M, y: 2.85, w: W - 2 * M, h: 1.1, fontFace: HEAD, fontSize: 46, color: WHITE, bold: true, margin: 0 });
s.addText("An automated, per-product application-security report built from Aikido — this deck explains what it's based on and the KPIs it tracks.",
  { x: M, y: 4.15, w: 10.5, h: 0.8, fontFace: BODY, fontSize: 16, color: "AEB8C7", margin: 0, lineSpacingMultiple: 1.1 });
s.addText("Methodology & KPI reference", { x: M, y: H - 0.6, w: 9, h: 0.3, fontFace: BODY, fontSize: 11, color: "5C6678", margin: 0 });

// =================================================================== 2 PURPOSE
s = pres.addSlide(); s.background = { color: WHITE };
kicker(s, "Purpose"); title(s, "What the report answers");
s.addText("A weekly read on the security posture of each product, so teams and leadership can see risk, compare products, and track whether we're improving — without logging into a scanner.",
  { x: M, y: 1.5, w: W - 2 * M, h: 0.7, fontFace: BODY, fontSize: 14, color: INK, margin: 0, lineSpacingMultiple: 1.1 });
const qs = [
  ["Which product carries the most risk?", "A single risk score per product ranks where to focus.", SEV.critical],
  ["Are we getting better or worse?", "Opened vs closed and the open-backlog trend over time.", ACCENT],
  ["Where does the risk come from?", "Our own code, the images we run, or the libraries we depend on.", SRC.dep],
  ["What needs attention now?", "Criticals, items past SLA, and the oldest unresolved findings.", SEV.high],
];
const qw = (W - 2 * M - 0.4) / 2, qh = 1.6;
qs.forEach((q, i) => {
  const x = M + (i % 2) * (qw + 0.4), y = 2.35 + Math.floor(i / 2) * (qh + 0.35);
  defCard(s, x, y, qw, qh, q[0], q[1], q[2]);
});
footer(s);

// =================================================================== 3 DATA BASIS
s = pres.addSlide(); s.background = { color: WHITE };
kicker(s, "What it's based on"); title(s, "Data source & scope");
const basis = [
  ["Aikido Security", "All findings come from Aikido's public REST API (OAuth2, read-only scopes teams:read + issues:read). The report never writes back.", ACCENT],
  ["Products = teams", "Each product is an Aikido team named Product:<name>. The report discovers them automatically and reports on each.", SRC.code],
  ["Across workspaces", "Credentials are per-workspace, so several workspaces are pulled and combined; products are namespaced Workspace · Product.", SRC.img],
  ["MOSK exception", "MOSK's teams don't use the Product: prefix, so that workspace is configured to report on ALL its teams.", SRC.infra],
  ["Full issue export", "The /issues/export endpoint returns every finding (open, closed, ignored, snoozed) with severity, type, CWE, CVE, package, timestamps and SLA.", SRC.dep],
  ["Time windows", "A reporting window (default 30 days) drives period KPIs; a longer window (default 12 weeks) drives the trend.", SEV.medium],
];
const bw = (W - 2 * M - 2 * 0.35) / 3, bh = 1.95;
basis.forEach((b, i) => {
  const x = M + (i % 3) * (bw + 0.35), y = 1.65 + Math.floor(i / 3) * (bh + 0.3);
  defCard(s, x, y, bw, bh, b[0], b[1], b[2]);
});
footer(s);

// =================================================================== 4 PIPELINE
s = pres.addSlide(); s.background = { color: WHITE };
kicker(s, "How it works"); title(s, "From scan data to your inbox");
const steps = [
  ["Aikido API", "OAuth2 token"],
  ["Product teams", "per workspace"],
  ["Issue export", "all findings"],
  ["KPI engine", "metrics + charts"],
  ["Delivery", "email · deck"],
];
const bx = 2.18, bh2 = 1.5, gap = (W - 2 * M - steps.length * bx) / (steps.length - 1), py = 2.7;
steps.forEach((st, i) => {
  const x = M + i * (bx + gap);
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: py, w: bx, h: bh2, rectRadius: 0.1, fill: { color: i === steps.length - 1 ? DARK : PANEL }, line: { color: i === steps.length - 1 ? DARK : LINE, width: 1 }, shadow: shadow() });
  s.addText(st[0], { x, y: py + 0.42, w: bx, h: 0.4, align: "center", fontFace: BODY, fontSize: 15, bold: true, color: i === steps.length - 1 ? WHITE : INK, margin: 0 });
  s.addText(st[1], { x, y: py + 0.84, w: bx, h: 0.3, align: "center", fontFace: BODY, fontSize: 11, color: i === steps.length - 1 ? "AEB8C7" : MUTED, margin: 0 });
  if (i < steps.length - 1) s.addShape(pres.shapes.LINE, { x: x + bx + 0.06, y: py + bh2 / 2, w: gap - 0.12, h: 0, line: { color: ACCENT, width: 2, endArrowType: "triangle" } });
});
s.addText("Runs on a weekly schedule (GitHub Actions) or on demand. The same metrics feed the email, this deck, and an HTML preview.",
  { x: M, y: 4.8, w: W - 2 * M, h: 0.6, align: "center", fontFace: BODY, fontSize: 13, color: MUTED, margin: 0 });
footer(s);

// =================================================================== 5 CLASSIFICATION
s = pres.addSlide(); s.background = { color: WHITE };
kicker(s, "How findings are classified"); title(s, "Three lenses on every finding");
const lenses = [
  ["By severity", "Critical · High · Medium · Low", "Aikido's severity, used for counts, the risk score and MTTR breakdowns.", [SEV.critical, SEV.high, SEV.medium, SEV.low]],
  ["By source / origin", "Code · Dependencies · Images · Secrets · Infra", "Where the risk comes from and how you fix it — insecure code (SAST), vulnerable libraries (SCA), CVEs in container images, leaked secrets, or IaC/cloud misconfig.", [SRC.code, SRC.dep, SRC.img, SRC.sec, SRC.infra]],
  ["By OWASP Top 10 (2021)", "A01 – A10", "Each finding is mapped to an OWASP category — by its CWE, or by Aikido type for component / config / secret findings.", [ACCENT, ACCENT, ACCENT, ACCENT, ACCENT]],
];
const lw = (W - 2 * M - 2 * 0.35) / 3, lh = 4.4, ly = 1.7;
lenses.forEach((l, i) => {
  const x = M + i * (lw + 0.35);
  card(s, x, ly, lw, lh, null);
  // row of color dots
  l[3].forEach((c, j) => s.addShape(pres.shapes.OVAL, { x: x + 0.3 + j * 0.32, y: ly + 0.32, w: 0.2, h: 0.2, fill: { color: c } }));
  s.addText(l[0], { x: x + 0.3, y: ly + 0.7, w: lw - 0.6, h: 0.5, fontFace: BODY, fontSize: 17, bold: true, color: INK, margin: 0 });
  s.addText(l[1], { x: x + 0.3, y: ly + 1.2, w: lw - 0.6, h: 0.5, fontFace: MONO, fontSize: 12, color: INK, margin: 0 });
  s.addText(l[2], { x: x + 0.3, y: ly + 1.75, w: lw - 0.6, h: lh - 2.0, fontFace: BODY, fontSize: 13, color: MUTED, margin: 0, valign: "top", lineSpacingMultiple: 1.1 });
});
footer(s);

// =================================================================== 6 KPI: EXPOSURE
s = pres.addSlide(); s.background = { color: WHITE };
kicker(s, "KPI catalog — 1 of 3"); title(s, "Exposure & risk");
const k1 = [
  ["Open backlog", "Count of currently-open findings, overall and per product.", ACCENT],
  ["Severity mix", "Open findings split by Critical / High / Medium / Low.", SEV.critical],
  ["Product risk score", "A single comparable number per product (formula below).", SEV.high],
  ["Risk & champion boards", "Two rankings: highest risk (act on) and best security hygiene (celebrate).", SRC.dep],
];
const kw = (W - 2 * M - 0.4) / 2, kh = 1.5;
k1.forEach((k, i) => { const x = M + (i % 2) * (kw + 0.4), y = 1.6 + Math.floor(i / 2) * (kh + 0.3); defCard(s, x, y, kw, kh, k[0], k[1], k[2]); });
// formula callouts: risk score (left) + champion score weighting (right)
const halfW = (W - 2 * M - 0.4) / 2, fx2 = M + halfW + 0.4;
s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: M, y: 5.05, w: halfW, h: 1.15, rectRadius: 0.08, fill: { color: DARK }, shadow: shadow() });
s.addText("RISK SCORE  (lower is better)", { x: M + 0.32, y: 5.22, w: halfW - 0.6, h: 0.3, fontFace: BODY, fontSize: 11, color: "7FA8FF", bold: true, charSpacing: 1.5, margin: 0 });
s.addText([
  { text: "10", options: { color: SEV.critical, bold: true } }, { text: "·Crit + ", options: { color: "AEB8C7" } },
  { text: "5", options: { color: SEV.high, bold: true } }, { text: "·High + ", options: { color: "AEB8C7" } },
  { text: "2", options: { color: SEV.medium, bold: true } }, { text: "·Med + ", options: { color: "AEB8C7" } },
  { text: "1", options: { color: SEV.low, bold: true } }, { text: "·Low", options: { color: "AEB8C7" } },
], { x: M + 0.32, y: 5.55, w: halfW - 0.6, h: 0.5, fontFace: MONO, fontSize: 16, margin: 0 });
s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: fx2, y: 5.05, w: halfW, h: 1.15, rectRadius: 0.08, fill: { color: "12361F" }, shadow: shadow() });
s.addText("\u{1F3C6}  CHAMPION SCORE  (higher is better)", { x: fx2 + 0.32, y: 5.22, w: halfW - 0.6, h: 0.3, fontFace: BODY, fontSize: 11, color: "7EE2A8", bold: true, charSpacing: 1.5, margin: 0 });
s.addText([
  { text: "30", options: { color: "7EE2A8", bold: true } }, { text: " MTTR + ", options: { color: "BFE9CE" } },
  { text: "30", options: { color: "7EE2A8", bold: true } }, { text: " SLA + ", options: { color: "BFE9CE" } },
  { text: "20", options: { color: "7EE2A8", bold: true } }, { text: " Closing + ", options: { color: "BFE9CE" } },
  { text: "20", options: { color: "7EE2A8", bold: true } }, { text: " Low-risk", options: { color: "BFE9CE" } },
], { x: fx2 + 0.32, y: 5.55, w: halfW - 0.6, h: 0.5, fontFace: MONO, fontSize: 16, margin: 0 });
footer(s);

// =================================================================== 7 KPI: REMEDIATION
s = pres.addSlide(); s.background = { color: WHITE };
kicker(s, "KPI catalog — 2 of 3"); title(s, "Remediation & SLA");
const k2 = [
  ["MTTR", "Time to remediate (mean & median, days) = closed − first detected.", ACCENT],
  ["MTTR by severity", "Median remediation time split by severity level.", SEV.high],
  ["MTTR by vuln type", "Which vulnerability types take longest to fix (persistence).", SRC.dep],
  ["SLA adherence", "Share of findings closed within Aikido's SLA target date.", "1A7F37"],
  ["Overdue", "Open findings already past their SLA remediation date.", SEV.critical],
  ["Aging buckets", "Open findings grouped by age: 0-7 / 8-30 / 31-90 / 90+ days.", SEV.medium],
];
const rw = (W - 2 * M - 2 * 0.35) / 3, rh = 1.95;
k2.forEach((k, i) => { const x = M + (i % 3) * (rw + 0.35), y = 1.7 + Math.floor(i / 3) * (rh + 0.3); defCard(s, x, y, rw, rh, k[0], k[1], k[2]); });
footer(s);

// =================================================================== 8 KPI: TREND & PATTERNS
s = pres.addSlide(); s.background = { color: WHITE };
kicker(s, "KPI catalog — 3 of 3"); title(s, "Trend, persistence & patterns");
const k3 = [
  ["Opened vs closed", "New vs resolved findings each week, and the net change.", ACCENT],
  ["Open backlog trend", "Backlog reconstructed at each week-end — a true time series.", SRC.img],
  ["Oldest open findings", "The longest-unresolved findings, ranked by age.", SEV.critical],
  ["Most repeated types", "The vulnerability types that recur most across products.", SEV.high],
  ["Top CWE classes", "Most common weakness types (e.g. CWE-79 XSS, CWE-89 SQLi).", SRC.dep],
  ["Top CVEs & packages", "Most frequent dependency CVEs and vulnerable packages.", SRC.code],
];
k3.forEach((k, i) => { const x = M + (i % 3) * (rw + 0.35), y = 1.7 + Math.floor(i / 3) * (rh + 0.3); defCard(s, x, y, rw, rh, k[0], k[1], k[2]); });
footer(s);

// =================================================================== 9 DELIVERY
s = pres.addSlide(); s.background = { color: WHITE };
kicker(s, "Delivery"); title(s, "Cadence, format & options");
const d = [
  ["Weekly, automated", "Runs every Monday via GitHub Actions (or on demand); secrets stay in your environment.", ACCENT],
  ["HTML email", "Sent to a recipient list over SMTP, with all charts embedded inline (plus a plain-text fallback).", SRC.code],
  ["Combined or per-workspace", "One consolidated email, or a separate report per Aikido workspace.", SRC.img],
  ["This deck & preview", "The same metrics also render to a PowerPoint and an HTML dry-run preview.", SRC.dep],
];
const dw = (W - 2 * M - 0.4) / 2, dh = 1.7;
d.forEach((k, i) => { const x = M + (i % 2) * (dw + 0.4), y = 1.7 + Math.floor(i / 2) * (dh + 0.35); defCard(s, x, y, dw, dh, k[0], k[1], k[2]); });
footer(s);

// =================================================================== 10 SCOPE & LIMITS
s = pres.addSlide(); s.background = { color: WHITE };
kicker(s, "Scope"); title(s, "What's included — and what isn't");
const colW = (W - 2 * M - 0.4) / 2;
card(s, M, 1.7, colW, 4.5, "1A7F37");
s.addText("Included", { x: M + 0.58, y: 1.92, w: colW - 0.9, h: 0.4, fontFace: BODY, fontSize: 16, bold: true, color: INK, margin: 0 });
s.addText([
  "Open backlog, severity & source mix",
  "Per-product risk score & leaderboard",
  "MTTR (overall, by severity, by type)",
  "SLA adherence & overdue findings",
  "Aging, opened/closed & backlog trend",
  "Oldest & most-repeated findings",
  "OWASP Top 10, CWE, CVE & packages",
].map((t, i, a) => ({ text: t, options: { bullet: { code: "2022", indent: 16 }, breakLine: true, paraSpaceAfter: 9, color: INK, fontFace: BODY, fontSize: 13.5 } })),
  { x: M + 0.35, y: 2.45, w: colW - 0.7, h: 3.6, valign: "top", margin: 0 });
const x2 = M + colW + 0.4;
card(s, x2, 1.7, colW, 4.5, MUTED);
s.addText("Not included (and why)", { x: x2 + 0.58, y: 1.92, w: colW - 0.9, h: 0.4, fontFace: BODY, fontSize: 16, bold: true, color: INK, margin: 0 });
s.addText([
  { text: "MTTD (time to detect)", options: { bold: true, color: INK, fontFace: BODY, fontSize: 13.5, breakLine: true } },
  { text: "No \u201cintroduced\u201d timestamp in the data — only detection.\n", options: { color: MUTED, fontFace: BODY, fontSize: 12.5, breakLine: true, paraSpaceAfter: 9 } },
  { text: "Reopen / recurrence rate", options: { bold: true, color: INK, fontFace: BODY, fontSize: 13.5, breakLine: true } },
  { text: "No reliable reopen signal in the export.\n", options: { color: MUTED, fontFace: BODY, fontSize: 12.5, breakLine: true, paraSpaceAfter: 9 } },
  { text: "Vulnerability density", options: { bold: true, color: INK, fontFace: BODY, fontSize: 13.5, breakLine: true } },
  { text: "Would need code-size / asset normalization Aikido doesn\u2019t provide.", options: { color: MUTED, fontFace: BODY, fontSize: 12.5, breakLine: true } },
], { x: x2 + 0.35, y: 2.45, w: colW - 0.7, h: 3.6, valign: "top", margin: 0 });
footer(s);

// =================================================================== 11 HOW TO READ (dark close)
s = pres.addSlide(); s.background = { color: DARK };
s.addText("USING THE REPORT", { x: M, y: 0.7, w: W - 2 * M, h: 0.3, fontFace: BODY, fontSize: 13, color: "7FA8FF", bold: true, charSpacing: 4, margin: 0 });
s.addText("How to read it each week", { x: M, y: 1.05, w: W - 2 * M, h: 0.7, fontFace: HEAD, fontSize: 30, color: WHITE, bold: true, margin: 0 });
const steps2 = [
  ["1", "Start with the leaderboard", "See which product carries the most risk this week."],
  ["2", "Triage criticals & overdue", "Act on critical/high findings and anything past SLA first."],
  ["3", "Check the origin split", "Route work: code \u2192 dev, images \u2192 platform, deps \u2192 upgrades."],
  ["4", "Watch the trend", "Opened-vs-closed and backlog tell you if you're gaining ground."],
];
steps2.forEach((st, i) => {
  const y = 2.2 + i * 1.05;
  s.addShape(pres.shapes.OVAL, { x: M, y, w: 0.6, h: 0.6, fill: { color: ACCENT } });
  s.addText(st[0], { x: M, y, w: 0.6, h: 0.6, align: "center", valign: "middle", fontFace: HEAD, fontSize: 22, bold: true, color: WHITE, margin: 0 });
  s.addText(st[1], { x: M + 0.95, y: y - 0.02, w: 10, h: 0.4, fontFace: BODY, fontSize: 18, bold: true, color: WHITE, margin: 0 });
  s.addText(st[2], { x: M + 0.95, y: y + 0.38, w: 10, h: 0.4, fontFace: BODY, fontSize: 13.5, color: "AEB8C7", margin: 0 });
});
s.addText("Generated by aikido-product-newsletter · data via the Aikido API", { x: M, y: H - 0.5, w: 10, h: 0.3, fontFace: BODY, fontSize: 10, color: "5C6678", margin: 0 });

pres.writeFile({ fileName: outPath }).then(() => console.log("wrote " + outPath));
