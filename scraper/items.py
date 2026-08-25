"""Scrapy Item mirroring scraper.synthetic.generator.FareRecord, so both live
spiders and the synthetic generator feed the exact same downstream pipeline
(pipeline/load.py, pipeline/dedupe.py)."""
import scrapy


class FareObservationItem(scrapy.Item):
    scraped_at = scrapy.Field()
    observation_date = scrapy.Field()
    source_name = scrapy.Field()
    route_label = scrapy.Field()
    origin = scrapy.Field()
    destination = scrapy.Field()
    carrier_code = scrapy.Field()
    flight_number = scrapy.Field()
    departure_date = scrapy.Field()
    advance_window_days = scrapy.Field()
    fare_class = scrapy.Field()

    base_fare = scrapy.Field()
    taxes = scrapy.Field()
    taxes_and_fees_lump = scrapy.Field()  # set instead of taxes when the source only shows a combined figure
    udf = scrapy.Field()
    convenience_fee = scrapy.Field()
    total_fare = scrapy.Field()

    availability_status = scrapy.Field()  # "available" | "sold_out" | "cancelled" | "unknown"
    data_source_type = scrapy.Field()  # always "live" for spider output
    raw_payload = scrapy.Field()
