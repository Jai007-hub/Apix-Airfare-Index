"""Scrapy project settings -- ethical-scraping safeguards live here.

ROBOTSTXT_OBEY, AutoThrottle and a single concurrent request per domain are
the load-bearing settings for requirement #4 (rate-limiting / compliance).
scrapy-playwright renders JS-heavy OTA search pages; CONCURRENT_REQUESTS_PER_DOMAIN=1
plus AutoThrottle keeps that from hammering any one site even when several
routes/windows are queued.
"""
import os

BOT_NAME = "apix_scraper"
SPIDER_MODULES = ["scraper.spiders"]
NEWSPIDER_MODULE = "scraper.spiders"

# --- Ethical scraping safeguards (see docs/ETHICAL_SCRAPING.md) ---
ROBOTSTXT_OBEY = True
CONCURRENT_REQUESTS = 4
CONCURRENT_REQUESTS_PER_DOMAIN = 1
DOWNLOAD_DELAY = 2.0
RANDOMIZE_DOWNLOAD_DELAY = True
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 2.0
AUTOTHROTTLE_MAX_DELAY = 30.0
AUTOTHROTTLE_TARGET_CONCURRENCY = 1.0
AUTOTHROTTLE_DEBUG = False
RETRY_TIMES = 2
RETRY_HTTP_CODES = [500, 502, 503, 504, 522, 524, 408]
# 403/429 are treated as block/CAPTCHA signals by CaptchaBlockDetectionMiddleware,
# not blindly retried -- see scraper/middlewares.py.

USER_AGENT = (
    "APIxResearchBot/1.0 (+mailto:research@apix-prototype.example; "
    "non-commercial CPI airfare index research; obeys robots.txt)"
)

DOWNLOADER_MIDDLEWARES = {
    "scraper.middlewares.RotateUserAgentMiddleware": 400,
    "scraper.middlewares.CaptchaBlockDetectionMiddleware": 450,
}

ITEM_PIPELINES = {
    "scraper.pipelines.FarePipeline": 300,
}

# --- Playwright (JS rendering for SPA-style OTA search pages) ---
DOWNLOAD_HANDLERS = {
    "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
    "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
}
TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
PLAYWRIGHT_LAUNCH_OPTIONS = {"headless": True}
PLAYWRIGHT_DEFAULT_NAVIGATION_TIMEOUT = 30_000

# Proxy rotation is opt-in: set HTTP_PROXY_LIST to a comma-separated list of
# proxy URLs to enable scraper.middlewares.ProxyRotationMiddleware. Left
# empty by default -- no proxies are bundled with this prototype.
HTTP_PROXY_LIST = [p.strip() for p in os.environ.get("HTTP_PROXY_LIST", "").split(",") if p.strip()]
if HTTP_PROXY_LIST:
    DOWNLOADER_MIDDLEWARES["scraper.middlewares.ProxyRotationMiddleware"] = 410

LOG_LEVEL = os.environ.get("SCRAPY_LOG_LEVEL", "INFO")
