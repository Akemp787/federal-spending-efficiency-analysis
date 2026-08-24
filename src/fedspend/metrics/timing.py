"""Obligation timing within the fiscal year: the year-end spending surge.

Federal appropriations are mostly annual. Money not obligated by 30 September
expires, and an agency that returns funds risks a smaller mark next year. The
documented behavioural result is a spike of obligations in the final weeks of
the fiscal year.

The concern is not that September spending exists - contracts have to be awarded
sometime, and many programme cycles genuinely land at year end. The concern is
what the literature on expiring-funds behaviour consistently finds: awards made
under time pressure are more likely to be non-competed, less likely to be
firm-fixed-price, and rate lower on subsequent quality review. So September
concentration is a *risk indicator*, not a finding on its own - which is why
this module also cross-references September's competition rate against the rest
of the year rather than reporting the surge in isolation.

Measures
--------
``september_share``  September obligations / fiscal-year obligations.
``q4_share``         July-September obligations / fiscal-year obligations.
``surge_ratio``      September obligations / mean monthly obligations in Oct-Aug.
                     A value of 1.0 means September looked like any other month.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

SEPTEMBER_FISCAL_MONTH = 12  # fiscal month 1 is October
Q4_FISCAL_MONTHS = (10, 11, 12)  # July, August, September


def timing_profile(
    monthly: pd.DataFrame,
    group_cols: list[str],
    *,
    value_col: str = "obligations",
    fiscal_month_col: str = "fiscal_month",
) -> pd.DataFrame:
    """Year-end concentration measures for each group."""
    df = monthly.copy()
    df["positive"] = df[value_col].clip(lower=0)
    df["is_september"] = df[fiscal_month_col] == SEPTEMBER_FISCAL_MONTH
    df["is_q4"] = df[fiscal_month_col].isin(Q4_FISCAL_MONTHS)
    df["september_obligations"] = df["positive"].where(df["is_september"], 0.0)
    df["q4_obligations"] = df["positive"].where(df["is_q4"], 0.0)
    df["non_september_obligations"] = df["positive"].where(~df["is_september"], np.nan)

    grouped = df.groupby(group_cols, dropna=False)
    out = grouped.agg(
        annual_obligations=("positive", "sum"),
        september_obligations=("september_obligations", "sum"),
        q4_obligations=("q4_obligations", "sum"),
        non_september_mean=("non_september_obligations", "mean"),
        months_observed=(fiscal_month_col, "nunique"),
    ).reset_index()

    total = out["annual_obligations"]
    out["september_share"] = (out["september_obligations"] / total).where(total > 0)
    out["q4_share"] = (out["q4_obligations"] / total).where(total > 0)
    out["surge_ratio"] = (out["september_obligations"] / out["non_september_mean"]).where(
        out["non_september_mean"] > 0
    )
    # Obligations above what an even 1/12 pace would have placed in September -
    # the money that looks schedule-driven rather than requirement-driven.
    out["september_excess_obligations"] = (
        (out["september_obligations"] - total / 12.0).clip(lower=0).where(total > 0)
    )
    out = out.drop(columns=["non_september_mean"])
    return out.sort_values(group_cols).reset_index(drop=True)


def monthly_seasonality(
    monthly: pd.DataFrame,
    *,
    fy_col: str = "fiscal_year",
    fiscal_month_col: str = "fiscal_month",
    value_col: str = "obligations",
) -> pd.DataFrame:
    """Government-wide monthly pattern, indexed so 100 = an even monthly pace."""
    df = monthly.copy()
    df["positive"] = df[value_col].clip(lower=0)
    by_month = (
        df.groupby([fy_col, fiscal_month_col, "month_name"], dropna=False)["positive"]
        .sum()
        .rename("obligations")
        .reset_index()
    )
    annual = by_month.groupby(fy_col)["obligations"].sum().rename("annual_total")
    by_month = by_month.merge(annual, on=fy_col, how="left")
    by_month["share"] = by_month["obligations"] / by_month["annual_total"]
    by_month["index_vs_even_pace"] = by_month["share"] * 12.0 * 100.0
    return by_month.sort_values([fy_col, fiscal_month_col]).reset_index(drop=True)


def surge_quality_contrast(
    monthly: pd.DataFrame,
    competition_by_month: pd.DataFrame | None = None,
    *,
    fy_col: str = "fiscal_year",
) -> pd.DataFrame:
    """Compare September's competition rate against the rest of the fiscal year.

    Returns an empty frame when no month-level competition extract is supplied;
    the surge measures above stand on their own, and this contrast is the
    optional deepening that turns a timing observation into a quality claim.
    """
    if competition_by_month is None or competition_by_month.empty:
        return pd.DataFrame(
            columns=[fy_col, "window", "competed_share", "obligations"]
        )

    df = competition_by_month.copy()
    df["positive"] = df["obligations"].clip(lower=0)
    df["window"] = np.where(
        df["fiscal_month"] == SEPTEMBER_FISCAL_MONTH, "September", "October-August"
    )
    grouped = df.groupby([fy_col, "window"], dropna=False)
    out = grouped.agg(
        obligations=("positive", "sum"),
        competed=("positive", lambda s: np.nan),  # placeholder, replaced below
    ).reset_index()

    competed = (
        df[df["is_competed"]]
        .groupby([fy_col, "window"], dropna=False)["positive"]
        .sum()
        .rename("competed_obligations")
        .reset_index()
    )
    out = out.drop(columns=["competed"]).merge(competed, on=[fy_col, "window"], how="left")
    out["competed_obligations"] = out["competed_obligations"].fillna(0.0)
    out["competed_share"] = (out["competed_obligations"] / out["obligations"]).where(
        out["obligations"] > 0
    )
    return out.sort_values([fy_col, "window"]).reset_index(drop=True)
