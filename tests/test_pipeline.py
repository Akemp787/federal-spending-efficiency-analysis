"""Tests over the pipeline plumbing and the committed sample data.

These run without network access. Where a test needs real numbers it reads the
sample CSVs in ``data/samples``, which are committed precisely so that a fresh
clone (and CI) can verify the published findings without re-pulling the API.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from fedspend.config import Config
from fedspend.ingest.usaspending_api import fiscal_month_window, fiscal_year_window
from fedspend.transform.deflator import build_deflator_table, deflate, to_fiscal_year_index

ROOT = Path(__file__).resolve().parents[1]
SAMPLES = ROOT / "data" / "samples"
requires_samples = pytest.mark.skipif(
    not (SAMPLES / "gov_summary.csv").exists(), reason="sample data not generated"
)


# --------------------------------------------------------------------- config
class TestConfig:
    def test_loads_and_exposes_the_window(self):
        cfg = Config.load()
        assert cfg.fiscal_years == [2021, 2022, 2023, 2024, 2025]
        assert cfg.base_fy == 2021
        assert cfg.latest_fy == 2025

    def test_competition_codes_are_disjoint_and_complete(self):
        cfg = Config.load()
        competed, not_competed = set(cfg.competed_codes), set(cfg.not_competed_codes)
        assert competed.isdisjoint(not_competed)
        assert len(competed | not_competed) == len(cfg.all_competition_codes)

    def test_follow_on_actions_default_to_not_competed(self):
        # The convention matters enough to pin: FPDS code E is the parent award's
        # competition, not this action's.
        assert "E" in Config.load().not_competed_codes

    def test_every_pricing_code_maps_to_exactly_one_risk_bucket(self):
        cfg = Config.load()
        buckets = cfg.pricing_bucket_by_code
        assert len(buckets) == len(cfg.all_pricing_codes)
        assert set(buckets.values()) <= {"fixed_price", "cost_reimbursement", "labor_hour", "other"}
        assert buckets["J"] == "fixed_price"        # firm fixed price
        assert buckets["Y"] == "labor_hour"         # time and materials
        assert buckets["U"] == "cost_reimbursement" # cost plus fixed fee

    def test_index_weights_sum_to_one(self):
        weights = Config.load()["efficiency_index"]["weights"]
        assert sum(weights.values()) == pytest.approx(1.0)


# ------------------------------------------------------------- fiscal calendar
class TestFiscalCalendar:
    def test_fiscal_year_runs_october_to_september(self):
        assert fiscal_year_window(2025) == ("2024-10-01", "2025-09-30")

    def test_fiscal_month_one_is_october_of_the_prior_year(self):
        start, end, year, month = fiscal_month_window(2025, 1)
        assert (start, end, year, month) == ("2024-10-01", "2024-10-31", 2024, 10)

    def test_fiscal_month_twelve_is_september(self):
        start, end, year, month = fiscal_month_window(2025, 12)
        assert (start, end, year, month) == ("2025-09-01", "2025-09-30", 2025, 9)

    def test_february_leap_year_end_date_is_correct(self):
        _, end, _, _ = fiscal_month_window(2024, 5)  # Feb 2024
        assert end == "2024-02-29"

    def test_twelve_months_tile_the_year_without_gaps(self):
        windows = [fiscal_month_window(2025, m) for m in range(1, 13)]
        assert windows[0][0] == fiscal_year_window(2025)[0]
        assert windows[-1][1] == fiscal_year_window(2025)[1]

    @pytest.mark.parametrize("bad", [0, 13, -1])
    def test_rejects_out_of_range_months(self, bad):
        with pytest.raises(ValueError):
            fiscal_month_window(2025, bad)


# -------------------------------------------------------------------- deflator
class TestDeflator:
    @staticmethod
    def _quarterly():
        # Four quarters per fiscal year, values chosen so FY means are round.
        rows = []
        for fy, value in ((2024, 100.0), (2025, 110.0)):
            for cal_year, month in ((fy - 1, 10), (fy, 1), (fy, 4), (fy, 7)):
                rows.append({"date": pd.Timestamp(cal_year, month, 1), "deflator": value})
        return pd.DataFrame(rows)

    def test_fiscal_year_index_averages_the_right_four_quarters(self):
        out = to_fiscal_year_index(self._quarterly(), [2024, 2025])
        assert out.loc[out.fiscal_year == 2024, "deflator"].iloc[0] == pytest.approx(100.0)
        assert out.loc[out.fiscal_year == 2025, "deflator"].iloc[0] == pytest.approx(110.0)
        assert (out["quarters_observed"] == 4).all()

    def test_missing_year_raises_rather_than_silently_dropping(self):
        with pytest.raises(ValueError, match="no data for fiscal years"):
            to_fiscal_year_index(self._quarterly(), [2024, 2025, 2026])

    def test_deflate_converts_to_constant_base_year_dollars(self):
        table = pd.DataFrame(
            {"fiscal_year": [2024, 2025], "real_multiplier": [1.10, 1.00]}
        )
        df = pd.DataFrame({"fiscal_year": [2024, 2025], "obligations": [100.0, 100.0]})
        out = deflate(df, table, "obligations")
        assert out["obligations_real"].tolist() == pytest.approx([110.0, 100.0])

    def test_deflate_raises_on_an_unmatched_year(self):
        table = pd.DataFrame({"fiscal_year": [2025], "real_multiplier": [1.0]})
        df = pd.DataFrame({"fiscal_year": [2019], "obligations": [1.0]})
        with pytest.raises(ValueError, match="No deflator"):
            deflate(df, table, "obligations")

    def test_base_year_multiplier_is_exactly_one(self):
        cache = ROOT / "data" / "raw" / "gdpdef_quarterly.csv"
        if not cache.exists():
            pytest.skip("deflator cache not present")
        table = build_deflator_table("", [2021, 2025], 2025, cache_path=cache)
        base = table.loc[table.fiscal_year == 2025, "real_multiplier"].iloc[0]
        assert base == pytest.approx(1.0)


# ------------------------------------------------------- published sample data
@requires_samples
class TestPublishedNumbers:
    @staticmethod
    def _gov():
        return pd.read_csv(SAMPLES / "gov_summary.csv").sort_values("fiscal_year")

    def test_every_fiscal_year_is_present(self):
        assert self._gov()["fiscal_year"].tolist() == [2021, 2022, 2023, 2024, 2025]

    def test_real_growth_is_materially_below_nominal_growth(self):
        gov = self._gov()
        nominal = gov["obligations"].iloc[-1] / gov["obligations"].iloc[0] - 1
        real = gov["obligations_real"].iloc[-1] / gov["obligations_real"].iloc[0] - 1
        assert nominal > real
        assert nominal - real > 0.10   # the deflator wedge is more than 10 points

    def test_shares_are_within_the_unit_interval(self):
        gov = self._gov()
        for col in ("competed_share", "government_risk_share", "september_share", "q4_share"):
            assert gov[col].between(0, 1).all(), col

    def test_september_share_always_exceeds_an_even_pace(self):
        assert (self._gov()["september_share"] > 1 / 12).all()

    def test_decomposition_reconciles_in_the_published_series(self):
        series = pd.read_csv(SAMPLES / "competition_decomposition_series.csv")
        assert series["reconciliation_residual"].abs().max() < 1e-9
        terms = series[["within_effect", "mix_effect", "interaction_effect"]].sum(axis=1)
        pd.testing.assert_series_equal(
            terms, series["total_change"], check_names=False, atol=1e-12
        )

    def test_index_scores_are_bounded_and_ranked_consistently(self):
        idx = pd.read_csv(SAMPLES / "efficiency_index.csv")
        assert idx["efficiency_index"].between(0, 100).all()
        ordered = idx.sort_values("rank")
        assert ordered["efficiency_index"].is_monotonic_decreasing

    def test_sensitivity_ranks_bracket_the_configured_rank(self):
        idx = pd.read_csv(SAMPLES / "efficiency_index.csv")[["agency_name", "rank"]]
        sens = pd.read_csv(SAMPLES / "index_sensitivity.csv")
        merged = idx.merge(sens, on="agency_name")
        assert (merged["rank_best"] <= merged["rank_worst"]).all()
        assert (merged["rank_best"] >= 1).all()
        assert (merged["rank_worst"] <= len(merged)).all()

    def test_scored_agencies_all_clear_the_materiality_floor(self):
        idx = pd.read_csv(SAMPLES / "efficiency_index.csv")
        floor = float(Config.load()["analysis"]["materiality_floor_usd"])
        assert (idx["obligations"] >= floor).all()
