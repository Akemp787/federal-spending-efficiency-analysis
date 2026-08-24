"""Loads the curated tables into a DuckDB file and installs the analytic views.

DuckDB rather than SQLite or Postgres because the workload is analytical
(columnar scans and window functions over parquet), it reads parquet natively so
loading is a single statement per table, and the whole warehouse is one file a
reviewer can open with no server to run.

The views in ``sql/`` are the SQL layer of the project: they express the same
analysis as the Python metrics modules, which means they also serve as an
independent check that the two paths agree.
"""

from __future__ import annotations

from pathlib import Path

import duckdb

from ..analysis import CURATED_FILES
from ..config import Config
from ..logging_utils import get_logger

log = get_logger(__name__)


def sql_dir(cfg: Config) -> Path:
    return cfg.root / "sql"


def build_warehouse(cfg: Config, *, rebuild: bool = True) -> Path:
    """Create ``data/curated/fedspend.duckdb`` with one table per curated parquet."""
    cfg.curated_dir.mkdir(parents=True, exist_ok=True)
    db_path = cfg.warehouse_path
    if rebuild and db_path.exists():
        db_path.unlink()

    con = duckdb.connect(str(db_path))
    try:
        loaded = 0
        for table, filename in CURATED_FILES.items():
            path = cfg.curated_dir / filename
            if not path.exists():
                log.warning("skipping %s (missing %s)", table, filename)
                continue
            con.execute(
                f"CREATE OR REPLACE TABLE {table} AS "
                f"SELECT * FROM read_parquet('{path.as_posix()}')"
            )
            n = con.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
            log.info("loaded %-34s %6d rows", table, n)
            loaded += 1

        installed = install_views(cfg, con)
        log.info("warehouse built: %d tables, %d views -> %s", loaded, installed, db_path)
    finally:
        con.close()
    return db_path


def install_views(cfg: Config, con: duckdb.DuckDBPyConnection) -> int:
    """Execute every ``.sql`` file in ``sql/`` in filename order."""
    installed = 0
    for path in sorted(sql_dir(cfg).glob("*.sql")):
        script = path.read_text(encoding="utf-8")
        try:
            con.execute(script)
            log.info("installed view script %s", path.name)
            installed += 1
        except duckdb.Error as exc:
            log.error("failed installing %s: %s", path.name, exc)
            raise
    return installed


def query(cfg: Config, sql: str):
    """Run a read-only query against the warehouse and return a DataFrame."""
    con = duckdb.connect(str(cfg.warehouse_path), read_only=True)
    try:
        return con.execute(sql).fetchdf()
    finally:
        con.close()
