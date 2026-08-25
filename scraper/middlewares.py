"""Downloader middlewares implementing requirement #4's safeguards:
session/UA rotation, optional proxy rotation, and CAPTCHA/block *detection*
with graceful backoff.

Explicitly out of scope, by design: solving or bypassing CAPTCHAs, or any
technique meant to evade a site's anti-bot measures. When a block/CAPTCHA is
detected the request is dropped and the cell is logged as failed -- the
operator re-runs with `--mode synthetic` to fill that gap, or revisits the
source's ToS. See docs/ETHICAL_SCRAPING.md.
"""
import itertools
import logging

from scrapy.exceptions import IgnoreRequest

logger = logging.getLogger("apix_scraper.middlewares")

# Small pool of descriptive, honest user agents (not spoofed browser strings)
# for the non-Playwright requests (robots.txt fetches, simple GETs). Pages
# rendered via Playwright necessarily carry a real browser UA -- that's a
# requirement of JS rendering, not an attempt to disguise the crawler; the
# crawler still identifies itself via honoring robots.txt and rate limits.
_USER_AGENTS = [
    "APIxResearchBot/1.0 (+mailto:research@apix-prototype.example)",
    "APIxResearchBot/1.0 (+mailto:research@apix-prototype.example; CPI airfare study)",
]

_BLOCK_TEXT_MARKERS = (
    "captcha",
    "unusual traffic",
    "access denied",
    "are you a robot",
    "verify you are human",
    "bot detection",
)
_BLOCK_STATUS_CODES = {403, 429, 503}


class RotateUserAgentMiddleware:
    def __init__(self):
        self._cycle = itertools.cycle(_USER_AGENTS)

    def process_request(self, request, spider):
        if "playwright" not in request.meta:
            request.headers.setdefault("User-Agent", next(self._cycle))
        return None


class CaptchaBlockDetectionMiddleware:
    """Detects (never solves) CAPTCHA/anti-bot block pages and drops the
    request instead of retrying into a ban."""

    def process_response(self, request, response, spider):
        if response.status in _BLOCK_STATUS_CODES:
            logger.warning("Block-like status %s for %s -- dropping, marking cell failed", response.status, request.url)
            spider.crawler.stats.inc_value("apix/blocked_responses")
            raise IgnoreRequest(f"Blocked response ({response.status}) from {request.url}")

        body_sample = response.text[:20_000].lower() if hasattr(response, "text") else ""
        if any(marker in body_sample for marker in _BLOCK_TEXT_MARKERS):
            logger.warning("CAPTCHA/block marker detected in body for %s -- dropping", request.url)
            spider.crawler.stats.inc_value("apix/captcha_detected")
            raise IgnoreRequest(f"CAPTCHA/block page detected at {request.url}")

        return response


class ProxyRotationMiddleware:
    """Opt-in proxy rotation -- only active when HTTP_PROXY_LIST is set
    (see scraper/settings.py). No proxies are bundled with this prototype."""

    def __init__(self, proxies):
        self._cycle = itertools.cycle(proxies)

    @classmethod
    def from_crawler(cls, crawler):
        proxies = crawler.settings.getlist("HTTP_PROXY_LIST")
        return cls(proxies)

    def process_request(self, request, spider):
        request.meta["proxy"] = next(self._cycle)
        return None
