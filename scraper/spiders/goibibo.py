from scraper.spiders.generic_ota import GenericOTASpider


class GoibiboSpider(GenericOTASpider):
    name = "goibibo"
    source_name = "goibibo"
    allowed_domains = ["goibibo.com"]
    search_base_url = "https://www.goibibo.com/flights/air-search"
