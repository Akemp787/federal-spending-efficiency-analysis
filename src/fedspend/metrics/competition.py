"""Competition rate: the share of obligations awarded through competition.

Definition
----------
An action is *competed* when its FPDS ``extent_competed`` code is one of the
codes listed under ``competition.competed`` in ``config/pipeline.yml`` - by
default A (full and open), D (full and open after exclusion of sources), F
(competed under Simplified Acquisition Procedures) and CDO (competitive delivery
order).

Code E, "follow-on to competed action", is deliberately counted as *not*
competed. The parent award was competed; this action was not. Agencies differ on
this convention, so ``competed_share`` accepts an override and the sensitivity
analysis re-runs the whole index under the opposite treatment.

Why it is the headline efficiency metric
----------------------------------------
Competition is the mechanism federal acquisition relies on to discipline price.
Non-competed dollars are not evidence of waste - sole-source is often lawful and
correct - but they are dollars where no market test occurred, which is precisely
the population an oversight function should size and prioritise.
"""

from __future__ import annotations

import pandas as pd


def competed_share(
    competition_df: pd.DataFrame,
    group_cols: list[str],
    *,
    competed_codes: list[str] | None = None,
    value_col: str = "obligations",
    code_col: str = "extent_competed_code",
) -> pd.DataFrame:
    """Aggregate the competition cross-tab into a competed share per group.

    Only positive obligations enter the denominator. A net-negative bucket means
    de-obligations exceeded new obligations in that category, which cannot be
    interpreted as a share of anything.
    """
    df = competition_df.copy()
    if competed_codes is not None:
        df["is_competed"] = df[code_col].isin(competed_codes)

    df["positive"] = df[value_col].clip(lower=0)

    grouped = df.groupby(group_cols, dropna=False)
    out = grouped.agg(
        total_obligations=(value_col, "sum"),
        classified_obligations=("positive", "sum"),
    ).reset_index()

    competed = (
        df[df["is_competed"]]
        .groupby(group_cols, dropna=False)["positive"]
        .sum()
        .rename("competed_obligations")
        .reset_index()
    )
    out = out.merge(competed, on=group_cols, how="left")
    out["competed_obligations"] = out["competed_obligations"].fillna(0.0)
    out["not_competed_obligations"] = (
        out["classified_obligations"] - out["competed_obligations"]
    )
    out["competed_share"] = (
        out["competed_obligations"] / out["classified_obligations"]
    ).where(out["classified_obligations"] > 0)
    out["not_competed_share"] = 1.0 - out["competed_share"]
    return out.sort_values(group_cols).reset_index(drop=True)


def competition_mix(
    competition_df: pd.DataFrame,
    group_cols: list[str],
    *,
    value_col: str = "obligations",
    label_col: str = "extent_competed_label",
) -> pd.DataFrame:
    """Share of obligations by individual extent-of-competition category."""
    df = competition_df.copy()
    df["positive"] = df[value_col].clip(lower=0)
    totals = df.groupby(group_cols, dropna=False)["positive"].sum().rename("group_total")
    out = (
        df.groupby([*group_cols, label_col], dropna=False)["positive"]
        .sum()
        .rename("obligations")
        .reset_index()
        .merge(totals, on=group_cols, how="left")
    )
    out["share"] = (out["obligations"] / out["group_total"]).where(out["group_total"] > 0)
    return out.sort_values([*group_cols, "obligations"], ascending=[*[True] * len(group_cols), False])


def noncompeted_dollar_exposure(
    competed: pd.DataFrame,
    *,
    benchmark: float | None = None,
    group_col: str = "agency_name",
    fy_col: str = "fiscal_year",
) -> pd.DataFrame:
    """Dollars an agency would move into competition to reach a benchmark rate.

    This converts a rate gap into money, which is the form a decision-maker can
    act on. ``benchmark`` defaults to the government-wide competed share in the
    same fiscal year, so each agency is measured against its peers in that year
    rather than against an arbitrary target.
    """
    df = competed.copy()
    if benchmark is None:
        totals = df.groupby(fy_col, as_index=False)[
            ["competed_obligations", "classified_obligations"]
        ].sum()
        totals["benchmark_share"] = (
            totals["competed_obligations"] / totals["classified_obligations"]
        )
        df = df.merge(totals[[fy_col, "benchmark_share"]], on=fy_col, how="left")
    else:
        df["benchmark_share"] = float(benchmark)

    df["share_gap_pp"] = (df["benchmark_share"] - df["competed_share"]) * 100.0
    df["dollars_below_benchmark"] = (
        (df["benchmark_share"] - df["competed_share"]).clip(lower=0)
        * df["classified_obligations"]
    )
    return df.sort_values("dollars_below_benchmark", ascending=False).reset_index(drop=True)
