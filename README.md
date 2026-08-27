# Federal Contract Spending Efficiency Analysis

**Where $3.58 trillion of federal contracting money went between 2021 and 2025 — and where it was spent without a competitive bid.**

The US government buys a lot of things. Most of it is supposed to go through competition, because
competition is what keeps prices honest. I wanted to know how much of it actually does, whether
that's changing, and which agencies account for the change.

This project pulls five years of federal contract data from a public government API, runs it
through a pipeline I built, and answers those questions. Every number below is reproducible from a
clean checkout.

---

## If you only have five minutes

| Start here | What it is |
|---|---|
| [**Executive summary**](docs/EXECUTIVE_SUMMARY.md) | The findings, written for a decision-maker. Two pages. |
| [**Recommendations**](docs/RECOMMENDATIONS.md) | Six actions, each sized in dollars and paired with the evidence that would prove it wrong. |
| [**Findings notebook**](notebooks/02_findings.ipynb) | The analysis with charts, rendered on GitHub — no setup needed. |
| [Interactive dashboard](outputs/dashboard.html) | The whole story as one page. Download and open it; it works offline. |

If you'd rather see how I think about the limits of my own work, read
[Limitations](docs/LIMITATIONS.md). It's the section I'd most want a hiring manager to read.

---

## What I found

**1 · Most of the "growth" in federal contracting isn't real growth.**
Spending rose 22.9% between FY2021 and FY2025, from $633.2B to $778.4B. That's the number you'd
report if you stopped there. Adjusted for inflation, the real increase is **4.3%** — about
**$118B of the $145B rise is just prices going up**, not the government buying more.

**2 · Competition dropped to a five-year low, and almost all of it traces to one department.**
The share of contract dollars awarded competitively fell from 70.3% to **66.3%** in FY2025, the
biggest one-year drop in the period.

That could mean two very different things: agencies genuinely competing less of their own work, or
the budget simply shifting toward agencies that were never very competitive. Those have opposite
implications, so I separated them mathematically. It's the first one, and it's concentrated:
**the Department of Defense accounts for 93% of the decline**. Its own competitive share fell from
58.0% to 52.7% while its budget grew. Had DoD just held its prior-year rate, **$25.9B more** would
have been competed.

**3 · Going one level deeper, it's really the Navy.**
Departments don't award contracts — the services and agencies inside them do. Running the same
analysis a level down, the **Department of the Navy** drove most of the DoD move: its competitive
share fell from **45.8% to 36.6%** on $176.6B of spending. The Air Force moved the *opposite*
direction over the same period.

Put the two steps together and **the Navy alone explains roughly 70% of the entire government-wide
decline** — about **$16.2B** measured against its own prior-year rate. A department-level metric
hides this completely, which is exactly why it's worth reporting at the level where contracts
actually get awarded.

**4 · I tested the obvious objection, and it doesn't hold up.**
The standard defense of a low competition rate is "we buy harder things — there's only one
supplier for a submarine reactor." That's testable, so I tested it, using a technique borrowed
from public health for comparing populations fairly.

Holding the product mix constant, DoD's 50.9% becomes **57.0%**, against a civilian-agency median
of **80.5%**. So what DoD buys explains about **6 points** of the gap. The remaining **23.5
points** is DoD competing less than other agencies *on the same kinds of purchases*. The objection
is real, but small.

**5 · Year-end spending hit a five-year high.**
Federal funding expires on September 30, and agencies rush to commit it before it disappears. In
FY2025, September alone carried **19.0%** of the year's contract dollars, against the 8.3% you'd
expect from an even pace. That's **$83.4B more than a steady pace** would have placed in a single
month, up from 16.2% in FY2023.

**6 · FY2025 split the government in two.**
Defense (+$45.6B), Veterans Affairs (+$11.4B) and Homeland Security (+$4.7B) grew, while Health
and Human Services (−28.7%), USAID (−44.9%) and GSA (−10.2%) contracted sharply. Housing and Urban
Development actually ended the year **net negative** — it cancelled more contract value than it
awarded. Spending became measurably more concentrated in fewer agencies.

**7 · I published a ranking, then showed why you shouldn't trust most of it.**
I built a composite "efficiency index" scoring 19 agencies across five dimensions. But the weights
in any index like that are a judgment call, so I re-scored every agency **2,000 times using
randomly chosen weights**. Only **4 of the 19** kept their position.

So the honest conclusion is the one in the documentation: the top and bottom of the ranking are
real, and **the middle is not meaningfully separable**. I'd rather publish an index with its
uncertainty attached than one that looks more authoritative than it is.

> **What this analysis does not claim.** Nothing here identifies waste, fraud, or abuse.
> Sole-source contracts are frequently lawful and correct, and some situations genuinely require
> cost-reimbursement contracts. Everything here points to *where a reviewer would learn the most*,
> not to wrongdoing. Details in [Limitations](docs/LIMITATIONS.md).

---

## What this project demonstrates

If you're reading this as a work sample, here's what it's meant to show.

**Turning a vague question into a measurable one.** "Is federal contracting efficient?" isn't
answerable as written. Competition rate, contract-type risk, vendor concentration and year-end
timing are — and each one connects to a real mechanism in how the government buys.

**Knowing which method the question calls for.** The competition finding needed a decomposition to
separate behavior from budget mix. The cross-agency comparison needed standardization, or it would
have compared missions instead of practices. The outlier detection needed robust statistics,
because a conventional z-score gets concealed by the very outlier it's looking for. None of these
are exotic; choosing the right one is the skill.

**Stress-testing my own conclusions.** The index sensitivity analysis exists specifically to find
out whether my results survive different reasonable assumptions. Most of the ranking didn't, and I
put that in the headline rather than a footnote.

**Building something reproducible.** Anyone can clone this and regenerate every published number,
offline, in about two seconds, because every API response is cached and committed. That matters
more than it sounds: the numbers can't quietly drift, and a reviewer can check my work instead of
taking it on faith.

**Catching my own mistakes before publishing.** Automated data-quality checks run on every build.
Two of them caught real bugs here — one where a government API silently dropped data, one where a
calculation could produce a mathematically impossible result. Both are documented in the open
rather than quietly patched.

**Writing for the person who has to act.** The recommendations are sized in dollars, given a
confidence level, and each one states what evidence would prove it wrong. One is deliberately
labeled low-confidence, because pretending otherwise would be worse than saying nothing.

**Tools:** Python (pandas, NumPy, SciPy) · SQL / DuckDB · statistical analysis · data pipeline
engineering · pytest and CI · data visualization · technical writing

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
in total. If a query fails, it's recorded in the run log rather than silently becoming a zero.

**Why an API instead of bulk downloads.** The government also publishes these records as raw files,
but they run to tens of gigabytes per year. The API computes the same summaries server-side, which
is what makes this repository something you can actually run rather than only read. For the three
measures the API genuinely can't provide, the bulk-file path is implemented in
[`bulk_archive.py`](src/fedspend/ingest/bulk_archive.py).

**Adjusting for inflation.** Every dollar figure appears in both raw and inflation-adjusted terms,
using the standard government price index. Prices rose 17.9% across this window, which is the
entire reason finding #1 exists.

**Storing and querying it.** Everything lands in a DuckDB database, with the analysis also
expressed as [SQL views](sql/) — a second, independent route to the same answers.

**Checking it.** Twelve automated data-quality checks run on every build and fail the build when
something breaks. The most important one: the competition table is assembled from nine separate API
calls per agency-year, so if those pieces don't add back up to the independently-retrieved total,
something is wrong. **All 325 agency-years reconcile within 1%.**

---

## Decisions I'd be glad to be asked about

| Decision | Reasoning |
|---|---|
| **Robust outlier detection** | A standard z-score is defeated by the outlier it's meant to catch. In this project's own test case, a value 100× larger than the rest scores 2.6 — below any alarm threshold — while the robust method scores over 500. |
| **Separating behavior from budget mix** | "Competition fell" and "money moved toward less-competitive agencies" call for completely different responses. The decomposition splits them exactly, with no unexplained remainder, which is what makes it a result rather than a story. |
| **Comparing agencies fairly** | Direct standardization — the same idea behind age-adjusted mortality rates — holds the product mix constant so a cross-agency comparison reflects practice rather than mission. It turned the most common objection into a hypothesis I could test, and reject. |
| **Publishing uncertainty alongside the ranking** | Re-scoring under 2,000 random weightings showed most ranks aren't stable. Saying so up front is the difference between an index and a league table. |
| **Assumptions in a config file** | Every judgment call — which codes count as competed, the risk categories, the materiality cutoff, the index weights — lives in [`config/pipeline.yml`](config/pipeline.yml), so anyone can change one and re-run without reading the code. |
| **A check that caught a real bug** | A validation contract failed on its first run: the government-wide sub-agency API query silently truncates its results and had dropped Interior's *largest* component, leaving the totals 33% short. Querying department-by-department fixed it. That check is the only reason it was caught before publication. |
| **Refusing to publish nonsense growth rates** | An agency that spent $12k in the base year and $5M later hasn't meaningfully grown 40,000%. Rates like that are suppressed rather than reported. |

---

## Running it yourself

```bash
git clone https://github.com/Akemp787/federal-spending-efficiency-analysis.git
cd federal-spending-efficiency-analysis
pip install -e ".[dev]"
make all
```

`make all` runs the whole pipeline and reproduces every number in this README. Because all API
responses are cached and committed, it runs **offline in about two seconds** — no API key, no
account, no waiting.

```bash
make test        # 69 tests, no network required
make validate    # 12 data-quality checks
fedspend query --sql "SELECT * FROM v_gov_headline"
```

---

## What's in the repository

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
```

---

## The dashboard

[`outputs/dashboard.html`](outputs/dashboard.html) is a single self-contained file — no build step,
no JavaScript libraries. Every chart is drawn directly from the analysis tables, and the page
follows your system's light or dark theme automatically. Download it and it works offline.

Every sentence on the page is generated from the data at render time, so the writing can't drift
away from the numbers as the analysis changes. The color palette is checked for color-blind
readability and contrast in both themes, and each chart expands to show the underlying figures as
a table.

---

## Data sources

- **[USAspending API](https://api.usaspending.gov/)** — federal contract award transactions
- **[GDP price deflator](https://fred.stlouisfed.org/series/GDPDEF)** via FRED — for inflation
  adjustment

Both are public and require no API key.

---

## About

Built by **Andrew Kemp** ([GitHub](https://github.com/Akemp787)) as an end-to-end demonstration of
turning a large public dataset into conclusions someone could act on.

Questions and feedback are welcome — open an issue.

MIT licensed.
