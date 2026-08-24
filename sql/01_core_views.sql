-- ===========================================================================
-- 01_core_views.sql
-- Government-wide and agency-level views over the curated fact table.
-- Installed into data/curated/fedspend.duckdb by `fedspend warehouse`.
-- ===========================================================================

-- Headline government-wide series, nominal and constant FY2025 dollars.
CREATE OR REPLACE VIEW v_gov_headline AS
SELECT
    fiscal_year,
    ROUND(obligations       / 1e9, 1)          AS obligations_bn_nominal,
    ROUND(obligations_real  / 1e9, 1)          AS obligations_bn_real_fy2025,
    ROUND(obligations_yoy_pct, 2)              AS yoy_nominal_pct,
    ROUND(obligations_real_yoy_pct, 2)         AS yoy_real_pct,
    ROUND(obligations_index_vs_base, 1)        AS index_nominal_fy2021_100,
    ROUND(obligations_real_index_vs_base, 1)   AS index_real_fy2021_100,
    ROUND(competed_share * 100, 2)             AS competed_pct,
    ROUND(government_risk_share * 100, 2)      AS government_risk_pct,
    ROUND(september_share * 100, 2)            AS september_pct,
    ROUND(q4_share * 100, 2)                   AS q4_pct,
    ROUND(agency_hhi, 0)                       AS agency_hhi,
    ROUND(agency_cr4 * 100, 1)                 AS agency_cr4_pct
FROM gov_summary
ORDER BY fiscal_year;

-- The gap between nominal and real growth, stated as the share of headline
-- growth that is purely the price level.
CREATE OR REPLACE VIEW v_inflation_effect AS
WITH bounds AS (
    SELECT
        min(fiscal_year)                                              AS base_fy,
        max(fiscal_year)                                              AS latest_fy,
        arg_min(obligations, fiscal_year)                             AS nominal_base,
        arg_max(obligations, fiscal_year)                             AS nominal_latest,
        arg_min(obligations_real, fiscal_year)                        AS real_base,
        arg_max(obligations_real, fiscal_year)                        AS real_latest
    FROM gov_summary
)
SELECT
    base_fy,
    latest_fy,
    ROUND((nominal_latest / nominal_base - 1) * 100, 2) AS nominal_growth_pct,
    ROUND((real_latest    / real_base    - 1) * 100, 2) AS real_growth_pct,
    ROUND(((nominal_latest / nominal_base) - (real_latest / real_base)) * 100, 2)
                                                        AS inflation_wedge_pp,
    ROUND((nominal_latest - real_latest / (real_base / nominal_base)) / 1e9, 1)
                                                        AS nominal_only_growth_bn
FROM bounds;

-- Agency-year panel with each agency's rank and share of the market that year.
CREATE OR REPLACE VIEW v_agency_panel AS
SELECT
    fiscal_year,
    agency_name,
    obligations,
    obligations_real,
    ROUND(obligations / SUM(obligations) OVER (PARTITION BY fiscal_year) * 100, 2)
        AS pct_of_government,
    RANK() OVER (PARTITION BY fiscal_year ORDER BY obligations DESC) AS spend_rank,
    ROUND(competed_share * 100, 2)        AS competed_pct,
    ROUND(government_risk_share * 100, 2) AS government_risk_pct,
    ROUND(september_share * 100, 2)       AS september_pct,
    ROUND(setaside_share * 100, 2)        AS setaside_pct,
    ROUND(vendor_hhi, 0)                  AS vendor_hhi,
    vendor_hhi_class,
    ROUND(change_pct_real, 2)             AS real_growth_pct,
    is_material
FROM fact_agency_year
ORDER BY fiscal_year, obligations DESC;

-- Year-over-year movement for the material agencies, with the prior year on the
-- same row so a reader never has to self-join to see the comparison.
CREATE OR REPLACE VIEW v_agency_yoy AS
SELECT
    fiscal_year,
    agency_name,
    ROUND(prior_year / 1e9, 2)                    AS prior_year_bn,
    ROUND(obligations / 1e9, 2)                   AS obligations_bn,
    ROUND(change_abs / 1e9, 2)                    AS change_bn,
    ROUND(change_pct, 2)                          AS change_pct_nominal,
    ROUND(change_pct_real, 2)                     AS change_pct_real,
    ROUND(real_growth_robust_z, 2)                AS real_growth_robust_z,
    real_growth_is_outlier
FROM fact_agency_year
WHERE is_material AND prior_year IS NOT NULL
ORDER BY fiscal_year DESC, change_abs ASC;
