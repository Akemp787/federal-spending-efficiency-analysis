"""Build the analytical extracts from the USAspending v2 aggregation API.

Design note
-----------
The USAspending *Award Data Archive* publishes transaction-level contract files
that run to tens of gigabytes per fiscal year. That is the right source when you
need row-level fields the API does not expose (number of offers received,
modification history). It is the wrong source for a repository that a reviewer
should be able to clone and reproduce in twenty minutes.

This module therefore treats the aggregation API as the primary source. Every
metric in the analysis is built from cross-tabulations the API computes
server-side, and each extract lands as a tidy parquet file keyed on
(fiscal_year, dimension). ``ingest/bulk_archive.py`` covers the transaction-level
path for the metrics that genuinely require it.

Each extract is *long* rather than wide, so adding a fiscal year or a new FPDS
code never changes a schema.
"""

from __future__ import annotations

import calendar
import json
from datetime import date, datetime, timezone
from typing import Any

import pandas as pd

from ..config import Config
from ..logging_utils import get_logger
from .client import UsaSpendingClient

log = get_logger(__name__)


def fiscal_year_window(fy: int) -> tuple[str, str]:
    """Return the (start, end) ISO dates of a federal fiscal year."""
    return f"{fy - 1}-10-01", f"{fy}-09-30"


def fiscal_month_window(fy: int, fiscal_month: int) -> tuple[str, str, int, int]:
    """Return (start, end, calendar_year, calendar_month) for a fiscal month.

    Fiscal month 1 is October of the preceding calendar year.
    """
    if not 1 <= fiscal_month <= 12:
        raise ValueError(f"fiscal_month must be 1-12, got {fiscal_month}")
    offset = fiscal_month + 9  # fiscal month 1 -> calendar month 10 (October)
    cal_year = fy - 1 if offset <= 12 else fy
    cal_month = offset if offset <= 12 else offset - 12
    last_day = calendar.monthrange(cal_year, cal_month)[1]
    return (
        f"{cal_year}-{cal_month:02d}-01",
        f"{cal_year}-{cal_month:02d}-{last_day:02d}",
        cal_year,
        cal_month,
    )


class Extractor:
    """Produces every interim parquet extract the warehouse consumes."""

    def __init__(self, cfg: Config, client: UsaSpendingClient | None = None) -> None:
        self.cfg = cfg
        src = cfg["source"]
        self.client = client or UsaSpendingClient(
            src["api_base"],
            cfg.cache_dir,
            timeout=src["request_timeout_seconds"],
            max_retries=src["max_retries"],
            backoff=src["retry_backoff_seconds"],
            cache_enabled=src["cache_enabled"],
        )

    # ------------------------------------------------------------- filters
    def _base_filters(self, fy: int, **extra: Any) -> dict[str, Any]:
        start, end = fiscal_year_window(fy)
        filters: dict[str, Any] = {
            "time_period": [
                {"start_date": start, "end_date": end, "date_type": self.cfg["source"]["date_type"]}
            ],
            "award_type_codes": self.cfg.award_type_codes,
        }
        filters.update({k: v for k, v in extra.items() if v is not None})
        return filters

    @staticmethod
    def _agency_filter(agency_name: str) -> list[dict[str, str]]:
        return [{"type": "awarding", "tier": "toptier", "name": agency_name}]

    # ------------------------------------------------------------ extracts
    def agency_totals(self) -> pd.DataFrame:
        """fiscal_year x awarding agency -> obligations."""
        rows = []
        for fy in self.cfg.fiscal_years:
            for r in self.client.paged_category("awarding_agency", self._base_filters(fy)):
                rows.append(
                    {
                        "fiscal_year": fy,
                        "agency_id": r.get("id"),
                        "agency_code": r.get("code"),
                        "agency_name": r.get("name"),
                        "agency_slug": r.get("agency_slug"),
                        "obligations": r.get("amount"),
                    }
                )
            log.info("agency_totals FY%s -> %s cumulative rows", fy, len(rows))
        return pd.DataFrame(rows)

    def competition_breakdown(self) -> pd.DataFrame:
        """fiscal_year x agency x extent_competed code -> obligations."""
        labels = {
            **self.cfg["competition"]["competed"],
            **self.cfg["competition"]["not_competed"],
        }
        competed = set(self.cfg.competed_codes)
        rows = []
        for fy in self.cfg.fiscal_years:
            for code in self.cfg.all_competition_codes:
                filters = self._base_filters(fy, extent_competed_type_codes=[code])
                for r in self.client.paged_category("awarding_agency", filters):
                    rows.append(
                        {
                            "fiscal_year": fy,
                            "agency_name": r.get("name"),
                            "extent_competed_code": code,
                            "extent_competed_label": labels[code],
                            "is_competed": code in competed,
                            "obligations": r.get("amount"),
                        }
                    )
            log.info("competition FY%s done (%s cumulative rows)", fy, len(rows))
        return pd.DataFrame(rows)

    def pricing_breakdown(self) -> pd.DataFrame:
        """fiscal_year x agency x contract pricing code -> obligations."""
        labels = {
            str(code): label
            for bucket in self.cfg["pricing_risk"].values()
            for code, label in bucket.items()
        }
        buckets = self.cfg.pricing_bucket_by_code
        rows = []
        for fy in self.cfg.fiscal_years:
            for code in self.cfg.all_pricing_codes:
                filters = self._base_filters(fy, contract_pricing_type_codes=[code])
                for r in self.client.paged_category("awarding_agency", filters):
                    rows.append(
                        {
                            "fiscal_year": fy,
                            "agency_name": r.get("name"),
                            "pricing_code": code,
                            "pricing_label": labels[code],
                            "risk_bucket": buckets[code],
                            "obligations": r.get("amount"),
                        }
                    )
            log.info("pricing FY%s done (%s cumulative rows)", fy, len(rows))
        return pd.DataFrame(rows)

    def setaside_totals(self) -> pd.DataFrame:
        """fiscal_year x agency -> obligations under a small-business set-aside."""
        rows = []
        for fy in self.cfg.fiscal_years:
            filters = self._base_filters(fy, set_aside_type_codes=self.cfg.setaside_codes)
            for r in self.client.paged_category("awarding_agency", filters):
                rows.append(
                    {
                        "fiscal_year": fy,
                        "agency_name": r.get("name"),
                        "setaside_obligations": r.get("amount"),
                    }
                )
            log.info("setaside FY%s done", fy)
        return pd.DataFrame(rows)

    def monthly_totals(self) -> pd.DataFrame:
        """fiscal_year x fiscal month x agency -> obligations (year-end surge)."""
        rows = []
        for fy in self.cfg.fiscal_years:
            for fm in range(1, 13):
                start, end, cal_year, cal_month = fiscal_month_window(fy, fm)
                filters = {
                    "time_period": [
                        {
                            "start_date": start,
                            "end_date": end,
                            "date_type": self.cfg["source"]["date_type"],
                        }
                    ],
                    "award_type_codes": self.cfg.award_type_codes,
                }
                for r in self.client.paged_category("awarding_agency", filters):
                    rows.append(
                        {
                            "fiscal_year": fy,
                            "fiscal_month": fm,
                            "calendar_year": cal_year,
                            "calendar_month": cal_month,
                            "month_name": calendar.month_abbr[cal_month],
                            "agency_name": r.get("name"),
                            "obligations": r.get("amount"),
                        }
                    )
            log.info("monthly FY%s done (%s cumulative rows)", fy, len(rows))
        return pd.DataFrame(rows)

    def vendor_totals(self, top_n: int = 100) -> pd.DataFrame:
        """fiscal_year -> government-wide top vendors."""
        rows = []
        for fy in self.cfg.fiscal_years:
            results = self.client.paged_category(
                "recipient", self._base_filters(fy), page_limit=100, max_pages=max(1, top_n // 100)
            )
            for rank, r in enumerate(results[:top_n], start=1):
                rows.append(
                    {
                        "fiscal_year": fy,
                        "rank": rank,
                        "recipient_name": r.get("name"),
                        "recipient_uei": r.get("uei"),
                        "obligations": r.get("amount"),
                    }
                )
            log.info("vendor_totals FY%s done", fy)
        return pd.DataFrame(rows)

    def agency_vendor_totals(
        self, agencies: list[str], top_n: int = 100
    ) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
        """fiscal_year x agency -> that agency's top vendors (input to vendor HHI).

        These per-agency recipient aggregations are the heaviest queries in the
        pipeline and USAspending occasionally drops the connection on them. A
        failure on one agency-year must not discard the other several hundred, so
        failures are collected and returned rather than raised. The gaps are
        recorded in the run manifest and the affected agency simply scores on
        four dimensions instead of five - visible degradation beats a silent
        zero or an aborted run.
        """
        rows: list[dict[str, Any]] = []
        failures: list[dict[str, Any]] = []
        for fy in self.cfg.fiscal_years:
            for agency in agencies:
                filters = self._base_filters(fy, agencies=self._agency_filter(agency))
                try:
                    results = self.client.paged_category(
                        "recipient", filters, page_limit=100, max_pages=max(1, top_n // 100)
                    )
                except Exception as exc:  # noqa: BLE001 - recorded, not swallowed
                    log.warning("agency_vendor FY%s %s FAILED: %s", fy, agency, exc)
                    failures.append({"fiscal_year": fy, "agency_name": agency, "error": str(exc)})
                    continue
                for rank, r in enumerate(results[:top_n], start=1):
                    rows.append(
                        {
                            "fiscal_year": fy,
                            "agency_name": agency,
                            "rank": rank,
                            "recipient_name": r.get("name"),
                            "recipient_uei": r.get("uei"),
                            "obligations": r.get("amount"),
                        }
                    )
            log.info("agency_vendor FY%s done (%s cumulative rows)", fy, len(rows))
        if failures:
            log.warning("agency_vendor: %d agency-year queries failed", len(failures))
        return pd.DataFrame(rows), failures

    def subagency_breakdown(self, agencies: list[str]) -> pd.DataFrame:
        """fiscal_year x sub-agency -> total and competed obligations.

        Sub-tier is where contracting is actually run. "The Department of
        Defense" does not award contracts; Navy, Army, Air Force and the defence
        agencies do, under different acquisition commands. A department-level
        competition finding that cannot say which component moved is not
        actionable, so this extract exists to close that gap.

        Queried one department at a time rather than government-wide. The
        unfiltered ``awarding_subagency`` aggregation silently truncates its
        result set - it stops at roughly 166 sub-agencies and drops the tail,
        which cost the Department of the Interior its largest component
        (Departmental Offices, $2.2B in FY2025) and left the roll-up 33% short.
        Filtering by department returns the complete list and reconciles exactly
        to the agency total, which the validation suite now asserts.
        """
        competed = self.cfg.competed_codes
        rows: dict[tuple, dict[str, Any]] = {}
        for fy in self.cfg.fiscal_years:
            for agency in agencies:
                base = self._base_filters(fy, agencies=self._agency_filter(agency))
                try:
                    totals = self.client.paged_category("awarding_subagency", base)
                    comp = self.client.paged_category(
                        "awarding_subagency",
                        self._base_filters(
                            fy,
                            agencies=self._agency_filter(agency),
                            extent_competed_type_codes=competed,
                        ),
                    )
                except Exception as exc:  # noqa: BLE001 - recorded by the caller
                    log.warning("subagency FY%s %s FAILED: %s", fy, agency, exc)
                    continue
                for r in totals:
                    key = (fy, agency, r.get("name"))
                    rows[key] = {
                        "fiscal_year": fy,
                        "agency_name": agency,
                        "subagency_name": r.get("name"),
                        "subagency_code": r.get("code"),
                        "obligations": r.get("amount"),
                        "competed_obligations": 0.0,
                    }
                for r in comp:
                    key = (fy, agency, r.get("name"))
                    if key in rows:
                        rows[key]["competed_obligations"] = r.get("amount") or 0.0
            log.info("subagency FY%s done (%s cumulative rows)", fy, len(rows))
        return pd.DataFrame(list(rows.values()))

    def agency_psc_breakdown(self, agencies: list[str], fiscal_years: list[int]) -> pd.DataFrame:
        """agency x product/service code x fiscal_year -> total and competed obligations.

        Feeds the portfolio-adjusted competition rate. Without it, comparing one
        agency's competition rate to another's compares what they buy as much as
        how they buy it: an agency procuring nuclear propulsion has fewer
        qualified sources than one procuring office furniture, and no amount of
        contracting reform changes that.
        """
        competed = self.cfg.competed_codes
        rows: dict[tuple, dict[str, Any]] = {}
        for fy in fiscal_years:
            for agency in agencies:
                base = self._base_filters(fy, agencies=self._agency_filter(agency))
                try:
                    totals = self.client.paged_category("psc", base, page_limit=100, max_pages=3)
                    comp = self.client.paged_category(
                        "psc",
                        self._base_filters(
                            fy,
                            agencies=self._agency_filter(agency),
                            extent_competed_type_codes=competed,
                        ),
                        page_limit=100,
                        max_pages=3,
                    )
                except Exception as exc:  # noqa: BLE001 - recorded by the caller
                    log.warning("psc FY%s %s FAILED: %s", fy, agency, exc)
                    continue
                for r in totals:
                    key = (fy, agency, r.get("code"))
                    rows[key] = {
                        "fiscal_year": fy,
                        "agency_name": agency,
                        "psc_code": r.get("code"),
                        "psc_name": r.get("name"),
                        "obligations": r.get("amount"),
                        "competed_obligations": 0.0,
                    }
                for r in comp:
                    key = (fy, agency, r.get("code"))
                    if key in rows:
                        rows[key]["competed_obligations"] = r.get("amount") or 0.0
            log.info("agency_psc FY%s done (%s cumulative rows)", fy, len(rows))
        return pd.DataFrame(list(rows.values()))

    def category_totals(self, category: str, top_n: int = 100) -> pd.DataFrame:
        """fiscal_year -> top values of an arbitrary spending category."""
        rows = []
        for fy in self.cfg.fiscal_years:
            results = self.client.paged_category(
                category, self._base_filters(fy), page_limit=100, max_pages=max(1, top_n // 100)
            )
            for rank, r in enumerate(results[:top_n], start=1):
                rows.append(
                    {
                        "fiscal_year": fy,
                        "category": category,
                        "rank": rank,
                        "code": r.get("code"),
                        "name": r.get("name"),
                        "obligations": r.get("amount"),
                    }
                )
            log.info("category %s FY%s done", category, fy)
        return pd.DataFrame(rows)


# ---------------------------------------------------------------- manifest
def write_manifest(cfg: Config, extras: dict[str, Any] | None = None) -> None:
    """Record exactly what was pulled and when, next to the curated data."""
    manifest = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "snapshot_date": date.today().isoformat(),
        "fiscal_years": cfg.fiscal_years,
        "award_type_codes": cfg.award_type_codes,
        "api_base": cfg["source"]["api_base"],
        "deflator_series": cfg["deflator"]["series_id"],
        "deflator_base_fy": cfg["deflator"]["base_fiscal_year"],
        "competition_competed_codes": cfg.competed_codes,
        "notes": (
            "Obligations are transaction-level federal_action_obligation summed "
            "server-side by USAspending. Negative values are de-obligations and "
            "are retained, so annual figures are net obligations."
        ),
    }
    if extras:
        manifest.update(extras)
    cfg.curated_dir.mkdir(parents=True, exist_ok=True)
    (cfg.curated_dir / "_manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    log.info("Wrote manifest -> %s", cfg.curated_dir / "_manifest.json")
