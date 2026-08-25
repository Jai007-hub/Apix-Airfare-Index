"""Loads FareRecord-shaped data (from the synthetic generator, or a Scrapy
item) into RawObservation rows. Bulk path is used for backfilling synthetic
history quickly; dedupe.upsert_raw_observation is used for incremental
live-scrape inserts (see scraper/pipelines.py).
"""
from sqlalchemy.orm import Session

from db.models import AvailabilityStatus, DataSourceType, RawObservation
from pipeline.dimensions import DimensionLookup


def _to_row_kwargs(record, dims: DimensionLookup) -> dict:
    return dict(
        scraped_at=record.scraped_at,
        observation_date=record.observation_date,
        source_id=dims.source_ids[record.source_name],
        route_id=dims.route_ids[record.route_label],
        carrier_id=dims.carrier_ids.get(record.carrier_code),
        flight_number=record.flight_number,
        departure_date=record.departure_date,
        advance_window_days=record.advance_window_days,
        fare_class=record.fare_class,
        base_fare=record.base_fare,
        taxes=record.taxes,
        udf=record.udf,
        convenience_fee=record.convenience_fee,
        total_fare=record.total_fare,
        availability_status=AvailabilityStatus(record.availability_status),
        data_source_type=DataSourceType(record.data_source_type),
    )


def bulk_load_records(session: Session, records: list, dims: DimensionLookup) -> int:
    """Fast path for freshly-generated synthetic backfills: assumes no
    pre-existing rows for these keys (true for a fresh seed) and skips the
    per-row existence check that pipeline/dedupe.py does for live scraping."""
    mappings = [_to_row_kwargs(r, dims) for r in records]
    session.bulk_insert_mappings(RawObservation, mappings)
    session.commit()
    return len(mappings)
