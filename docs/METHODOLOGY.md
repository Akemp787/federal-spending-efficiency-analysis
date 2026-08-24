# Methodology

Every analytical judgement in this project is recorded in
[`config/pipeline.yml`](../config/pipeline.yml) rather than buried in code, so a reviewer can
see and change an assumption without reading the implementation. This document explains the
choices and why they were made.

---

## 1. Source and scope

**Source.** The USAspending v2 aggregation API (`api.usaspending.gov/api/v2`).

**Why the API rather than the bulk archive.** USAspending's Award Data Archive publishes
transaction-level contract files running to tens of gigabytes per fiscal year. That is the right
source for fields the API does not expose — number of offers received, modification history — and
[`src/fedspend/ingest/bulk_archive.py`](../src/fedspend/ingest/bulk_archive.py) covers that path.
It is the wrong primary source for a repository a reviewer should be able to clone and reproduce
in twenty minutes. Every metric here is built from cross-tabulations the API computes server-side.

**Scope.** Award type codes `A`, `B`, `C`, `D` — definitive contracts, purchase orders, delivery
orders, and BPA calls. IDV *vehicles* (`IDV_*`) are excluded because obligations are recorded on
the orders placed against them; counting both double-counts.

**Time basis.** `action_date`, so a transaction lands in the fiscal year it was obligated.
FY *y* runs 1 October *y−1* to 30 September *y*.

**Measure.** `federal_action_obligation`, summed server-side. Negative values are de-obligations
and are **retained**, so all figures are *net* obligations. This is why an agency can post a
negative fiscal year (HUD, FY2025) when terminations exceed new awards.

### Reproducibility

Every API response is cached to disk under a SHA-256 hash of its request body
(`data/raw/_api_cache/`). Re-running the pipeline is free, works offline, and makes published
numbers reproducible from the cached payloads. `data/curated/_manifest.json` records the snapshot
date, the exact filters used, and the call counts.

```bash
make all          # ingest → analyse → warehouse → validate → report
```

---

## 2. Inflation adjustment

**Series.** BEA GDP implicit price deflator (FRED `GDPDEF`, quarterly, index 2017 = 100),
retrieved from FRED's keyless CSV endpoint.

**Why the GDP deflator and not CPI-U.** The subject is government purchases of goods and
services, not household consumption. CPI-U measures a consumer basket that bears little
relationship to what federal agencies buy.

**Fiscal-year construction.** A fiscal-year deflator is the unweighted mean of the four calendar
quarters beginning October of the prior year — exactly the federal fiscal year, with no
interpolation.

| Fiscal year | Deflator | Multiplier to constant FY2025 $ |
|---|---:|---:|
| 2021 | 108.50 | 1.1790 |
| 2022 | 116.18 | 1.1011 |
| 2023 | 121.57 | 1.0523 |
| 2024 | 124.66 | 1.0262 |
| 2025 | 127.93 | 1.0000 |

Cumulative FY2021→FY2025 inflation is **17.9%**, which is why nominal and real growth differ by
18.7 percentage points.

---

## 3. Competition

An action counts as **competed** when its FPDS `extent_competed` code is:

| Code | Meaning |
|---|---|
| `A` | Full and open competition |
| `D` | Full and open after exclusion of sources |
| `F` | Competed under Simplified Acquisition Procedures |
| `CDO` | Competitive delivery order |

and **not competed** for `B`, `C`, `E`, `G`, `NDO`.

**The `E` decision.** Code `E` is "follow-on to competed action". The parent award was competed;
*this* action was not. Agencies differ on the convention, so this project follows the FPDS-NG
competition-rate treatment (E = not competed) and re-runs the entire index under the opposite
convention in the sensitivity analysis. The choice is a config value, not a constant.

**Denominator.** Only positive obligations enter. A net-negative bucket means de-obligations
exceeded new obligations in that category, which cannot be interpreted as a share of anything.

### Shift-share decomposition

A spending-weighted rate is `S = Σᵢ wᵢ·sᵢ` over agencies. Its change decomposes exactly:

```
ΔS = Σᵢ wᵢ⁰·Δsᵢ        within effect  — agencies changed their own behaviour
   + Σᵢ Δwᵢ·(sᵢ⁰ − S⁰)  mix effect     — dollars moved between agencies
   + Σᵢ Δwᵢ·Δsᵢ         interaction
```

The three terms sum to the observed change with **no residual** (validated to < 1e-9), which is
what makes the attribution a result rather than an assertion.

**Why the mix term is centred on `S⁰`.** Weights sum to one in both periods, so `Σ Δwᵢ = 0` and
therefore `Σ Δwᵢ·sᵢ⁰ = Σ Δwᵢ·(sᵢ⁰ − S⁰)` — centring leaves the total identical while making each
agency's contribution readable. Uncentred, a growing agency always shows a positive mix term
regardless of whether it competes more or less than average, which inverts the sign of the thing
the reader is trying to understand.

---

## 4. Contract-type risk

Ordered by who bears cost-overrun risk, following FAR:

| Bucket | FPDS codes | Government risk |
|---|---|---|
| Fixed price | A, B, J, K, L, M | low — contractor absorbs overruns |
| Cost reimbursement | R, S, T, U, V | **high** — government pays allowable costs |
| Labor hour / T&M | Y, Z | **high** — FAR 16.601(c) least preferred |
| Other | 1, 2, 3 | undetermined |

`government_risk_share` = (cost-reimbursement + labor-hour) ÷ classified obligations.

**This is not a verdict.** FAR 16.301-2 permits cost-reimbursement where cost uncertainty
prevents a fixed price, and research and complex services legitimately require it. A defence
research agency *should* look different from a supply agency. The measure sizes the population
carrying government cost risk and, more usefully, shows whether that population is growing.

---

## 5. Concentration

Standard antitrust measures applied to the buyer side of the federal market.

- **HHI** — sum of squared percentage shares, 0–10,000. DOJ/FTC thresholds: <1,500
  unconcentrated, 1,500–2,500 moderately, >2,500 highly concentrated.
- **Normalised HHI** — `(H − 1/n)/(1 − 1/n)`, removing the mechanical effect of participant count
  so a 12-vendor market and a 900-vendor market compare on equal terms. This is the form the
  efficiency index consumes.
- **CR-n** and **Gini** for distributional context.

**Truncation is handled explicitly.** Vendor extracts hold each agency's top 100 recipients.
Shares are computed against the agency's *true* total obligations, never against the sum of the
truncated list, so the HHI is a strict lower bound — the omitted tail is excluded rather than
misattributed. `coverage_share` is reported alongside every HHI so the reader can see how much of
the market the measure observed. Negative values are excluded: a negative market share is not a
share.

---

## 6. Obligation timing

- `september_share` — September ÷ fiscal-year obligations (even pace = 8.3%)
- `q4_share` — July–September ÷ fiscal-year obligations
- `surge_ratio` — September ÷ mean monthly obligations in October–August (1.0 = an ordinary month)
- `september_excess_obligations` — dollars above what a level 1/12 pace would have placed

September concentration is treated as a **risk indicator**, not a finding. The behavioural
mechanism — annual appropriations expiring on 30 September — is well documented, as is the
associated pattern that year-end awards are more likely to be non-competed and less likely to be
firm-fixed-price. That makes the population worth sampling; it does not make any individual award
improper.

---

## 7. Outlier detection

Federal spending distributions are heavily right-skewed and contain the outliers being searched
for. A classical z-score is self-defeating here: the outlier inflates the standard deviation
meant to detect it (*masking*). In the project's own test case, a value 100× the others scores a
classical z of 2.6 — below any threshold — while the robust score exceeds 500.

Every detector is therefore built on the **median and median absolute deviation**, which have a
50% breakdown point. The MAD is scaled by 1.4826 so that under normality it estimates the same
quantity as the standard deviation, keeping the familiar "3σ" reading meaningful. Where the MAD
is zero (more than half the observations share a value) the code falls back to a scaled mean
absolute deviation rather than dividing by zero.

Comparisons are scoped **within fiscal year**, so a government-wide shift does not flag everyone
at once.

---

## 8. The Contract Efficiency Index

Five dimensions, each normalised so that higher = more efficient:

| Dimension | Raw measure | Weight |
|---|---|---:|
| competition | competed share | 0.30 |
| pricing_risk | 1 − government-risk share | 0.25 |
| vendor_diversity | 1 − normalised vendor HHI | 0.20 |
| spend_discipline | 1 − September share | 0.15 |
| stability | 1 − real YoY growth volatility | 0.10 |

**Construction.** Each raw dimension is winsorised at the 5th/95th percentiles (so one extreme
agency cannot compress the scale), min-max scaled to 0–100, then weighted. Weights are
renormalised over the dimensions an agency actually has, so a missing dimension reduces
confidence rather than silently scoring zero.

**Population.** Agencies with ≥ $1B in FY2025 obligations (19 of 69). Ranking a percentage
computed on a $111M base against one computed on a $492B base is not a comparison, and an agency
with negative net obligations has no denominator at all.

### Composite indices have three known problems. All three are handled.

| Problem | Mitigation |
|---|---|
| Weights are arbitrary | Published in config; every agency re-scored under **2,000 random weightings** drawn from a flat Dirichlet (the uniform distribution on the simplex) |
| Normalisation is scale-dependent | Winsorisation before min-max scaling |
| Aggregation hides the driver | Component sub-scores returned alongside every composite |

**The sensitivity result is reported honestly.** Only 3 of 19 agencies hold the same quartile
across the weighting distribution. The middle of the ranking is **not separable**, and the
documentation says so rather than presenting 19 ranks as equally meaningful. The index is a
triage device for allocating review effort.

The index is additionally re-scored under four named alternative weightings (configured, equal,
competition-only, risk-weighted) with the rank spread reported per agency.

---

## 9. Validation

Ten contracts run on every build; ERROR-severity failures fail CI.

The most important is **cross-tab reconciliation**. The competition table is assembled from nine
separate API calls per agency-year, one per FPDS code; the pricing table from sixteen. If those
slices do not sum back to the independently retrieved agency total, the extraction is wrong and
every downstream figure is suspect.

| Check | Result |
|---|---|
| Fiscal year coverage | PASS |
| Unique (fiscal_year, agency) key | PASS |
| Competition slices reconcile to totals | PASS — 325/325 agency-years within 1% |
| Pricing slices reconcile to totals | PASS — 325/325 agency-years within 1% |
| Monthly slices reconcile to annual | PASS — 5/5 fiscal years |
| Shares within [0, 1] | PASS |
| Deflator monotonic | PASS |
| Shift-share reconciles exactly | PASS — max residual 3.4e-16 |
| Index population above floor | PASS |
| Net-negative obligations | WARN — 4 agency-years flagged for interpretation |

The 1% tolerance absorbs transactions USAspending assigns a null code, which no code-filtered
query returns.

Full report: `outputs/tables/validation_report.csv`.

---

## 10. Architecture

```
config/pipeline.yml         every analytical assumption, in one reviewable file
src/fedspend/
  ingest/                   cached, retrying API client + extract orchestration
  transform/                deflator and normalisation
  metrics/                  concentration · competition · pricing_risk · timing
                            growth · anomaly · decomposition · efficiency_index
  warehouse/                DuckDB build + SQL view installation
  validate/                 data-quality contracts
  report/                   SVG charts, dashboard, BI exports
  analysis.py               orchestration: extracts → curated tables
  cli.py                    fedspend <stage>
sql/                        analytic views (independent expression of the metrics)
tests/                      63 known-answer tests, no network
```

Data flows one way: `data/raw` (cache) → `data/interim` (tidy extracts) →
`data/curated` (analytical tables + DuckDB) → `outputs` (dashboard, CSV exports).
Each stage reads the previous stage from disk, so any stage can be re-run alone.
