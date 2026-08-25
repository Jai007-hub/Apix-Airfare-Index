from scraper.spiders.generic_airline import GenericAirlineSpider


class AkasaAirSpider(GenericAirlineSpider):
    name = "akasa_air"
    source_name = "akasa_air"
    allowed_domains = ["akasaair.com"]
    search_base_url = "https://www.akasaair.com/book/flight-search"
    carrier_code = "QP"
