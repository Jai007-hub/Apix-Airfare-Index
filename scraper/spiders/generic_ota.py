"""Shared scaffold for the OTA spiders that haven't been hardened against a
live DOM yet (see scraper/spiders/makemytrip.py for the fully-wired
reference this pattern follows). Subclasses set the URL/domain and, once
verified against the real site, override CSS_* selectors.
"""
import json
import logging
from datetime import date
from urllib.parse import urlencode

from scraper import config
from scraper.spiders.base import BaseFareSpider
from scraper.spiders.parsing_utils import parse_amount

logger = logging.getLogger(__name__)

_CARRIER_NAME_TO_CODE = {c.name.lower(): c.code for c in config.CARRIERS}


class GenericOTASpider(BaseFareSpider):
    use_playwright = True

    # -- override in subclasses --
    search_base_url: str = None
    CSS_CARD = "div.listingCard, li[data-testid='flight-listing-card']"
    CSS_CARRIER_NAME = ".airline-name::text, [data-testid='airline-name']::text"
    CSS_FLIGHT_NUMBER = ".flight-number::text, [data-testid='flight-number']::text"
    CSS_SOLD_OUT = ".sold-out, [data-testid='sold-out']"
    CSS_BASE_FARE = ".base-fare::text, [data-testid='base-fare']::text"
    CSS_TAXES_FEES = ".taxes-fees::text, [data-testid='taxes-fees']::text"
    CSS_TOTAL_FARE = ".total-fare::text, [data-testid='total-fare']::text"

    def build_search_url(self, route: config.RouteDef, departure_date: date) -> str:
        params = {"from": route.origin, "to": route.destination, "date": departure_date.isoformat(), "cabin": "E"}
        return f"{self.search_base_url}?{urlencode(params)}"

    def parse(self, response):
        cards = response.css(self.CSS_CARD)
        if not cards:
            logger.info(
                "%s: no listing cards parsed for %s on %s -- verify CSS_CARD against the live DOM",
                self.source_name, response.meta["route"].label, response.meta["departure_date"],
            )
            return

        for card in cards:
            carrier_name = (card.css(self.CSS_CARRIER_NAME).get() or "").strip()
            carrier_code = _CARRIER_NAME_TO_CODE.get(carrier_name.lower())
            if carrier_code is None:
                continue

            flight_number = (card.css(self.CSS_FLIGHT_NUMBER).get() or "").strip() or None
            if bool(card.css(self.CSS_SOLD_OUT)):
                yield self.make_item(
                    response, carrier_code=carrier_code, flight_number=flight_number,
                    fare_class="Economy", availability_status="sold_out",
                )
                continue

            base_fare_text = card.css(self.CSS_BASE_FARE).get()
            taxes_text = card.css(self.CSS_TAXES_FEES).get()
            total_fare_text = card.css(self.CSS_TOTAL_FARE).get()

            base_fare = parse_amount(base_fare_text)
            taxes_lump = parse_amount(taxes_text)
            total_fare = parse_amount(total_fare_text)
            if base_fare is None and total_fare is None:
                continue

            yield self.make_item(
                response,
                carrier_code=carrier_code,
                flight_number=flight_number,
                fare_class="Economy",
                base_fare=base_fare,
                total_fare=total_fare,
                taxes_and_fees_lump=taxes_lump,
                availability_status="available",
                raw_payload=json.dumps({"carrier_name": carrier_name}),
            )
