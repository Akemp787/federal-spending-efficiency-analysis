# Limitations

What this analysis can and cannot support. Read this before citing any figure.

---

## 1. The central caveat

**Nothing in this project identifies waste, fraud, or abuse.**

Every output is a *prioritisation signal* — an indication of where contract-level examination
would be most productive. The distinction matters concretely:

| The data shows | It does **not** show |
|---|---|
| $232.4B of DoD obligations were not competed | that any of those awards was improper |
| 19.0% of FY2025 dollars were obligated in September | that year-end awards were rushed or wasteful |
| HHS moved 10.3 pp toward cost-reimbursement | that cost-reimbursement was the wrong vehicle |
| An agency ranks 19th on the efficiency index | that the agency performs badly |

Sole-source awards are frequently lawful and correct (a single qualified source, an urgent and
compelling need, a follow-on where re-competition would cost more than it saves).
Cost-reimbursement is the appropriate vehicle when cost uncertainty prevents a fixed price.
September awards are often simply the normal end of a programme cycle. Establishing whether any
specific pattern is a problem requires contract-level review — which is the work this analysis is
designed to target, not replace.

---

## 2. Measurement limitations

**Obligations, not outlays.** Figures are net `federal_action_obligation` — money committed, not
money spent. An obligation may be de-obligated, and a large obligation in September may be
outlaid over several subsequent years. De-obligations are retained in the totals, which is why an
agency can post a negative fiscal year.

**Contracts only.** Award types A/B/C/D. Grants, loans, direct payments, insurance, and
intergovernmental transfers are out of scope, so this is not a picture of federal spending — it
is a picture of federal *contracting*. IDV vehicles are excluded to avoid double-counting the
orders placed against them.

**Awarding agency, not funding agency.** Attribution is to the agency that awarded the contract.
Where one agency awards on another's behalf — a substantial share of GSA's volume — the
obligation is attributed to the awarding agency. This materially affects GSA's profile in
particular, and it is the reason a franchise-fund agency should not be compared to a
mission agency without adjustment.

**Two tiers, not four.** Analysis runs at department and sub-agency level. FPDS carries further
levels — contracting office, major command — and the Navy finding would be more actionable still
if it named the command. Office-level attribution is the natural next step and is supported by the
same API pattern.

---

## 3. Metric-specific limitations

### Competition

- **Follow-on actions (code E) are counted as not competed.** This is the FPDS-NG convention but
  not universal. The sensitivity analysis re-runs under the opposite treatment.
- **The rate does not measure competition quality.** A competed action that attracts exactly one
  bid has satisfied the process without obtaining price discipline. The single-offer rate — the
  materially better measure — requires `number_of_offers_received`, which the aggregation API does
  not expose. It is implemented in the bulk-archive path
  ([`bulk_archive.py`](../src/fedspend/ingest/bulk_archive.py)) but is **not** in the published
  headline figures.
- **The category control is coarse.** Cross-agency comparison is now portfolio-adjusted by
  direct standardisation (see `METHODOLOGY.md` §3b), which removes the composition objection at
  the level of PSC first character. But "guided missiles" contains both a sole-source integration
  contract and a competitive components buy, so the residual gap is an **upper bound** on the
  practice difference. Finer strata would shrink it; how much is unknown.
- **Portfolio adjustment covers one fiscal year.** The PSC extract runs for the two most recent
  years only, so the adjusted rate is a latest-year snapshot rather than a trend.

### Contract-type risk

Contract type is chosen for the requirement, not as a performance choice. The measure sizes a
population; it does not allege misuse. Comparing a research agency's cost-reimbursement share to
a supply agency's is not a like-for-like comparison.

### Concentration

- **Vendor HHI is truncated** at each agency's top 100 recipients. Shares are computed against
  true agency totals, so the value is a strict lower bound rather than a biased estimate, and
  `coverage_share` reports how much of the market was observed. For most large agencies coverage
  is high; for agencies with very long vendor tails it is lower and the HHI correspondingly more
  conservative.
- **No corporate-family rollup.** Recipients are counted as reported. Subsidiaries of one parent
  may appear as separate vendors, which *understates* true concentration. `recipient_parent_name`
  in the bulk path would address this.

### Year-end timing

`september_excess_obligations` measures dollars above a level 1/12 pace. A level pace is a
benchmark, not a norm — no one has established that even monthly obligation is optimal. The
figure is a magnitude for the surge, not a quantification of waste.

### The efficiency index

- **The weights are a judgement.** This is the reason the sensitivity analysis exists and is
  published alongside every rank.
- **Only 4 of 19 agencies hold the same quartile** across 2,000 random weightings. The middle of
  the ranking is **not separable** and should not be reported as an ordering.
- **The five dimensions are not independent.** An agency with a thin vendor base likely also
  competes less; the composite double-counts to an unquantified degree. A factor analysis would
  establish how much — it has not been done.
- **No size or mission adjustment.** Agencies are compared as they are.

---

## 4. Data limitations

**FPDS data quality.** The underlying data is agency-reported and carries known reporting lags,
corrections, and coding inconsistencies. USAspending publishes corrections continuously, so
figures for recent periods can move after the snapshot date recorded in
`data/curated/_manifest.json`.

**FY2025 completeness.** FY2025 closed 30 September 2025 and this snapshot was taken well after
the ~90-day settlement window, so the year is treated as complete. Late corrections remain
possible.

**Null codes.** A small number of transactions carry a null `extent_competed` or
`type_of_contract_pricing`. These are returned by no code-filtered query, which is why the
reconciliation checks use a 1% tolerance rather than requiring exact equality. All 325 agency-years
reconcile within that band.

**Deflator vintage.** BEA revises the GDP deflator. Real figures will shift slightly on revision.
The quarterly source series is cached in `data/raw/gdpdef_quarterly.csv` so any published real
figure can be traced to the exact vintage used.

---

## 5. What would strengthen this analysis

Honest statement of the next steps, in rough order of value:

1. **September quality contrast** — compare the competition rate and fixed-price share of
   year-end awards against the same agency's October–August baseline. This turns the timing
   observation into a process finding or retires it. A ~60-call extract; the highest-value next
   build, and the open question behind recommendation R3.
2. **Single-offer rate** via the bulk archive — turns "competed" into "actually contested". A
   competed award drawing one bid satisfied the process without obtaining price discipline.
3. **Contract-type standardisation** — apply the same portfolio adjustment used for competition
   to `government_risk_share`, which would settle whether the HHS shift is composition or
   practice (recommendation R4).
4. **Contracting-office attribution** within Navy — take the finding from a service to a command.
5. **Corporate-family rollup** of recipients — current vendor HHI understates concentration.
6. **Outlay linkage** — connect obligations to actual spending to test whether the September
   surge translates into different execution outcomes.
7. **Award-level modification analysis** — ceiling growth is implemented but not yet integrated
   into the published findings.
