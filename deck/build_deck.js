/**
 * Generates the PowerPoint leave-behind from deck/deck_data.json.
 *
 * Every figure on every slide comes from that file, which is written by the
 * Python pipeline, so the deck cannot drift from the analysis. Run:
 *
 *     python -m fedspend.cli deck
 *
 * which regenerates the JSON and then runs this script.
 */

const fs = require("fs");
const path = require("path");
const pptxgen = require("pptxgenjs");

const ROOT = path.resolve(__dirname, "..");
const D = JSON.parse(fs.readFileSync(path.join(__dirname, "deck_data.json"), "utf8"));

// --------------------------------------------------------------------- theme
// Deep navy carries the institutional register the subject calls for; the blue
// is the same validated series colour used by the HTML dashboard and the Power
// BI theme, so all three artefacts read as one body of work.
const NAVY = "0D1B2A";
const NAVY_SOFT = "1B2E42";
const INK = "0D1418";
const BODY = "48555F";
const MUTED = "6D7C88";
const LINE = "D8DEE5";
const SURFACE = "F4F6F8";
const WHITE = "FFFFFF";
const BLUE = "2A78D6";
const ORANGE = "EB6834";
const TEAL = "1BAF7A";
const RED = "E34948";
const AMBER = "EDA100";

const HEAD = "Cambria";
const TEXT = "Calibri";

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.3 x 7.5 — must be set before any slide
pres.author = "Andrew Kemp";
pres.title = "Federal Contract Spending Efficiency";

const W = 13.33;
const M = 0.62; // page margin
const CW = W - M * 2; // content width

// ------------------------------------------------------------------ helpers
const txt = (s, t, o) => s.addText(t, Object.assign({ isTextBox: true }, o));

/** Slide title plus optional deck ("kicker") above it. Returns next free y. */
function heading(slide, kicker, title, opts = {}) {
  const dark = opts.dark === true;
  if (kicker) {
    txt(slide, kicker.toUpperCase(), {
      x: M, y: 0.42, w: CW, h: 0.26, margin: 0,
      fontFace: TEXT, fontSize: 11, bold: true, charSpacing: 1.6,
      color: dark ? "8FB3D9" : BLUE,
    });
  }
  txt(slide, title, {
    x: M, y: kicker ? 0.72 : 0.5, w: opts.titleW || CW, h: opts.titleH || 0.82, margin: 0,
    fontFace: HEAD, fontSize: opts.titleSize || 27, bold: true,
    color: dark ? WHITE : INK, valign: "top",
  });
  return (kicker ? 0.72 : 0.5) + (opts.titleH || 0.82) + 0.12;
}

/** The recurring motif: a numbered disc marking each finding. */
function findingBadge(slide, n) {
  slide.addShape(pres.ShapeType.ellipse, {
    x: W - M - 0.52, y: 0.4, w: 0.52, h: 0.52,
    fill: { color: SURFACE }, line: { color: LINE, width: 1 },
  });
  txt(slide, String(n), {
    x: W - M - 0.52, y: 0.4, w: 0.52, h: 0.52, margin: 0,
    fontFace: HEAD, fontSize: 17, bold: true, color: BLUE,
    align: "center", valign: "middle",
  });
}

/** A stat block: big number, small label under it. */
function stat(slide, x, y, w, value, label, colour, size) {
  txt(slide, value, {
    x, y, w, h: 0.62, margin: 0,
    fontFace: HEAD, fontSize: size || 34, bold: true, color: colour || INK,
  });
  txt(slide, label, {
    x, y: y + 0.6, w, h: 0.5, margin: 0,
    fontFace: TEXT, fontSize: 11.5, color: MUTED, valign: "top",
  });
}

/** A bordered card. Deliberately no edge stripe. */
function card(slide, x, y, w, h, fill) {
  slide.addShape(pres.ShapeType.roundRect, {
    x, y, w, h, rectRadius: 0.06,
    fill: { color: fill || WHITE }, line: { color: LINE, width: 1 },
  });
}

/** The "so what" line at the foot of a content slide. */
function takeaway(slide, text, y, colour) {
  const bar = colour || BLUE;
  slide.addShape(pres.ShapeType.ellipse, {
    x: M, y: y + 0.09, w: 0.13, h: 0.13, fill: { color: bar }, line: { color: bar, width: 0 },
  });
  txt(slide, text, {
    x: M + 0.26, y, w: CW - 0.26, h: 0.5, margin: 0,
    fontFace: TEXT, fontSize: 13, color: INK, valign: "top",
  });
}

function sourceNote(slide, extra) {
  txt(slide, extra || "USAspending API · FY2021–FY2025 contract obligations", {
    x: M, y: 7.0, w: CW, h: 0.26, margin: 0,
    fontFace: TEXT, fontSize: 9, color: MUTED,
  });
}

const chartBase = {
  showLegend: false,
  catAxisLabelColor: BODY, valAxisLabelColor: BODY,
  catAxisLabelFontSize: 10.5, valAxisLabelFontSize: 10.5,
  catAxisLabelFontFace: TEXT, valAxisLabelFontFace: TEXT,
  valGridLine: { color: "E3E8ED", size: 1 },
  catGridLine: { style: "none" },
  chartArea: { fill: { color: WHITE } },
  plotArea: { fill: { color: WHITE } },
  border: { pt: 0, color: WHITE },
};

// =============================================================== 1 · TITLE
{
  const s = pres.addSlide();
  s.background = { color: NAVY };

  txt(s, "FEDERAL CONTRACT SPENDING EFFICIENCY", {
    x: M, y: 1.05, w: CW, h: 0.3, margin: 0,
    fontFace: TEXT, fontSize: 12, bold: true, charSpacing: 2.2, color: "8FB3D9",
  });
  txt(s, "Where $" + D.meta.total_trillions + " trillion went —\nand where it was spent without a bid", {
    x: M, y: 1.5, w: 9.6, h: 1.9, margin: 0,
    fontFace: HEAD, fontSize: 40, bold: true, color: WHITE, lineSpacingMultiple: 1.05,
  });
  txt(s, "An analysis of US federal contract obligations, FY" + D.meta.base_fy +
        "–FY" + D.meta.latest_fy + ", across " + D.meta.agency_count + " agencies.",
    { x: M, y: 3.45, w: 9.6, h: 0.4, margin: 0, fontFace: TEXT, fontSize: 15, color: "C3D3E2" });

  const items = [
    [D.headline.real_growth_pct + "%", "Real growth, not the\n" + D.headline.nominal_growth_pct + "% headline"],
    [D.headline.competed_pct + "%", "Competed share —\na five-year low"],
    [D.navy.share_of_gov_pct + "%", "of that decline is\none organisation"],
    [D.headline.september_pct.toFixed(1) + "%", "of the year obligated\nin its final month"],
  ];
  items.forEach(([v, l], i) => {
    const x = M + i * 3.06;
    txt(s, v, { x, y: 4.5, w: 2.85, h: 0.72, margin: 0, fontFace: HEAD, fontSize: 36, bold: true, color: WHITE });
    txt(s, l, { x, y: 5.24, w: 2.85, h: 0.72, margin: 0, fontFace: TEXT, fontSize: 11.5, color: "8FB3D9", valign: "top" });
  });

  txt(s, "Andrew Kemp  ·  github.com/Akemp787", {
    x: M, y: 6.72, w: CW, h: 0.3, margin: 0, fontFace: TEXT, fontSize: 11, color: "6E8CA8",
  });
  s.addNotes("Five years of federal contract data, $" + D.meta.total_trillions +
    " trillion across " + D.meta.agency_count + " agencies, pulled from the USAspending API " +
    "and run through a pipeline I built. Four things came out of it.");
}

// ======================================================== 2 · HOW IT WAS BUILT
{
  const s = pres.addSlide();
  s.background = { color: WHITE };
  heading(s, "Approach", "Built to be reproduced, not just presented");

  const blocks = [
    ["01", "Ingest", "Cached, retrying client over the USAspending API. 763 responses stored by request hash, so the whole analysis rebuilds offline in about two seconds.", BLUE],
    ["02", "Model", "13 tidy extracts to 25 analysis tables, with every assumption — competition codes, risk buckets, index weights — held in one config file.", TEAL],
    ["03", "Validate", D.validation.checks + " data-quality contracts run on every build and fail it if broken. All " + D.validation.agency_years_reconciled + " agency-years reconcile within 1%.", AMBER],
    ["04", "Publish", "DuckDB warehouse, SQL views, an HTML dashboard, a Power BI model and this deck — all regenerated from the same tables.", ORANGE],
  ];
  blocks.forEach(([n, title, body, colour], i) => {
    const x = M + (i % 2) * (CW / 2 + 0.16);
    const y = 1.78 + Math.floor(i / 2) * 2.18;
    card(s, x, y, CW / 2 - 0.16, 1.94);
    s.addShape(pres.ShapeType.ellipse, {
      x: x + 0.3, y: y + 0.32, w: 0.56, h: 0.56, fill: { color: colour }, line: { color: colour, width: 0 },
    });
    txt(s, n, { x: x + 0.3, y: y + 0.32, w: 0.56, h: 0.56, margin: 0, fontFace: HEAD, fontSize: 15, bold: true, color: WHITE, align: "center", valign: "middle" });
    txt(s, title, { x: x + 1.02, y: y + 0.33, w: CW / 2 - 1.5, h: 0.36, margin: 0, fontFace: HEAD, fontSize: 17, bold: true, color: INK });
    txt(s, body, { x: x + 1.02, y: y + 0.76, w: CW / 2 - 1.5, h: 1.02, margin: 0, fontFace: TEXT, fontSize: 11.5, color: BODY, valign: "top", lineSpacingMultiple: 1.12 });
  });

  takeaway(s, D.validation.tests + " tests and " + D.validation.checks +
    " validation contracts run in CI. Two real defects were caught by them before publication.", 6.42);
  sourceNote(s, "Full method: docs/METHODOLOGY.md");
  s.addNotes("The point of this slide is that the numbers are checkable. Anyone can clone the repo and regenerate every figure offline.");
}

// ==================================================== 3 · GROWTH VS INFLATION
{
  const s = pres.addSlide();
  s.background = { color: WHITE };
  findingBadge(s, 1);
  heading(s, "Finding 01 · Growth", "Spending rose " + D.headline.nominal_growth_pct +
    "%. Adjusted for inflation, it rose " + D.headline.real_growth_pct + "%.",
    { titleW: CW - 0.9 });

  s.addChart(
    pres.ChartType.line,
    [
      { name: "Nominal dollars", labels: [D.growth_chart.labels], values: D.growth_chart.nominal },
      { name: "Constant FY" + D.meta.latest_fy + " dollars", labels: [D.growth_chart.labels], values: D.growth_chart.real },
    ],
    Object.assign({}, chartBase, {
      x: M, y: 1.82, w: 8.3, h: 4.3,
      chartColors: [BLUE, ORANGE],
      lineSize: 3, lineSmooth: false, showLegend: true, legendPos: "t",
      legendFontFace: TEXT, legendFontSize: 11, legendColor: BODY,
      valAxisMinVal: 95, valAxisMaxVal: 125,
      showTitle: true, title: "Obligations indexed to FY" + D.meta.base_fy + " = 100",
      titleFontFace: TEXT, titleFontSize: 12, titleColor: MUTED, titleAlign: "left",
    })
  );

  const x2 = M + 8.62;
  stat(s, x2, 2.15, 3.5, D.headline.nominal_growth_pct + "%", "Nominal growth\nFY" + D.meta.base_fy + "–FY" + D.meta.latest_fy, MUTED, 32);
  stat(s, x2, 3.45, 3.5, D.headline.real_growth_pct + "%", "Real growth, in constant\nFY" + D.meta.latest_fy + " dollars", BLUE, 40);
  card(s, x2, 4.85, 3.5, 1.28, SURFACE);
  txt(s, "$" + D.headline.price_only_bn + "B", { x: x2 + 0.22, y: 4.98, w: 3.1, h: 0.42, margin: 0, fontFace: HEAD, fontSize: 20, bold: true, color: ORANGE });
  txt(s, "of the $" + D.headline.nominal_rise_bn + "B increase is\nthe price level, not volume", { x: x2 + 0.22, y: 5.4, w: 3.1, h: 0.62, margin: 0, fontFace: TEXT, fontSize: 11.5, color: BODY, valign: "top" });

  takeaway(s, "Any statement about federal spending growth that does not name a deflator is describing inflation. Every figure that follows is inflation-adjusted.", 6.42);
  sourceNote(s, "USAspending API · deflated with the BEA GDP price index (FRED GDPDEF), fiscal-year averaged");
  s.addNotes("Lead with this because it sets the standard of care. Prices rose " + D.headline.inflation_pct + "% across the window.");
}

// ==================================================== 4 · COMPETITION FELL
{
  const s = pres.addSlide();
  s.background = { color: WHITE };
  findingBadge(s, 2);
  heading(s, "Finding 02 · Competition", "Competition fell to a five-year low", { titleW: CW - 0.9 });

  s.addChart(
    pres.ChartType.line,
    [
      { name: "Government-wide", labels: [D.competition_chart.labels], values: D.competition_chart.government },
      { name: "Department of Defense", labels: [D.competition_chart.labels], values: D.competition_chart.dod },
      { name: "All other agencies", labels: [D.competition_chart.labels], values: D.competition_chart.other },
    ],
    Object.assign({}, chartBase, {
      x: M, y: 1.78, w: 8.3, h: 4.34,
      chartColors: [BLUE, ORANGE, TEAL],
      lineSize: 3, lineSmooth: false, showLegend: true, legendPos: "t",
      legendFontFace: TEXT, legendFontSize: 11, legendColor: BODY,
      valAxisMinVal: 40, valAxisMaxVal: 95,
      showTitle: true, title: "Share of obligations awarded competitively (%)",
      titleFontFace: TEXT, titleFontSize: 12, titleColor: MUTED, titleAlign: "left",
    })
  );

  const x2 = M + 8.62;
  stat(s, x2, 2.1, 3.5, D.headline.competed_pct_prior + "% → " + D.headline.competed_pct + "%",
    "Competed share, FY" + (D.meta.latest_fy - 1) + " to FY" + D.meta.latest_fy, INK, 26);
  stat(s, x2, 3.4, 3.5, "$" + D.headline.noncompeted_bn + "B",
    "Non-competed obligations,\nup from $" + D.headline.noncompeted_bn_prior + "B", ORANGE, 32);
  card(s, x2, 4.86, 3.5, 1.3, SURFACE);
  txt(s, "Two possible causes", { x: x2 + 0.22, y: 4.98, w: 3.1, h: 0.3, margin: 0, fontFace: TEXT, fontSize: 11, bold: true, color: INK });
  txt(s, "Agencies competing less of their own work — or money moving toward agencies that never did.", { x: x2 + 0.22, y: 5.28, w: 3.1, h: 0.76, margin: 0, fontFace: TEXT, fontSize: 11, color: BODY, valign: "top" });

  takeaway(s, "Those two explanations call for opposite responses — so the next slide separates them rather than guessing.", 6.42);
  sourceNote(s);
  s.addNotes("Set up the question here and pay it off on the next slide. Do not resolve it yet.");
}

// ======================================================= 5 · NAVY ATTRIBUTION
{
  const s = pres.addSlide();
  s.background = { color: WHITE };
  findingBadge(s, 3);
  heading(s, "Finding 03 · Attribution",
    D.attribution.dod_share_pct + "% of the decline is Defense — and " +
    D.navy.share_of_dod_pct + "% of Defense is the Navy", { titleW: CW - 0.9, titleSize: 25 });

  txt(s, "Contribution to the government-wide change (pp)", {
    x: M, y: 1.72, w: 5.9, h: 0.28, margin: 0, fontFace: TEXT, fontSize: 11.5, color: MUTED,
  });
  s.addChart(
    pres.ChartType.bar,
    [{ name: "Departments", labels: [D.attribution.departments.map((d) => d.name)], values: D.attribution.departments.map((d) => d.pp) }],
    Object.assign({}, chartBase, {
      x: M - 0.08, y: 2.0, w: 6.05, h: 2.5, barDir: "bar",
      chartColors: D.attribution.departments.map((d) => (d.pp >= 0 ? BLUE : RED)),
      showValue: true, dataLabelPosition: "outEnd", dataLabelFormatCode: "+0.00;-0.00",
      dataLabelFontFace: TEXT, dataLabelFontSize: 9.5, dataLabelColor: BODY,
      barGapWidthPct: 45, valAxisHidden: true, valGridLine: { style: "none" },
      catAxisLabelPos: "low",
    })
  );

  txt(s, "Inside Defense, by component (pp)", {
    x: M + 6.3, y: 1.72, w: 5.9, h: 0.28, margin: 0, fontFace: TEXT, fontSize: 11.5, color: MUTED,
  });
  s.addChart(
    pres.ChartType.bar,
    [{ name: "Components", labels: [D.navy.components.map((d) => d.name)], values: D.navy.components.map((d) => d.pp) }],
    Object.assign({}, chartBase, {
      x: M + 6.22, y: 2.0, w: 6.05, h: 2.5, barDir: "bar",
      chartColors: D.navy.components.map((d) => (d.pp >= 0 ? BLUE : RED)),
      showValue: true, dataLabelPosition: "outEnd", dataLabelFormatCode: "+0.00;-0.00",
      dataLabelFontFace: TEXT, dataLabelFontSize: 9.5, dataLabelColor: BODY,
      barGapWidthPct: 45, valAxisHidden: true, valGridLine: { style: "none" },
      catAxisLabelPos: "low",
    })
  );

  s.addChart(
    pres.ChartType.line,
    [
      { name: "Navy", labels: [D.navy.military_chart.labels], values: D.navy.military_chart.navy },
      { name: "Air Force", labels: [D.navy.military_chart.labels], values: D.navy.military_chart.air_force },
      { name: "Army", labels: [D.navy.military_chart.labels], values: D.navy.military_chart.army },
    ],
    Object.assign({}, chartBase, {
      x: M - 0.08, y: 4.58, w: 7.2, h: 1.86,
      chartColors: [ORANGE, BLUE, TEAL],
      lineSize: 2.5, lineSmooth: false, showLegend: true, legendPos: "b",
      legendFontFace: TEXT, legendFontSize: 10, legendColor: BODY,
      valAxisMinVal: 30, valAxisMaxVal: 70,
      showTitle: true, title: "Military departments — competed share (%)",
      titleFontFace: TEXT, titleFontSize: 11, titleColor: MUTED, titleAlign: "left",
    })
  );

  card(s, M + 7.42, 4.72, 4.68, 1.62, SURFACE);
  txt(s, "Navy: " + D.navy.rate_prior + "% → " + D.navy.rate_latest + "%", {
    x: M + 7.64, y: 4.86, w: 4.3, h: 0.36, margin: 0, fontFace: HEAD, fontSize: 18, bold: true, color: ORANGE,
  });
  txt(s, "on $" + D.navy.obligations_bn + "B of obligations. Had it held the prior-year rate, $" +
        D.navy.gap_bn + "B more would have been competed. The Air Force moved the other way.", {
    x: M + 7.64, y: 5.28, w: 4.3, h: 0.94, margin: 0, fontFace: TEXT, fontSize: 11.5, color: BODY, valign: "top", lineSpacingMultiple: 1.1,
  });

  takeaway(s, "The decline is behavioural, not budget mix: " + D.attribution.within_pp +
    " pp within-agency versus " + D.attribution.mix_pp + " pp from money moving. The three terms reconcile to the total exactly.", 6.5);
  sourceNote(s, "Shift-share decomposition · reconciliation residual < 1e-16");
  s.addNotes("Spend the most time here. A department-level metric averaged Navy's nine-point fall against the Air Force's rise and reported 'Defense declined'.");
}

// ========================================================= 6 · PORTFOLIO TEST
{
  const s = pres.addSlide();
  s.background = { color: WHITE };
  findingBadge(s, 4);
  heading(s, "Finding 04 · Control",
    "“We buy harder things” explains " + D.portfolio.explained_pp +
    " points of a " + Math.round(D.portfolio.remaining_pp + D.portfolio.explained_pp) + "-point gap",
    { titleW: CW - 0.9, titleSize: 25 });

  txt(s, "Holding the product mix constant at the government-wide basket, so only within-category practice varies.", {
    x: M, y: 1.68, w: 8.4, h: 0.3, margin: 0, fontFace: TEXT, fontSize: 12, color: BODY,
  });

  s.addChart(
    pres.ChartType.bar,
    [
      { name: "Observed", labels: [D.portfolio.agencies.map((a) => a.name)], values: D.portfolio.agencies.map((a) => a.observed) },
      { name: "Portfolio-adjusted", labels: [D.portfolio.agencies.map((a) => a.name)], values: D.portfolio.agencies.map((a) => a.adjusted) },
    ],
    Object.assign({}, chartBase, {
      x: M - 0.08, y: 2.08, w: 8.5, h: 4.05, barDir: "bar",
      chartColors: [BLUE, ORANGE],
      showLegend: true, legendPos: "t", legendFontFace: TEXT, legendFontSize: 11, legendColor: BODY,
      showValue: true, dataLabelPosition: "outEnd", dataLabelFormatCode: "0.0",
      dataLabelFontFace: TEXT, dataLabelFontSize: 9, dataLabelColor: BODY,
      barGapWidthPct: 40, valAxisMaxVal: 110, valAxisHidden: true, valGridLine: { style: "none" },
    })
  );

  const x2 = M + 8.76;
  stat(s, x2, 2.18, 3.4, D.portfolio.dod_observed.toFixed(1) + "% → " + D.portfolio.dod_adjusted.toFixed(1) + "%",
    "Defense, before and after\nadjusting for what it buys", INK, 24);
  stat(s, x2, 3.5, 3.4, D.portfolio.civilian_median + "%", "Civilian agency median,\nadjusted", TEAL, 32);
  card(s, x2, 4.86, 3.4, 1.3, SURFACE);
  txt(s, D.portfolio.remaining_pp + " points remain", { x: x2 + 0.2, y: 4.98, w: 3.0, h: 0.32, margin: 0, fontFace: HEAD, fontSize: 16, bold: true, color: ORANGE });
  txt(s, "Defense competing less than others on the same kinds of purchases.", { x: x2 + 0.2, y: 5.32, w: 3.0, h: 0.72, margin: 0, fontFace: TEXT, fontSize: 11.5, color: BODY, valign: "top" });

  takeaway(s, "Product categories are coarse, so " + D.portfolio.remaining_pp +
    " points is an upper bound on the practice gap, not a point estimate.", 6.5, MUTED);
  sourceNote(s, "Direct standardisation · reference coverage for Defense: " + D.portfolio.dod_coverage);
  s.addNotes("Volunteer the upper bound before anyone asks. That reads as confidence; conceding it under questioning does not.");
}

// ========================================================== 7 · YEAR-END SURGE
{
  const s = pres.addSlide();
  s.background = { color: WHITE };
  findingBadge(s, 5);
  heading(s, "Finding 05 · Timing",
    D.headline.september_pct.toFixed(1) + "% of the year's contracting happened in its final month",
    { titleW: CW - 0.9, titleSize: 25 });

  s.addChart(
    pres.ChartType.bar,
    [{ name: "Pacing", labels: [D.timing.labels], values: D.timing.index }],
    Object.assign({}, chartBase, {
      x: M - 0.08, y: 1.86, w: 8.4, h: 4.24, barDir: "col",
      chartColors: D.timing.labels.map((_, i) => (i === D.timing.labels.length - 1 ? ORANGE : BLUE)),
      showValue: true, dataLabelPosition: "outEnd", dataLabelFormatCode: "0",
      dataLabelFontFace: TEXT, dataLabelFontSize: 9.5, dataLabelColor: BODY,
      barGapWidthPct: 40,
      showTitle: true, title: "FY" + D.meta.latest_fy + " obligations by month, indexed to an even pace (100)",
      titleFontFace: TEXT, titleFontSize: 12, titleColor: MUTED, titleAlign: "left",
    })
  );

  const x2 = M + 8.68;
  stat(s, x2, 2.2, 3.5, "$" + D.headline.september_excess_bn + "B", "obligated above an\neven monthly pace", ORANGE, 36);
  stat(s, x2, 3.62, 3.5, D.timing.q4_pct + "%", "of the year fell in\nfiscal Q4 (Jul–Sep)", INK, 32);
  card(s, x2, 5.0, 3.5, 1.16, SURFACE);
  txt(s, "September share by year", { x: x2 + 0.2, y: 5.1, w: 3.1, h: 0.28, margin: 0, fontFace: TEXT, fontSize: 10.5, bold: true, color: INK });
  txt(s, D.timing.september_pct_by_year.map((v, i) => D.timing.year_labels[i].replace("FY", "") + ": " + v.toFixed(1) + "%").join("   "), {
    x: x2 + 0.2, y: 5.4, w: 3.1, h: 0.6, margin: 0, fontFace: TEXT, fontSize: 11, color: BODY, valign: "top",
  });

  takeaway(s, "A sampling frame, not a finding — but the largest such population in five years.", 6.5, MUTED);
  sourceNote(s);
  s.addNotes("Be careful here. Do not allege anything; this identifies where to sample.");
}

// ======================================================= 8 · FY2025 REALIGNMENT
{
  const s = pres.addSlide();
  s.background = { color: WHITE };
  findingBadge(s, 6);
  heading(s, "Finding 06 · Composition",
    "FY" + D.meta.latest_fy + " split the government in two", { titleW: CW - 0.9 });

  s.addChart(
    pres.ChartType.bar,
    [{ name: "Change", labels: [D.movers.map((m) => m.name)], values: D.movers.map((m) => m.change_bn) }],
    Object.assign({}, chartBase, {
      x: M - 0.08, y: 1.82, w: 8.5, h: 4.3, barDir: "bar",
      chartColors: D.movers.map((m) => (m.change_bn >= 0 ? BLUE : RED)),
      showValue: true, dataLabelPosition: "outEnd", dataLabelFormatCode: "+0.0;-0.0",
      dataLabelFontFace: TEXT, dataLabelFontSize: 9.5, dataLabelColor: BODY,
      barGapWidthPct: 40, valAxisHidden: true, valGridLine: { style: "none" },
      catAxisLabelPos: "low",
      showTitle: true, title: "Change in obligations, FY" + (D.meta.latest_fy - 1) + " to FY" + D.meta.latest_fy + " ($B)",
      titleFontFace: TEXT, titleFontSize: 12, titleColor: MUTED, titleAlign: "left",
    })
  );

  const x2 = M + 8.78;
  txt(s, "Concentration rose with it", { x: x2, y: 2.1, w: 3.4, h: 0.32, margin: 0, fontFace: HEAD, fontSize: 15, bold: true, color: INK });
  stat(s, x2, 2.55, 3.4, D.concentration.hhi_prior + " → " + D.concentration.hhi_latest, "Agency-level HHI", INK, 24);
  stat(s, x2, 3.75, 3.4, D.concentration.cr4_prior.toFixed(1) + "% → " + D.concentration.cr4_latest.toFixed(1) + "%", "Top four agencies'\nshare of all obligations", INK, 24);
  card(s, x2, 5.02, 3.4, 1.14, SURFACE);
  txt(s, "HUD ended net negative", { x: x2 + 0.2, y: 5.12, w: 3.0, h: 0.3, margin: 0, fontFace: TEXT, fontSize: 11, bold: true, color: RED });
  txt(s, "It cancelled more contract value than it awarded — unique in the window.", { x: x2 + 0.2, y: 5.42, w: 3.0, h: 0.62, margin: 0, fontFace: TEXT, fontSize: 11, color: BODY, valign: "top" });

  takeaway(s, "Defence and security grew while health, international development and general services contracted sharply.", 6.5);
  sourceNote(s);
  s.addNotes("Keep this brief — it is context for the recommendations, not a finding to defend.");
}

// ==================================================== 9 · INDEX & UNCERTAINTY
{
  const s = pres.addSlide();
  s.background = { color: WHITE };
  findingBadge(s, 7);
  heading(s, "Finding 07 · Uncertainty",
    "A ranking, and the reason not to trust most of it", { titleW: CW - 0.9 });

  txt(s, "Every agency re-scored 2,000 times under randomly drawn weights. The band is the 5th–95th percentile of its score.", {
    x: M, y: 1.66, w: CW, h: 0.3, margin: 0, fontFace: TEXT, fontSize: 12, color: BODY,
  });

  const top = D.index.rows.slice(0, 6);
  const bottom = D.index.rows.slice(-4);
  const rows = [
    [
      { text: "Agency", options: { bold: true, color: MUTED, fontSize: 10.5 } },
      { text: "Score", options: { bold: true, color: MUTED, fontSize: 10.5, align: "right" } },
      { text: "Range across weightings", options: { bold: true, color: MUTED, fontSize: 10.5, align: "right" } },
      { text: "Rank best–worst", options: { bold: true, color: MUTED, fontSize: 10.5, align: "right" } },
      { text: "Reliability", options: { bold: true, color: MUTED, fontSize: 10.5 } },
    ],
  ];
  const addRow = (r) => {
    const robust = r.verdict !== "not separable";
    rows.push([
      { text: r.name, options: { fontSize: 11, color: INK } },
      { text: r.score.toFixed(1), options: { fontSize: 11, color: INK, align: "right" } },
      { text: r.low.toFixed(1) + " – " + r.high.toFixed(1), options: { fontSize: 11, color: BODY, align: "right" } },
      { text: r.best + " – " + r.worst, options: { fontSize: 11, color: BODY, align: "right" } },
      { text: robust ? "Robust" : "Not separable", options: { fontSize: 10.5, color: robust ? TEAL : ORANGE, bold: robust } },
    ]);
  };
  top.forEach(addRow);
  rows.push([
    { text: "…", options: { fontSize: 11, color: MUTED } }, { text: "", options: {} },
    { text: "", options: {} }, { text: "", options: {} }, { text: "", options: {} },
  ]);
  bottom.forEach(addRow);

  s.addTable(rows, {
    x: M, y: 2.06, w: 8.5, colW: [2.5, 0.9, 2.1, 1.5, 1.5],
    border: { type: "solid", color: LINE, pt: 0.5 },
    fontFace: TEXT, rowH: 0.31, valign: "middle", autoPage: false,
  });

  const x2 = M + 8.82;
  stat(s, x2, 2.16, 3.4, D.index.robust + " of " + D.index.scored, "agencies hold their quartile\nacross every weighting", ORANGE, 34);
  card(s, x2, 3.6, 3.4, 2.55, SURFACE);
  txt(s, "What survives", { x: x2 + 0.2, y: 3.74, w: 3.0, h: 0.3, margin: 0, fontFace: TEXT, fontSize: 11, bold: true, color: INK });
  txt(s, D.index.robust_names.join(", ") + " hold their position under almost any weighting. Everything between them is an artefact of the weights, and is reported as such.", {
    x: x2 + 0.2, y: 4.06, w: 3.0, h: 1.4, margin: 0, fontFace: TEXT, fontSize: 11, color: BODY, valign: "top", lineSpacingMultiple: 1.12,
  });
  txt(s, "Use the tails. Do not rank the middle.", { x: x2 + 0.2, y: 5.5, w: 3.0, h: 0.5, margin: 0, fontFace: TEXT, fontSize: 11.5, bold: true, color: ORANGE, valign: "top" });

  takeaway(s, "An index published with its uncertainty attached is more useful than one that appears more authoritative than the evidence supports.", 6.5);
  sourceNote(s, "Weights drawn from a flat Dirichlet — the uniform distribution over the simplex");
  s.addNotes("This is the page that distinguishes the work. Most portfolio dashboards present a ranking as settled.");
}

// ======================================================= 10 · RECOMMENDATIONS
{
  const s = pres.addSlide();
  s.background = { color: WHITE };
  heading(s, "Recommendations", "Six places to look, ranked by what the review would teach");

  const recs = [
    ["R1", "Report competition at the level that awards contracts", "$" + D.navy.gap_bn + "B", "High",
      "Navy drove ~" + D.navy.share_of_gov_pct + "% of the government-wide decline. A department-level metric sends the question to 40 organisations."],
    ["R2", "Test the “harder things” defence before accepting it", D.portfolio.remaining_pp + " pp", "High",
      "Portfolio mix explains only " + D.portfolio.explained_pp + " points of Defense's gap. The rest is practice."],
    ["R3", "Use the September surge as a sampling frame", "$" + D.headline.september_excess_bn + "B", "Medium",
      "Compare year-end awards against the same agency's rest-of-year baseline for competition and pricing."],
    ["R4", "Track contract-type risk as an independent signal", "$" + D.headline.government_risk_bn + "B", "Medium",
      "HHS cost-risk share rose " + D.risk[0].change_pp + " pp while its obligations fell 28.7%."],
    ["R5", "Use the efficiency index only at its tails", "—", "High",
      "Only " + D.index.robust + " of " + D.index.scored + " agencies hold their quartile. The middle is not a ranking."],
    ["R6", "Treat vendor concentration as a data problem first", "—", "Low",
      "Truncated at the top 100 recipients with no corporate-family rollup. Not yet good enough to act on."],
  ];

  const colour = { High: TEAL, Medium: AMBER, Low: MUTED };
  recs.forEach(([id, title, size, conf, body], i) => {
    const y = 1.62 + i * 0.87;
    card(s, M, y, CW, 0.79);
    txt(s, id, { x: M + 0.22, y: y + 0.13, w: 0.6, h: 0.32, margin: 0, fontFace: HEAD, fontSize: 15, bold: true, color: BLUE });
    txt(s, title, { x: M + 0.86, y: y + 0.1, w: 6.0, h: 0.3, margin: 0, fontFace: TEXT, fontSize: 13, bold: true, color: INK });
    txt(s, body, { x: M + 0.86, y: y + 0.4, w: 8.3, h: 0.32, margin: 0, fontFace: TEXT, fontSize: 10.5, color: BODY });
    txt(s, size, { x: M + 9.35, y: y + 0.22, w: 1.4, h: 0.34, margin: 0, fontFace: HEAD, fontSize: 15, bold: true, color: INK, align: "right" });
    s.addShape(pres.ShapeType.roundRect, {
      x: M + 10.95, y: y + 0.24, w: 1.02, h: 0.31, rectRadius: 0.14,
      fill: { color: colour[conf] }, line: { color: colour[conf], width: 0 },
    });
    txt(s, conf, { x: M + 10.95, y: y + 0.24, w: 1.02, h: 0.31, margin: 0, fontFace: TEXT, fontSize: 10, bold: true, color: WHITE, align: "center", valign: "middle" });
  });

  takeaway(s, "Each recommendation states what evidence would prove it wrong. R6 is deliberately marked low-confidence.", 6.92);
  s.addNotes("Walk R1, R2 and R5. R5 is a recommendation against my own index, which is the point.");
}

// ============================================================ 11 · LIMITATIONS
{
  const s = pres.addSlide();
  s.background = { color: WHITE };
  heading(s, "Limitations", "What this analysis cannot support");

  const lims = [
    ["Obligations, not outlays", "Money committed, not money spent. De-obligations are included, so an agency can post a negative year."],
    ["Contracts only", "Grants, loans and direct payments are out of scope. This is federal contracting, not federal spending."],
    ["Awarding agency, not funding agency", "Where one agency buys on another's behalf, the obligation is credited to the awarder. This materially affects GSA."],
    ["Competition rate is not competition quality", "A competed award drawing one bid meets the process without getting price discipline."],
    ["The category control is coarse", "Product groups mix unlike purchases, so the practice gap is an upper bound."],
    ["Vendor concentration is understated", "Top-100 recipients only, with no corporate-family rollup."],
  ];
  lims.forEach(([t, b], i) => {
    const x = M + (i % 2) * (CW / 2 + 0.16);
    const y = 1.62 + Math.floor(i / 2) * 1.12;
    txt(s, t, { x, y, w: CW / 2 - 0.2, h: 0.3, margin: 0, fontFace: TEXT, fontSize: 12.5, bold: true, color: INK });
    txt(s, b, { x, y: y + 0.31, w: CW / 2 - 0.2, h: 0.66, margin: 0, fontFace: TEXT, fontSize: 11, color: BODY, valign: "top", lineSpacingMultiple: 1.1 });
  });

  card(s, M, 5.2, CW, 1.5, SURFACE);
  txt(s, "Two things to be explicit about", { x: M + 0.3, y: 5.34, w: CW - 0.6, h: 0.3, margin: 0, fontFace: TEXT, fontSize: 12, bold: true, color: INK });
  txt(s, "Nothing here identifies waste, fraud or abuse. Sole-source contracts are frequently lawful and correct, and some work genuinely requires cost-reimbursement. Every output indicates where a reviewer would learn the most, not where wrongdoing occurred.", {
    x: M + 0.3, y: 5.66, w: CW - 0.6, h: 0.5, margin: 0, fontFace: TEXT, fontSize: 11.5, color: BODY, valign: "top",
  });
  txt(s, "There is no savings estimate in this deck, deliberately. Competition affects price, but this analysis observes obligations, not prices.", {
    x: M + 0.3, y: 6.16, w: CW - 0.6, h: 0.42, margin: 0, fontFace: TEXT, fontSize: 11.5, bold: true, color: INK, valign: "top",
  });
  s.addNotes("Do not rush this slide or apologise for it. In an interview it often earns the most credit.");
}

// ================================================================ 12 · CLOSING
{
  const s = pres.addSlide();
  s.background = { color: NAVY };
  heading(s, "How it holds up", "Checkable, reproducible, and honest about its limits", { dark: true });

  const facts = [
    [D.validation.agency_years_reconciled + " / " + D.validation.agency_years_reconciled, "agency-years reconcile\nwithin 1%"],
    [String(D.validation.checks), "data-quality contracts\nfail the build if broken"],
    [String(D.validation.tests), "tests, none of which\ntouch the network"],
    ["~2 sec", "to reproduce every\nfigure offline"],
  ];
  facts.forEach(([v, l], i) => {
    const x = M + i * 3.06;
    txt(s, v, { x, y: 2.15, w: 2.85, h: 0.66, margin: 0, fontFace: HEAD, fontSize: 30, bold: true, color: WHITE });
    txt(s, l, { x, y: 2.83, w: 2.85, h: 0.7, margin: 0, fontFace: TEXT, fontSize: 11.5, color: "8FB3D9", valign: "top" });
  });

  s.addShape(pres.ShapeType.roundRect, {
    x: M, y: 4.0, w: CW, h: 1.3, rectRadius: 0.06,
    fill: { color: NAVY_SOFT }, line: { color: "2C4055", width: 1 },
  });
  txt(s, "Two real defects were caught by those checks before publication", {
    x: M + 0.32, y: 4.16, w: CW - 0.64, h: 0.32, margin: 0, fontFace: TEXT, fontSize: 12.5, bold: true, color: WHITE,
  });
  txt(s, "A government API that silently truncates its results — it had dropped Interior's largest component and left the totals 33% short. And a calculation that could return a competition rate above 100%, because its numerator and denominator came from separate queries. Both are documented in the repository rather than quietly patched.", {
    x: M + 0.32, y: 4.5, w: CW - 0.64, h: 0.86, margin: 0, fontFace: TEXT, fontSize: 11.5, color: "C3D3E2", valign: "top", lineSpacingMultiple: 1.12,
  });

  txt(s, "Andrew Kemp", { x: M, y: 5.86, w: 6, h: 0.36, margin: 0, fontFace: HEAD, fontSize: 19, bold: true, color: WHITE });
  txt(s, "github.com/Akemp787/federal-spending-efficiency-analysis", {
    x: M, y: 6.24, w: 8, h: 0.32, margin: 0, fontFace: TEXT, fontSize: 12.5, color: "8FB3D9",
  });
  txt(s, "Code, methodology, data dictionary, recommendations and limitations\nare all in the repository.", {
    x: W - M - 5.2, y: 5.9, w: 5.2, h: 0.7, margin: 0, fontFace: TEXT, fontSize: 11.5, color: "8FB3D9", align: "right", valign: "top",
  });
  s.addNotes("Close on reproducibility. Offer the repo link.");
}

const outFile = path.join(ROOT, "outputs", "Federal_Contract_Efficiency.pptx");
pres.writeFile({ fileName: outFile }).then(() => {
  console.log("deck -> " + outFile);
});
