from scraper.spiders.generic_ota import GenericOTASpider


class YatraSpider(GenericOTASpider):
    name = "yatra"
    source_name = "yatra"
    allowed_domains = ["yatra.com"]
    search_base_url = "https://www.yatra.com/flights/search"
