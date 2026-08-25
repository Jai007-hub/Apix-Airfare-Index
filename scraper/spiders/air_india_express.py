from scraper.spiders.generic_airline import GenericAirlineSpider


class AirIndiaExpressSpider(GenericAirlineSpider):
    name = "air_india_express"
    source_name = "air_india_express"
    allowed_domains = ["airindiaexpress.com"]
    search_base_url = "https://www.airindiaexpress.com/book/flight-search"
    carrier_code = "IX"
