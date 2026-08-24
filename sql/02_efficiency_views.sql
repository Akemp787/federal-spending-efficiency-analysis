-- ===========================================================================
-- 02_efficiency_views.sql
-- Competition, contract-type risk, year-end timing, and the review shortlist.
-- ===========================================================================

-- Competition rate by agency across the window, wide by fiscal year, with the
-- latest-year move called out. This is the table the competition finding rests on.
CREATE OR REPLACE VIEW v_competition_by_agency AS
WITH pivoted AS (
    SELECT
        agency_name,
        MAX(CASE WHEN fiscal_year = 2021 THEN competed_share END) AS fy2021,
        MAX(CASE WHEN fiscal_year = 2022 THEN competed_share END) AS fy2022,
        MAX(CASE WHEN fiscal_year = 2023 THEN competed_share END) AS fy2023,
        MAX(CASE WHEN fiscal_year = 2024 THEN competed_share END) AS fy2024,
        MAX(CASE WHEN fiscal_year = 2025 THEN competed_share END) AS fy2025,
        MAX(CASE WHEN fiscal_year = 2025 THEN obligations END)    AS obligations_fy2025
    FROM fact_agency_year
    WHERE is_material
    GROUP BY agency_name
)
SELECT
    agency_name,
    ROUND(obligations_fy2025 / 1e9, 2)         AS obligations_bn_fy2025,
    ROUND(fy2021 * 100, 1)                     AS competed_pct_fy2021,
    ROUND(fy2022 * 100, 1)                     AS competed_pct_fy2022,
    ROUND(fy2023 * 100, 1)                     AS competed_pct_fy2023,
    ROUND(fy2024 * 100, 1)                     AS competed_pct_fy2024,
    ROUND(fy2025 * 100, 1)                     AS competed_pct_fy2025,
    ROUND((fy2025 - fy2024) * 100, 2)          AS change_pp_fy2024_fy2025,
    ROUND((fy2025 - fy2021) * 100, 2)          AS change_pp_fy2021_fy2025,
    -- Dollars that would have been competed had the agency held its FY2024 rate.
    ROUND(GREATEST(fy2024 - fy2025, 0) * obligations_fy2025 / 1e9, 2)
                                               AS bn_not_competed_vs_prior_rate
FROM pivoted
WHERE obligations_fy2025 > 0
ORDER BY change_pp_fy2024_fy2025 ASC;

-- Shift-share attribution: how much of the government-wide competition move
-- each agency caused, split into behaviour (within) and budget mix (mix).
CREATE OR REPLACE VIEW v_competition_attribution AS
SELECT
    agency_name,
    ROUND(w_0 * 100, 2)                  AS weight_pct_prior,
    ROUND(w_1 * 100, 2)                  AS weight_pct_latest,
    ROUND(s_0 * 100, 1)                  AS competed_pct_prior,
    ROUND(s_1 * 100, 1)                  AS competed_pct_latest,
    ROUND(within_effect * 100, 3)        AS within_effect_pp,
    ROUND(mix_effect * 100, 3)           AS mix_effect_pp,
    ROUND(interaction_effect * 100, 3)   AS interaction_effect_pp,
    ROUND(total_effect * 100, 3)         AS total_effect_pp
FROM competition_decomposition
ORDER BY abs(total_effect) DESC;

-- Contract-type risk migration between the first and last year of the window.
CREATE OR REPLACE VIEW v_risk_migration AS
SELECT
    agency_name,
    ROUND(government_risk_share_base   * 100, 1) AS government_risk_pct_base,
    ROUND(government_risk_share_latest * 100, 1) AS government_risk_pct_latest,
    ROUND(change_pp, 2)                          AS change_pp,
    ROUND(dollars_shifted_to_government_risk / 1e9, 2)
                                                 AS bn_shifted_to_government_risk,
    ROUND(classified_obligations_latest / 1e9, 2) AS obligations_bn_latest
FROM risk_migration
ORDER BY change_pp DESC;

-- Year-end concentration, agency by agency, latest year.
CREATE OR REPLACE VIEW v_year_end_surge AS
SELECT
    fiscal_year,
    agency_name,
    ROUND(obligations / 1e9, 2)                      AS obligations_bn,
    ROUND(september_share * 100, 1)                  AS september_pct,
    ROUND(q4_share * 100, 1)                         AS q4_pct,
    ROUND(surge_ratio, 2)                            AS surge_ratio,
    ROUND(september_excess_obligations / 1e9, 2)     AS bn_above_even_pace,
    CASE
        WHEN september_share >= 0.30 THEN 'severe'
        WHEN september_share >= 0.20 THEN 'elevated'
        WHEN september_share >= 0.12 THEN 'typical'
        ELSE 'low'
    END                                              AS surge_band
FROM fact_agency_year
WHERE is_material AND obligations > 0
ORDER BY fiscal_year DESC, september_share DESC;

-- The review shortlist: scale on one axis, non-competed exposure on the other.
CREATE OR REPLACE VIEW v_review_shortlist AS
SELECT
    agency_name,
    quadrant,
    is_priority,
    ROUND(obligations / 1e9, 2)                   AS obligations_bn,
    ROUND(competed_share * 100, 1)                AS competed_pct,
    ROUND(not_competed_obligations / 1e9, 2)      AS bn_not_competed,
    ROUND(government_risk_obligations / 1e9, 2)   AS bn_government_risk_priced,
    ROUND(september_excess_obligations / 1e9, 2)  AS bn_september_above_pace,
    ROUND(efficiency_index, 1)                    AS efficiency_index,
    rank                                          AS efficiency_rank,
    quartile
FROM review_shortlist
ORDER BY is_priority DESC, bn_not_competed DESC;

-- Efficiency index joined to its sensitivity result, so no rank is ever read
-- without the evidence on whether that rank survives a different weighting.
CREATE OR REPLACE VIEW v_efficiency_index_with_confidence AS
SELECT
    e.rank,
    e.agency_name,
    ROUND(e.efficiency_index, 1)          AS efficiency_index,
    ROUND(e.obligations / 1e9, 2)         AS obligations_bn,
    ROUND(e.competition_score, 1)         AS competition_score,
    ROUND(e.pricing_risk_score, 1)        AS pricing_risk_score,
    ROUND(e.vendor_diversity_score, 1)    AS vendor_diversity_score,
    ROUND(e.spend_discipline_score, 1)    AS spend_discipline_score,
    ROUND(e.stability_score, 1)           AS stability_score,
    s.rank_median,
    s.rank_best,
    s.rank_worst,
    s.rank_iqr,
    ROUND(s.quartile_confidence_pct, 1)   AS quartile_confidence_pct,
    s.quartile_verdict
FROM efficiency_index e
LEFT JOIN index_sensitivity s USING (agency_name)
ORDER BY e.rank;
