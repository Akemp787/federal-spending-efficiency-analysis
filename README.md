# Federal Contract Spending Efficiency Analysis

**FY2021–FY2025 · $3.58 trillion in federal contract obligations · 69 agencies**

An end-to-end analytics project that takes US federal contract data from a public API through a
reproducible pipeline, a DuckDB warehouse, a validated metrics layer, and a composite index — to
a set of findings about where the government's contracting dollars are least exposed to a market
test, and where oversight effort would be best spent.

[**Executive summary**](docs/EXECUTIVE_SUMMARY.md) ·
[Methodology](docs/METHODOLOGY.md) ·
[Data dictionary](docs/DATA_DICTIONARY.md) ·
[**Recommendations**](docs/RECOMMENDATIONS.md) ·
[Limitations](docs/LIMITATIONS.md) ·
[Interactive dashboard](outputs/dashboard.html)

---

## Headline findings

**1 · Four-fifths of the headline growth is the price level.**
Nominal contract obligations rose 22.9% from FY2021 to FY2025 ($633.2B → $778.4B). In constant
FY2025 dollars the increase is **4.3%** — roughly **$118B** of the $145B nominal rise is the GDP
deflator, not additional goods and services.

**2 · Competition fell to a five-year low, and 93% of the drop is one department.**
The competed share of obligations fell from 70.3% to **66.3%** in FY2025. A shift-share
decomposition separates behaviour from budget composition and reconciles exactly (residual
< 1e-15): the decline is **−3.06 pp within-agency** versus −0.76 pp mix. The Department of
Defense alone contributes **−3.67 of the −3.97 pp**, its own competed share falling from
**58.0% to 52.7%** while its share of federal contract dollars grew. Had DoD merely held its
FY2024 rate, **$25.9B more** would have been competed.

**3 · One component drives it: the Navy.**
Running the same decomposition a level down localises the Defense move to the **Department of
the Navy**, which contributed −3.98 pp of Defense's −5.25 pp. Navy's competed share fell from
**45.8% to 36.6%** on $176.6B — while the Air Force moved the *other way*. Chaining the two
decompositions, **Navy alone accounts for roughly 70% of the entire government-wide decline**,
worth **$16.2B** against its own prior-year rate.

**4 · The "we buy harder things" defence explains 6 points of a 30-point gap.**
Direct standardisation holds the product mix at the government-wide basket so only
within-category practice varies. Defense's observed 50.9% becomes **57.0%** adjusted, against a
civilian median of **80.5%**. Its portfolio explains **6.1 points**; the remaining **23.5** is
competing less than other agencies *within the same product categories*.

**5 · The year-end surge is the highest in five years.**
September carried **19.0%** of FY2025 obligations against an 8.3% even pace — **$83.4B above a
level pace**, up from 16.2% in FY2023.

**6 · FY2025 split the portfolio.**
Defense (+$45.6B), Veterans Affairs (+$11.4B) and Homeland Security (+$4.7B) grew while HHS
(−28.7%), USAID (−44.9%) and GSA (−10.2%) contracted. HUD posted **net-negative obligations** for
the full year. Agency-level HHI rose from 3,800 to **4,158**.

**7 · The ranking is published with its own uncertainty.**
The Contract Efficiency Index scores 19 agencies across five dimensions — and is re-scored under
**2,000 random weightings**. Only 3 of 19 hold their quartile. The documentation states plainly
that **the middle of the ranking is not separable**, because an index whose weights are a
judgement should be presented as a triage device, not a verdict.

Six costed recommendations, each with the evidence that would falsify it, are in
[**docs/RECOMMENDATIONS.md**](docs/RECOMMENDATIONS.md).

> Nothing here identifies waste, fraud, or abuse. Every output is a prioritisation signal.
> See [Limitations](docs/LIMITATIONS.md).

---

## Quick start

```bash
git clone https://github.com/Akemp787/federal-spending-efficiency-analysis.git
cd federal-spending-efficiency-analysis
pip install -e ".[dev]"
make all
```

`make all` runs `ingest → analyse → warehouse → validate → report` and reproduces every number in
this README from the public API in roughly 15 minutes. Responses are cached under a hash of the
request body, so the second run is instant and offline.

```bash
make test        # 69 known-answer tests, no network
make validate    # 12 data-quality contracts
fedspend query --sql "SELECT * FROM v_gov_headline"
```

---

## What the pipeline does

```
USAspending v2 API ──▶ data/raw/_api_cache/   content-addressed responses
                              │
       FRED GDPDEF ───────────┤
                              ▼
                       data/interim/          13 tidy long extracts
                              ▼
                       data/curated/          25 analytical tables + fedspend.duckdb
                              ▼
                       outputs/               dashboard.html · 18 BI-ready CSVs
```

**Ingestion.** A retrying, rate-limited, disk-cached client pulls agency × fiscal-year
cross-tabulations by extent-of-competition (9 FPDS codes), contract pricing type (16 codes),
fiscal month (12 slices), set-aside status, per-agency vendor breakdowns, sub-agency
competition, and agency x product-category cross-tabs — building 345 agency-years of measures. Failures on individual agency-year queries are recorded in the run
manifest rather than aborting the run or silently zeroing a value.

**Why the API and not the 30GB bulk archive.** The aggregation endpoints compute every
cross-tabulation this analysis needs server-side, which makes the repository something a reviewer
can clone and reproduce rather than only read. The transaction-level path is implemented in
[`bulk_archive.py`](src/fedspend/ingest/bulk_archive.py) for the three measures that genuinely
require row-level fields — single-offer rate, ceiling growth, untruncated vendor HHI.

**Transformation.** Every dollar figure is published in nominal **and** constant FY2025 dollars,
using the BEA GDP implicit price deflator averaged over the four quarters of each federal fiscal
year. Cumulative FY2021–FY2025 inflation is 17.9%, which is the entire reason finding 1 exists.

**Warehouse.** DuckDB, loaded from parquet, with the analytic layer expressed as SQL views in
[`sql/`](sql/) — an independent expression of the same metrics.

**Validation.** Twelve contracts, ERROR-severity failures break CI. The important one is
reconciliation: the competition table is assembled from nine separate API calls per agency-year,
so if those slices do not sum back to the independently-retrieved agency total, every downstream
figure is suspect. **All 325 agency-years reconcile within 1%.**

---

## Technical choices worth a look

| Choice | Why |
|---|---|
| **Robust (MAD) outlier detection** | A classical z-score is masked by the outlier it is meant to find. In the project's own test case a value 100× the others scores a classical z of 2.6 — below any threshold — while the robust score exceeds 500. |
| **Shift-share decomposition** | Separates "agencies changed behaviour" from "money moved between agencies". The two carry opposite implications, and the terms reconcile with no residual, making the attribution a result rather than a story. |
| **Centred mix term** | Since `Σ Δw = 0`, centring on the base rate leaves the total identical but makes each agency's contribution readable. Uncentred, a growing agency always shows a positive mix term regardless of whether it competes above or below average. |
| **Truncation handled explicitly** | Vendor HHI uses top-100 recipients but computes shares against *true* agency totals, making it a strict lower bound rather than a biased estimate. `coverage_share` ships alongside every value. |
| **Weight sensitivity by Dirichlet sampling** | The index weights are a judgement, so the index is re-scored 2,000 times under weightings drawn uniformly from the simplex — and the honest conclusion, that most ranks are not separable, is the headline rather than a footnote. |
| **Config-driven assumptions** | Competition taxonomy, FAR-grounded pricing-risk buckets, materiality floor, and index weights all live in [`config/pipeline.yml`](config/pipeline.yml), so a reviewer can change an assumption without reading the code. |
| **Direct standardisation** | Borrowed from epidemiology's age-standardised mortality rate: hold the product mix constant so cross-agency comparison measures practice rather than mission. It converts the most common objection to a competition league table into a testable, and rejected, hypothesis. |
| **A validation check that caught a real defect** | The sub-agency roll-up contract failed on first run: the government-wide `awarding_subagency` query silently truncates and had dropped Interior's largest component. Switching to per-department queries fixed it. The check is why it was found rather than published. |
| **Growth suppressed off a non-positive base** | Publishing a 40,000% jump because an agency obligated $12k in the base year is how a portfolio project loses credibility. |

---

## Repository layout

```
config/pipeline.yml          every analytical assumption, in one reviewable file
src/fedspend/
  ingest/                    API client (cache + retry), extract orchestration, bulk archive
  transform/                 GDP deflator → constant dollars
  metrics/                   concentration · competition · pricing_risk · timing
                             growth · anomaly · decomposition · standardization
                             efficiency_index
  warehouse/                 DuckDB build, SQL view installation
  validate/                  data-quality contracts
  report/                    inline-SVG charts, dashboard, BI exports
  analysis.py                extracts → 25 curated tables
  cli.py                     fedspend <stage>
sql/                         analytic views over the warehouse
tests/                       69 known-answer tests
docs/                        executive summary · recommendations · methodology
                             data dictionary · limitations
data/samples/                committed outputs, so a clone verifies findings without re-pulling
outputs/                     dashboard.html · star-schema CSVs for Power BI/Tableau
```

---

## The dashboard

[`outputs/dashboard.html`](outputs/dashboard.html) is a single file with no build step and no
JavaScript dependencies — every chart is inline SVG generated from the curated tables, with
colours bound to CSS custom properties so the page follows the reader's light/dark theme without
re-rendering. The only external request is the Google Fonts stylesheet, and every face has a real
fallback stack, so the page renders correctly offline.

Every sentence in it is built from the data at render time, so the prose cannot drift from the
figures. The palette is validated for colour-vision-deficiency separation and surface contrast in
both themes; every chart carries a legend, direct labels, a hover layer, and an expandable table
view of its underlying numbers.

`outputs/dashboard_fragment.html` is the same page without the document skeleton, for embedding
in a host that supplies its own.

---

## Data sources

- **[USAspending API v2](https://api.usaspending.gov/)** — federal contract award transactions
  (award types A, B, C, D; `action_date` basis)
- **[BEA GDP implicit price deflator](https://fred.stlouisfed.org/series/GDPDEF)** via FRED —
  quarterly, fiscal-year averaged

Public data, no API key required.

---

## Author

**Andrew Kemp** — [GitHub](https://github.com/Akemp787)

MIT licensed.
