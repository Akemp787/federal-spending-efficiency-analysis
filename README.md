# Federal Contract Spending Efficiency Analysis

**Where $3.58 trillion of federal contracting money went between 2021 and 2025 — and where it was spent without a competitive bid.**

The US government buys a lot of things. Most of that spending is supposed to go through
competition, because competition is what keeps prices honest. This project measures how much of it
actually does, whether that is changing, and which agencies account for the change.

It pulls five years of federal contract data from a public government API, runs it through a
purpose-built pipeline, and answers those questions. Every number below is reproducible from a
clean checkout.

---

## A five-minute review

| Start here | What it is |
|---|---|
| [**Executive summary**](docs/EXECUTIVE_SUMMARY.md) | The findings, written for a decision-maker. Two pages. |
| [**Recommendations**](docs/RECOMMENDATIONS.md) | Six actions, each sized in dollars and paired with the evidence that would prove it wrong. |
| [**Findings notebook**](notebooks/02_findings.ipynb) | The analysis with charts, rendered on GitHub — no setup needed. |
| [Interactive dashboard](outputs/dashboard.html) | The whole story as one page. Download and open it; it works offline. |
| [**Power BI report**](powerbi/README.md) | A modelled star schema, DAX measures, theme and page-by-page build guide for a ten-page deck. |

For how the project treats the limits of its own conclusions, see
[Limitations](docs/LIMITATIONS.md) — the section most worth a reviewer's attention.

---

## Findings

**1 · Most of the "growth" in federal contracting is not real growth.**
Spending rose 22.9% between FY2021 and FY2025, from $633.2B to $778.4B. That is the figure a
surface reading would report. Adjusted for inflation, the real increase is **4.3%** — about
**$118B of the $145B rise is price level**, not additional goods and services.

**2 · Competition dropped to a five-year low, and almost all of it traces to one department.**
The share of contract dollars awarded competitively fell from 70.3% to **66.3%** in FY2025, the
largest one-year drop in the period.

That could mean two very different things: agencies genuinely competing less of their own work, or
the budget shifting toward agencies that were never especially competitive. The two carry opposite
implications, so the analysis separates them mathematically. It is the first, and it is
concentrated: **the Department of Defense accounts for 93% of the decline**. Its own competitive
share fell from 58.0% to 52.7% while its budget grew. Had DoD held its prior-year rate,
**$25.9B more** would have been competed.

**3 · One level deeper, it is the Navy.**
Departments do not award contracts; the services and agencies inside them do. Running the same
analysis at that level, the **Department of the Navy** drove most of the DoD move: its competitive
share fell from **45.8% to 36.6%** on $176.6B of spending. The Air Force moved in the *opposite*
direction over the same period.

Chaining the two steps, **the Navy alone explains roughly 70% of the entire government-wide
decline** — about **$16.2B** measured against its own prior-year rate. A department-level metric
conceals this completely, which is precisely why competition is worth reporting at the level where
contracts are actually awarded.

**4 · The obvious objection was tested, and it does not hold up.**
The standard defence of a low competition rate is that the mission requires sole-source buying —
there is only one supplier for a submarine reactor. That claim is testable, and the analysis tests
it using a technique borrowed from public health for comparing populations fairly.

Holding the product mix constant, DoD's 50.9% becomes **57.0%**, against a civilian-agency median
of **80.5%**. What DoD buys therefore explains roughly **6 points** of the gap. The remaining
**23.5 points** is DoD competing less than other agencies *on the same kinds of purchases*. The
objection is real, but small.

**5 · Year-end spending hit a five-year high.**
Federal funding expires on September 30, and agencies commit it before it lapses. In FY2025,
September alone carried **19.0%** of the year's contract dollars against the 8.3% an even pace
would imply. That is **$83.4B more than a steady pace** would have placed in a single month, up
from 16.2% in FY2023.

**6 · FY2025 split the government in two.**
Defense (+$45.6B), Veterans Affairs (+$11.4B) and Homeland Security (+$4.7B) grew, while Health
and Human Services (−28.7%), USAID (−44.9%) and GSA (−10.2%) contracted sharply. Housing and Urban
Development ended the year **net negative**, cancelling more contract value than it awarded.
Spending became measurably more concentrated in fewer agencies.

**7 · The ranking is published together with the reasons not to trust most of it.**
A composite "efficiency index" scores 19 agencies across five dimensions. Because the weights in
any such index are a judgment call, every agency was re-scored **2,000 times under randomly chosen
weights**. Only **4 of the 19** held their position.

The conclusion stated throughout the documentation follows from that: the top and bottom of the
ranking are real, and **the middle is not meaningfully separable**. An index published with its
uncertainty attached is more useful than one that appears more authoritative than the evidence
supports.

> **What this analysis does not claim.** Nothing here identifies waste, fraud, or abuse.
> Sole-source contracts are frequently lawful and correct, and some situations genuinely require
> cost-reimbursement contracts. Every output indicates *where a reviewer would learn the most*,
> not where wrongdoing occurred. Details in [Limitations](docs/LIMITATIONS.md).

---

## What this project demonstrates

Read as a work sample, the project is intended to show the following.

**Turning a vague question into a measurable one.** "Is federal contracting efficient?" is not
answerable as written. Competition rate, contract-type risk, vendor concentration and year-end
timing are, and each connects to a real mechanism in how the government buys.

**Selecting the method the question calls for.** The competition finding required a decomposition
to separate behaviour from budget mix. The cross-agency comparison required standardisation, or it
would have compared missions rather than practices. The outlier detection required robust
statistics, because a conventional z-score is concealed by the very outlier it is meant to find.
None of these techniques is exotic; choosing the right one is the skill.

**Stress-testing the analysis against itself.** The index sensitivity analysis exists to establish
whether the results survive different but equally reasonable assumptions. Most of the ranking did
not, and that appears in the headline rather than a footnote.

**Building something reproducible.** The repository can be cloned and every published number
regenerated offline in about two seconds, because each API response is cached and committed. The
consequence matters more than it sounds: figures cannot quietly drift, and a reviewer can verify
the work rather than take it on trust.

**Catching errors before publication.** Automated data-quality checks run on every build. Two of
them caught real defects here — one where a government API silently dropped data, one where a
calculation could return a mathematically impossible result. Both are documented openly rather
than quietly patched.

**Writing for the person who has to act.** The recommendations are sized in dollars, assigned a
confidence level, and each states what evidence would prove it wrong. One is deliberately labelled
low-confidence, because presenting it otherwise would be worse than omitting it.

**Tools:** Python (pandas, NumPy, SciPy) · SQL / DuckDB · statistical analysis · data pipeline
engineering · pytest and CI · data visualisation · technical writing

---

## How it works

```
USAspending API  ─┐
                  ├─▶  cached responses  ─▶  13 clean extracts  ─▶  25 analysis tables
FRED (inflation) ─┘                                                       │
                                                                          ▼
                                            dashboard  ·  18 spreadsheet-ready exports
```

**Getting the data.** A client that retries on failure, respects rate limits and caches every
response pulls contract data broken out by competition type, contract pricing type, month,
small-business status, vendor, sub-agency and product category — 345 agency-years of measurements
in total. A failed query is recorded in the run log rather than silently becoming a zero.

**Why an API instead of bulk downloads.** The same records are published as raw files, but those
run to tens of gigabytes per year. The API computes the equivalent summaries server-side, which is
what makes this repository something a reviewer can run rather than only read. For the three
measures the API genuinely cannot provide, the bulk-file path is implemented in
[`bulk_archive.py`](src/fedspend/ingest/bulk_archive.py).

**Adjusting for inflation.** Every dollar figure appears in both raw and inflation-adjusted terms,
using the standard government price index. Prices rose 17.9% across this window, which is the
entire reason finding 1 exists.

**Storing and querying it.** Everything lands in a DuckDB database, with the analysis also
expressed as [SQL views](sql/) — a second, independent route to the same answers.

**Checking it.** Twelve automated data-quality checks run on every build and fail the build when
something breaks. The most consequential: the competition table is assembled from nine separate
API calls per agency-year, so if those pieces do not add back up to the independently retrieved
total, something is wrong. **All 325 agency-years reconcile within 1%.**

---

## Design decisions and their rationale

| Decision | Reasoning |
|---|---|
| **Robust outlier detection** | A standard z-score is defeated by the outlier it is meant to catch. In this project's own test case, a value 100× larger than the rest scores 2.6 — below any alarm threshold — while the robust method scores over 500. |
| **Separating behaviour from budget mix** | "Competition fell" and "money moved toward less-competitive agencies" call for entirely different responses. The decomposition splits them exactly, with no unexplained remainder, which is what makes it a result rather than a narrative. |
| **Comparing agencies fairly** | Direct standardisation — the principle behind age-adjusted mortality rates — holds the product mix constant so a cross-agency comparison reflects practice rather than mission. It converts the most common objection into a hypothesis that can be tested, and rejected. |
| **Publishing uncertainty alongside the ranking** | Re-scoring under 2,000 random weightings showed most ranks are not stable. Stating that up front is the difference between an index and a league table. |
| **Assumptions in a config file** | Every judgment call — which codes count as competed, the risk categories, the materiality cutoff, the index weights — lives in [`config/pipeline.yml`](config/pipeline.yml), so a reviewer can change one and re-run without reading the code. |
| **A check that caught a real defect** | A validation contract failed on its first run: the government-wide sub-agency API query silently truncates its results and had dropped Interior's *largest* component, leaving totals 33% short. Querying department by department fixed it. That check is the only reason the defect was caught before publication. |
| **Suppressing meaningless growth rates** | An agency that obligated $12k in the base year and $5M later has not meaningfully grown 40,000%. Rates computed off a negligible base are suppressed rather than reported. |

---

## Reproducing the analysis

```bash
git clone https://github.com/Akemp787/federal-spending-efficiency-analysis.git
cd federal-spending-efficiency-analysis
pip install -e ".[dev]"
make all
```

`make all` runs the full pipeline and reproduces every number in this README. Because all API
responses are cached and committed, it completes **offline in about two seconds** — no API key, no
account, no waiting.

```bash
make test        # 69 tests, no network required
make validate    # 12 data-quality checks
fedspend query --sql "SELECT * FROM v_gov_headline"
```

---

## Repository contents

```
config/pipeline.yml     every analytical assumption, in one readable file
src/fedspend/
  ingest/               API client (caching, retries), plus the bulk-file path
  transform/            inflation adjustment
  metrics/              competition · concentration · pricing risk · timing
                        growth · outliers · decomposition · standardization
                        efficiency index
  warehouse/            DuckDB build and SQL views
  validate/             data-quality checks
  report/               charts, dashboard, spreadsheet exports
  analysis.py           extracts → 25 analysis tables
  cli.py                command-line interface
sql/                    analytic views over the warehouse
tests/                  69 tests
docs/                   executive summary · recommendations · methodology
                        data dictionary · limitations
notebooks/              pipeline walkthrough · findings · index deep-dive
data/samples/           committed results, so a fresh clone can verify the findings
outputs/                dashboard.html · CSVs formatted for Power BI / Tableau
powerbi/                star schema, DAX, theme, build guide and talk track
```

---

## The Power BI report

[`powerbi/`](powerbi/README.md) contains everything needed to assemble a ten-page Power BI
presentation: 25 model-ready tables in a star schema, ~40 documented DAX measures, a theme file
carrying the validated palette, a page-by-page build guide, and a talk track.

The data is shaped for the visuals it feeds — legend-driven charts get long tables rather than
wide ones — and the model's structural guarantees are enforced by 35 contract tests, because a
duplicate key or an orphan foreign key in Power BI does not raise an error, it just quietly
returns the wrong number. The recommendations and limitations pages are bound to data tables
rather than typed into text boxes, so the deck regenerates with the analysis.

`.pbix` files can only be authored in Power BI Desktop, so the file itself is assembled by hand
from the guide — roughly an hour of mechanical work.

---

## The dashboard

[`outputs/dashboard.html`](outputs/dashboard.html) is a single self-contained file — no build step,
no JavaScript libraries. Every chart is drawn directly from the analysis tables, and the page
follows the reader's light or dark system theme automatically. It renders offline.

Every sentence on the page is generated from the data at render time, so the prose cannot drift
away from the figures as the analysis changes. The colour palette is validated for colour-vision
deficiency separation and contrast in both themes, and each chart expands to show its underlying
numbers as a table.

---

## Data sources

- **[USAspending API](https://api.usaspending.gov/)** — federal contract award transactions
- **[GDP price deflator](https://fred.stlouisfed.org/series/GDPDEF)** via FRED — for inflation
  adjustment

Both are public and require no API key.

---

## About

Built by **Andrew Kemp** ([GitHub](https://github.com/Akemp787)) as an end-to-end demonstration of
turning a large public dataset into conclusions that can be acted on.

Questions and feedback are welcome — please open an issue.

MIT licensed.
