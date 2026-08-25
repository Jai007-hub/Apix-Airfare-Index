# Ethical Scraping Policy

This prototype's live scraping engine (`scraper/`) is built to the following
non-negotiable rules. They're enforced in code, not just documented:

## 1. robots.txt is obeyed, always

`ROBOTSTXT_OBEY = True` in `scraper/settings.py`. Scrapy fetches and caches
each domain's robots.txt and will not request a disallowed path. If a
source's robots.txt disallows the fare-search path this prototype needs,
that source is simply not scraped live -- there is no override flag. The
synthetic fallback (`scraper/synthetic/`) covers the resulting gap in the
demo dataset, tagged `data_source_type=synthetic_fallback` so it's never
mistaken for a real observation.

## 2. Rate limiting

- `CONCURRENT_REQUESTS_PER_DOMAIN = 1` -- never more than one in-flight
  request to a given site.
- `AUTOTHROTTLE_ENABLED = True` with a conservative target concurrency of
  1.0 and randomized delay -- the crawler backs off automatically if a site
  responds slowly, rather than hammering it.
- The daily schedule (`scraper/scheduler.py`) runs at an off-peak hour by
  default (03:00 local), configurable via `APIX_SCHEDULE_HOUR`.

## 3. No CAPTCHA solving, no anti-bot evasion

`scraper/middlewares.py`'s `CaptchaBlockDetectionMiddleware` inspects
responses for block/CAPTCHA signals (403/429/503 status codes, or body text
like "captcha", "unusual traffic", "verify you are human") and **drops the
request** -- it never attempts to solve, retry-through, or disguise the
crawler to get past a block. A blocked cell is logged and left for the
synthetic generator to fill, or for the operator to revisit manually.
Proxy rotation (`ProxyRotationMiddleware`) is opt-in via `HTTP_PROXY_LIST`
and, again, exists for distributing legitimate rate-limited load -- not for
evading a block that a site has deliberately imposed.

## 4. Honest identification

`USER_AGENT` in `scraper/settings.py` identifies the crawler and a contact
address rather than spoofing a browser string, for the non-JS-rendered
requests Scrapy makes directly (robots.txt fetches, simple GETs). Pages
rendered via Playwright necessarily carry a real browser UA -- that's a
mechanical requirement of executing a site's JavaScript, not an attempt to
disguise the crawler; robots.txt compliance and rate limiting still apply
identically to those requests.

## 5. Scope discipline

The crawler only ever requests fare-search result pages for the documented
city-pair basket (`scraper/config.py`) across five advance-purchase windows.
It does not authenticate, does not attempt to complete a booking, and does
not crawl beyond the search results it needs.

## Per-source status

Two spiders (`indigo`, `makemytrip`) are hardened reference implementations.
The remaining nine (`air_india`, `air_india_express`, `akasa_air`,
`spicejet`, `yatra`, `easemytrip`, `cleartrip`, `ixigo`, `goibibo`) share the
same compliant request/rate-limiting framework but use placeholder CSS
selectors -- see `scraper/spiders/generic_airline.py` and
`generic_ota.py`. Before running any spider against a live site, re-check
that site's current robots.txt and Terms of Service; this document describes
the crawler's behavior, not a legal clearance for any specific source.
