# Archived v1 notebook

`00_v1_data_cleaning.ipynb` is the original FY2021–FY2024 cleaning notebook from the first
version of this project. It is kept for provenance.

Its logic — chunked reads of the USAspending Award Data Archive, schema standardisation across
fiscal years, type coercion, and multi-year consolidation — is superseded by
[`src/fedspend/ingest/bulk_archive.py`](../../src/fedspend/ingest/bulk_archive.py), which does
the same job as tested, importable, memory-bounded code that writes a partitioned parquet dataset
rather than holding frames in a kernel.

The v2 pipeline does not depend on this notebook.
