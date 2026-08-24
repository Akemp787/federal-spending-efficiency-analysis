"""Contract-type risk: who bears the cost of a cost overrun.

Under a firm-fixed-price contract the contractor absorbs overruns. Under a
cost-reimbursement contract the government pays allowable costs whatever they
turn out to be, and under time-and-materials it pays for hours delivered with no
positive incentive to control them - which is why FAR 16.601(c) makes T&M the
least preferred vehicle, permitted only after a written determination that no
other contract type is suitable.

Contract type is not a verdict. R&D and complex services legitimately require
cost-reimbursement, and a defense research agency should look different from a
supply agency. What the measure gives an oversight function is the *size of the
population* where the government carries the cost risk, agency by agency and
year over year - and, more usefully, whether that population is growing.
"""

from __future__ import annotations

import pandas as pd

# Buckets where the government, not the contractor, absorbs cost growth.
GOVERNMENT_RISK_BUCKETS = ("cost_reimbursement", "labor_hour")


def pricing_mix(
    pricing_df: pd.DataFrame,
    group_cols: list[str],
    *,
    value_col: str = "obligations",
    bucket_col: str = "risk_bucket",
) -> pd.DataFrame:
    """Share of obligations by pricing-risk bucket, wide by bucket."""
    df = pricing_df.copy()
    df["positive"] = df[value_col].clip(lower=0)

    totals = (
        df.groupby(group_cols, dropna=False)["positive"].sum().rename("classified_obligations")
    )
    wide = (
        df.groupby([*group_cols, bucket_col], dropna=False)["positive"]
        .sum()
        .unstack(bucket_col)
        .fillna(0.0)
    )
    for bucket in ("fixed_price", "cost_reimbursement", "labor_hour", "other"):
        if bucket not in wide.columns:
            wide[bucket] = 0.0

    out = wide.join(totals).reset_index()
    for bucket in ("fixed_price", "cost_reimbursement", "labor_hour", "other"):
        out[f"{bucket}_share"] = (out[bucket] / out["classified_obligations"]).where(
            out["classified_obligations"] > 0
        )

    out["government_risk_obligations"] = out[list(GOVERNMENT_RISK_BUCKETS)].sum(axis=1)
    out["government_risk_share"] = (
        out["government_risk_obligations"] / out["classified_obligations"]
    ).where(out["classified_obligations"] > 0)
    out["fixed_price_discipline"] = out["fixed_price_share"]
    return out.sort_values(group_cols).reset_index(drop=True)


def pricing_detail(
    pricing_df: pd.DataFrame,
    group_cols: list[str],
    *,
    value_col: str = "obligations",
    label_col: str = "pricing_label",
) -> pd.DataFrame:
    """Long detail at individual FPDS pricing-code level with within-group shares."""
    df = pricing_df.copy()
    df["positive"] = df[value_col].clip(lower=0)
    totals = df.groupby(group_cols, dropna=False)["positive"].sum().rename("group_total")
    out = (
        df.groupby([*group_cols, label_col, "risk_bucket"], dropna=False)["positive"]
        .sum()
        .rename("obligations")
        .reset_index()
        .merge(totals, on=group_cols, how="left")
    )
    out["share"] = (out["obligations"] / out["group_total"]).where(out["group_total"] > 0)
    return out.sort_values([*group_cols, "obligations"], ascending=[*[True] * len(group_cols), False])


def risk_migration(
    mix: pd.DataFrame,
    *,
    fy_col: str = "fiscal_year",
    group_col: str = "agency_name",
    base_fy: int | None = None,
    latest_fy: int | None = None,
) -> pd.DataFrame:
    """Change in government-risk share between two fiscal years, in dollars and points.

    A rising government-risk share on a flat budget means the same money is
    buying less price certainty than it used to. Expressing the shift as
    ``dollars_shifted_to_government_risk`` holds the latest year's spending
    constant, so the figure isolates the change in *contract type* rather than
    the change in volume.
    """
    df = mix[[fy_col, group_col, "government_risk_share", "classified_obligations"]].copy()
    years = sorted(df[fy_col].unique())
    base_fy = base_fy if base_fy is not None else years[0]
    latest_fy = latest_fy if latest_fy is not None else years[-1]

    base = df[df[fy_col] == base_fy].set_index(group_col)
    latest = df[df[fy_col] == latest_fy].set_index(group_col)

    out = pd.DataFrame(
        {
            "government_risk_share_base": base["government_risk_share"],
            "government_risk_share_latest": latest["government_risk_share"],
            "classified_obligations_latest": latest["classified_obligations"],
        }
    ).dropna(subset=["government_risk_share_base", "government_risk_share_latest"])

    out["change_pp"] = (
        out["government_risk_share_latest"] - out["government_risk_share_base"]
    ) * 100.0
    out["dollars_shifted_to_government_risk"] = (
        out["change_pp"] / 100.0
    ) * out["classified_obligations_latest"]
    out["base_fiscal_year"] = base_fy
    out["latest_fiscal_year"] = latest_fy
    return out.reset_index().sort_values("change_pp", ascending=False).reset_index(drop=True)
