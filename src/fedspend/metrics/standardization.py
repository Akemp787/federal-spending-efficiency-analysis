"""Portfolio-adjusted rates via direct standardisation.

The problem
-----------
Comparing one agency's competition rate to another's compares *what they buy* at
least as much as *how they buy it*. An agency procuring nuclear propulsion
systems has a handful of qualified sources; an agency procuring office furniture
has hundreds. No amount of contracting reform closes that gap, so a raw
league table of competition rates partly ranks mission, not management.

The fix is the technique epidemiology uses to compare mortality across
populations with different age structures: **direct standardisation**. Hold the
product mix constant at a common reference, and let only the within-category
rates vary.

    observed rate      R_a  = sum_s ( w_as * r_as )
    standardised rate  R*_a = sum_s ( W_s  * r_as )

where ``w_as`` is agency *a*'s own share of spend in product category *s*,
``W_s`` is the reference (government-wide) share, and ``r_as`` is the agency's
competition rate within that category.

The difference between the two decomposes the agency's position:

* ``portfolio_effect = R_a - R*_a`` — the part of the observed rate attributable
  to *what* the agency buys.
* ``R*_a`` — what the agency's rate would be if it bought the government's
  basket, which is the number that compares practice to practice.

Reading it
----------
An agency whose standardised rate is far above its observed rate is competing
well within hard categories, and its low headline number is mostly mission. An
agency whose two rates are close cannot explain its position by what it buys.

Coverage caveat
---------------
Where an agency has no spend in a reference category its within-category rate is
undefined. Reference weights are renormalised over the categories the agency
actually participates in, and ``reference_coverage`` reports how much of the
reference basket that represents. A standardised rate built on thin coverage is
reported but should not be ranked.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

#: Federal Product and Service Code groups, keyed by the first character.
#: Letters are services (A is research and development); digits are the Federal
#: Supply Classification, i.e. products and equipment.
PSC_CATEGORY = {
    "A": "R&D",
    "B": "Special studies & analysis",
    "C": "Architecture & engineering",
    "D": "IT & telecommunications",
    "E": "Purchase of structures",
    "F": "Natural resources & conservation",
    "G": "Social services",
    "H": "Quality control & testing",
    "J": "Equipment maintenance & repair",
    "K": "Equipment modification",
    "L": "Technical representative services",
    "M": "Facility operation",
    "N": "Equipment installation",
    "P": "Salvage",
    "Q": "Medical services",
    "R": "Professional & management support",
    "S": "Utilities & housekeeping",
    "T": "Media & publications",
    "U": "Education & training",
    "V": "Transportation & travel",
    "W": "Equipment lease & rental",
    "X": "Facility lease & rental",
    "Y": "Construction of structures",
    "Z": "Maintenance & repair of structures",
}

#: Coarse roll-up, used when fine categories leave too many thin cells.
PSC_GROUP = {
    "A": "Research & development",
    "Y": "Construction",
    "Z": "Construction",
    "E": "Construction",
}


def psc_category(code: object) -> str:
    """Map a Product and Service Code to its category name."""
    if code is None or (isinstance(code, float) and np.isnan(code)):
        return "Unclassified"
    text = str(code).strip().upper()
    if not text:
        return "Unclassified"
    head = text[0]
    if head.isdigit():
        return "Products & equipment"
    return PSC_CATEGORY.get(head, "Unclassified")


def psc_group(code: object) -> str:
    """Coarse roll-up: R&D, construction, products, or services."""
    if code is None:
        return "Unclassified"
    text = str(code).strip().upper()
    if not text:
        return "Unclassified"
    head = text[0]
    if head.isdigit():
        return "Products & equipment"
    return PSC_GROUP.get(head, "Services")


def prepare_strata(
    df: pd.DataFrame,
    *,
    code_col: str = "psc_code",
    coarse: bool = False,
    min_stratum_share: float = 0.005,
) -> pd.DataFrame:
    """Attach a stratum label, folding negligible categories into 'Other'.

    ``min_stratum_share`` is measured against total reference spend. Categories
    below it carry too little money for a within-category rate to be stable, and
    a standardised rate is only as trustworthy as its thinnest weighted cell.
    """
    out = df.copy()
    labeller = psc_group if coarse else psc_category
    out["stratum"] = out[code_col].map(labeller)

    totals = out.groupby("stratum")["obligations"].sum()
    share = totals.clip(lower=0) / totals.clip(lower=0).sum()
    keep = set(share[share >= min_stratum_share].index)
    out["stratum"] = np.where(out["stratum"].isin(keep), out["stratum"], "Other")
    return out


def standardise_rate(
    df: pd.DataFrame,
    *,
    group_col: str = "agency_name",
    stratum_col: str = "stratum",
    numerator_col: str = "competed_obligations",
    denominator_col: str = "obligations",
    reference: pd.Series | None = None,
) -> pd.DataFrame:
    """Direct standardisation of a rate across strata.

    ``reference`` is a Series of stratum weights summing to one. When omitted it
    is derived from the pooled data, which makes the government-wide basket the
    reference and leaves the spend-weighted average of the standardised rates
    close to the government-wide observed rate.
    """
    work = df.copy()
    work[denominator_col] = work[denominator_col].clip(lower=0)
    work[numerator_col] = work[numerator_col].clip(lower=0)

    cells = (
        work.groupby([group_col, stratum_col], as_index=False)[
            [numerator_col, denominator_col]
        ]
        .sum()
    )
    cells["rate"] = (cells[numerator_col] / cells[denominator_col]).where(
        cells[denominator_col] > 0
    )

    # The numerator and denominator come from two separate API queries, and
    # clipping de-obligations to zero can leave a cell whose competed subtotal
    # exceeds its own total. Such a cell yields a rate above 1, which propagates
    # into a standardised rate above 100% - arithmetically produced, physically
    # impossible. Those cells are dropped rather than clamped: a clamp would
    # silently keep a value known to be wrong, and the count is reported so the
    # reader can see how much was discarded.
    tolerance = 1.01
    inconsistent = cells["rate"] > tolerance
    cells["is_inconsistent"] = inconsistent
    cells.loc[inconsistent, "rate"] = np.nan
    # Rounding can still leave a cell a hair over 1.0; that is a representation
    # artefact rather than a data problem, so it is clamped.
    cells["rate"] = cells["rate"].clip(upper=1.0)

    if reference is None:
        ref_totals = work.groupby(stratum_col)[denominator_col].sum()
        reference = ref_totals / ref_totals.sum()
    reference = reference.rename("reference_weight")

    cells = cells.merge(reference, left_on=stratum_col, right_index=True, how="left")
    cells["reference_weight"] = cells["reference_weight"].fillna(0.0)

    records = []
    for name, grp in cells.groupby(group_col):
        usable = grp[grp["rate"].notna() & (grp[denominator_col] > 0)]
        total = usable[denominator_col].sum()
        if total <= 0:
            continue

        observed = float((usable[denominator_col] / total * usable["rate"]).sum())

        ref_mass = usable["reference_weight"].sum()
        if ref_mass > 0:
            weights = usable["reference_weight"] / ref_mass
            standardised = float((weights * usable["rate"]).sum())
        else:
            standardised = float("nan")

        records.append(
            {
                group_col: name,
                "observed_rate": observed,
                "standardised_rate": standardised,
                "portfolio_effect": observed - standardised,
                "reference_coverage": float(ref_mass),
                "strata_observed": int(len(usable)),
                "strata_dropped_inconsistent": int(grp["is_inconsistent"].sum()),
                "obligations": float(total),
            }
        )

    out = pd.DataFrame(records)
    if out.empty:
        return out
    # Dollars the agency would gain or lose if its practice matched its basket.
    out["dollars_explained_by_portfolio"] = out["portfolio_effect"] * out["obligations"]
    return out.sort_values("standardised_rate", ascending=False).reset_index(drop=True)


def stratum_detail(
    df: pd.DataFrame,
    *,
    group_col: str = "agency_name",
    stratum_col: str = "stratum",
    numerator_col: str = "competed_obligations",
    denominator_col: str = "obligations",
) -> pd.DataFrame:
    """Within-stratum rates and weights, so any standardised rate can be opened up."""
    work = df.copy()
    work[denominator_col] = work[denominator_col].clip(lower=0)
    work[numerator_col] = work[numerator_col].clip(lower=0)

    cells = work.groupby([group_col, stratum_col], as_index=False)[
        [numerator_col, denominator_col]
    ].sum()
    cells["rate"] = (cells[numerator_col] / cells[denominator_col]).where(
        cells[denominator_col] > 0
    )
    group_totals = cells.groupby(group_col)[denominator_col].transform("sum")
    cells["own_weight"] = cells[denominator_col] / group_totals

    ref = work.groupby(stratum_col)[denominator_col].sum()
    ref = (ref / ref.sum()).rename("reference_weight")
    cells = cells.merge(ref, left_on=stratum_col, right_index=True, how="left")

    gov_rate = (
        work.groupby(stratum_col)[numerator_col].sum()
        / work.groupby(stratum_col)[denominator_col].sum()
    ).rename("government_rate")
    cells = cells.merge(gov_rate, left_on=stratum_col, right_index=True, how="left")
    cells["rate_vs_government_pp"] = (cells["rate"] - cells["government_rate"]) * 100.0
    return cells.sort_values([group_col, denominator_col], ascending=[True, False])
