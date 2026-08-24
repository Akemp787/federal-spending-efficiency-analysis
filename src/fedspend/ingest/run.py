"""Orchestrates the full extract stage and lands tidy parquet in ``data/interim``.

Ingestion runs in two phases because one extract depends on another: the set of
agencies worth pulling a vendor breakdown for is defined by their obligation
volume, which is only known after the agency totals land.
"""

from __future__ import annotations

import pandas as pd

from ..config import Config
from ..logging_utils import get_logger
from ..transform.deflator import build_deflator_table
from .usaspending_api import Extractor, write_manifest

log = get_logger(__name__)

EXTRACT_FILES = {
    "agency_totals": "agency_fy.parquet",
    "competition": "agency_fy_competition.parquet",
    "pricing": "agency_fy_pricing.parquet",
    "setaside": "agency_fy_setaside.parquet",
    "monthly": "agency_fy_month.parquet",
    "vendors": "vendor_fy.parquet",
    "agency_vendors": "agency_vendor_fy.parquet",
    "naics": "naics_fy.parquet",
    "psc": "psc_fy.parquet",
    "state": "state_fy.parquet",
    "deflator": "deflator_fy.parquet",
}


def _save(df: pd.DataFrame, cfg: Config, key: str) -> pd.DataFrame:
    path = cfg.interim_dir / EXTRACT_FILES[key]
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False)
    log.info("saved %-26s %6d rows -> %s", key, len(df), path.name)
    return df


def material_agencies(agency_fy: pd.DataFrame, floor_usd: float) -> list[str]:
    """Agencies clearing the obligation floor in at least one fiscal year.

    Using "any year" rather than "the latest year" keeps agencies that were
    material earlier in the window but collapsed later - exactly the cases the
    change analysis exists to surface.
    """
    peak = agency_fy.groupby("agency_name", as_index=False)["obligations"].max()
    keep = peak.loc[peak["obligations"] >= floor_usd, "agency_name"]
    return sorted(keep.tolist())


def run_ingest(cfg: Config, *, skip_existing: bool = False) -> dict[str, pd.DataFrame]:
    """Execute every extract. Returns the frames keyed by extract name."""
    cfg.ensure_dirs()
    ex = Extractor(cfg)
    out: dict[str, pd.DataFrame] = {}

    def need(key: str) -> bool:
        if not skip_existing:
            return True
        path = cfg.interim_dir / EXTRACT_FILES[key]
        if path.exists():
            out[key] = pd.read_parquet(path)
            log.info("skip %-26s (exists, %d rows)", key, len(out[key]))
            return False
        return True

    # ---- phase 1: agency totals drive everything downstream ----------------
    if need("agency_totals"):
        out["agency_totals"] = _save(ex.agency_totals(), cfg, "agency_totals")

    agencies = material_agencies(
        out["agency_totals"], float(cfg["analysis"]["materiality_floor_usd"])
    )
    log.info(
        "%d agencies clear the $%.1fB materiality floor",
        len(agencies),
        cfg["analysis"]["materiality_floor_usd"] / 1e9,
    )

    # ---- phase 2: dimensional cross-tabs -----------------------------------
    if need("competition"):
        out["competition"] = _save(ex.competition_breakdown(), cfg, "competition")
    if need("pricing"):
        out["pricing"] = _save(ex.pricing_breakdown(), cfg, "pricing")
    if need("setaside"):
        out["setaside"] = _save(ex.setaside_totals(), cfg, "setaside")
    if need("monthly"):
        out["monthly"] = _save(ex.monthly_totals(), cfg, "monthly")
    if need("vendors"):
        out["vendors"] = _save(
            ex.vendor_totals(top_n=int(cfg["analysis"]["top_n_vendors"]) * 2), cfg, "vendors"
        )
    vendor_failures: list = []
    if need("agency_vendors"):
        frame, vendor_failures = ex.agency_vendor_totals(agencies, top_n=100)
        out["agency_vendors"] = _save(frame, cfg, "agency_vendors")
    if need("naics"):
        out["naics"] = _save(ex.category_totals("naics", top_n=100), cfg, "naics")
    if need("psc"):
        out["psc"] = _save(ex.category_totals("psc", top_n=100), cfg, "psc")
    if need("state"):
        out["state"] = _save(ex.category_totals("state_territory", top_n=100), cfg, "state")

    # ---- phase 3: reference series -----------------------------------------
    if need("deflator"):
        out["deflator"] = _save(
            build_deflator_table(
                cfg["deflator"]["url"],
                cfg.fiscal_years,
                int(cfg["deflator"]["base_fiscal_year"]),
                cache_path=cfg.raw_dir / "gdpdef_quarterly.csv",
            ),
            cfg,
            "deflator",
        )

    write_manifest(
        cfg,
        {
            "material_agencies": agencies,
            "materiality_floor_usd": cfg["analysis"]["materiality_floor_usd"],
            "agency_vendor_query_failures": vendor_failures,
            "api_cache_hits": ex.client.stats["cache_hits"],
            "api_network_calls": ex.client.stats["network_calls"],
        },
    )
    log.info(
        "ingest complete: %d network calls, %d cache hits",
        ex.client.stats["network_calls"],
        ex.client.stats["cache_hits"],
    )
    return out
