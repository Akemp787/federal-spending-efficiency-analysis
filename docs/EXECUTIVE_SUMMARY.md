# Executive Summary

**Federal contract spending efficiency, FY2021–FY2025**
Scope: $3.58 trillion in federal contract obligations · 69 awarding agencies · USAspending API
Snapshot and full reproduction instructions: [`METHODOLOGY.md`](METHODOLOGY.md)

---

## The short version

Federal contract obligations reached **$778.4B in FY2025**, a 22.9% increase over FY2021. Almost
none of that is more buying: in constant FY2025 dollars the increase is **4.3%**. Against that
essentially flat real baseline, three things moved in FY2025 — competition fell to a five-year
low, year-end concentration hit a five-year high, and the portfolio bifurcated sharply between
defence and civilian agencies.

The competition decline is not a budget-composition artefact. **93% of it traces to a single
department's own contracting behaviour.**

---

## Finding 1 — Four-fifths of the headline growth is the price level

| | FY2021 | FY2025 | Change |
|---|---:|---:|---:|
| Nominal obligations | $633.2B | $778.4B | **+22.9%** |
| Constant FY2025 dollars | $746.5B | $778.4B | **+4.3%** |

Roughly **$118B** of the $145B nominal increase is the GDP price deflator, not additional goods
and services. Real obligations have moved within a narrow band for five years: indexed to
FY2021 = 100, the real series reads 100 → 100.4 → 105.2 → 101.9 → 104.3.

**Implication.** Any statement about federal contract spending "growth" that does not name a
deflator is describing inflation. Every finding below uses the real series.

---

## Finding 2 — Competition fell to 66.3%, and one department accounts for 93% of the drop

The competed share of obligations fell from **70.3% in FY2024 to 66.3% in FY2025** — a 3.97
percentage-point decline, the largest single-year move in the window. Non-competed obligations
rose from $220.2B to **$262.7B**.

There are two possible explanations with opposite management implications, and a shift-share
decomposition separates them exactly (residual < 1e-15):

| Effect | Contribution | Reading |
|---|---:|---|
| **Within** — agencies competing less of their own work | **−3.06 pp** | behavioural |
| **Mix** — dollars moving toward less-competitive agencies | −0.76 pp | compositional |
| Interaction | −0.15 pp | |
| **Total** | **−3.97 pp** | |

The decline is behavioural, and it is concentrated. The Department of Defense contributes
**−3.67 pp of the −3.97 pp total (93%)**: its own competed share fell from **58.0% to 52.7%**
while its share of federal contract dollars grew from 60.2% to 63.1%.

**Sizing it.** Had DoD merely held its FY2024 competition rate, **$25.9B more** of FY2025
obligations would have been competed. DoD's non-competed obligations totalled **$232.4B** — 88%
of all non-competed contract dollars government-wide.

**Implication.** Government-wide competition reporting obscures this. The rate is effectively a
DoD statistic, and reviewing it at the government level asks the wrong 37 agencies for an
explanation.

---

## Finding 3 — Inside Defense, the Navy accounts for three-quarters of the move

Departments do not award contracts; their components do, under separate acquisition commands.
Running the same decomposition one level down localises Defense's −5.25 pp internal change:

| Component | FY2025 obligations | Competed FY2024 → FY2025 | Contribution |
|---|---:|---:|---:|
| **Department of the Navy** | $176.6B | **45.8% → 36.6%** | **−3.98 pp (76%)** |
| Department of the Army | $107.4B | 61.5% → 55.1% | −1.45 pp |
| Department of the Air Force | $98.5B | 46.4% → **49.6%** | **+0.92 pp** |
| Defense Logistics Agency | $55.9B | 82.6% → 81.4% | −0.27 pp |

Chaining the two decompositions, **the Navy alone accounts for roughly 70% of the
government-wide decline**. Had it held its FY2024 rate, **$16.2B more** would have been competed.
Navy's non-competed obligations totalled **$112.0B**.

The Air Force moved the *other* way, which is what makes this a Navy question rather than a
defence-wide one — and what a department-level metric conceals.

---

## Finding 4 — The "we buy harder things" defence explains 6 points of a 30-point gap

The standard objection to a low competition rate is that the mission requires sole-source buying.
Direct standardisation tests it: hold the product mix at the government-wide basket, and let only
within-category rates vary.

| | Observed | Portfolio-adjusted | Explained by mix |
|---|---:|---:|---:|
| Department of Defense | 50.9% | **57.0%** | 6.1 pp |
| Civilian agency median | — | **80.5%** | — |

Defense's product mix accounts for **6.1 percentage points**. After adjustment it remains
**23.5 points** below the civilian median — competing less than other agencies *within the same
product categories*.

**Caveat stated up front:** Product and Service Codes are coarse, so 23.5 pp is an *upper bound*
on the practice gap. Finer strata would shrink it. Reference coverage is reported per agency
(Defense: 0.98), so this is not a thin-cell artefact.

---

## Finding 5 — The year-end surge is the highest in five years

Annual appropriations expire on 30 September. In FY2025, September carried **19.0% of the year's
contract obligations** against an even-pace expectation of 8.3% — **$83.4B above a level pace**,
and the highest September concentration in the window (16.9 → 17.9 → 16.2 → 17.6 → **19.0**).
Fiscal Q4 as a whole carried 37.2%.

**Implication.** This is a risk indicator, not a finding. Programme cycles genuinely land at year
end. What makes the population worth sampling is that awards written against an expiring
appropriation are where schedule pressure is highest — and that this year the population is
larger than it has been at any point in five years.

---

## Finding 6 — FY2025 split the portfolio

Beneath a +5.1% government-wide move, agency-level changes were unusually large and unusually
one-directional.

| Grew | Change | | Contracted | Change |
|---|---:|---|---|---:|
| Defense | +$45.6B | | Health & Human Services | −$8.6B (−28.7%) |
| Veterans Affairs | +$11.4B | | International Development | −$3.3B (−44.9%) |
| Homeland Security | +$4.7B | | Housing & Urban Development | −$2.9B (to **−$1.3B net**) |
| Energy | +$2.5B | | General Services | −$2.7B (−10.2%) |

Housing and Urban Development posted **net-negative obligations** for the full fiscal year, meaning
de-obligations exceeded new awards — an event with no precedent elsewhere in the window.

Concentration rose accordingly: agency-level HHI moved from 3,800 to **4,158** and the top four
agencies' share from 79.5% to **83.0%**.

---

## Finding 7 — A second risk signal is moving independently

Contract-type risk (cost-reimbursement plus time-and-materials dollars, where the government
rather than the contractor absorbs overruns) was flat government-wide at 33.0%. Underneath that,
individual agencies moved substantially between FY2021 and FY2025:

| Agency | FY2021 | FY2025 | Change |
|---|---:|---:|---:|
| Health & Human Services | 38.9% | 49.2% | **+10.3 pp** |
| Justice | 28.1% | 33.8% | +5.6 pp |
| General Services | 49.6% | 55.0% | +5.4 pp |

HHS shifted toward government-borne cost risk while its obligations fell 28.7% — a smaller
portfolio carrying a larger share of cost exposure.

---

## Where to look first

The review shortlist ranks agencies on scale against non-competed exposure. The top of that list
is unambiguous:

| Agency | FY2025 obligations | Non-competed | Competed rate |
|---|---:|---:|---:|
| **Defense** | $491.7B | **$232.4B** | 52.7% |
| Veterans Affairs | $78.3B | $6.1B | 92.2% |
| NASA | $15.8B | $5.4B | 66.0% |
| State | $9.9B | $2.6B | 73.4% |

A composite Contract Efficiency Index scores 19 material agencies across five dimensions. It is
published **with** a sensitivity analysis re-scoring every agency under 2,000 random weightings,
and that analysis is candid: only three agencies hold the same quartile across the weighting
distribution. **The ranking's middle is not separable and should not be read as one.** The index
is a triage device for allocating review effort, not a performance verdict.

---

## What this analysis does not claim

Nothing here identifies waste, fraud, or abuse. Sole-source awards are frequently lawful and
correct; cost-reimbursement contracts are appropriate for research and complex services;
September awards are often the normal end of a programme cycle. Every output is a prioritisation
signal indicating where contract-level examination would be most productive. Six costed recommendations, each stating what would falsify it, are in
[`RECOMMENDATIONS.md`](RECOMMENDATIONS.md). Full treatment of the caveats is in
[`LIMITATIONS.md`](LIMITATIONS.md).
