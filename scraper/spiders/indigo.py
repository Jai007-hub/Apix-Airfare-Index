"""Reference spider #1: IndiGo direct (airline site, JS-rendered via Playwright).

Wired end-to-end (request -> parse -> item -> pipeline). The CSS selectors
below follow IndiGo's typical flight-card markup pattern but, like any
scraper, WILL need re-verification against the live DOM periodically --
airline sites restyle their booking flow often. Treat this as the reference
implementation to copy when hardening the scaffolded spiders in this
directory, not as a guarantee it matches today's production markup exactly.
"""
import json
import logging
from datetime import date
from urllib.parse import urlencode

from scraper import config
from scraper.spiders.base import BaseFareSpider
from scraper.spiders.parsing_utils import parse_amount

logger = logging.getLogger(__name__)


class IndigoSpider(BaseFareSpider):
    name = "indigo"
    source_name = "indigo"
    use_playwright = True
    allowed_domains = ["goindigo.in"]

    def build_search_url(self, route: config.RouteDef, departure_date: date) -> str:
        params = {
            "origin": route.origin,
            "destination": route.destination,
            "departureDate": departure_date.isoformat(),
            "paxType": "ADT-1",
            "cabinClass": "ECONOMY",
        }
        return f"https://www.goindigo.in/booking/flight-search?{urlencode(params)}"

    def parse(self, response):
        cards = response.css("div.flight-card, li[data-testid='flight-result']")
        if not cards:
            logger.info("No flight cards parsed for %s on %s (markup may have changed, or genuinely no flights)",
                        response.meta["route"].label, response.meta["departure_date"])
            return

        for card in cards:
            flight_number = card.css(".flight-number::text, [data-testid='flight-number']::text").get()
            fare_text = card.css(".fare-amount::text, [data-testid='fare-amount']::text").get()
            sold_out = bool(card.css(".sold-out, [data-testid='sold-out']"))

            if sold_out:
                yield self.make_item(
                    response,
                    carrier_code="6E",
                    flight_number=(flight_number or "").strip() or None,
                    fare_class="Economy",
                    availability_status="sold_out",
                )
                continue

            total_fare = parse_amount(fare_text)
            if total_fare is None:
                continue

            yield self.make_item(
                response,
                carrier_code="6E",
                flight_number=(flight_number or "").strip() or None,
                fare_class="Economy",
                total_fare=total_fare,  # IndiGo shows an all-in fare; base/taxes split via pipeline/decompose.py
                availability_status="available",
                raw_payload=json.dumps({"fare_text": fare_text, "flight_number": flight_number}),
            )
