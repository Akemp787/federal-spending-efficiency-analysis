"""Contract tests for the Power BI export.

A Power BI model fails in ways a CSV never does: a duplicate key silently
becomes a many-to-many relationship, an orphan foreign key silently drops rows
from a visual, and neither shows up as an error - the numbers just come out
quietly wrong. These tests assert the model's structural guarantees so a change
to the analysis cannot break the report without failing the build first.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
PBI = ROOT / "work-in-progress" / "powerbi"
DATA = PBI / "data"

requires_export = pytest.mark.skipif(
    not (DATA / "dim_agency.csv").exists(),
    reason="Power BI export not built (run `fedspend powerbi`)",
)

# (fact table, foreign key, dimension table, dimension key)
RELATIONSHIPS = [
    ("fact_agency_year", "agency_name", "dim_agency", "agency_name"),
    ("fact_portfolio_adjusted", "agency_name", "dim_agency", "agency_name"),
    ("fact_efficiency_index", "agency_name", "dim_agency", "agency_name"),
    ("fact_index_sensitivity", "agency_name", "dim_agency", "agency_name"),
    ("fact_review_shortlist", "agency_name", "dim_agency", "agency_name"),
    ("fact_risk_migration", "agency_name", "dim_agency", "agency_name"),
    ("fact_vendor_concentration", "agency_name", "dim_agency", "agency_name"),
    ("viz_largest_movers", "agency_name", "dim_agency", "agency_name"),
    ("viz_portfolio_adjusted", "agency_name", "dim_agency", "agency_name"),
    ("viz_efficiency_index", "agency_name", "dim_agency", "agency_name"),
    ("fact_subagency_year", "subagency_key", "dim_subagency", "subagency_key"),
    ("fact_agency_year", "fiscal_year", "dim_fiscal_year", "fiscal_year"),
    ("fact_month", "fiscal_year", "dim_fiscal_year", "fiscal_year"),
    ("fact_government_year", "fiscal_year", "dim_fiscal_year", "fiscal_year"),
    ("fact_subagency_year", "fiscal_year", "dim_fiscal_year", "fiscal_year"),
    ("viz_growth_index", "fiscal_year", "dim_fiscal_year", "fiscal_year"),
    ("viz_competition_trend", "fiscal_year", "dim_fiscal_year", "fiscal_year"),
    ("viz_military_departments", "fiscal_year", "dim_fiscal_year", "fiscal_year"),
]

DIMENSION_KEYS = [
    ("dim_fiscal_year", "fiscal_year"),
    ("dim_agency", "agency_name"),
    ("dim_subagency", "subagency_key"),
    ("dim_glossary", "term"),
]


def read(name: str) -> pd.DataFrame:
    return pd.read_csv(DATA / f"{name}.csv")


@requires_export
class TestModelStructure:
    @pytest.mark.parametrize(("table", "key"), DIMENSION_KEYS)
    def test_dimension_keys_are_unique(self, table, key):
        """A duplicate on the one-side makes the relationship many-to-many."""
        df = read(table)
        dupes = df[key][df[key].duplicated()].tolist()
        assert not dupes, f"{table}.{key} has duplicates: {dupes[:5]}"

    @pytest.mark.parametrize(("fact", "fk", "dim", "pk"), RELATIONSHIPS)
    def test_no_orphan_foreign_keys(self, fact, fk, dim, pk):
        """An orphan key drops rows from a visual with no error shown."""
        orphans = set(read(fact)[fk].dropna()) - set(read(dim)[pk])
        assert not orphans, f"{fact}.{fk} has {len(orphans)} orphans: {sorted(orphans)[:3]}"

    def test_subagency_name_alone_would_not_work_as_a_key(self):
        """Documents *why* the composite key exists.

        If this ever starts passing, the bare name became unique and the
        surrogate key could be simplified - but until then, removing it would
        silently break the relationship.
        """
        dim = read("dim_subagency")
        assert not dim["subagency_name"].is_unique, (
            "subagency_name is now unique; the composite key may no longer be needed"
        )
        assert dim["subagency_key"].is_unique


@requires_export
class TestVisualTables:
    def test_growth_index_is_long_with_two_series(self):
        df = read("viz_growth_index")
        assert set(df.columns) >= {"fiscal_year", "basis", "index_value", "sort_order"}
        assert df["basis"].nunique() == 2
        # One row per (year, basis) - a wide table here would break the legend.
        assert not df.duplicated(["fiscal_year", "basis"]).any()

    def test_competition_trend_has_three_series_per_year(self):
        df = read("viz_competition_trend")
        assert df["series"].nunique() == 3
        assert df.groupby("fiscal_year").size().eq(3).all()

    def test_portfolio_table_pairs_every_agency(self):
        df = read("viz_portfolio_adjusted")
        assert set(df["measure"]) == {"Observed", "Portfolio-adjusted"}
        assert df.groupby("agency_name").size().eq(2).all()

    def test_rates_are_within_bounds(self):
        df = read("viz_portfolio_adjusted")
        assert df["rate"].between(0, 1).all()
        assert df["rate_pct"].between(0, 100).all()

    def test_monthly_pacing_covers_twelve_months_with_one_september(self):
        df = read("viz_monthly_pacing")
        assert len(df) == 12
        assert df["is_september"].sum() == 1
        assert df.loc[df["is_september"], "fiscal_month"].iloc[0] == 12

    def test_efficiency_band_is_ordered_and_non_negative(self):
        df = read("viz_efficiency_index")
        # Error-bar offsets must be non-negative or the visual renders inverted.
        assert (df["band_low"] >= -1e-9).all()
        assert (df["band_high"] >= -1e-9).all()
        assert df["efficiency_index"].is_monotonic_decreasing

    def test_movers_direction_matches_sign(self):
        df = read("viz_largest_movers")
        assert (df.loc[df["direction"] == "Increase", "change_bn"] >= 0).all()
        assert (df.loc[df["direction"] == "Decrease", "change_bn"] < 0).all()


@requires_export
class TestNarrativeTables:
    def test_recommendations_are_complete(self):
        df = read("viz_recommendations")
        assert len(df) == 6
        assert set(df["confidence"]) <= {"High", "Medium", "Low"}
        assert df["evidence"].str.len().gt(30).all(), "every recommendation needs its evidence"
        assert (df["confidence"] == "Low").any(), "at least one low-confidence item is intended"

    def test_limitations_cover_the_required_categories(self):
        df = read("viz_limitations")
        assert {"Scope", "Measurement", "Method", "Interpretation"} <= set(df["category"])
        joined = " ".join(df["limitation"] + " " + df["detail"]).lower()
        # The two claims the deck must never be read as making.
        assert "waste, fraud or abuse" in joined
        assert "savings" in joined


@requires_export
class TestTheme:
    def test_theme_is_valid_json_with_required_keys(self):
        theme = json.loads((PBI / "fedspend_theme.json").read_text(encoding="utf-8"))
        assert {"name", "dataColors", "background", "foreground"} <= set(theme)
        assert len(theme["dataColors"]) >= 4

    def test_theme_colours_are_hex(self):
        theme = json.loads((PBI / "fedspend_theme.json").read_text(encoding="utf-8"))
        for colour in theme["dataColors"]:
            assert colour.startswith("#") and len(colour) == 7, colour


@requires_export
class TestDaxReferencesResolve:
    """Every table named in measures.dax must exist in the export.

    Catches the common failure where a table is renamed in the exporter and the
    DAX silently references a table that is no longer there.
    """

    def test_all_referenced_tables_exist(self):
        import re

        dax = (PBI / "measures.dax").read_text(encoding="utf-8")
        # Strip comments so commentary about tables is not treated as a reference.
        body = "\n".join(
            line for line in dax.splitlines() if not line.strip().startswith("//")
        )
        referenced = set(re.findall(r"\b((?:fact|dim|viz)_[a-z_]+)\[", body))
        available = {p.stem for p in DATA.glob("*.csv")}
        missing = referenced - available
        assert not missing, f"measures.dax references missing tables: {sorted(missing)}"
