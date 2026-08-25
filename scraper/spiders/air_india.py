from scraper.spiders.generic_airline import GenericAirlineSpider


class AirIndiaSpider(GenericAirlineSpider):
    name = "air_india"
    source_name = "air_india"
    allowed_domains = ["airindia.com"]
    search_base_url = "https://www.airindia.com/en-in/book/flight-search"
    carrier_code = "AI"
