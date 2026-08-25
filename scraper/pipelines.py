"""Scrapy item pipeline: decomposes each scraped fare and upserts it as a
RawObservation, via the same pipeline/ modules the synthetic generator and
seed script use -- one write path for live and synthetic data."""
import logging
from datetime import datetime

from db.database import SessionLocal
from db.models import AvailabilityStatus, DataSourceType
from pipeline.decompose import decompose_fare
from pipeline.dedupe import upsert_raw_observation
from pipeline.dimensions import ensure_dimensions

logger = logging.getLogger("apix_scraper.pipelines")


class FarePipeline:
    def open_spider(self, spider):
        self.session = SessionLocal()
        self.dims = ensure_dimensions(self.session)

    def close_spider(self, spider):
        self.session.close()

    def process_item(self, item, spider):
        decomposed = decompose_fare(
            origin=item["origin"],
            destination=item["destination"],
            source_name=item["source_name"],
            base_fare=item.get("base_fare"),
            total_fare=item.get("total_fare"),
            taxes_and_fees_lump=item.get("taxes_and_fees_lump"),
        )

        route_id = self.dims.route_ids.get(item["route_label"])
        carrier_id = self.dims.carrier_ids.get(item.get("carrier_code"))
        source_id = self.dims.source_ids.get(item["source_name"])
        if route_id is None or source_id is None:
            logger.error("Unknown route/source for item %s -- dropping", dict(item))
            return item

        fields = dict(
            scraped_at=item.get("scraped_at", datetime.now()),
            observation_date=item["observation_date"],
            source_id=source_id,
            route_id=route_id,
            carrier_id=carrier_id,
            flight_number=item.get("flight_number"),
            departure_date=item["departure_date"],
            advance_window_days=item["advance_window_days"],
            fare_class=item.get("fare_class"),
            base_fare=decomposed["base_fare"],
            taxes=decomposed["taxes"],
            udf=decomposed["udf"],
            convenience_fee=decomposed["convenience_fee"],
            total_fare=decomposed["total_fare"],
            availability_status=AvailabilityStatus(item.get("availability_status", "unknown")),
            data_source_type=DataSourceType.LIVE,
            raw_payload=item.get("raw_payload"),
        )
        upsert_raw_observation(self.session, fields)
        return item
