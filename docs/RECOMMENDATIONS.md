# Recommendations

Six recommendations derived from the FY2021–FY2025 analysis, ordered by expected value of the
review effort rather than by dollar size.

**How to read these.** Each recommendation names the population it applies to, sizes it in
dollars, states the evidence, and — critically — states **what would show it to be wrong**. None
of them is a finding of waste. A recommendation here means *this is where an oversight function
would learn the most per hour spent*, which is a different and more defensible claim.

**Standing caveat.** This analysis observes obligations, not decisions. It can identify where no
market test occurred; it cannot see the justification file that may fully explain why. Every
recommendation below is a request for a look, not an allegation.

---

## R1 — Rebaseline competition reporting to the sub-agency that actually awards

**Population** Department of the Navy · **$176.6B** in FY2025 obligations
**Confidence** High — the attribution is arithmetic, not inference

### The finding

Government-wide competed share fell 3.97 pp in FY2025. Successive exact decompositions localise
almost all of it to one organisation:

| Level | Contribution | Share of the level above |
|---|---:|---:|
| Government-wide change | −3.97 pp | — |
| → Department of Defense | −3.67 pp | **93%** |
| → → Department of the Navy | −3.98 pp of DoD's −5.25 pp | **76%** |
| **Navy's share of the government-wide move** | | **≈ 70%** |

Navy's own competed share fell from **45.8% to 36.6%** — a 9.2-point drop in one year, against a
five-year range of 39–46%. Air Force moved the *other* way (+3.2 pp), which is what makes this a
Navy question rather than a defence-wide one.

**Sizing.** Had Navy held its FY2024 rate, **$16.2B more** of FY2025 obligations would have been
competed.

### Recommendation

Report and review competition at sub-agency level, not department level. A department-level
metric averaged Navy's 9-point fall against Air Force's 3-point rise and DLA's 81% rate, and
reported "DoD declined" — which directs the question to 40 organisations, 39 of which did not
cause it.

### What would show this wrong

- A small number of very large Navy shipbuilding or propulsion awards landing in FY2025 could
  move the rate mechanically without any change in practice. **Check first:** the FY2025
  award-level distribution for Navy PSC categories 19xx (ships) and 1410 (missiles). If the drop
  is three awards, this is a lumpiness artefact, not a trend.
- A change in how Navy codes `extent_competed` would produce the same signature.

---

## R2 — Test the "we buy harder things" defence before accepting it

**Population** Department of Defense · **$491.7B** · **Confidence** High

### The finding

The standard response to a low competition rate is that the mission requires sole-source buying.
That is testable. Using direct standardisation — holding the product mix constant at the
government-wide basket and letting only within-category rates vary:

| | Observed | Portfolio-adjusted | Gap explained by mix |
|---|---:|---:|---:|
| Department of Defense | 50.9% | **57.0%** | 6.1 pp |
| Civilian agency median | — | **80.5%** | — |

DoD's product mix explains **6.1 points**. After adjustment it remains **23.5 points** below the
civilian median. Roughly **three-quarters of the gap is practice, not mission** — DoD competes
less *within the same product categories* than civilian agencies do.

### Recommendation

Use the portfolio-adjusted rate as the comparison basis in any cross-agency competition
discussion. It removes the single most common objection to the raw comparison, and it moves the
conversation from "our mission is different" to the specific product categories where the
within-category gap is largest (`portfolio_stratum_detail` ranks these per agency).

### What would show this wrong

- Product and Service Codes are coarse. "Guided missiles" contains both a sole-source prime
  integration contract and a competitive components buy. Finer strata could shrink the residual
  gap. **The honest bound:** 23.5 pp is an upper estimate of the practice gap, not a point
  estimate.
- Coverage is reported per agency (`reference_coverage`); DoD's is 0.98, so this is not a
  thin-cell artefact.

---

## R3 — Sample the September population, and sample it for contract type

**Population** **$83.4B** obligated above an even pace in September FY2025 · **Confidence** Medium

### The finding

September carried **19.0%** of FY2025 contract obligations against an 8.3% even-pace
expectation — the highest concentration in the five years observed (16.9 → 17.9 → 16.2 → 17.6 →
19.0). Fiscal Q4 carried 37.2%.

### Recommendation

Do **not** treat September volume as a finding. Treat it as a sampling frame. The specific test
worth running: within the September population, compare competition rate and fixed-price share
against the same agency's October–August baseline. If year-end awards are systematically less
competed and less fixed-price, that is a process finding with a clear remedy (earlier requirement
definition, multi-year vehicles). If they are indistinguishable, the surge is a scheduling
artefact and should be dropped as an oversight priority.

**This project does not yet answer that question** — the month × competition cross-tab is not in
the current extract. It is a ~60-call addition and is the highest-value next build.

### What would show this wrong

- Programme cycles genuinely cluster at year end for legitimate reasons (option exercises,
  annual service renewals). A high September share with a *normal* competition and pricing
  profile is not a problem.

---

## R4 — Treat rising government-risk pricing as a separate, independent signal

**Population** **$256.5B** priced cost-reimbursement or time-and-materials in FY2025 (33.0%)
**Confidence** Medium

### The finding

Government-wide contract-type risk was flat, but individual agencies moved substantially over the
window:

| Agency | FY2021 | FY2025 | Change |
|---|---:|---:|---:|
| Health & Human Services | 38.9% | 49.2% | **+10.3 pp** |
| Justice | 28.1% | 33.8% | +5.6 pp |
| General Services | 49.6% | 55.0% | +5.4 pp |

HHS is the case worth opening: its cost-risk share rose 10 points **while its obligations fell
28.7%**. A shrinking portfolio that is simultaneously shifting toward government-borne cost risk
is a different situation from a growing one doing the same thing, and the combination is not
visible in either metric alone.

### Recommendation

Pair the contract-type series with the volume series in any portfolio review. Under FAR 16.301-2
cost-reimbursement requires a determination that cost uncertainty prevents a fixed price; a
10-point shift over four years is a reasonable trigger for asking whether those determinations
are still being made deliberately or have become the default.

### What would show this wrong

- If HHS's remaining portfolio is disproportionately R&D and managed-care services — which
  legitimately carry cost-reimbursement — the shift is composition, not practice. **The same
  standardisation used in R2 would settle it**, and has not yet been run on contract type. That
  is a direct extension of existing code.

---

## R5 — Do not rank agencies on the efficiency index; use only its tails

**Population** 19 agencies scored · **Confidence** High (about the limitation itself)

### The finding

The Contract Efficiency Index combines five dimensions into one score. Re-scored under 2,000
weightings drawn uniformly from the simplex, **only 4 of 19 agencies hold their quartile**. Most
ranks move enough across defensible weightings that the ordering carries no information.

### Recommendation

Use the index the way it survives scrutiny: as a **tail detector**. The agencies that sit in the
bottom quartile under almost any weighting are a genuine shortlist. The ordering within the
middle is an artefact of weight choice and should not appear in any briefing as a ranking.

If a single defensible number is needed instead, use the portfolio-adjusted competition rate from
R2 — one dimension, one explicit adjustment, no weighting judgement.

### What would show this wrong

Nothing about the sensitivity result is likely to change; it is a property of the construction.
What *could* change is the index's usefulness: a factor analysis establishing that the five
dimensions load onto fewer independent factors would justify a simpler, more stable composite.
That analysis has not been done.

---

## R6 — Re-examine vendor concentration where the buyer is small and the market is thin

**Population** Agencies with vendor HHI above the DOJ "highly concentrated" threshold
**Confidence** Low — this is the weakest recommendation here, and is included with that label

### The finding

Vendor concentration within agencies varies by two orders of magnitude (HHI 40 to 4,878). Several
agencies exceed the DOJ/FTC 2,500 "highly concentrated" threshold.

### Why the confidence is low

1. Vendor HHI is computed on each agency's **top 100** recipients, so it is a strict lower bound.
2. There is **no corporate-family rollup** — subsidiaries of one parent count separately, which
   understates true concentration by an unknown amount.
3. High concentration in a small agency buying one specialised thing is expected, not alarming.

### Recommendation

Treat this as a **data-improvement priority rather than a finding**. Rolling recipients up to
`recipient_parent_name` (available in the bulk-archive path) would make the measure trustworthy
enough to act on. Until then it belongs in the index as a component, not in a briefing as a
conclusion.

---

## Sizing summary

| # | Population | FY2025 dollars | Confidence |
|---|---|---:|---|
| R1 | Navy competition decline | $16.2B vs prior-year rate | High |
| R2 | DoD practice gap after portfolio adjustment | 23.5 pp of $491.7B | High |
| R3 | September above even pace | $83.4B | Medium |
| R4 | Government-risk-priced obligations | $256.5B | Medium |
| R5 | — (methodological) | — | High |
| R6 | Concentrated vendor bases | not reliably sizeable | Low |

For scale: **one percentage point** of government-wide competition is **$7.8B** of obligations
moving into competed status.

---

## What none of this supports

- That any specific award was improper.
- That non-competed dollars are wasted dollars. Sole-source is frequently lawful and correct.
- That cost-reimbursement contracting is misuse. It is required where cost uncertainty prevents
  a fixed price.
- Any dollar estimate of "savings". Competition affects price, but this analysis observes no
  prices — only obligations. Anyone converting these figures into a savings claim is going beyond
  what the data can carry.

Full treatment in [`LIMITATIONS.md`](LIMITATIONS.md).
