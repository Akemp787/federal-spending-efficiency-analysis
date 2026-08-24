"""Data-quality contracts run against the curated tables.

A published number should be accompanied by evidence that it was checked. Each
check returns a structured result rather than raising, so the whole suite runs
and produces a report; ``fedspend validate`` exits non-zero if any ERROR-severity
check fails, which is what CI gates on.

The most valuable check here is ``check_competition_reconciliation``: the
competition cross-tab is assembled from nine separate API calls per agency-year,
one per FPDS extent-competed code. If those nine calls do not sum back to the
independently retrieved agency total, something is wrong with the extraction and
every competition figure downstream is suspect. That reconciliation is the reason
to trust the rest.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

import pandas as pd

from ..config import Config
from ..logging_utils import get_logger

log = get_logger(__name__)

ERROR = "ERROR"
WARN = "WARN"


@dataclass
class CheckResult:
    name: str
    passed: bool
    severity: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
def check_fiscal_year_coverage(fact: pd.DataFrame, expected: list[int]) -> CheckResult:
    found = sorted(fact["fiscal_year"].unique().tolist())
    missing = sorted(set(expected) - set(found))
    return CheckResult(
        "fiscal_year_coverage",
        not missing,
        ERROR,
        f"Expected {expected}, found {found}" + (f", missing {missing}" if missing else ""),
        {"expected": expected, "found": found, "missing": missing},
    )


def check_no_duplicate_keys(fact: pd.DataFrame) -> CheckResult:
    dupes = fact.duplicated(subset=["fiscal_year", "agency_name"]).sum()
    return CheckResult(
        "unique_agency_year_key",
        dupes == 0,
        ERROR,
        f"{dupes} duplicate (fiscal_year, agency_name) rows",
        {"duplicate_rows": int(dupes)},
    )


def check_competition_reconciliation(
    cfg: Config, tolerance: float = 0.01
) -> CheckResult:
    """The nine extent-competed slices must sum back to the agency total.

    Tolerance is relative. A 1% band absorbs the small differences that arise
    because USAspending assigns a handful of transactions a null extent-competed
    code, which no code-filtered query returns.
    """
    agency = pd.read_parquet(cfg.interim_dir / "agency_fy.parquet")
    comp = pd.read_parquet(cfg.interim_dir / "agency_fy_competition.parquet")

    sliced = comp.groupby(["fiscal_year", "agency_name"], as_index=False)["obligations"].sum()
    merged = agency.merge(
        sliced, on=["fiscal_year", "agency_name"], how="inner", suffixes=("_total", "_sliced")
    )
    merged = merged[merged["obligations_total"].abs() > 1_000_000]
    merged["rel_diff"] = (
        merged["obligations_sliced"] - merged["obligations_total"]
    ) / merged["obligations_total"]

    breaches = merged[merged["rel_diff"].abs() > tolerance]
    worst = merged.reindex(merged["rel_diff"].abs().sort_values(ascending=False).index).head(5)
    return CheckResult(
        "competition_slices_reconcile_to_totals",
        breaches.empty,
        ERROR,
        (
            f"{len(breaches)} of {len(merged)} agency-years exceed "
            f"{tolerance:.1%} reconciliation tolerance"
        ),
        {
            "agency_years_checked": int(len(merged)),
            "breaches": int(len(breaches)),
            "max_abs_rel_diff": float(merged["rel_diff"].abs().max()) if len(merged) else 0.0,
            "worst": worst[
                ["fiscal_year", "agency_name", "obligations_total", "obligations_sliced", "rel_diff"]
            ].to_dict("records"),
        },
    )


def check_pricing_reconciliation(cfg: Config, tolerance: float = 0.01) -> CheckResult:
    """The sixteen pricing-type slices must sum back to the agency total."""
    agency = pd.read_parquet(cfg.interim_dir / "agency_fy.parquet")
    price = pd.read_parquet(cfg.interim_dir / "agency_fy_pricing.parquet")

    sliced = price.groupby(["fiscal_year", "agency_name"], as_index=False)["obligations"].sum()
    merged = agency.merge(
        sliced, on=["fiscal_year", "agency_name"], how="inner", suffixes=("_total", "_sliced")
    )
    merged = merged[merged["obligations_total"].abs() > 1_000_000]
    merged["rel_diff"] = (
        merged["obligations_sliced"] - merged["obligations_total"]
    ) / merged["obligations_total"]
    breaches = merged[merged["rel_diff"].abs() > tolerance]
    return CheckResult(
        "pricing_slices_reconcile_to_totals",
        breaches.empty,
        ERROR,
        f"{len(breaches)} of {len(merged)} agency-years exceed {tolerance:.1%} tolerance",
        {
            "agency_years_checked": int(len(merged)),
            "breaches": int(len(breaches)),
            "max_abs_rel_diff": float(merged["rel_diff"].abs().max()) if len(merged) else 0.0,
        },
    )


def check_monthly_reconciliation(cfg: Config, tolerance: float = 0.01) -> CheckResult:
    """Twelve fiscal months must sum back to the fiscal-year total."""
    agency = pd.read_parquet(cfg.interim_dir / "agency_fy.parquet")
    monthly = pd.read_parquet(cfg.interim_dir / "agency_fy_month.parquet")

    annual = agency.groupby("fiscal_year", as_index=False)["obligations"].sum()
    summed = monthly.groupby("fiscal_year", as_index=False)["obligations"].sum()
    merged = annual.merge(summed, on="fiscal_year", suffixes=("_total", "_monthly"))
    merged["rel_diff"] = (
        merged["obligations_monthly"] - merged["obligations_total"]
    ) / merged["obligations_total"]
    breaches = merged[merged["rel_diff"].abs() > tolerance]
    return CheckResult(
        "monthly_slices_reconcile_to_annual",
        breaches.empty,
        ERROR,
        f"{len(breaches)} of {len(merged)} fiscal years exceed {tolerance:.1%} tolerance",
        {"detail": merged.to_dict("records")},
    )


def check_shares_in_range(fact: pd.DataFrame) -> CheckResult:
    """Every share column must lie in [0, 1] where the denominator is positive."""
    share_cols = [
        "competed_share",
        "fixed_price_share",
        "cost_reimbursement_share",
        "labor_hour_share",
        "government_risk_share",
        "september_share",
        "q4_share",
    ]
    offenders: dict[str, int] = {}
    for col in share_cols:
        if col not in fact.columns:
            continue
        s = fact.loc[fact["obligations"] > 0, col].dropna()
        bad = int(((s < -1e-9) | (s > 1 + 1e-9)).sum())
        if bad:
            offenders[col] = bad
    return CheckResult(
        "shares_within_unit_interval",
        not offenders,
        ERROR,
        f"{len(offenders)} share columns contain out-of-range values" if offenders else "all shares in [0,1]",
        {"offenders": offenders},
    )


def check_deflator_monotonic(cfg: Config) -> CheckResult:
    d = pd.read_parquet(cfg.interim_dir / "deflator_fy.parquet").sort_values("fiscal_year")
    monotonic = bool(d["deflator"].is_monotonic_increasing)
    return CheckResult(
        "deflator_monotonic_increasing",
        monotonic,
        WARN,
        "GDP deflator rises across the window" if monotonic else "deflator is not monotonic",
        {"series": d[["fiscal_year", "deflator"]].to_dict("records")},
    )


def check_negative_obligations(fact: pd.DataFrame) -> CheckResult:
    """Agencies with net-negative annual obligations, flagged for interpretation.

    Not an error: a fiscal year in which de-obligations exceed new awards is a
    real and meaningful event. It is flagged because share metrics computed on a
    negative denominator are undefined, and downstream code must exclude them.
    """
    neg = fact[fact["obligations"] < 0][["fiscal_year", "agency_name", "obligations"]]
    return CheckResult(
        "negative_net_obligations",
        neg.empty,
        WARN,
        f"{len(neg)} agency-years have net-negative obligations (de-obligations exceeded awards)",
        {"rows": neg.to_dict("records")},
    )


def check_index_population(cfg: Config) -> CheckResult:
    scored = pd.read_parquet(cfg.curated_dir / "efficiency_index.parquet")
    floor = float(cfg["analysis"]["materiality_floor_usd"])
    below = scored[scored["obligations"] < floor]
    return CheckResult(
        "index_population_above_materiality_floor",
        below.empty,
        ERROR,
        f"{len(below)} scored agencies fall below the ${floor / 1e9:.1f}B floor",
        {"agencies_scored": int(len(scored)), "below_floor": below["agency_name"].tolist()},
    )


def check_decomposition_reconciles(cfg: Config, tolerance: float = 1e-9) -> CheckResult:
    """Shift-share terms must sum to the observed change with no residual."""
    series = pd.read_parquet(cfg.curated_dir / "competition_decomposition_series.parquet")
    worst = float(series["reconciliation_residual"].abs().max())
    return CheckResult(
        "shift_share_reconciles_exactly",
        worst <= tolerance,
        ERROR,
        f"max |residual| = {worst:.2e} (tolerance {tolerance:.0e})",
        {"max_abs_residual": worst},
    )


# ---------------------------------------------------------------------------
def run_all(cfg: Config) -> pd.DataFrame:
    """Run the full suite and return one row per check."""
    fact = pd.read_parquet(cfg.curated_dir / "fact_agency_year.parquet")

    results = [
        check_fiscal_year_coverage(fact, cfg.fiscal_years),
        check_no_duplicate_keys(fact),
        check_competition_reconciliation(cfg),
        check_pricing_reconciliation(cfg),
        check_monthly_reconciliation(cfg),
        check_shares_in_range(fact),
        check_deflator_monotonic(cfg),
        check_negative_obligations(fact),
        check_index_population(cfg),
        check_decomposition_reconciles(cfg),
    ]

    for r in results:
        level = log.info if r.passed else (log.error if r.severity == ERROR else log.warning)
        level("[%s] %-42s %s", "PASS" if r.passed else r.severity, r.name, r.message)

    df = pd.DataFrame([r.as_dict() for r in results])
    out_path = cfg.outputs_dir / "tables" / "validation_report.csv"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.drop(columns=["details"]).to_csv(out_path, index=False)
    log.info("validation report -> %s", out_path)
    return df


def has_blocking_failures(results: pd.DataFrame) -> bool:
    return bool(((~results["passed"]) & (results["severity"] == ERROR)).any())
