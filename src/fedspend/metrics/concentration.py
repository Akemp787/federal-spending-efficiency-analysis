"""Market-concentration measures for spending distributions.

The measures here are the standard antitrust toolkit applied to the buyer side
of the federal market: how much of an agency's obligations flow to how few
vendors, and how much of the government's obligations flow to how few agencies.

Truncation
----------
Vendor extracts hold each agency's top 100 recipients, not all of them. Shares
are therefore always computed against the agency's *true* total obligations
(passed in as ``total``), never against the sum of the truncated list. This makes
the resulting HHI a strict lower bound: the omitted tail contributes a small
positive amount that is excluded rather than misattributed. ``coverage_share``
is reported alongside every HHI so a reader can see how much of the market the
measure actually observed.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

# DOJ/FTC Horizontal Merger Guidelines thresholds, in HHI points.
HHI_UNCONCENTRATED = 1500.0
HHI_MODERATELY_CONCENTRATED = 2500.0


def herfindahl(values: np.ndarray | pd.Series, total: float | None = None) -> float:
    """Herfindahl-Hirschman Index in points (0-10,000).

    ``total`` defaults to the sum of ``values``. Supply it explicitly when
    ``values`` is a truncated top-N list so shares stay anchored to the real
    market size.
    """
    v = np.asarray(values, dtype="float64")
    v = v[np.isfinite(v) & (v > 0)]  # de-obligations cannot hold market share
    denom = float(total) if total is not None else float(v.sum())
    if denom <= 0 or v.size == 0:
        return float("nan")
    shares = v / denom
    return float(np.sum(shares**2) * 10_000.0)


def normalized_herfindahl(values: np.ndarray | pd.Series, total: float | None = None) -> float:
    """HHI rescaled to [0, 1] against the number of observed participants.

    Removes the mechanical effect of participant count, so a 12-vendor market and
    a 900-vendor market can be compared on equal terms.
    """
    v = np.asarray(values, dtype="float64")
    v = v[np.isfinite(v) & (v > 0)]
    n = v.size
    if n <= 1:
        return float("nan")
    h = herfindahl(v, total) / 10_000.0
    return float((h - 1.0 / n) / (1.0 - 1.0 / n))


def concentration_ratio(values: np.ndarray | pd.Series, n: int, total: float | None = None) -> float:
    """CR-n: share of the market held by the largest ``n`` participants (0-1)."""
    v = np.asarray(values, dtype="float64")
    v = v[np.isfinite(v) & (v > 0)]
    denom = float(total) if total is not None else float(v.sum())
    if denom <= 0 or v.size == 0:
        return float("nan")
    return float(np.sort(v)[::-1][:n].sum() / denom)


def gini(values: np.ndarray | pd.Series) -> float:
    """Gini coefficient of a spending distribution (0 = even, 1 = one winner)."""
    v = np.asarray(values, dtype="float64")
    v = np.sort(v[np.isfinite(v) & (v > 0)])
    n = v.size
    if n == 0 or v.sum() <= 0:
        return float("nan")
    index = np.arange(1, n + 1)
    return float((2.0 * np.sum(index * v)) / (n * v.sum()) - (n + 1.0) / n)


def classify_hhi(hhi: float) -> str:
    """Label an HHI against the DOJ/FTC thresholds."""
    if not np.isfinite(hhi):
        return "undetermined"
    if hhi < HHI_UNCONCENTRATED:
        return "unconcentrated"
    if hhi < HHI_MODERATELY_CONCENTRATED:
        return "moderately concentrated"
    return "highly concentrated"


def concentration_profile(
    df: pd.DataFrame,
    group_cols: list[str],
    value_col: str,
    totals: pd.DataFrame | None = None,
    total_col: str = "obligations",
    top_ns: tuple[int, ...] = (1, 4, 10, 20),
) -> pd.DataFrame:
    """Compute the full concentration profile for each group.

    Parameters
    ----------
    df
        Long frame of participant-level values (e.g. agency-vendor obligations).
    group_cols
        Columns defining each market (e.g. ``["fiscal_year", "agency_name"]``).
    totals
        Optional frame keyed on ``group_cols`` carrying the true market size in
        ``total_col``. Strongly recommended whenever ``df`` is a top-N truncation.
    """
    total_lookup: dict[tuple, float] = {}
    if totals is not None:
        idx = totals.set_index(group_cols)[total_col]
        total_lookup = {
            (k if isinstance(k, tuple) else (k,)): float(v) for k, v in idx.items()
        }

    records = []
    for key, grp in df.groupby(group_cols, dropna=False):
        key_t = key if isinstance(key, tuple) else (key,)
        values = grp[value_col]
        observed = float(values[values > 0].sum())
        market_total = total_lookup.get(key_t)
        denom = market_total if market_total and market_total > 0 else observed

        rec: dict = dict(zip(group_cols, key_t, strict=True))
        rec["participants_observed"] = int((values > 0).sum())
        rec["observed_obligations"] = observed
        rec["market_total"] = denom
        rec["coverage_share"] = observed / denom if denom > 0 else float("nan")
        rec["hhi"] = herfindahl(values, denom)
        rec["hhi_normalized"] = normalized_herfindahl(values, denom)
        rec["hhi_class"] = classify_hhi(rec["hhi"])
        rec["gini"] = gini(values)
        for n in top_ns:
            rec[f"cr{n}"] = concentration_ratio(values, n, denom)
        records.append(rec)

    return pd.DataFrame(records).sort_values(group_cols).reset_index(drop=True)
