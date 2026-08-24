"""The Contract Efficiency Index (CEI) and its sensitivity analysis.

What the index is
-----------------
A single 0-100 score per agency, built from five dimensions that each capture a
different way contract dollars can be spent well or badly:

===================  ====================================================
Dimension            Raw measure (higher = more efficient)
===================  ====================================================
competition          share of obligations competed
pricing_risk         share NOT cost-reimbursement or time-and-materials
vendor_diversity     1 - normalised vendor HHI
spend_discipline     1 - September share of annual obligations
stability            1 - real year-over-year growth volatility
===================  ====================================================

What the index is not
---------------------
It is not a measure of waste, and a low score is not an accusation. A defence
research agency buying developmental systems *should* run more cost-reimbursement
work and a thinner vendor base than an agency buying office supplies. Composite
indices also carry three well-known problems, all of which are handled explicitly
rather than ignored:

1. **Weights are arbitrary.** Mitigated by publishing the weights in config and
   re-scoring under thousands of random weightings; an agency whose rank is
   stable across that distribution is not an artefact of one weighting choice.
2. **Normalisation is scale-dependent.** Mitigated by winsorising before min-max
   scaling, so one extreme agency cannot compress everyone else into a narrow band.
3. **Aggregation hides the driver.** Mitigated by always returning the component
   sub-scores alongside the composite, so any score can be decomposed.

The honest framing, and the one the report uses: the CEI is a *triage device*
that ranks where to look first, not a verdict on how anyone performed.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

DIMENSIONS = (
    "competition",
    "pricing_risk",
    "vendor_diversity",
    "spend_discipline",
    "stability",
)


def winsorize(s: pd.Series, lower_q: float, upper_q: float) -> pd.Series:
    """Clip a series to its own quantiles, ignoring NaN."""
    valid = s.dropna()
    if valid.empty:
        return s
    lo, hi = valid.quantile(lower_q), valid.quantile(upper_q)
    return s.clip(lower=lo, upper=hi)


def minmax_score(s: pd.Series) -> pd.Series:
    """Scale to 0-100. A degenerate (zero-range) dimension scores a flat 50."""
    lo, hi = s.min(), s.max()
    if not np.isfinite(lo) or not np.isfinite(hi) or hi == lo:
        return pd.Series(np.where(s.notna(), 50.0, np.nan), index=s.index)
    return (s - lo) / (hi - lo) * 100.0


def build_raw_dimensions(
    competed: pd.DataFrame,
    pricing: pd.DataFrame,
    vendor_conc: pd.DataFrame,
    timing: pd.DataFrame,
    trend: pd.DataFrame,
    *,
    group_col: str = "agency_name",
) -> pd.DataFrame:
    """Assemble the five raw dimensions onto one row per agency.

    All inputs are expected to be already filtered to the scoring fiscal year,
    except ``trend``, which is a whole-window summary by construction.
    """
    frames = {
        "competition": competed.set_index(group_col)["competed_share"],
        "pricing_risk": 1.0 - pricing.set_index(group_col)["government_risk_share"],
        "vendor_diversity": 1.0 - vendor_conc.set_index(group_col)["hhi_normalized"],
        "spend_discipline": 1.0 - timing.set_index(group_col)["september_share"],
        "stability": -trend.set_index(group_col)["yoy_real_volatility_pp"],
    }
    raw = pd.DataFrame(frames)
    raw.columns = [f"{c}_raw" for c in raw.columns]
    return raw


def score_index(
    raw: pd.DataFrame,
    weights: dict[str, float],
    *,
    winsor: tuple[float, float] = (0.05, 0.95),
    group_col: str = "agency_name",
) -> pd.DataFrame:
    """Turn raw dimensions into winsorised, normalised sub-scores and a composite.

    Weights are renormalised over whichever dimensions an agency actually has,
    so one missing dimension reduces confidence rather than silently scoring
    that dimension as zero.
    """
    out = raw.copy()
    for dim in DIMENSIONS:
        col = f"{dim}_raw"
        if col not in out.columns:
            out[col] = np.nan
        out[f"{dim}_score"] = minmax_score(winsorize(out[col], *winsor))

    score_cols = [f"{d}_score" for d in DIMENSIONS]
    w = np.array([weights[d] for d in DIMENSIONS], dtype="float64")
    values = out[score_cols].to_numpy(dtype="float64")

    present = np.isfinite(values)
    weight_matrix = np.where(present, w, 0.0)
    weight_sums = weight_matrix.sum(axis=1)
    weighted = np.nansum(np.where(present, values, 0.0) * weight_matrix, axis=1)

    with np.errstate(invalid="ignore", divide="ignore"):
        out["efficiency_index"] = np.where(weight_sums > 0, weighted / weight_sums, np.nan)

    out["dimensions_available"] = present.sum(axis=1)
    out["weight_coverage"] = weight_sums / w.sum()
    out = out.sort_values("efficiency_index", ascending=False)
    out["rank"] = out["efficiency_index"].rank(ascending=False, method="min")
    out["quartile"] = pd.qcut(
        out["efficiency_index"].rank(method="first"),
        4,
        labels=["Q4 (lowest)", "Q3", "Q2", "Q1 (highest)"],
    )
    return out.reset_index().rename(columns={"index": group_col})


def weight_sensitivity(
    raw: pd.DataFrame,
    *,
    n_draws: int = 2000,
    winsor: tuple[float, float] = (0.05, 0.95),
    group_col: str = "agency_name",
    seed: int = 20250930,
) -> pd.DataFrame:
    """Re-score under ``n_draws`` random weightings and summarise rank stability.

    Weights are drawn from a flat Dirichlet over the five dimensions, which is
    the uniform distribution on the simplex - every weighting that sums to one is
    equally likely. An agency that stays in the bottom quartile across the whole
    distribution is a robust finding; one that swings by twenty ranks is an
    artefact of the chosen weights and is reported as such.
    """
    rng = np.random.default_rng(seed)

    scored = raw.copy()
    for dim in DIMENSIONS:
        scored[f"{dim}_score"] = minmax_score(winsorize(scored[f"{dim}_raw"], *winsor))
    score_cols = [f"{d}_score" for d in DIMENSIONS]
    values = scored[score_cols].to_numpy(dtype="float64")
    present = np.isfinite(values)
    filled = np.where(present, values, 0.0)

    n_agencies = values.shape[0]
    ranks = np.empty((n_draws, n_agencies), dtype="float64")
    scores = np.empty((n_draws, n_agencies), dtype="float64")

    for i in range(n_draws):
        w = rng.dirichlet(np.ones(len(DIMENSIONS)))
        wm = np.where(present, w, 0.0)
        denom = wm.sum(axis=1)
        with np.errstate(invalid="ignore", divide="ignore"):
            s = np.where(denom > 0, (filled * wm).sum(axis=1) / denom, np.nan)
        scores[i] = s
        ranks[i] = pd.Series(s).rank(ascending=False, method="min").to_numpy()

    bottom_quartile_cut = np.ceil(n_agencies * 0.75)
    out = pd.DataFrame(
        {
            group_col: scored.index,
            "score_mean": np.nanmean(scores, axis=0),
            "score_p05": np.nanpercentile(scores, 5, axis=0),
            "score_p95": np.nanpercentile(scores, 95, axis=0),
            "rank_median": np.nanmedian(ranks, axis=0),
            "rank_best": np.nanmin(ranks, axis=0),
            "rank_worst": np.nanmax(ranks, axis=0),
            "rank_iqr": np.nanpercentile(ranks, 75, axis=0)
            - np.nanpercentile(ranks, 25, axis=0),
            "pct_draws_in_bottom_quartile": (ranks >= bottom_quartile_cut).mean(axis=0) * 100.0,
            "pct_draws_in_top_quartile": (ranks <= np.ceil(n_agencies * 0.25)).mean(axis=0)
            * 100.0,
        }
    )
    # Stability threshold: a rank whose interquartile range spans more than a
    # fifth of the field is not separable from its neighbours under a different
    # but equally defensible weighting, and should not be reported as a ranking.
    out["rank_is_stable"] = out["rank_iqr"] <= max(2.0, n_agencies * 0.20)
    # The more useful signal than exact rank is whether an agency lands in the
    # same quartile regardless of weighting. Reported explicitly so the writeup
    # can say which parts of the table survive the sensitivity test and which do
    # not, rather than presenting all 19 ranks as equally meaningful.
    out["quartile_confidence_pct"] = out[
        ["pct_draws_in_bottom_quartile", "pct_draws_in_top_quartile"]
    ].max(axis=1)
    out["quartile_verdict"] = np.select(
        [
            out["pct_draws_in_bottom_quartile"] >= 70,
            out["pct_draws_in_top_quartile"] >= 70,
        ],
        ["robustly bottom quartile", "robustly top quartile"],
        default="not separable",
    )
    return out.sort_values("rank_median").reset_index(drop=True)


def compare_weightings(
    raw: pd.DataFrame,
    weightings: dict[str, dict[str, float]],
    *,
    winsor: tuple[float, float] = (0.05, 0.95),
    group_col: str = "agency_name",
) -> pd.DataFrame:
    """Score the same agencies under several named weightings, side by side."""
    frames = []
    for name, weights in weightings.items():
        scored = score_index(raw, weights, winsor=winsor, group_col=group_col)
        frames.append(
            scored[[group_col, "efficiency_index", "rank"]].assign(weighting=name)
        )
    long = pd.concat(frames, ignore_index=True)
    wide = long.pivot(index=group_col, columns="weighting", values="rank")
    wide["rank_spread"] = wide.max(axis=1) - wide.min(axis=1)
    return wide.sort_values("rank_spread", ascending=False).reset_index()
