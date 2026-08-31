"""One-shot demo seed: generates calibrated synthetic fare history, runs it
through cleaning + index construction, then validates the computed monthly
APIx against the real MoSPI CPI airfare sub-index (cpi_1054.xlsx). This is
what gives the API/dashboard something to show without depending on live
scraping succeeding first, and satisfies requirement #10's back-test by
construction.

    python -m scripts.seed_demo_data
    python -m scripts.seed_demo_data --start 2026-06-01 --end 2026-07-31

Re-running this against an already-seeded database will fail on duplicate
raw observations for any date range that overlaps what's already loaded --
see scripts/extend_demo_data.py to top up an existing database with only
the missing trailing days instead of re-seeding from scratch.
"""
import argparse
from datetime import date
from pathlib import Path

from db.database import init_db, session_scope
from index.apix import build_and_persist_all
from pipeline.clean import clean_date_range
from pipeline.dimensions import ensure_dimensions
from pipeline.load import bulk_load_records
from scraper.synthetic.generator import SyntheticFareGenerator
from validation.backtest import run_backtest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CPI_XLSX = PROJECT_ROOT / "cpi_1054.xlsx"

# The synthetic history spans exactly the period cpi_1054.xlsx covers:
# January 2025 through July 2026. Both ends are fixed rather than running to
# "today" for two reasons -- every month of generated fares then has a real
# CPI month to be validated against, and the seed is reproducible, so a
# teammate seeding next week gets a byte-identical database rather than a
# quietly different date range. Anything past July 2026 could not be
# back-tested, so it isn't generated.
# These are the single source of truth; scripts/extend_demo_data.py imports
# them rather than keeping its own copy.
DEMO_START = date(2025, 1, 1)
DEMO_END = date(2026, 7, 31)


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed the APIx demo database end-to-end")
    parser.add_argument("--start", type=str, default=DEMO_START.isoformat())
    parser.add_argument("--end", type=str, default=DEMO_END.isoformat())
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--cpi-xlsx", type=str, default=str(DEFAULT_CPI_XLSX))
    args = parser.parse_args()

    start = date.fromisoformat(args.start)
    end = date.fromisoformat(args.end)
    n_days = (end - start).days + 1
    print(f"Seeding synthetic fare history: {start} .. {end} ({n_days} days)")

    init_db()

    generator = SyntheticFareGenerator(seed=args.seed)
    records = generator.generate_range(start, end)
    with session_scope() as session:
        dims = ensure_dimensions(session)
        n_loaded = bulk_load_records(session, records, dims)
    print(f"Loaded {n_loaded} raw fare observations")

    with session_scope() as session:
        n_clean = clean_date_range(session, start, end)
    print(f"Cleaned into {n_clean} (route x carrier x window) daily cells")

    with session_scope() as session:
        counts = build_and_persist_all(session, start, end)
    print(f"Index rows written: {counts}")

    with session_scope() as session:
        result = run_backtest(session, args.cpi_xlsx)

    if "error" in result:
        print(f"Validation backtest: {result['error']}")
    else:
        print(
            f"Validation backtest vs cpi_1054.xlsx: {result['n_months_compared']} month(s) compared, "
            f"MAPE={result['mape_pct']}%, Pearson r={result['pearson_correlation']}"
        )
        for r in result["results"]:
            print(f"  {r['year']}-{r['month']:02d}: APIx(rebased)={r['apix_rebased']}  CPI={r['cpi_index']}  diff={r['pct_diff']}%")

    print("\nDone. Start the API with:  uvicorn api.main:app --reload")


if __name__ == "__main__":
    main()
