"""Growth, trend, and volatility - measured in constant dollars.

Every rate in this module is available in both nominal and real terms, and the
real series is the one the findings cite. Over FY2021-FY2025 the GDP deflator
rose about 18%, so an agency whose nominal obligations grew 18% did not grow at
all. Reporting nominal growth alone would attribute the price level to
management.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def year_over_year(
    df: pd.DataFrame,
    group_cols: list[str],
    value_col: str,
    *,
    fy_col: str = "fiscal_year",
    suffix: str = "",
) -> pd.DataFrame:
    """Append absolute and percentage year-over-year change within each group.

    Percentage change is suppressed where the prior year is non-positive: a
    growth rate off a zero or negative base is arithmetically defined but
    analytically meaningless, and publishing a 40,000% jump because an agency
    obligated $12k in the base year is how a portfolio project loses credibility.
    """
    out = df.sort_values([*group_cols, fy_col]).copy()
    grp = out.groupby(group_cols, dropna=False)[value_col]
    prev = grp.shift(1)
    out[f"prior_year{suffix}"] = prev
    out[f"change_abs{suffix}"] = out[value_col] - prev
    out[f"change_pct{suffix}"] = np.where(
        prev > 0, (out[value_col] - prev) / prev * 100.0, np.nan
    )
    return out


def cagr(first: float, last: float, periods: int) -> float:
    """Compound annual growth rate over ``periods`` years, in percent."""
    if periods <= 0 or first is None or last is None:
        return float("nan")
    if not np.isfinite(first) or not np.isfinite(last) or first <= 0 or last <= 0:
        return float("nan")
    return float(((last / first) ** (1.0 / periods) - 1.0) * 100.0)


def trend_summary(
    df: pd.DataFrame,
    group_cols: list[str],
    *,
    nominal_col: str = "obligations",
    real_col: str = "obligations_real",
    fy_col: str = "fiscal_year",
) -> pd.DataFrame:
    """One row per group: level, growth, CAGR, and volatility across the window."""
    records = []
    for key, grp in df.groupby(group_cols, dropna=False):
        key_t = key if isinstance(key, tuple) else (key,)
        g = grp.sort_values(fy_col)
        years = g[fy_col].tolist()
        n_periods = len(years) - 1

        rec: dict = dict(zip(group_cols, key_t, strict=True))
        rec["first_fiscal_year"] = years[0]
        rec["last_fiscal_year"] = years[-1]
        rec["obligations_first"] = float(g[nominal_col].iloc[0])
        rec["obligations_last"] = float(g[nominal_col].iloc[-1])
        rec["obligations_total"] = float(g[nominal_col].sum())
        rec["cagr_nominal_pct"] = cagr(
            rec["obligations_first"], rec["obligations_last"], n_periods
        )

        if real_col in g.columns:
            rec["obligations_real_first"] = float(g[real_col].iloc[0])
            rec["obligations_real_last"] = float(g[real_col].iloc[-1])
            rec["obligations_real_total"] = float(g[real_col].sum())
            rec["cagr_real_pct"] = cagr(
                rec["obligations_real_first"], rec["obligations_real_last"], n_periods
            )
            rec["change_real_abs"] = rec["obligations_real_last"] - rec["obligations_real_first"]
            rec["change_real_pct"] = (
                (rec["obligations_real_last"] / rec["obligations_real_first"] - 1.0) * 100.0
                if rec["obligations_real_first"] > 0
                else np.nan
            )
            yoy = g[real_col].pct_change().dropna() * 100.0
            rec["yoy_real_volatility_pp"] = float(yoy.std(ddof=1)) if len(yoy) > 1 else np.nan
            rec["yoy_real_max_swing_pp"] = (
                float(yoy.abs().max()) if len(yoy) else np.nan
            )
            # Slope of a least-squares fit on log-real obligations: a single
            # summary of direction that is robust to one anomalous end year,
            # unlike a first-to-last comparison.
            positive = g.loc[g[real_col] > 0]
            if len(positive) >= 3:
                slope = np.polyfit(positive[fy_col], np.log(positive[real_col]), 1)[0]
                rec["log_trend_pct_per_year"] = float((np.exp(slope) - 1.0) * 100.0)
            else:
                rec["log_trend_pct_per_year"] = np.nan
        records.append(rec)

    return pd.DataFrame(records)


def contribution_to_change(
    df: pd.DataFrame,
    group_col: str,
    value_col: str,
    *,
    fy_col: str = "fiscal_year",
    base_fy: int | None = None,
    latest_fy: int | None = None,
) -> pd.DataFrame:
    """Decompose the government-wide change into each group's contribution.

    Answers "what actually moved the total", which is almost always a different
    question from "who grew fastest in percentage terms" - the fastest growers
    are usually small, and the movers are usually large.
    """
    years = sorted(df[fy_col].unique())
    base_fy = base_fy if base_fy is not None else years[0]
    latest_fy = latest_fy if latest_fy is not None else years[-1]

    base = df[df[fy_col] == base_fy].groupby(group_col)[value_col].sum()
    latest = df[df[fy_col] == latest_fy].groupby(group_col)[value_col].sum()

    out = pd.DataFrame({"base": base, "latest": latest}).fillna(0.0)
    out["change"] = out["latest"] - out["base"]
    total_change = out["change"].sum()
    out["share_of_total_change"] = (
        out["change"] / total_change if total_change != 0 else np.nan
    )
    out["base_fiscal_year"] = base_fy
    out["latest_fiscal_year"] = latest_fy
    return (
        out.reset_index()
        .sort_values("change", key=lambda s: s.abs(), ascending=False)
        .reset_index(drop=True)
    )
