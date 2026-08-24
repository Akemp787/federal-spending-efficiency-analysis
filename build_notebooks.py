"""Generate and execute the analysis notebooks.

Notebooks are built from source here rather than hand-edited so that their
outputs are always consistent with the curated data, and so a rebuild after a
data refresh is one command rather than a manual re-run of three files.

    python build_notebooks.py

This script is a build tool, not part of the ``fedspend`` package.
"""

from __future__ import annotations

from pathlib import Path

import nbformat as nbf
from nbclient import NotebookClient

ROOT = Path(__file__).resolve().parent
NB_DIR = ROOT / "notebooks"

PRELUDE = """\
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

ROOT = Path.cwd().parent if Path.cwd().name == "notebooks" else Path.cwd()
sys.path.insert(0, str(ROOT / "src"))

pd.set_option("display.width", 190)
pd.set_option("display.max_columns", 60)
pd.set_option("display.float_format", lambda v: f"{v:,.3f}")

# Categorical slots validated for colour-vision-deficiency separation and
# contrast against a light surface (see the project's dataviz palette).
BLUE, ORANGE, AQUA, RED = "#2a78d6", "#eb6834", "#1baf7a", "#e34948"
plt.rcParams.update({
    "figure.figsize": (10, 4.4), "figure.dpi": 110,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.alpha": 0.25, "grid.linewidth": 0.7,
    "axes.titlesize": 12, "axes.titleweight": "semibold",
    "font.size": 10, "axes.labelsize": 10,
})

CURATED = ROOT / "data" / "curated"
SAMPLES = ROOT / "data" / "samples"

def load(name):
    \"\"\"Read a curated table, falling back to the committed sample CSV.\"\"\"
    parquet = CURATED / f"{name}.parquet"
    if parquet.exists():
        return pd.read_parquet(parquet)
    return pd.read_csv(SAMPLES / f"{name}.csv")

print("pandas", pd.__version__, "| numpy", np.__version__)
"""


def md(text: str) -> nbf.NotebookNode:
    return nbf.v4.new_markdown_cell(text)


def code(text: str) -> nbf.NotebookNode:
    return nbf.v4.new_code_cell(text)


# ---------------------------------------------------------------------------
def notebook_01() -> nbf.NotebookNode:
    nb = nbf.v4.new_notebook()
    nb.cells = [
        md(
            "# 01 · Pipeline walkthrough\n\n"
            "How raw USAspending responses become the analytical tables the findings rest on, "
            "and the evidence that the transformation is correct.\n\n"
            "**Stages:** `ingest → analyse → warehouse → validate → report`\n\n"
            "Every stage reads the previous stage from disk, so any stage can be re-run alone. "
            "See [`docs/METHODOLOGY.md`](../docs/METHODOLOGY.md) for the reasoning behind each "
            "analytical choice."
        ),
        code(PRELUDE),
        md(
            "## 1. Configuration is data, not code\n\n"
            "Every judgement call — which FPDS codes count as competed, how pricing types map to "
            "risk buckets, the materiality floor, the index weights — lives in "
            "`config/pipeline.yml`. A reviewer can change an assumption and re-run without "
            "reading the implementation."
        ),
        code(
            "from fedspend.config import Config\n\n"
            "cfg = Config.load(ROOT / 'config' / 'pipeline.yml')\n"
            "print('fiscal years      :', cfg.fiscal_years)\n"
            "print('award types       :', cfg.award_type_codes)\n"
            "print('competed codes    :', cfg.competed_codes)\n"
            "print('not-competed codes:', cfg.not_competed_codes)\n"
            "print('materiality floor : ${:,.0f}'.format(cfg['analysis']['materiality_floor_usd']))\n"
            "print()\n"
            "print('index weights:')\n"
            "for dim, w in cfg['efficiency_index']['weights'].items():\n"
            "    print(f'  {dim:<18} {w:.2f}')"
        ),
        md(
            "### The `E` decision\n\n"
            "FPDS code `E` is *follow-on to competed action*. The parent award was competed; this "
            "action was not. Agencies differ on the convention, so the project follows the "
            "FPDS-NG treatment (E = not competed) **and** re-runs the whole index under the "
            "opposite convention in the sensitivity analysis. It is a config value, not a "
            "constant buried in a function."
        ),
        code(
            "buckets = pd.Series(cfg.pricing_bucket_by_code).rename('risk_bucket')\n"
            "labels = {str(c): l for b in cfg['pricing_risk'].values() for c, l in b.items()}\n"
            "pd.DataFrame({'label': pd.Series(labels), 'risk_bucket': buckets}).sort_values('risk_bucket')"
        ),
        md(
            "## 2. Inflation adjustment\n\n"
            "The GDP implicit price deflator, not CPI-U: the subject is government purchases of "
            "goods and services, not a household basket. A fiscal-year deflator is the mean of "
            "the four calendar quarters beginning October of the prior year — exactly the federal "
            "fiscal year, with no interpolation."
        ),
        code(
            "deflator = pd.read_parquet(CURATED.parent / 'interim' / 'deflator_fy.parquet') \\\n"
            "    if (CURATED.parent / 'interim' / 'deflator_fy.parquet').exists() else None\n"
            "if deflator is None:\n"
            "    gov = load('gov_summary')\n"
            "    deflator = gov[['fiscal_year', 'real_multiplier']]\n"
            "deflator"
        ),
        code(
            "gov = load('gov_summary').sort_values('fiscal_year')\n"
            "cum = (gov['real_multiplier'].iloc[0] - 1) * 100\n"
            "print(f'Cumulative FY{gov.fiscal_year.iloc[0]}-FY{gov.fiscal_year.iloc[-1]} inflation: {cum:.1f}%')\n"
            "print('A nominal increase smaller than this is a real DECREASE.')"
        ),
        md(
            "## 3. Reconciliation — the check that makes the rest trustworthy\n\n"
            "The competition table is assembled from **nine separate API calls per agency-year**, "
            "one per FPDS extent-competed code. The pricing table comes from sixteen. If those "
            "slices do not sum back to the independently retrieved agency total, the extraction "
            "is wrong and every downstream figure is suspect.\n\n"
            "This is the single most important cell in the project."
        ),
        code(
            "interim = CURATED.parent / 'interim'\n"
            "if (interim / 'agency_fy.parquet').exists():\n"
            "    agency = pd.read_parquet(interim / 'agency_fy.parquet')\n"
            "    comp = pd.read_parquet(interim / 'agency_fy_competition.parquet')\n"
            "    sliced = comp.groupby(['fiscal_year','agency_name'], as_index=False)['obligations'].sum()\n"
            "    m = agency.merge(sliced, on=['fiscal_year','agency_name'], suffixes=('_total','_sliced'))\n"
            "    m = m[m['obligations_total'].abs() > 1e6]\n"
            "    m['rel_diff'] = (m.obligations_sliced - m.obligations_total) / m.obligations_total\n"
            "    print(f'agency-years checked      : {len(m)}')\n"
            "    print(f'max |relative difference| : {m.rel_diff.abs().max():.2e}')\n"
            "    print(f'breaches of 1% tolerance  : {(m.rel_diff.abs() > 0.01).sum()}')\n"
            "else:\n"
            "    print('interim extracts not present - run `make ingest` to reproduce this check')"
        ),
        md(
            "The residual difference comes from transactions USAspending assigns a null "
            "extent-competed code, which no code-filtered query returns. That is why the contract "
            "uses a 1% tolerance rather than demanding exact equality — and why the tolerance is "
            "stated rather than tuned until it passed."
        ),
        md("## 4. The full validation suite"),
        code(
            "report = ROOT / 'outputs' / 'tables' / 'validation_report.csv'\n"
            "if report.exists():\n"
            "    display(pd.read_csv(report)[['name','passed','severity','message']])\n"
            "else:\n"
            "    print('run `make validate` to generate the report')"
        ),
        md(
            "## 5. What comes out\n\n"
            "21 curated tables. `fact_agency_year` is the centre of the model: one row per "
            "agency per fiscal year carrying every derived measure."
        ),
        code(
            "fact = load('fact_agency_year_material') if not (CURATED/'fact_agency_year.parquet').exists() \\\n"
            "       else load('fact_agency_year')\n"
            "print(f'{len(fact)} rows x {fact.shape[1]} columns')\n"
            "print()\n"
            "for c in fact.columns:\n"
            "    print(' ', c)"
        ),
        code(
            "cols = ['fiscal_year','agency_name','obligations','obligations_real',\n"
            "        'competed_share','government_risk_share','september_share','vendor_hhi']\n"
            "fact[fact.fiscal_year == fact.fiscal_year.max()].nlargest(10, 'obligations')[cols]"
        ),
    ]
    return nb


def notebook_02() -> nbf.NotebookNode:
    nb = nbf.v4.new_notebook()
    nb.cells = [
        md(
            "# 02 · Findings\n\n"
            "The analysis. Each section states a claim, shows the evidence, and says what the "
            "claim does **not** support.\n\n"
            "Full narrative: [`docs/EXECUTIVE_SUMMARY.md`](../docs/EXECUTIVE_SUMMARY.md)"
        ),
        code(PRELUDE),
        code(
            "gov = load('gov_summary').sort_values('fiscal_year')\n"
            "fact = load('fact_agency_year') if (CURATED/'fact_agency_year.parquet').exists() \\\n"
            "       else load('fact_agency_year_material')\n"
            "first, last, prev = gov.iloc[0], gov.iloc[-1], gov.iloc[-2]\n"
            "BASE, LATEST = int(first.fiscal_year), int(last.fiscal_year)\n"
            "print(f'window FY{BASE}-FY{LATEST} | total obligations ${gov.obligations.sum()/1e12:.2f}T')"
        ),
        md(
            "## Finding 1 — Most of the growth is the price level\n\n"
            "A statement about federal spending 'growth' that does not name a deflator is "
            "describing inflation."
        ),
        code(
            "nom = (last.obligations / first.obligations - 1) * 100\n"
            "real = (last.obligations_real / first.obligations_real - 1) * 100\n"
            "price_only = last.obligations - first.obligations * (last.obligations_real / first.obligations_real)\n"
            "print(f'FY{BASE} -> FY{LATEST}')\n"
            "print(f'  nominal growth : {nom:+.2f}%   (${first.obligations/1e9:,.1f}B -> ${last.obligations/1e9:,.1f}B)')\n"
            "print(f'  real growth    : {real:+.2f}%   (constant FY{LATEST} dollars)')\n"
            "print(f'  price level    : ${price_only/1e9:,.1f}B of the ${(last.obligations-first.obligations)/1e9:,.1f}B increase')"
        ),
        code(
            "fig, ax = plt.subplots()\n"
            "x = gov.fiscal_year.astype(int)\n"
            "ax.plot(x, gov.obligations_index_vs_base, 'o-', color=BLUE, lw=2, label='Nominal dollars')\n"
            "ax.plot(x, gov.obligations_real_index_vs_base, 'o-', color=ORANGE, lw=2,\n"
            "        label=f'Constant FY{LATEST} dollars')\n"
            "ax.axhline(100, color='#999', ls='--', lw=1)\n"
            "for series, colour in ((gov.obligations_index_vs_base, BLUE),\n"
            "                       (gov.obligations_real_index_vs_base, ORANGE)):\n"
            "    ax.annotate(f'{series.iloc[-1]:.1f}', (x.iloc[-1], series.iloc[-1]),\n"
            "                textcoords='offset points', xytext=(8, -3), color=colour, weight='bold')\n"
            "ax.set(title=f'Federal contract obligations indexed to FY{BASE} = 100',\n"
            "       xlabel='Fiscal year', ylabel='Index')\n"
            "ax.set_xticks(x); ax.legend(frameon=False)\n"
            "plt.tight_layout(); plt.show()"
        ),
        md(
            "## Finding 2 — Competition fell, and the decomposition says why\n\n"
            "Two explanations carry opposite management implications:\n\n"
            "* **within** — agencies competed less of their own work (behavioural)\n"
            "* **mix** — dollars moved toward agencies that were already less competitive "
            "(compositional)\n\n"
            "Shift-share separates them exactly. `S = Σ wᵢ·sᵢ`, and\n\n"
            "```\n"
            "ΔS = Σ wᵢ⁰·Δsᵢ  +  Σ Δwᵢ·(sᵢ⁰ − S⁰)  +  Σ Δwᵢ·Δsᵢ\n"
            "     within          mix                 interaction\n"
            "```"
        ),
        code(
            "from fedspend.metrics.decomposition import shift_share, shift_share_series\n\n"
            "d = fact[['fiscal_year','agency_name','obligations','competed_share']].dropna(subset=['competed_share'])\n"
            "contrib, summ = shift_share(d, group_col='agency_name', weight_col='obligations',\n"
            "                            rate_col='competed_share', base_period=LATEST-1, latest_period=LATEST)\n"
            "print(f'FY{LATEST-1} competed share : {summ[\"rate_base\"]*100:.2f}%')\n"
            "print(f'FY{LATEST} competed share : {summ[\"rate_latest\"]*100:.2f}%')\n"
            "print(f'total change          : {summ[\"total_change\"]*100:+.2f} pp')\n"
            "print()\n"
            "print(f'  within effect       : {summ[\"within_effect\"]*100:+.2f} pp   (behaviour)')\n"
            "print(f'  mix effect          : {summ[\"mix_effect\"]*100:+.2f} pp   (composition)')\n"
            "print(f'  interaction         : {summ[\"interaction_effect\"]*100:+.2f} pp')\n"
            "print(f'  residual            : {summ[\"reconciliation_residual\"]:.2e}  <- exact')"
        ),
        md(
            "**The residual is zero to floating-point precision.** The three terms account for "
            "the entire observed change, which is what makes this an attribution rather than a "
            "narrative."
        ),
        code(
            "top = contrib.reindex(contrib.total_effect.abs().sort_values(ascending=False).index).head(8)\n"
            "out = pd.DataFrame({\n"
            "    'agency': top.agency_name,\n"
            "    f'weight FY{LATEST-1} %': (top.w_0*100).round(1),\n"
            "    f'weight FY{LATEST} %': (top.w_1*100).round(1),\n"
            "    f'competed FY{LATEST-1} %': (top.s_0*100).round(1),\n"
            "    f'competed FY{LATEST} %': (top.s_1*100).round(1),\n"
            "    'within pp': (top.within_effect*100).round(2),\n"
            "    'mix pp': (top.mix_effect*100).round(2),\n"
            "    'total pp': (top.total_effect*100).round(2),\n"
            "})\n"
            "out.reset_index(drop=True)"
        ),
        code(
            "fig, ax = plt.subplots(figsize=(10, 4.6))\n"
            "t = top.sort_values('total_effect')\n"
            "vals = (t.total_effect*100).values\n"
            "ax.barh(range(len(t)), vals, color=[BLUE if v >= 0 else RED for v in vals], height=.6)\n"
            "ax.set_yticks(range(len(t))); ax.set_yticklabels(t.agency_name, fontsize=9)\n"
            "ax.axvline(0, color='#666', lw=1.2)\n"
            "for i, v in enumerate(vals):\n"
            "    ax.annotate(f'{v:+.2f}', (v, i), textcoords='offset points',\n"
            "                xytext=(6 if v >= 0 else -6, -3), ha='left' if v >= 0 else 'right', fontsize=9)\n"
            "ax.set(title=f'Contribution to the FY{LATEST} change in competed share (pp)', xlabel='Percentage points')\n"
            "ax.grid(axis='y', alpha=0)\n"
            "plt.tight_layout(); plt.show()"
        ),
        code(
            "series = shift_share_series(d, group_col='agency_name', weight_col='obligations',\n"
            "                            rate_col='competed_share')\n"
            "s = series.copy()\n"
            "for c in ['rate_base','rate_latest','total_change','within_effect','mix_effect','interaction_effect']:\n"
            "    s[c] = (s[c]*100).round(2)\n"
            "s[['base_period','latest_period','rate_base','rate_latest','total_change',\n"
            "   'within_effect','mix_effect','interaction_effect']].astype({'base_period':int,'latest_period':int})"
        ),
        md(
            "> **What this does not show.** Non-competed dollars are not improper dollars. "
            "Sole-source awards are frequently lawful and correct. What the measure gives an "
            "oversight function is the size of the population where no market test occurred."
        ),
        md("## Finding 3 — Year-end concentration"),
        code(
            "season = load('monthly_seasonality')\n"
            "latest_season = season[season.fiscal_year == LATEST].sort_values('fiscal_month')\n"
            "fig, ax = plt.subplots()\n"
            "colours = [ORANGE if m == 12 else BLUE for m in latest_season.fiscal_month]\n"
            "ax.bar(range(12), latest_season.index_vs_even_pace, color=colours, width=.66)\n"
            "ax.axhline(100, color='#666', ls='--', lw=1.2)\n"
            "ax.annotate('even monthly pace', (11.4, 103), ha='right', fontsize=9, color='#666')\n"
            "ax.annotate(f'{latest_season.index_vs_even_pace.iloc[-1]:.0f}',\n"
            "            (11, latest_season.index_vs_even_pace.iloc[-1]), textcoords='offset points',\n"
            "            xytext=(0, 6), ha='center', color=ORANGE, weight='bold')\n"
            "ax.set_xticks(range(12)); ax.set_xticklabels(latest_season.month_name)\n"
            "ax.set(title=f'FY{LATEST} obligations by month, indexed to an even pace (100)', ylabel='Index')\n"
            "plt.tight_layout(); plt.show()"
        ),
        code(
            "t = gov[['fiscal_year','september_share','q4_share','surge_ratio','september_excess_obligations']].copy()\n"
            "t['september %'] = (t.september_share*100).round(2)\n"
            "t['Q4 %'] = (t.q4_share*100).round(2)\n"
            "t['surge ratio'] = t.surge_ratio.round(2)\n"
            "t['$B above even pace'] = (t.september_excess_obligations/1e9).round(1)\n"
            "t[['fiscal_year','september %','Q4 %','surge ratio','$B above even pace']].astype({'fiscal_year':int})"
        ),
        md(
            "> **What this does not show.** Programme cycles genuinely land at year end. "
            "September concentration is a *risk indicator* that identifies a population worth "
            "sampling — awards written against an expiring appropriation, where schedule pressure "
            "is highest — not evidence that any individual award was improper."
        ),
        md("## Finding 4 — The FY2025 composition shift"),
        code(
            "m = fact[fact.fiscal_year == LATEST].copy()\n"
            "m = m[m.prior_year.notna() & (m.prior_year.abs() > 1e9)]\n"
            "m['change_bn'] = m.change_abs / 1e9\n"
            "m = m.reindex(m.change_bn.abs().sort_values(ascending=False).index).head(12).sort_values('change_bn')\n"
            "fig, ax = plt.subplots(figsize=(10, 5))\n"
            "ax.barh(range(len(m)), m.change_bn, color=[BLUE if v >= 0 else RED for v in m.change_bn], height=.62)\n"
            "ax.set_yticks(range(len(m))); ax.set_yticklabels(m.agency_name, fontsize=9)\n"
            "ax.axvline(0, color='#666', lw=1.2)\n"
            "for i, v in enumerate(m.change_bn):\n"
            "    ax.annotate(f'{v:+,.1f}', (v, i), textcoords='offset points',\n"
            "                xytext=(6 if v >= 0 else -6, -3), ha='left' if v >= 0 else 'right', fontsize=9)\n"
            "ax.set(title=f'Change in contract obligations, FY{LATEST-1} to FY{LATEST} ($B)', xlabel='$ billions')\n"
            "ax.grid(axis='y', alpha=0)\n"
            "plt.tight_layout(); plt.show()"
        ),
        code(
            "cols = {'agency_name':'agency','prior_year':f'FY{LATEST-1} $B','obligations':f'FY{LATEST} $B',\n"
            "        'change_abs':'change $B','change_pct':'nominal %','change_pct_real':'real %'}\n"
            "t = m.sort_values('change_bn')[list(cols)].rename(columns=cols)\n"
            "for c in [f'FY{LATEST-1} $B', f'FY{LATEST} $B', 'change $B']:\n"
            "    t[c] = (t[c]/1e9).round(2)\n"
            "t.round(2).reset_index(drop=True)"
        ),
        md(
            "Concentration moved with it — the market got less distributed, not more:"
        ),
        code(
            "c = gov[['fiscal_year','agency_hhi','agency_cr4','agency_cr10']].copy()\n"
            "c['agency HHI'] = c.agency_hhi.round(0)\n"
            "c['top 4 share %'] = (c.agency_cr4*100).round(1)\n"
            "c['top 10 share %'] = (c.agency_cr10*100).round(1)\n"
            "c[['fiscal_year','agency HHI','top 4 share %','top 10 share %']].astype({'fiscal_year':int})"
        ),
    ]
    return nb


def notebook_03() -> nbf.NotebookNode:
    nb = nbf.v4.new_notebook()
    nb.cells = [
        md(
            "# 03 · The Contract Efficiency Index\n\n"
            "Building a composite index, and then doing the work that decides whether anyone "
            "should believe it.\n\n"
            "A composite index carries three well-known problems. This notebook builds the index "
            "and then attacks each one:\n\n"
            "1. **The weights are arbitrary** → re-score under 2,000 random weightings\n"
            "2. **Normalisation is scale-dependent** → winsorise before scaling\n"
            "3. **Aggregation hides the driver** → always return the sub-scores"
        ),
        code(PRELUDE),
        code(
            "from fedspend.config import Config\n"
            "from fedspend.metrics import efficiency_index as cei\n\n"
            "cfg = Config.load(ROOT / 'config' / 'pipeline.yml')\n"
            "idx = load('efficiency_index')\n"
            "sens = load('index_sensitivity')\n"
            "LATEST = int(cfg.latest_fy)\n"
            "print(f'{len(idx)} agencies scored on FY{LATEST}')\n"
            "print('dimensions:', ', '.join(cei.DIMENSIONS))"
        ),
        md(
            "## 1. The dimensions\n\n"
            "| Dimension | Raw measure (higher = more efficient) | Weight |\n"
            "|---|---|---:|\n"
            "| competition | share of obligations competed | 0.30 |\n"
            "| pricing_risk | 1 − government-risk share | 0.25 |\n"
            "| vendor_diversity | 1 − normalised vendor HHI | 0.20 |\n"
            "| spend_discipline | 1 − September share | 0.15 |\n"
            "| stability | 1 − real YoY growth volatility | 0.10 |\n\n"
            "**Population:** agencies with ≥ $1B in the scored year. Ranking a percentage "
            "computed on a $111M base against one computed on a $492B base is not a comparison."
        ),
        code(
            "raw_cols = [f'{d}_raw' for d in cei.DIMENSIONS]\n"
            "score_cols = [f'{d}_score' for d in cei.DIMENSIONS]\n"
            "idx.set_index('agency_name')[raw_cols].round(3).sort_values('competition_raw', ascending=False)"
        ),
        md(
            "## 2. Winsorise, then scale\n\n"
            "Min-max scaling is scale-dependent: one extreme agency compresses everyone else into "
            "a narrow band. Clipping each dimension to its own 5th/95th percentiles first stops a "
            "single outlier from setting the range for the whole field."
        ),
        code(
            "fig, axes = plt.subplots(1, 2, figsize=(11, 3.8))\n"
            "for ax, col, title in zip(axes, ['stability_raw','vendor_diversity_raw'],\n"
            "                          ['stability (−volatility)','vendor diversity (1 − nHHI)']):\n"
            "    v = idx[col].dropna()\n"
            "    w = cei.winsorize(v, 0.05, 0.95)\n"
            "    ax.scatter(v, [1]*len(v), color=BLUE, alpha=.75, s=42, label='raw')\n"
            "    ax.scatter(w, [0]*len(w), color=ORANGE, alpha=.75, s=42, label='winsorised')\n"
            "    ax.set_yticks([0,1]); ax.set_yticklabels(['winsorised','raw'])\n"
            "    ax.set_title(title); ax.grid(axis='y', alpha=0)\n"
            "axes[0].legend(frameon=False, fontsize=9)\n"
            "plt.tight_layout(); plt.show()"
        ),
        md("## 3. The scores"),
        code(
            "view = idx.set_index('agency_name')[score_cols + ['efficiency_index','rank']].sort_values('rank')\n"
            "view.round(1)"
        ),
        code(
            "fig, ax = plt.subplots(figsize=(10, 6))\n"
            "d = idx.sort_values('efficiency_index')\n"
            "s = sens.set_index('agency_name').reindex(d.agency_name)\n"
            "y = range(len(d))\n"
            "ax.barh(y, d.efficiency_index, color=BLUE, height=.62, zorder=2)\n"
            "ax.hlines(y, s.score_p05.values, s.score_p95.values, color='#666', lw=1.6, zorder=3)\n"
            "ax.scatter(s.score_p05.values, y, marker='|', color='#666', s=70, zorder=3)\n"
            "ax.scatter(s.score_p95.values, y, marker='|', color='#666', s=70, zorder=3)\n"
            "ax.set_yticks(list(y)); ax.set_yticklabels(d.agency_name, fontsize=9)\n"
            "ax.set(title=f'Contract Efficiency Index FY{LATEST}\\n(bar = configured weights; whisker = 5th–95th pct of 2,000 random weightings)',\n"
            "       xlabel='Index (0–100)')\n"
            "ax.grid(axis='y', alpha=0)\n"
            "plt.tight_layout(); plt.show()"
        ),
        md(
            "## 4. Do the ranks survive a different weighting?\n\n"
            "Weights are drawn from a flat Dirichlet — the uniform distribution over the simplex, "
            "so every weighting that sums to one is equally likely. If a rank moves twenty places "
            "across that distribution, the rank is an artefact of the chosen weights."
        ),
        code(
            "s = sens.sort_values('rank_median')\n"
            "cols = ['agency_name','rank_median','rank_best','rank_worst','rank_iqr',\n"
            "        'pct_draws_in_bottom_quartile','pct_draws_in_top_quartile','quartile_verdict']\n"
            "s[cols].round(1).reset_index(drop=True)"
        ),
        code(
            "verdicts = sens.quartile_verdict.value_counts()\n"
            "print(verdicts.to_string())\n"
            "print()\n"
            "robust = sens[sens.quartile_verdict != 'not separable']\n"
            "print(f'{len(robust)} of {len(sens)} agencies hold their quartile across the weighting distribution:')\n"
            "for _, r in robust.iterrows():\n"
            "    print(f'  {r.agency_name:<46} {r.quartile_verdict}')"
        ),
        md(
            "### This is the honest result, and it is the point\n\n"
            "Most of the ranking does **not** survive a change of weights. Reporting the index as "
            "a clean 1-to-19 ordering would be presenting weighting choices as findings.\n\n"
            "What *is* robust: the bottom of the table. Those agencies score poorly under almost "
            "any weighting anyone might reasonably choose, which is a result worth acting on. "
            "The middle is not separable and is reported as such."
        ),
        md("## 5. Named alternative weightings"),
        code(
            "comparison = load('index_weighting_comparison')\n"
            "comparison.round(1).reset_index(drop=True)"
        ),
        code(
            "wide = comparison.set_index('agency_name')\n"
            "cols = [c for c in ['configured','equal','risk_weighted','competition_only'] if c in wide.columns]\n"
            "fig, ax = plt.subplots(figsize=(9.5, 6))\n"
            "order = wide.sort_values('configured').index\n"
            "for i, c in enumerate(cols):\n"
            "    ax.plot(wide.loc[order, c].values, range(len(order)), 'o-',\n"
            "            color=[BLUE, ORANGE, AQUA, RED][i], lw=1.4, ms=5, alpha=.85, label=c)\n"
            "ax.set_yticks(range(len(order))); ax.set_yticklabels(order, fontsize=9)\n"
            "ax.invert_xaxis()\n"
            "ax.set(title='Rank under four weightings (further right = better rank)', xlabel='Rank')\n"
            "ax.legend(frameon=False, fontsize=9); ax.grid(axis='y', alpha=0)\n"
            "plt.tight_layout(); plt.show()"
        ),
        md(
            "## 6. Decomposing any score\n\n"
            "A composite that cannot be taken apart is not usable. Every score returns its "
            "sub-scores, so 'why is this agency here' is always answerable."
        ),
        code(
            "target = idx.sort_values('efficiency_index').iloc[0]['agency_name']\n"
            "row = idx.set_index('agency_name').loc[target]\n"
            "weights = cfg['efficiency_index']['weights']\n"
            "parts = pd.DataFrame({\n"
            "    'sub-score': [row[f'{d}_score'] for d in cei.DIMENSIONS],\n"
            "    'weight':    [weights[d] for d in cei.DIMENSIONS],\n"
            "}, index=list(cei.DIMENSIONS))\n"
            "parts['contribution'] = parts['sub-score'] * parts['weight']\n"
            "print(f'{target}  —  index {row.efficiency_index:.1f}')\n"
            "display(parts.round(2))\n"
            "print(f'sum of contributions: {parts.contribution.sum():.1f}')"
        ),
        md(
            "---\n\n"
            "## What the index is for\n\n"
            "It is a **triage device** that ranks where to look first. It is not a measure of "
            "waste, and a low score is not an accusation — a defence research agency buying "
            "developmental systems *should* run more cost-reimbursement work and a thinner vendor "
            "base than an agency buying office supplies.\n\n"
            "See [`docs/LIMITATIONS.md`](../docs/LIMITATIONS.md)."
        ),
    ]
    return nb


NOTEBOOKS = {
    "01_pipeline_walkthrough.ipynb": notebook_01,
    "02_findings.ipynb": notebook_02,
    "03_efficiency_index.ipynb": notebook_03,
}


def main() -> None:
    NB_DIR.mkdir(parents=True, exist_ok=True)
    for name, builder in NOTEBOOKS.items():
        nb = builder()
        nb.metadata.update(
            {
                "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                "language_info": {"name": "python", "version": "3.11"},
            }
        )
        path = NB_DIR / name
        print(f"executing {name} ...")
        client = NotebookClient(
            nb, timeout=600, kernel_name="python3", resources={"metadata": {"path": str(NB_DIR)}}
        )
        client.execute()
        nbf.write(nb, path)
        print(f"  wrote {path} ({path.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
