from scraper.spiders.generic_ota import GenericOTASpider


class IxigoSpider(GenericOTASpider):
    name = "ixigo"
    source_name = "ixigo"
    allowed_domains = ["ixigo.com"]
    search_base_url = "https://www.ixigo.com/search/result/flight"
