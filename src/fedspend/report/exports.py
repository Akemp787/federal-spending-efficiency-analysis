"""CSV exports and the committed sample datasets.

Two audiences are served here:

* **Power BI / Excel / Tableau** - a star-schema-shaped set of CSVs in
  ``outputs/tables`` that can be pointed at directly, with one fact table and
  conformed dimensions rather than one wide denormalised sheet.
* **A reviewer cloning the repository** - small sample extracts in
  ``data/samples`` that are committed to git, so the notebooks and tests run
  without anyone re-pulling several hundred API responses first.
"""

from __future__ import annotations

import pandas as pd

from ..analysis import CURATED_FILES
from ..config import Config
from ..logging_utils import get_logger

log = get_logger(__name__)

# Tables worth exposing to a BI tool, with the shape they play in a star schema.
BI_EXPORTS = {
    "fact_agency_year": "fact_agency_year",
    "gov_summary": "fact_government_year",
    "monthly_seasonality": "fact_month",
    "efficiency_index": "fact_efficiency_index",
    "index_sensitivity": "dim_index_sensitivity",
    "review_shortlist": "fact_review_shortlist",
    "competition_decomposition": "fact_competition_attribution",
    "vendor_concentration": "fact_vendor_concentration",
    "top_vendors": "dim_top_vendors",
    "agency_trend": "dim_agency_trend",
    "risk_migration": "fact_risk_migration",
    "category_naics": "dim_naics",
    "category_psc": "dim_psc",
    "category_state": "dim_state",
}


def export_tables(cfg: Config) -> list:
    """Write curated tables as CSV for BI tools, plus a dimension for agencies."""
    cfg.tables_dir.mkdir(parents=True, exist_ok=True)
    written = []

    for key, out_name in BI_EXPORTS.items():
        src = cfg.curated_dir / CURATED_FILES[key]
        if not src.exists():
            log.warning("skipping export %s (missing %s)", out_name, src.name)
            continue
        df = pd.read_parquet(src)
        dest = cfg.tables_dir / f"{out_name}.csv"
        df.to_csv(dest, index=False)
        written.append(dest)
        log.info("export %-30s %6d rows -> %s", out_name, len(df), dest.name)

    # Conformed agency dimension so BI models join on a single key.
    fact = pd.read_parquet(cfg.curated_dir / CURATED_FILES["fact_agency_year"])
    dim = (
        fact.sort_values("fiscal_year")
        .groupby("agency_name", as_index=False)
        .agg(
            agency_code=("agency_code", "last"),
            agency_slug=("agency_slug", "last"),
            peak_obligations=("obligations", "max"),
            latest_obligations=("obligations", "last"),
            is_material=("is_material", "max"),
            years_present=("fiscal_year", "nunique"),
        )
        .sort_values("peak_obligations", ascending=False)
    )
    dest = cfg.tables_dir / "dim_agency.csv"
    dim.to_csv(dest, index=False)
    written.append(dest)
    log.info("export %-30s %6d rows -> %s", "dim_agency", len(dim), dest.name)
    return written


def write_samples(cfg: Config, max_rows: int = 2000) -> list:
    """Commit-sized samples so the repo is runnable without re-pulling the API."""
    cfg.samples_dir.mkdir(parents=True, exist_ok=True)
    written = []

    # These are small enough to ship whole - shipping the real table beats
    # shipping a truncated one a reader cannot reconcile against the writeup.
    whole = [
        "gov_summary",
        "efficiency_index",
        "index_sensitivity",
        "index_weighting_comparison",
        "review_shortlist",
        "agency_trend",
        "monthly_seasonality",
        "risk_migration",
        "competition_decomposition_series",
        "competition_decomposition",
    ]
    for key in whole:
        src = cfg.curated_dir / CURATED_FILES[key]
        if not src.exists():
            continue
        df = pd.read_parquet(src)
        dest = cfg.samples_dir / f"{key}.csv"
        df.to_csv(dest, index=False)
        written.append(dest)
        log.info("sample %-34s %6d rows -> %s", key, len(df), dest.name)

    # The fact table is sampled to the material agencies only.
    fact = pd.read_parquet(cfg.curated_dir / CURATED_FILES["fact_agency_year"])
    sample = fact[fact["is_material"]].head(max_rows)
    dest = cfg.samples_dir / "fact_agency_year_material.csv"
    sample.to_csv(dest, index=False)
    written.append(dest)
    log.info("sample %-34s %6d rows -> %s", "fact_agency_year", len(sample), dest.name)

    return written
