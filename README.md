# APIx -- Real-time Airfare Price Index for India

A prototype pipeline that scrapes/synthesizes airline & OTA fares across a
DGCA-weighted city-pair basket and five advance-purchase windows (T+1/7/15/30/45),
cleans and decomposes them, builds a real-time airfare price index, validates
it against the official MoSPI CPI airfare sub-index, and serves it via an API
+ React dashboard. See `docs/ARCHITECTURE.md` for the full design and
`docs/VALIDATION.md` for why this defaults to a calibrated synthetic dataset
rather than depending on live scraping succeeding.

## Quickstart (backend + API, Python only)

A `.venv/` (Python 3.13) already exists in this project with every
dependency installed -- it exists specifically so the project always runs
against the right Python, regardless of what else is installed system-wide
or which `python` a plain terminal happens to resolve to.

```bash
.venv\Scripts\activate      # Windows

# Backfill demo data (Feb-Jul 2026 synthetic history), clean, build the index,
# and backtest against cpi_1054.xlsx -- takes about a minute.
python -m scripts.seed_demo_data

# Serve the API
uvicorn api.main:app --reload
# -> http://127.0.0.1:8000/docs
```

(On a fresh machine without `.venv/` yet: `python -m venv .venv`, activate
it as above, then `pip install -r requirements.txt`.)

## Dashboard (needs Node.js -- not installed in this environment; install it, then:)

```bash
cd dashboard
npm install
npm run dev
# -> http://localhost:5173  (proxies /api to http://127.0.0.1:8000 by default)
```

## Live scraping (optional, in addition to the synthetic default)

```bash
playwright install chromium
python -m scraper.run live --sources indigo,makemytrip     # hardened reference spiders
python -m scraper.run live                                  # all 11 sources (9 use placeholder selectors -- see docs/ETHICAL_SCRAPING.md)
```

Live and synthetic rows coexist in the same database, distinguished by
`data_source_type`. Re-run the daily job manually any time with
`python -m scraper.run synthetic --days 1` or start the long-lived scheduler
(`python -m scraper.scheduler`, see `.env.example` for mode/timing config).

## Tests

```bash
pytest
```

26 tests cover fare decomposition, outlier cleaning, index-construction math,
lead-time elasticity, the synthetic generator, offline (fixture-HTML) spider
parsing, and the API layer.

## Layout

```
scraper/    scraping engine (Scrapy+Playwright spiders, ethical-scraping
            middlewares, scheduler) + the calibrated synthetic generator
pipeline/   RawObservation -> CleanFare (decomposition, outlier removal, dedupe)
db/         SQLAlchemy schema (SQLite by default, DATABASE_URL for Postgres)
index/      APIx construction, basket weights, elasticity, heatmap
validation/ backtest against cpi_1054.xlsx (the real CPI airfare sub-index)
api/        FastAPI app
dashboard/  React + Vite + Recharts UI
scripts/    one-shot demo seed
tests/      pytest suite
docs/       architecture, ethical-scraping policy, data dictionary, API, validation
```

See `docs/ARCHITECTURE.md`, `docs/ETHICAL_SCRAPING.md`,
`docs/DATA_DICTIONARY.md`, `docs/API.md`, `docs/VALIDATION.md`.
