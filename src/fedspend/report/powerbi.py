"""Builds a Power BI-ready star schema plus a theme file.

Why this is a separate export
-----------------------------
``report/exports.py`` writes the curated analysis tables as CSV. Those are correct
but they are not a *model*: they carry wide analytical columns, no conformed date
dimension, and several measures sit in wide form (one column per series) because
that is what the SVG charts consume.

Power BI wants the opposite shape. A legend-driven visual needs one row per
(category, series, value) rather than one column per series, and relationships
need a single-column key on a dimension table. Handing a reviewer the analysis
tables and calling it a Power BI deliverable pushes an hour of unpivoting onto
them, so this module does that work here where it can be tested and re-run.

Output layout (``powerbi/data``)
    dim_*        one row per entity, single-column key, no measures
    fact_*       additive measures keyed to the dimensions
    viz_*        pre-unpivoted long tables shaped for one specific visual each

Everything is deterministic given the curated tables.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from ..config import Config
from ..logging_utils import get_logger

log = get_logger(__name__)

# Categorical slots validated for colour-vision-deficiency separation and
# contrast in both light and dark modes; reused so the deck matches the HTML
# dashboard and the notebooks.
SERIES_COLOURS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#4a3aa7", "#e34948"]
POSITIVE = "#2a78d6"
NEGATIVE = "#e34948"


def _curated(cfg: Config, name: str) -> pd.DataFrame:
    return pd.read_parquet(cfg.curated_dir / f"{name}.parquet")


def _write(df: pd.DataFrame, out_dir: Path, name: str) -> Path:
    path = out_dir / f"{name}.csv"
    df.to_csv(path, index=False)
    log.info("powerbi %-34s %5d rows x %2d cols", name, len(df), df.shape[1])
    return path


# ---------------------------------------------------------------- dimensions
def build_dimensions(cfg: Config, out: Path) -> None:
    gov = _curated(cfg, "gov_summary").sort_values("fiscal_year")
    fact = _curated(cfg, "fact_agency_year")
    sub = _curated(cfg, "subagency_competition")

    latest = cfg.latest_fy
    floor = float(cfg["analysis"]["materiality_floor_usd"])

    # A fiscal-year dimension rather than a date table: every measure in this
    # model is annual, so a day-grain calendar would add rows and relationships
    # that no visual uses. Sort keys are explicit so Power BI orders correctly.
    fy = pd.DataFrame({"fiscal_year": gov["fiscal_year"].astype(int)})
    fy["fiscal_year_label"] = "FY" + fy["fiscal_year"].astype(str)
    fy["fiscal_year_start"] = pd.to_datetime(
        (fy["fiscal_year"] - 1).astype(str) + "-10-01"
    )
    fy["fiscal_year_end"] = pd.to_datetime(fy["fiscal_year"].astype(str) + "-09-30")
    fy["is_latest"] = fy["fiscal_year"] == latest
    fy["is_base"] = fy["fiscal_year"] == cfg.base_fy
    fy = fy.merge(
        gov[["fiscal_year", "real_multiplier"]].assign(
            fiscal_year=lambda d: d["fiscal_year"].astype(int)
        ),
        on="fiscal_year",
        how="left",
    )
    _write(fy, out, "dim_fiscal_year")

    latest_rows = fact[fact["fiscal_year"] == latest]
    agency = (
        fact.sort_values("fiscal_year")
        .groupby("agency_name", as_index=False)
        .agg(
            agency_code=("agency_code", "last"),
            peak_obligations=("obligations", "max"),
            latest_obligations=("obligations", "last"),
        )
    )
    agency["is_scored_in_index"] = agency["agency_name"].isin(
        latest_rows.loc[latest_rows["obligations"] >= floor, "agency_name"]
    )
    agency["size_band"] = pd.cut(
        agency["latest_obligations"],
        [-float("inf"), 0, 1e9, 1e10, 1e11, float("inf")],
        labels=["Net negative", "Under $1B", "$1B–$10B", "$10B–$100B", "Over $100B"],
    ).astype(str)
    _write(agency.sort_values("latest_obligations", ascending=False), out, "dim_agency")

    subdim = (
        sub.sort_values("fiscal_year")
        .groupby(["subagency_name", "agency_name"], as_index=False)
        .agg(
            subagency_code=("subagency_code", "last"),
            latest_obligations=("obligations", "last"),
        )
        .sort_values("latest_obligations", ascending=False)
    )
    subdim["is_military_department"] = subdim["subagency_name"].isin(
        ["Department of the Navy", "Department of the Army", "Department of the Air Force"]
    )
    # Sub-agency names are NOT unique across government - eight of them repeat,
    # because several departments run an organisation of the same name (an
    # Office of the Inspector General, an Immediate Office of the Secretary).
    # A relationship keyed on the bare name would be rejected as ambiguous, so
    # the dimension carries a composite surrogate key and every fact that joins
    # to it is given the same key.
    subdim["subagency_key"] = subdim["agency_name"] + " | " + subdim["subagency_name"]
    assert subdim["subagency_key"].is_unique, "composite sub-agency key is not unique"
    _write(
        subdim[["subagency_key", "subagency_name", "agency_name", "subagency_code",
                "latest_obligations", "is_military_department"]],
        out,
        "dim_subagency",
    )

    # A glossary table lets the report carry its own definitions page and feed
    # visual tooltips, so a viewer never meets an unexplained term.
    glossary = pd.DataFrame(
        [
            ("Obligation", "A binding commitment of federal funds. Not the same as money spent."),
            ("Competed share", "Share of obligations awarded under full and open competition or an equivalent competitive procedure."),
            ("Portfolio-adjusted rate", "Competition rate recomputed as if the agency bought the government-wide mix of goods and services. Separates practice from mission."),
            ("Within effect", "The part of a change caused by organisations changing their own behaviour."),
            ("Mix effect", "The part of a change caused by money moving between organisations."),
            ("Government-risk pricing", "Cost-reimbursement and time-and-materials contracts, where the government rather than the contractor absorbs cost overruns."),
            ("HHI", "Herfindahl-Hirschman Index, 0-10,000. Above 2,500 is 'highly concentrated' under DOJ/FTC guidelines."),
            ("September concentration", "Share of a fiscal year's obligations placed in its final month. An even pace would be 8.3%."),
            ("Contract Efficiency Index", "Composite 0-100 score across five dimensions. A triage device for where to look, not a performance verdict."),
            ("Constant FY2025 dollars", "Inflation-adjusted using the GDP price deflator, so amounts across years are comparable."),
        ],
        columns=["term", "definition"],
    )
    _write(glossary, out, "dim_glossary")


# --------------------------------------------------------------------- facts
def build_facts(cfg: Config, out: Path) -> None:
    latest = cfg.latest_fy
    fact = _curated(cfg, "fact_agency_year")
    gov = _curated(cfg, "gov_summary")

    keep = [
        "fiscal_year", "agency_name", "obligations", "obligations_real",
        "competed_obligations", "not_competed_obligations", "competed_share",
        "fixed_price_share", "cost_reimbursement_share", "labor_hour_share",
        "government_risk_share", "government_risk_obligations",
        "setaside_share", "september_obligations", "september_share", "q4_share",
        "surge_ratio", "september_excess_obligations", "vendor_hhi",
        "vendor_hhi_class", "vendor_cr4", "vendor_coverage_share",
        "change_abs", "change_pct", "change_pct_real", "real_growth_is_outlier",
        "is_material",
    ]
    _write(fact[[c for c in keep if c in fact.columns]], out, "fact_agency_year")
    _write(gov, out, "fact_government_year")
    _write(_curated(cfg, "monthly_seasonality"), out, "fact_month")
    sub_fact = _curated(cfg, "subagency_competition").copy()
    sub_fact["subagency_key"] = sub_fact["agency_name"] + " | " + sub_fact["subagency_name"]
    _write(sub_fact, out, "fact_subagency_year")
    _write(_curated(cfg, "efficiency_index"), out, "fact_efficiency_index")
    _write(_curated(cfg, "index_sensitivity"), out, "fact_index_sensitivity")
    _write(_curated(cfg, "review_shortlist"), out, "fact_review_shortlist")
    _write(_curated(cfg, "risk_migration"), out, "fact_risk_migration")
    _write(_curated(cfg, "portfolio_adjusted_competition"), out, "fact_portfolio_adjusted")
    _write(_curated(cfg, "vendor_concentration"), out, "fact_vendor_concentration")

    # Both attribution levels stacked into one table with a `level` column, so a
    # single visual can drill from department to component.
    agency_attr = _curated(cfg, "competition_decomposition").assign(
        level="Department", parent="Government-wide"
    ).rename(columns={"agency_name": "entity"})
    sub_attr = _curated(cfg, "subagency_decomposition").assign(level="Component").rename(
        columns={"subagency_name": "entity", "agency_name": "parent"}
    )
    cols = [
        "level", "parent", "entity", "w_0", "w_1", "s_0", "s_1",
        "within_effect", "mix_effect", "interaction_effect", "total_effect",
    ]
    attribution = pd.concat(
        [agency_attr[[c for c in cols if c in agency_attr.columns]],
         sub_attr[[c for c in cols if c in sub_attr.columns]]],
        ignore_index=True,
    )
    attribution["total_effect_pp"] = attribution["total_effect"] * 100
    attribution["within_effect_pp"] = attribution["within_effect"] * 100
    attribution["mix_effect_pp"] = attribution["mix_effect"] * 100
    attribution["fiscal_year"] = latest
    # Same ambiguity applies to component rows, so give attribution a key that
    # is unique whichever level a visual is filtered to.
    attribution["entity_key"] = attribution["parent"] + " | " + attribution["entity"]
    _write(attribution, out, "fact_competition_attribution")

    _write(
        _curated(cfg, "validation_report")
        if (cfg.curated_dir / "validation_report.parquet").exists()
        else pd.read_csv(cfg.tables_dir / "validation_report.csv"),
        out,
        "fact_validation",
    )


# ------------------------------------------------- pre-shaped visual sources
def build_visual_tables(cfg: Config, out: Path) -> None:
    """Long-format tables, one per visual that needs a legend series."""
    latest = cfg.latest_fy
    gov = _curated(cfg, "gov_summary").sort_values("fiscal_year")
    fact = _curated(cfg, "fact_agency_year")
    sub = _curated(cfg, "subagency_competition")
    padj = _curated(cfg, "portfolio_adjusted_competition")
    season = _curated(cfg, "monthly_seasonality")

    # 1. Nominal vs real, indexed to the base year.
    growth = pd.concat(
        [
            gov[["fiscal_year", "obligations_index_vs_base"]]
            .rename(columns={"obligations_index_vs_base": "index_value"})
            .assign(basis="Nominal dollars"),
            gov[["fiscal_year", "obligations_real_index_vs_base"]]
            .rename(columns={"obligations_real_index_vs_base": "index_value"})
            .assign(basis=f"Constant FY{latest} dollars"),
        ],
        ignore_index=True,
    )
    growth["sort_order"] = (growth["basis"] == f"Constant FY{latest} dollars").astype(int)
    _write(growth, out, "viz_growth_index")

    # 2. Competition trend: government-wide, DoD, and everyone else.
    dod = fact[fact["agency_name"] == "Department of Defense"].sort_values("fiscal_year")
    other = fact[fact["agency_name"] != "Department of Defense"].copy()
    other["competed_obligations"] = other["competed_obligations"].fillna(0.0)
    other["not_competed_obligations"] = other["not_competed_obligations"].fillna(0.0)
    og = other.groupby("fiscal_year", as_index=False)[
        ["competed_obligations", "not_competed_obligations"]
    ].sum()
    og["rate"] = og["competed_obligations"] / (
        og["competed_obligations"] + og["not_competed_obligations"]
    )
    comp_lines = pd.concat(
        [
            gov[["fiscal_year", "competed_share"]]
            .rename(columns={"competed_share": "rate"})
            .assign(series="Government-wide", sort_order=0),
            dod[["fiscal_year", "competed_share"]]
            .rename(columns={"competed_share": "rate"})
            .assign(series="Department of Defense", sort_order=1),
            og[["fiscal_year", "rate"]].assign(series="All other agencies", sort_order=2),
        ],
        ignore_index=True,
    )
    comp_lines["rate_pct"] = comp_lines["rate"] * 100
    _write(comp_lines, out, "viz_competition_trend")

    # 3. Military departments, to show Navy falling while Air Force rose.
    mil = sub[
        sub["subagency_name"].isin(
            ["Department of the Navy", "Department of the Army", "Department of the Air Force"]
        )
    ][["fiscal_year", "subagency_name", "competed_share", "obligations"]].copy()
    mil["rate_pct"] = mil["competed_share"] * 100
    mil = mil.rename(columns={"subagency_name": "series"})
    _write(mil.sort_values(["series", "fiscal_year"]), out, "viz_military_departments")

    # 4. Observed vs portfolio-adjusted, long so both dots share one axis.
    dumbbell = pd.concat(
        [
            padj[["agency_name", "observed_rate"]]
            .rename(columns={"observed_rate": "rate"})
            .assign(measure="Observed", sort_order=0),
            padj[["agency_name", "standardised_rate"]]
            .rename(columns={"standardised_rate": "rate"})
            .assign(measure="Portfolio-adjusted", sort_order=1),
        ],
        ignore_index=True,
    )
    dumbbell["rate_pct"] = dumbbell["rate"] * 100
    dumbbell = dumbbell.merge(
        padj[["agency_name", "standardised_rate", "reference_coverage"]].rename(
            columns={"standardised_rate": "sort_by_adjusted"}
        ),
        on="agency_name",
        how="left",
    )
    _write(dumbbell, out, "viz_portfolio_adjusted")

    # 5. Monthly pacing for the latest year, with the even-pace reference.
    month = season[season["fiscal_year"] == latest].sort_values("fiscal_month").copy()
    month["even_pace"] = 100.0
    month["is_september"] = month["fiscal_month"] == 12
    _write(month, out, "viz_monthly_pacing")

    # 6. Largest movers, pre-signed so conditional formatting is a single rule.
    movers = fact[(fact["fiscal_year"] == latest) & fact["prior_year"].notna()].copy()
    movers = movers[movers["prior_year"].abs() > 1e9]
    movers["change_bn"] = movers["change_abs"] / 1e9
    movers["direction"] = movers["change_bn"].apply(
        lambda v: "Increase" if v >= 0 else "Decrease"
    )
    movers = movers.reindex(
        movers["change_bn"].abs().sort_values(ascending=False).index
    ).head(14)
    _write(
        movers[
            ["agency_name", "prior_year", "obligations", "change_abs", "change_bn",
             "change_pct", "change_pct_real", "direction"]
        ],
        out,
        "viz_largest_movers",
    )

    # 7. Efficiency index with its uncertainty band, ready for an error-bar visual.
    idx = _curated(cfg, "efficiency_index")[
        ["agency_name", "efficiency_index", "rank", "obligations"]
    ]
    sens = _curated(cfg, "index_sensitivity")[
        ["agency_name", "score_p05", "score_p95", "rank_best", "rank_worst",
         "quartile_verdict"]
    ]
    band = idx.merge(sens, on="agency_name", how="left")
    band["band_low"] = band["efficiency_index"] - band["score_p05"]
    band["band_high"] = band["score_p95"] - band["efficiency_index"]
    band["is_robust"] = band["quartile_verdict"] != "not separable"
    _write(band.sort_values("efficiency_index", ascending=False), out, "viz_efficiency_index")

    # 8 & 9. Narrative tables: the two slides the deck has to end on.
    _write(_recommendations_table(latest), out, "viz_recommendations")
    _write(_limitations_table(), out, "viz_limitations")


def _recommendations_table(latest: int) -> pd.DataFrame:
    """The recommendations slide, as data rather than a text box.

    Kept as a table so the slide can be sorted, filtered and conditionally
    formatted like any other visual, and so the wording lives in version control
    next to the analysis that produced it.
    """
    rows = [
        ("R1", "Report competition at the level that awards contracts",
         "Department of the Navy", 16.2,
         "Navy drove ~70% of the government-wide decline; its rate fell 45.8% to 36.6% on $176.6B.",
         "High", 1),
        ("R2", "Test the 'we buy harder things' defence before accepting it",
         "Department of Defense", 0.0,
         "Portfolio adjustment explains only 6.1 pp of DoD's gap; 23.5 pp is practice, not mission.",
         "High", 2),
        ("R3", "Use the September surge as a sampling frame, not a finding",
         "Government-wide", 83.4,
         "September carried 19.0% of FY2025 obligations against an 8.3% even pace.",
         "Medium", 3),
        ("R4", "Track contract-type risk as an independent signal",
         "Health & Human Services", 256.5,
         "HHS cost-risk share rose 10.3 pp while its obligations fell 28.7%.",
         "Medium", 4),
        ("R5", "Use the efficiency index only at its tails, never as a ranking",
         "19 scored agencies", 0.0,
         "Only 4 of 19 agencies hold their quartile across 2,000 random weightings.",
         "High", 5),
        ("R6", "Treat vendor concentration as a data-quality priority first",
         "Concentrated agencies", 0.0,
         "Vendor HHI is truncated at the top 100 and has no corporate-family rollup.",
         "Low", 6),
    ]
    df = pd.DataFrame(
        rows,
        columns=["id", "recommendation", "population", "sizing_bn", "evidence",
                 "confidence", "sort_order"],
    )
    df["sizing_label"] = df["sizing_bn"].apply(
        lambda v: f"${v:,.1f}B" if v > 0 else "Not dollar-sized"
    )
    df["fiscal_year"] = latest
    return df


def _limitations_table() -> pd.DataFrame:
    """The limitations slide, as data. Categorised so it can be grouped."""
    rows = [
        ("Scope", "Obligations, not outlays",
         "Figures are money committed, not money spent. De-obligations are included, so an agency can post a negative year."),
        ("Scope", "Contracts only",
         "Grants, loans and direct payments are out of scope. This is a picture of federal contracting, not federal spending."),
        ("Attribution", "Awarding agency, not funding agency",
         "Where one agency buys on another's behalf, the obligation is credited to the awarding agency. This materially affects GSA."),
        ("Measurement", "Competition rate is not competition quality",
         "A competed award drawing a single bid satisfies the process without obtaining price discipline. The single-offer rate needs transaction-level data."),
        ("Measurement", "Portfolio adjustment is coarse",
         "Product categories group unlike purchases, so the 23.5 pp practice gap is an upper bound rather than a point estimate."),
        ("Measurement", "Vendor concentration is understated",
         "Computed on the top 100 recipients with no corporate-family rollup, so subsidiaries count separately."),
        ("Method", "Index weights are a judgement",
         "Only 4 of 19 agencies hold their quartile across 2,000 random weightings. The middle of the ranking is not separable."),
        ("Data", "Source data carries reporting lag",
         "Agency-reported FPDS data is corrected continuously, so recent figures can move after the snapshot date."),
        ("Interpretation", "Nothing here identifies waste, fraud or abuse",
         "Sole-source awards are frequently lawful and correct. Every output indicates where review would be most productive, not where wrongdoing occurred."),
        ("Interpretation", "No savings estimate is possible",
         "Competition affects price, but this analysis observes obligations, not prices. Converting these figures into savings would exceed the evidence."),
    ]
    df = pd.DataFrame(rows, columns=["category", "limitation", "detail"])
    df["sort_order"] = range(1, len(df) + 1)
    return df


# --------------------------------------------------------------------- theme
def build_theme(out: Path) -> Path:
    """A Power BI theme JSON carrying the validated palette and type scale."""
    theme = {
        "name": "Federal Contract Efficiency",
        "dataColors": SERIES_COLOURS,
        "background": "#FFFFFF",
        "foreground": "#0D1418",
        "tableAccent": POSITIVE,
        "good": "#0CA30C",
        "neutral": "#6D7C88",
        "bad": NEGATIVE,
        "maximum": POSITIVE,
        "center": "#F0EFEC",
        "minimum": NEGATIVE,
        "textClasses": {
            "title": {"fontFace": "Segoe UI Semibold", "fontSize": 16, "color": "#0D1418"},
            "header": {"fontFace": "Segoe UI Semibold", "fontSize": 12, "color": "#0D1418"},
            "label": {"fontFace": "Segoe UI", "fontSize": 10, "color": "#48555F"},
            "callout": {"fontFace": "Segoe UI Light", "fontSize": 36, "color": "#0D1418"},
        },
        "visualStyles": {
            "*": {
                "*": {
                    "background": [{"show": True, "color": {"solid": {"color": "#FFFFFF"}}}],
                    "border": [{"show": True, "color": {"solid": {"color": "#D8DEE5"}}, "radius": 6}],
                    "visualHeader": [{"show": False}],
                    "title": [{"show": True, "fontSize": 12, "fontColor": {"solid": {"color": "#0D1418"}}}],
                    # Recessive gridlines: the data should carry more ink than the frame.
                    "categoryAxis": [{"gridlineShow": False, "labelColor": {"solid": {"color": "#48555F"}}, "fontSize": 10}],
                    "valueAxis": [{"gridlineColor": {"solid": {"color": "#E3E8ED"}}, "labelColor": {"solid": {"color": "#48555F"}}, "fontSize": 10}],
                    "legend": [{"position": "TopCenter", "showTitle": False, "fontSize": 10, "labelColor": {"solid": {"color": "#48555F"}}}],
                }
            },
            "page": {"*": {"background": [{"color": {"solid": {"color": "#F4F6F8"}}, "transparency": 0}]}},
            "card": {"*": {"labels": [{"fontSize": 32, "color": {"solid": {"color": "#0D1418"}}}],
                            "categoryLabels": [{"fontSize": 10, "color": {"solid": {"color": "#6D7C88"}}}]}},
            "lineChart": {"*": {"lineStyles": [{"strokeWidth": 3, "showMarker": True, "markerSize": 5}]}},
            "slicer": {"*": {"header": [{"show": True, "fontColor": {"solid": {"color": "#48555F"}}}]}},
        },
    }
    path = out / "fedspend_theme.json"
    path.write_text(json.dumps(theme, indent=2), encoding="utf-8")
    log.info("powerbi theme -> %s", path.name)
    return path


# ----------------------------------------------------------------- orchestrate
def build_powerbi_package(cfg: Config) -> Path:
    """Write the whole Power BI package under ``powerbi/``."""
    root = cfg.root / "powerbi"
    data = root / "data"
    data.mkdir(parents=True, exist_ok=True)

    build_dimensions(cfg, data)
    build_facts(cfg, data)
    build_visual_tables(cfg, data)
    build_theme(root)

    n = len(list(data.glob("*.csv")))
    log.info("Power BI package complete: %d tables -> %s", n, data)
    return root
