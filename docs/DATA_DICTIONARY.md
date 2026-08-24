# Data Dictionary

Curated tables in `data/curated/` (parquet) and `outputs/tables/` (CSV, BI-ready).
All monetary values are **US dollars**, unsuffixed columns are **nominal**, and columns ending
`_real` are **constant FY2025 dollars**. Shares are proportions in `[0, 1]`; anything expressed
in percentage points is named `_pp` or `_pct`.

---

## Data flow

```
data/raw/_api_cache/     content-addressed API responses (reproducibility)
data/raw/                gdpdef_quarterly.csv — deflator source series
        ↓
data/interim/            tidy long extracts, one per API cross-tab
        ↓
data/curated/            analytical tables + fedspend.duckdb  ← documented below
        ↓
outputs/                 dashboard.html, tables/*.csv
```

---

## `fact_agency_year` — the central fact table
**Grain:** one row per (fiscal_year, agency_name) · 345 rows

### Keys and identity
| Column | Type | Description |
|---|---|---|
| `fiscal_year` | int | Federal fiscal year (1 Oct *y−1* – 30 Sep *y*) |
| `agency_id` | int | USAspending internal toptier agency id |
| `agency_code` | str | Agency abbreviation (`DOD`, `VA`, …) |
| `agency_name` | str | Toptier awarding agency name — the join key across all tables |
| `agency_slug` | str | USAspending URL slug |

### Scale
| Column | Type | Description |
|---|---|---|
| `obligations` | float | Net `federal_action_obligation`. **Can be negative** when de-obligations exceed new awards |
| `real_multiplier` | float | Factor converting this year's dollars to constant FY2025 dollars |
| `obligations_real` | float | `obligations × real_multiplier` |

### Competition
| Column | Type | Description |
|---|---|---|
| `competed_obligations` | float | Obligations under FPDS codes A, D, F, CDO (positive values only) |
| `not_competed_obligations` | float | Obligations under B, C, E, G, NDO |
| `competed_share` | float | `competed ÷ (competed + not competed)`. Null where the denominator is non-positive |

### Contract-type risk
| Column | Type | Description |
|---|---|---|
| `fixed_price_share` | float | Share in FPDS pricing codes A, B, J, K, L, M |
| `cost_reimbursement_share` | float | Share in R, S, T, U, V |
| `labor_hour_share` | float | Share in Y, Z (time-and-materials, labor hours) |
| `government_risk_share` | float | `cost_reimbursement_share + labor_hour_share` — dollars where the government absorbs overruns |
| `government_risk_obligations` | float | The same population in dollars |

### Small business
| Column | Type | Description |
|---|---|---|
| `setaside_obligations` | float | Obligations under a small-business set-aside code |
| `setaside_share` | float | As a share of agency obligations. **Narrower than total small-business dollars** — a small firm can win full and open |

### Obligation timing
| Column | Type | Description |
|---|---|---|
| `september_obligations` | float | Obligations in the final month of the fiscal year |
| `september_share` | float | September ÷ annual. Even pace = 0.0833 |
| `q4_share` | float | July–September ÷ annual |
| `surge_ratio` | float | September ÷ mean monthly obligations Oct–Aug. **1.0 = an ordinary month** |
| `september_excess_obligations` | float | Dollars above a level 1/12 pace; floored at zero |

### Vendor concentration
| Column | Type | Description |
|---|---|---|
| `vendor_hhi` | float | HHI over the agency's top 100 recipients, 0–10,000. **Lower bound** (see `vendor_coverage_share`) |
| `hhi_normalized` | float | `(H − 1/n)/(1 − 1/n)`, 0–1 — removes participant-count effects. This is what the index consumes |
| `vendor_hhi_class` | str | `unconcentrated` / `moderately concentrated` / `highly concentrated` (DOJ thresholds) |
| `vendor_gini` | float | Gini of the vendor distribution |
| `vendor_cr1`, `_cr4`, `_cr10` | float | Share held by the largest 1 / 4 / 10 recipients |
| `vendor_coverage_share` | float | Observed top-100 obligations ÷ true agency total. **Read every HHI against this** |
| `vendors_observed` | float | Count of recipients with positive obligations in the extract |

### Growth and outlier flags
| Column | Type | Description |
|---|---|---|
| `prior_year`, `change_abs`, `change_pct` | float | Nominal YoY. `change_pct` is **null when the prior year was ≤ 0** |
| `prior_year_real`, `change_abs_real`, `change_pct_real` | float | The same in constant dollars |
| `real_growth_robust_z` | float | MAD-based z-score of real growth, computed **within fiscal year** |
| `real_growth_iqr_lower` / `_upper` | float | Tukey fences (k = 1.5) within fiscal year |
| `real_growth_is_high_outlier` / `_is_low_outlier` / `_is_outlier` | bool | Flags at \|z\| ≥ 3.0 |
| `is_material` | bool | Peak obligations across the window ≥ $1B. Uses **peak, not latest**, so agencies that collapsed stay in trend analysis |

---

## `gov_summary` — government-wide series
**Grain:** one row per fiscal_year · 5 rows

Carries the same competition, pricing, timing and set-aside measures aggregated across all
agencies, plus:

| Column | Type | Description |
|---|---|---|
| `agency_hhi`, `agency_cr1/4/10`, `agency_gini` | float | Concentration of obligations **across agencies** — how few departments hold the money |
| `vendor_hhi_top100`, `vendor_cr10` | float | Government-wide vendor concentration over the top 100 recipients |
| `vendor_coverage_share` | float | Share of government obligations the top-100 vendor list observes |
| `obligations_yoy_pct`, `obligations_real_yoy_pct` | float | Year-over-year change, nominal and real |
| `obligations_index_vs_base`, `obligations_real_index_vs_base` | float | Indexed to FY2021 = 100 |

---

## `efficiency_index` — Contract Efficiency Index
**Grain:** one row per scored agency (FY2025, ≥ $1B) · 19 rows

| Column | Type | Description |
|---|---|---|
| `<dim>_raw` | float | Raw dimension value before winsorising, oriented so **higher = more efficient** |
| `<dim>_score` | float | Winsorised (5th/95th) and min-max scaled to 0–100 |
| `efficiency_index` | float | Weighted mean of available sub-scores, 0–100 |
| `dimensions_available` | int | How many of the five dimensions the agency had (max 5) |
| `weight_coverage` | float | Share of total weight the available dimensions carry — a confidence measure |
| `rank` | float | 1 = highest score. **Read with `index_sensitivity` before citing** |
| `quartile` | cat | `Q1 (highest)` … `Q4 (lowest)` |

Dimensions: `competition`, `pricing_risk`, `vendor_diversity`, `spend_discipline`, `stability`.

---

## `index_sensitivity` — robustness of every rank
**Grain:** one row per scored agency · 19 rows

Produced by re-scoring under 2,000 weightings drawn from a flat Dirichlet.

| Column | Type | Description |
|---|---|---|
| `score_mean`, `score_p05`, `score_p95` | float | Score distribution across the draws |
| `rank_median`, `rank_best`, `rank_worst` | float | Rank distribution |
| `rank_iqr` | float | Interquartile range of rank — **the headline instability measure** |
| `pct_draws_in_bottom_quartile` / `_top_quartile` | float | Share of draws landing in each tail |
| `rank_is_stable` | bool | `rank_iqr ≤ max(2, 20% of field)` |
| `quartile_confidence_pct` | float | Max of the two tail percentages |
| `quartile_verdict` | str | `robustly bottom quartile` / `robustly top quartile` / **`not separable`** |

> Only 3 of 19 agencies are separable. Treat `not separable` as meaning the rank carries no
> information.

---

## `competition_decomposition` — shift-share attribution
**Grain:** one row per agency for the FY2024→FY2025 change · 69 rows

| Column | Type | Description |
|---|---|---|
| `w_0`, `w_1` | float | Agency share of total obligations, base and latest period |
| `s_0`, `s_1` | float | Agency competed share, base and latest period |
| `dw`, `ds` | float | Changes in weight and rate |
| `within_effect` | float | `w_0 × ds` — the agency changed its own behaviour |
| `mix_effect` | float | `dw × (s_0 − S_0)` — **centred** on the base-period overall rate |
| `mix_effect_uncentred` | float | `dw × s_0`, retained for reference; sums to the same total |
| `interaction_effect` | float | `dw × ds` |
| `total_effect` | float | Sum of the three. **Column sums reconcile to the observed change with no residual** |

Companion tables `competition_decomposition_series` and `risk_decomposition_series` carry the
same decomposition for every consecutive year pair, with a `reconciliation_residual` column that
validation asserts is < 1e-9.

---

## `review_shortlist` — prioritisation output
**Grain:** one row per material agency · 21 rows

| Column | Type | Description |
|---|---|---|
| `quadrant` | str | 2×2 on scale × non-competed exposure, cut at **medians of the reviewed population** |
| `is_priority` | bool | High spend **and** high non-competed exposure |
| `exposure_upper_bound` | float | Max of the three exposure measures. **Named as an upper bound because the components overlap** — do not sum them |
| `obligations_median_cut`, `not_competed_obligations_median_cut` | float | The cut values used, so the quadrants are auditable |

---

## `agency_trend` — whole-window summary
**Grain:** one row per material agency · 21 rows

| Column | Type | Description |
|---|---|---|
| `cagr_nominal_pct`, `cagr_real_pct` | float | Compound annual growth over the window |
| `change_real_abs`, `change_real_pct` | float | First-to-last change in constant dollars |
| `yoy_real_volatility_pp` | float | Standard deviation of real YoY growth — feeds the index `stability` dimension |
| `yoy_real_max_swing_pp` | float | Largest single-year absolute move |
| `log_trend_pct_per_year` | float | Slope of a least-squares fit on log real obligations — robust to one anomalous end year |

---

## `monthly_seasonality`
**Grain:** one row per (fiscal_year, fiscal_month) · 60 rows

| Column | Type | Description |
|---|---|---|
| `fiscal_month` | int | **1 = October**, 12 = September |
| `share` | float | Month's share of the fiscal-year total |
| `index_vs_even_pace` | float | `share × 12 × 100`. **100 = an even monthly pace** |

---

## `vendor_concentration` and `risk_migration`

`vendor_concentration` (105 rows) carries the full concentration profile per (fiscal_year,
agency_name), including `participants_observed`, `market_total`, `coverage_share`, `hhi`,
`hhi_normalized`, `hhi_class`, `gini`, and `cr1`/`cr4`/`cr10`/`cr20`.

`risk_migration` (21 rows) compares each agency's `government_risk_share` between the first and
last fiscal year. `dollars_shifted_to_government_risk` applies the percentage-point change to
latest-year obligations, isolating the change in **contract type** from the change in volume.

---

## Reference tables

| Table | Grain | Notes |
|---|---|---|
| `top_vendors` | fiscal_year × rank | Government-wide top 50 recipients with UEI |
| `category_naics` / `category_psc` | fiscal_year × rank | Top 100 industry / product-service codes |
| `category_state` | fiscal_year × rank | Place-of-performance state totals |
| `contribution_to_change` | agency | Each agency's contribution to the FY2021→FY2025 real change; `share_of_total_change` sums to 1 |
| `noncompeted_exposure` | fiscal_year × agency | `dollars_below_benchmark` = dollars needed to reach that year's government-wide competed rate |

---

## BI exports

`outputs/tables/` mirrors the curated tables in star-schema shape for Power BI, Tableau or Excel:
`fact_agency_year`, `fact_government_year`, `fact_month`, `fact_efficiency_index`,
`fact_review_shortlist`, `fact_competition_attribution`, `fact_vendor_concentration`,
`fact_risk_migration`, with conformed dimensions `dim_agency`, `dim_agency_trend`,
`dim_index_sensitivity`, `dim_top_vendors`, `dim_naics`, `dim_psc`, `dim_state`.

Join on `agency_name`; `dim_agency` is the conformed agency dimension.
