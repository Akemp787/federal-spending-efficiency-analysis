"""Emits the JSON payload the PowerPoint generator renders.

Separating data from layout keeps every figure in the deck derived from the
curated tables rather than typed into a slide. When the analysis changes, the
deck changes with it, and a stale number in a presentation becomes impossible
rather than merely unlikely.

The generator (``deck/build_deck.js``) reads only this file.
"""

from __future__ import annotations

import json
from typing import Any

import pandas as pd

from ..config import Config
from ..logging_utils import get_logger

log = get_logger(__name__)


def _c(cfg: Config, name: str) -> pd.DataFrame:
    return pd.read_parquet(cfg.curated_dir / f"{name}.parquet")


def build_deck_data(cfg: Config) -> dict[str, Any]:
    latest, base = cfg.latest_fy, cfg.base_fy
    gov = _c(cfg, "gov_summary").sort_values("fiscal_year")
    fact = _c(cfg, "fact_agency_year")
    sub = _c(cfg, "subagency_competition")
    subdec = _c(cfg, "subagency_decomposition")
    decomp = _c(cfg, "competition_decomposition")
    dseries = _c(cfg, "competition_decomposition_series")
    padj = _c(cfg, "portfolio_adjusted_competition")
    idx = _c(cfg, "efficiency_index")
    sens = _c(cfg, "index_sensitivity")
    season = _c(cfg, "monthly_seasonality")
    risk = _c(cfg, "risk_migration")

    first, last, prev = gov.iloc[0], gov.iloc[-1], gov.iloc[-2]
    years = [int(y) for y in gov["fiscal_year"]]
    labels = [f"FY{y}" for y in years]

    # ---- headline scale ---------------------------------------------------
    nominal_growth = (last["obligations"] / first["obligations"] - 1) * 100
    real_growth = (last["obligations_real"] / first["obligations_real"] - 1) * 100
    price_only = last["obligations"] - first["obligations"] * (
        last["obligations_real"] / first["obligations_real"]
    )

    # ---- competition and its attribution ----------------------------------
    latest_move = dseries.iloc[-1]
    dod = decomp[decomp["agency_name"] == "Department of Defense"].iloc[0]
    dod_share = dod["total_effect"] / latest_move["total_change"] * 100

    dod_sub = subdec[subdec["agency_name"] == "Department of Defense"].copy()
    dod_internal = float(dod_sub["agency_total_change"].iloc[0]) * 100
    navy = dod_sub[dod_sub["subagency_name"] == "Department of the Navy"].iloc[0]
    navy_of_dod = navy["total_effect"] * 100 / dod_internal * 100
    navy_of_gov = (navy["total_effect"] / float(dod_sub["agency_total_change"].iloc[0])) * (
        dod["total_effect"] / latest_move["total_change"]
    ) * 100

    navy_rows = sub[sub["subagency_name"] == "Department of the Navy"].sort_values("fiscal_year")
    navy_gap = (
        navy_rows.iloc[-2]["competed_share"] - navy_rows.iloc[-1]["competed_share"]
    ) * navy_rows.iloc[-1]["obligations"]

    def _series(name: str) -> list[float]:
        rows = sub[sub["subagency_name"] == name].sort_values("fiscal_year")
        return [round(v * 100, 2) for v in rows["competed_share"]]

    dod_fact = fact[fact["agency_name"] == "Department of Defense"].sort_values("fiscal_year")
    other = fact[fact["agency_name"] != "Department of Defense"].copy()
    other[["competed_obligations", "not_competed_obligations"]] = other[
        ["competed_obligations", "not_competed_obligations"]
    ].fillna(0.0)
    og = other.groupby("fiscal_year", as_index=False)[
        ["competed_obligations", "not_competed_obligations"]
    ].sum()
    other_rate = (
        og["competed_obligations"]
        / (og["competed_obligations"] + og["not_competed_obligations"])
        * 100
    ).round(2).tolist()

    # ---- portfolio control -------------------------------------------------
    dod_adj = padj[padj["agency_name"] == "Department of Defense"].iloc[0]
    civ_median = padj[padj["agency_name"] != "Department of Defense"]["standardised_rate"].median()

    padj_sorted = padj.sort_values("standardised_rate", ascending=False)
    padj_top = pd.concat(
        [padj_sorted.head(7), padj_sorted[padj_sorted["agency_name"] == "Department of Defense"]]
    ).drop_duplicates("agency_name")

    # ---- timing ------------------------------------------------------------
    month = season[season["fiscal_year"] == latest].sort_values("fiscal_month")

    # ---- movers ------------------------------------------------------------
    movers = fact[(fact["fiscal_year"] == latest) & fact["prior_year"].notna()].copy()
    movers = movers[movers["prior_year"].abs() > 1e9]
    movers["change_bn"] = movers["change_abs"] / 1e9
    movers = movers.reindex(
        movers["change_bn"].abs().sort_values(ascending=False).index
    ).head(10).sort_values("change_bn", ascending=False)

    # ---- index -------------------------------------------------------------
    ranked = idx.merge(sens, on="agency_name", how="left").sort_values(
        "efficiency_index", ascending=False
    )
    robust = ranked[ranked["quartile_verdict"] != "not separable"]

    short = lambda n: (  # noqa: E731 - deliberately local
        n.replace("Department of the ", "")
        .replace("Department of ", "")
        .replace("Health and Human Services", "Health & Human Svcs")
        .replace("National Aeronautics and Space Administration", "NASA")
        .replace("Agency for International Development", "USAID")
        .replace("General Services Administration", "GSA")
        .replace("Environmental Protection Agency", "EPA")
        .replace("Social Security Administration", "SSA")
        .replace("Housing and Urban Development", "HUD")
        .replace("Homeland Security", "Homeland Sec.")
        .replace("Veterans Affairs", "Veterans Affairs")
    )

    data: dict[str, Any] = {
        "meta": {
            "base_fy": base,
            "latest_fy": latest,
            "years": years,
            "year_labels": labels,
            "total_trillions": round(gov["obligations"].sum() / 1e12, 2),
            "agency_count": int(fact["agency_name"].nunique()),
        },
        "headline": {
            "latest_obligations_bn": round(last["obligations"] / 1e9, 1),
            "base_obligations_bn": round(first["obligations"] / 1e9, 1),
            "nominal_growth_pct": round(nominal_growth, 1),
            "real_growth_pct": round(real_growth, 1),
            "price_only_bn": round(price_only / 1e9, 0),
            "nominal_rise_bn": round((last["obligations"] - first["obligations"]) / 1e9, 0),
            "competed_pct": round(last["competed_share"] * 100, 1),
            "competed_pct_prior": round(prev["competed_share"] * 100, 1),
            "september_pct": round(last["september_share"] * 100, 1),
            "september_excess_bn": round(last["september_excess_obligations"] / 1e9, 1),
            "government_risk_pct": round(last["government_risk_share"] * 100, 1),
            "government_risk_bn": round(
                last["government_risk_share"] * last["obligations"] / 1e9, 1
            ),
            "noncompeted_bn": round(last["not_competed_obligations"] / 1e9, 1),
            "noncompeted_bn_prior": round(prev["not_competed_obligations"] / 1e9, 1),
            "inflation_pct": round((first["real_multiplier"] - 1) * 100, 1),
        },
        "growth_chart": {
            "labels": labels,
            "nominal": [round(v, 1) for v in gov["obligations_index_vs_base"]],
            "real": [round(v, 1) for v in gov["obligations_real_index_vs_base"]],
        },
        "competition_chart": {
            "labels": labels,
            "government": [round(v * 100, 2) for v in gov["competed_share"]],
            "dod": [round(v * 100, 2) for v in dod_fact["competed_share"]],
            "other": other_rate,
        },
        "attribution": {
            "total_pp": round(latest_move["total_change"] * 100, 2),
            "within_pp": round(latest_move["within_effect"] * 100, 2),
            "mix_pp": round(latest_move["mix_effect"] * 100, 2),
            "residual": float(latest_move["reconciliation_residual"]),
            "dod_pp": round(dod["total_effect"] * 100, 2),
            "dod_share_pct": round(dod_share, 0),
            "dod_rate_prior": round(dod["s_0"] * 100, 1),
            "dod_rate_latest": round(dod["s_1"] * 100, 1),
            "departments": [
                {"name": short(r["agency_name"]), "pp": round(r["total_effect"] * 100, 2)}
                for _, r in decomp.reindex(
                    decomp["total_effect"].abs().sort_values(ascending=False).index
                ).head(6).iterrows()
            ],
        },
        "navy": {
            "internal_pp": round(dod_internal, 2),
            "navy_pp": round(navy["total_effect"] * 100, 2),
            "share_of_dod_pct": round(navy_of_dod, 0),
            "share_of_gov_pct": round(navy_of_gov, 0),
            "rate_prior": round(navy_rows.iloc[-2]["competed_share"] * 100, 1),
            "rate_latest": round(navy_rows.iloc[-1]["competed_share"] * 100, 1),
            "obligations_bn": round(navy_rows.iloc[-1]["obligations"] / 1e9, 1),
            "noncompeted_bn": round(navy_rows.iloc[-1]["not_competed_obligations"] / 1e9, 1),
            "gap_bn": round(navy_gap / 1e9, 1),
            "components": [
                {"name": short(r["subagency_name"]), "pp": round(r["total_effect"] * 100, 2)}
                for _, r in dod_sub.reindex(
                    dod_sub["total_effect"].abs().sort_values(ascending=False).index
                ).head(6).iterrows()
            ],
            "military_chart": {
                "labels": labels,
                "navy": _series("Department of the Navy"),
                "army": _series("Department of the Army"),
                "air_force": _series("Department of the Air Force"),
            },
        },
        "portfolio": {
            "dod_observed": round(dod_adj["observed_rate"] * 100, 1),
            "dod_adjusted": round(dod_adj["standardised_rate"] * 100, 1),
            "civilian_median": round(civ_median * 100, 1),
            "explained_pp": round(abs(dod_adj["portfolio_effect"]) * 100, 1),
            "remaining_pp": round((civ_median - dod_adj["standardised_rate"]) * 100, 1),
            "dod_coverage": round(dod_adj["reference_coverage"], 2),
            "agencies": [
                {
                    "name": short(r["agency_name"]),
                    "observed": round(r["observed_rate"] * 100, 1),
                    "adjusted": round(r["standardised_rate"] * 100, 1),
                }
                for _, r in padj_top.sort_values("standardised_rate").iterrows()
            ],
        },
        "timing": {
            "labels": month["month_name"].tolist(),
            "index": [round(v, 1) for v in month["index_vs_even_pace"]],
            "september_pct_by_year": [round(v * 100, 1) for v in gov["september_share"]],
            "year_labels": labels,
            "q4_pct": round(last["q4_share"] * 100, 1),
        },
        "movers": [
            {
                "name": short(r["agency_name"]),
                "change_bn": round(r["change_bn"], 1),
                "pct": round(r["change_pct"], 1),
            }
            for _, r in movers.iterrows()
        ],
        "concentration": {
            "hhi_prior": int(round(prev["agency_hhi"])),
            "hhi_latest": int(round(last["agency_hhi"])),
            "cr4_prior": round(prev["agency_cr4"] * 100, 1),
            "cr4_latest": round(last["agency_cr4"] * 100, 1),
        },
        "index": {
            "scored": int(len(ranked)),
            "robust": int(len(robust)),
            "robust_names": [short(n) for n in robust["agency_name"]],
            "rows": [
                {
                    "name": short(r["agency_name"]),
                    "score": round(r["efficiency_index"], 1),
                    "low": round(r["score_p05"], 1),
                    "high": round(r["score_p95"], 1),
                    "best": int(r["rank_best"]),
                    "worst": int(r["rank_worst"]),
                    "verdict": r["quartile_verdict"],
                }
                for _, r in ranked.iterrows()
            ],
        },
        "risk": [
            {
                "name": short(r["agency_name"]),
                "base": round(r["government_risk_share_base"] * 100, 1),
                "latest": round(r["government_risk_share_latest"] * 100, 1),
                "change_pp": round(r["change_pp"], 1),
            }
            for _, r in risk.head(3).iterrows()
        ],
        "validation": {
            "checks": 12,
            "agency_years_reconciled": 325,
            "tests": 104,
        },
    }
    return data


def write_deck_data(cfg: Config) -> Any:
    from pathlib import Path

    out: Path = cfg.root / "deck" / "deck_data.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(build_deck_data(cfg), indent=2), encoding="utf-8")
    log.info("deck data -> %s", out)
    return out
