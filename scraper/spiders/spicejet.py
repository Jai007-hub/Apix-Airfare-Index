from scraper.spiders.generic_airline import GenericAirlineSpider


class SpiceJetSpider(GenericAirlineSpider):
    name = "spicejet"
    source_name = "spicejet"
    allowed_domains = ["spicejet.com"]
    search_base_url = "https://www.spicejet.com/book/flight-search"
    carrier_code = "SG"
