-- ===========================================================================
-- 03_attribution_views.sql
-- Sub-agency attribution and the portfolio-adjusted competition rate.
-- ===========================================================================

-- Sub-agency competition, latest year, with the prior year on the same row.
CREATE OR REPLACE VIEW v_subagency_competition AS
WITH latest AS (
    SELECT max(fiscal_year) AS fy FROM subagency_competition
),
paired AS (
    SELECT
        c.agency_name,
        c.subagency_name,
        c.obligations,
        c.not_competed_obligations,
        c.competed_share                          AS competed_latest,
        p.competed_share                          AS competed_prior
    FROM subagency_competition c
    LEFT JOIN subagency_competition p
           ON p.subagency_name = c.subagency_name
          AND p.fiscal_year    = (SELECT fy FROM latest) - 1
    WHERE c.fiscal_year = (SELECT fy FROM latest)
)
SELECT
    agency_name,
    subagency_name,
    ROUND(obligations / 1e9, 2)                   AS obligations_bn,
    ROUND(competed_prior  * 100, 1)               AS competed_pct_prior,
    ROUND(competed_latest * 100, 1)               AS competed_pct_latest,
    ROUND((competed_latest - competed_prior) * 100, 2)
                                                  AS change_pp,
    ROUND(not_competed_obligations / 1e9, 2)      AS bn_not_competed,
    -- Dollars that would have been competed at the prior-year rate.
    ROUND(GREATEST(competed_prior - competed_latest, 0) * obligations / 1e9, 2)
                                                  AS bn_vs_prior_rate
FROM paired
WHERE obligations > 1e9
ORDER BY change_pp ASC;

-- Which component moved its parent department, and by how much.
CREATE OR REPLACE VIEW v_subagency_attribution AS
SELECT
    agency_name,
    subagency_name,
    ROUND(w_1 * 100, 1)                    AS weight_pct_of_department,
    ROUND(s_0 * 100, 1)                    AS competed_pct_prior,
    ROUND(s_1 * 100, 1)                    AS competed_pct_latest,
    ROUND(within_effect * 100, 3)          AS within_effect_pp,
    ROUND(mix_effect * 100, 3)             AS mix_effect_pp,
    ROUND(total_effect * 100, 3)           AS total_effect_pp,
    ROUND(agency_total_change * 100, 3)    AS department_change_pp,
    ROUND(total_effect / NULLIF(agency_total_change, 0) * 100, 1)
                                           AS pct_of_department_change
FROM subagency_decomposition
ORDER BY abs(total_effect) DESC;

-- Observed vs portfolio-adjusted competition: practice separated from mission.
CREATE OR REPLACE VIEW v_portfolio_adjusted AS
SELECT
    agency_name,
    ROUND(obligations / 1e9, 2)             AS obligations_bn,
    ROUND(observed_rate * 100, 1)           AS observed_pct,
    ROUND(standardised_rate * 100, 1)       AS portfolio_adjusted_pct,
    ROUND(portfolio_effect * 100, 1)        AS portfolio_effect_pp,
    ROUND(reference_coverage, 3)            AS reference_coverage,
    strata_observed,
    strata_dropped_inconsistent,
    CASE
        WHEN reference_coverage < 0.80 THEN 'thin coverage - do not rank'
        WHEN portfolio_effect > 0.05  THEN 'observed rate flattered by portfolio'
        WHEN portfolio_effect < -0.05 THEN 'observed rate depressed by portfolio'
        ELSE 'portfolio broadly neutral'
    END                                     AS reading
FROM portfolio_adjusted_competition
ORDER BY standardised_rate DESC;

-- Within-category detail: where an agency's gap to the government actually sits.
CREATE OR REPLACE VIEW v_portfolio_stratum_gaps AS
SELECT
    agency_name,
    stratum,
    ROUND(obligations / 1e9, 3)             AS obligations_bn,
    ROUND(own_weight * 100, 1)              AS pct_of_agency_spend,
    ROUND(reference_weight * 100, 1)        AS pct_of_government_spend,
    ROUND(rate * 100, 1)                    AS competed_pct,
    ROUND(government_rate * 100, 1)         AS government_competed_pct,
    ROUND(rate_vs_government_pp, 1)         AS gap_pp,
    -- Dollars attributable to the agency trailing the government in this category.
    ROUND(LEAST(rate_vs_government_pp, 0) / 100 * obligations / 1e9, 3)
                                            AS bn_behind_government
FROM portfolio_stratum_detail
WHERE obligations > 1e8
ORDER BY agency_name, obligations DESC;
