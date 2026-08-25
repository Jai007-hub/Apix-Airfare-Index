"""Offline parse tests: feed fixture HTML directly into the spiders' parse()
methods (no network, no Playwright) to verify the extraction logic itself is
correct. These don't prove the selectors match today's live DOM (see the
module docstrings in scraper/spiders/indigo.py and makemytrip.py) -- they
prove that *given* markup matching those selectors, the spider produces
correctly-shaped, correctly-decomposed items.
"""
from datetime import date

from scrapy.http import HtmlResponse, Request

from scraper.config import ROUTES
from scraper.spiders.indigo import IndigoSpider
from scraper.spiders.makemytrip import MakeMyTripSpider

DEL_BOM = next(r for r in ROUTES if r.label == "DEL-BOM")


def _make_response(url: str, html: str, route, departure_date, advance_window_days, observation_date):
    request = Request(
        url=url,
        meta={
            "route": route,
            "departure_date": departure_date,
            "advance_window_days": advance_window_days,
            "observation_date": observation_date,
        },
    )
    return HtmlResponse(url=url, request=request, body=html.encode("utf-8"), encoding="utf-8")


def test_indigo_spider_parses_available_and_sold_out_cards():
    html = """
    <html><body>
      <div class="flight-card">
        <span class="flight-number">6E607</span>
        <span class="fare-amount">Rs. 8,428</span>
      </div>
      <div class="flight-card">
        <span class="flight-number">6E205</span>
        <span class="sold-out">Sold Out</span>
      </div>
    </body></html>
    """
    response = _make_response(
        "https://www.goindigo.in/booking/flight-search", html, DEL_BOM, date(2026, 7, 2), 1, date(2026, 7, 1)
    )
    spider = IndigoSpider()
    items = list(spider.parse(response))

    assert len(items) == 2
    available, sold_out = items
    assert available["carrier_code"] == "6E"
    assert available["flight_number"] == "6E607"
    assert available["total_fare"] == 8428.0
    assert available["availability_status"] == "available"
    assert available["route_label"] == "DEL-BOM"

    assert sold_out["availability_status"] == "sold_out"
    assert sold_out["total_fare"] is None


def test_makemytrip_spider_parses_known_carrier_and_skips_unknown():
    html = """
    <html><body>
      <div class="listingCard">
        <span class="airline-name">IndiGo</span>
        <span class="flight-number">6E607</span>
        <span class="base-fare">Rs. 7,046</span>
        <span class="taxes-fees">Rs. 1,382</span>
        <span class="total-fare">Rs. 8,428</span>
      </div>
      <div class="listingCard">
        <span class="airline-name">SomeOtherAirline</span>
        <span class="flight-number">XX123</span>
        <span class="total-fare">Rs. 5,000</span>
      </div>
    </body></html>
    """
    response = _make_response(
        "https://www.makemytrip.com/flight/search", html, DEL_BOM, date(2026, 7, 2), 1, date(2026, 7, 1)
    )
    spider = MakeMyTripSpider()
    items = list(spider.parse(response))

    assert len(items) == 1  # the unknown-carrier card is skipped
    item = items[0]
    assert item["carrier_code"] == "6E"
    assert item["base_fare"] == 7046.0
    assert item["taxes_and_fees_lump"] == 1382.0
    assert item["total_fare"] == 8428.0
