# Architecture

## Problem

MoSPI's CPI airfare sub-index is collected manually from a limited set of
outlets, but >90% of domestic tickets are bought online and fares swing
200-400% intraday based on advance-booking window, day-of-week, demand,
season and fuel surcharges. APIx automates daily collection across a
representative basket of routes and booking windows so the index reflects
what travellers actually pay.

## Data flow

```
scraper/spiders/*.py  ─┐                      scraper/synthetic/generator.py
 (live, Scrapy+        │                        (calibrated synthetic
  Playwright)          │                         fallback -- see below)
                        ▼                                │
              scraper/pipelines.py                       │
              (FarePipeline: decompose                    │
               + upsert)                                  │
                        │                                 │
                        ▼                                 ▼
              db.RawObservation  ◄─────── pipeline/load.py (bulk insert)
                        │
                        ▼
              pipeline/clean.py  (MAD outlier removal, sold-out handling)
                        │
                        ▼
              db.CleanFare  (daily median fare per route x carrier x window)
                        │
                        ▼
              index/apix.py  (DGCA-weighted index, daily/weekly/monthly)
                        │
                        ▼
              db.IndexValue  ──────────────►  api/  (FastAPI)  ──►  dashboard/ (React)
                        │
                        ▼
              validation/backtest.py  vs  cpi_1054.xlsx (official CPI airfare index)
                        │
                        ▼
              db.ValidationResult
```

## Why hybrid (live + synthetic)

Live scraping of production airline/OTA sites is inherently fragile for a
demo: anti-bot measures, CAPTCHAs, and markup changes can silently break a
spider between when it's written and when it's run. Rather than pretend
otherwise, the system stores a `data_source_type` on every RawObservation
(`live` or `synthetic_fallback`) and defaults the running pipeline to the
calibrated synthetic generator (`scraper/synthetic/`), so cleaning, index
construction, the API and the dashboard are always exercisable end to end.
The real spiders (`scraper/spiders/`) are fully wired into the same
pipeline and item schema -- pointing `scraper/run.py` at `--mode live`
produces indistinguishable RawObservation rows, just tagged `live`.

Two spiders (IndiGo, MakeMyTrip) are hardened reference implementations
demonstrating the airline-direct and OTA-aggregator cases; the other nine
share the same base classes (`scraper/spiders/generic_airline.py`,
`generic_ota.py`) with placeholder CSS selectors that need verifying
against each site's current DOM -- see the module docstrings.

## Key modules

| Module | Responsibility |
|---|---|
| `scraper/config.py` | Single source of truth: city-pair basket + DGCA weights, carriers, sources, advance-purchase windows |
| `scraper/synthetic/` | Calibrated synthetic fare generator (stylized lead-time/seasonality/day-of-week facts) |
| `scraper/spiders/`, `scraper/middlewares.py`, `scraper/pipelines.py` | Real scraping engine: robots.txt compliance, rate limiting, CAPTCHA/block detection, item -> DB |
| `scraper/scheduler.py` | Daily cron job (APScheduler) |
| `pipeline/` | RawObservation -> CleanFare: decomposition, outlier removal, dedupe |
| `db/models.py` | SQLAlchemy schema (SQLite by default, Postgres via `DATABASE_URL`) |
| `index/` | APIx construction, basket weights, lead-time elasticity, sector heatmap |
| `validation/backtest.py` | APIx vs `cpi_1054.xlsx` (official CPI airfare sub-index) |
| `api/` | FastAPI app exposing everything above |
| `dashboard/` | React + Vite + Recharts UI |
| `scripts/seed_demo_data.py` | One-shot: backfill synthetic history -> clean -> index -> backtest |

## Index methodology

See the docstring at the top of `index/apix.py` and `docs/VALIDATION.md` for
the full weighted-relative construction and the base-period rebasing used
when comparing against CPI.
