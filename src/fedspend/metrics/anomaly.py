"""Outlier detection for review prioritisation.

Method choice
-------------
Federal spending distributions are heavily right-skewed and contain the very
outliers being searched for. A classical z-score computed from the mean and
standard deviation is therefore self-defeating: the outlier inflates the
dispersion estimate that is supposed to detect it, a phenomenon called masking.

Every detector here is built on the median and the median absolute deviation,
which have a 50% breakdown point - half the observations can be arbitrarily
corrupted before the estimate moves. The MAD is scaled by 1.4826 so that for
normally distributed data it estimates the same quantity as the standard
deviation, which keeps the familiar "3 sigma" reading meaningful.

Flags are review triggers, not findings. A flag says an agency-year is unlike
its peers; establishing whether that is a problem requires the contract-level
work this analysis is designed to target.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

MAD_TO_SIGMA = 1.4826


def robust_z(values: np.ndarray | pd.Series) -> np.ndarray:
    """Median-absolute-deviation z-scores.

    Falls back to a mean-absolute-deviation scale when the MAD is zero, which
    happens when more than half the observations share one value.
    """
    v = np.asarray(values, dtype="float64")
    finite = v[np.isfinite(v)]
    if finite.size == 0:
        return np.full_like(v, np.nan)

    median = np.median(finite)
    mad = np.median(np.abs(finite - median))
    scale = mad * MAD_TO_SIGMA
    if scale == 0:
        mean_abs = np.mean(np.abs(finite - median))
        scale = mean_abs * 1.2533 if mean_abs > 0 else np.nan
    if not np.isfinite(scale) or scale == 0:
        return np.zeros_like(v)
    return (v - median) / scale


def iqr_fences(values: np.ndarray | pd.Series, k: float = 1.5) -> tuple[float, float]:
    """Tukey fences. ``k=1.5`` marks outliers, ``k=3.0`` marks far outliers."""
    v = np.asarray(values, dtype="float64")
    v = v[np.isfinite(v)]
    if v.size < 4:
        return float("nan"), float("nan")
    q1, q3 = np.percentile(v, [25, 75])
    iqr = q3 - q1
    return float(q1 - k * iqr), float(q3 + k * iqr)


def flag_outliers(
    df: pd.DataFrame,
    value_col: str,
    *,
    within: list[str] | None = None,
    threshold: float = 3.0,
    prefix: str | None = None,
) -> pd.DataFrame:
    """Attach robust z-scores and outlier flags, optionally within subgroups.

    ``within`` scopes the comparison - passing ``["fiscal_year"]`` compares each
    agency against its peers *in that year*, so a government-wide shift does not
    flag everyone at once.
    """
    out = df.copy()
    p = prefix or value_col

    if within:
        out[f"{p}_robust_z"] = (
            out.groupby(within, dropna=False)[value_col]
            .transform(lambda s: pd.Series(robust_z(s), index=s.index))
        )
        fences = out.groupby(within, dropna=False)[value_col].transform(
            lambda s: pd.Series(np.repeat(iqr_fences(s)[1], len(s)), index=s.index)
        )
        low_fences = out.groupby(within, dropna=False)[value_col].transform(
            lambda s: pd.Series(np.repeat(iqr_fences(s)[0], len(s)), index=s.index)
        )
    else:
        out[f"{p}_robust_z"] = robust_z(out[value_col])
        lo, hi = iqr_fences(out[value_col])
        fences = pd.Series(hi, index=out.index)
        low_fences = pd.Series(lo, index=out.index)

    out[f"{p}_iqr_upper"] = fences
    out[f"{p}_iqr_lower"] = low_fences
    out[f"{p}_is_high_outlier"] = out[f"{p}_robust_z"] >= threshold
    out[f"{p}_is_low_outlier"] = out[f"{p}_robust_z"] <= -threshold
    out[f"{p}_is_outlier"] = out[f"{p}_is_high_outlier"] | out[f"{p}_is_low_outlier"]
    return out


def priority_matrix(
    df: pd.DataFrame,
    *,
    scale_col: str,
    signal_col: str,
    group_col: str = "agency_name",
    scale_label: str = "spend",
    signal_label: str = "signal",
) -> pd.DataFrame:
    """Classic 2x2: split a population on scale and on a risk signal.

    Quadrants are cut at the *median* of each axis rather than at an absolute
    threshold, so the output is a ranked shortlist of the population under
    review rather than a claim that any agency has crossed a standard.
    """
    out = df.copy()
    scale_cut = out[scale_col].median()
    signal_cut = out[signal_col].median()

    high_scale = out[scale_col] >= scale_cut
    high_signal = out[signal_col] >= signal_cut

    out["quadrant"] = np.select(
        [high_scale & high_signal, high_scale & ~high_signal, ~high_scale & high_signal],
        [
            f"High {scale_label} / high {signal_label}",
            f"High {scale_label} / low {signal_label}",
            f"Low {scale_label} / high {signal_label}",
        ],
        default=f"Low {scale_label} / low {signal_label}",
    )
    out["is_priority"] = high_scale & high_signal
    out[f"{scale_col}_median_cut"] = scale_cut
    out[f"{signal_col}_median_cut"] = signal_cut
    return out.sort_values([signal_col, scale_col], ascending=False).reset_index(drop=True)
