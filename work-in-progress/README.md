# Work in progress

Things that are built but **not finished as a deliverable**. Everything outside this folder is
complete: the analysis, the validation, the documentation, the HTML dashboard and the slide deck.

The distinction being drawn here is between *a working component* and *a finished artefact*. Each
item below is real, tested code that produces real output — it just does not yet amount to the
thing a reader would expect from its name.

---

## `powerbi/` — model complete, report not built

**What is finished**

- 25 model-ready tables in a star schema, with pre-validated relationships
- ~40 documented DAX measures
- A theme file carrying the same colour-vision-validated palette as the rest of the project
- A page-by-page build guide and a talk track for a ten-page report
- 35 contract tests asserting key uniqueness, referential integrity, visual-table shape and
  rate bounds

**What is not**

There is **no `.pbix` file**. A Power BI report can only be authored inside Power BI Desktop, so
the file itself has to be assembled by hand from [`powerbi/README.md`](powerbi/README.md) —
roughly an hour of mechanical work, since the data is already shaped for the visuals it feeds and
the measures are written.

Until that exists, calling this "a Power BI report" would overstate it. Hence this folder.

Regenerate the model at any time:

```bash
python -m fedspend.cli powerbi
```

---

## Also unfinished, though not in this folder

**`src/fedspend/ingest/bulk_archive.py`** — the transaction-level path, for the three measures the
aggregation API cannot produce: single-offer rate, contract ceiling growth, and an untruncated
vendor HHI.

The code is written and documented, but it has **never been run end to end**, it has **no test
coverage**, and none of the published findings depend on it. It lives in `src/` rather than here
because it is an importable part of the package and moving it would break the module layout — but
it should be read as unproven rather than finished.

Running it requires downloading the USAspending Award Data Archive, which is tens of gigabytes per
fiscal year.

---

## What would finish each of these

| Item | Remaining work |
|---|---|
| Power BI report | Assemble the `.pbix` from the build guide; export to PDF or publish to Power BI Service |
| `bulk_archive.py` | Run it against one fiscal year, add tests, and fold the single-offer rate into the competition finding — it is the sharpest available measure of competition *quality* |

The broader analytical backlog — the September quality contrast, contract-type standardisation,
contracting-office attribution — is in
[`docs/LIMITATIONS.md`](../docs/LIMITATIONS.md), section 5.
