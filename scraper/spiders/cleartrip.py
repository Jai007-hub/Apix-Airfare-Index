from scraper.spiders.generic_ota import GenericOTASpider


class CleartripSpider(GenericOTASpider):
    name = "cleartrip"
    source_name = "cleartrip"
    allowed_domains = ["cleartrip.com"]
    search_base_url = "https://www.cleartrip.com/flights/results"
