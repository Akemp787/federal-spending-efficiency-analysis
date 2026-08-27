"""Turns the interim extracts into the curated analytical tables.

This is the layer where raw cross-tabs become the things a decision-maker reads:
an agency-year fact table, a government-wide summary, the efficiency index, and
the review shortlist. Everything it writes is deterministic given the interim
parquet files, so the published numbers can always be regenerated.
"""

from __future__ import annotations

import pandas as pd

from .config import Config
from .logging_utils import get_logger
from .metrics import (
    anomaly,
    competition,
    concentration,
    decomposition,
    efficiency_index,
    growth,
    timing,
)
from .metrics import pricing_risk as pricing
from .metrics import standardization as stdz
from .transform.deflator import deflate

log = get_logger(__name__)

CURATED_FILES = {
    "fact_agency_year": "fact_agency_year.parquet",
    "gov_summary": "gov_summary.parquet",
    "monthly_seasonality": "monthly_seasonality.parquet",
    "vendor_concentration": "vendor_concentration.parquet",
    "top_vendors": "top_vendors.parquet",
    "agency_trend": "agency_trend.parquet",
    "efficiency_index": "efficiency_index.parquet",
    "index_sensitivity": "index_sensitivity.parquet",
    "index_weighting_comparison": "index_weighting_comparison.parquet",
    "review_shortlist": "review_shortlist.parquet",
    "competition_mix": "competition_mix.parquet",
    "pricing_detail": "pricing_detail.parquet",
    "risk_migration": "risk_migration.parquet",
    "contribution_to_change": "contribution_to_change.parquet",
    "noncompeted_exposure": "noncompeted_exposure.parquet",
    "category_naics": "category_naics.parquet",
    "category_psc": "category_psc.parquet",
    "category_state": "category_state.parquet",
    "competition_decomposition": "competition_decomposition.parquet",
    "competition_decomposition_series": "competition_decomposition_series.parquet",
    "risk_decomposition_series": "risk_decomposition_series.parquet",
    "subagency_competition": "subagency_competition.parquet",
    "subagency_decomposition": "subagency_decomposition.parquet",
    "portfolio_adjusted_competition": "portfolio_adjusted_competition.parquet",
    "portfolio_stratum_detail": "portfolio_stratum_detail.parquet",
}


def _read(cfg: Config, name: str) -> pd.DataFrame:
    return pd.read_parquet(cfg.interim_dir / name)


def _save(df: pd.DataFrame, cfg: Config, key: str) -> pd.DataFrame:
    path = cfg.curated_dir / CURATED_FILES[key]
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False)
    log.info("curated %-28s %6d rows -> %s", key, len(df), path.name)
    return df


# ---------------------------------------------------------------------------
def build_fact_agency_year(cfg: Config) -> pd.DataFrame:
    """One row per agency per fiscal year, carrying every derived measure."""
    agency = _read(cfg, "agency_fy.parquet")
    deflator = _read(cfg, "deflator_fy.parquet")
    comp = _read(cfg, "agency_fy_competition.parquet")
    price = _read(cfg, "agency_fy_pricing.parquet")
    setaside = _read(cfg, "agency_fy_setaside.parquet")
    monthly = _read(cfg, "agency_fy_month.parquet")
    agency_vendor = _read(cfg, "agency_vendor_fy.parquet")

    fact = deflate(agency, deflator, "obligations")

    # competition ---------------------------------------------------------
    comp_agg = competition.competed_share(comp, ["fiscal_year", "agency_name"])
    fact = fact.merge(
        comp_agg[
            [
                "fiscal_year",
                "agency_name",
                "competed_obligations",
                "not_competed_obligations",
                "competed_share",
            ]
        ],
        on=["fiscal_year", "agency_name"],
        how="left",
    )

    # pricing risk --------------------------------------------------------
    price_agg = pricing.pricing_mix(price, ["fiscal_year", "agency_name"])
    fact = fact.merge(
        price_agg[
            [
                "fiscal_year",
                "agency_name",
                "fixed_price_share",
                "cost_reimbursement_share",
                "labor_hour_share",
                "government_risk_share",
                "government_risk_obligations",
            ]
        ],
        on=["fiscal_year", "agency_name"],
        how="left",
    )

    # small-business set-aside -------------------------------------------
    fact = fact.merge(setaside, on=["fiscal_year", "agency_name"], how="left")
    fact["setaside_obligations"] = fact["setaside_obligations"].fillna(0.0)
    fact["setaside_share"] = (fact["setaside_obligations"] / fact["obligations"]).where(
        fact["obligations"] > 0
    )

    # obligation timing ---------------------------------------------------
    time_agg = timing.timing_profile(monthly, ["fiscal_year", "agency_name"])
    fact = fact.merge(
        time_agg[
            [
                "fiscal_year",
                "agency_name",
                "september_obligations",
                "september_share",
                "q4_share",
                "surge_ratio",
                "september_excess_obligations",
            ]
        ],
        on=["fiscal_year", "agency_name"],
        how="left",
    )

    # vendor concentration within the agency ------------------------------
    vendor_conc = concentration.concentration_profile(
        agency_vendor,
        ["fiscal_year", "agency_name"],
        "obligations",
        totals=agency[["fiscal_year", "agency_name", "obligations"]],
        total_col="obligations",
    )
    fact = fact.merge(
        vendor_conc[
            [
                "fiscal_year",
                "agency_name",
                "hhi",
                "hhi_normalized",
                "hhi_class",
                "gini",
                "cr1",
                "cr4",
                "cr10",
                "coverage_share",
                "participants_observed",
            ]
        ].rename(
            columns={
                "hhi": "vendor_hhi",
                "hhi_normalized": "hhi_normalized",
                "hhi_class": "vendor_hhi_class",
                "gini": "vendor_gini",
                "cr1": "vendor_cr1",
                "cr4": "vendor_cr4",
                "cr10": "vendor_cr10",
                "coverage_share": "vendor_coverage_share",
                "participants_observed": "vendors_observed",
            }
        ),
        on=["fiscal_year", "agency_name"],
        how="left",
    )

    # growth --------------------------------------------------------------
    fact = growth.year_over_year(fact, ["agency_name"], "obligations")
    fact = growth.year_over_year(
        fact, ["agency_name"], "obligations_real", suffix="_real"
    )

    # outlier flags, scoped within each fiscal year -----------------------
    fact = anomaly.flag_outliers(
        fact, "change_pct_real", within=["fiscal_year"],
        threshold=float(cfg["analysis"]["anomaly_robust_z_threshold"]),
        prefix="real_growth",
    )

    floor = float(cfg["analysis"]["materiality_floor_usd"])
    peak = fact.groupby("agency_name")["obligations"].transform("max")
    fact["is_material"] = peak >= floor
    return fact.sort_values(["fiscal_year", "obligations"], ascending=[True, False]).reset_index(
        drop=True
    )


def build_gov_summary(cfg: Config, fact: pd.DataFrame) -> pd.DataFrame:
    """Government-wide headline series - the numbers the executive summary opens with."""
    comp = _read(cfg, "agency_fy_competition.parquet")
    price = _read(cfg, "agency_fy_pricing.parquet")
    monthly = _read(cfg, "agency_fy_month.parquet")
    setaside = _read(cfg, "agency_fy_setaside.parquet")
    deflator = _read(cfg, "deflator_fy.parquet")
    vendors = _read(cfg, "vendor_fy.parquet")
    agency = _read(cfg, "agency_fy.parquet")

    totals = agency.groupby("fiscal_year", as_index=False)["obligations"].sum()
    summary = deflate(totals, deflator, "obligations")

    summary = summary.merge(
        competition.competed_share(comp, ["fiscal_year"])[
            ["fiscal_year", "competed_share", "competed_obligations", "not_competed_obligations"]
        ],
        on="fiscal_year",
        how="left",
    )
    summary = summary.merge(
        pricing.pricing_mix(price, ["fiscal_year"])[
            [
                "fiscal_year",
                "fixed_price_share",
                "cost_reimbursement_share",
                "labor_hour_share",
                "government_risk_share",
            ]
        ],
        on="fiscal_year",
        how="left",
    )
    summary = summary.merge(
        timing.timing_profile(monthly, ["fiscal_year"])[
            [
                "fiscal_year",
                "september_share",
                "q4_share",
                "surge_ratio",
                "september_excess_obligations",
            ]
        ],
        on="fiscal_year",
        how="left",
    )

    sa = setaside.groupby("fiscal_year", as_index=False)["setaside_obligations"].sum()
    summary = summary.merge(sa, on="fiscal_year", how="left")
    summary["setaside_share"] = summary["setaside_obligations"] / summary["obligations"]

    # agency-level and vendor-level concentration of the whole market
    agency_conc = concentration.concentration_profile(
        agency, ["fiscal_year"], "obligations"
    )[["fiscal_year", "hhi", "cr1", "cr4", "cr10", "gini"]].rename(
        columns={
            "hhi": "agency_hhi",
            "cr1": "agency_cr1",
            "cr4": "agency_cr4",
            "cr10": "agency_cr10",
            "gini": "agency_gini",
        }
    )
    summary = summary.merge(agency_conc, on="fiscal_year", how="left")

    vendor_conc = concentration.concentration_profile(
        vendors, ["fiscal_year"], "obligations", totals=totals, total_col="obligations"
    )[["fiscal_year", "hhi", "cr10", "coverage_share"]].rename(
        columns={
            "hhi": "vendor_hhi_top100",
            "cr10": "vendor_cr10",
            "coverage_share": "vendor_coverage_share",
        }
    )
    summary = summary.merge(vendor_conc, on="fiscal_year", how="left")

    summary = growth.year_over_year(summary, [], "obligations") if False else summary
    summary = summary.sort_values("fiscal_year").reset_index(drop=True)
    for col in ("obligations", "obligations_real"):
        summary[f"{col}_yoy_pct"] = summary[col].pct_change() * 100.0
    base = summary.iloc[0]
    summary["obligations_index_vs_base"] = summary["obligations"] / base["obligations"] * 100.0
    summary["obligations_real_index_vs_base"] = (
        summary["obligations_real"] / base["obligations_real"] * 100.0
    )
    return summary


def build_efficiency_index(cfg: Config, fact: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Score the material agencies on the latest fiscal year."""
    latest = cfg.latest_fy
    floor = float(cfg["analysis"]["materiality_floor_usd"])

    # The index population is agencies that were material *in the scored year*,
    # which is stricter than the `is_material` flag on the fact table (that flag
    # uses peak obligations across the window, so trend analysis can still see
    # agencies that have since collapsed). Ranking a percentage metric computed
    # on a $111M base against one computed on a $492B base is not a comparison,
    # and an agency whose net obligations are negative has no denominator at all.
    scored_pop = fact[
        (fact["fiscal_year"] == latest) & (fact["obligations"] >= floor)
    ].copy()
    log.info(
        "efficiency index scored on %d agencies with >= $%.1fB in FY%d",
        len(scored_pop),
        floor / 1e9,
        latest,
    )

    trend = growth.trend_summary(
        fact[fact["agency_name"].isin(scored_pop["agency_name"])], ["agency_name"]
    ).set_index("agency_name")

    raw = efficiency_index.build_raw_dimensions(
        competed=scored_pop[["agency_name", "competed_share"]],
        pricing=scored_pop[["agency_name", "government_risk_share"]],
        vendor_conc=scored_pop[["agency_name", "hhi_normalized"]],
        timing=scored_pop[["agency_name", "september_share"]],
        trend=trend.reset_index()[["agency_name", "yoy_real_volatility_pp"]],
    )

    weights = dict(cfg["efficiency_index"]["weights"])
    winsor = tuple(cfg["efficiency_index"]["winsorize"])
    scored = efficiency_index.score_index(raw, weights, winsor=winsor)

    scored = scored.merge(
        scored_pop[
            [
                "agency_name",
                "obligations",
                "obligations_real",
                "competed_share",
                "government_risk_share",
                "september_share",
                "vendor_hhi",
                "hhi_normalized",
                "vendor_cr4",
                "setaside_share",
            ]
        ],
        on="agency_name",
        how="left",
    )
    scored["fiscal_year"] = latest

    sens_cfg = cfg["efficiency_index"]["sensitivity"]
    sensitivity = efficiency_index.weight_sensitivity(
        raw, n_draws=int(sens_cfg["n_random_weightings"]), winsor=winsor
    )

    weightings = {"configured": weights}
    if sens_cfg.get("equal_weights"):
        n = len(efficiency_index.DIMENSIONS)
        weightings["equal"] = {d: 1.0 / n for d in efficiency_index.DIMENSIONS}
    weightings["competition_only"] = {
        d: (1.0 if d == "competition" else 0.0) for d in efficiency_index.DIMENSIONS
    }
    weightings["risk_weighted"] = {
        "competition": 0.40,
        "pricing_risk": 0.35,
        "vendor_diversity": 0.15,
        "spend_discipline": 0.10,
        "stability": 0.0,
    }
    comparison = efficiency_index.compare_weightings(raw, weightings, winsor=winsor)

    return {
        "efficiency_index": scored,
        "index_sensitivity": sensitivity,
        "index_weighting_comparison": comparison,
    }


def build_review_shortlist(cfg: Config, fact: pd.DataFrame, scored: pd.DataFrame) -> pd.DataFrame:
    """Rank agencies for review on scale x risk, and size the exposure in dollars."""
    latest = cfg.latest_fy
    latest_fact = fact[fact["is_material"] & (fact["fiscal_year"] == latest)].copy()

    shortlist = latest_fact[
        [
            "agency_name",
            "obligations",
            "obligations_real",
            "competed_share",
            "not_competed_obligations",
            "government_risk_share",
            "government_risk_obligations",
            "september_share",
            "september_excess_obligations",
            "vendor_hhi",
            "vendor_cr4",
            "change_pct_real",
            "real_growth_robust_z",
            "real_growth_is_outlier",
        ]
    ].merge(
        scored[["agency_name", "efficiency_index", "rank", "quartile"]],
        on="agency_name",
        how="left",
    )

    shortlist = anomaly.priority_matrix(
        shortlist,
        scale_col="obligations",
        signal_col="not_competed_obligations",
        scale_label="spend",
        signal_label="non-competed exposure",
    )

    # A single, explicitly-defined exposure figure per agency: dollars that are
    # non-competed, government-risk-priced, or obligated above an even pace in
    # September. These overlap, so the components are kept separate and the
    # combined column is deliberately named as an upper bound.
    shortlist["exposure_upper_bound"] = shortlist[
        ["not_competed_obligations", "government_risk_obligations", "september_excess_obligations"]
    ].max(axis=1)
    return shortlist.sort_values(
        ["is_priority", "not_competed_obligations"], ascending=[False, False]
    ).reset_index(drop=True)


# ---------------------------------------------------------------------------
def run_analysis(cfg: Config) -> dict[str, pd.DataFrame]:
    """Build and persist every curated table."""
    cfg.ensure_dirs()
    out: dict[str, pd.DataFrame] = {}

    fact = build_fact_agency_year(cfg)
    out["fact_agency_year"] = _save(fact, cfg, "fact_agency_year")
    out["gov_summary"] = _save(build_gov_summary(cfg, fact), cfg, "gov_summary")

    monthly = _read(cfg, "agency_fy_month.parquet")
    out["monthly_seasonality"] = _save(
        timing.monthly_seasonality(monthly), cfg, "monthly_seasonality"
    )

    agency = _read(cfg, "agency_fy.parquet")
    agency_vendor = _read(cfg, "agency_vendor_fy.parquet")
    out["vendor_concentration"] = _save(
        concentration.concentration_profile(
            agency_vendor,
            ["fiscal_year", "agency_name"],
            "obligations",
            totals=agency[["fiscal_year", "agency_name", "obligations"]],
        ),
        cfg,
        "vendor_concentration",
    )
    out["top_vendors"] = _save(
        _read(cfg, "vendor_fy.parquet").query(
            f"rank <= {int(cfg['analysis']['top_n_vendors'])}"
        ),
        cfg,
        "top_vendors",
    )

    floor = float(cfg["analysis"]["materiality_floor_usd"])
    material = fact[fact["is_material"]]
    out["agency_trend"] = _save(
        growth.trend_summary(material, ["agency_name"]), cfg, "agency_trend"
    )
    out["contribution_to_change"] = _save(
        growth.contribution_to_change(
            fact, "agency_name", "obligations_real", base_fy=cfg.base_fy, latest_fy=cfg.latest_fy
        ),
        cfg,
        "contribution_to_change",
    )

    index_tables = build_efficiency_index(cfg, fact)
    for key, df in index_tables.items():
        out[key] = _save(df, cfg, key)

    out["review_shortlist"] = _save(
        build_review_shortlist(cfg, fact, index_tables["efficiency_index"]),
        cfg,
        "review_shortlist",
    )

    # ---- why the government-wide competition rate moved --------------------
    decomp_input = fact[
        ["fiscal_year", "agency_name", "obligations", "competed_share", "government_risk_share"]
    ].dropna(subset=["competed_share"])
    contributions, _ = decomposition.shift_share(
        decomp_input,
        group_col="agency_name",
        weight_col="obligations",
        rate_col="competed_share",
        base_period=cfg.latest_fy - 1,
        latest_period=cfg.latest_fy,
    )
    out["competition_decomposition"] = _save(
        contributions, cfg, "competition_decomposition"
    )
    out["competition_decomposition_series"] = _save(
        decomposition.shift_share_series(
            decomp_input,
            group_col="agency_name",
            weight_col="obligations",
            rate_col="competed_share",
        ),
        cfg,
        "competition_decomposition_series",
    )
    out["risk_decomposition_series"] = _save(
        decomposition.shift_share_series(
            decomp_input.dropna(subset=["government_risk_share"]),
            group_col="agency_name",
            weight_col="obligations",
            rate_col="government_risk_share",
        ),
        cfg,
        "risk_decomposition_series",
    )

    comp = _read(cfg, "agency_fy_competition.parquet")
    out["competition_mix"] = _save(
        competition.competition_mix(comp, ["fiscal_year"]), cfg, "competition_mix"
    )
    out["noncompeted_exposure"] = _save(
        competition.noncompeted_dollar_exposure(
            competition.competed_share(
                comp[comp["agency_name"].isin(material["agency_name"].unique())],
                ["fiscal_year", "agency_name"],
            )
        ),
        cfg,
        "noncompeted_exposure",
    )

    price = _read(cfg, "agency_fy_pricing.parquet")
    out["pricing_detail"] = _save(
        pricing.pricing_detail(price, ["fiscal_year"]), cfg, "pricing_detail"
    )
    out["risk_migration"] = _save(
        pricing.risk_migration(
            pricing.pricing_mix(
                price[price["agency_name"].isin(material["agency_name"].unique())],
                ["fiscal_year", "agency_name"],
            ),
            base_fy=cfg.base_fy,
            latest_fy=cfg.latest_fy,
        ),
        cfg,
        "risk_migration",
    )

    # ---- sub-agency: where contracting is actually run ---------------------
    sub = _read(cfg, "subagency_fy.parquet")
    sub["competed_share"] = (
        sub["competed_obligations"].clip(lower=0) / sub["obligations"].clip(lower=0)
    ).where(sub["obligations"] > 0)
    sub["not_competed_obligations"] = (
        sub["obligations"].clip(lower=0) - sub["competed_obligations"].clip(lower=0)
    )
    out["subagency_competition"] = _save(sub, cfg, "subagency_competition")

    # Decompose each department's own competition move across its components.
    frames = []
    for agency, grp in sub.dropna(subset=["competed_share"]).groupby("agency_name"):
        if grp["fiscal_year"].nunique() < 2 or grp["subagency_name"].nunique() < 2:
            continue
        contrib, summary = decomposition.shift_share(
            grp,
            group_col="subagency_name",
            weight_col="obligations",
            rate_col="competed_share",
            base_period=cfg.latest_fy - 1,
            latest_period=cfg.latest_fy,
        )
        contrib["agency_name"] = agency
        contrib["agency_total_change"] = summary["total_change"]
        frames.append(contrib)
    out["subagency_decomposition"] = _save(
        pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(),
        cfg,
        "subagency_decomposition",
    )

    # ---- portfolio-adjusted competition ------------------------------------
    psc = _read(cfg, "agency_psc_fy.parquet")
    scored = set(
        fact[(fact["fiscal_year"] == cfg.latest_fy) & (fact["obligations"] >= floor)][
            "agency_name"
        ]
    )
    psc_latest = stdz.prepare_strata(
        psc[(psc["fiscal_year"] == cfg.latest_fy) & (psc["agency_name"].isin(scored))]
    )
    adjusted = stdz.standardise_rate(psc_latest)
    adjusted["fiscal_year"] = cfg.latest_fy
    out["portfolio_adjusted_competition"] = _save(
        adjusted, cfg, "portfolio_adjusted_competition"
    )
    out["portfolio_stratum_detail"] = _save(
        stdz.stratum_detail(psc_latest), cfg, "portfolio_stratum_detail"
    )

    for key, fname in (
        ("category_naics", "naics_fy.parquet"),
        ("category_psc", "psc_fy.parquet"),
        ("category_state", "state_fy.parquet"),
    ):
        out[key] = _save(_read(cfg, fname), cfg, key)

    log.info("analysis complete: %d curated tables", len(out))
    return out
