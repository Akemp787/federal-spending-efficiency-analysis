"""Command-line interface: ``fedspend <stage>``.

The pipeline is a sequence of stages that each read the previous stage's output
from disk, so any stage can be re-run alone. ``fedspend all`` runs the lot and is
what the Makefile and CI invoke.

    fedspend ingest      pull USAspending extracts -> data/interim
    fedspend analyse     build curated tables      -> data/curated
    fedspend warehouse   load DuckDB + SQL views   -> data/curated/fedspend.duckdb
    fedspend validate    run data-quality contracts (non-zero exit on failure)
    fedspend report      render dashboard + tables -> outputs/
    fedspend sample      refresh the committed sample extracts
    fedspend powerbi     build the Power BI star schema + theme -> powerbi/
    fedspend query       run ad-hoc SQL against the warehouse
    fedspend all         ingest -> analyse -> warehouse -> validate -> report -> powerbi
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .config import Config
from .logging_utils import get_logger, setup_logging

log = get_logger(__name__)


def _cfg(args: argparse.Namespace) -> Config:
    return Config.load(args.config)


def cmd_ingest(args: argparse.Namespace) -> int:
    from .ingest.run import run_ingest

    run_ingest(_cfg(args), skip_existing=not args.refresh)
    return 0


def cmd_analyse(args: argparse.Namespace) -> int:
    from .analysis import run_analysis

    run_analysis(_cfg(args))
    return 0


def cmd_warehouse(args: argparse.Namespace) -> int:
    from .warehouse.build import build_warehouse

    build_warehouse(_cfg(args))
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    from .validate import checks

    cfg = _cfg(args)
    results = checks.run_all(cfg)
    if checks.has_blocking_failures(results):
        log.error("validation FAILED - see outputs/tables/validation_report.csv")
        return 1
    log.info("validation passed (%d checks)", len(results))
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    from .report.dashboard import build_dashboard
    from .report.exports import export_tables

    cfg = _cfg(args)
    export_tables(cfg)
    build_dashboard(cfg)
    return 0


def cmd_powerbi(args: argparse.Namespace) -> int:
    from .report.powerbi import build_powerbi_package

    build_powerbi_package(_cfg(args))
    return 0


def cmd_sample(args: argparse.Namespace) -> int:
    from .report.exports import write_samples

    write_samples(_cfg(args))
    return 0


def cmd_query(args: argparse.Namespace) -> int:
    from .warehouse.build import query

    cfg = _cfg(args)
    sql = Path(args.file).read_text(encoding="utf-8") if args.file else args.sql
    if not sql:
        log.error("provide SQL with --sql or --file")
        return 2
    df = query(cfg, sql)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(args.out, index=False)
        log.info("wrote %d rows -> %s", len(df), args.out)
    else:
        import pandas as pd

        with pd.option_context("display.width", 200, "display.max_columns", 60):
            print(df.to_string(index=False))
    return 0


def cmd_all(args: argparse.Namespace) -> int:
    for step in (
        cmd_ingest,
        cmd_analyse,
        cmd_warehouse,
        cmd_validate,
        cmd_report,
        cmd_powerbi,
    ):
        code = step(args)
        if code != 0:
            log.error("stage %s failed with exit code %d", step.__name__, code)
            return code
    log.info("pipeline complete")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="fedspend",
        description="Federal contract spending efficiency analytics pipeline.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--config", help="path to pipeline.yml", default=None)
    parser.add_argument("-v", "--verbose", action="store_true", help="debug logging")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("ingest", help="pull USAspending extracts")
    p.add_argument(
        "--refresh",
        action="store_true",
        help="re-pull extracts that already exist (API cache still applies)",
    )
    p.set_defaults(func=cmd_ingest)

    sub.add_parser("analyse", help="build curated tables").set_defaults(func=cmd_analyse)
    sub.add_parser("analyze", help=argparse.SUPPRESS).set_defaults(func=cmd_analyse)
    sub.add_parser("warehouse", help="build the DuckDB warehouse").set_defaults(
        func=cmd_warehouse
    )
    sub.add_parser("validate", help="run data-quality contracts").set_defaults(
        func=cmd_validate
    )
    sub.add_parser("report", help="render dashboard and exports").set_defaults(func=cmd_report)
    sub.add_parser("sample", help="refresh committed sample data").set_defaults(func=cmd_sample)
    sub.add_parser(
        "powerbi", help="build the Power BI star schema and theme"
    ).set_defaults(func=cmd_powerbi)

    q = sub.add_parser("query", help="run SQL against the warehouse")
    q.add_argument("--sql", help="SQL string")
    q.add_argument("--file", help="path to a .sql file")
    q.add_argument("--out", help="write results to CSV instead of stdout")
    q.set_defaults(func=cmd_query)

    a = sub.add_parser("all", help="run the entire pipeline")
    a.add_argument("--refresh", action="store_true", help="re-pull existing extracts")
    a.set_defaults(func=cmd_all)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    setup_logging(args.verbose)
    try:
        return int(args.func(args))
    except KeyboardInterrupt:
        log.warning("interrupted")
        return 130


if __name__ == "__main__":
    sys.exit(main())
