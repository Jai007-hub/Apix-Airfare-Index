"""CLI entrypoint for data acquisition.

    python -m scraper.run synthetic --days 60                 # backfill synthetic history
    python -m scraper.run synthetic --days 60 --end-date 2026-07-31
    python -m scraper.run live --sources indigo,makemytrip     # run real spiders (needs `playwright install`)
    python -m scraper.run live                                 # run all 11 spiders
    python -m scraper.run process --start 2026-06-01 --end 2026-07-31   # re-run clean+index only

Every subcommand ends by re-running the cleaning pipeline and index
construction over the affected date range, so the DB is always left in a
consistent, query-ready state.
"""
import argparse
from datetime import date, timedelta

from db.database import init_db, session_scope
from index.apix import build_and_persist_all
from pipeline.clean import clean_date_range
from pipeline.dimensions import ensure_dimensions
from pipeline.load import bulk_load_records
from scraper import config
from scraper.synthetic.generator import SyntheticFareGenerator


def _process(start: date, end: date) -> None:
    with session_scope() as session:
        n_clean = clean_date_range(session, start, end)
        counts = build_and_persist_all(session, start, end)
    print(f"Cleaned {n_clean} route/carrier/window cells over {start}..{end}; index rows written: {counts}")


def cmd_synthetic(args: argparse.Namespace) -> None:
    init_db()
    end = date.fromisoformat(args.end_date) if args.end_date else date.today()
    start = end - timedelta(days=args.days - 1)

    generator = SyntheticFareGenerator(seed=args.seed)
    records = generator.generate_range(start, end)
    with session_scope() as session:
        dims = ensure_dimensions(session)
        n = bulk_load_records(session, records, dims)
    print(f"Loaded {n} synthetic raw observations for {start}..{end}")
    _process(start, end)


def _spider_registry() -> dict:
    from scraper.spiders.air_india import AirIndiaSpider
    from scraper.spiders.air_india_express import AirIndiaExpressSpider
    from scraper.spiders.akasa_air import AkasaAirSpider
    from scraper.spiders.cleartrip import CleartripSpider
    from scraper.spiders.easemytrip import EaseMyTripSpider
    from scraper.spiders.goibibo import GoibiboSpider
    from scraper.spiders.indigo import IndigoSpider
    from scraper.spiders.ixigo import IxigoSpider
    from scraper.spiders.makemytrip import MakeMyTripSpider
    from scraper.spiders.spicejet import SpiceJetSpider
    from scraper.spiders.yatra import YatraSpider

    return {
        "indigo": IndigoSpider,
        "air_india": AirIndiaSpider,
        "air_india_express": AirIndiaExpressSpider,
        "akasa_air": AkasaAirSpider,
        "spicejet": SpiceJetSpider,
        "makemytrip": MakeMyTripSpider,
        "yatra": YatraSpider,
        "easemytrip": EaseMyTripSpider,
        "cleartrip": CleartripSpider,
        "ixigo": IxigoSpider,
        "goibibo": GoibiboSpider,
    }


def cmd_live(args: argparse.Namespace) -> None:
    init_db()
    from scrapy.crawler import CrawlerProcess
    from scrapy.settings import Settings

    settings = Settings()
    settings.setmodule("scraper.settings")

    registry = _spider_registry()
    names = args.sources.split(",") if args.sources else list(registry)
    unknown = [n for n in names if n not in registry]
    if unknown:
        raise SystemExit(f"Unknown source(s): {unknown}. Options: {sorted(registry)}")

    process = CrawlerProcess(settings)
    for name in names:
        process.crawl(registry[name])
    process.start()

    today = date.today()
    _process(today, today)


def cmd_process(args: argparse.Namespace) -> None:
    init_db()
    start = date.fromisoformat(args.start)
    end = date.fromisoformat(args.end) if args.end else start
    _process(start, end)


def main() -> None:
    parser = argparse.ArgumentParser(description="APIx data acquisition CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    p_synth = sub.add_parser("synthetic", help="Backfill calibrated synthetic fare history")
    p_synth.add_argument("--days", type=int, default=60)
    p_synth.add_argument("--end-date", type=str, default=None, help="YYYY-MM-DD, defaults to today")
    p_synth.add_argument("--seed", type=int, default=42)
    p_synth.set_defaults(func=cmd_synthetic)

    p_live = sub.add_parser("live", help="Run real spiders against live sites (requires `playwright install`)")
    p_live.add_argument("--sources", type=str, default=None, help=f"Comma-separated subset of {[s.name for s in config.SOURCES]}")
    p_live.set_defaults(func=cmd_live)

    p_proc = sub.add_parser("process", help="Re-run cleaning + index construction only")
    p_proc.add_argument("--start", type=str, required=True)
    p_proc.add_argument("--end", type=str, default=None)
    p_proc.set_defaults(func=cmd_process)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
