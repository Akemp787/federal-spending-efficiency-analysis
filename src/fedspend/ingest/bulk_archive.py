"""Transaction-level ingestion from the USAspending Award Data Archive.

When this path is needed
------------------------
The aggregation API in :mod:`~fedspend.ingest.usaspending_api` is the project's
primary source and supports every metric in the published analysis. Three
measures genuinely cannot be built from it, because they depend on fields the
category endpoints do not expose:

* **Single-offer rate** - the share of competed dollars that drew exactly one
  offer (``number_of_offers_received == 1``). Competition that attracts one bid
  is competition in form only, and this is the sharpest available proxy for it.
* **Ceiling growth** - how far ``current_total_value_of_award`` has drifted from
  ``base_and_exercised_options_value`` over an award's modification history.
* **Award-level concentration** - HHI computed over every recipient rather than
  each agency's top 100.

This module loads the archive files for those questions. It is deliberately not
required for ``make all``.

Scale and approach
------------------
A single fiscal year of "All Contracts Full" is tens of gigabytes unzipped, far
past what fits in memory. Files are therefore streamed in chunks, projected down
to the needed columns on read, filtered, and appended to a partitioned parquet
dataset. Peak memory stays proportional to the chunk size rather than the file
size, so this runs on a laptop.

Usage
-----
Download the fiscal-year archives from
https://www.usaspending.gov/download_center/award_data_archive into
``data/raw/archive/FY<year>/`` (zip or csv, either is fine), then::

    from fedspend.ingest.bulk_archive import load_fiscal_year, single_offer_rate
    load_fiscal_year(cfg, 2025)
    single_offer_rate(cfg, 2025)
"""

from __future__ import annotations

import zipfile
from collections.abc import Iterator
from pathlib import Path

import pandas as pd

from ..config import Config
from ..logging_utils import get_logger

log = get_logger(__name__)

#: Columns projected on read. Everything else is discarded before it reaches
#: memory, which is the difference between this running and not running.
ARCHIVE_COLUMNS = [
    "contract_transaction_unique_key",
    "contract_award_unique_key",
    "award_id_piid",
    "modification_number",
    "federal_action_obligation",
    "base_and_exercised_options_value",
    "current_total_value_of_award",
    "action_date",
    "action_date_fiscal_year",
    "awarding_agency_name",
    "awarding_sub_agency_name",
    "funding_agency_name",
    "recipient_name",
    "recipient_uei",
    "recipient_parent_name",
    "award_type",
    "type_of_contract_pricing",
    "extent_competed",
    "number_of_offers_received",
    "type_of_set_aside",
    "product_or_service_code",
    "naics_code",
    "contracting_officers_determination_of_business_size",
    "primary_place_of_performance_state_name",
]

NUMERIC_COLUMNS = [
    "federal_action_obligation",
    "base_and_exercised_options_value",
    "current_total_value_of_award",
    "number_of_offers_received",
    "action_date_fiscal_year",
]


def archive_dir(cfg: Config, fiscal_year: int) -> Path:
    return cfg.raw_dir / "archive" / f"FY{fiscal_year}"


def partition_path(cfg: Config, fiscal_year: int) -> Path:
    return cfg.interim_dir / "transactions" / f"fiscal_year={fiscal_year}"


def _iter_source_files(directory: Path) -> Iterator[tuple[str, object]]:
    """Yield (name, file-like) for every CSV in the directory, zipped or loose."""
    if not directory.exists():
        raise FileNotFoundError(
            f"No archive directory at {directory}. Download the fiscal-year files "
            "from https://www.usaspending.gov/download_center/award_data_archive"
        )
    for path in sorted(directory.iterdir()):
        if path.suffix.lower() == ".zip":
            with zipfile.ZipFile(path) as zf:
                for member in zf.namelist():
                    if member.lower().endswith(".csv"):
                        with zf.open(member) as handle:
                            yield f"{path.name}::{member}", handle
        elif path.suffix.lower() == ".csv":
            with path.open("rb") as handle:
                yield path.name, handle


def _clean_chunk(chunk: pd.DataFrame) -> pd.DataFrame:
    chunk.columns = chunk.columns.str.strip().str.lower().str.replace(" ", "_", regex=False)
    for col in NUMERIC_COLUMNS:
        if col in chunk.columns:
            chunk[col] = pd.to_numeric(chunk[col], errors="coerce")
    if "action_date" in chunk.columns:
        chunk["action_date"] = pd.to_datetime(chunk["action_date"], errors="coerce")
    for col in chunk.select_dtypes(include="object").columns:
        chunk[col] = chunk[col].astype("string").str.strip()
    return chunk


def load_fiscal_year(
    cfg: Config,
    fiscal_year: int,
    *,
    chunk_size: int = 500_000,
    columns: list[str] | None = None,
) -> Path:
    """Stream one fiscal year's archive into a partitioned parquet dataset.

    Returns the partition directory. Rows whose ``action_date_fiscal_year`` does
    not match are dropped: the archive files are organised by the year the file
    was published, not solely by the year of the action.
    """
    columns = columns or ARCHIVE_COLUMNS
    out_dir = partition_path(cfg, fiscal_year)
    out_dir.mkdir(parents=True, exist_ok=True)

    total_rows = 0
    part = 0
    for name, handle in _iter_source_files(archive_dir(cfg, fiscal_year)):
        log.info("reading %s", name)
        reader = pd.read_csv(
            handle,
            usecols=lambda c: c.strip().lower().replace(" ", "_") in set(columns),
            chunksize=chunk_size,
            low_memory=False,
        )
        for chunk in reader:
            chunk = _clean_chunk(chunk)
            if "action_date_fiscal_year" in chunk.columns:
                chunk = chunk[chunk["action_date_fiscal_year"] == fiscal_year]
            if chunk.empty:
                continue
            chunk.to_parquet(out_dir / f"part-{part:05d}.parquet", index=False)
            total_rows += len(chunk)
            part += 1
            if part % 20 == 0:
                log.info("  %s rows written so far", f"{total_rows:,}")

    log.info("FY%s: %s transactions -> %s", fiscal_year, f"{total_rows:,}", out_dir)
    return out_dir


def _read_partition(cfg: Config, fiscal_year: int, columns: list[str]) -> pd.DataFrame:
    path = partition_path(cfg, fiscal_year)
    if not path.exists():
        raise FileNotFoundError(f"No loaded transactions for FY{fiscal_year}. Run load_fiscal_year first.")
    return pd.read_parquet(path, columns=columns)


def single_offer_rate(cfg: Config, fiscal_year: int) -> pd.DataFrame:
    """Share of *competed* obligations that drew exactly one offer, by agency.

    This is the measure the aggregation API cannot produce, and the reason the
    bulk path exists. A competed action that attracts a single bid has satisfied
    the process but not obtained the price discipline competition is for, so this
    rate is a materially stronger signal than the headline competition rate.
    """
    df = _read_partition(
        cfg,
        fiscal_year,
        [
            "awarding_agency_name",
            "federal_action_obligation",
            "extent_competed",
            "number_of_offers_received",
        ],
    )
    competed_labels = {
        "FULL AND OPEN COMPETITION",
        "FULL AND OPEN COMPETITION AFTER EXCLUSION OF SOURCES",
        "COMPETED UNDER SAP",
        "COMPETITIVE DELIVERY ORDER",
    }
    df["obligations"] = df["federal_action_obligation"].clip(lower=0)
    competed = df[df["extent_competed"].str.upper().isin(competed_labels)]

    grouped = competed.groupby("awarding_agency_name", as_index=False).agg(
        competed_obligations=("obligations", "sum")
    )
    single = (
        competed[competed["number_of_offers_received"] == 1]
        .groupby("awarding_agency_name", as_index=False)
        .agg(single_offer_obligations=("obligations", "sum"))
    )
    out = grouped.merge(single, on="awarding_agency_name", how="left")
    out["single_offer_obligations"] = out["single_offer_obligations"].fillna(0.0)
    out["single_offer_rate"] = (
        out["single_offer_obligations"] / out["competed_obligations"]
    ).where(out["competed_obligations"] > 0)
    out["fiscal_year"] = fiscal_year
    return out.sort_values("single_offer_obligations", ascending=False).reset_index(drop=True)


def ceiling_growth(cfg: Config, fiscal_year: int, min_base_value: float = 1e6) -> pd.DataFrame:
    """Growth from an award's base value to its current total value, by agency.

    Computed at award level (deduplicating to the latest modification), so
    repeated modifications on one award count once.
    """
    df = _read_partition(
        cfg,
        fiscal_year,
        [
            "contract_award_unique_key",
            "awarding_agency_name",
            "modification_number",
            "base_and_exercised_options_value",
            "current_total_value_of_award",
        ],
    )
    latest = (
        df.sort_values("modification_number")
        .groupby("contract_award_unique_key", as_index=False)
        .last()
    )
    latest = latest[latest["base_and_exercised_options_value"] >= min_base_value]
    latest["ceiling_growth_pct"] = (
        latest["current_total_value_of_award"] / latest["base_and_exercised_options_value"] - 1.0
    ) * 100.0

    out = latest.groupby("awarding_agency_name", as_index=False).agg(
        awards=("contract_award_unique_key", "count"),
        median_ceiling_growth_pct=("ceiling_growth_pct", "median"),
        p90_ceiling_growth_pct=("ceiling_growth_pct", lambda s: s.quantile(0.90)),
        base_value_total=("base_and_exercised_options_value", "sum"),
        current_value_total=("current_total_value_of_award", "sum"),
    )
    out["aggregate_growth_pct"] = (
        out["current_value_total"] / out["base_value_total"] - 1.0
    ) * 100.0
    out["fiscal_year"] = fiscal_year
    return out.sort_values("aggregate_growth_pct", ascending=False).reset_index(drop=True)
