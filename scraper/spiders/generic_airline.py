"""Shared scaffold for the airline-direct spiders that haven't been hardened
against a live DOM yet (see scraper/spiders/indigo.py for the fully-wired
reference this pattern follows). Subclasses only need to set the URL/domain
and, once verified against the real site, override CSS_* selectors.

This is real, runnable Scrapy code -- robots.txt compliance, rate limiting
and item construction all work today -- the placeholder selectors are the
one thing each subclass's maintainer should verify before relying on it for
`--mode live`.
"""
import json
import logging
from datetime import date
from urllib.parse import urlencode

from scraper import config
from scraper.spiders.base import BaseFareSpider
from scraper.spiders.parsing_utils import parse_amount

logger = logging.getLogger(__name__)


class GenericAirlineSpider(BaseFareSpider):
    use_playwright = True

    # -- override in subclasses --
    search_base_url: str = None
    carrier_code: str = None
    CSS_CARD = "div.flight-card, li[data-testid='flight-result']"
    CSS_FLIGHT_NUMBER = ".flight-number::text, [data-testid='flight-number']::text"
    CSS_FARE = ".fare-amount::text, [data-testid='fare-amount']::text"
    CSS_SOLD_OUT = ".sold-out, [data-testid='sold-out']"

    def build_search_url(self, route: config.RouteDef, departure_date: date) -> str:
        params = {"origin": route.origin, "destination": route.destination, "date": departure_date.isoformat()}
        return f"{self.search_base_url}?{urlencode(params)}"

    def parse(self, response):
        cards = response.css(self.CSS_CARD)
        if not cards:
            logger.info(
                "%s: no flight cards parsed for %s on %s -- verify CSS_CARD against the live DOM",
                self.source_name, response.meta["route"].label, response.meta["departure_date"],
            )
            return

        for card in cards:
            flight_number = (card.css(self.CSS_FLIGHT_NUMBER).get() or "").strip() or None
            if bool(card.css(self.CSS_SOLD_OUT)):
                yield self.make_item(
                    response, carrier_code=self.carrier_code, flight_number=flight_number,
                    fare_class="Economy", availability_status="sold_out",
                )
                continue

            fare_text = card.css(self.CSS_FARE).get()
            total_fare = parse_amount(fare_text)
            if total_fare is None:
                continue

            yield self.make_item(
                response,
                carrier_code=self.carrier_code,
                flight_number=flight_number,
                fare_class="Economy",
                total_fare=total_fare,
                availability_status="available",
                raw_payload=json.dumps({"fare_text": fare_text}),
            )
