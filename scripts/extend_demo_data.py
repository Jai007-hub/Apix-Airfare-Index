"""Tops up an already-seeded database with only the missing trailing days,
so the dashboard never goes stale as "today" advances, without touching or
duplicating the existing history. (Re-running scripts/seed_demo_data.py over
a range that overlaps what's already loaded would crash on duplicate raw
observations instead -- flight numbers are deterministic given the same
seed + date, so it collides with the existing unique constraint.)

    python -m scripts.extend_demo_data                  # fills through today
    python -m scripts.extend_demo_data --end 2026-09-01  # fills through a specific date
"""
import argparse
from datetime import date, timedelta
from pathlib import Path

from db.database import init_db, session_scope
from db.models import RawObservation
from index.apix import build_and_persist_all
from pipeline.clean import clean_date_range
from pipeline.dimensions import ensure_dimensions
from pipeline.load import bulk_load_records
from scraper.synthetic.generator import SyntheticFareGenerator
from validation.backtest import run_backtest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CPI_XLSX = PROJECT_ROOT / "cpi_1054.xlsx"
SEED_BASE_START = date(2026, 2, 1)  # must match scripts/seed_demo_data.py's default start


def main() -> None:
    parser = argparse.ArgumentParser(description="Top up the demo database with missing trailing days")
    parser.add_argument("--end", type=str, default=date.today().isoformat())
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--cpi-xlsx", type=str, default=str(DEFAULT_CPI_XLSX))
    args = parser.parse_args()

    end = date.fromisoformat(args.end)
    init_db()

    with session_scope() as session:
        latest = (
            session.query(RawObservation.observation_date)
            .order_by(RawObservation.observation_date.desc())
            .first()
        )

    if latest is None:
        raise SystemExit("No existing data found -- run `python -m scripts.seed_demo_data` first.")

    gap_start = latest[0] + timedelta(days=1)
    if gap_start > end:
        print(f"Already up to date (latest observation_date = {latest[0]}, requested end = {end}). Nothing to do.")
        return

    print(f"Filling gap: {gap_start} .. {end}")
    generator = SyntheticFareGenerator(seed=args.seed)
    records = generator.generate_range(gap_start, end)
    with session_scope() as session:
        dims = ensure_dimensions(session)
        n_loaded = bulk_load_records(session, records, dims)
    print(f"Loaded {n_loaded} raw fare observations")

    with session_scope() as session:
        n_clean = clean_date_range(session, gap_start, end)
    print(f"Cleaned into {n_clean} (route x carrier x window) daily cells")

    # Recompute the index over the FULL span so daily/weekly/monthly series stay
    # continuous and correctly based -- idempotent for already-existing days
    # (same inputs -> same outputs, just re-upserted).
    with session_scope() as session:
        counts = build_and_persist_all(session, SEED_BASE_START, end)
    print(f"Index rows written/updated: {counts}")

    with session_scope() as session:
        result = run_backtest(session, args.cpi_xlsx)
    if "error" in result:
        print(f"Validation backtest: {result['error']}")
    else:
        print(
            f"Validation backtest vs cpi_1054.xlsx: {result['n_months_compared']} month(s) compared, "
            f"MAPE={result['mape_pct']}%, Pearson r={result['pearson_correlation']}"
        )

    print("\nDone.")


if __name__ == "__main__":
    main()
