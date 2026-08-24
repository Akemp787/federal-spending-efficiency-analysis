"""Shift-share decomposition of a change in a spending-weighted rate.

The problem this solves
-----------------------
Government-wide competition rate fell between FY2024 and FY2025. There are two
completely different explanations, and they carry opposite management
implications:

* **Within effect** - agencies genuinely competed less of their own work. That is
  a behavioural change and an oversight finding.
* **Mix effect** - agencies did not change, but the dollars moved toward agencies
  that were always less competitive. That is a budget-composition outcome, and
  reporting it as declining competition would be wrong.

A weighted rate is ``S = sum_i(w_i * s_i)`` over agencies, where ``w_i`` is an
agency's share of total obligations and ``s_i`` is its own rate. The change
between two periods decomposes exactly:

    dS = sum_i(w_i0 * ds_i)      <- within effect
       + sum_i(dw_i * s_i0)      <- mix effect
       + sum_i(dw_i * ds_i)      <- interaction

The three terms sum to the total change with no residual, which is what makes
this worth doing rather than asserting a story. Agencies present in only one
period are handled by treating the absent period as zero weight, so entries and
exits land in the mix term where they belong.
"""

from __future__ import annotations

import pandas as pd


def shift_share(
    df: pd.DataFrame,
    *,
    group_col: str,
    weight_col: str,
    rate_col: str,
    period_col: str = "fiscal_year",
    base_period: int | None = None,
    latest_period: int | None = None,
) -> tuple[pd.DataFrame, dict[str, float]]:
    """Decompose the change in a weighted rate into within, mix, and interaction.

    Returns the per-group contributions and a summary dict whose ``total_change``
    reconciles to the directly computed change in the weighted rate.

    Negative weights (an agency whose net obligations are negative because
    de-obligations exceeded new awards) are clipped to zero: a negative share of
    a total is not interpretable as a weight, and leaving it in would make the
    decomposition arithmetically valid but meaningless.
    """
    periods = sorted(df[period_col].unique())
    base_period = base_period if base_period is not None else periods[0]
    latest_period = latest_period if latest_period is not None else periods[-1]

    def _slice(period: int) -> pd.DataFrame:
        s = df[df[period_col] == period][[group_col, weight_col, rate_col]].copy()
        s[weight_col] = s[weight_col].clip(lower=0)
        total = s[weight_col].sum()
        s["w"] = s[weight_col] / total if total > 0 else 0.0
        return s.set_index(group_col)[["w", rate_col]].rename(columns={rate_col: "s"})

    base = _slice(base_period)
    latest = _slice(latest_period)

    joined = base.join(latest, how="outer", lsuffix="_0", rsuffix="_1")
    joined["w_0"] = joined["w_0"].fillna(0.0)
    joined["w_1"] = joined["w_1"].fillna(0.0)
    # A group absent in one period has no rate there; its rate is irrelevant
    # because it is multiplied by a zero weight in every term it appears in.
    joined["s_0"] = joined["s_0"].fillna(0.0)
    joined["s_1"] = joined["s_1"].fillna(0.0)

    rate_0 = float((base["w"] * base["s"]).sum())
    rate_1 = float((latest["w"] * latest["s"]).sum())

    joined["dw"] = joined["w_1"] - joined["w_0"]
    joined["ds"] = joined["s_1"] - joined["s_0"]
    joined["within_effect"] = joined["w_0"] * joined["ds"]
    # The mix term is centred on the base-period overall rate. Weights sum to one
    # in both periods, so sum(dw) == 0 and sum(dw * s_0) == sum(dw * (s_0 - S_0)):
    # centring leaves the total untouched while making each agency's contribution
    # readable. Uncentred, an agency that grew would always show a positive mix
    # term regardless of whether it competes more or less than average, which
    # inverts the sign of the thing the reader is trying to understand.
    joined["mix_effect"] = joined["dw"] * (joined["s_0"] - rate_0)
    joined["mix_effect_uncentred"] = joined["dw"] * joined["s_0"]
    joined["interaction_effect"] = joined["dw"] * joined["ds"]
    joined["total_effect"] = (
        joined["within_effect"] + joined["mix_effect"] + joined["interaction_effect"]
    )

    summary = {
        "base_period": float(base_period),
        "latest_period": float(latest_period),
        "rate_base": rate_0,
        "rate_latest": rate_1,
        "total_change": rate_1 - rate_0,
        "within_effect": float(joined["within_effect"].sum()),
        "mix_effect": float(joined["mix_effect"].sum()),
        "interaction_effect": float(joined["interaction_effect"].sum()),
    }
    summary["reconciliation_residual"] = summary["total_change"] - (
        summary["within_effect"] + summary["mix_effect"] + summary["interaction_effect"]
    )
    summary["within_share_of_change"] = (
        summary["within_effect"] / summary["total_change"]
        if summary["total_change"] != 0
        else float("nan")
    )
    summary["mix_share_of_change"] = (
        summary["mix_effect"] / summary["total_change"]
        if summary["total_change"] != 0
        else float("nan")
    )

    contributions = (
        joined.reset_index()
        .sort_values("total_effect", key=lambda s: s.abs(), ascending=False)
        .reset_index(drop=True)
    )
    contributions["base_period"] = base_period
    contributions["latest_period"] = latest_period
    return contributions, summary


def shift_share_series(
    df: pd.DataFrame,
    *,
    group_col: str,
    weight_col: str,
    rate_col: str,
    period_col: str = "fiscal_year",
) -> pd.DataFrame:
    """Run the decomposition for every consecutive period pair in the data."""
    periods = sorted(df[period_col].unique())
    rows = []
    for base_period, latest_period in zip(periods[:-1], periods[1:], strict=True):
        _, summary = shift_share(
            df,
            group_col=group_col,
            weight_col=weight_col,
            rate_col=rate_col,
            period_col=period_col,
            base_period=base_period,
            latest_period=latest_period,
        )
        rows.append(summary)
    return pd.DataFrame(rows)
