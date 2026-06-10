/*
 * Build a Product Security Newsletter deck from a report.json
 * (produced by `python -m main ... --save-json`).
 *
 *   node pptx/build_deck.js <report.json> <out.pptx>
 *
 * Charts are native PowerPoint charts (editable), not images.
 */
const fs = require("fs");
const pptxgen = require("pptxgenjs");

const [, , reportPath = "out/report.json", outPath = "out/newsletter.pptx"] = process.argv;
const R = JSON.parse(fs.readFileSync(reportPath, "utf8"));

// ---- palette -------------------------------------------------------------
const DARK = "0E1726", PANEL = "F4F6F9", INK = "1A1D24", MUTED = "5B6470";
const LINE = "E4E7EC", ACCENT = "2F6DF6", WHITE = "FFFFFF";
const SEV = { critical: "F85149", high: "FB8500", medium: "D4A200", low: "58A6FF" };
const SRC = {
  "Code (SAST)": "2F6DF6", "Dependencies (SCA)": "8957E5", "Container images": "1F9AA8",
  "Secrets": "F85149", "Infrastructure": "D4760A", "Other": "8B949E",
};
const SOURCE_ORDER = ["Code (SAST)", "Dependencies (SCA)", "Container images", "Secrets", "Infrastructure", "Other"];

const HEAD = "Cambria";        // safe serif header
const BODY = "Calibri";        // safe sans body
const MONO = "Consolas";

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";   // 13.33 x 7.5
pres.author = "aikido-product-newsletter";
pres.title = "Product Security Newsletter";
const W = 13.33, H = 7.5, M = 0.6;

const dt = (s) => new Date(s * 1000).toLocaleDateString("en-US", { month: "short", day: "2-digit", year: "numeric" });
const clean = (s) => String(s).replace(/\*/g, "");
const products = Object.values(R.products).sort((a, b) => b.risk_score - a.risk_score);
const ov = R.overall;
const overdue = products.reduce((a, p) => a + (p.overdue_open || 0), 0);
const net = ov.opened_this_period - ov.closed_this_period;
const shadow = () => ({ type: "outer", color: "20304A", blur: 8, offset: 2, angle: 90, opacity: 0.18 });

// ---- helpers -------------------------------------------------------------
function kicker(slide, text, color = ACCENT) {
  slide.addText(text.toUpperCase(), {
    x: M, y: 0.42, w: W - 2 * M, h: 0.3, fontFace: BODY, fontSize: 12,
    color, bold: true, charSpacing: 3, margin: 0,
  });
}
function title(slide, text) {
  slide.addText(text, {
    x: M, y: 0.7, w: W - 2 * M, h: 0.7, fontFace: HEAD, fontSize: 30,
    color: INK, bold: true, margin: 0,
  });
}
let _pg = 1;
function footer(slide) {
  _pg++;
  slide.addText([
    { text: "Product Security Newsletter", options: { color: MUTED } },
    { text: "    ·    data via Aikido", options: { color: "9AA4B2" } },
  ], { x: M, y: H - 0.45, w: 8, h: 0.3, fontFace: BODY, fontSize: 9, margin: 0 });
  slide.addText(String(_pg), { x: W - 1.1, y: H - 0.45, w: 0.5, h: 0.3, fontFace: BODY, fontSize: 9, color: MUTED, align: "right" });
}
const cap = (s) => s[0].toUpperCase() + s.slice(1);
function chartBase(extra) {
  return Object.assign({
    chartArea: { fill: { color: WHITE } }, plotArea: { fill: { color: WHITE } },
    catAxisLabelColor: MUTED, valAxisLabelColor: MUTED,
    catAxisLabelFontFace: BODY, valAxisLabelFontFace: BODY,
    catAxisLabelFontSize: 11, valAxisLabelFontSize: 10,
    valGridLine: { color: LINE, size: 0.5 }, catGridLine: { style: "none" },
    showTitle: false,
  }, extra);
}

// ========================================================================
// 1) TITLE (dark)
// ========================================================================
let s = pres.addSlide();
s.background = { color: DARK };
s.addText("PRODUCT SECURITY", { x: M, y: 2.25, w: W - 2 * M, h: 0.5, fontFace: BODY, fontSize: 16, color: "7FA8FF", bold: true, charSpacing: 5, margin: 0 });
s.addText("Security Newsletter", { x: M, y: 2.7, w: W - 2 * M, h: 1.1, fontFace: HEAD, fontSize: 54, color: WHITE, bold: true, margin: 0 });
s.addText(`${dt(R.window_start)}  –  ${dt(R.generated_at)}      ·      ${products.length} products      ·      ${R.window_days}-day window`,
  { x: M, y: 3.95, w: W - 2 * M, h: 0.4, fontFace: BODY, fontSize: 15, color: "AEB8C7", margin: 0 });
// mini stat row
const mini = [["Open issues", ov.open], ["Critical", ov.severity_open.critical], ["High", ov.severity_open.high], ["Past SLA", overdue]];
mini.forEach(([lab, val], i) => {
  const x = M + i * 2.5;
  s.addText(String(val), { x, y: 4.75, w: 2.3, h: 0.7, fontFace: HEAD, fontSize: 40, color: i === 1 ? SEV.critical : WHITE, bold: true, margin: 0 });
  s.addText(lab.toUpperCase(), { x, y: 5.5, w: 2.3, h: 0.3, fontFace: BODY, fontSize: 11, color: "8B95A5", charSpacing: 2, margin: 0 });
});
s.addText("Generated from Aikido · per-product (Product:* teams)", { x: M, y: H - 0.6, w: 9, h: 0.3, fontFace: BODY, fontSize: 10, color: "5C6678", margin: 0 });

// ========================================================================
// 2) EXECUTIVE SUMMARY (stat cards)
// ========================================================================
s = pres.addSlide(); s.background = { color: WHITE };
kicker(s, "Executive summary");
title(s, "Where we stand this period");
const cards = [
  ["Open issues", String(ov.open), "", INK],
  ["Critical / High", `${ov.severity_open.critical} / ${ov.severity_open.high}`, "open", SEV.critical],
  ["Past SLA", String(overdue), "overdue", SEV.high],
  ["Median MTTR", ov.mttr_all.median == null ? "—" : String(ov.mttr_all.median), "days to remediate", ACCENT],
  ["Opened / Closed", `${ov.opened_this_period} / ${ov.closed_this_period}`, "this period", INK],
  ["Net backlog", (net > 0 ? "+" : "") + net, net > 0 ? "growing" : "shrinking", net > 0 ? SEV.critical : "1A7F37"],
];
const cw = (W - 2 * M - 2 * 0.4) / 3, ch = 1.85;
cards.forEach((c, i) => {
  const col = i % 3, row = Math.floor(i / 3);
  const x = M + col * (cw + 0.4), y = 1.7 + row * (ch + 0.35);
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w: cw, h: ch, rectRadius: 0.08, fill: { color: PANEL }, line: { color: LINE, width: 1 }, shadow: shadow() });
  s.addText(c[0].toUpperCase(), { x: x + 0.3, y: y + 0.25, w: cw - 0.6, h: 0.3, fontFace: BODY, fontSize: 12, color: MUTED, bold: true, charSpacing: 1.5, margin: 0 });
  s.addText(c[1], { x: x + 0.28, y: y + 0.62, w: cw - 0.56, h: 0.85, fontFace: HEAD, fontSize: 44, color: c[3], bold: true, margin: 0 });
  if (c[2]) s.addText(c[2], { x: x + 0.3, y: y + 1.45, w: cw - 0.6, h: 0.3, fontFace: BODY, fontSize: 12, color: MUTED, margin: 0 });
});
footer(s);

// ========================================================================
// 3) RISK LEADERBOARD (bar chart + table)
// ========================================================================
s = pres.addSlide(); s.background = { color: WHITE };
kicker(s, "Product comparison");
title(s, "Product risk leaderboard");
s.addText("Risk score = 10·Critical + 5·High + 2·Medium + 1·Low (open issues)", { x: M, y: 1.5, w: 11, h: 0.3, fontFace: BODY, fontSize: 12, color: MUTED, margin: 0 });
const lb = R.leaderboard.slice().reverse();
s.addChart(pres.charts.BAR, [{ name: "Risk", labels: lb.map(b => b.name), values: lb.map(b => b.risk_score) }],
  chartBase({ x: M, y: 1.95, w: 6.6, h: 4.8, barDir: "bar", chartColors: [ACCENT], showValue: true, dataLabelPosition: "outEnd", dataLabelColor: INK, dataLabelFontFace: BODY, dataLabelFontSize: 11, showLegend: false }));
// table on the right
const head = ["Product", "Risk", "C", "H", "SLA!", "MTTR"].map(t => ({ text: t, options: { fill: { color: DARK }, color: WHITE, bold: true, fontFace: BODY, fontSize: 11, align: "center" } }));
const rows = R.leaderboard.map(b => [
  { text: b.name, options: { fontFace: BODY, fontSize: 11, color: INK, align: "left" } },
  { text: String(b.risk_score), options: { fontFace: MONO, fontSize: 11, bold: true, align: "center" } },
  { text: String(b.open_critical), options: { fontFace: MONO, fontSize: 11, color: SEV.critical, align: "center" } },
  { text: String(b.open_high), options: { fontFace: MONO, fontSize: 11, color: SEV.high, align: "center" } },
  { text: String(b.overdue), options: { fontFace: MONO, fontSize: 11, align: "center" } },
  { text: b.mttr_median == null ? "—" : b.mttr_median + "d", options: { fontFace: MONO, fontSize: 11, align: "center" } },
]);
s.addTable([head, ...rows], { x: 7.5, y: 1.95, w: 5.2, colW: [2.15, 0.65, 0.5, 0.5, 0.65, 0.75], border: { type: "solid", pt: 0.5, color: LINE }, align: "center", valign: "middle", rowH: 0.4, fill: { color: WHITE } });
footer(s);

// ========================================================================
// 4) SEVERITY BY PRODUCT (stacked bar)
// ========================================================================
s = pres.addSlide(); s.background = { color: WHITE };
kicker(s, "Exposure");
title(s, "Open issues by severity, per product");
const pr = products.slice().reverse();
const sevSeries = ["critical", "high", "medium", "low"].map(sev => ({ name: sev[0].toUpperCase() + sev.slice(1), labels: pr.map(p => p.name), values: pr.map(p => p.severity_open[sev]) }));
s.addChart(pres.charts.BAR, sevSeries, chartBase({
  x: M, y: 1.7, w: W - 2 * M, h: 4.9, barDir: "bar", barGrouping: "stacked",
  chartColors: [SEV.critical, SEV.high, SEV.medium, SEV.low],
  showLegend: true, legendPos: "b", legendColor: MUTED, legendFontFace: BODY, legendFontSize: 11,
  showValue: false,
}));
footer(s);

// ========================================================================
// 5) FINDINGS BY SOURCE / ORIGIN (doughnut + per-product stacked)
// ========================================================================
s = pres.addSlide(); s.background = { color: WHITE };
kicker(s, "Root cause");
title(s, "Where the findings come from");
s.addText([
  { text: "Code (SAST)", options: { color: SRC["Code (SAST)"], bold: true } },
  { text: " = insecure code we wrote      ", options: { color: MUTED } },
  { text: "Container images", options: { color: SRC["Container images"], bold: true } },
  { text: " = CVEs in images we run      ", options: { color: MUTED } },
  { text: "Dependencies (SCA)", options: { color: SRC["Dependencies (SCA)"], bold: true } },
  { text: " = vulnerable libraries", options: { color: MUTED } },
], { x: M, y: 1.5, w: W - 2 * M, h: 0.35, fontFace: BODY, fontSize: 12, margin: 0 });
const srcCats = SOURCE_ORDER.filter(c => (ov.source_open[c] || 0) > 0);
s.addChart(pres.charts.DOUGHNUT, [{ name: "Source", labels: srcCats, values: srcCats.map(c => ov.source_open[c]) }],
  chartBase({ x: M, y: 2.1, w: 4.8, h: 4.5, chartColors: srcCats.map(c => SRC[c]), holeSize: 58, showLegend: true, legendPos: "b", legendColor: MUTED, legendFontFace: BODY, legendFontSize: 10, showValue: false, dataLabelColor: WHITE, dataLabelFontFace: BODY, dataLabelFontSize: 10, showPercent: true, valAxisHidden: true, catAxisHidden: true, valGridLine: { style: "none" } }));
const srcSeries = srcCats.map(c => ({ name: c, labels: pr.map(p => p.name), values: pr.map(p => (p.source_open && p.source_open[c]) || 0) }));
s.addChart(pres.charts.BAR, srcSeries, chartBase({
  x: 5.7, y: 2.1, w: W - 5.7 - M, h: 4.5, barDir: "bar", barGrouping: "stacked",
  chartColors: srcCats.map(c => SRC[c]), showLegend: false,
}));
footer(s);

// ========================================================================
// OWASP TOP 10 (2021) RISK
// ========================================================================
s = pres.addSlide(); s.background = { color: WHITE };
kicker(s, "Risk framework");
title(s, "Risk by OWASP Top 10 (2021)");
s.addText("Open findings mapped to OWASP categories (by CWE, or by type for components/config/secrets), stacked by severity.",
  { x: M, y: 1.5, w: W - 2 * M, h: 0.3, fontFace: BODY, fontSize: 12, color: MUTED, margin: 0 });
const ow = R.owasp || {};
const owCats = Object.keys(ow).sort((a, b) => ow[a].count - ow[b].count); // asc -> largest on top
const owSeries = ["critical", "high", "medium", "low"].map(sev => ({ name: cap(sev), labels: owCats, values: owCats.map(c => ow[c][sev] || 0) }));
s.addChart(pres.charts.BAR, owSeries, chartBase({
  x: M, y: 1.95, w: W - 2 * M, h: 4.7, barDir: "bar", barGrouping: "stacked",
  chartColors: [SEV.critical, SEV.high, SEV.medium, SEV.low],
  showLegend: true, legendPos: "b", legendColor: MUTED, legendFontFace: BODY, legendFontSize: 11,
}));
footer(s);
s = pres.addSlide(); s.background = { color: WHITE };
kicker(s, "Remediation health");
title(s, "How fast we fix, and what's aging");
const sevs = ["critical", "high", "medium", "low"];
s.addText("Median time-to-remediate by severity (days)", { x: M, y: 1.55, w: 6, h: 0.3, fontFace: BODY, fontSize: 12, color: MUTED, margin: 0 });
s.addChart(pres.charts.BAR, [{ name: "Days", labels: sevs.map(x => x[0].toUpperCase() + x.slice(1)), values: sevs.map(x => (ov.mttr_by_sev[x] && ov.mttr_by_sev[x].median) || 0) }],
  chartBase({ x: M, y: 1.9, w: 6.1, h: 2.4, barDir: "col", chartColors: [SEV.critical, SEV.high, SEV.medium, SEV.low], showValue: true, dataLabelPosition: "outEnd", dataLabelColor: INK, dataLabelFontFace: BODY, dataLabelFontSize: 11, showLegend: false }));
const ageOrder = ["0-7", "8-30", "31-90", "90+"];
const ageAgg = ageOrder.map(b => products.reduce((a, p) => a + ((p.aging && p.aging[b]) || 0), 0));
s.addText("Open-issue aging (days open)", { x: M, y: 4.45, w: 6, h: 0.3, fontFace: BODY, fontSize: 12, color: MUTED, margin: 0 });
s.addChart(pres.charts.BAR, [{ name: "Open", labels: ageOrder.map(b => b + "d"), values: ageAgg }],
  chartBase({ x: M, y: 4.8, w: 6.1, h: 2.0, barDir: "col", chartColors: ["3FB950", "D4A200", SEV.high, SEV.critical], showValue: true, dataLabelPosition: "outEnd", dataLabelColor: INK, dataLabelFontFace: BODY, dataLabelFontSize: 11, showLegend: false }));
// SLA callouts on the right
const slaPct = (() => { let inSla = 0, withSla = 0; for (const p of products) { if (p.sla) { inSla += p.sla.closed_in_sla; withSla += p.sla.closed_with_sla; } } return withSla ? Math.round(100 * inSla / withSla) : null; })();
const big = [["SLA adherence", slaPct == null ? "—" : slaPct + "%", "closed within target", slaPct != null && slaPct >= 80 ? "1A7F37" : SEV.high],
["Currently overdue", String(overdue), "past remediation date", SEV.critical]];
big.forEach(([lab, val, sub, col], i) => {
  const x = 7.4, y = 1.9 + i * 2.45, w = W - 7.4 - M, h = 2.1;
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.08, fill: { color: PANEL }, line: { color: LINE, width: 1 }, shadow: shadow() });
  s.addText(lab.toUpperCase(), { x: x + 0.3, y: y + 0.3, w: w - 0.6, h: 0.3, fontFace: BODY, fontSize: 12, color: MUTED, bold: true, charSpacing: 1.5, margin: 0 });
  s.addText(val, { x: x + 0.28, y: y + 0.7, w: w - 0.56, h: 0.95, fontFace: HEAD, fontSize: 52, color: col, bold: true, margin: 0 });
  s.addText(sub, { x: x + 0.3, y: y + 1.62, w: w - 0.6, h: 0.3, fontFace: BODY, fontSize: 12, color: MUTED, margin: 0 });
});
footer(s);

// ========================================================================
// PERSISTENCE & RECURRENCE (MTTR by type + oldest + most repeated)
// ========================================================================
s = pres.addSlide(); s.background = { color: WHITE };
kicker(s, "Persistence & recurrence");
title(s, "What lingers, and what keeps coming back");
s.addText("Slowest vulnerability types to remediate (median MTTR, days)", { x: M, y: 1.55, w: 6.5, h: 0.3, fontFace: BODY, fontSize: 12, color: MUTED, margin: 0 });
const byType = (R.mttr_by_type || []).slice(0, 7).reverse();
s.addChart(pres.charts.BAR, [{ name: "Median days", labels: byType.map(d => `${d.type.slice(0, 26)} (n=${d.n})`), values: byType.map(d => d.median) }],
  chartBase({ x: M, y: 1.9, w: 6.7, h: 4.8, barDir: "bar", chartColors: ["D29922"], showValue: true, dataLabelPosition: "outEnd", dataLabelColor: INK, dataLabelFontFace: BODY, dataLabelFontSize: 11, showLegend: false }));
// oldest findings table (right)
const ox = 7.5, ow2 = W - 7.5 - M;
s.addText("OLDEST OPEN FINDINGS", { x: ox, y: 1.55, w: ow2, h: 0.3, fontFace: BODY, fontSize: 12, color: MUTED, bold: true, charSpacing: 1.5, margin: 0 });
const oHead = ["Age", "Finding", "Sev", "Product"].map(t => ({ text: t, options: { fill: { color: DARK }, color: WHITE, bold: true, fontFace: BODY, fontSize: 10 } }));
const oRows = (R.oldest_open || []).slice(0, 6).map(c => [
  { text: (c.age_days ?? "—") + "d", options: { fontFace: MONO, fontSize: 10, color: SEV.critical, bold: true } },
  { text: c.rule, options: { fontFace: BODY, fontSize: 10, color: INK } },
  { text: c.severity, options: { fontFace: BODY, fontSize: 9, color: SEV[c.severity] || INK, bold: true } },
  { text: c.product, options: { fontFace: BODY, fontSize: 10, color: MUTED } },
]);
s.addTable([oHead, ...oRows], { x: ox, y: 1.9, w: ow2, colW: [0.7, 2.4, 0.85, 1.43], border: { type: "solid", pt: 0.5, color: LINE }, valign: "middle", rowH: 0.42, fill: { color: WHITE } });
s.addText("MOST REPEATED VULNERABILITY TYPES", { x: ox, y: 4.95, w: ow2, h: 0.3, fontFace: BODY, fontSize: 12, color: MUTED, bold: true, charSpacing: 1.5, margin: 0 });
const rep = (R.top_vuln_types || []).slice(0, 6);
const repRuns = rep.flatMap(([t, n]) => [
  { text: t, options: { fontFace: BODY, fontSize: 12, color: INK, breakLine: false } },
  { text: `  ×${n}`, options: { fontFace: BODY, fontSize: 12, color: SEV.high, bold: true, breakLine: true } },
]);
s.addText(repRuns.length ? repRuns : [{ text: "—" }], { x: ox, y: 5.35, w: ow2, h: 1.35, valign: "top", margin: 0, paraSpaceAfter: 3 });
footer(s);

// ========================================================================
// 7) TREND (combo: opened/closed columns + backlog line)
// ========================================================================
s = pres.addSlide(); s.background = { color: WHITE };
kicker(s, "Trend");
title(s, `Opened vs closed, with open backlog`);
const t = R.trend;
s.addChart([
  { type: pres.charts.BAR, data: [{ name: "Opened", labels: t.weeks, values: t.opened }, { name: "Closed", labels: t.weeks, values: t.closed }], options: { barDir: "col", chartColors: [SEV.high, "3FB950"] } },
  { type: pres.charts.LINE, data: [{ name: "Open backlog", labels: t.weeks, values: t.backlog }], options: { chartColors: [ACCENT], lineSize: 3, lineSmooth: true, secondaryValAxis: true, secondaryCatAxis: true } },
], chartBase({
  x: M, y: 1.8, w: W - 2 * M, h: 4.9,
  showLegend: true, legendPos: "b", legendColor: MUTED, legendFontFace: BODY, legendFontSize: 11,
  valAxes: [
    { valAxisLabelColor: MUTED, valAxisLabelFontFace: BODY, valAxisLabelFontSize: 10, valGridLine: { color: LINE, size: 0.5 }, valAxisTitle: "Issues / week", showValAxisTitle: true, valAxisTitleColor: MUTED, valAxisTitleFontSize: 11 },
    { valAxisLabelColor: ACCENT, valAxisLabelFontFace: BODY, valAxisLabelFontSize: 10, valGridLine: { style: "none" }, valAxisTitle: "Open backlog", showValAxisTitle: true, valAxisTitleColor: ACCENT, valAxisTitleFontSize: 11 },
  ],
  catAxes: [
    { catAxisLabelColor: MUTED, catAxisLabelFontFace: BODY, catAxisLabelFontSize: 9 },
    { catAxisHidden: true },
  ],
}));
footer(s);

// ========================================================================
// 8) MOST CRITICAL OPEN FINDINGS (table)
// ========================================================================
s = pres.addSlide(); s.background = { color: WHITE };
kicker(s, "Act now");
title(s, "Most critical open findings");
const th = ["Severity", "Finding", "Product", "Repo / asset", "CVE / package", "Age", ""].map(t => ({ text: t, options: { fill: { color: DARK }, color: WHITE, bold: true, fontFace: BODY, fontSize: 11 } }));
const crit = R.top_critical_issues.slice(0, 8).map(c => [
  { text: c.severity, options: { fontFace: BODY, fontSize: 11, color: SEV[c.severity] || INK, bold: true } },
  { text: clean(c.rule), options: { fontFace: BODY, fontSize: 11, color: INK } },
  { text: c.product, options: { fontFace: BODY, fontSize: 11, color: INK } },
  { text: c.repo || "—", options: { fontFace: MONO, fontSize: 10, color: MUTED } },
  { text: c.cve || c.package || "—", options: { fontFace: MONO, fontSize: 10, color: MUTED } },
  { text: (c.age_days ?? "—") + "d", options: { fontFace: MONO, fontSize: 10, color: INK } },
  { text: c.overdue ? "OVERDUE" : "", options: { fontFace: BODY, fontSize: 9, color: SEV.critical, bold: true } },
]);
s.addTable([th, ...crit], { x: M, y: 1.7, w: W - 2 * M, colW: [1.1, 3.7, 1.7, 2.0, 2.1, 0.7, 0.83], border: { type: "solid", pt: 0.5, color: LINE }, valign: "middle", rowH: 0.55, fill: { color: WHITE } });
footer(s);

// ========================================================================
// 9) TOP WEAKNESSES (CWE bar + packages list)
// ========================================================================
s = pres.addSlide(); s.background = { color: WHITE };
kicker(s, "Patterns");
title(s, "Most common weaknesses & packages");
const cwes = (R.top_cwes || []).slice(0, 7).reverse();
s.addText("Top CWE classes (open findings)", { x: M, y: 1.55, w: 6, h: 0.3, fontFace: BODY, fontSize: 12, color: MUTED, margin: 0 });
s.addChart(pres.charts.BAR, [{ name: "Findings", labels: cwes.map(c => c[0]), values: cwes.map(c => c[1]) }],
  chartBase({ x: M, y: 1.9, w: 6.6, h: 4.7, barDir: "bar", chartColors: ["8957E5"], showValue: true, dataLabelPosition: "outEnd", dataLabelColor: INK, dataLabelFontFace: BODY, dataLabelFontSize: 11, showLegend: false }));
// packages / CVEs list card
const px = 7.6, pw = W - 7.6 - M;
s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: px, y: 1.9, w: pw, h: 4.7, rectRadius: 0.06, fill: { color: PANEL }, line: { color: LINE, width: 1 }, shadow: shadow() });
s.addText("TOP VULNERABLE PACKAGES", { x: px + 0.3, y: 2.15, w: pw - 0.6, h: 0.3, fontFace: BODY, fontSize: 12, color: MUTED, bold: true, charSpacing: 1.5, margin: 0 });
const pkgs = (R.top_packages || []).slice(0, 5);
const pkgRuns = pkgs.length ? pkgs.flatMap(([p, n]) => [
  { text: p, options: { fontFace: MONO, fontSize: 13, color: INK, breakLine: false } },
  { text: `   ×${n}`, options: { fontFace: BODY, fontSize: 13, color: SEV.high, bold: true, breakLine: true } },
]) : [{ text: "—", options: { fontFace: BODY, color: MUTED } }];
s.addText(pkgRuns, { x: px + 0.3, y: 2.55, w: pw - 0.6, h: 1.7, valign: "top", margin: 0, paraSpaceAfter: 5 });
s.addText("TOP CVEs", { x: px + 0.3, y: 4.4, w: pw - 0.6, h: 0.3, fontFace: BODY, fontSize: 12, color: MUTED, bold: true, charSpacing: 1.5, margin: 0 });
const cves = (R.top_cves || []).slice(0, 4);
const cveRuns = cves.length ? cves.flatMap(([c, n]) => [
  { text: c, options: { fontFace: MONO, fontSize: 12, color: INK, breakLine: false } },
  { text: `   ×${n}`, options: { fontFace: BODY, fontSize: 12, color: SEV.critical, bold: true, breakLine: true } },
]) : [{ text: "—", options: { fontFace: BODY, color: MUTED } }];
s.addText(cveRuns, { x: px + 0.3, y: 4.8, w: pw - 0.6, h: 1.6, valign: "top", margin: 0, paraSpaceAfter: 5 });
footer(s);

// ========================================================================
// 10) INSIGHTS & TAKEAWAYS (dark close)
// ========================================================================
s = pres.addSlide(); s.background = { color: DARK };
s.addText("KEY TAKEAWAYS", { x: M, y: 0.7, w: W - 2 * M, h: 0.3, fontFace: BODY, fontSize: 13, color: "7FA8FF", bold: true, charSpacing: 4, margin: 0 });
s.addText("What the data is telling us", { x: M, y: 1.05, w: W - 2 * M, h: 0.7, fontFace: HEAD, fontSize: 30, color: WHITE, bold: true, margin: 0 });
const ins = (R.insights || []).map(t => ({ text: clean(t), options: { bullet: { code: "2022", indent: 18 }, color: "DCE3EC", fontFace: BODY, fontSize: 13, paraSpaceAfter: 6, breakLine: true } }));
s.addText(ins, { x: M, y: 1.85, w: W - 2 * M, h: 4.95, valign: "top", margin: 0 });
s.addText("Generated by aikido-product-newsletter · data via the Aikido API", { x: M, y: H - 0.4, w: 10, h: 0.3, fontFace: BODY, fontSize: 10, color: "5C6678", margin: 0 });

pres.writeFile({ fileName: outPath }).then(() => console.log("wrote " + outPath));
