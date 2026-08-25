"""Reference spider #2: MakeMyTrip (OTA, JS-heavy SPA, Playwright-rendered).

Same caveat as scraper/spiders/indigo.py: selectors follow MakeMyTrip's
typical result-list pattern and are a starting point to re-verify against
the live DOM, not a guaranteed-current match. Demonstrates the OTA case:
multiple carriers per page, and a combined "Base Fare + Taxes & Fees" split
handled by pipeline/decompose.py via taxes_and_fees_lump.
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


class MakeMyTripSpider(BaseFareSpider):
    name = "makemytrip"
    source_name = "makemytrip"
    use_playwright = True
    allowed_domains = ["makemytrip.com"]

    def build_search_url(self, route: config.RouteDef, departure_date: date) -> str:
        params = {
            "itinerary": f"{route.origin}-{route.destination}-{departure_date.isoformat()}",
            "tripType": "O",
            "paxType": "A-1_C-0_I-0",
            "cabinClass": "E",
        }
        return f"https://www.makemytrip.com/flight/search?{urlencode(params)}"

    def parse(self, response):
        cards = response.css("div.listingCard, li[data-testid='flight-listing-card']")
        if not cards:
            logger.info(
                "No listing cards parsed for %s on %s (markup may have changed, or genuinely no flights)",
                response.meta["route"].label, response.meta["departure_date"],
            )
            return

        for card in cards:
            carrier_name = (card.css(".airline-name::text, [data-testid='airline-name']::text").get() or "").strip()
            carrier_code = _CARRIER_NAME_TO_CODE.get(carrier_name.lower())
            if carrier_code is None:
                continue  # not one of the 5 carriers in the basket

            flight_number = card.css(".flight-number::text, [data-testid='flight-number']::text").get()
            sold_out = bool(card.css(".sold-out, [data-testid='sold-out']"))
            if sold_out:
                yield self.make_item(
                    response, carrier_code=carrier_code, flight_number=flight_number,
                    fare_class="Economy", availability_status="sold_out",
                )
                continue

            base_fare_text = card.css(".base-fare::text, [data-testid='base-fare']::text").get()
            taxes_text = card.css(".taxes-fees::text, [data-testid='taxes-fees']::text").get()
            total_fare_text = card.css(".total-fare::text, [data-testid='total-fare']::text").get()

            base_fare = parse_amount(base_fare_text)
            taxes_lump = parse_amount(taxes_text)
            total_fare = parse_amount(total_fare_text)

            if base_fare is None and total_fare is None:
                continue

            yield self.make_item(
                response,
                carrier_code=carrier_code,
                flight_number=(flight_number or "").strip() or None,
                fare_class="Economy",
                base_fare=base_fare,
                total_fare=total_fare,
                taxes_and_fees_lump=taxes_lump,
                availability_status="available",
                raw_payload=json.dumps({
                    "carrier_name": carrier_name, "base_fare_text": base_fare_text,
                    "taxes_text": taxes_text, "total_fare_text": total_fare_text,
                }),
            )
