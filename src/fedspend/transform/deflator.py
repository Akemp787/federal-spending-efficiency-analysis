"""Convert nominal obligations to constant fiscal-year dollars.

Why this module exists
----------------------
Between FY2021 and FY2025 the GDP price deflator rose by roughly a sixth. A
portfolio analysis that reports "federal contract spending grew X%" without
adjusting for that is reporting the price level as if it were a policy outcome.
Every growth figure in this project is therefore published in both nominal and
constant dollars, and the constant-dollar series is the one the findings rest on.

Source
------
BEA's GDP implicit price deflator (FRED series ``GDPDEF``, quarterly, index
2017 = 100), retrieved from FRED's keyless CSV endpoint. The GDP deflator is
used rather than CPI-U because the subject is government purchases of goods and
services, not household consumption.

A fiscal-year deflator is the unweighted mean of the four calendar quarters
beginning October of the prior year, which is exactly the federal fiscal year.
"""

from __future__ import annotations

import io
from pathlib import Path

import pandas as pd
import requests

from ..logging_utils import get_logger

log = get_logger(__name__)

_FISCAL_QUARTER_START_MONTHS = (10, 1, 4, 7)


def fetch_deflator_quarterly(url: str, cache_path: Path | None = None) -> pd.DataFrame:
    """Download (or read from cache) the quarterly deflator series."""
    if cache_path and cache_path.exists():
        log.info("Deflator: using cached %s", cache_path.name)
        text = cache_path.read_text(encoding="utf-8")
    else:
        log.info("Deflator: fetching %s", url)
        resp = requests.get(url, timeout=60)
        resp.raise_for_status()
        text = resp.text
        if cache_path:
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            cache_path.write_text(text, encoding="utf-8")

    df = pd.read_csv(io.StringIO(text))
    date_col, value_col = df.columns[0], df.columns[1]
    df = df.rename(columns={date_col: "date", value_col: "deflator"})
    df["date"] = pd.to_datetime(df["date"])
    df["deflator"] = pd.to_numeric(df["deflator"], errors="coerce")
    return df.dropna(subset=["deflator"]).reset_index(drop=True)


def to_fiscal_year_index(quarterly: pd.DataFrame, fiscal_years: list[int]) -> pd.DataFrame:
    """Collapse quarterly observations into one deflator per fiscal year.

    A quarter belongs to fiscal year ``y`` when it starts in Oct/Nov/Dec of
    ``y-1`` or in Jan..Sep of ``y``.
    """
    q = quarterly.copy()
    q["month"] = q["date"].dt.month
    q = q[q["month"].isin(_FISCAL_QUARTER_START_MONTHS)]
    q["fiscal_year"] = q["date"].dt.year.where(q["month"] != 10, q["date"].dt.year + 1)

    fy = (
        q.groupby("fiscal_year", as_index=False)
        .agg(deflator=("deflator", "mean"), quarters_observed=("deflator", "size"))
        .sort_values("fiscal_year")
    )
    fy = fy[fy["fiscal_year"].isin(fiscal_years)].reset_index(drop=True)

    missing = sorted(set(fiscal_years) - set(fy["fiscal_year"]))
    if missing:
        raise ValueError(f"Deflator series has no data for fiscal years: {missing}")
    incomplete = fy.loc[fy["quarters_observed"] < 4, "fiscal_year"].tolist()
    if incomplete:
        log.warning(
            "Deflator: fiscal years %s built from fewer than 4 quarters "
            "(BEA has not published the full year yet)",
            incomplete,
        )
    return fy


def build_deflator_table(
    url: str, fiscal_years: list[int], base_fy: int, cache_path: Path | None = None
) -> pd.DataFrame:
    """Return fiscal_year, deflator, and the multiplier to constant ``base_fy`` dollars."""
    fy = to_fiscal_year_index(fetch_deflator_quarterly(url, cache_path), fiscal_years)
    base_row = fy.loc[fy["fiscal_year"] == base_fy]
    if base_row.empty:
        raise ValueError(f"Base fiscal year {base_fy} not present in deflator table")
    base_value = float(base_row["deflator"].iloc[0])

    fy["deflator_base_fy"] = base_fy
    fy["real_multiplier"] = base_value / fy["deflator"]
    fy["cumulative_inflation_vs_base_pct"] = (fy["deflator"] / base_value - 1.0) * 100.0
    return fy


def deflate(
    df: pd.DataFrame,
    deflator_table: pd.DataFrame,
    value_cols: str | list[str],
    fy_col: str = "fiscal_year",
    suffix: str = "_real",
) -> pd.DataFrame:
    """Attach constant-dollar versions of ``value_cols`` to ``df``."""
    cols = [value_cols] if isinstance(value_cols, str) else list(value_cols)
    out = df.merge(
        deflator_table[[fy_col, "real_multiplier"]], on=fy_col, how="left", validate="many_to_one"
    )
    if out["real_multiplier"].isna().any():
        bad = sorted(out.loc[out["real_multiplier"].isna(), fy_col].unique())
        raise ValueError(f"No deflator for fiscal years {bad}")
    for col in cols:
        out[f"{col}{suffix}"] = out[col] * out["real_multiplier"]
    return out
