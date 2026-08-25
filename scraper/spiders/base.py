"""Common request-fanout logic shared by every source spider: iterate the
city-pair basket x advance-purchase windows, issue one search request per
cell, and normalize the eventual parse result into a FareObservationItem.

Subclasses implement build_search_url() and parse(); everything else
(routing, robots.txt compliance via settings, rate limiting via settings,
item construction) is handled here so adding a new source is a small diff.
"""
import abc
from datetime import date, datetime, timedelta

import scrapy

from scraper import config
from scraper.items import FareObservationItem


class BaseFareSpider(scrapy.Spider, abc.ABC):
    source_name: str = None  # must match a name in scraper.config.SOURCES
    use_playwright: bool = False

    async def start(self):
        # Scrapy >=2.13 calls start() instead of start_requests(); this
        # wrapper keeps start_requests() as the single implementation so it
        # also still works on older Scrapy versions that call it directly.
        for request in self.start_requests():
            yield request

    def start_requests(self):
        observation_date = date.today()
        for route in config.ROUTES:
            for window in config.ADVANCE_WINDOWS:
                departure_date = observation_date + timedelta(days=window)
                url = self.build_search_url(route, departure_date)
                meta = {
                    "route": route,
                    "departure_date": departure_date,
                    "advance_window_days": window,
                    "observation_date": observation_date,
                }
                if self.use_playwright:
                    meta["playwright"] = True
                yield scrapy.Request(url, callback=self.parse, meta=meta, dont_filter=True)

    @abc.abstractmethod
    def build_search_url(self, route: "config.RouteDef", departure_date: date) -> str:
        """Return the fare-search URL for this route/departure-date."""

    @abc.abstractmethod
    def parse(self, response):
        """Extract fare cards from the response and yield FareObservationItem(s)
        via self.make_item(...)."""

    def make_item(
        self,
        response,
        *,
        carrier_code: str,
        flight_number: str | None,
        fare_class: str | None,
        base_fare: float | None = None,
        total_fare: float | None = None,
        taxes_and_fees_lump: float | None = None,
        availability_status: str = "available",
        raw_payload: str | None = None,
    ) -> FareObservationItem:
        route: config.RouteDef = response.meta["route"]
        return FareObservationItem(
            scraped_at=datetime.now(),
            observation_date=response.meta["observation_date"],
            source_name=self.source_name,
            route_label=route.label,
            origin=route.origin,
            destination=route.destination,
            carrier_code=carrier_code,
            flight_number=flight_number,
            departure_date=response.meta["departure_date"],
            advance_window_days=response.meta["advance_window_days"],
            fare_class=fare_class,
            base_fare=base_fare,
            total_fare=total_fare,
            taxes_and_fees_lump=taxes_and_fees_lump,
            availability_status=availability_status,
            data_source_type="live",
            raw_payload=raw_payload,
        )
