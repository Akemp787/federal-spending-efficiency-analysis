# Power BI report — build guide

Everything needed to assemble a ten-page Power BI presentation from this analysis:
a modelled star schema, the DAX, a theme file, and page-by-page instructions.

**What is here and what is not.** A `.pbix` file can only be authored inside Power BI Desktop, so
it cannot be generated from code. Everything *around* it is generated: the data is already shaped
for the visuals it feeds, the relationships are pre-validated, the measures are written, and the
theme carries the palette. Assembly is roughly **60–90 minutes of mechanical work** rather than a
design exercise.

```
powerbi/
├── data/                  25 model-ready CSVs (dim_ / fact_ / viz_)
├── fedspend_theme.json    colour palette, typography, visual defaults
├── measures.dax           ~40 DAX measures, grouped and commented
├── README.md              this file
└── TALK_TRACK.md          what to say on each page
```

Regenerate any time the analysis changes:

```bash
python -m fedspend.cli powerbi
```

---

## Step 1 — Load and model (about 20 minutes)

**Import.** Power BI Desktop ▸ *Get data* ▸ *Text/CSV* ▸ select all 25 files in `powerbi/data`
▸ *Load*. Or *Get data* ▸ *Folder* to bring them in as one batch.

**Apply the theme.** *View* ▸ *Themes* ▸ *Browse for themes* ▸ `fedspend_theme.json`. This sets
the series colours, background, typography and default gridline treatment, so nothing below
requires manual colour picking.

**Relationships.** Power BI will auto-detect some of these; check each one and fix the rest in
*Model view*. All are one-to-many, single direction, from dimension to fact.

| From (one side) | To (many side) | Key |
|---|---|---|
| `dim_fiscal_year` | `fact_agency_year`, `fact_government_year`, `fact_month`, `fact_subagency_year`, `viz_growth_index`, `viz_competition_trend`, `viz_military_departments`, `viz_monthly_pacing` | `fiscal_year` |
| `dim_agency` | `fact_agency_year`, `fact_portfolio_adjusted`, `fact_efficiency_index`, `fact_index_sensitivity`, `fact_review_shortlist`, `fact_risk_migration`, `fact_vendor_concentration`, `viz_largest_movers`, `viz_portfolio_adjusted`, `viz_efficiency_index` | `agency_name` |
| `dim_subagency` | `fact_subagency_year` | `subagency_key` |

> **Why `subagency_key` and not `subagency_name`.** Sub-agency names are not unique across
> government — eight repeat, because several departments run an organisation of the same name
> (an Office of the Inspector General, an Immediate Office of the Secretary). A relationship on
> the bare name is ambiguous and Power BI will reject it. The exporter builds
> `agency_name | subagency_name` as a surrogate key and asserts its uniqueness. **This is worth
> knowing if anyone asks how you handled the model** — it is a real modelling decision, not a
> formatting one.

**Column formatting.** Set these once in *Model view* and every visual inherits them:

| Columns | Format |
|---|---|
| `obligations`, `obligations_real`, `*_obligations`, `change_abs` | Currency, 0 decimals, thousands separator |
| `competed_share`, `*_share`, `observed_rate`, `standardised_rate`, `rate` | Percentage, 1 decimal |
| `*_pp`, `*_pct`, `change_pp` | Decimal, 1–2 decimals |
| `vendor_hhi`, `agency_hhi` | Whole number |
| `fiscal_year` | Whole number, **Summarization: Don't summarize** |

**Sort orders.** Select the column, then *Column tools* ▸ *Sort by column*:

- `dim_fiscal_year[fiscal_year_label]` → sort by `fiscal_year`
- `viz_growth_index[basis]` → sort by `sort_order`
- `viz_competition_trend[series]` → sort by `sort_order`
- `viz_portfolio_adjusted[measure]` → sort by `sort_order`
- `viz_recommendations[id]` → sort by `sort_order`
- `viz_limitations[limitation]` → sort by `sort_order`
- `fact_month[month_name]` → sort by `fiscal_month`

**Measures.** Create a blank table to hold them: *Home* ▸ *Enter data* ▸ name it `_Measures`
▸ *Load*. Then paste each block from [`measures.dax`](measures.dax) via *Modeling* ▸ *New
measure*. They will group under `_Measures` in the field list instead of scattering across fact
tables.

---

## Step 2 — Build the pages

Ten pages. Each has a **headline** (a text box across the top, stating the finding as a sentence),
the visual, and a **so-what** line at the bottom.

The single most important formatting habit throughout: **the page title states the finding, not
the topic.** "Competition fell 4 points, and one department caused it" earns attention;
"Competition Analysis" does not.

---

### Page 1 · Executive summary

**Purpose:** the whole argument in one screen, so a viewer who leaves after 60 seconds still has it.

| Element | Build |
|---|---|
| Title text box | `Where $3.58 trillion went — and where it was spent without a competitive bid` |
| Subtitle | `US federal contract obligations, FY2021–FY2025 · Source: USAspending API` |
| 5 × **Card** visuals across the top | See below |
| **Line chart**, lower left | `viz_growth_index` — Axis `fiscal_year`, Legend `basis`, Values `index_value` |
| **Table**, lower right | `viz_recommendations` — `id`, `recommendation`, `sizing_label`, `confidence` |

Card values, left to right:

1. `[Total Obligations $B]` filtered to FY2025 — label "FY2025 obligations"
2. `[Real Growth vs Base %]` — label "Real growth since FY2021"
3. `[Competed Share]` — label "Competed share"
4. `[September Share]` — label "September concentration"
5. `[Government-Risk Share]` — label "Government-risk pricing"

> Put a slicer on `dim_fiscal_year[fiscal_year_label]` in the top-right corner and **sync it
> across every page** (*View* ▸ *Sync slicers*). One control driving ten pages is the thing that
> makes this read as a model rather than ten disconnected charts.

---

### Page 2 · Growth is mostly inflation

**Headline:** `Spending rose 22.9%. Adjusted for inflation, it rose 4.3%.`

- **Line chart** (large, centre): `viz_growth_index` — Axis `fiscal_year`, Legend `basis`,
  Values `index_value`.
  - *Format* ▸ *Y axis* ▸ start at 95 so the divergence is visible without exaggerating it.
  - Add a constant line at 100 (*Analytics* ▸ *Constant line*), grey, dashed, label "FY2021 = 100".
  - Turn on data labels for the last point only (*Format* ▸ *Data labels* ▸ customise series).
- **Two cards** beneath: `[Growth vs Base %]` and `[Real Growth vs Base %]`.
- **So-what box:** `About $118B of the $145B increase is price level, not additional goods and
  services. Every figure in this report is inflation-adjusted.`

---

### Page 3 · Competition fell to a five-year low

**Headline:** bind the title to the measure `[Title — Competition]` so it restates itself when the
year slicer moves. *Format* ▸ *Title* ▸ *fx* ▸ *Field value* ▸ `Title — Competition`.

- **Line chart:** `viz_competition_trend` — Axis `fiscal_year`, Legend `series`, Values `rate_pct`.
  Three lines: government-wide, Defense, all other agencies. The gap between Defense and everyone
  else is the point of the page.
- **Two cards:** `[Competed Share Change pp]` and `[Non-Competed $B]`.
- **So-what box:** `Non-competed obligations rose from $220.2B to $262.7B in a single year.`

---

### Page 4 · One department, then one service

**Headline:** `93% of the decline is Defense — and 76% of Defense is the Navy`

This is the strongest page. Build it as a two-step drill:

- **Bar chart, left:** `fact_competition_attribution` filtered to `level = "Department"` —
  Y axis `entity`, X axis `total_effect_pp`, sorted ascending. Set *Data colors* ▸ *fx* ▸
  *Field value* ▸ `Colour — Attribution` so losses are red and gains blue.
- **Bar chart, right:** same table filtered to `level = "Component"` **and**
  `parent = "Department of Defense"`.
- **Line chart, bottom:** `viz_military_departments` — Axis `fiscal_year`, Legend `series`,
  Values `rate_pct`. This shows Navy falling while the Air Force rises, which is what makes it a
  Navy question rather than a defence-wide one.
- **So-what box:** `Navy's competed share fell 45.8% → 36.6% on $176.6B. Had it held the prior
  year's rate, $16.2B more would have been competed.`

> If asked how the attribution works: the decomposition splits the change into agencies changing
> their own behaviour versus money moving between agencies, and the parts sum to the total exactly.
> `[Attribution Residual pp]` displays 0.00 — worth putting on the methodology page as proof.

---

### Page 5 · Testing the obvious objection

**Headline:** `"We buy harder things" explains 6 points of a 30-point gap`

Power BI has no native dumbbell chart, so use a **scatter chart**, which reads even better here:

- **Scatter chart:** `fact_portfolio_adjusted` — X axis `observed_rate`, Y axis
  `standardised_rate`, Details `agency_name`, Size `obligations`.
  - Add a y = x reference line (*Analytics* ▸ *Trend line*, or a constant line if the axes share a
    range). Agencies **above** the line are helped by portfolio adjustment; those **below** are
    flattered by their product mix.
- **Alternative if you prefer the dumbbell:** clustered bar chart on `viz_portfolio_adjusted` —
  Y axis `agency_name`, X axis `rate_pct`, Legend `measure`, sorted by `sort_by_adjusted`.
- **Cards:** `[Portfolio Effect pp]` and `[Gap to Civilian Median pp]`.
- **So-what box:** `Defense's product mix explains 6.1 points. The remaining 23.5 points is
  competing less than other agencies on the same kinds of purchases.`
- **Caveat box (small, muted):** `Product categories are coarse, so 23.5 points is an upper bound.`

---

### Page 6 · The year-end surge

**Headline:** `19% of the year's contracting happened in its final month`

- **Column chart:** `viz_monthly_pacing` — X axis `month_name`, Y axis `index_vs_even_pace`.
  - *Data colors* ▸ *fx* ▸ `Colour — September` so September is orange and every other month blue.
    One highlighted bar beats a second series.
  - *Analytics* ▸ *Constant line* at 100, labelled "even monthly pace".
- **Card:** `[September Above Even Pace $B]`.
- **So-what box:** `$83.4B more than a steady pace would have placed in one month — the highest
  concentration in five years.`
- **Caveat box:** `This is a sampling frame, not a finding. Programme cycles genuinely cluster at
  year end.`

---

### Page 7 · FY2025 split the government

**Headline:** `Defense and security grew; civilian and international contracted sharply`

- **Bar chart:** `viz_largest_movers` — Y axis `agency_name`, X axis `change_bn`, sorted.
  *Data colors* ▸ *fx* ▸ `Colour — Diverging`.
- **Table beside it:** `agency_name`, `prior_year`, `obligations`, `change_pct`, `change_pct_real`.
  Apply *Conditional formatting* ▸ *Background color* on `change_pct`, diverging red-to-blue.
- **So-what box:** `Housing and Urban Development ended the year net negative — it cancelled more
  contract value than it awarded.`

---

### Page 8 · A ranking, and why not to trust most of it

**Headline:** bind to `[Title — Index Caveat]`.

- **Bar chart:** `viz_efficiency_index` — Y axis `agency_name`, X axis `efficiency_index`,
  sorted descending.
  - *Analytics* ▸ *Error bars* ▸ upper `band_high`, lower `band_low`. These show the 5th–95th
    percentile of scores across 2,000 random weightings. **The error bars are the point of the
    page** — where they overlap, the ranking is not real.
- **Table beside it:** `agency_name`, `rank`, `rank_best`, `rank_worst`, `quartile_verdict`.
- **Card:** `[Robust Agency Count]`.
- **So-what box:** `Only 4 of 19 agencies hold their quartile. The top and bottom are real; the
  middle is not separable and should not be read as an ordering.`

> This page is the one that distinguishes the work. Most portfolio dashboards present a ranking as
> settled. Showing the uncertainty, and saying which parts survive it, is the senior move.

---

### Page 9 · Recommendations

**Headline:** `Six places to look, sized and ranked by what they would teach`

- **Table** (full width): `viz_recommendations` — `id`, `recommendation`, `population`,
  `sizing_label`, `confidence`, `evidence`.
  - *Conditional formatting* ▸ *Font color* on `confidence` ▸ *fx* ▸ `Colour — Confidence`
    (green / amber / grey).
  - Widen the `evidence` column and enable *Word wrap*.
  - Turn the *Values* font size up to 11 and row padding up — this page is read, not scanned.
- **Text box, bottom:** `Each recommendation states what evidence would prove it wrong.
  R6 is deliberately labelled low-confidence.`

> Keeping the recommendations as a **table bound to data** rather than a static text box means they
> re-render when the analysis changes, and it demonstrates the same discipline as the rest of the
> model. It is also the answer if an interviewer asks "how do you keep a deck in sync with the
> data?"

---

### Page 10 · Limitations

**Headline:** `What this analysis cannot support`

- **Table:** `viz_limitations` — `category`, `limitation`, `detail`, grouped by `category`.
- **Callout text box** (make it visually prominent):
  `Nothing here identifies waste, fraud or abuse. Sole-source awards are frequently lawful and
  correct. Every output indicates where review would be most productive, not where wrongdoing
  occurred.`
- **Second callout:** `No savings estimate is possible. Competition affects price, but this
  analysis observes obligations, not prices.`

> Do not treat this as a disclaimer page to click past. In a consulting interview it is often the
> page that earns the most credit, because it shows you know the boundary of your own evidence.

---

### Optional page 11 · Method and data quality

Worth adding if the audience is technical.

- **Table:** `fact_validation` — `name`, `passed`, `severity`, `message`. Twelve automated checks,
  run on every build.
- **Card:** `[Attribution Residual pp]` — displays 0.00, which is the proof the decomposition is
  exact rather than approximate.
- **Table:** `dim_glossary` — every term the deck uses, defined.
- **Text box:** `All 325 agency-years reconcile within 1%. Two defects were caught by these checks
  before publication: a government API that silently truncated results, and a calculation that
  could return an impossible rate.`

---

## Step 3 — Polish

- **Consistent page furniture.** Same title position, same font sizes, same margins on every page.
  Build page 2 fully, then copy it and swap the visual.
- **Turn off visual headers** in reading view: *File* ▸ *Options* ▸ *Report settings*.
- **Page navigation.** Insert ▸ *Buttons* ▸ *Navigator* ▸ *Page navigator* for a clickable
  contents strip.
- **Alt text** on every visual (*Format* ▸ *General* ▸ *Alt text*) — accessibility, and it reads as
  professional care.
- **Tooltips.** Set a tooltip page showing the agency's five-year trend, so hovering any bar gives
  context without leaving the page.
- **Export.** *File* ▸ *Export* ▸ *PDF* gives a shareable deck. Publish to Power BI Service if you
  want a live link for applications.

---

## What to emphasise if you are presenting this

The analysis is the substance, but these are the model-building decisions worth naming:

1. **A composite key for sub-agencies**, because the natural key was not unique — a real modelling
   problem, found and handled.
2. **Rates recomputed from components, not averaged.** `[Competed Share]` divides summed dollars
   rather than averaging agency rates, because an unweighted average of rates is not the
   government's rate. This is the most common error in a spending dashboard.
3. **Dynamic titles bound to measures**, so a headline cannot go stale when a slicer moves.
4. **Uncertainty shown on the ranking**, not hidden.
5. **Narrative pages bound to data tables**, so the deck regenerates with the analysis.

See [`TALK_TRACK.md`](TALK_TRACK.md) for what to say on each page.
