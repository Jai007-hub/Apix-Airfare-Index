from scraper.spiders.generic_ota import GenericOTASpider


class EaseMyTripSpider(GenericOTASpider):
    name = "easemytrip"
    source_name = "easemytrip"
    allowed_domains = ["easemytrip.com"]
    search_base_url = "https://www.easemytrip.com/flights/search"
