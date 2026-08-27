"""Unit tests for the metric implementations.

These are known-answer tests, not smoke tests: each case has a value that can be
worked out by hand, so a regression changes a number rather than merely throwing.
None of them touch the network.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from fedspend.metrics import (
    anomaly,
    competition,
    concentration,
    decomposition,
    growth,
    pricing_risk,
    timing,
)
from fedspend.metrics import efficiency_index as cei
from fedspend.metrics import standardization as stdz


# --------------------------------------------------------------- concentration
class TestConcentration:
    def test_monopoly_scores_10000(self):
        assert concentration.herfindahl([100.0]) == pytest.approx(10_000.0)

    def test_four_equal_players_score_2500(self):
        assert concentration.herfindahl([25, 25, 25, 25]) == pytest.approx(2_500.0)

    def test_explicit_total_anchors_shares_to_the_real_market(self):
        # Two observed vendors at 25 each, but the market is really 100.
        # Shares are 0.25 and 0.25 -> 2 * 0.0625 * 10000 = 1250, not 5000.
        assert concentration.herfindahl([25, 25], total=100) == pytest.approx(1_250.0)
        assert concentration.herfindahl([25, 25]) == pytest.approx(5_000.0)

    def test_negative_values_cannot_hold_market_share(self):
        assert concentration.herfindahl([50, 50, -20]) == pytest.approx(5_000.0)

    def test_normalized_hhi_is_zero_for_a_perfectly_even_market(self):
        assert concentration.normalized_herfindahl([10] * 5) == pytest.approx(0.0, abs=1e-12)

    def test_concentration_ratio(self):
        assert concentration.concentration_ratio([40, 30, 20, 10], 2) == pytest.approx(0.7)

    def test_gini_is_zero_when_perfectly_even(self):
        assert concentration.gini([10, 10, 10, 10]) == pytest.approx(0.0, abs=1e-9)

    def test_hhi_classification_uses_doj_thresholds(self):
        assert concentration.classify_hhi(1_400) == "unconcentrated"
        assert concentration.classify_hhi(2_000) == "moderately concentrated"
        assert concentration.classify_hhi(3_000) == "highly concentrated"

    def test_profile_reports_coverage_when_truncated(self):
        df = pd.DataFrame({"g": ["a", "a"], "v": [30.0, 20.0]})
        totals = pd.DataFrame({"g": ["a"], "obligations": [100.0]})
        out = concentration.concentration_profile(df, ["g"], "v", totals=totals)
        assert out["coverage_share"].iloc[0] == pytest.approx(0.5)
        assert out["market_total"].iloc[0] == pytest.approx(100.0)


# ---------------------------------------------------------------- competition
class TestCompetition:
    @staticmethod
    def _frame():
        return pd.DataFrame(
            {
                "fiscal_year": [2025] * 4,
                "agency_name": ["X"] * 4,
                "extent_competed_code": ["A", "D", "C", "E"],
                "is_competed": [True, True, False, False],
                "obligations": [60.0, 20.0, 15.0, 5.0],
            }
        )

    def test_competed_share(self):
        out = competition.competed_share(self._frame(), ["fiscal_year", "agency_name"])
        assert out["competed_share"].iloc[0] == pytest.approx(0.80)
        assert out["not_competed_obligations"].iloc[0] == pytest.approx(20.0)

    def test_override_reclassifies_follow_on_actions(self):
        out = competition.competed_share(
            self._frame(), ["fiscal_year", "agency_name"], competed_codes=["A", "D", "E"]
        )
        assert out["competed_share"].iloc[0] == pytest.approx(0.85)

    def test_negative_buckets_do_not_enter_the_denominator(self):
        df = self._frame()
        df.loc[df["extent_competed_code"] == "C", "obligations"] = -15.0
        out = competition.competed_share(df, ["fiscal_year", "agency_name"])
        # denominator becomes 60 + 20 + 0 + 5 = 85
        assert out["competed_share"].iloc[0] == pytest.approx(80 / 85)

    def test_exposure_measures_dollars_below_the_peer_benchmark(self):
        competed = pd.DataFrame(
            {
                "fiscal_year": [2025, 2025],
                "agency_name": ["Low", "High"],
                "competed_obligations": [50.0, 90.0],
                "classified_obligations": [100.0, 100.0],
                "competed_share": [0.5, 0.9],
            }
        )
        out = competition.noncompeted_dollar_exposure(competed)
        low = out[out["agency_name"] == "Low"].iloc[0]
        assert low["benchmark_share"] == pytest.approx(0.70)  # 140/200
        assert low["dollars_below_benchmark"] == pytest.approx(20.0)


# --------------------------------------------------------------- pricing risk
class TestPricingRisk:
    def test_government_risk_share_sums_the_right_buckets(self):
        df = pd.DataFrame(
            {
                "fiscal_year": [2025] * 4,
                "risk_bucket": ["fixed_price", "cost_reimbursement", "labor_hour", "other"],
                "obligations": [60.0, 20.0, 10.0, 10.0],
            }
        )
        out = pricing_risk.pricing_mix(df, ["fiscal_year"])
        assert out["government_risk_share"].iloc[0] == pytest.approx(0.30)
        assert out["fixed_price_share"].iloc[0] == pytest.approx(0.60)

    def test_missing_buckets_default_to_zero(self):
        df = pd.DataFrame(
            {"fiscal_year": [2025], "risk_bucket": ["fixed_price"], "obligations": [100.0]}
        )
        out = pricing_risk.pricing_mix(df, ["fiscal_year"])
        assert out["labor_hour_share"].iloc[0] == pytest.approx(0.0)
        assert out["government_risk_share"].iloc[0] == pytest.approx(0.0)


# --------------------------------------------------------------------- timing
class TestTiming:
    def test_even_year_gives_a_surge_ratio_of_one(self):
        df = pd.DataFrame(
            {
                "fiscal_year": [2025] * 12,
                "fiscal_month": list(range(1, 13)),
                "month_name": ["m"] * 12,
                "obligations": [100.0] * 12,
            }
        )
        out = timing.timing_profile(df, ["fiscal_year"])
        assert out["september_share"].iloc[0] == pytest.approx(1 / 12)
        assert out["surge_ratio"].iloc[0] == pytest.approx(1.0)
        assert out["september_excess_obligations"].iloc[0] == pytest.approx(0.0)

    def test_year_end_spike_is_detected(self):
        obligations = [10.0] * 11 + [200.0]
        df = pd.DataFrame(
            {
                "fiscal_year": [2025] * 12,
                "fiscal_month": list(range(1, 13)),
                "month_name": ["m"] * 12,
                "obligations": obligations,
            }
        )
        out = timing.timing_profile(df, ["fiscal_year"])
        assert out["september_share"].iloc[0] == pytest.approx(200 / 310)
        assert out["surge_ratio"].iloc[0] == pytest.approx(20.0)

    def test_seasonality_index_is_100_at_an_even_pace(self):
        df = pd.DataFrame(
            {
                "fiscal_year": [2025] * 12,
                "fiscal_month": list(range(1, 13)),
                "month_name": ["m"] * 12,
                "obligations": [50.0] * 12,
            }
        )
        out = timing.monthly_seasonality(df)
        assert out["index_vs_even_pace"].round(6).eq(100.0).all()


# --------------------------------------------------------------------- growth
class TestGrowth:
    def test_cagr(self):
        assert growth.cagr(100, 121, 2) == pytest.approx(10.0)

    def test_cagr_is_undefined_off_a_non_positive_base(self):
        assert np.isnan(growth.cagr(0, 100, 2))
        assert np.isnan(growth.cagr(-5, 100, 2))

    def test_yoy_suppresses_growth_off_a_non_positive_base(self):
        df = pd.DataFrame(
            {"g": ["a"] * 3, "fiscal_year": [2023, 2024, 2025], "v": [0.0, 50.0, 75.0]}
        )
        out = growth.year_over_year(df, ["g"], "v")
        assert np.isnan(out["change_pct"].iloc[1])          # base was zero
        assert out["change_pct"].iloc[2] == pytest.approx(50.0)

    def test_contribution_shares_sum_to_one(self):
        df = pd.DataFrame(
            {
                "fiscal_year": [2021, 2021, 2025, 2025],
                "agency_name": ["a", "b", "a", "b"],
                "v": [100.0, 100.0, 150.0, 130.0],
            }
        )
        out = growth.contribution_to_change(df, "agency_name", "v")
        assert out["change"].sum() == pytest.approx(80.0)
        assert out["share_of_total_change"].sum() == pytest.approx(1.0)


# -------------------------------------------------------------------- anomaly
class TestAnomaly:
    def test_robust_z_is_not_masked_by_the_outlier_it_measures(self):
        # A single extreme value inflates the standard deviation enough to hide
        # itself from a classical z-score. The MAD is unmoved by it.
        values = [10, 11, 9, 10, 12, 10, 11, 1000]
        classical = (values[-1] - np.mean(values)) / np.std(values, ddof=1)
        robust = anomaly.robust_z(values)[-1]
        assert classical < 3          # masked
        assert robust > 500           # detected

    def test_robust_z_degrades_gracefully_when_the_mad_is_zero(self):
        # More than half the observations share a value, so MAD == 0 and the
        # mean-absolute-deviation fallback takes over. The score is smaller than
        # the MAD path would give but still clears the outlier threshold.
        values = [10] * 7 + [1000]
        z = anomaly.robust_z(values)[-1]
        assert np.isfinite(z)
        assert z > 3

    def test_zero_mad_falls_back_without_dividing_by_zero(self):
        z = anomaly.robust_z([5, 5, 5, 5, 9])
        assert np.isfinite(z).all()

    def test_flags_respect_the_threshold(self):
        df = pd.DataFrame({"v": [1, 1, 1, 1, 1, 50]})
        out = anomaly.flag_outliers(df, "v", threshold=3.0)
        assert bool(out["v_is_high_outlier"].iloc[-1]) is True
        assert not out["v_is_high_outlier"].iloc[:-1].any()

    def test_priority_matrix_splits_on_medians(self):
        # medians are scale 2.5 and signal 2.5; only "d" is at or above both.
        df = pd.DataFrame(
            {
                "agency_name": list("abcd"),
                "scale": [1.0, 2.0, 3.0, 4.0],
                "signal": [1.0, 4.0, 2.0, 3.0],
            }
        ).set_index("agency_name")
        out = anomaly.priority_matrix(
            df.reset_index(), scale_col="scale", signal_col="signal"
        ).set_index("agency_name")
        assert out["is_priority"].sum() == 1
        assert bool(out.loc["d", "is_priority"]) is True
        assert bool(out.loc["b", "is_priority"]) is False   # high signal, low scale
        assert out.loc["b", "quadrant"] == "Low spend / high signal"


# -------------------------------------------------------------- decomposition
class TestShiftShare:
    def test_pure_within_effect_when_weights_are_unchanged(self):
        df = pd.DataFrame(
            {
                "fiscal_year": [2024, 2024, 2025, 2025],
                "agency_name": ["a", "b", "a", "b"],
                "obligations": [50.0, 50.0, 50.0, 50.0],
                "rate": [0.8, 0.6, 0.7, 0.6],
            }
        )
        _, s = decomposition.shift_share(
            df, group_col="agency_name", weight_col="obligations", rate_col="rate"
        )
        assert s["total_change"] == pytest.approx(-0.05)
        assert s["within_effect"] == pytest.approx(-0.05)
        assert s["mix_effect"] == pytest.approx(0.0, abs=1e-12)

    def test_pure_mix_effect_when_rates_are_unchanged(self):
        df = pd.DataFrame(
            {
                "fiscal_year": [2024, 2024, 2025, 2025],
                "agency_name": ["a", "b", "a", "b"],
                "obligations": [50.0, 50.0, 75.0, 25.0],
                "rate": [0.4, 0.8, 0.4, 0.8],
            }
        )
        _, s = decomposition.shift_share(
            df, group_col="agency_name", weight_col="obligations", rate_col="rate"
        )
        assert s["within_effect"] == pytest.approx(0.0, abs=1e-12)
        assert s["mix_effect"] == pytest.approx(s["total_change"])

    def test_terms_always_reconcile_to_the_observed_change(self):
        rng = np.random.default_rng(7)
        df = pd.DataFrame(
            {
                "fiscal_year": [2024] * 6 + [2025] * 6,
                "agency_name": list("abcdef") * 2,
                "obligations": rng.uniform(1, 500, 12),
                "rate": rng.uniform(0, 1, 12),
            }
        )
        _, s = decomposition.shift_share(
            df, group_col="agency_name", weight_col="obligations", rate_col="rate"
        )
        assert abs(s["reconciliation_residual"]) < 1e-12

    def test_centred_mix_terms_sum_to_the_aggregate_mix_effect(self):
        df = pd.DataFrame(
            {
                "fiscal_year": [2024, 2024, 2025, 2025],
                "agency_name": ["a", "b", "a", "b"],
                "obligations": [50.0, 50.0, 90.0, 10.0],
                "rate": [0.3, 0.9, 0.35, 0.85],
            }
        )
        c, s = decomposition.shift_share(
            df, group_col="agency_name", weight_col="obligations", rate_col="rate"
        )
        assert c["mix_effect"].sum() == pytest.approx(s["mix_effect"])
        assert c["total_effect"].sum() == pytest.approx(s["total_change"])


# ----------------------------------------------------------- efficiency index
class TestEfficiencyIndex:
    @staticmethod
    def _raw():
        return pd.DataFrame(
            {
                "competition_raw": [0.9, 0.7, 0.5, 0.95, 0.6],
                "pricing_risk_raw": [0.8, 0.6, 0.4, 0.9, 0.7],
                "vendor_diversity_raw": [0.7, 0.8, 0.3, 0.85, 0.5],
                "spend_discipline_raw": [0.85, 0.75, 0.6, 0.9, 0.55],
                "stability_raw": [-2.0, -5.0, -12.0, -1.0, -8.0],
            },
            index=["A", "B", "C", "D", "E"],
        )

    def test_scores_land_between_zero_and_one_hundred(self):
        out = cei.score_index(self._raw(), {d: 0.2 for d in cei.DIMENSIONS})
        assert out["efficiency_index"].between(0, 100).all()

    def test_best_agency_on_every_dimension_ranks_first(self):
        out = cei.score_index(self._raw(), {d: 0.2 for d in cei.DIMENSIONS})
        assert out.iloc[0]["agency_name"] == "D"

    def test_a_missing_dimension_renormalises_rather_than_scoring_zero(self):
        raw = self._raw()
        raw.loc["A", "stability_raw"] = np.nan
        out = cei.score_index(raw, {d: 0.2 for d in cei.DIMENSIONS}).set_index("agency_name")
        assert out.loc["A", "dimensions_available"] == 4
        assert out.loc["A", "weight_coverage"] == pytest.approx(0.8)
        assert np.isfinite(out.loc["A", "efficiency_index"])

    def test_degenerate_dimension_scores_a_flat_fifty(self):
        raw = self._raw()
        raw["competition_raw"] = 0.5
        out = cei.score_index(raw, {d: 0.2 for d in cei.DIMENSIONS})
        assert out["competition_score"].eq(50.0).all()

    def test_sensitivity_is_deterministic_and_bounded(self):
        raw = self._raw()
        a = cei.weight_sensitivity(raw, n_draws=200, seed=1)
        b = cei.weight_sensitivity(raw, n_draws=200, seed=1)
        pd.testing.assert_frame_equal(a, b)
        assert a["rank_best"].min() >= 1
        assert a["rank_worst"].max() <= len(raw)

    def test_winsorize_clips_to_quantiles(self):
        s = pd.Series([0, 1, 2, 3, 100])
        out = cei.winsorize(s, 0.0, 0.75)
        assert out.max() == pytest.approx(3.0)


# ------------------------------------------------------------ standardisation
class TestStandardisation:
    @staticmethod
    def _frame():
        # Two agencies. "Hard" buys mostly hardware (1410, a low-competition
        # stratum); "Easy" buys mostly professional services (R425). Within each
        # stratum their rates are IDENTICAL - 20% on hardware, 90% on services -
        # so every point of the observed gap is portfolio, and the standardised
        # rates must come out equal.
        return pd.DataFrame(
            {
                "agency_name": ["Hard", "Hard", "Easy", "Easy"],
                "psc_code": ["1410", "R425", "1410", "R425"],
                "obligations": [900.0, 100.0, 100.0, 900.0],
                "competed_obligations": [180.0, 90.0, 20.0, 810.0],
            }
        )

    def test_psc_category_maps_letters_and_digits(self):
        assert stdz.psc_category("R425") == "Professional & management support"
        assert stdz.psc_category("1510") == "Products & equipment"
        assert stdz.psc_category("AC13") == "R&D"
        assert stdz.psc_category(None) == "Unclassified"

    def test_identical_within_category_rates_standardise_to_the_same_value(self):
        out = stdz.standardise_rate(
            stdz.prepare_strata(self._frame(), min_stratum_share=0.0)
        ).set_index("agency_name")
        # observed differs (portfolio), standardised does not (practice)
        assert out.loc["Hard", "observed_rate"] == pytest.approx(0.27)
        assert out.loc["Easy", "observed_rate"] == pytest.approx(0.83)
        assert out.loc["Hard", "standardised_rate"] == pytest.approx(
            out.loc["Easy", "standardised_rate"]
        )

    def test_portfolio_effect_is_observed_minus_standardised(self):
        out = stdz.standardise_rate(stdz.prepare_strata(self._frame(), min_stratum_share=0.0))
        assert out["portfolio_effect"].values == pytest.approx(
            (out["observed_rate"] - out["standardised_rate"]).values
        )

    def test_standardised_rate_never_exceeds_one(self):
        # Regression guard. The numerator and denominator come from separate API
        # queries, so a cell can report more competed dollars than total dollars.
        # Such a cell must be dropped, not propagated into a rate above 100%.
        df = pd.DataFrame(
            {
                "agency_name": ["X", "X"],
                "psc_code": ["1410", "R425"],
                "obligations": [100.0, 100.0],
                "competed_obligations": [400.0, 50.0],  # first stratum is impossible
            }
        )
        out = stdz.standardise_rate(stdz.prepare_strata(df, min_stratum_share=0.0))
        assert (out["standardised_rate"] <= 1.0).all()
        assert (out["observed_rate"] <= 1.0).all()
        assert out["strata_dropped_inconsistent"].iloc[0] == 1

    def test_thin_strata_fold_into_other(self):
        df = pd.DataFrame(
            {
                "agency_name": ["X"] * 3,
                "psc_code": ["1410", "R425", "U001"],
                "obligations": [1000.0, 1000.0, 1.0],
                "competed_obligations": [500.0, 500.0, 1.0],
            }
        )
        out = stdz.prepare_strata(df, min_stratum_share=0.01)
        assert "Other" in set(out["stratum"])

    def test_coverage_is_reported_when_an_agency_misses_categories(self):
        df = pd.DataFrame(
            {
                "agency_name": ["Full", "Full", "Narrow"],
                "psc_code": ["1410", "R425", "1410"],
                "obligations": [500.0, 500.0, 500.0],
                "competed_obligations": [250.0, 400.0, 250.0],
            }
        )
        out = stdz.standardise_rate(
            stdz.prepare_strata(df, min_stratum_share=0.0)
        ).set_index("agency_name")
        assert out.loc["Full", "reference_coverage"] == pytest.approx(1.0)
        assert out.loc["Narrow", "reference_coverage"] < 1.0
