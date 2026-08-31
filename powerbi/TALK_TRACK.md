# Talk track

What to say on each page. Timings assume a **12-minute walkthrough** with questions after; the
short version in brackets is for a 5-minute slot.

The through-line, so every page has a job: *spending looks like it grew but didn't → competition
fell → here is exactly who → the obvious excuse doesn't hold → here is what to do → here is what
this can't tell you.*

---

## Page 1 · Executive summary — 60 seconds

> "This is five years of federal contract data — $3.58 trillion across 69 agencies, pulled from
> the USAspending API and run through a pipeline I built. Four things came out of it. Spending
> looks like it grew 23%, but nearly all of that is inflation. Competition fell to a five-year
> low, and almost all of the drop traces to a single organisation. September spending hit a
> five-year high. And I built a ranking that I'll then show you why not to trust."

Then move on. Do not read the cards aloud — they are there to be seen.

---

## Page 2 · Growth is mostly inflation — 60 seconds

> "The headline number is 22.9% growth. In constant dollars it's 4.3%. About $118 billion of that
> $145 billion increase is the price level, not more goods and services.
>
> I lead with this because any statement about federal spending growth that doesn't name a
> deflator is really describing inflation. Everything after this page is inflation-adjusted."

**[5-min version: keep this. It sets the standard of care for everything else.]**

---

## Page 3 · Competition fell — 90 seconds

> "The share of contract dollars awarded competitively fell from 70.3% to 66.3% — the biggest
> one-year drop in the window. In dollars, non-competed obligations went from $220 billion to
> $263 billion.
>
> Now, that could mean two completely different things. Either agencies genuinely competed less of
> their own work, or the budget just shifted toward agencies that were never very competitive.
> Those call for opposite responses, so I didn't guess — I separated them."

Pause here. This sets up the next page, which is the payoff.

---

## Page 4 · One department, then one service — 2 minutes ★

**This is the page to spend time on.**

> "It's behaviour, not budget mix. And it's concentrated: the Department of Defense accounts for
> 93% of the government-wide decline.
>
> But 'Defense' is 40 organisations, and departments don't actually award contracts — the services
> inside them do. So I ran the same decomposition one level down. Three-quarters of the Defense
> move is the **Navy**: its competed share fell from 45.8% to 36.6%, on $176 billion of spending.
>
> Look at the bottom chart — the Air Force moved in the *opposite* direction over the same period.
> That's what makes this a Navy question rather than a defence-wide one, and it's completely
> invisible at department level.
>
> Chaining the two steps, the Navy alone explains roughly 70% of the entire government-wide
> decline. If it had simply held its prior-year rate, $16 billion more would have been competed."

**If asked how the decomposition works:**

> "It's shift-share. The overall rate is a spending-weighted average of agency rates, so a change
> in it comes from three sources: agencies changing their own rates, weights moving between
> agencies, and the interaction. The three terms sum to the observed change exactly — the residual
> is 1e-17, which is floating-point zero. That's what makes it an attribution rather than a story."

**[5-min version: this page plus page 5. If you only show two things, show these.]**

---

## Page 5 · Testing the objection — 2 minutes ★

> "The obvious pushback is: Defense buys harder things. There's one supplier for a submarine
> reactor. That's a fair objection — and it's testable, so I tested it.
>
> I used direct standardisation, which is the same technique used to compare mortality rates
> across countries with different age structures. You hold the product mix constant at the
> government-wide basket and let only the within-category rates vary. That answers: what would
> this agency's rate be if it bought what everyone else buys?
>
> Defense goes from 50.9% to 57.0%. The civilian median is 80.5%. So its product mix explains
> about 6 points of the gap — the objection is real. But 23.5 points survives, which is Defense
> competing less than other agencies *on the same kinds of purchases*.
>
> I'd flag that product categories are coarse, so I'd treat 23.5 as an upper bound rather than a
> point estimate."

That last sentence matters. Volunteering the bound before anyone asks is the difference between
confident and overclaiming.

---

## Page 6 · The year-end surge — 60 seconds

> "Federal funding expires on September 30, and you can see the result. September carried 19% of
> the year's contract dollars against the 8.3% an even pace would give — about $83 billion above
> pace, the highest in five years.
>
> I want to be careful here: this is not a finding, it's a sampling frame. Programme cycles
> genuinely land at year end. What makes the population interesting is that awards written against
> an expiring appropriation are where schedule pressure is highest — so that's where I'd sample
> first, not where I'd allege anything."

---

## Page 7 · FY2025 split the government — 45 seconds

> "Underneath a 5% government-wide move, the agency-level changes were unusually large and
> unusually one-directional. Defense, Veterans Affairs and Homeland Security grew. Health and Human
> Services fell 29%, USAID 45%.
>
> Housing and Urban Development actually ended the year net negative — it cancelled more contract
> value than it awarded, which doesn't happen anywhere else in the window."

---

## Page 8 · The ranking, and its uncertainty — 90 seconds ★

> "I built a composite efficiency index across five dimensions. The problem with any index like
> this is that the weights are a judgment call — and someone can always ask why you weighted
> competition at 30% instead of 40%.
>
> So rather than defend one weighting, I re-scored every agency 2,000 times under randomly drawn
> weights. Those error bars are the 5th to 95th percentile of each agency's score across all of
> them.
>
> Only 4 of 19 agencies hold their quartile. So the honest read is: the top and the bottom are
> real, and the middle is not separable — where those bars overlap, the ranking carries no
> information. I'd use this as a triage device for where to look first, not as a scorecard."

**If asked why publish it at all:** "Because the tails are genuinely informative, and because an
index with its uncertainty attached is more useful than one that looks more authoritative than the
evidence supports."

---

## Page 9 · Recommendations — 2 minutes

Walk R1, R2 and R5, then point at the rest.

> "Six recommendations, ordered by what the review effort would teach rather than by dollar size.
>
> **R1** is the reporting change: measure competition at the level that actually awards contracts.
> A department-level metric averaged the Navy's nine-point fall against the Air Force's rise and
> reported 'Defense declined', which sends the question to 40 organisations when 39 of them didn't
> cause it.
>
> **R2** is to use the portfolio-adjusted rate as the comparison basis, because it removes the
> single most common objection before it's raised.
>
> **R5** is a recommendation against my own index — use the tails, don't rank the middle.
>
> Every one of these states what evidence would prove it wrong, and R6 is deliberately marked
> low-confidence because the underlying vendor data isn't good enough to act on yet."

---

## Page 10 · Limitations — 60 seconds

Do not rush this page or apologise for it.

> "Two things I want to be explicit about.
>
> First, nothing here identifies waste, fraud or abuse. Sole-source contracts are frequently lawful
> and correct, and some work genuinely requires cost-reimbursement. Everything in this deck points
> to where a reviewer would learn the most — not to wrongdoing.
>
> Second, there's no savings number in this deck, and that's deliberate. Competition affects price,
> but this analysis observes obligations, not prices. Converting any of these figures into a
> savings claim would go past what the data can carry."

---

## Optional page 11 · Method and data quality — 60 seconds

Use if the audience is technical or if someone asks "how do you know this is right?"

> "Twelve automated data-quality checks run every time the pipeline builds, and they fail the build
> if they break. The important one is reconciliation: the competition table is assembled from nine
> separate API calls per agency-year, so if those pieces don't add back up to the independently
> retrieved total, something is wrong. All 325 agency-years reconcile within 1%.
>
> Two of those checks caught real bugs before publication. One was a government API that silently
> truncates its results — it had dropped Interior's largest component and left the totals 33%
> short. The other was a calculation that could return a competition rate above 100% because the
> numerator and denominator came from separate queries. Both are documented in the repo rather than
> quietly patched."

---

## Questions you should expect

**"Why the API instead of the bulk files?"**
> "The bulk archive is tens of gigabytes per fiscal year. The API computes the same aggregations
> server-side, which means anyone can clone the repo and reproduce every number offline in about
> two seconds — every API response is cached and committed. For the three measures the API can't
> provide, the bulk path is implemented but not required."

**"How current is this?"**
> "FY2025 is complete — it closed on September 30 and this snapshot is well past the settlement
> window. FPDS data does get corrected continuously, so the snapshot date is recorded with the
> data."

**"Could a few large awards explain the Navy drop?"**
> "That's the right question, and it's the first thing I'd check — it's written into the
> recommendation as the falsification test. If the drop is three shipbuilding awards it's a
> lumpiness artefact, not a trend. Answering it needs award-level data, which is the bulk path."

**"What would you do next?"**
> "Compare the September population's competition rate against the same agency's rest-of-year
> baseline. That turns the timing observation into either a process finding or a retired
> hypothesis, and it's about sixty API calls. It's written up as recommendation R3."

**"How long did this take?"**
> Be honest, and emphasise that the pipeline is reusable — pointing it at a new fiscal year or a
> different award type is a config change, not a rebuild.

---

## Delivery notes

- **Lead with the finding, not the method.** Say "the Navy caused 70% of it", then explain how you
  know. Reversing that order loses the room.
- **Say the caveat before you're asked.** Volunteering the upper bound on page 5 reads as
  confidence; conceding it under questioning reads as having been caught.
- **Do not read the numbers off the slide.** They are on screen. Say what they mean.
- **The two pages that differentiate this work are 4 and 8** — the attribution chain and the
  uncertainty on the ranking. If time gets cut, protect those.
