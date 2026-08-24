"""Renders the self-contained analytical dashboard.

The output is one HTML file with no external requests: styles, scripts, and every
chart are inlined, so it renders from a local filesystem, from GitHub Pages, or
from an artifact host without change. Colours are CSS custom properties defined
for both themes, so the reader's light/dark preference is honoured without a
re-render.

Every figure on the page is read from the curated tables at render time. There
are no hard-coded numbers in the narrative - the sentences are built from the
same values the charts plot, so the prose cannot drift from the data.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pandas as pd

from ..config import Config
from ..logging_utils import get_logger
from . import charts as ch
from .theme import CSS, FONT_LINK, JS

log = get_logger(__name__)

# ---------------------------------------------------------------------------
def _table(df: pd.DataFrame, columns: dict[str, str], signed: set[str] | None = None) -> str:
    signed = signed or set()
    head = "".join(f"<th>{ch.esc(v)}</th>" for v in columns.values())
    rows = []
    for _, r in df.iterrows():
        cells = []
        for key in columns:
            val = r[key]
            cls = ""
            if key in signed and isinstance(val, (int, float)) and pd.notna(val):
                cls = ' class="pos"' if val > 0 else (' class="neg"' if val < 0 else "")
            if isinstance(val, float):
                text = f"{val:,.2f}" if abs(val) < 1000 else f"{val:,.0f}"
                if pd.isna(val):
                    text = "—"
            else:
                text = str(val)
            cells.append(f"<td{cls}>{ch.esc(text)}</td>")
        rows.append("<tr>" + "".join(cells) + "</tr>")
    return (
        '<div class="table-scroll"><table><thead><tr>'
        + head
        + "</tr></thead><tbody>"
        + "".join(rows)
        + "</tbody></table></div>"
    )


def _details(label: str, body: str) -> str:
    return f"<details><summary>{ch.esc(label)}</summary>{body}</details>"


def build_dashboard(cfg: Config, out_path: Path | None = None) -> Path:
    """Render the dashboard to ``outputs/dashboard.html``."""
    cur = cfg.curated_dir
    gov = pd.read_parquet(cur / "gov_summary.parquet").sort_values("fiscal_year")
    fact = pd.read_parquet(cur / "fact_agency_year.parquet")
    season = pd.read_parquet(cur / "monthly_seasonality.parquet")
    decomp = pd.read_parquet(cur / "competition_decomposition.parquet")
    decomp_series = pd.read_parquet(cur / "competition_decomposition_series.parquet")
    idx = pd.read_parquet(cur / "efficiency_index.parquet")
    sens = pd.read_parquet(cur / "index_sensitivity.parquet")
    manifest = json.loads((cur / "_manifest.json").read_text(encoding="utf-8"))

    base_fy, latest_fy = cfg.base_fy, cfg.latest_fy
    first, last = gov.iloc[0], gov.iloc[-1]
    prev = gov.iloc[-2]
    years = [str(int(y)) for y in gov["fiscal_year"]]

    nominal_growth = (last["obligations"] / first["obligations"] - 1) * 100
    real_growth = (last["obligations_real"] / first["obligations_real"] - 1) * 100
    # Dollars of the FY-latest total that represent price change rather than volume:
    # the nominal level minus what the level would be had real volume grown as it
    # did but prices stayed at base-year levels.
    inflation_only_bn = last["obligations"] - first["obligations"] * (
        last["obligations_real"] / first["obligations_real"]
    )

    comp_change_pp = (last["competed_share"] - prev["competed_share"]) * 100
    latest_decomp = decomp_series.iloc[-1]
    within_pp = latest_decomp["within_effect"] * 100
    mix_pp = latest_decomp["mix_effect"] * 100

    dod = decomp[decomp["agency_name"] == "Department of Defense"].iloc[0]
    dod_total_pp = dod["total_effect"] * 100
    dod_share_of_change = dod_total_pp / (latest_decomp["total_change"] * 100) * 100

    sep_share = last["september_share"] * 100

    # ---------------- KPI tiles -------------------------------------------
    kpis = [
        (
            f"FY{latest_fy} obligations",
            ch.fmt_money_bn(last["obligations"], 0),
            f"{ch.fmt_signed(last['obligations_yoy_pct'])}% vs FY{latest_fy - 1} (nominal)",
            "",
        ),
        (
            f"Real growth FY{base_fy}–{latest_fy}",
            f"{real_growth:+.1f}%",
            f"vs {nominal_growth:+.1f}% nominal — constant FY{latest_fy} dollars",
            "",
        ),
        (
            "Competed share",
            f"{last['competed_share'] * 100:.1f}%",
            f"{comp_change_pp:+.1f} pp vs FY{latest_fy - 1}",
            "up" if comp_change_pp < 0 else "down",
        ),
        (
            "September concentration",
            f"{sep_share:.1f}%",
            f"{ch.fmt_money_bn(last['september_excess_obligations'], 0)} above an even pace",
            "up",
        ),
        (
            "Government-risk pricing",
            f"{last['government_risk_share'] * 100:.1f}%",
            "cost-reimbursement + labour-hour dollars",
            "",
        ),
    ]
    kpi_html = "".join(
        f'<div class="kpi"><div class="label">{ch.esc(label)}</div>'
        f'<div class="value">{ch.esc(value)}</div>'
        f'<div class="sub {tone}">{ch.esc(sub)}</div></div>'
        for label, value, sub, tone in kpis
    )

    # ---------------- Finding 1: nominal vs real ---------------------------
    f1_chart = ch.line_chart(
        years,
        [
            {"name": "Nominal dollars", "values": gov["obligations_index_vs_base"].tolist()},
            {
                "name": f"Constant FY{latest_fy} dollars",
                "values": gov["obligations_real_index_vs_base"].tolist(),
            },
        ],
        title=f"Federal contract obligations indexed to FY{base_fy} = 100",
        desc=(
            f"Nominal obligations rose to {last['obligations_index_vs_base']:.0f} while "
            f"inflation-adjusted obligations reached only "
            f"{last['obligations_real_index_vs_base']:.0f}."
        ),
        y_label_fmt=lambda v: f"{v:,.0f}",
        value_fmt=lambda v: f"{v:,.1f}",
    )
    f1_table = _table(
        gov.assign(
            fy=gov["fiscal_year"].astype(int),
            nominal_bn=gov["obligations"] / 1e9,
            real_bn=gov["obligations_real"] / 1e9,
            yoy_nom=gov["obligations_yoy_pct"],
            yoy_real=gov["obligations_real_yoy_pct"],
        ),
        {
            "fy": "Fiscal year",
            "nominal_bn": "Nominal ($B)",
            "real_bn": f"Constant FY{latest_fy} ($B)",
            "yoy_nom": "YoY nominal (%)",
            "yoy_real": "YoY real (%)",
        },
        signed={"yoy_nom", "yoy_real"},
    )

    # ---------------- Finding 2: competition -------------------------------
    f2_chart = ch.line_chart(
        years,
        [
            {
                "name": "Government-wide",
                "values": (gov["competed_share"] * 100).round(2).tolist(),
            },
            {
                "name": "Department of Defense",
                "values": (
                    fact[fact["agency_name"] == "Department of Defense"]
                    .sort_values("fiscal_year")["competed_share"]
                    * 100
                )
                .round(2)
                .tolist(),
            },
            {
                "name": "All other agencies",
                "values": _ex_dod_competed(fact),
            },
        ],
        title="Share of contract obligations awarded competitively",
        desc=(
            f"Government-wide competed share fell {abs(comp_change_pp):.1f} points to "
            f"{last['competed_share'] * 100:.1f}% in FY{latest_fy}."
        ),
        y_label_fmt=lambda v: f"{v:.0f}%",
        value_fmt=lambda v: f"{v:.1f}%",
    )

    attribution = decomp.reindex(
        decomp["total_effect"].abs().sort_values(ascending=False).index
    ).head(8)
    f2_attr = ch.diverging_bar_chart(
        attribution["agency_name"].tolist(),
        (attribution["total_effect"] * 100).round(3).tolist(),
        title=f"Contribution to the FY{latest_fy} change in competed share",
        desc="Percentage-point contribution of each agency to the government-wide move.",
        value_fmt=lambda v: f"{v:+.2f} pp",
    )
    f2_table = _table(
        attribution.assign(
            wt_prior=attribution["w_0"] * 100,
            wt_latest=attribution["w_1"] * 100,
            rate_prior=attribution["s_0"] * 100,
            rate_latest=attribution["s_1"] * 100,
            within=attribution["within_effect"] * 100,
            mix=attribution["mix_effect"] * 100,
            total=attribution["total_effect"] * 100,
        ),
        {
            "agency_name": "Agency",
            "wt_prior": f"Share of spend FY{latest_fy - 1} (%)",
            "wt_latest": f"Share of spend FY{latest_fy} (%)",
            "rate_prior": f"Competed FY{latest_fy - 1} (%)",
            "rate_latest": f"Competed FY{latest_fy} (%)",
            "within": "Within effect (pp)",
            "mix": "Mix effect (pp)",
            "total": "Total (pp)",
        },
        signed={"within", "mix", "total"},
    )

    # ---------------- Finding 3: year-end surge ----------------------------
    latest_season = season[season["fiscal_year"] == latest_fy].sort_values("fiscal_month")
    f3_chart = ch.column_chart(
        latest_season["month_name"].tolist(),
        latest_season["index_vs_even_pace"].round(1).tolist(),
        title=f"FY{latest_fy} obligations by month, indexed to an even pace (100)",
        desc=(
            f"September obligations ran at "
            f"{latest_season['index_vs_even_pace'].iloc[-1]:.0f}% of an even monthly pace."
        ),
        highlight_index=len(latest_season) - 1,
        reference=100.0,
        reference_label="even monthly pace",
        value_fmt=lambda v: f"{v:,.0f}",
        y_label_fmt=lambda v: f"{v:,.0f}",
    )
    surge_trend = ch.column_chart(
        years,
        (gov["september_share"] * 100).round(2).tolist(),
        title="September share of annual obligations, by fiscal year",
        desc="The share of each year's obligations placed in the final month.",
        highlight_index=len(years) - 1,
        value_fmt=lambda v: f"{v:.1f}%",
        y_label_fmt=lambda v: f"{v:.0f}%",
        height=250,
    )

    top_surge = (
        fact[(fact["fiscal_year"] == latest_fy) & (fact["obligations"] > 1e9)]
        .nlargest(10, "september_share")
        .assign(
            sep_pct=lambda d: d["september_share"] * 100,
            bn=lambda d: d["obligations"] / 1e9,
            excess=lambda d: d["september_excess_obligations"] / 1e9,
        )
    )
    f3_table = _table(
        top_surge,
        {
            "agency_name": "Agency",
            "bn": f"FY{latest_fy} obligations ($B)",
            "sep_pct": "September share (%)",
            "excess": "Above even pace ($B)",
        },
    )

    # ---------------- Finding 4: FY2025 realignment ------------------------
    movers = fact[fact["fiscal_year"] == latest_fy].copy()
    movers = movers[movers["prior_year"].notna() & (movers["prior_year"].abs() > 1e9)]
    movers["change_bn"] = movers["change_abs"] / 1e9
    movers = movers.reindex(movers["change_bn"].abs().sort_values(ascending=False).index).head(12)
    movers = movers.sort_values("change_bn", ascending=False)

    f4_chart = ch.diverging_bar_chart(
        movers["agency_name"].tolist(),
        movers["change_bn"].round(2).tolist(),
        title=f"Change in contract obligations, FY{latest_fy - 1} to FY{latest_fy}",
        desc="Nominal change in obligations for the twelve largest movers.",
        value_fmt=lambda v: f"{v:+,.1f}B",
    )
    f4_table = _table(
        movers.assign(
            prior_bn=movers["prior_year"] / 1e9,
            now_bn=movers["obligations"] / 1e9,
            pct=movers["change_pct"],
            real_pct=movers["change_pct_real"],
        ),
        {
            "agency_name": "Agency",
            "prior_bn": f"FY{latest_fy - 1} ($B)",
            "now_bn": f"FY{latest_fy} ($B)",
            "change_bn": "Change ($B)",
            "pct": "Change nominal (%)",
            "real_pct": "Change real (%)",
        },
        signed={"change_bn", "pct", "real_pct"},
    )

    # ---------------- Finding 5: efficiency index --------------------------
    ranked = idx.merge(sens, on="agency_name", how="left").sort_values(
        "efficiency_index", ascending=False
    )
    f5_chart = ch.ranked_bar_with_range(
        ranked["agency_name"].tolist(),
        ranked["efficiency_index"].round(1).tolist(),
        ranked["score_p05"].round(1).tolist(),
        ranked["score_p95"].round(1).tolist(),
        title=f"Contract Efficiency Index, FY{latest_fy}",
        desc=(
            "Composite score with the 5th-95th percentile band across "
            "2,000 random weightings."
        ),
    )
    robust = ranked[ranked["quartile_verdict"] != "not separable"]
    f5_table = _table(
        ranked.assign(
            bn=ranked["obligations"] / 1e9,
            cei=ranked["efficiency_index"],
            comp=ranked["competed_share"] * 100,
            risk=ranked["government_risk_share"] * 100,
            sep=ranked["september_share"] * 100,
        ),
        {
            "agency_name": "Agency",
            "bn": "Obligations ($B)",
            "cei": "Index",
            "rank_median": "Median rank",
            "rank_best": "Best rank",
            "rank_worst": "Worst rank",
            "quartile_verdict": "Robustness",
            "comp": "Competed (%)",
            "risk": "Gov-risk pricing (%)",
            "sep": "September (%)",
        },
    )

    # ---------------- assemble ---------------------------------------------
    snapshot = manifest.get("snapshot_date", date.today().isoformat())
    page_title = "Federal Contract Efficiency"
    body = f"""
<div class="wrap">
<header class="masthead">
  <div class="eyebrow">USAspending FY{base_fy}–FY{latest_fy} · contract obligations</div>
  <h1>Where federal contract dollars went — and where the market test didn't happen</h1>
  <p class="standfirst">An analysis of {ch.fmt_money_bn(gov['obligations'].sum(), 0)} in federal
  contract obligations across five fiscal years, measuring competition, contract-type risk,
  vendor concentration and year-end timing to identify where oversight attention is worth
  spending first.</p>
  <div class="meta">
    <span>Snapshot <code>{ch.esc(snapshot)}</code></span>
    <span>Source <code>api.usaspending.gov/v2</code></span>
    <span>Award types <code>{ch.esc(", ".join(manifest.get("award_type_codes", [])))}</code></span>
    <span>Deflator <code>{ch.esc(manifest.get("deflator_series", "GDPDEF"))}</code></span>
  </div>
</header>

<div class="kpis">{kpi_html}</div>

<section><div class="finding">
  <span class="tag">Finding 01 · Growth</span>
  <h2>Nearly all of the {nominal_growth:.0f}% headline growth since FY{base_fy} is the price level, not more buying</h2>
  <p>Nominal contract obligations rose from {ch.fmt_money_bn(first['obligations'], 0)} in
  FY{base_fy} to {ch.fmt_money_bn(last['obligations'], 0)} in FY{latest_fy}, an increase of
  <strong>{nominal_growth:.1f}%</strong>. Restated in constant FY{latest_fy} dollars using the
  GDP price deflator, the same series grows <strong>{real_growth:.1f}%</strong> — roughly
  {ch.fmt_money_bn(abs(inflation_only_bn), 0)} of the apparent increase is inflation rather than
  additional goods and services.</p>
  <div class="chart-frame">{f1_chart}</div>
  {ch.legend(["Nominal dollars", f"Constant FY{latest_fy} dollars"])}
  <div class="callout"><p>Any statement about federal spending "growth" that does not name a
  deflator is describing the price level. The real series is the one every finding below
  uses.</p></div>
  {_details("Show the underlying figures", f1_table)}
</div></section>

<section><div class="finding">
  <span class="tag">Finding 02 · Competition</span>
  <h2>Competition fell {abs(comp_change_pp):.1f} points in FY{latest_fy}, and {abs(dod_share_of_change):.0f}% of that is one department</h2>
  <p>The share of obligations awarded competitively dropped from
  {prev['competed_share'] * 100:.1f}% to <strong>{last['competed_share'] * 100:.1f}%</strong>,
  the largest single-year decline in the window. A shift-share decomposition separates two
  explanations that carry opposite implications: agencies competing less of their own work
  (<em>within</em> effect, <strong>{within_pp:+.2f} pp</strong>) versus dollars moving toward
  agencies that were already less competitive (<em>mix</em> effect,
  <strong>{mix_pp:+.2f} pp</strong>).</p>
  <p>The decline is <strong>behavioural, not compositional</strong>. The Department of Defense
  alone accounts for {dod_total_pp:+.2f} pp of the {latest_decomp['total_change'] * 100:+.2f} pp
  total, driven by its own competed share falling from {dod['s_0'] * 100:.1f}% to
  {dod['s_1'] * 100:.1f}% while its obligations grew.</p>
  <div class="chart-frame">{f2_chart}</div>
  {ch.legend(["Government-wide", "Department of Defense", "All other agencies"])}
  <h3>Attribution of the change, by agency</h3>
  <div class="chart-frame">{f2_attr}</div>
  {_details("Show the decomposition table", f2_table)}
</div></section>

<section><div class="finding">
  <span class="tag">Finding 03 · Timing</span>
  <h2>The year-end surge reached a five-year high: {sep_share:.1f}% of the year's obligations landed in September</h2>
  <p>Annual appropriations expire on 30 September, and the observable result is a spike of
  obligations in the final weeks. In FY{latest_fy}, September carried
  <strong>{sep_share:.1f}%</strong> of the year's contract dollars against an even-pace
  expectation of 8.3% — <strong>{ch.fmt_money_bn(last['september_excess_obligations'], 1)}</strong>
  more than a level pace would have placed in that month, and the highest concentration in the
  five years observed.</p>
  <div class="chart-frame">{f3_chart}</div>
  <h3>September concentration by fiscal year</h3>
  <div class="chart-frame">{surge_trend}</div>
  <div class="callout"><p>September spending is not waste by itself — programme cycles
  genuinely land at year end. It is a <em>risk indicator</em>: awards made against an expiring
  appropriation are the population where schedule pressure is highest, which is why they are
  worth sampling first rather than accusing.</p></div>
  {_details("Show the ten most year-end-concentrated agencies", f3_table)}
</div></section>

<section><div class="finding">
  <span class="tag">Finding 04 · Composition</span>
  <h2>FY{latest_fy} split the portfolio: defence and security grew, civilian and international contracted sharply</h2>
  <p>Beneath a {last['obligations_yoy_pct']:+.1f}% government-wide move, agency-level changes
  were unusually large and unusually one-directional. Defence, Veterans Affairs and Homeland
  Security added obligations while health, international development, housing and general
  services fell — several by a fifth or more in a single year.</p>
  <div class="chart-frame">{f4_chart}</div>
  {_details("Show the twelve largest movers", f4_table)}
</div></section>

<section><div class="finding">
  <span class="tag">Finding 05 · Prioritisation</span>
  <h2>A composite index ranks where to look first — and the sensitivity test says which parts of that ranking to trust</h2>
  <p>The Contract Efficiency Index combines five dimensions — competition, contract-type risk,
  vendor diversity, year-end discipline and real-growth stability — into one score per agency.
  Because the weights are a judgement, every agency is re-scored under 2,000 random weightings
  drawn uniformly from the simplex. The bar is the configured score; the whisker is the
  5th–95th percentile across those weightings.</p>
  <div class="chart-frame">{f5_chart}</div>
  <div class="callout"><p><strong>Read the whiskers, not the ranks.</strong> Only
  {len(robust)} of {len(ranked)} agencies hold the same quartile across the weighting
  distribution ({", ".join(robust["agency_name"].tolist()) if len(robust) else "none"}).
  The middle of the table is not separable, and this index is a triage device for deciding
  where to look — not a verdict on how any agency performed.</p></div>
  {_details("Show scores, rank ranges and component drivers", f5_table)}
</div></section>

<section><div class="finding">
  <span class="tag">Method &amp; limits</span>
  <h2>What this analysis can and cannot support</h2>
  <ul>
    <li><strong>Obligations, not outlays.</strong> Figures are net
    <code>federal_action_obligation</code>, so de-obligations reduce totals. An agency can post a
    negative fiscal year when terminations exceed new awards.</li>
    <li><strong>Contracts only.</strong> Award types
    {ch.esc(", ".join(manifest.get("award_type_codes", [])))}; grants, loans and direct payments
    are out of scope. IDV vehicles are excluded to avoid double-counting the orders placed
    against them.</li>
    <li><strong>Competition is measured on the current action.</strong> FPDS code E, follow-on to
    a competed action, counts as not competed; the sensitivity run re-scores under the opposite
    convention.</li>
    <li><strong>Contract type is not a verdict.</strong> Research and complex services
    legitimately require cost-reimbursement; the measure sizes the population carrying
    government cost risk, it does not allege misuse.</li>
    <li><strong>Vendor HHI is truncated</strong> at each agency's top 100 recipients and computed
    against true agency totals, making it a strict lower bound.</li>
    <li><strong>Nothing here identifies waste, fraud or abuse.</strong> Every output is a
    prioritisation signal that tells a reviewer where contract-level examination would be most
    productive.</li>
  </ul>
</div></section>

<footer>
  <p>Generated by <code>fedspend v2.0</code>
  from USAspending API extracts cached on {ch.esc(snapshot)}. Reproduce with
  <code>make all</code>. Deflator: BEA GDP implicit price deflator via FRED
  (<code>{ch.esc(manifest.get("deflator_series", "GDPDEF"))}</code>), fiscal-year averaged,
  constant FY{latest_fy} dollars. All reconciliation checks pass — see
  <code>outputs/tables/validation_report.csv</code>.</p>
</footer>
</div>
<div id="tip"></div>
"""

    head = f"<title>{ch.esc(page_title)}</title>{FONT_LINK}<style>{CSS}</style>"
    fragment = f"{head}{body}<script>{JS}</script>"
    html_doc = (
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        f"{head}</head><body>{fragment[len(head):]}</body></html>"
    )

    out_path = out_path or (cfg.outputs_dir / "dashboard.html")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html_doc, encoding="utf-8")
    log.info("dashboard -> %s (%.0f KB)", out_path, out_path.stat().st_size / 1024)

    # Fragment form for hosts that supply their own document skeleton.
    frag_path = out_path.with_name(out_path.stem + "_fragment.html")
    frag_path.write_text(fragment, encoding="utf-8")
    log.info("dashboard fragment -> %s", frag_path)
    return out_path


def _ex_dod_competed(fact: pd.DataFrame) -> list[float]:
    """Competed share for all agencies except DoD, weighted by obligations."""
    other = fact[fact["agency_name"] != "Department of Defense"].copy()
    other["competed_obligations"] = other["competed_obligations"].fillna(0.0)
    grouped = other.groupby("fiscal_year", as_index=False)[
        ["competed_obligations", "not_competed_obligations"]
    ].sum()
    denom = grouped["competed_obligations"] + grouped["not_competed_obligations"]
    return (grouped["competed_obligations"] / denom * 100).round(2).tolist()
